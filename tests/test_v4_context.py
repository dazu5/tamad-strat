"""V4 context (#21): equilibrium zones and the continuation pill."""

import pandas as pd
import pytest

from tamad import zones
from tamad.experiments import RunConfig, _context_mask
from tests.conftest import make_candles


def swing_candles():
    """Down to a clear pivot low (bar 10), up to a clear pivot high (bar 20),
    then drift: exactly one low and one high pivot at defaults (left=6, right=2)."""
    rows = []
    price = 110.0
    for i in range(31):
        if i <= 10:
            price = 110.0 - i          # bar 10 low = 100
        elif i <= 20:
            price = 100.0 + 2 * (i - 10)   # bar 20 high = 120
        else:
            price = 119.0 - 0.1 * (i - 21)
        rows.append((price + 0.1, price + 0.4, price - 0.4, price - 0.1))
    return make_candles(rows)


def test_eq_zone_geometry_and_birth():
    candles = swing_candles()
    z = zones.eq_zones(candles)
    assert len(z) == 1
    zone = z.iloc[0]
    assert zone["kind"] == "eq"
    low_extreme = float(candles["low"].iloc[10])     # 99.6
    high_extreme = float(candles["high"].iloc[20])   # 120.4
    mid = (low_extreme + high_extreme) / 2
    assert (zone["lower"] + zone["upper"]) / 2 == pytest.approx(mid)
    assert zone["born"] == candles.index[22]         # later pivot + right(2)
    assert zone["died"] > zone["born"]


def test_eq_zone_birth_has_no_lookahead():
    candles = swing_candles()
    before = zones.eq_zones(candles)
    mutated = candles.copy()
    mutated.iloc[25:, :4] = mutated.iloc[25:, :4] + 50.0   # after born (bar 22)
    after = zones.eq_zones(mutated)
    pd.testing.assert_series_equal(before.iloc[0][["kind", "lower", "upper", "born"]],
                                   after.iloc[0][["kind", "lower", "upper", "born"]])


def test_eq_registered_in_detectors():
    assert "eq" in zones.DETECTORS
    z = zones.detect(swing_candles(), ("eq",))
    assert set(z["kind"]) == {"eq"}


def trend_pullback_candles(pullback=True, n_up=40, n_down=21):
    rows = []
    price = 100.0
    for _ in range(n_up):
        price += 2.0
        rows.append((price - 1.6, price + 0.4, price - 2.0, price))
    for _ in range(n_down):
        price += 0.5 if not pullback else -0.5
        step = (0.9, 0.4) if not pullback else (-0.1, -0.9)
        rows.append((price - step[0], price + 0.4, price + step[1] - 1.0, price))
    return make_candles(rows)


def one_setup(candles, bar, side):
    entry = float(candles["close"].iloc[bar])
    return pd.DataFrame(
        {"side": [side], "entry": [entry], "sl": [entry - 3.0 * side],
         "tp": [entry + 9.0 * side], "risk": [3.0], "sweep": [False],
         "c1_atr_mult": [1.0], "full_wick": [True]},
        index=pd.DatetimeIndex([candles.index[bar]], name="time"))


def test_continuation_keeps_with_trend_pullback_long():
    candles = trend_pullback_candles(pullback=True)
    setups = one_setup(candles, len(candles) - 1, side=1)
    mask = _context_mask(setups, candles, "continuation")
    assert mask.iloc[0]


def test_continuation_drops_counter_trend_short_at_same_bar():
    candles = trend_pullback_candles(pullback=True)
    setups = one_setup(candles, len(candles) - 1, side=-1)
    assert not _context_mask(setups, candles, "continuation").iloc[0]


def test_continuation_drops_long_without_pullback():
    candles = trend_pullback_candles(pullback=False)
    setups = one_setup(candles, len(candles) - 1, side=1)
    assert not _context_mask(setups, candles, "continuation").iloc[0]


def test_unknown_context_raises():
    candles = trend_pullback_candles()
    setups = one_setup(candles, len(candles) - 1, side=1)
    with pytest.raises(ValueError):
        _context_mask(setups, candles, "moon_phase")


def test_new_fields_keep_existing_hashes_stable():
    base = dict(symbol="BTCUSDT", interval="15m", start="2020-01-01", end="2021-01-01")
    default_form = RunConfig(**base)
    explicit_defaults = RunConfig(**base, context=None, full_wick_required=False)
    assert default_form.config_hash() == explicit_defaults.config_hash()
    assert RunConfig(**base, context="continuation").config_hash() != default_form.config_hash()
    assert RunConfig(**base, full_wick_required=True).config_hash() != default_form.config_hash()
