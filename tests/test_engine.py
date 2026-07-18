import pandas as pd

from tamad.engine import simulate
from tests.conftest import make_candles


def make_setup(candles, bar, side=1, sl=98.0, rr=3.0):
    """One-row setups frame in the detector's schema, signal at `bar`."""
    entry = candles["close"].iloc[bar]
    risk = (entry - sl) * side
    return pd.DataFrame(
        {
            "side": [side],
            "entry": [entry],
            "sl": [sl],
            "tp": [entry + side * rr * risk],
            "risk": [risk],
            "sweep": [True],
            "c1_atr_mult": [1.0],
        },
        index=pd.DatetimeIndex([candles.index[bar]], name="time"),
    )


def test_fill_at_next_bar_open_and_levels_recomputed_from_fill():
    candles = make_candles([
        (100, 101, 99, 100.5),   # signal bar (setup crafted here)
        (101, 102, 100, 101.5),  # fill bar: entry at open = 101
        (101.5, 102, 100.5, 101),
    ])
    setups = make_setup(candles, 0, sl=98.0)
    trades = simulate(setups, candles)
    assert len(trades) == 1
    t = trades.iloc[0]
    assert t["entry_time"] == candles.index[1]
    assert t["fill"] == 101.0
    assert t["sl"] == 98.0
    assert t["tp"] == 101.0 + 3 * (101.0 - 98.0)   # fill + 3 x fill-risk
    assert t["exit_reason"] == "end_of_data"


def test_sl_first_when_one_bar_touches_both_levels():
    candles = make_candles([
        (100, 101, 99, 100.5),
        (100, 101, 99.5, 100.5),   # fill at 100, sl 98 -> tp 106
        (100.5, 107, 97, 105),     # touches both -> conservative: SL
    ])
    trades = simulate(make_setup(candles, 0, sl=98.0), candles)
    t = trades.iloc[0]
    assert t["exit_reason"] == "sl"
    assert t["exit_price"] == 98.0
    assert t["r_multiple"] == -1.0
    assert t["pnl"] == -1.0


def test_tp_exit_pays_full_rr():
    candles = make_candles([
        (100, 101, 99, 100.5),
        (100, 101, 99.5, 100.5),   # fill 100, sl 98, tp 106
        (100.5, 106.5, 99, 106),   # tp touched, sl untouched
    ])
    trades = simulate(make_setup(candles, 0, sl=98.0), candles)
    t = trades.iloc[0]
    assert t["exit_reason"] == "tp"
    assert t["exit_price"] == 106.0
    assert t["r_multiple"] == 3.0
    assert t["pnl"] == 3.0


def test_sl_exit_loses_one_r():
    candles = make_candles([
        (100, 101, 99, 100.5),
        (100, 101, 99.5, 100.5),
        (100.5, 101, 97.5, 98.5),  # sl 98 touched
    ])
    t = simulate(make_setup(candles, 0, sl=98.0), candles).iloc[0]
    assert t["exit_reason"] == "sl"
    assert t["r_multiple"] == -1.0


def test_bearish_trade_mirrors():
    candles = make_candles([
        (100, 101, 99, 100.5),
        (100, 100.5, 99, 99.5),    # fill 100 short, sl 102 -> tp 94
        (99.5, 100, 93.5, 94),     # tp touched
    ])
    t = simulate(make_setup(candles, 0, side=-1, sl=102.0), candles).iloc[0]
    assert t["exit_reason"] == "tp"
    assert t["tp"] == 100.0 - 3 * (102.0 - 100.0)
    assert t["r_multiple"] == 3.0


def test_setups_while_trade_open_are_skipped():
    candles = make_candles([
        (100, 101, 99, 100.5),     # setup A signal
        (100, 101, 99.5, 100.5),   # A fills at 100 (sl 90: stays open a while)
        (100.5, 101, 99.5, 100),   # setup B signal (should be skipped)
        (100, 101, 99.5, 100.5),
        (100.5, 101, 89, 89.5),    # A exits at sl 90
        (89.5, 90, 88, 89),
    ])
    setups = pd.concat([
        make_setup(candles, 0, sl=90.0),
        make_setup(candles, 2, sl=95.0),
    ])
    trades = simulate(setups, candles)
    assert len(trades) == 1
    assert trades.iloc[0]["exit_reason"] == "sl"


def test_signal_on_last_bar_produces_no_trade():
    candles = make_candles([
        (100, 101, 99, 100.5),
        (100, 101, 99.5, 100.5),
    ])
    trades = simulate(make_setup(candles, 1, sl=98.0), candles)
    assert trades.empty


def test_gap_through_stop_at_fill_is_skipped():
    candles = make_candles([
        (100, 101, 99, 100.5),
        (97, 98, 96, 97.5),        # opens below sl 98 -> unsizeable, skip
        (97.5, 98, 96, 97),
    ])
    trades = simulate(make_setup(candles, 0, sl=98.0), candles)
    assert trades.empty
