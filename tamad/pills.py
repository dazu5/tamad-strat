"""Pattern pills (#7): marginal contribution of ideal-sweep and C1-size.

Compares V0 against each pill and their combinations per asset/timeframe
on the training period. Retention = trade count relative to V0; a variant
retaining under COLLAPSE_RATIO of V0's sample is flagged `collapsed` per
the spec rule (drop the filter if it starves the sample).

Usage:
    python -m tamad.pills --start 2017-08-01 --end 2023-01-01 \
        --report docs/PILLS_RESULTS.md
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from tamad import experiments
from tamad.experiments import RunConfig
from tamad.matrix import INTERVALS, SYMBOLS

COLLAPSE_RATIO = 0.10
C1_GRID = (1.0, 1.5, 2.0)


def _variants(c1_grid):
    yield "v0", dict()
    yield "sweep", dict(sweep_required=True)
    for k in c1_grid:
        yield f"c1@{k}", dict(c1_min_atr=k)
    for k in c1_grid:
        yield f"both@{k}", dict(sweep_required=True, c1_min_atr=k)


def compare(symbols, intervals, start, end, c1_grid=C1_GRID) -> pd.DataFrame:
    rows = []
    for symbol in symbols:
        for interval in intervals:
            v0_count = None
            for variant, pills in _variants(c1_grid):
                record = experiments.run(RunConfig(
                    symbol=symbol, interval=interval, start=start, end=end, **pills))
                m = record["metrics"]
                if variant == "v0":
                    v0_count = m["trade_count"]
                retention = (m["trade_count"] / v0_count) if v0_count else 0.0
                rows.append({
                    "symbol": symbol, "interval": interval, "variant": variant,
                    "config_hash": record["config_hash"],
                    "trade_count": m["trade_count"],
                    "retention": retention,
                    "collapsed": retention < COLLAPSE_RATIO and variant != "v0",
                    "win_rate": m["win_rate"],
                    "expectancy_r": m["expectancy_r"],
                    "net_r": m["net_r"],
                    "profit_factor": m["profit_factor"],
                })
    return pd.DataFrame(rows)


def write_report(table: pd.DataFrame, path) -> None:
    lines = ["# Pattern pills — marginal contribution (training period)", "",
             "Retention = trades kept vs V0. `collapsed` = under "
             f"{COLLAPSE_RATIO:.0%} retention (filter starves the sample).", ""]
    for (symbol, interval), group in table.groupby(["symbol", "interval"]):
        lines += [f"## {symbol} {interval}", "",
                  group.drop(columns=["symbol", "interval"]).to_markdown(index=False), ""]
    agg = (table[~table["collapsed"]]
           .groupby("variant")[["win_rate", "profit_factor"]].mean()
           .sort_values("profit_factor", ascending=False))
    lines += ["## Variant means (non-collapsed combos)", "", agg.to_markdown(), ""]
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--start", required=True)
    p.add_argument("--end", required=True)
    p.add_argument("--report", default=None)
    args = p.parse_args()
    table = compare(SYMBOLS, INTERVALS, args.start, args.end)
    print(table.to_string(index=False))
    if args.report:
        write_report(table, args.report)
        print(f"report written to {args.report}")


if __name__ == "__main__":
    main()
