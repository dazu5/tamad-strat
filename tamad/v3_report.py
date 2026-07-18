"""HTF-bias mode V3 comparison (#13).

Per trigger timeframe: V0 baseline vs bias from 4h and 1d, each with the
trade's own 3R target and with the HTF pattern's extended target
(tp_mode="htf"). Reports effective realized RR (mean R of winning
trades) alongside PF — an extended target only pays if winners actually
reach it. Training period only; the timeframe-distance verdict comes
from comparing bias TFs across trigger TFs.

Usage:
    python -m tamad.v3_report --start 2017-08-01 --end 2023-01-01 \
        --report docs/V3_RESULTS.md
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from tamad import experiments
from tamad.experiments import RunConfig
from tamad.matrix import INTERVALS, SYMBOLS

VARIANTS = [
    ("v0", dict()),
    ("4h_own", dict(bias_tf="4h", tp_mode="own")),
    ("4h_htf", dict(bias_tf="4h", tp_mode="htf")),
    ("1d_own", dict(bias_tf="1d", tp_mode="own")),
    ("1d_htf", dict(bias_tf="1d", tp_mode="htf")),
]


def realized_win_rr(config_hash: str) -> float:
    try:
        trades = experiments.load_trades(config_hash)
    except FileNotFoundError:
        return float("nan")
    wins = trades[trades["r_multiple"] > 0]
    return float(wins["r_multiple"].mean()) if len(wins) else float("nan")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--start", required=True)
    p.add_argument("--end", required=True)
    p.add_argument("--report", default=None)
    args = p.parse_args()

    rows = []
    for symbol in SYMBOLS:
        for interval in INTERVALS:
            for name, extra in VARIANTS:
                record = experiments.run(RunConfig(
                    symbol=symbol, interval=interval,
                    start=args.start, end=args.end, **extra))
                m = record["metrics"]
                rows.append({
                    "symbol": symbol, "interval": interval, "variant": name,
                    "trade_count": m["trade_count"], "win_rate": m["win_rate"],
                    "expectancy_r": m["expectancy_r"], "net_r": m["net_r"],
                    "profit_factor": m["profit_factor"],
                    "realized_win_rr": realized_win_rr(record["config_hash"]),
                })
                print(f"{symbol} {interval} {name}: n={m['trade_count']} "
                      f"wr={m['win_rate']:.3f} pf={m['profit_factor']:.3f}",
                      flush=True)

    table = pd.DataFrame(rows)
    if args.report:
        lines = ["# HTF-bias mode V3 (training period)", ""]
        for (symbol, interval), group in table.groupby(["symbol", "interval"]):
            lines += [f"## {symbol} {interval}", "",
                      group.drop(columns=["symbol", "interval"])
                      .to_markdown(index=False), ""]
        agg = table.groupby("variant")[
            ["win_rate", "profit_factor", "realized_win_rr"]].mean() \
            .sort_values("profit_factor", ascending=False)
        lines += ["## Variant means", "", agg.to_markdown(), ""]
        Path(args.report).write_text("\n".join(lines), encoding="utf-8")
        print(f"report written to {args.report}")


if __name__ == "__main__":
    main()
