"""Ablation study (#14): every pill combination, PF-ranked.

The grid (rationale in docs/ABLATION_RESULTS.md when run):
    sweep_required:  off, on                                   x2
    c1_min_atr:      off, 1.0  (the #7 survivor; 1.5+ collapse) x2
    zones:           none, swing, sr, fvg, ob, div, all         x7
    session:         all, asia, europe, us                      x4
    bias:            none, 4h, 1d  (tp_mode own; htf collapsed
                     win rate in the #13 screen)                x3
    = 336 configurations, evaluated on the portfolio frame
      (all basket combos combined, flat $1 risk, zero costs).

For speed the harness precomputes each combo's context ONCE (setups,
zone memberships, session masks, bias-qualifying sets) and evaluates
every configuration as boolean masks + one engine simulation. An
equivalence test pins harness output to experiments.run for the same
config. Selection happens on the training period only; confirm_on_test
re-runs chosen configs through experiments.run on the test window.
"""

from __future__ import annotations

import itertools
import json
from dataclasses import replace
from pathlib import Path

import pandas as pd

from tamad import data, engine, experiments, metrics, pattern
from tamad.experiments import RunConfig
from tamad.matrix import INTERVALS, SYMBOLS

GRID = {
    "sweep_required": [False, True],
    "c1_min_atr": [None, 1.0],
    "zones": [(), ("swing",), ("sr",), ("fvg",), ("ob",), ("div",),
              ("swing", "sr", "fvg", "ob", "div")],
    "session": [None, "asia_00_08", "europe_08_16", "us_16_24"],
    "bias_tf": [None, "4h", "1d"],
}
ZONE_KINDS = ("swing", "sr", "fvg", "ob", "div")


def combo_context(symbol: str, interval: str, start: str, end: str) -> dict:
    """Everything needed to evaluate any grid config on one combo."""
    candles = data.candles(symbol, interval, start, end)
    setups = pattern.detect(candles)
    base_cfg = RunConfig(symbol=symbol, interval=interval, start=start, end=end)
    kind_hits = {}
    for kind in ZONE_KINDS:
        kept = experiments._filter_by_zones(
            setups, candles, replace(base_cfg, zones=(kind,)))
        kind_hits[kind] = set(kept.index)
    bias_keep = {}
    for tf in ("4h", "1d"):
        htf_candles = data.candles(symbol, tf, start, end)
        htf_setups = pattern.detect(htf_candles)
        kept = experiments._apply_bias(setups, htf_setups, tf,
                                       bias_max_age=12, tp_mode="own")
        bias_keep[tf] = set(kept.index)
    return {"symbol": symbol, "interval": interval,
            "candles": candles, "setups": setups,
            "kind_hits": kind_hits, "bias_keep": bias_keep}


def evaluate(ctx: dict, cfg: dict) -> pd.DataFrame:
    """Trades for one grid config on one combo context."""
    setups = ctx["setups"]
    mask = pd.Series(True, index=setups.index)
    if cfg["sweep_required"]:
        mask &= setups["sweep"]
    if cfg["c1_min_atr"] is not None:
        mask &= setups["c1_atr_mult"] >= cfg["c1_min_atr"]
    if cfg["session"]:
        mask &= experiments._session_mask(setups.index, cfg["session"])
    if cfg["zones"]:
        qualifying = set()
        for kind in cfg["zones"]:
            qualifying |= ctx["kind_hits"][kind]
        mask &= setups.index.isin(list(qualifying))
    if cfg["bias_tf"]:
        mask &= setups.index.isin(list(ctx["bias_keep"][cfg["bias_tf"]]))
    return engine.simulate(setups[mask], ctx["candles"])


def portfolio_row(trade_frames: list[pd.DataFrame]) -> dict:
    combined = (pd.concat(trade_frames, ignore_index=True)
                if trade_frames else pd.DataFrame({"r_multiple": [], "pnl": []}))
    return metrics.summarize(combined)


def run_grid(contexts: list[dict]) -> pd.DataFrame:
    rows = []
    keys = list(GRID)
    for values in itertools.product(*(GRID[k] for k in keys)):
        cfg = dict(zip(keys, values))
        frames = []
        per_combo_pf = []
        for ctx in contexts:
            trades = evaluate(ctx, cfg)
            frames.append(trades)
            per_combo_pf.append(metrics.summarize(trades)["profit_factor"])
        agg = portfolio_row(frames)
        rows.append({
            **{k: (",".join(v) if isinstance(v, tuple) else v)
               for k, v in cfg.items()},
            **agg,
            "combos_pf_above_1": sum(1 for pf in per_combo_pf if pf > 1.0),
        })
    table = pd.DataFrame(rows).sort_values("profit_factor", ascending=False)
    return table.reset_index(drop=True)


def confirm_on_test(top: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    """Re-run chosen configs through experiments.run on the test window."""
    rows = []
    for _, r in top.iterrows():
        frames = []
        for symbol in SYMBOLS:
            for interval in INTERVALS:
                config = RunConfig(
                    symbol=symbol, interval=interval, start=start, end=end,
                    sweep_required=bool(r["sweep_required"]),
                    c1_min_atr=None if pd.isna(r["c1_min_atr"]) else float(r["c1_min_atr"]),
                    zones=tuple(k for k in str(r["zones"]).split(",") if k),
                    session=None if pd.isna(r["session"]) else r["session"],
                    bias_tf=None if pd.isna(r["bias_tf"]) else r["bias_tf"],
                )
                record = experiments.run(config)
                try:
                    frames.append(experiments.load_trades(record["config_hash"]))
                except FileNotFoundError:
                    pass
        agg = portfolio_row(frames)
        rows.append({**{k: r[k] for k in GRID}, **agg})
    return pd.DataFrame(rows)


def main() -> None:
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--start", default="2017-08-01")
    p.add_argument("--end", default="2023-01-01")
    p.add_argument("--test-start", default="2023-01-01")
    p.add_argument("--test-end", default="2025-01-01")
    p.add_argument("--top", type=int, default=10)
    p.add_argument("--report", default="docs/ABLATION_RESULTS.md")
    args = p.parse_args()

    contexts = []
    for symbol in SYMBOLS:
        for interval in INTERVALS:
            print(f"context {symbol} {interval}...", flush=True)
            contexts.append(combo_context(symbol, interval, args.start, args.end))

    print("evaluating grid...", flush=True)
    train_table = run_grid(contexts)
    train_table.to_json("results/ablation_train.json", orient="records", indent=2)

    top = train_table.head(args.top)
    print("confirming top configs on test...", flush=True)
    test_table = confirm_on_test(top, args.test_start, args.test_end)

    lines = ["# Ablation study", "",
             f"Grid: {' x '.join(str(len(v)) for v in GRID.values())} = "
             f"{len(train_table)} configurations. Portfolio frame (9 combos, "
             "flat $1 risk, zero costs). Ranked by profit factor on the "
             f"TRAINING window [{args.start} .. {args.end}); the top "
             f"{args.top} were then confirmed on the TEST window "
             f"[{args.test_start} .. {args.test_end}) via the experiment "
             "runner (selection never saw test data).", "",
             "## Training ranking (top 25)", "",
             train_table.head(25).to_markdown(index=False), "",
             "## Bottom 5 (for contrast)", "",
             train_table.tail(5).to_markdown(index=False), "",
             "## Test confirmation of the training top 10", "",
             test_table.to_markdown(index=False), ""]
    Path(args.report).write_text("\n".join(lines), encoding="utf-8")
    print(f"report written to {args.report}")


if __name__ == "__main__":
    main()
