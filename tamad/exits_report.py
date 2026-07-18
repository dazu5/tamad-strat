"""Exit-structure exploration (#15).

Runs the surviving configuration's setups through every exit structure:
the taught fixed 1:3, a fixed-RR ladder (0.5R-4R), the 1R-step trailing
stop, and an ATR trail — per combo, on a chosen window. Ranked by PF and
by net R; realized average winner R shows what each structure actually
collects. Train first, then confirm the chosen structure on test.

Usage:
    python -m tamad.exits_report --start 2017-08-01 --end 2023-01-01 \
        --report docs/EXITS_RESULTS.md [--sweep] [--c1 1.0] [--zones swing,sr] \
        [--session asia_00_08] [--bias 4h]
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from tamad import ablation, exits, metrics
from tamad.matrix import INTERVALS, SYMBOLS

STRUCTURES = [
    ("fixed_0.5R", exits.FixedRR(0.5)),
    ("fixed_1R", exits.FixedRR(1.0)),
    ("fixed_1.5R", exits.FixedRR(1.5)),
    ("fixed_2R", exits.FixedRR(2.0)),
    ("taught_3R", exits.FixedRR(3.0)),
    ("fixed_4R", exits.FixedRR(4.0)),
    ("trail_1R", exits.TrailStep(1.0)),
    ("trail_0.5R", exits.TrailStep(0.5)),
    ("atr_trail_2", exits.AtrTrail(mult=2.0)),
]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--start", required=True)
    p.add_argument("--end", required=True)
    p.add_argument("--sweep", action="store_true")
    p.add_argument("--c1", type=float, default=None)
    p.add_argument("--zones", default="")
    p.add_argument("--session", default=None)
    p.add_argument("--bias", default=None)
    p.add_argument("--report", default=None)
    args = p.parse_args()
    cfg = dict(sweep_required=args.sweep, c1_min_atr=args.c1,
               zones=tuple(k for k in args.zones.split(",") if k),
               session=args.session, bias_tf=args.bias)

    rows = []
    for symbol in SYMBOLS:
        for interval in INTERVALS:
            ctx = ablation.combo_context(symbol, interval, args.start, args.end)
            setups = ctx["setups"]
            mask = pd.Series(True, index=setups.index)
            if cfg["sweep_required"]:
                mask &= setups["sweep"]
            if cfg["c1_min_atr"] is not None:
                mask &= setups["c1_atr_mult"] >= cfg["c1_min_atr"]
            if cfg["session"]:
                from tamad.experiments import _session_mask
                mask &= _session_mask(setups.index, cfg["session"])
            if cfg["zones"]:
                qualifying = set()
                for kind in cfg["zones"]:
                    qualifying |= ctx["kind_hits"][kind]
                mask &= setups.index.isin(list(qualifying))
            if cfg["bias_tf"]:
                mask &= setups.index.isin(list(ctx["bias_keep"][cfg["bias_tf"]]))
            selected = setups[mask]
            for name, strategy in STRUCTURES:
                trades = exits.simulate_with_exit(selected, ctx["candles"], strategy)
                m = metrics.summarize(trades)
                wins = trades[trades["r_multiple"] > 0]
                rows.append({
                    "symbol": symbol, "interval": interval, "structure": name,
                    **m,
                    "avg_win_r": float(wins["r_multiple"].mean()) if len(wins) else 0.0,
                })
                print(f"{symbol} {interval} {name}: n={m['trade_count']} "
                      f"wr={m['win_rate']:.3f} pf={m['profit_factor']:.3f} "
                      f"net={m['net_r']:+.0f}R", flush=True)

    table = pd.DataFrame(rows)
    if args.report:
        lines = ["# Exit-structure exploration", "",
                 f"Config pills: {cfg} · window [{args.start} .. {args.end}) · "
                 "zero costs · flat $1 risk.", ""]
        for (symbol, interval), group in table.groupby(["symbol", "interval"]):
            lines += [f"## {symbol} {interval}", "",
                      group.drop(columns=["symbol", "interval"])
                      .sort_values("profit_factor", ascending=False)
                      .to_markdown(index=False), ""]
        agg = table.groupby("structure")[
            ["win_rate", "profit_factor", "net_r", "avg_win_r"]].mean() \
            .sort_values("profit_factor", ascending=False)
        lines += ["## Structure means across combos", "", agg.to_markdown(), ""]
        Path(args.report).write_text("\n".join(lines), encoding="utf-8")
        print(f"report written to {args.report}")


if __name__ == "__main__":
    main()
