"""V4 as-documented audit (#22): the official spec on its own terms.

Grid (2 rr x 2 wick x 2 c1 x 6 zones x 2 session x 2 context = 192
configs) over BTC/ETH/SOL x the doc's traded timeframes 15m/30m/1h/4h,
evaluated combo-major on the portfolio frame (flat $1, zero costs),
ranked by profit factor on TRAINING only. The top configs are then
confirmed on TEST via experiments.run (selection never sees test), the
doc's own claims (52% @ 2RR, 46% @ 3RR) are checked against measured
test win rates, the continuation pill is ablated on/off on the best
confirmed config, and survivors get costed at Binance spot taker and
MEXC futures taker. Holdout (2025+) stays sealed throughout.

Usage:
    python -m tamad.v4 --report docs/V4_RESULTS.md
"""

from __future__ import annotations

import argparse
import gc
import itertools
import json
from dataclasses import replace
from pathlib import Path

import pandas as pd

from tamad import costs, data, engine, experiments, metrics, pattern
from tamad.ablation import portfolio_row
from tamad.experiments import RunConfig
from tamad.matrix import SYMBOLS

GRID_V4 = {
    "rr": [2.0, 3.0],
    "full_wick_required": [False, True],
    "c1_min_atr": [None, 1.0],
    "zones": [(), ("eq",), ("sr",), ("fvg",), ("ob",), ("eq", "sr", "fvg")],
    "session": [None, "us_16_24"],
    "context": [None, "continuation"],
}
INTERVALS_V4 = ("15m", "30m", "1h", "4h")
V4_ZONE_KINDS = ("eq", "sr", "fvg", "ob")

MEXC_FUT = costs.CostModel(fee_pct_per_side=0.0002, spread_pct=0.0003)

DOC_BUNDLES = {
    "doc-minimal (wick rule only)": dict(full_wick_required=True),
    "doc-full (wick + eq/sr/fvg levels)": dict(full_wick_required=True,
                                               zones=("eq", "sr", "fvg")),
}
DOC_CLAIMS = {2.0: 0.52, 3.0: 0.46}


def combo_context_v4(symbol: str, interval: str, start: str, end: str) -> dict:
    """Everything needed to evaluate any V4 config on one combo."""
    candles = data.candles(symbol, interval, start, end)
    setups = pattern.detect(candles)
    base_cfg = RunConfig(symbol=symbol, interval=interval, start=start, end=end)
    kind_hits = {}
    for kind in V4_ZONE_KINDS:
        kept = experiments._filter_by_zones(
            setups, candles, replace(base_cfg, zones=(kind,)))
        kind_hits[kind] = set(kept.index)
    session_keep = set(setups.index[
        experiments._session_mask(setups.index, "us_16_24").to_numpy()])
    context_keep = set(setups.index[
        experiments._context_mask(setups, candles, "continuation").to_numpy()])
    return {"symbol": symbol, "interval": interval,
            "candles": candles, "setups": setups, "kind_hits": kind_hits,
            "session_keep": session_keep, "context_keep": context_keep}


def select_setups_v4(ctx: dict, cfg: dict) -> pd.DataFrame:
    setups = ctx["setups"]
    mask = pd.Series(True, index=setups.index)
    if cfg["full_wick_required"]:
        mask &= setups["full_wick"]
    if cfg["c1_min_atr"] is not None:
        mask &= setups["c1_atr_mult"] >= cfg["c1_min_atr"]
    if cfg["zones"]:
        qualifying = set()
        for kind in cfg["zones"]:
            qualifying |= ctx["kind_hits"][kind]
        mask &= setups.index.isin(list(qualifying))
    if cfg["session"]:
        mask &= setups.index.isin(list(ctx["session_keep"]))
    if cfg["context"]:
        mask &= setups.index.isin(list(ctx["context_keep"]))
    return setups[mask]


def evaluate_v4(ctx: dict, cfg: dict) -> pd.DataFrame:
    return engine.simulate(select_setups_v4(ctx, cfg), ctx["candles"], rr=cfg["rr"])


def _grid_configs() -> list[dict]:
    keys = list(GRID_V4)
    return [dict(zip(keys, values))
            for values in itertools.product(*(GRID_V4[k] for k in keys))]


