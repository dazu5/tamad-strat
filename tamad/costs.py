"""Venue cost model (#18): fees + spread applied to R-accounted trades.

With flat $1 risk, a trade's notional is fill / risk_distance dollars,
so a round-trip cost of c% of notional subtracts c% x fill / risk_distance
from the trade's R. Tight stops relative to price magnify cost in R terms
— exactly the effect that kills low-timeframe edges.

Documented defaults (Binance spot, standard tier, no BNB discount):
taker fee 0.10% per side, plus 0.02% spread allowance on majors
= 0.22% of notional per round trip.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class CostModel:
    fee_pct_per_side: float = 0.001   # 0.10%
    spread_pct: float = 0.0002        # 0.02%

    @property
    def round_trip_pct(self) -> float:
        return 2 * self.fee_pct_per_side + self.spread_pct


BINANCE_SPOT = CostModel()
ZERO = CostModel(0.0, 0.0)


def apply(trades: pd.DataFrame, model: CostModel) -> pd.DataFrame:
    """Return trades with cost-adjusted r_multiple/pnl and a cost_r column."""
    out = trades.copy()
    if out.empty:
        out["cost_r"] = pd.Series(dtype=float)
        return out
    risk_distance = (out["fill"] - out["sl"]).abs()
    cost_r = model.round_trip_pct * out["fill"] / risk_distance
    out["cost_r"] = cost_r
    out["r_multiple"] = out["r_multiple"] - cost_r
    out["pnl"] = out["r_multiple"]   # pnl is per-$1-risk throughout the project
    return out
