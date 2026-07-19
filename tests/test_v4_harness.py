"""V4 harness (#22): grid enumeration, rr plumbing, equivalence to the runner."""

import pandas as pd
import pytest

from tamad import data, experiments, v4
from tamad.experiments import RunConfig


def _frame(rows, start="2022-01-01"):
    idx = pd.date_range(start, periods=len(rows), freq="15min", tz="UTC")
    df = pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=idx)
    df["volume"] = 1.0
    return df


@pytest.fixture
def synthetic(monkeypatch, tmp_path):
    monkeypatch.setattr(experiments, "STORE_DIR", tmp_path / "results")
    candles = _frame([
        (100, 101, 99, 100.5), (100.5, 101, 99.5, 100),
        (100, 101, 95, 96), (96, 99, 94, 98.5),
        (98.5, 99, 96.5, 97), (97, 98, 96, 96.5),
        (96.5, 107, 96, 106.5), (106.5, 107.5, 105, 107),
    ])
    monkeypatch.setattr(data, "candles", lambda *a, **k: candles)
    return candles


@pytest.fixture
def two_r_only(monkeypatch, tmp_path):
    """Path reaches 2R (103) but never 3R (106), then stops out at 94."""
    monkeypatch.setattr(experiments, "STORE_DIR", tmp_path / "results")
    candles = _frame([
        (100, 101, 99, 100.5), (100.5, 101, 99.5, 100),
        (100, 101, 95, 96), (96, 99, 94, 98.5),
        (98.5, 99, 96.5, 97), (97, 98, 96, 96.5),
        (96.5, 104, 96, 103.5), (103.5, 104, 93.5, 94),
    ])
    monkeypatch.setattr(data, "candles", lambda *a, **k: candles)
    return candles


BASE = dict(rr=3.0, full_wick_required=False, c1_min_atr=None,
            zones=(), session=None, context=None)


def test_harness_matches_experiments_run(synthetic):
    ctx = v4.combo_context_v4("BTCUSDT", "15m", "2022-01-01", "2022-06-30")
    for override in (
        dict(rr=2.0),
        dict(full_wick_required=True),
        dict(context="continuation"),        # ret20 warmup -> zero trades
        dict(session="us_16_24"),            # fixture signals at 01:00 UTC
        dict(zones=("eq",)),
    ):
        cfg = {**BASE, **override}
        harness = v4.evaluate_v4(ctx, cfg)
        record = experiments.run(RunConfig(
            symbol="BTCUSDT", interval="15m",
            start="2022-01-01", end="2022-06-30",
            rr=cfg["rr"], full_wick_required=cfg["full_wick_required"],
            c1_min_atr=cfg["c1_min_atr"], zones=cfg["zones"],
            session=cfg["session"], context=cfg["context"]))
        assert len(harness) == record["metrics"]["trade_count"], override


def test_rr_changes_the_outcome(two_r_only):
    ctx = v4.combo_context_v4("BTCUSDT", "15m", "2022-01-01", "2022-06-30")
    win_2r = v4.evaluate_v4(ctx, {**BASE, "rr": 2.0})
    loss_3r = v4.evaluate_v4(ctx, {**BASE, "rr": 3.0})
    assert win_2r["pnl"].sum() == pytest.approx(2.0)
    assert loss_3r["pnl"].sum() == pytest.approx(-1.0)


def test_grid_enumerates_192_sorted(synthetic):
    ctx = v4.combo_context_v4("BTCUSDT", "15m", "2022-01-01", "2022-06-30")
    table = v4.run_grid_v4([ctx])
    assert len(table) == 2 * 2 * 2 * 6 * 2 * 2
    assert "win_rate" in table.columns
    pf = table["profit_factor"]
    assert (pf.iloc[0] >= pf.iloc[-1]) or pf.iloc[0] == float("inf")
