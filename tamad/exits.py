"""Pluggable exit structures (#15).

`simulate_with_exit` mirrors the engine's fill and one-trade-at-a-time
semantics but delegates the exit decision to a strategy object:

- FixedRR(rr): the taught structure — hard TP at rr x risk (delegates to
  the fast engine path).
- TrailStep(step_r): no TP; the stop ratchets one step behind each full
  step_r x risk the price advances (Revelio's winning structure).
- AtrTrail(mult, period): stop trails the close's peak by mult x ATR,
  ratchet-only.

Intrabar conservatism everywhere: the CURRENT stop is checked against a
bar before any upgrade that bar would earn.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from tamad import engine
from tamad.pattern import atr


@dataclass(frozen=True)
class FixedRR:
    rr: float = 3.0
    name: str = "fixed_rr"


@dataclass(frozen=True)
class TrailStep:
    step_r: float = 1.0
    name: str = "trail_step"


@dataclass(frozen=True)
class AtrTrail:
    mult: float = 2.0
    period: int = 14
    name: str = "atr_trail"


def _trail_exit(candles, start, side, fill, risk, sl0, strategy, atr_arr):
    """Walk bars forward; return (exit_index, exit_price) or (None, None)."""
    highs = candles["high"].to_numpy()
    lows = candles["low"].to_numpy()
    closes = candles["close"].to_numpy()
    stop = sl0
    peak = fill
    for i in range(start, len(candles)):
        # 1) conservative: current stop first
        hit = lows[i] <= stop if side == 1 else highs[i] >= stop
        if hit:
            return i, stop
        # 2) then earn upgrades from this bar's extreme
        if isinstance(strategy, TrailStep):
            extreme = highs[i] if side == 1 else lows[i]
            levels = int(((extreme - fill) * side) / (strategy.step_r * risk))
            if levels >= 1:
                candidate = fill + side * (levels - 1) * strategy.step_r * risk
                if (candidate - stop) * side > 0:
                    stop = candidate
        else:  # AtrTrail
            ref = closes[i]
            peak = max(peak, ref) if side == 1 else min(peak, ref)
            candidate = peak - side * strategy.mult * atr_arr[i]
            if (candidate - stop) * side > 0:
                stop = candidate
    return None, None


def simulate_with_exit(
    setups: pd.DataFrame,
    candles: pd.DataFrame,
    strategy,
    risk_per_trade: float = 1.0,
) -> pd.DataFrame:
    if isinstance(strategy, FixedRR):
        return engine.simulate(setups, candles, rr=strategy.rr,
                               risk_per_trade=risk_per_trade)

    atr_arr = atr(candles, getattr(strategy, "period", 14)) \
        .bfill().fillna(0.0).to_numpy()
    opens = candles["open"].to_numpy()
    positions = candles.index.get_indexer(setups.index)

    trades = []
    open_until = None
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

        exit_index, exit_price = _trail_exit(
            candles, pos + 1, side, fill, risk, sl, strategy, atr_arr)
        if exit_index is None:
            exit_time = candles.index[-1]
            exit_price = float(candles["close"].iloc[-1])
            exit_reason = "end_of_data"
        else:
            exit_time = candles.index[exit_index]
            exit_reason = "trail"

        r_multiple = (exit_price - fill) * side / risk
        trades.append({
            "signal_time": signal_time, "entry_time": entry_time, "side": side,
            "fill": fill, "sl": sl, "tp": float("nan"),
            "exit_time": exit_time, "exit_price": exit_price,
            "exit_reason": exit_reason, "r_multiple": r_multiple,
            "pnl": r_multiple * risk_per_trade,
        })
        open_until = exit_time
    return pd.DataFrame(trades, columns=engine.TRADE_COLUMNS)
