"""Trade-list metrics. Profit factor is the quality metric; trade count is
quantity; return is a consequence (see METHODOLOGY.md)."""

from __future__ import annotations

import pandas as pd


def summarize(trades: pd.DataFrame) -> dict:
    r = trades["r_multiple"] if len(trades) else pd.Series(dtype=float)
    pnl = trades["pnl"] if len(trades) else pd.Series(dtype=float)
    wins = int((r > 0).sum())
    losses = int((r < 0).sum())
    gross_profit = float(pnl[pnl > 0].sum())
    gross_loss = float(-pnl[pnl < 0].sum())
    return {
        "trade_count": int(len(trades)),
        "wins": wins,
        "losses": losses,
        "win_rate": wins / len(trades) if len(trades) else 0.0,
        "net_r": float(r.sum()),
        "expectancy_r": float(r.mean()) if len(trades) else 0.0,
        "profit_factor": (gross_profit / gross_loss) if gross_loss > 0
                         else (float("inf") if gross_profit > 0 else 0.0),
    }


def equity_curve(trades: pd.DataFrame) -> pd.Series:
    """Cumulative net R over exit time (flat-risk equity in R units)."""
    ordered = trades.sort_values("exit_time")
    curve = ordered["r_multiple"].cumsum()
    curve.index = pd.to_datetime(ordered["exit_time"], utc=True)
    return curve


def max_drawdown_r(trades: pd.DataFrame) -> float:
    """Largest peak-to-trough decline of the flat-risk equity curve, in R."""
    curve = equity_curve(trades)
    if curve.empty:
        return 0.0
    return float((curve.cummax() - curve).max())


def summary_table(summary: dict, title: str = "") -> str:
    lines = [title] if title else []
    lines += [
        f"  trades:        {summary['trade_count']}",
        f"  wins/losses:   {summary['wins']}/{summary['losses']}",
        f"  win rate:      {summary['win_rate']:.1%}",
        f"  expectancy:    {summary['expectancy_r']:+.3f} R",
        f"  net:           {summary['net_r']:+.1f} R",
        f"  profit factor: {summary['profit_factor']:.3f}",
    ]
    return "\n".join(lines)
