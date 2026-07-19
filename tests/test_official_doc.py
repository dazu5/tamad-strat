"""Official-doc deltas (#20): the both-wick validity rule and the doc's claims."""

import pytest

from tamad import claims
from tamad.pattern import detect
from tests.conftest import make_candles


def all_wicked_triplet():
    """Bullish R-G-R at bars 2-4; every candle has both wicks; fillers
    colored so no other triplet completes anywhere."""
    return make_candles([
        (100.0, 101.5, 99.5, 101.0),   # green filler, both wicks
        (101.0, 102.0, 99.8, 100.2),   # red filler, both wicks
        (100.2, 100.8, 96.5, 97.0),    # C1 red climax, both wicks
        (97.0, 99.5, 96.2, 99.0),      # C2 green sweep, both wicks
        (99.0, 99.8, 97.5, 97.8),      # C3 red hold (97.8 >= 97), both wicks
        (97.8, 99.6, 97.6, 99.4),      # green filler, closes above C3 open
    ])


def test_full_wick_true_when_all_six_wicks_present():
    setups = detect(all_wicked_triplet())
    assert len(setups) == 1
    assert bool(setups.iloc[0]["full_wick"]) is True


def test_full_wick_false_on_marubozu_middle_candle():
    candles = all_wicked_triplet()
    candles.iloc[3] = [97.0, 99.0, 97.0, 99.0, 1.0]  # C2 opens at low, closes at high
    setups = detect(candles)
    assert len(setups) == 1                          # detection unchanged
    assert bool(setups.iloc[0]["full_wick"]) is False


def test_full_wick_false_on_flat_top_signal_candle():
    candles = all_wicked_triplet()
    candles.iloc[4] = [99.0, 99.0, 97.5, 97.8, 1.0]  # C3 has no upper wick
    setups = detect(candles)
    assert len(setups) == 1
    assert bool(setups.iloc[0]["full_wick"]) is False


def test_official_2rr_claim_math():
    r = claims.check_claim(0.52, 2.0, 300)
    assert r["breakeven_wr"] == pytest.approx(1 / 3)
    assert r["expectancy_r"] == pytest.approx(0.52 * 2 - 0.48)


def test_official_3rr_claim_math():
    r = claims.check_claim(0.46, 3.0, 300)
    assert r["breakeven_wr"] == pytest.approx(0.25)
    assert r["expectancy_r"] == pytest.approx(0.46 * 3 - 0.54)


def test_official_claims_registry():
    table = claims.official_claims()
    assert {(c["label"], c["wr"], c["rr"]) for c in table} == {
        ("group journal", 0.60, 3.0),
        ("official doc @2RR", 0.52, 2.0),
        ("official doc @3RR", 0.46, 3.0),
    }
    for c in table:
        assert c["expectancy_r"] == pytest.approx(c["wr"] * c["rr"] - (1 - c["wr"]))
