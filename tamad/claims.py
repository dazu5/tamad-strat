"""Monte Carlo claim checker: are claimed performance numbers plausible?

Pure simulation over claimed win rate / RR / trade count — reads no market
data. Formalizes the Phase-0 check in STRATEGY_SPEC.md section 1b.

Usage:
    python -m tamad.claims --wr 0.60 --rr 3 --n 300
"""

from __future__ import annotations

import argparse
import math

import numpy as np


def check_claim(
    win_rate: float,
    rr: float,
    n_trades: int,
    compound_risk: float = 0.01,
    paths: int = 2000,
    seed: int = 42,
) -> dict:
    expectancy = win_rate * rr - (1 - win_rate)
    variance = (win_rate * rr * rr + (1 - win_rate)) - expectancy**2
    half = 1.96 * math.sqrt(win_rate * (1 - win_rate) / n_trades)

    rng = np.random.default_rng(seed)
    outcomes = rng.random((paths, n_trades)) < win_rate
    step = np.where(outcomes, 1 + compound_risk * rr, 1 - compound_risk)
    equity = np.cumprod(step, axis=1)
    peaks = np.maximum.accumulate(equity, axis=1)
    maxdd = (1 - equity / peaks).max(axis=1)

    return {
        "expectancy_r": expectancy,
        "breakeven_wr": 1 / (1 + rr),
        "wr_ci95": (win_rate - half, win_rate + half),
        "flat_expected_net_r": expectancy * n_trades,
        "flat_sd_net_r": math.sqrt(n_trades * variance),
        "compound_median_multiple": float(np.median(equity[:, -1])),
        "compound_p5_multiple": float(np.percentile(equity[:, -1], 5)),
        "compound_p95_multiple": float(np.percentile(equity[:, -1], 95)),
        "compound_median_maxdd": float(np.median(maxdd)),
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--wr", type=float, required=True, help="claimed win rate, e.g. 0.60")
    p.add_argument("--rr", type=float, required=True, help="claimed reward:risk, e.g. 3")
    p.add_argument("--n", type=int, required=True, help="claimed trade count")
    p.add_argument("--risk", type=float, default=0.01, help="compounding risk per trade")
    args = p.parse_args()
    r = check_claim(args.wr, args.rr, args.n, compound_risk=args.risk)
    lo, hi = r["wr_ci95"]
    print(f"Claim check - WR {args.wr:.0%} at 1:{args.rr:g} over {args.n} trades")
    print(f"  expectancy:        {r['expectancy_r']:+.2f} R/trade (breakeven WR {r['breakeven_wr']:.1%})")
    print(f"  WR 95% CI at n:    {lo:.1%} .. {hi:.1%}")
    print(f"  flat risk net:     {r['flat_expected_net_r']:+.0f} R (sd {r['flat_sd_net_r']:.0f} R)")
    print(f"  compounding {args.risk:.1%}/trade over the claimed sample:")
    print(f"    median multiple: {r['compound_median_multiple']:.2f}x "
          f"(p5 {r['compound_p5_multiple']:.2f}x, p95 {r['compound_p95_multiple']:.2f}x)")
    print(f"    median max DD:   {r['compound_median_maxdd']:.1%}")


if __name__ == "__main__":
    main()
