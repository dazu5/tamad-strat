import pandas as pd
import pytest

from tamad import ablation, data, experiments
from tamad.experiments import RunConfig


@pytest.fixture
def synthetic(monkeypatch, tmp_path):
    monkeypatch.setattr(experiments, "STORE_DIR", tmp_path / "results")
    rows = [
        (100, 101, 99, 100.5), (100.5, 101, 99.5, 100),
        (100, 101, 95, 96), (96, 99, 94, 98.5),
        (98.5, 99, 96.5, 97), (97, 98, 96, 96.5),
        (96.5, 107, 96, 106.5), (106.5, 107.5, 105, 107),
    ]
    idx = pd.date_range("2022-01-01", periods=len(rows), freq="15min", tz="UTC")
    candles = pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=idx)
    candles["volume"] = 1.0
    monkeypatch.setattr(data, "candles", lambda *a, **k: candles)
    return candles


def test_context_and_evaluate_match_experiments_run(synthetic):
    ctx = ablation.combo_context("BTCUSDT", "15m", "2022-01-01", "2022-06-30")
    for cfg in (
        dict(sweep_required=False, c1_min_atr=None, zones=(), session=None, bias_tf=None),
        dict(sweep_required=True, c1_min_atr=None, zones=(), session=None, bias_tf=None),
        dict(sweep_required=False, c1_min_atr=None, zones=(), session="asia_00_08", bias_tf=None),
    ):
        harness_trades = ablation.evaluate(ctx, cfg)
        record = experiments.run(RunConfig(
            symbol="BTCUSDT", interval="15m", start="2022-01-01", end="2022-06-30",
            sweep_required=cfg["sweep_required"], c1_min_atr=cfg["c1_min_atr"],
            zones=cfg["zones"], session=cfg["session"], bias_tf=cfg["bias_tf"]))
        assert len(harness_trades) == record["metrics"]["trade_count"]


def test_grid_enumerates_full_cartesian(synthetic):
    ctx = ablation.combo_context("BTCUSDT", "15m", "2022-01-01", "2022-06-30")
    table = ablation.run_grid([ctx])
    expected = 2 * 2 * 7 * 4 * 3
    assert len(table) == expected
    assert table.iloc[0]["profit_factor"] >= table.iloc[-1]["profit_factor"]
    assert "combos_pf_above_1" in table.columns


def test_session_pill_filters_by_utc_hour(synthetic):
    record_all = experiments.run(RunConfig(
        symbol="BTCUSDT", interval="15m", start="2022-01-01", end="2022-06-30"))
    record_us = experiments.run(RunConfig(
        symbol="BTCUSDT", interval="15m", start="2022-01-01", end="2022-06-30",
        session="us_16_24"))
    # the fixture's single setup signals at 01:00 UTC -> asia only
    assert record_all["metrics"]["trade_count"] == 1
    assert record_us["metrics"]["trade_count"] == 0
