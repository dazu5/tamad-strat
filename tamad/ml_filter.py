"""Phase 7 ML layer (#19): a random forest FILTERS trades, never generates them.

Revelio's TJR-rebuild move: train a random forest on PRE-TRADE features of
the strategy's own trades, read the importance ranking, extract candidate
rules as interpretable thresholds, veto anything without market logic,
and only then confirm survivors on the locked test window — with and
without costs. Expected outcome per the methodology: almost everything
dies.

Discipline in code:
- every feature is computed from bars at or before the signal bar
  (fixture-enforced: tests/test_ml_filter.py mutates the future);
- the forest trains ONLY on trades whose EXIT is before the split;
- candidate thresholds come from training quantiles alone;
- the test window is touched exclusively by `confirm_rules`, in a
  separate CLI stage run after the human veto pass.

Usage:
    python -m tamad.ml_filter --stage candidates
    python -m tamad.ml_filter --stage confirm --rules results/ml/confirm_these.json
"""

from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path

import numpy as np
import pandas as pd

from tamad import pattern
from tamad.zones import rsi

FEATURE_SPECS = {
    "side": "long/short structural asymmetry (spot crypto's long bias) — the TJR survivor analog",
    "sweep": "liquidity grab before the reversal (the group's own rationale)",
    "c1_atr_mult": "climax exhaustion — an outsized first candle marks capitulation",
    "risk_pct": "stop width vs price: wider stops survive noise AND pay less cost in R",
    "c1_range_atr": "conviction of the climax leg vs regime volatility",
    "c2_body_atr": "strength of the reclaim candle",
    "c2_range_atr": "reach of the reclaim candle",
    "c3_body_atr": "size of the hold candle",
    "c3_range_atr": "reach of the hold candle",
    "hold_margin_atr": "how decisively C3 held C2's open — the hold rule as a number",
    "c3_front_wick_atr": "rejection tail in the reversal direction on the signal candle",
    "vol_ratio": "volatility regime (ATR vs its 30d mean) — expansion vs compression",
    "atr_pct": "absolute volatility level of the asset at signal time",
    "hour": "session liquidity structure (US hours already proved out-of-sample)",
    "dow": "weekly cycle — WEAK logic unless it maps to weekend/weekday liquidity",
    "is_weekend": "weekend crypto liquidity thins; different participant mix",
    "ema50_dist_atr": "counter-trend depth vs the fast regime",
    "ema200_dist_atr": "counter-trend depth vs the slow regime",
    "ret20_atr": "how stretched the move into the pattern is (short-horizon momentum)",
    "dist_hi20_atr": "room overhead to recent extremes",
    "dist_lo20_atr": "support beneath at recent extremes",
    "rsi14": "momentum exhaustion (the divergence family, continuous form)",
    "in_swing": "anchored at a recent swing extreme (taught significant area)",
    "in_sr": "anchored at a multi-touch S/R cluster (taught significant area)",
    "in_fvg": "anchored at an unfilled imbalance (taught significant area)",
    "in_ob": "anchored at an order block (the proven survivor zone)",
    "in_div": "anchored at an RSI divergence (taught significant area)",
    "confluence_count": "stacked significant areas agreeing on the level",
}

ZONE_KINDS = ("swing", "sr", "fvg", "ob", "div")


def _pf(r: pd.Series) -> float:
    gross_p = float(r[r > 0].sum())
    gross_l = float(-r[r < 0].sum())
    if gross_l > 0:
        return gross_p / gross_l
    return float("inf") if gross_p > 0 else 0.0


