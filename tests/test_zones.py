import pandas as pd
import pytest

from tamad import zones
from tamad.zones import ZoneConfig
from tests.conftest import make_candles


def v_shape(depth_bar=5, n=12, base=100.0):
    """Candles carving a clear swing low at `depth_bar`."""
    rows = []
    for i in range(n):
        dist = abs(i - depth_bar)
        low = base - 5 + dist            # v-shaped lows, minimum at depth_bar
        rows.append((low + 1.5, low + 2.0, low, low + 1.0))
    return make_candles(rows)


CFG = ZoneConfig(swing_left=3, swing_right=2, atr_period=3)


def test_swing_low_zone_born_only_after_right_confirmation():
    candles = v_shape()
    zs = zones.swing_zones(candles, CFG)
    lows = zs[zs["kind"] == "swing_low"]
    assert len(lows) == 1
    z = lows.iloc[0]
    # pivot bar is index 5; confirmation needs swing_right=2 more bars
    assert z["born"] == candles.index[7]
    assert z["lower"] <= 95.0 <= z["upper"]     # contains the pivot low


def test_swing_high_mirror():
    candles = v_shape()
    inverted = candles.copy()
    inverted["high"] = 200 - candles["low"]
    inverted["low"] = 200 - candles["high"]
    inverted["open"] = 200 - candles["open"]
    inverted["close"] = 200 - candles["close"]
    zs = zones.swing_zones(inverted, CFG)
    assert (zs["kind"] == "swing_high").sum() == 1


def test_swing_zone_expires_after_max_age():
    candles = v_shape(n=12)
    cfg = ZoneConfig(swing_left=3, swing_right=2, swing_max_age=3, atr_period=3)
    z = zones.swing_zones(candles, cfg).iloc[0]
    assert z["died"] == candles.index[10]        # born at 7 + 3 bars


def test_sr_zone_needs_min_touches():
    # three v-shapes bottoming near the same price -> 3 clustered pivots
    parts = [v_shape(depth_bar=5, n=11), v_shape(depth_bar=5, n=11),
             v_shape(depth_bar=5, n=11)]
    candles = pd.concat(parts)
    candles.index = pd.date_range("2022-01-01", periods=len(candles),
                                  freq="15min", tz="UTC")
    cfg = ZoneConfig(swing_left=3, swing_right=2, sr_min_touches=3,
                     atr_period=3, swing_max_age=1000)
    sr = zones.sr_zones(candles, cfg)
    assert len(sr) == 1
    z = sr.iloc[0]
    assert z["kind"] == "sr"
    assert z["lower"] <= 95.0 <= z["upper"]
    # born at the third touch's confirmation, i.e. in the third segment
    assert z["born"] >= candles.index[22 + 5]


def test_sr_scattered_pivots_form_no_zone():
    a = v_shape(depth_bar=5, n=11)
    b = v_shape(depth_bar=5, n=11, base=150.0)   # far away in price
    candles = pd.concat([a, b])
    candles.index = pd.date_range("2022-01-01", periods=len(candles),
                                  freq="15min", tz="UTC")
    cfg = ZoneConfig(swing_left=3, swing_right=2, sr_min_touches=3, atr_period=3)
    assert zones.sr_zones(candles, cfg).empty


def test_active_at_respects_lifetime():
    candles = v_shape()
    zs = zones.swing_zones(candles, CFG)
    born = zs.iloc[0]["born"]
    assert zones.active_at(zs, born - pd.Timedelta("15min")).empty
    assert len(zones.active_at(zs, born)) == 1


def test_confluence_matches_price_inside_zone_with_tolerance():
    zs = pd.DataFrame([{"kind": "swing_low", "lower": 94.0, "upper": 96.0,
                        "born": pd.Timestamp("2022-01-01", tz="UTC"),
                        "died": pd.Timestamp("2022-02-01", tz="UTC")}])
    t = pd.Timestamp("2022-01-05", tz="UTC")
    assert list(zones.confluence(zs, t, price=95.0, pad=0.0)["kind"]) == ["swing_low"]
    assert zones.confluence(zs, t, price=97.0, pad=0.0).empty
    assert len(zones.confluence(zs, t, price=96.5, pad=1.0)) == 1
