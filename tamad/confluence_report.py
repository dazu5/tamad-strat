"""V1.x / V2 zone experiments and the confluence-count verdict (#8-#10).

Runs, per asset/timeframe on the training period: V1.<kind> for each of
the five zone detectors, V2 (any zone qualifies, as taught), and buckets
V0 setups by how many distinct zone kinds they fall in (0 / 1 / 2+),
simulating each bucket. Answers "does confluence help, and does MORE
confluence help more?" with training data only.

Usage:
    python -m tamad.confluence_report --start 2017-08-01 --end 2023-01-01 \
        --report docs/ZONES_RESULTS.md
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from tamad import data, engine, experiments, metrics, pattern
from tamad.experiments import RunConfig
from tamad.matrix import INTERVALS, SYMBOLS

KINDS = ("swing", "sr", "fvg", "ob", "div")


def kind_membership(symbol, interval, start, end) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """V0 setups plus, per zone kind, the set of qualifying signal times."""
    candles = data.candles(symbol, interval, start, end)
    setups = pattern.detect(candles)
    hits = {}
    for kind in KINDS:
        cfg = RunConfig(symbol=symbol, interval=interval, start=start, end=end,
                        zones=(kind,))
        kept = experiments._filter_by_zones(setups, candles, cfg)
        hits[kind] = set(kept.index)
    return candles, setups, hits


def bucket_metrics(candles, setups, hits) -> pd.DataFrame:
    counts = pd.Series(
        [sum(t in s for s in hits.values()) for t in setups.index],
        index=setups.index,
    )
    rows = {}
    for label, mask in (
        ("0_zones", counts == 0),
        ("1_zone", counts == 1),
        ("2plus_zones", counts >= 2),
    ):
        trades = engine.simulate(setups[mask], candles)
        rows[label] = metrics.summarize(trades)
    return pd.DataFrame(rows).T


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--start", required=True)
    p.add_argument("--end", required=True)
    p.add_argument("--report", default=None)
    args = p.parse_args()

    v1_rows = []
    bucket_frames = []
    for symbol in SYMBOLS:
        for interval in INTERVALS:
            for kind in KINDS + ("V2",):
                zones = KINDS if kind == "V2" else (kind,)
                record = experiments.run(RunConfig(
                    symbol=symbol, interval=interval,
                    start=args.start, end=args.end, zones=tuple(zones)))
                v1_rows.append({
                    "symbol": symbol, "interval": interval,
                    "variant": f"V1.{kind}" if kind != "V2" else "V2",
                    **record["metrics"],
                })
                print(f"{symbol} {interval} {kind}: "
                      f"n={record['metrics']['trade_count']} "
                      f"wr={record['metrics']['win_rate']:.3f} "
                      f"pf={record['metrics']['profit_factor']:.3f}", flush=True)
            candles, setups, hits = kind_membership(
                symbol, interval, args.start, args.end)
            buckets = bucket_metrics(candles, setups, hits)
            buckets.insert(0, "combo", f"{symbol} {interval}")
            bucket_frames.append(buckets)

    v1 = pd.DataFrame(v1_rows)
    buckets_all = pd.concat(bucket_frames)
    if args.report:
        lines = ["# Zone experiments — V1.x, V2, confluence counts (training)", ""]
        for variant, group in v1.groupby("variant"):
            lines += [f"## {variant}", "", group.drop(columns="variant")
                      .to_markdown(index=False), ""]
        agg = v1.groupby("variant")[["win_rate", "profit_factor"]].mean() \
                .sort_values("profit_factor", ascending=False)
        lines += ["## Variant means", "", agg.to_markdown(), ""]
        lines += ["## Confluence-count buckets (per combo)", "",
                  buckets_all.to_markdown(), ""]
        agg2 = buckets_all.groupby(buckets_all.index)[
            ["win_rate", "profit_factor"]].mean()
        lines += ["## Bucket means", "", agg2.to_markdown(), ""]
        Path(args.report).write_text("\n".join(lines), encoding="utf-8")
        print(f"report written to {args.report}")


if __name__ == "__main__":
    main()
