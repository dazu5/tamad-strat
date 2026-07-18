import pandas as pd
import pytest

from tamad import sizing


def trades_of(rs, start="2022-01-01", freq="1D", asset="BTCUSDT"):
    idx = pd.date_range(start, periods=len(rs), freq=freq, tz="UTC")
    return pd.DataFrame({"exit_time": idx, "r_multiple": rs, "asset": asset})


def test_fixed_pct_compounds_on_current_equity():
    trades = trades_of([3.0, -1.0])
    curve = sizing.equity_curve(trades, sizing.FixedPct(0.01), start_equity=10_000)
    assert curve.iloc[0] == pytest.approx(10_000 * 1.03)          # +3R at 1%
    assert curve.iloc[1] == pytest.approx(10_000 * 1.03 * 0.99)   # -1R of current


def test_high_watermark_risks_percent_of_peak():
    # the Revelio example: 10k at 2%; lose then win returns exactly to 10k
    trades = trades_of([-1.0, 1.0])
    curve = sizing.equity_curve(trades, sizing.HighWatermark(0.02),
                                start_equity=10_000)
    assert curve.iloc[0] == pytest.approx(9_800)
    assert curve.iloc[1] == pytest.approx(10_000)   # stake was 2% of the PEAK


def test_max_drawdown_pct_of_curve():
    trades = trades_of([3.0, -1.0, -1.0, -1.0, 3.0])
    curve = sizing.equity_curve(trades, sizing.FixedPct(0.10), start_equity=10_000)
    dd = sizing.max_drawdown_pct(curve)
    assert 0.20 < dd < 0.30          # three 10% losses off the peak, compounding


def test_dd_parity_pct_scales_toward_target():
    trades = trades_of([3.0, -1.0, -1.0, -1.0, -1.0, -1.0, 3.0])
    full = sizing.max_drawdown_pct(
        sizing.equity_curve(trades, sizing.FixedPct(0.02), 10_000))
    target = full / 2
    pct = sizing.dd_parity_pct(trades, target_dd=target, sizer=sizing.FixedPct)
    achieved = sizing.max_drawdown_pct(
        sizing.equity_curve(trades, sizing.FixedPct(pct), 10_000))
    assert achieved == pytest.approx(target, rel=0.15)
    assert pct < 0.02


def test_portfolio_merges_chronologically_and_attributes_pnl():
    a = trades_of([3.0, -1.0], asset="BTCUSDT")
    b = trades_of([2.0], start="2022-01-01 12:00", asset="ETHUSDT")
    curve, contrib = sizing.portfolio_curve(
        {"BTCUSDT": (a, sizing.FixedPct(0.01)), "ETHUSDT": (b, sizing.FixedPct(0.02))},
        start_equity=10_000)
    assert contrib["BTCUSDT"] + contrib["ETHUSDT"] == pytest.approx(
        curve.iloc[-1] - 10_000)
    assert contrib["ETHUSDT"] > 0
