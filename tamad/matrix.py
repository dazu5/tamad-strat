"""V0 matrix execution and slice breakdowns.

Runs the naked pattern across the basket x timeframes through the
experiment runner and reports results sliced by asset, timeframe,
direction, session (UTC thirds — crypto has no exchange sessions), and
month. Slices under MIN_TRADES are flagged and excluded from conclusions.

Usage:
    python -m tamad.matrix --start 2017-01-01 --end 2023-01-01
"""

from __future__ import annotations

import argparse

import pandas as pd

from tamad import experiments, metrics
from tamad.experiments import RunConfig

MIN_TRADES = 30
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
INTERVALS = ["5m", "15m", "1h"]

_SESSION_BINS = [(0, 8, "asia_00_08"), (8, 16, "europe_08_16"), (16, 24, "us_16_24")]


def _group_key(trades: pd.DataFrame, by: str) -> pd.Series:
    entry = pd.to_datetime(trades["entry_time"], utc=True)
    if by == "direction":
        return trades["side"].map({1: "long", -1: "short"})
    if by == "session":
        hours = entry.dt.hour
        out = pd.Series(index=trades.index, dtype=object)
        for lo, hi, name in _SESSION_BINS:
            out[(hours >= lo) & (hours < hi)] = name
        return out
    if by == "month":
        return entry.dt.strftime("%Y-%m")
    raise ValueError(f"unknown breakdown: {by}")


def breakdown(trades: pd.DataFrame, by: str) -> pd.DataFrame:
    rows = {}
    for key, group in trades.groupby(_group_key(trades, by)):
        s = metrics.summarize(group)
        s["small_sample"] = s["trade_count"] < MIN_TRADES
        rows[key] = s
    return pd.DataFrame(rows).T.sort_index()


def run_matrix(symbols, intervals, start, end) -> pd.DataFrame:
    rows = []
    for symbol in symbols:
        for interval in intervals:
            record = experiments.run(RunConfig(
                symbol=symbol, interval=interval, start=start, end=end))
            rows.append({
                "symbol": symbol,
                "interval": interval,
                "config_hash": record["config_hash"],
                "split": record["split"],
                "setups": record["setups"],
                **record["metrics"],
            })
    return pd.DataFrame(rows)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--start", required=True)
    p.add_argument("--end", required=True)
    args = p.parse_args()
    table = run_matrix(SYMBOLS, INTERVALS, args.start, args.end)
    cols = ["symbol", "interval", "trade_count", "win_rate", "expectancy_r",
            "net_r", "profit_factor"]
    print(table[cols].to_string(index=False,
          formatters={"win_rate": "{:.1%}".format,
                      "expectancy_r": "{:+.3f}".format,
                      "net_r": "{:+.1f}".format,
                      "profit_factor": "{:.3f}".format}))


if __name__ == "__main__":
    main()
