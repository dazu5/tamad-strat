import pandas as pd
import pytest


def make_candles(rows, start="2020-01-01", freq="15min"):
    """Build a candle frame from (open, high, low, close) tuples."""
    idx = pd.date_range(start, periods=len(rows), freq=freq, tz="UTC")
    df = pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=idx)
    df["volume"] = 1.0
    df.index.name = "time"
    return df


@pytest.fixture
def bullish_triplet():
    """C1 red climax, C2 green reclaim that sweeps C1's low, C3 red hold.

    C1: o=100 h=101 l=95  c=96   (red, body 4)
    C2: o=96  h=99  l=94  c=98.5 (green, sweeps 94 < 95)
    C3: o=98.5 h=99 l=96.5 c=97  (red, close 97 >= C2 open 96 -> hold)
    Setup: entry=97, sl=min(95,94,96.5)=94, risk=3, tp=97+9=106.
    """
    return make_candles([
        (100, 101, 99, 100.5),   # filler green so pattern sits mid-series
        (100.5, 101, 99.5, 100), # filler red
        (100, 101, 95, 96),      # C1
        (96, 99, 94, 98.5),      # C2
        (98.5, 99, 96.5, 97),    # C3 -> signal bar
        (97, 98, 96, 96.5),      # next bar, red so no mirror triplet forms
    ])