def run_grid_v4(contexts=None, combo_specs=None, start=None, end=None) -> pd.DataFrame:
    """Combo-major sweep: one context in memory at a time (OOM rule)."""
    configs = _grid_configs()
    acc = [{"gross_p": 0.0, "gross_l": 0.0, "net": 0.0, "n": 0, "wins": 0,
            "pf_above": 0} for _ in configs]

    def sweep(ctx):
        for i, cfg in enumerate(configs):
            trades = evaluate_v4(ctx, cfg)
            pnl = trades["pnl"]
            gross_p = float(pnl[pnl > 0].sum())
            gross_l = float(-pnl[pnl < 0].sum())
            acc[i]["gross_p"] += gross_p
            acc[i]["gross_l"] += gross_l
            acc[i]["net"] += float(pnl.sum())
            acc[i]["n"] += int(len(trades))
            acc[i]["wins"] += int((pnl > 0).sum())
            if gross_l > 0 and gross_p / gross_l > 1.0:
                acc[i]["pf_above"] += 1

    if contexts is not None:
        for ctx in contexts:
            sweep(ctx)
    else:
        for symbol, interval in combo_specs:
            print(f"context {symbol} {interval}...", flush=True)
            ctx = combo_context_v4(symbol, interval, start, end)
            sweep(ctx)
            del ctx
            gc.collect()

    rows = []
    for cfg, a in zip(configs, acc):
        pf = (a["gross_p"] / a["gross_l"]) if a["gross_l"] > 0 else (
            float("inf") if a["gross_p"] > 0 else 0.0)
        rows.append({
            **{k: (",".join(v) if isinstance(v, tuple) else v)
               for k, v in cfg.items()},
            "trade_count": a["n"],
            "wins": a["wins"],
            "win_rate": a["wins"] / a["n"] if a["n"] else 0.0,
            "net_r": a["net"],
            "expectancy_r": a["net"] / a["n"] if a["n"] else 0.0,
            "profit_factor": pf,
            "combos_pf_above_1": a["pf_above"],
        })
    return pd.DataFrame(rows).sort_values(
        "profit_factor", ascending=False).reset_index(drop=True)


def _row_to_config(row, symbol: str, interval: str, start: str, end: str) -> RunConfig:
    return RunConfig(
        symbol=symbol, interval=interval, start=start, end=end,
        rr=float(row["rr"]),
        full_wick_required=bool(row["full_wick_required"]),
        c1_min_atr=None if pd.isna(row["c1_min_atr"]) else float(row["c1_min_atr"]),
        zones=tuple(k for k in str(row["zones"]).split(",") if k),
        session=None if (row["session"] is None or pd.isna(row["session"])) else row["session"],
        context=None if (row["context"] is None or pd.isna(row["context"])) else row["context"],
    )


def _portfolio_over_combos(row, start: str, end: str) -> dict:
    frames = []
    for symbol in SYMBOLS:
        for interval in INTERVALS_V4:
            record = experiments.run(_row_to_config(row, symbol, interval, start, end))
            try:
                frames.append(experiments.load_trades(record["config_hash"]))
            except FileNotFoundError:
                pass
    return portfolio_row(frames)


