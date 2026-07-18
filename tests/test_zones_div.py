import pandas as pd

from tamad import zones
from tamad.zones import ZoneConfig
from tests.conftest import make_candles


def div_fixture():
    """Decline to a low, bounce, then a spring: a wick undercuts the first
    low while closes hold firm — price lower low, RSI higher low."""
    rows = []
    price = 100.0
    for _ in range(4):                 # lead-in gains so RSI has memory
        rows.append((price, price + 0.6, price - 0.1, price + 0.5))
        price += 0.5
    for _ in range(6):                 # decline to pivot1 (low 94.6)
        rows.append((price, price + 0.2, price - 1.4, price - 1.2))
        price -= 1.2
    for _ in range(5):                 # bounce
        rows.append((price, price + 1.1, price - 0.1, price + 1.0))
        price += 1.0
    for wick in (1.5, 2.0, 4.5):       # spring: deep wicks, mild closes
        rows.append((price, price + 0.2, price - wick, price - 0.4))
        price -= 0.4                   # final wick 94.5 < 94.6, closes firm
    for _ in range(4):                 # recovery confirms the second pivot
        rows.append((price, price + 1.1, price - 0.1, price + 1.0))
        price += 1.0
    return make_candles(rows)


CFG = ZoneConfig(swing_left=4, swing_right=2, div_lookback=25, atr_period=5)


def test_regular_bullish_divergence_detected():
    candles = div_fixture()
    zs = zones.div_zones(candles, CFG)
    bull = zs[zs["kind"] == "div_bull"]
    assert len(bull) == 1
    z = bull.iloc[0]
    second_low = candles["low"].min()       # the spring wick (94.5)
    assert z["lower"] <= second_low <= z["upper"] + 1.0
    # born only after the second pivot confirms (swing_right bars later)
    assert z["born"] > candles["low"].idxmin()


def test_no_divergence_when_momentum_confirms():
    # second decline violent in CLOSE terms: RSI makes a lower low too
    rows = []
    price = 100.0
    for _ in range(4):
        rows.append((price, price + 0.6, price - 0.1, price + 0.5))
        price += 0.5
    for _ in range(6):
        rows.append((price, price + 0.2, price - 1.4, price - 1.2))
        price -= 1.2
    for _ in range(5):
        rows.append((price, price + 1.1, price - 0.1, price + 1.0))
        price += 1.0
    for _ in range(4):                 # violent plunge to a lower low
        rows.append((price, price + 0.2, price - 2.7, price - 2.5))
        price -= 2.5
    for _ in range(4):
        rows.append((price, price + 1.1, price - 0.1, price + 1.0))
        price += 1.0
    candles = make_candles(rows)
    zs = zones.div_zones(candles, CFG)
    assert zs[zs["kind"] == "div_bull"].empty


def test_rsi_bounded_and_reacts_to_direction():
    candles = div_fixture()
    r = zones.rsi(candles["close"], 5)
    valid = r.dropna()
    assert ((valid >= 0) & (valid <= 100)).all()
    assert r.iloc[9] < 45            # end of the decline: depressed
    assert r.iloc[13] > r.iloc[9]    # bounce lifts RSI
