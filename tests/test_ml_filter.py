"""Phase 7 ML layer (#19): feature hygiene, split discipline, rule extraction."""

import numpy as np
import pandas as pd
import pytest

from tamad import ml_filter

from tests.conftest import make_candles


def walk_candles(n=60, start="2022-06-01", freq="15min"):
    """Deterministic wiggly candles: alternating red/green pairs, mild drift."""
    rows = []
    price = 100.0
    for i in range(n):
        drift = 0.3 if (i // 2) % 2 == 0 else -0.25
        o = price
        c = price + drift
        h = max(o, c) + 0.2
        l = min(o, c) - 0.2
        rows.append((o, h, l, c))
        price = c
    return make_candles(rows, start=start, freq=freq)


def one_setup(candles, bar, side=1):
    entry = float(candles["close"].iloc[bar])
    sl = entry - 1.5 * side
    return pd.DataFrame(
        {
            "side": [side], "entry": [entry], "sl": [sl],
            "tp": [entry + side * 3 * (entry - sl) * side],
            "risk": [(entry - sl) * side], "sweep": [True], "c1_atr_mult": [1.2],
        },
        index=pd.DatetimeIndex([candles.index[bar]], name="time"),
    )


def synthetic_pair(n=200, edge_feature=None, seed=7, year_split=100):
    """(features, trades) where wins are random unless edge_feature plants one."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2022-01-01", periods=n, freq="6h", tz="UTC")
    feats = pd.DataFrame({
        "vol_ratio": rng.uniform(0.5, 2.0, n),
        "risk_pct": rng.uniform(0.05, 1.0, n),
        "hour": idx.hour.astype(float),
    }, index=idx)
    if edge_feature:
        above = feats[edge_feature] > feats[edge_feature].median()
        win = above & (rng.random(n) < 0.8)
    else:
        win = pd.Series(rng.random(n) < 0.4, index=idx)
    r = np.where(win, 2.0, -1.0)
    exit_time = idx + pd.Timedelta(hours=3)
    if year_split is not None:
        exit_time = exit_time.where(
            np.arange(n) < year_split, exit_time + pd.DateOffset(years=1))
    trades = pd.DataFrame({
        "signal_time": idx, "exit_time": exit_time, "side": 1,
        "fill": 100.0, "sl": 99.0,
        "r_multiple": r, "pnl": r, "asset": "BTCUSDT",
    })
    return feats, trades


def test_features_computed_without_lookahead():
    candles = walk_candles()
    setups = one_setup(candles, bar=30)
    before = ml_filter.build_features(candles, setups)

    mutated = candles.copy()
    mutated.iloc[31:, :4] = mutated.iloc[31:, :4] + 50.0
    after = ml_filter.build_features(mutated, setups)

    pd.testing.assert_frame_equal(before, after)


def test_features_include_cost_and_context_columns():
    candles = walk_candles()
    setups = one_setup(candles, bar=30)
    kind_hits = {"ob": {candles.index[30]}, "swing": set(), "sr": set(),
                 "fvg": set(), "div": set()}
    feats = ml_filter.build_features(candles, setups, kind_hits=kind_hits)
    for col in ("risk_pct", "vol_ratio", "hour", "rsi14", "in_ob",
                "confluence_count", "hold_margin_atr"):
        assert col in feats.columns
    assert feats.loc[candles.index[30], "in_ob"] == 1.0
    assert feats.loc[candles.index[30], "confluence_count"] == 1.0
    expected_risk_pct = 100 * 1.5 / float(candles["close"].iloc[30])
    assert feats.loc[candles.index[30], "risk_pct"] == pytest.approx(expected_risk_pct)


def test_merge_aligns_trades_with_features_on_signal_time():
    feats, trades = synthetic_pair(n=50)
    trades = trades.iloc[:40]  # some setups never became trades
    X, y, meta = ml_filter.merge(feats, trades)
    assert len(X) == 40
    assert list(X.index) == list(trades["signal_time"])
    assert (y == (trades["r_multiple"].to_numpy() > 0)).all()
    assert "exit_time" in meta.columns and "r_multiple" in meta.columns


def test_study_trains_only_on_pre_split_exits():
    pair = synthetic_pair(n=200, year_split=120)
    train_end = pd.Timestamp("2023-01-01", tz="UTC")
    study = ml_filter.run_study([pair], train_end=train_end, n_estimators=40)
    assert study["train_meta"]["exit_time"].max() < train_end
    assert study["n_train"] == 120
    assert study["n_total"] == 200


def test_study_is_deterministic():
    pair = synthetic_pair(n=200)
    train_end = pd.Timestamp("2023-01-01", tz="UTC")
    a = ml_filter.run_study([pair], train_end=train_end, n_estimators=40)
    b = ml_filter.run_study([pair], train_end=train_end, n_estimators=40)
    pd.testing.assert_series_equal(a["importances"], b["importances"])


def test_candidate_rules_recover_a_planted_edge():
    pair = synthetic_pair(n=400, edge_feature="vol_ratio", year_split=None)
    train_end = pd.Timestamp("2030-01-01", tz="UTC")  # everything is training
    study = ml_filter.run_study([pair], train_end=train_end, n_estimators=60)
    assert study["importances"].index[0] == "vol_ratio"

    rules = ml_filter.candidate_rules(study, top_k=3)
    best = rules.iloc[0]
    assert best["feature"] == "vol_ratio"
    assert best["direction"] == ">="
    assert best["train_pf"] > best["baseline_pf"]

    feats, trades = pair
    kept = ml_filter.apply_rule(feats, trades, best["feature"],
                                best["direction"], best["threshold"])
    assert 0 < len(kept) < len(trades)
    assert (feats.loc[kept["signal_time"], "vol_ratio"] >= best["threshold"]).all()


def test_confirm_rules_reports_test_window_with_and_without_costs():
    pair = synthetic_pair(n=400, edge_feature="vol_ratio", year_split=200)
    train_end = pd.Timestamp("2023-01-01", tz="UTC")
    rules = pd.DataFrame([{"feature": "vol_ratio", "direction": ">=",
                           "threshold": float(pair[0]["vol_ratio"].median()),
                           "pool": "final"}])
    out = ml_filter.confirm_rules(rules, [pair], train_end=train_end)
    row = out.iloc[0]
    assert row["test_n_kept"] < row["test_n_baseline"]
    assert row["test_pf_filtered"] > row["test_pf_baseline"]
    assert row["test_pf_filtered_costs"] < row["test_pf_filtered"]


def test_side_asymmetry_groups_by_asset_and_side():
    feats, trades = synthetic_pair(n=200, year_split=100)
    trades.loc[trades.index[::2], "side"] = -1
    table = ml_filter.side_asymmetry([(feats, trades)],
                                     train_end=pd.Timestamp("2023-01-01", tz="UTC"))
    assert set(table["side"]) == {1, -1}
    assert (table["asset"] == "BTCUSDT").all()
    assert {"train_pf", "test_pf", "train_n", "test_n"} <= set(table.columns)


def test_rediscovery_check_flags_known_filters():
    imp = pd.Series({"in_ob": 0.3, "hour": 0.25, "vol_ratio": 0.2,
                     "risk_pct": 0.15, "rsi14": 0.1}).sort_values(ascending=False)
    result = ml_filter.rediscovery_check(imp, top_n=5)
    assert result["passed"] is True
    imp2 = pd.Series({"vol_ratio": 0.4, "rsi14": 0.3, "ret20_atr": 0.2,
                      "c2_body_atr": 0.06, "in_ob": 0.04}).sort_values(ascending=False)
    assert ml_filter.rediscovery_check(imp2, top_n=3)["passed"] is False
