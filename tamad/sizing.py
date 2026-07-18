"""Position sizing strategies and portfolio combination (#17).

Sizers turn a chronological trade list (r_multiple per trade) into a
dollar equity curve:

- FixedPct(pct): stake = pct x current equity (volatility drag applies).
- HighWatermark(pct): stake = pct x peak equity ever reached — a loss
  does not shrink the next stake, countering the drag.

`dd_parity_pct` searches the risk percentage at which a trade list's
standalone max drawdown hits a target (drawdown-parity sizing across
assets). `portfolio_curve` merges per-asset trade lists chronologically
onto one shared equity curve and attributes dollar PnL per asset.
Overlapping trades across assets share equity sequentially by exit time —
the standard flat approximation, matching the methodology's usage.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class FixedPct:
    pct: float

    def stake(self, equity: float, peak: float) -> float:
        return self.pct * equity


@dataclass(frozen=True)
class HighWatermark:
    pct: float

    def stake(self, equity: float, peak: float) -> float:
        return self.pct * peak


def equity_curve(trades: pd.DataFrame, sizer, start_equity: float = 10_000.0) -> pd.Series:
    ordered = trades.sort_values("exit_time")
    equity = start_equity
    peak = start_equity
    values = []
    for r in ordered["r_multiple"]:
        equity += float(r) * sizer.stake(equity, peak)
        peak = max(peak, equity)
        values.append(equity)
    return pd.Series(values, index=pd.to_datetime(ordered["exit_time"], utc=True))


def max_drawdown_pct(curve: pd.Series) -> float:
    if curve.empty:
        return 0.0
    peaks = curve.cummax()
    return float(((peaks - curve) / peaks).max())


def dd_parity_pct(trades: pd.DataFrame, target_dd: float, sizer=FixedPct,
                  lo: float = 0.0001, hi: float = 0.10, tol: float = 1e-4) -> float:
    """Bisect the risk percentage whose standalone max drawdown hits target."""
    for _ in range(50):
        mid = (lo + hi) / 2
        dd = max_drawdown_pct(equity_curve(trades, sizer(mid)))
        if abs(dd - target_dd) < tol:
            return mid
        if dd > target_dd:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def portfolio_curve(per_asset: dict, start_equity: float = 10_000.0):
    """Merge per-asset (trades, sizer) chronologically onto one equity curve.

    Returns (curve, contribution) where contribution maps asset -> dollar
    PnL earned by that asset's trades.
    """
    rows = []
    for asset, (trades, sizer) in per_asset.items():
        t = trades.sort_values("exit_time")
        for _, row in t.iterrows():
            rows.append((pd.Timestamp(row["exit_time"]), asset,
                         float(row["r_multiple"]), sizer))
    rows.sort(key=lambda x: x[0])

    equity = start_equity
    peak = start_equity
    contribution = {asset: 0.0 for asset in per_asset}
    values, index = [], []
    for when, asset, r, sizer in rows:
        pnl = r * sizer.stake(equity, peak)
        equity += pnl
        peak = max(peak, equity)
        contribution[asset] += pnl
        values.append(equity)
        index.append(when)
    return pd.Series(values, index=pd.DatetimeIndex(index)), contribution
