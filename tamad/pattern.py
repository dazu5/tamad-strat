"""Tamad pattern detector: candles in, setup events out. Pure, no I/O.

Bullish: C1 red, C2 green, C3 red with the hold rule C3.close >= C2.open
(wick below allowed). Bearish is the mirror. The setup's entry is the C3
close (signal frame; the engine fills at the next bar's open), SL is the
extreme price the three candles tapped (wicks included), TP is a fixed
multiple of risk (taught: 1:3).

Dojis (close == open) are neither red nor green, so a doji anywhere in the
triplet invalidates the pattern. Setups whose risk is zero (entry equals
the pattern extreme) are dropped: they cannot be sized.

The detector also reports the ideal-sweep flag (C2 took C1's extreme) and
C1 body size in ATR multiples; filtering on those is downstream config
(pattern pills, issue #7), not detection.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class PatternConfig:
    rr: float = 3.0
    atr_period: int = 14


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(period).mean()


def _empty_setups() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "side": pd.Series(dtype=int),
            "entry": pd.Series(dtype=float),
            "sl": pd.Series(dtype=float),
            "tp": pd.Series(dtype=float),
            "risk": pd.Series(dtype=float),
            "sweep": pd.Series(dtype=bool),
            "c1_atr_mult": pd.Series(dtype=float),
            "full_wick": pd.Series(dtype=bool),
        },
        index=pd.DatetimeIndex([], name="time", tz="UTC"),
    )


def detect(df: pd.DataFrame, config: PatternConfig = PatternConfig()) -> pd.DataFrame:
    """Return one row per setup, indexed by the signal (C3) bar's time.

    Columns: side (+1 long / -1 short), entry, sl, tp, risk,
    sweep (bool), c1_atr_mult (C1 body / ATR; NaN while ATR warms up).
    """
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    red = c < o
    green = c > o

    c1_o, c1_h, c1_l, c1_c = o.shift(2), h.shift(2), l.shift(2), c.shift(2)
    c2_o, c2_h, c2_l = o.shift(1), h.shift(1), l.shift(1)

    bull = red.shift(2, fill_value=False) & green.shift(1, fill_value=False) & red & (c >= c2_o)
    bear = green.shift(2, fill_value=False) & red.shift(1, fill_value=False) & green & (c <= c2_o)

    pattern_low = pd.concat([c1_l, c2_l, l], axis=1).min(axis=1)
    pattern_high = pd.concat([c1_h, c2_h, h], axis=1).max(axis=1)
    atr_series = atr(df, config.atr_period)

    # official-doc validity rule (#20): every candle in the triplet must
    # carry BOTH wicks; flag only — filtering is downstream config
    body_top = pd.concat([o, c], axis=1).max(axis=1)
    body_bot = pd.concat([o, c], axis=1).min(axis=1)
    both_wicks = (h > body_top) & (l < body_bot)
    triplet_wicked = (both_wicks
                      & both_wicks.shift(1, fill_value=False)
                      & both_wicks.shift(2, fill_value=False))

    frames = []
    for mask, side in ((bull, 1), (bear, -1)):
        sel = df.index[mask]
        if sel.empty:
            continue
        entry = c[sel]
        sl = (pattern_low if side == 1 else pattern_high)[sel]
        risk = (entry - sl) * side
        setups = pd.DataFrame(
            {
                "side": side,
                "entry": entry,
                "sl": sl,
                "tp": entry + side * config.rr * risk,
                "risk": risk,
                "sweep": (c2_l[sel] < c1_l[sel]) if side == 1 else (c2_h[sel] > c1_h[sel]),
                "c1_atr_mult": (c1_c[sel] - c1_o[sel]).abs() / atr_series[sel],
                "full_wick": triplet_wicked[sel],
            }
        )
        frames.append(setups[setups["risk"] > 0])
    if not frames:
        return _empty_setups()
    out = pd.concat(frames).sort_index()
    out.index.name = "time"
    return out