def confirm_on_test_v4(top: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    rows = []
    for _, r in top.iterrows():
        agg = _portfolio_over_combos(r, start, end)
        rows.append({**{k: r[k] for k in GRID_V4}, **agg})
        print(f"confirmed: rr={r['rr']} wick={r['full_wick_required']} "
              f"c1={r['c1_min_atr']} zones={r['zones']} sess={r['session']} "
              f"ctx={r['context']} -> test PF {agg['profit_factor']:.3f} "
              f"({agg['trade_count']} trades)", flush=True)
    return pd.DataFrame(rows)


def doc_claim_check(start: str, end: str) -> pd.DataFrame:
    """Measured TEST win rates for the doc's own configurations vs its claims."""
    rows = []
    for label, pills in DOC_BUNDLES.items():
        for rr, claimed in DOC_CLAIMS.items():
            row = {"rr": rr, "full_wick_required": pills.get("full_wick_required", False),
                   "c1_min_atr": None, "zones": ",".join(pills.get("zones", ())),
                   "session": None, "context": None}
            agg = _portfolio_over_combos(row, start, end)
            rows.append({
                "config": label, "rr": rr, "claimed_wr": claimed,
                "measured_wr": agg["win_rate"], "trades": agg["trade_count"],
                "breakeven_wr": 1 / (1 + rr),
                "profit_factor": agg["profit_factor"],
            })
            print(f"claim check {label} @{rr:g}RR: measured "
                  f"{agg['win_rate']:.1%} vs claimed {claimed:.0%}", flush=True)
    return pd.DataFrame(rows)


def continuation_ablation(best_row, train: tuple[str, str],
                          test: tuple[str, str]) -> pd.DataFrame:
    """The pill must earn its place: best config with context on vs off."""
    rows = []
    for context in ("continuation", None):
        variant = dict(best_row)
        variant["context"] = context
        for window, (s, e) in (("train", train), ("test", test)):
            agg = _portfolio_over_combos(variant, s, e)
            rows.append({"context": context or "off", "window": window,
                         "trades": agg["trade_count"], "win_rate": agg["win_rate"],
                         "net_r": agg["net_r"], "profit_factor": agg["profit_factor"]})
    return pd.DataFrame(rows)


def survivor_costs(best_row, start: str, end: str) -> pd.DataFrame:
    """Per-interval venue costs on the best confirmed config's TEST trades."""
    rows = []
    for interval in INTERVALS_V4:
        frames = []
        for symbol in SYMBOLS:
            record = experiments.run(_row_to_config(best_row, symbol, interval, start, end))
            try:
                frames.append(experiments.load_trades(record["config_hash"]))
            except FileNotFoundError:
                pass
        if not frames:
            continue
        pooled = pd.concat(frames, ignore_index=True)
        rows.append({
            "interval": interval, "trades": len(pooled),
            "pf_zero_cost": metrics.summarize(pooled)["profit_factor"],
            "pf_binance_spot": metrics.summarize(
                costs.apply(pooled, costs.BINANCE_SPOT))["profit_factor"],
            "pf_mexc_futures": metrics.summarize(
                costs.apply(pooled, MEXC_FUT))["profit_factor"],
        })
    return pd.DataFrame(rows)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--start", default="2017-08-01")
    p.add_argument("--end", default="2023-01-01")
    p.add_argument("--test-start", default="2023-01-01")
    p.add_argument("--test-end", default="2025-01-01")
    p.add_argument("--top", type=int, default=10)
    p.add_argument("--report", default="docs/V4_RESULTS.md")
    args = p.parse_args()

    combo_specs = [(s, i) for s in SYMBOLS for i in INTERVALS_V4]
    train_table = run_grid_v4(combo_specs=combo_specs,
                              start=args.start, end=args.end)
    Path("results").mkdir(exist_ok=True)
    train_table.to_json("results/v4_train.json", orient="records", indent=2)
    print("training grid done", flush=True)

    top = train_table.head(args.top)
    test_table = confirm_on_test_v4(top, args.test_start, args.test_end)

    claims_table = doc_claim_check(args.test_start, args.test_end)

    best = test_table.sort_values("profit_factor", ascending=False).iloc[0]
    cont_table = continuation_ablation(
        {k: best[k] for k in GRID_V4},
        (args.start, args.end), (args.test_start, args.test_end))
    costs_table = survivor_costs({k: best[k] for k in GRID_V4},
                                 args.test_start, args.test_end)

    fmt = lambda df: df.round(3).to_markdown(index=False)
    lines = [
        "# V4 as-documented audit", "",
        f"Grid: {' x '.join(str(len(v)) for v in GRID_V4.values())} = "
        f"{len(train_table)} configs · combos: BTC/ETH/SOL x "
        f"{'/'.join(INTERVALS_V4)} · flat $1, zero costs · ranked by PF on "
        f"TRAINING [{args.start} .. {args.end}); top {args.top} confirmed on "
        f"TEST [{args.test_start} .. {args.test_end}) via the experiment "
        "runner. Selection never saw test. Holdout sealed.", "",
        "## Training ranking (top 25)", "", fmt(train_table.head(25)), "",
        "## Bottom 5 (for contrast)", "", fmt(train_table.tail(5)), "",
        "## Test confirmation of the training top 10", "", fmt(test_table), "",
        "## The doc's own claims vs measured TEST win rates", "",
        fmt(claims_table), "",
        "## Continuation pill ablation on the best confirmed config", "",
        fmt(cont_table), "",
        "## Venue costs on the best confirmed config (TEST, pooled assets)", "",
        fmt(costs_table), "",
    ]
    Path(args.report).write_text("\n".join(lines), encoding="utf-8")
    print(f"report written to {args.report}", flush=True)


if __name__ == "__main__":
    main()
