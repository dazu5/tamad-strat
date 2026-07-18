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

import pandas as pd

TRADE_COLUMNS = [
    "signal_time", "entry_time", "side", "fill", "sl", "tp",
    "exit_time", "exit_price", "exit_reason", "r_multiple", "pnl",
]


def simulate(
    setups: pd.DataFrame,
    candles: pd.DataFrame,
    rr: float = 3.0,
    risk_per_trade: float = 1.0,
) -> pd.DataFrame:
    """Run the taught baseline over one asset's candles."""
    trades = []
    open_until = None  # exit time of the currently open trade

    positions = candles.index.get_indexer(setups.index)
    for (signal_time, s), pos in zip(setups.iterrows(), positions):
        if pos < 0 or pos + 1 >= len(candles):
            continue
        entry_time = candles.index[pos + 1]
        if open_until is not None and entry_time <= open_until:
            continue

        side = int(s["side"])
        fill = float(candles["open"].iloc[pos + 1])
        sl = float(s["sl"])
        risk = (fill - sl) * side
        if risk <= 0:
            continue
        tp = fill + side * rr * risk

        exit_time, exit_price, exit_reason = None, None, None
        for i in range(pos + 1, len(candles)):
            bar = candles.iloc[i]
            sl_hit = bar["low"] <= sl if side == 1 else bar["high"] >= sl
            tp_hit = bar["high"] >= tp if side == 1 else bar["low"] <= tp
            if sl_hit:  # conservative: SL wins when both touch
                exit_time, exit_price, exit_reason = candles.index[i], sl, "sl"
                break
            if tp_hit:
                exit_time, exit_price, exit_reason = candles.index[i], tp, "tp"
                break
        if exit_reason is None:
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
