import pandas as pd

from tamad import zones
from tamad.zones import ZoneConfig
from tests.conftest import make_candles

CFG = ZoneConfig(atr_period=3, fvg_min_atr=0.0, ob_displacement_atr=1.5)


def test_bullish_fvg_zone_between_c1_high_and_c3_low():
    candles = make_candles([
        (100, 101, 99, 100.5),
        (100.5, 101, 99.5, 100.2),
        (100.2, 100.8, 99.8, 100.4),
        (100.4, 103, 100.3, 102.8),   # strong bar creates the gap
        (102.8, 104, 102.2, 103.5),   # low 102.2 > high of bar1 (100.8): FVG
        (103.5, 104, 103, 103.8),
    ])
    zs = zones.fvg_zones(candles, CFG)
    bull = zs[zs["kind"] == "fvg_bull"]
    assert len(bull) == 1
    z = bull.iloc[0]
    assert z["lower"] == 100.8       # middle-bar predecessor high
    assert z["upper"] == 102.2       # successor low
    assert z["born"] == candles.index[4]


def test_fvg_min_size_filters_small_gaps():
    candles = make_candles([
        (100, 101, 99, 100.5),
        (100.5, 101, 99.5, 100.2),
        (100.2, 100.8, 99.8, 100.4),
        (100.4, 103, 100.3, 102.8),
        (102.8, 104, 102.2, 103.5),
        (103.5, 104, 103, 103.8),
    ])
    big_min = ZoneConfig(atr_period=3, fvg_min_atr=10.0)
    assert zones.fvg_zones(candles, big_min).empty


def test_fvg_dies_when_fully_filled():
    candles = make_candles([
        (100, 101, 99, 100.5),
        (100.5, 101, 99.5, 100.2),
        (100.2, 100.8, 99.8, 100.4),
        (100.4, 103, 100.3, 102.8),
        (102.8, 104, 102.2, 103.5),   # gap [100.8, 102.2] born here
        (103.5, 104, 103, 103.2),
        (103.2, 103.5, 100.5, 100.9), # low 100.5 <= 100.8: gap fully filled
        (100.9, 101.5, 100.6, 101.2),
    ])
    z = zones.fvg_zones(candles, CFG).iloc[0]
    assert z["died"] == candles.index[6]


def test_bearish_fvg_mirror():
    candles = make_candles([
        (100, 101, 99, 100.5),
        (100.5, 101, 99.5, 100.2),
        (100.2, 100.8, 99.6, 100.0),
        (100.0, 100.1, 97.5, 97.8),
        (97.8, 98.4, 97.0, 97.5),     # high 98.4 < low of bar2 (99.6): bear FVG
        (97.5, 98, 97, 97.4),
    ])
    bear = zones.fvg_zones(candles, CFG)
    bear = bear[bear["kind"] == "fvg_bear"]
    assert len(bear) == 1
    assert bear.iloc[0]["lower"] == 98.4
    assert bear.iloc[0]["upper"] == 99.6


def test_bullish_order_block_is_last_red_before_displacement():
    candles = make_candles([
        (100, 101, 99, 100.5),
        (100.5, 101, 99.8, 100.1),    # red candle  <- the OB
        (100.1, 105, 100, 104.8),     # green displacement (body 4.7 >> ATR)
        (104.8, 105.5, 104, 105),
        (105, 106, 104.5, 105.5),
    ])
    obs = zones.ob_zones(candles, CFG)
    bull = obs[obs["kind"] == "ob_bull"]
    assert len(bull) == 1
    z = bull.iloc[0]
    assert z["lower"] == 99.8        # OB candle low
    assert z["upper"] == 100.5       # OB candle body top (its open)
    assert z["born"] == candles.index[2]   # known at the displacement bar


def test_no_order_block_without_displacement():
    candles = make_candles([
        (100, 101, 99, 100.5),
        (100.5, 101, 99.8, 100.1),
        (100.1, 100.6, 100, 100.4),   # mild green, no displacement
        (100.4, 100.8, 100.2, 100.6),
        (100.6, 100.9, 100.4, 100.7),
    ])
    assert zones.ob_zones(candles, CFG).empty


def test_bearish_order_block_mirror():
    candles = make_candles([
        (100, 101, 99, 100.5),
        (100.4, 101.2, 100.2, 101.0),  # green candle <- the OB
        (101.0, 101.1, 96, 96.2),      # red displacement down
        (96.2, 97, 95.5, 96),
        (96, 96.5, 95, 95.5),
    ])
    obs = zones.ob_zones(candles, CFG)
    bear = obs[obs["kind"] == "ob_bear"]
    assert len(bear) == 1
    z = bear.iloc[0]
    assert z["lower"] == 100.4       # OB candle body bottom (its open)
    assert z["upper"] == 101.2       # OB candle high
