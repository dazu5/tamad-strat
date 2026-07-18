"""Event-driven simulator: setups + candles in, trade list out.

Fills happen at the next bar's open after the signal bar. Risk and TP are
recomputed from the actual fill price (the SL level itself never moves).
Intrabar ambiguity resolves conservatively: when one bar touches both SL
and TP, the trade exits at SL. One trade per asset at a time; setups that
fire while a trade is open are skipped. An open trade at the end of data
closes at the final bar's close with reason "end_of_data".

Costs are deliberately absent until issue #18; risk_per_trade defaults to
the flat $1 used for expectancy measurement.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

TRADE_COLUMNS = [
    "signal_time", "entry_time", "side", "fill", "sl", "tp",
    "exit_time", "exit_price", "exit_reason", "r_multiple", "pnl",
]

_CHUNK = 512  # bars scanned per step; most trades resolve inside one chunk


def _first_exit(highs, lows, start, side, sl, tp):
    """Index and reason of the first bar from `start` hitting SL or TP.

    Bar-order semantics match the reference loop: the exit bar is the
    first bar touching either level, and SL wins a same-bar tie.
    """
    n = len(highs)
    for lo in range(start, n, _CHUNK):
        hi = min(lo + _CHUNK, n)
        if side == 1:
            sl_hit = lows[lo:hi] <= sl
            tp_hit = highs[lo:hi] >= tp
        else:
            sl_hit = highs[lo:hi] >= sl
            tp_hit = lows[lo:hi] <= tp
        either = sl_hit | tp_hit
        if either.any():
            i = int(np.argmax(either))
            return lo + i, ("sl" if sl_hit[i] else "tp")
    return None, None


def simulate(
    setups: pd.DataFrame,
    candles: pd.DataFrame,
    rr: float = 3.0,
    risk_per_trade: float = 1.0,
) -> pd.DataFrame:
    """Run the taught baseline over one asset's candles."""
    trades = []
    open_until = None  # exit time of the currently open trade

    opens = candles["open"].to_numpy()
    highs = candles["high"].to_numpy()
    lows = candles["low"].to_numpy()
    positions = candles.index.get_indexer(setups.index)

    for (signal_time, s), pos in zip(setups.iterrows(), positions):
        if pos < 0 or pos + 1 >= len(candles):
            continue
        entry_time = candles.index[pos + 1]
        if open_until is not None and entry_time <= open_until:
            continue

        side = int(s["side"])
        fill = float(opens[pos + 1])
        sl = float(s["sl"])
        risk = (fill - sl) * side
        if risk <= 0:
            continue
        tp = fill + side * rr * risk

        exit_index, exit_reason = _first_exit(highs, lows, pos + 1, side, sl, tp)
        if exit_reason is not None:
            exit_time = candles.index[exit_index]
            exit_price = sl if exit_reason == "sl" else tp
        else:
            exit_time = candles.index[-1]
            exit_price = float(candles["close"].iloc[-1])
            exit_reason = "end_of_data"

        r_multiple = (exit_price - fill) * side / risk
        trades.append({
            "signal_time": signal_time,
            "entry_time": entry_time,
            "side": side,
            "fill": fill,
            "sl": sl,
            "tp": tp,
            "exit_time": exit_time,
            "exit_price": exit_price,
            "exit_reason": exit_reason,
            "r_multiple": r_multiple,
            "pnl": r_multiple * risk_per_trade,
        })
        open_until = exit_time

    return pd.DataFrame(trades, columns=TRADE_COLUMNS)