def build_features(candles: pd.DataFrame, setups: pd.DataFrame,
                   kind_hits: dict | None = None) -> pd.DataFrame:
    """One row per setup, every value computed from bars <= the signal bar."""
    o, h, l, c = candles["open"], candles["high"], candles["low"], candles["close"]
    atr_s = pattern.atr(candles)
    body = (c - o).abs()
    rng = h - l

    delta = candles.index.to_series().diff().median()
    win30 = max(20, int(pd.Timedelta(days=30) / delta)) if pd.notna(delta) else 20

    feats = pd.DataFrame(index=candles.index)
    feats["c1_range_atr"] = rng.shift(2) / atr_s
    feats["c2_body_atr"] = body.shift(1) / atr_s
    feats["c2_range_atr"] = rng.shift(1) / atr_s
    feats["c3_body_atr"] = body / atr_s
    feats["c3_range_atr"] = rng / atr_s
    feats["vol_ratio"] = atr_s / atr_s.rolling(win30, min_periods=win30 // 10).mean()
    feats["atr_pct"] = 100 * atr_s / c
    feats["hour"] = candles.index.hour.astype(float)
    feats["dow"] = candles.index.dayofweek.astype(float)
    feats["is_weekend"] = (candles.index.dayofweek >= 5).astype(float)
    ema50 = c.ewm(span=50, adjust=False).mean()
    ema200 = c.ewm(span=200, adjust=False).mean()
    feats["ema50_dist_atr"] = (c - ema50) / atr_s
    feats["ema200_dist_atr"] = (c - ema200) / atr_s
    feats["ret20_atr"] = (c - c.shift(20)) / atr_s
    feats["dist_hi20_atr"] = (h.rolling(20).max() - c) / atr_s
    feats["dist_lo20_atr"] = (c - l.rolling(20).min()) / atr_s
    feats["rsi14"] = rsi(c, 14)
    lower_wick = (pd.concat([o, c], axis=1).min(axis=1) - l) / atr_s
    upper_wick = (h - pd.concat([o, c], axis=1).max(axis=1)) / atr_s

    out = feats.loc[setups.index].copy()
    side = setups["side"].astype(float)
    out["side"] = side
    out["sweep"] = setups["sweep"].astype(float)
    out["c1_atr_mult"] = setups["c1_atr_mult"]
    out["risk_pct"] = 100 * setups["risk"] / setups["entry"]
    out["hold_margin_atr"] = (c.loc[setups.index] - o.shift(1).loc[setups.index]) \
        * side / atr_s.loc[setups.index]
    out["c3_front_wick_atr"] = np.where(
        side > 0, lower_wick.loc[setups.index], upper_wick.loc[setups.index])

    if kind_hits is not None:
        total = pd.Series(0.0, index=out.index)
        for kind in ZONE_KINDS:
            member = out.index.isin(list(kind_hits.get(kind, ()))).astype(float)
            out[f"in_{kind}"] = member
            total += member
        out["confluence_count"] = total
    return out


def merge(features: pd.DataFrame, trades: pd.DataFrame):
    """Align feature rows to trades by signal_time -> (X, y, meta)."""
    sig = pd.DatetimeIndex(trades["signal_time"])
    X = features.reindex(sig)
    y = pd.Series(trades["r_multiple"].to_numpy() > 0, index=sig, name="win")
    meta_cols = [c for c in ("exit_time", "r_multiple", "pnl", "asset",
                             "side", "fill", "sl") if c in trades.columns]
    meta = trades[meta_cols].copy()
    meta.index = sig
    return X, y, meta


def run_study(pairs: list, train_end: pd.Timestamp, seed: int = 42,
              n_estimators: int = 300, min_samples_leaf: int = 30,
              n_jobs: int = 2) -> dict:
    """Fit the forest on trades whose EXIT precedes train_end. Returns the
    importance ranking plus the exact training frame (for hygiene tests)."""
    from sklearn.ensemble import RandomForestClassifier

    xs, ys, metas = [], [], []
    for features, trades in pairs:
        X, y, meta = merge(features, trades)
        xs.append(X)
        ys.append(y)
        metas.append(meta)
    X = pd.concat(xs)
    y = pd.concat(ys)
    meta = pd.concat(metas)

    if "asset" in meta.columns and meta["asset"].nunique() > 1:
        for asset in sorted(meta["asset"].unique()):
            X[f"asset_{asset}"] = (meta["asset"] == asset).to_numpy().astype(float)

    valid = X.notna().all(axis=1).to_numpy()
    X, y, meta = X[valid], y[valid], meta[valid]

    exit_t = pd.to_datetime(meta["exit_time"], utc=True)
    train_mask = (exit_t < train_end).to_numpy()
    X_train, y_train, train_meta = X[train_mask], y[train_mask], meta[train_mask]

    model = RandomForestClassifier(
        n_estimators=n_estimators, min_samples_leaf=min_samples_leaf,
        random_state=seed, n_jobs=n_jobs)
    model.fit(X_train.to_numpy(), y_train.to_numpy())
    importances = pd.Series(model.feature_importances_, index=X_train.columns) \
        .sort_values(ascending=False)

    return {"model": model, "importances": importances,
            "X_train": X_train, "y_train": y_train, "train_meta": train_meta,
            "n_train": int(train_mask.sum()), "n_total": int(len(X)),
            "n_dropped_nan": int((~valid).sum()), "train_end": train_end}


def candidate_rules(study: dict, top_k: int = 8,
                    quantiles=tuple(np.round(np.arange(0.1, 0.91, 0.1), 2)),
                    min_retention: float = 0.2, max_retention: float = 0.95,
                    min_lift: float = 1.05) -> pd.DataFrame:
    """Best single-threshold rule per top-importance feature, TRAINING data only."""
    X, meta = study["X_train"], study["train_meta"]
    baseline_pf = _pf(meta["r_multiple"])
    rows = []
    for feature in study["importances"].index[:top_k]:
        best = None
        for q in quantiles:
            thr = float(X[feature].quantile(q))
            for direction in (">=", "<="):
                mask = (X[feature] >= thr) if direction == ">=" else (X[feature] <= thr)
                retention = float(mask.mean())
                if not (min_retention <= retention <= max_retention):
                    continue
                pf = _pf(meta["r_multiple"][mask.to_numpy()])
                if best is None or pf > best["train_pf"]:
                    best = {"feature": feature, "direction": direction,
                            "threshold": thr, "quantile": float(q),
                            "train_retention": retention, "train_pf": pf,
                            "baseline_pf": baseline_pf,
                            "rationale": FEATURE_SPECS.get(
                                feature.split("asset_")[0] if feature.startswith("asset_")
                                else feature,
                                "asset identity — basket membership question"
                                if feature.startswith("asset_") else "")}
        if best is not None and best["train_pf"] > baseline_pf * min_lift:
            rows.append(best)
    out = pd.DataFrame(rows, columns=["feature", "direction", "threshold",
                                      "quantile", "train_retention", "train_pf",
                                      "baseline_pf", "rationale"])
    return out.sort_values("train_pf", ascending=False).reset_index(drop=True)


def apply_rule(features: pd.DataFrame, trades: pd.DataFrame,
               feature: str, direction: str, threshold: float) -> pd.DataFrame:
    vals = features.reindex(pd.DatetimeIndex(trades["signal_time"]))[feature]
    mask = (vals >= threshold) if direction == ">=" else (vals <= threshold)
    return trades[mask.fillna(False).to_numpy()]


def _pooled_test(pairs: list, train_end: pd.Timestamp, rule_features: list):
    """Concat pairs positionally, feature values attached as __<name> columns."""
    frames = []
    for features, trades in pairs:
        aug = trades.copy()
        sig = pd.DatetimeIndex(trades["signal_time"])
        for feature in rule_features:
            aug[f"__{feature}"] = features.reindex(sig)[feature].to_numpy()
        frames.append(aug)
    pooled = pd.concat(frames, ignore_index=True)
    exit_t = pd.to_datetime(pooled["exit_time"], utc=True)
    return pooled[(exit_t >= train_end).to_numpy()]


def confirm_rules(rules: pd.DataFrame, pairs: list,
                  train_end: pd.Timestamp) -> pd.DataFrame:
    """THE test-window touch: baseline vs filtered, with and without costs."""
    from tamad import costs as costs_mod

    test = _pooled_test(pairs, train_end, list(rules["feature"].unique()))
    with_costs = costs_mod.apply(test, costs_mod.BINANCE_SPOT)
    rows = []
    for _, rule in rules.iterrows():
        vals = test[f"__{rule['feature']}"]
        mask = ((vals >= rule["threshold"]) if rule["direction"] == ">="
                else (vals <= rule["threshold"])).fillna(False).to_numpy()
        rows.append({
            "feature": rule["feature"], "direction": rule["direction"],
            "threshold": rule["threshold"],
            "test_n_baseline": int(len(test)), "test_n_kept": int(mask.sum()),
            "test_retention": float(mask.mean()) if len(test) else 0.0,
            "test_pf_baseline": _pf(test["r_multiple"]),
            "test_pf_filtered": _pf(test["r_multiple"][mask]),
            "test_pf_baseline_costs": _pf(with_costs["r_multiple"]),
            "test_pf_filtered_costs": _pf(with_costs["r_multiple"][mask]),
        })
    return pd.DataFrame(rows)


def side_asymmetry(pairs: list, train_end: pd.Timestamp) -> pd.DataFrame:
    """Per asset x side PF, train and test — the long-only-indices analog."""
    pooled = pd.concat([t for _, t in pairs], ignore_index=True)
    exit_t = pd.to_datetime(pooled["exit_time"], utc=True)
    is_train = (exit_t < train_end).to_numpy()
    rows = []
    for (asset, side), group in pooled.groupby(["asset", "side"]):
        g_train = group[is_train[group.index]]
        g_test = group[~is_train[group.index]]
        rows.append({"asset": asset, "side": int(side),
                     "train_n": int(len(g_train)), "train_pf": _pf(g_train["r_multiple"]),
                     "test_n": int(len(g_test)), "test_pf": _pf(g_test["r_multiple"])})
    return pd.DataFrame(rows).sort_values(["asset", "side"]).reset_index(drop=True)


def rediscovery_check(importances: pd.Series, top_n: int = 10,
                      known=("in_ob", "confluence_count", "hour")) -> dict:
    """The forest must re-find filters we already proved, or it's noise."""
    order = list(importances.index)
    ranks = {k: (order.index(k) + 1) if k in order else None for k in known}
    passed = any(r is not None and r <= top_n for r in ranks.values())
    return {"passed": bool(passed), "ranks": ranks, "top_n": top_n}


# ---------------------------------------------------------------- CLI

FINAL_PILLS = dict(sweep_required=False, c1_min_atr=1.0, zones=("ob",),
                   session="us_16_24", bias_tf=None)
SANITY_PILLS = dict(sweep_required=False, c1_min_atr=1.0, zones=(),
                    session=None, bias_tf=None)


def _pool_paths(out_dir: Path, pool: str, interval: str, symbol: str):
    stem = out_dir / f"pool_{pool}_{interval}_{symbol}"
    return Path(f"{stem}_features.parquet"), Path(f"{stem}_trades.parquet")


def build_pools(interval: str, start: str, end: str, out_dir: Path) -> dict:
    """Build + persist (features, trades) per pool; cached across stages."""
    from tamad import ablation, engine, exits
    from tamad.matrix import SYMBOLS

    pools = {"final": [], "sanity": []}
    for symbol in SYMBOLS:
        cached = True
        for pool in pools:
            for path in _pool_paths(out_dir, pool, interval, symbol):
                cached &= path.exists()
        if cached:
            for pool in pools:
                fp, tp = _pool_paths(out_dir, pool, interval, symbol)
                pools[pool].append((pd.read_parquet(fp), pd.read_parquet(tp)))
            print(f"{symbol} {interval}: pools loaded from cache", flush=True)
            continue

        ctx = ablation.combo_context(symbol, interval, start, end)
        feats_all = build_features(ctx["candles"], ctx["setups"],
                                   kind_hits=ctx["kind_hits"])
        for pool, pills, simulate in (
            ("final", FINAL_PILLS,
             lambda s, c: exits.simulate_with_exit(s, c, exits.TrailStep(1.0))),
            ("sanity", SANITY_PILLS,
             lambda s, c: engine.simulate(s, c)),
        ):
            setups = ablation.select_setups(ctx, pills)
            trades = simulate(setups, ctx["candles"])
            trades["asset"] = symbol
            feats = feats_all.reindex(pd.DatetimeIndex(trades["signal_time"]))
            fp, tp = _pool_paths(out_dir, pool, interval, symbol)
            feats.to_parquet(fp)
            trades.to_parquet(tp)
            pools[pool].append((feats, trades))
            print(f"{symbol} {interval} {pool}: {len(trades)} trades", flush=True)
        del ctx, feats_all
        gc.collect()
    return pools


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage", choices=["candidates", "confirm"], required=True)
    p.add_argument("--start", default="2017-08-01")
    p.add_argument("--end", default="2025-01-01")
    p.add_argument("--train-end", default="2023-01-01")
    p.add_argument("--intervals", default="5m,15m,1h")
    p.add_argument("--out-dir", default="results/ml")
    p.add_argument("--rules", help="confirm stage: json list of "
                   "{interval, pool, feature, direction, threshold}")
    args = p.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    train_end = pd.Timestamp(args.train_end, tz="UTC")
    intervals = args.intervals.split(",")

    if args.stage == "candidates":
        for interval in intervals:
            pools = build_pools(interval, args.start, args.end, out_dir)
            result = {}
            for pool, pairs in pools.items():
                study = run_study(pairs, train_end)
                cands = candidate_rules(study)
                result[pool] = {
                    "n_train": study["n_train"], "n_total": study["n_total"],
                    "n_dropped_nan": study["n_dropped_nan"],
                    "importances": study["importances"].round(4).to_dict(),
                    "candidates": cands.to_dict(orient="records"),
                    "rediscovery": rediscovery_check(study["importances"]),
                }
                print(f"\n== {interval} {pool}: n_train={study['n_train']} "
                      f"rediscovery={result[pool]['rediscovery']}", flush=True)
                print(study["importances"].head(12).to_string(), flush=True)
                print(cands.to_string(index=False), flush=True)
                del study
                gc.collect()
            (out_dir / f"candidates_{interval}.json").write_text(
                json.dumps(result, indent=2, default=str), encoding="utf-8")
            del pools
            gc.collect()
        print("\ncandidates stage complete — veto pass happens in the doc; "
              "then run --stage confirm", flush=True)
        return

    if not args.rules:
        raise SystemExit("--stage confirm requires --rules <json>")
    chosen = json.loads(Path(args.rules).read_text(encoding="utf-8"))
    for interval in intervals:
        subset = [r for r in chosen if r["interval"] == interval]
        if not subset:
            continue
        pools = build_pools(interval, args.start, args.end, out_dir)
        out = {}
        for pool in {r["pool"] for r in subset}:
            rules = pd.DataFrame([r for r in subset if r["pool"] == pool])
            confirmed = confirm_rules(rules, pools[pool], train_end)
            out[pool] = confirmed.to_dict(orient="records")
            print(f"\n== {interval} {pool} confirmation", flush=True)
            print(confirmed.to_string(index=False), flush=True)
        asym = side_asymmetry(pools["final"], train_end)
        out["side_asymmetry"] = asym.to_dict(orient="records")
        print(asym.to_string(index=False), flush=True)
        (out_dir / f"confirmed_{interval}.json").write_text(
            json.dumps(out, indent=2, default=str), encoding="utf-8")
        del pools
        gc.collect()


if __name__ == "__main__":
    main()
