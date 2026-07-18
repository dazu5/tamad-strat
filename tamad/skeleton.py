"""Walking skeleton: candles -> setups -> trades -> metrics, one command.

Usage:
    python -m tamad.skeleton --symbol BTCUSDT --interval 15m \
        --start 2022-01-01 --end 2022-07-01

Zero costs, flat $1 risk, taught exits (SL = pattern extreme, TP = 3R).
The holdout lock applies here directly until the experiment runner (#5)
takes over enforcement: any window touching 2025-01-01 or later refuses
to run without the runner's explicit unlock.
"""

from __future__ import annotations

import argparse

import pandas as pd

from tamad import data, engine, metrics, pattern

HOLDOUT_START = pd.Timestamp("2025-01-01", tz="UTC")


def run(symbol: str, interval: str, start: str, end: str) -> dict:
    if data.to_utc(end) > HOLDOUT_START:
        raise SystemExit(
            f"HOLDOUT LOCK: window may not touch {HOLDOUT_START.date()} or later "
            "(see CLAUDE.md; unlock arrives with issue #18 sign-off)."
        )
    candles = data.get_candles(symbol, interval, start, end)
    setups = pattern.detect(candles)
    trades = engine.simulate(setups, candles)
    summary = metrics.summarize(trades)
    summary["setups"] = int(len(setups))
    summary["exit_reasons"] = (
        trades["exit_reason"].value_counts().to_dict() if len(trades) else {}
    )
    return summary


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--symbol", default="BTCUSDT")
    p.add_argument("--interval", default="15m")
    p.add_argument("--start", required=True)
    p.add_argument("--end", required=True)
    args = p.parse_args()
    summary = run(args.symbol, args.interval, args.start, args.end)
    title = f"V0 walking skeleton - {args.symbol} {args.interval} [{args.start} .. {args.end})"
    print(metrics.summary_table(summary, title))
    print(f"  setups:        {summary['setups']}")
    print(f"  exit reasons:  {summary['exit_reasons']}")


if __name__ == "__main__":
    main()
