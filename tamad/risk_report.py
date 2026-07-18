"""Risk and portfolio engineering (#17).

Per asset, on the surviving configuration (C1>=1xATR + OB zone + US
session) with the chosen trail_1R exit:

- sizing comparison: fixed 1%, high-watermark 1%, high-watermark 0.5%
- drawdown-parity percentages calibrated on TRAINING trades only
  (target ~20% standalone maxDD, high-watermark sizing), then applied
  UNSEEN to the test window - honest out-of-sample risk numbers
- portfolio: parity-sized assets merged chronologically, per-asset
  dollar contribution on the test window

Reported for both a 5m-based and a 15m-based portfolio (the cost
decision between them belongs to #18).

Usage:
    python -m tamad.risk_report --report docs/RISK_RESULTS.md
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from tamad import ablation, exits, sizing
from tamad.matrix import SYMBOLS

TRAIN_END = pd.Timestamp("2023-01-01", tz="UTC")
TARGET_DD = 0.20
PILLS = dict(sweep_required=False, c1_min_atr=1.0, zones=("ob",),
             session="us_16_24", bias_tf=None)


def survivor_trades(symbol: str, interval: str, start: str, end: str) -> pd.DataFrame:
    ctx = ablation.combo_context(symbol, interval, start, end)
    trades = exits.simulate_with_exit(
        ablation.select_setups(ctx, PILLS), ctx["candles"], exits.TrailStep(1.0))
    trades["asset"] = symbol
    return trades


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--start", default="2017-08-01")
    p.add_argument("--end", default="2025-01-01")
    p.add_argument("--report", default="docs/RISK_RESULTS.md")
    args = p.parse_args()

    lines = ["# Risk & portfolio engineering", "",
             "Survivor config + trail_1R exit · zero costs · parity calibrated "
             "on training only, applied unseen to test.", ""]

    for interval in ("5m", "15m"):
        lines += [f"## {interval}-based portfolio", ""]
        per_asset = {}
        parity = {}
        rows = []
        for symbol in SYMBOLS:
            trades = survivor_trades(symbol, interval, args.start, args.end)
            exit_t = pd.to_datetime(trades["exit_time"], utc=True)
            train = trades[exit_t < TRAIN_END]
            test = trades[exit_t >= TRAIN_END]
            pct = sizing.dd_parity_pct(train, TARGET_DD, sizer=sizing.HighWatermark)
            parity[symbol] = pct
            for label, sizer in (
                ("fixed 1%", sizing.FixedPct(0.01)),
                ("HWM 1%", sizing.HighWatermark(0.01)),
                ("HWM 0.5%", sizing.HighWatermark(0.005)),
                (f"HWM parity ({pct:.2%})", sizing.HighWatermark(pct)),
            ):
                ctr = sizing.equity_curve(train, sizer)
                cte = sizing.equity_curve(test, sizer)
                rows.append({
                    "asset": symbol, "sizing": label,
                    "train_return": ctr.iloc[-1] / 10_000 - 1 if len(ctr) else 0.0,
                    "train_maxdd": sizing.max_drawdown_pct(ctr),
                    "test_return": cte.iloc[-1] / 10_000 - 1 if len(cte) else 0.0,
                    "test_maxdd": sizing.max_drawdown_pct(cte),
                })
            per_asset[symbol] = (test, sizing.HighWatermark(pct))
            print(f"{symbol} {interval}: parity={pct:.3%} "
                  f"train_n={len(train)} test_n={len(test)}", flush=True)

        table = pd.DataFrame(rows)
        for col in ("train_return", "train_maxdd", "test_return", "test_maxdd"):
            table[col] = (table[col] * 100).round(1)
        lines += [table.to_markdown(index=False), ""]

        curve, contrib = sizing.portfolio_curve(per_asset)
        total = curve.iloc[-1] / 10_000 - 1 if len(curve) else 0.0
        lines += [f"### Portfolio (parity-sized, TEST window only)",
                  "",
                  f"- return: {total:.1%} · maxDD: "
                  f"{sizing.max_drawdown_pct(curve):.1%}",
                  "- contribution: " + ", ".join(
                      f"{a}: ${v:,.0f}" for a, v in contrib.items()), ""]
        print(f"{interval} portfolio test: {total:.1%}, "
              f"dd {sizing.max_drawdown_pct(curve):.1%}", flush=True)

    Path(args.report).write_text("\n".join(lines), encoding="utf-8")
    print(f"report written to {args.report}")


if __name__ == "__main__":
    main()
