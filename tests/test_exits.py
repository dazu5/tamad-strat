import pandas as pd
import pytest

from tamad import exits
from tamad.engine import simulate
from tests.conftest import make_candles
from tests.test_engine import make_setup


def test_fixed_rr_matches_engine_baseline():
    candles = make_candles([
        (100, 101, 99, 100.5),
        (100, 101, 99.5, 100.5),
        (100.5, 106.5, 99, 106),
    ])
    setups = make_setup(candles, 0, sl=98.0)
    baseline = simulate(setups, candles, rr=3.0)
    via_exits = exits.simulate_with_exit(setups, candles, exits.FixedRR(3.0))
    assert baseline.iloc[0]["exit_reason"] == via_exits.iloc[0]["exit_reason"]
    assert baseline.iloc[0]["r_multiple"] == via_exits.iloc[0]["r_multiple"]


def test_trail_step_exits_one_level_below_peak():
    # fill 100, sl 98 (risk 2). +1R=102, +2R=104. Peak 104.5 -> stop at 102.
    candles = make_candles([
        (100, 101, 99, 100.5),
        (100, 101, 99.5, 100.5),      # fill bar
        (100.5, 102.5, 100, 102.2),   # reaches +1R -> stop to breakeven (100)
        (102.2, 104.5, 102.1, 104),   # reaches +2R -> stop to +1R (102)
        (104, 104.2, 101.5, 101.8),   # falls through 102 -> exit at 102
    ])
    trades = exits.simulate_with_exit(
        make_setup(candles, 0, sl=98.0), candles, exits.TrailStep(1.0))
    t = trades.iloc[0]
    assert t["exit_reason"] == "trail"
    assert t["exit_price"] == pytest.approx(102.0)
    assert t["r_multiple"] == pytest.approx(1.0)


def test_trail_step_initial_stop_is_pattern_stop():
    candles = make_candles([
        (100, 101, 99, 100.5),
        (100, 101, 99.5, 100.5),
        (100.5, 101, 97.5, 98),       # straight down through 98
    ])
    t = exits.simulate_with_exit(
        make_setup(candles, 0, sl=98.0), candles, exits.TrailStep(1.0)).iloc[0]
    assert t["exit_price"] == pytest.approx(98.0)
    assert t["r_multiple"] == pytest.approx(-1.0)


def test_trail_step_stop_checked_before_level_upgrade():
    # one bar spans both the current stop and a new level: conservative exit
    candles = make_candles([
        (100, 101, 99, 100.5),
        (100, 101, 99.5, 100.5),
        (100.5, 102.5, 100, 102.2),   # stop -> breakeven (100)
        (102.2, 104.5, 99.5, 100.2),  # touches 100 AND 104: stop first
    ])
    t = exits.simulate_with_exit(
        make_setup(candles, 0, sl=98.0), candles, exits.TrailStep(1.0)).iloc[0]
    assert t["exit_price"] == pytest.approx(100.0)
    assert t["r_multiple"] == pytest.approx(0.0)


def test_trail_step_short_mirror():
    # short fill 100, sl 102 (risk 2). -1R=98 -> stop 100; -2R=96 -> stop 98.
    candles = make_candles([
        (100, 101, 99, 100.5),
        (100, 100.5, 99, 99.5),
        (99.5, 100, 97.8, 98),        # reaches 98 -> stop to 100
        (98, 98.5, 95.8, 96),         # reaches 96 -> stop to 98
        (96, 98.5, 95.9, 98.2),       # rallies through 98 -> exit at 98
    ])
    t = exits.simulate_with_exit(
        make_setup(candles, 0, side=-1, sl=102.0), candles,
        exits.TrailStep(1.0)).iloc[0]
    assert t["exit_price"] == pytest.approx(98.0)
    assert t["r_multiple"] == pytest.approx(1.0)


def test_end_of_data_closes_open_trail_trade():
    candles = make_candles([
        (100, 101, 99, 100.5),
        (100, 101, 99.5, 100.5),
        (100.5, 101.5, 100, 101),
    ])
    t = exits.simulate_with_exit(
        make_setup(candles, 0, sl=98.0), candles, exits.TrailStep(1.0)).iloc[0]
    assert t["exit_reason"] == "end_of_data"


def test_atr_trail_ratchets_and_exits():
    candles = make_candles([
        (100, 101, 99, 100.5),
        (100, 101, 99.5, 100.5),
        (100.5, 104, 100.4, 103.8),
        (103.8, 106, 103.6, 105.8),
        (105.8, 106, 102.0, 102.2),   # deep pullback hits the trail
    ])
    trades = exits.simulate_with_exit(
        make_setup(candles, 0, sl=98.0), candles,
        exits.AtrTrail(mult=1.0, period=2))
    t = trades.iloc[0]
    assert t["exit_reason"] == "trail"
    assert t["r_multiple"] > 0        # exits in profit after the run-up
