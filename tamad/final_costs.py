"""Costs rerun for #18 (the AFK portion — the holdout stays locked).

Applies the documented Binance spot cost model (0.10%/side taker +
0.02% spread = 0.22% of notional per round trip) to the final
configuration's trades (survivor pills + trail_1R exit) per asset and
interval, over the full non-holdout span. Costs in R scale with
fill/risk-distance, so tight-stopped low-TF trades pay the most — this
is the report that decides which timeframe portfolio survives.

Usage:
    python -m tamad.final_costs --report docs/COSTS_RESULTS.md
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from tamad import costs, metrics, sizing
from tamad.matrix import SYMBOLS
from tamad.risk_report import survivor_trades

TRAIN_END = pd.Timestamp("2023-01-01", tz="UTC")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--start", default="2017-08-01")
    p.add_argument("--end", default="2025-01-01")
    p.add_argument("--report", default="docs/COSTS_RESULTS.md")
    args = p.parse_args()

    lines = ["# Costs applied to the final configuration", "",
             "Survivor pills + trail_1R · Binance spot model: 0.10%/side + "
             "0.02% spread = 0.22% of notional per round trip · cost in R = "
             "0.22% x fill / risk-distance · holdout still locked.", ""]

    rows = []
    portfolios = {}
    for interval in ("5m", "15m", "1h"):
        for symbol in SYMBOLS:
            trades = survivor_trades(symbol, interval, args.start, args.end)
            with_costs = costs.apply(trades, costs.BINANCE_SPOT)
            m0 = metrics.summarize(trades)
            m1 = metrics.summarize(with_costs)
            rows.append({
                "interval": interval, "asset": symbol,
                "trades": m0["trade_count"],
                "net_r_zero_cost": round(m0["net_r"], 1),
                "net_r_with_costs": round(m1["net_r"], 1),
                "pf_zero_cost": round(m0["profit_factor"], 3),
                "pf_with_costs": round(m1["profit_factor"], 3),
                "median_cost_r": round(float(with_costs["cost_r"].median()), 3),
            })
            portfolios.setdefault(interval, []).append(with_costs)
            print(rows[-1], flush=True)

    table = pd.DataFrame(rows)
    lines += ["## Per asset and interval", "", table.to_markdown(index=False), ""]

    lines += ["## Parity portfolio on the TEST window, with costs", ""]
    for interval, frames in portfolios.items():
        per_asset = {}
        for symbol, wc in zip(SYMBOLS, frames):
            exit_t = pd.to_datetime(wc["exit_time"], utc=True)
            train = wc[exit_t < TRAIN_END]
            test = wc[exit_t >= TRAIN_END]
            if len(train) < 20 or len(test) == 0:
                continue
            pct = sizing.dd_parity_pct(train, 0.20, sizer=sizing.HighWatermark)
            per_asset[symbol] = (test, sizing.HighWatermark(pct))
        if not per_asset:
            continue
        curve, contrib = sizing.portfolio_curve(per_asset)
        ret = curve.iloc[-1] / 10_000 - 1 if len(curve) else 0.0
        dd = sizing.max_drawdown_pct(curve)
        lines += [f"- **{interval}**: test return {ret:.1%}, maxDD {dd:.1%} · "
                  + ", ".join(f"{a}: ${v:,.0f}" for a, v in contrib.items())]
        print(f"{interval} portfolio with costs: {ret:.1%}, dd {dd:.1%}", flush=True)

    Path(args.report).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"report written to {args.report}")


if __name__ == "__main__":
    main()
