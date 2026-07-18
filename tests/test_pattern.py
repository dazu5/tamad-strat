import pandas as pd

from tamad.pattern import detect
from tests.conftest import make_candles


def test_bullish_setup_detected_with_exact_levels(bullish_triplet):
    setups = detect(bullish_triplet)
    assert len(setups) == 1
    s = setups.iloc[0]
    assert s["side"] == 1
    assert s["entry"] == 97.0          # C3 close
    assert s["sl"] == 94.0             # pattern extreme incl. C2 sweep wick
    assert s["risk"] == 3.0
    assert s["tp"] == 106.0            # entry + 3 * risk
    assert setups.index[0] == bullish_triplet.index[4]  # signal = C3 bar


def test_hold_rule_violation_yields_no_setup(bullish_triplet):
    candles = bullish_triplet.copy()
    # C3 closes below C2 open (96) -> reclaim failed, no setup
    candles.iloc[4, candles.columns.get_loc("close")] = 95.5
    assert detect(candles).empty


def test_hold_rule_equality_is_valid(bullish_triplet):
    candles = bullish_triplet.copy()
    candles.iloc[4, candles.columns.get_loc("close")] = 96.0  # == C2 open
    assert len(detect(candles)) == 1


def test_doji_anywhere_in_triplet_invalidates(bullish_triplet):
    candles = bullish_triplet.copy()
    # make C3 a doji (close == open)
    candles.iloc[4, candles.columns.get_loc("close")] = 98.5
    assert detect(candles).empty


def test_sweep_flag_reflects_c2_taking_c1_low(bullish_triplet):
    setups = detect(bullish_triplet)
    assert bool(setups.iloc[0]["sweep"]) is True

    no_sweep = bullish_triplet.copy()
    no_sweep.iloc[3, no_sweep.columns.get_loc("low")] = 95.5  # C2 low above C1 low
    setups = detect(no_sweep)
    assert len(setups) == 1
    assert bool(setups.iloc[0]["sweep"]) is False
    assert setups.iloc[0]["sl"] == 95.0  # extreme is now C1's low


def test_bearish_mirror_detected():
    candles = make_candles([
        (100, 101, 99, 100.5),
        (100.5, 101.5, 100, 101),  # green filler: no red-green-red triplet upstream
        (100, 105, 99, 104),       # C1 green climax
        (104, 106, 101, 101.5),    # C2 red, sweeps C1 high (106 > 105)
        (101.5, 103.5, 101, 103),  # C3 green, close 103 <= C2 open 104 -> hold
        (103, 104.5, 102.5, 104),  # green filler: no mirror triplet downstream
    ])
    setups = detect(candles)
    assert len(setups) == 1
    s = setups.iloc[0]
    assert s["side"] == -1
    assert s["entry"] == 103.0
    assert s["sl"] == 106.0           # pattern extreme high
    assert s["risk"] == 3.0
    assert s["tp"] == 94.0            # entry - 3 * risk
    assert bool(s["sweep"]) is True


def test_zero_risk_setup_dropped():
    # C3 closes exactly at the pattern low -> risk 0, cannot be sized
    candles = make_candles([
        (100, 101, 99, 100.5),
        (100.5, 101, 99.5, 100),
        (100, 101, 96, 97),      # C1 red, low 96
        (97, 99, 96, 98.5),      # C2 green, low 96
        (98.5, 99, 96, 96.5),    # C3 red, close 96.5 >= 97? no -> adjust
    ])
    # craft precisely: C2 open 97, C3 close must be >= 97 AND equal pattern low
    # impossible for a red C3 (close < open <= high) unless lows sit at 97 too
    candles = make_candles([
        (100, 101, 99, 100.5),
        (100.5, 101, 99.5, 100),
        (100, 101, 97, 98),      # C1 red, low 97
        (97, 99, 97, 98.5),      # C2 green, open 97, low 97
        (98.5, 99, 97, 97),      # C3: close 97 == open? no, open 98.5 -> red, close 97 == pattern low
    ])
    setups = detect(candles)
    assert setups.empty
