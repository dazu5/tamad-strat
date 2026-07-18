"""One-file PDF report of the whole validation (docs/report/).

Recomputes the final configuration (survivor pills + trail_1R) on the
same code paths as the published docs — ablation.combo_context,
select_setups, simulate_with_exit, costs.apply — and renders the full
story: claim vs data, version ladder, equity curves, the cost kill-shot,
parity portfolios, and next steps. Holdout stays locked (window ends
2025-01-01).

Usage:
    python -m tamad.pdf_report --out docs/report/tamad-strat-report.pdf
"""

from __future__ import annotations

import argparse
import gc
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages

from tamad import ablation, costs, exits, metrics, sizing
from tamad.matrix import SYMBOLS
from tamad.risk_report import PILLS

TRAIN_END = pd.Timestamp("2023-01-01", tz="UTC")
INTERVALS = ("5m", "15m", "1h")
PAGE = (11.69, 8.27)  # A4 landscape
INK = "#1a1a2e"
BLUE = "#2563eb"
RED = "#dc2626"
GREEN = "#16a34a"
GRAY = "#6b7280"


def compute(start: str, end: str) -> dict:
    """One combo at a time (memory), keep only the small trade lists."""
    out = {}
    for interval in INTERVALS:
        for symbol in SYMBOLS:
            ctx = ablation.combo_context(symbol, interval, start, end)
            setups = ablation.select_setups(ctx, PILLS)
            trail = exits.simulate_with_exit(setups, ctx["candles"], exits.TrailStep(1.0))
            taught = exits.simulate_with_exit(setups, ctx["candles"], exits.FixedRR(3.0))
            del ctx, setups
            gc.collect()
            out[(interval, symbol)] = {
                "trail": trail,
                "trail_costs": costs.apply(trail, costs.BINANCE_SPOT),
                "taught": taught,
            }
            print(f"{symbol} {interval}: {len(trail)} trades", flush=True)
    return out


def text_page(pdf: PdfPages, title: str, blocks: list[tuple[str, str]]) -> None:
    """A page of (heading, body) text blocks."""
    fig = plt.figure(figsize=PAGE)
    fig.text(0.07, 0.93, title, fontsize=20, fontweight="bold", color=INK)
    y = 0.85
    for heading, body in blocks:
        if heading:
            fig.text(0.07, y, heading, fontsize=12.5, fontweight="bold", color=BLUE)
            y -= 0.035
        fig.text(0.07, y, body, fontsize=10.5, color=INK, va="top", linespacing=1.55)
        y -= 0.045 + 0.026 * (body.count("\n") + 1)
    pdf.savefig(fig)
    plt.close(fig)


def page_title(pdf: PdfPages, results: dict, start: str, end: str) -> None:
    n_total = sum(len(v["trail"]) for v in results.values())
    fig = plt.figure(figsize=PAGE)
    fig.text(0.5, 0.72, "Tamad-Strat", ha="center", fontsize=34, fontweight="bold", color=INK)
    fig.text(0.5, 0.65, "Quant validation report — the 3-candle reversal, Revelio-style",
             ha="center", fontsize=14, color=GRAY)
    fig.text(0.5, 0.585, f"Data: Binance spot {start} → {end} · BTC / ETH / SOL · "
             f"5m / 15m / 1h · {n_total:,} final-config trades",
             ha="center", fontsize=10.5, color=GRAY)
    fig.text(0.5, 0.55, "Train ≤ 2022 · Test 2023–2024 · HOLDOUT 2025+ still locked "
             "(sign-off pending on issue #18)", ha="center", fontsize=10.5, color=RED)
    verdict = (
        "1.  The naked pattern is a coin flip — 97,535 trades, win rate pinned at the 25% breakeven.\n"
        "2.  Every taught rule is inert or harmful: the ideal sweep, zone confluence stacking, HTF bias.\n"
        "3.  A real pre-cost edge exists, found by ablation: C1 ≥ 1×ATR + order-block zone + US session,\n"
        "     exited with a 1R trailing stop — 9/10 training picks confirmed on unseen 2023–24 data.\n"
        "4.  Spot taker costs destroy it: tight pattern stops make 0.22% round trips cost 0.2–1.4R per trade.\n"
        "     Every with-costs portfolio is negative. The 60% claim is not in the written rules."
    )
    fig.text(0.5, 0.42, "VERDICT", ha="center", fontsize=13, fontweight="bold", color=INK)
    fig.text(0.5, 0.38, verdict, ha="center", va="top", fontsize=11, color=INK, linespacing=1.8)
    pdf.savefig(fig)
    plt.close(fig)


def page_claim(pdf: PdfPages, results: dict) -> None:
    taught = pd.concat([v["taught"] for v in results.values()])
    trail = pd.concat([v["trail"] for v in results.values()])
    wr_taught = float((taught["r_multiple"] > 0).mean())
    wr_trail = float((trail["r_multiple"] > 0).mean())

    fig, ax = plt.subplots(figsize=PAGE)
    fig.subplots_adjust(top=0.82, bottom=0.3, left=0.09, right=0.95)
    fig.text(0.07, 0.92, "The claim vs the data", fontsize=20, fontweight="bold", color=INK)
    labels = ["Group claim\n(journaled, 1:3)", "Naked pattern\n(97,535 trades)",
              f"Final config, taught 1:3 exit\n({len(taught):,} trades)",
              f"Final config, trail_1R exit\n({len(trail):,} trades)"]
    values = [0.60, 0.250, wr_taught, wr_trail]
    colors = [GRAY, RED, BLUE, GREEN]
    bars = ax.bar(labels, [v * 100 for v in values], color=colors, width=0.55)
    ax.axhline(25, color=RED, linestyle="--", linewidth=1)
    ax.text(3.45, 26, "25% = breakeven at 1:3", color=RED, fontsize=9, ha="right")
    for bar, v in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, v * 100 + 1, f"{v:.1%}",
                ha="center", fontsize=11, fontweight="bold", color=INK)
    ax.set_ylabel("win rate")
    ax.set_ylim(0, 70)
    ax.spines[["top", "right"]].set_visible(False)
    fig.text(0.07, 0.16,
             "At 1:3 RR the breakeven win rate is 25%; 60% over 300 trades would mean +1.4R per trade "
             "(≈ +420R total), far outside the\nnoise band (95% CI ≈ ±5.5pp). Nothing mechanical in the "
             "written rules reproduces it. The trailing exit's higher win rate is not\ncomparable to the "
             "25% line — its payoff distribution differs (many small +0..1R wins). The 60% almost "
             "certainly lives in discretion\nor journaling, not in the rules as written.",
             fontsize=10, color=INK, va="top", linespacing=1.6)
    pdf.savefig(fig)
    plt.close(fig)


def page_ladder(pdf: PdfPages) -> None:
    rows = [
        ("V0  naked pattern", "all triplets, 1:3, no filters", "coin flip — WR = breakeven, PF ≈ 1.0", "docs/V0_RESULTS.md"),
        ("V1  ideal sweep", "C2 sweeps C1 low/high", "no lift; bottom of ablation ranks", "docs/PILLS_RESULTS.md"),
        ("V1  C1 ≥ 1×ATR", "climax first candle", "modest lift — first real clue", "docs/PILLS_RESULTS.md"),
        ("V2  as taught", "pattern at any of 5 zone types", "filters nothing (~70% qualify)", "docs/ZONES_RESULTS.md"),
        ("V2  confluence stack", "2+ zones agree", "flat: PF 0.98 / 1.01 / 1.00", "docs/ZONES_RESULTS.md"),
        ("V3  HTF bias", "4h/1d pattern gates LTF entries", "hurts at every bias age", "docs/V3_RESULTS.md"),
        ("Ablation  336 configs", "train-select → test-confirm", "survivor: C1≥1×ATR + OB + US session (9/10 held)", "docs/ABLATION_RESULTS.md"),
        ("Exits", "1:3 vs trail 1R / 0.5R vs ATR-trail", "trail_1R best OOS (test PF 1.44 vs 1.18)", "docs/EXITS_RESULTS.md"),
        ("Risk", "fixed vs high-watermark vs parity", "parity sizing holds OOS", "docs/RISK_RESULTS.md"),
        ("Costs", "0.22% notional round trip", "ALL portfolios negative; only ETH 1h ≈ breakeven", "docs/COSTS_RESULTS.md"),
    ]
    fig, ax = plt.subplots(figsize=PAGE)
    ax.axis("off")
    fig.text(0.07, 0.92, "The version ladder — every rule made to earn its place",
             fontsize=20, fontweight="bold", color=INK)
    table = ax.table(cellText=[list(r) for r in rows],
                     colLabels=["stage", "what was tested", "verdict", "source"],
                     colWidths=[0.18, 0.27, 0.38, 0.17],
                     cellLoc="left", loc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(9.5)
    table.scale(1, 1.75)
    for (r, c), cell in table.get_celld().items():
        cell.set_edgecolor("#e5e7eb")
        if r == 0:
            cell.set_facecolor(INK)
            cell.set_text_props(color="white", fontweight="bold")
        elif "survivor" in rows[r - 1][2] or "best OOS" in rows[r - 1][2] or "holds" in rows[r - 1][2]:
            cell.set_facecolor("#ecfdf5")
        elif "negative" in rows[r - 1][2] or "hurts" in rows[r - 1][2]:
            cell.set_facecolor("#fef2f2")
    pdf.savefig(fig)
    plt.close(fig)


def page_equity(pdf: PdfPages, results: dict, interval: str) -> None:
    fig, axes = plt.subplots(len(SYMBOLS), 1, figsize=PAGE, sharex=True)
    fig.subplots_adjust(top=0.86, hspace=0.35, left=0.08, right=0.95, bottom=0.09)
    fig.text(0.07, 0.93, f"Final configuration on {interval} — equity in R (flat 1R per trade)",
             fontsize=17, fontweight="bold", color=INK)
    for ax, symbol in zip(axes, SYMBOLS):
        r = results[(interval, symbol)]
        for trades, color, label in ((r["trail"], BLUE, "zero cost"),
                                     (r["trail_costs"], RED, "with Binance spot costs")):
            if trades.empty:
                continue
            curve = metrics.equity_curve(trades)
            ax.plot(curve.index, curve.values, color=color, linewidth=1.2, label=label)
        ax.axvline(TRAIN_END, color=GRAY, linestyle=":", linewidth=1)
        ax.axhline(0, color=GRAY, linewidth=0.6)
        m = metrics.summarize(r["trail"])
        mc = metrics.summarize(r["trail_costs"])
        ax.set_title(f"{symbol} — {m['trade_count']} trades · PF {m['profit_factor']:.2f} zero-cost "
                     f"→ {mc['profit_factor']:.2f} with costs", fontsize=10.5, loc="left", color=INK)
        ax.set_ylabel("net R", fontsize=9)
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(labelsize=8)
    axes[0].legend(fontsize=9, loc="upper left")
    axes[0].text(TRAIN_END, axes[0].get_ylim()[1], "  train | test", fontsize=8, color=GRAY, va="top")
    pdf.savefig(fig)
    plt.close(fig)


def page_costs(pdf: PdfPages, results: dict) -> None:
    fig, ax = plt.subplots(figsize=PAGE)
    fig.subplots_adjust(top=0.82, bottom=0.28, left=0.08, right=0.95)
    fig.text(0.07, 0.92, "The kill-shot: profit factor before vs after spot taker costs",
             fontsize=20, fontweight="bold", color=INK)
    labels, pf0, pf1, med = [], [], [], []
    for interval in INTERVALS:
        for symbol in SYMBOLS:
            r = results[(interval, symbol)]
            labels.append(f"{symbol[:3]}\n{interval}")
            pf0.append(metrics.summarize(r["trail"])["profit_factor"])
            pf1.append(metrics.summarize(r["trail_costs"])["profit_factor"])
            med.append(float(r["trail_costs"]["cost_r"].median()))
    x = range(len(labels))
    ax.bar([i - 0.2 for i in x], pf0, width=0.4, color=BLUE, label="zero cost")
    ax.bar([i + 0.2 for i in x], pf1, width=0.4, color=RED, label="with costs (0.22% round trip)")
    ax.axhline(1.0, color=INK, linestyle="--", linewidth=1)
    ax.text(len(labels) - 0.5, 1.05, "PF 1.0 = breakeven", fontsize=9, ha="right", color=INK)
    for i, m in enumerate(med):
        ax.text(i, max(pf0[i], pf1[i]) + 0.08, f"−{m:.2f}R\n/trade", ha="center", fontsize=8, color=GRAY)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("profit factor")
    ax.legend(fontsize=10)
    ax.spines[["top", "right"]].set_visible(False)
    fig.text(0.07, 0.14,
             "Why: risk per trade is the tiny distance to the pattern-extreme stop, but cost is charged on the "
             "full notional — notional/risk ratios of\n300–650× turn a 0.22% round trip into 0.7–1.4R on 5m. "
             "The pattern's defining feature (the tight stop) is exactly what makes it cost-doomed.\nA BNB fee "
             "discount (~23% off) changes no signs. Only ETH 1h survives at ≈ breakeven (PF 1.04).",
             fontsize=10, color=INK, va="top", linespacing=1.6)
    pdf.savefig(fig)
    plt.close(fig)


def page_portfolios(pdf: PdfPages, results: dict) -> None:
    fig, axes = plt.subplots(1, len(INTERVALS), figsize=PAGE)
    fig.subplots_adjust(top=0.8, bottom=0.18, left=0.07, right=0.97, wspace=0.25)
    fig.text(0.07, 0.92, "Parity portfolios on the TEST window (calibrated on training only)",
             fontsize=20, fontweight="bold", color=INK)
    fig.text(0.07, 0.87, "High-watermark sizing, per-asset risk bisected on training trades to a 20% "
             "standalone max drawdown, then applied unseen to 2023–2024. $10,000 start.",
             fontsize=10, color=GRAY)
    for ax, interval in zip(axes, INTERVALS):
        for key, color, label in (("trail", BLUE, "zero cost"), ("trail_costs", RED, "with costs")):
            per_asset = {}
            for symbol in SYMBOLS:
                trades = results[(interval, symbol)][key]
                exit_t = pd.to_datetime(trades["exit_time"], utc=True)
                train, test = trades[exit_t < TRAIN_END], trades[exit_t >= TRAIN_END]
                if len(train) < 20 or len(test) == 0:
                    continue
                pct = sizing.dd_parity_pct(train, 0.20, sizer=sizing.HighWatermark)
                per_asset[symbol] = (test, sizing.HighWatermark(pct))
            if not per_asset:
                continue
            curve, _ = sizing.portfolio_curve(per_asset)
            ret = curve.iloc[-1] / 10_000 - 1 if len(curve) else 0.0
            ax.plot(curve.index, curve.values, color=color, linewidth=1.3,
                    label=f"{label}: {ret:+.0%}")
        ax.axhline(10_000, color=GRAY, linewidth=0.6, linestyle=":")
        ax.set_yscale("log")
        ax.set_title(interval, fontsize=13, fontweight="bold", color=INK)
        ax.legend(fontsize=8.5)
        ax.tick_params(labelsize=7.5)
        ax.spines[["top", "right"]].set_visible(False)
    fig.text(0.07, 0.06, "Log scale. The blue curves are the pre-cost edge (real, confirmed OOS). "
             "The red curves are what a spot taker account would actually experience.",
             fontsize=10, color=INK)
    pdf.savefig(fig)
    plt.close(fig)


def page_next(pdf: PdfPages) -> None:
    text_page(pdf, "What was optimized — and what could still move the needle", [
        ("Optimization already done (the Revelio ladder)",
         "Pills one at a time (sweep, C1 size) · five zone families alone and stacked · HTF bias at every age ·\n"
         "336-config ablation grid selected on training and confirmed on unseen 2023–24 · four exit structures ·\n"
         "three sizing schemes with drawdown-parity calibration · costs applied last. Result: PF ≈ 1.0 → 1.44 (test,\n"
         "pre-cost). The strategy that survived shares only the 3-candle trigger with the one taught."),
        ("The binding constraint is execution cost, not entry quality",
         "Further entry filters cannot fix a strategy paying 0.2–1.4R per trade in fees. The levers that remain:"),
        ("1. Wider stops",
         "Stop at pattern-extreme minus an ATR buffer (or the zone edge) shrinks the notional/risk ratio and\n"
         "directly divides the cost in R. Test whether the pre-cost edge survives the wider stop."),
        ("2. Maker / futures execution",
         "Binance futures maker is 0.02%/side (~10× cheaper). Entry as a limit at C3 close with conservative\n"
         "fill modeling (require trade-through). Different strategy — fills are uncertain — but the only path\n"
         "that plausibly flips the after-cost sign on low timeframes."),
        ("3. Trade where costs are survivable",
         "1h already pays only ~0.2R/trade; 4h as a traded timeframe (not just bias) is untested. Widen the\n"
         "asset basket at 1h+ to rebuild trade count."),
        ("4. Regime and robustness work",
         "Volatility-regime and day-of-week clues (the US-session find suggests more structure) · parameter-\n"
         "neighborhood gradients around the survivor · walk-forward instead of a single split."),
        ("The gate",
         "Each new optimization round spends the test set. Run the improvement round first, then unlock the\n"
         "2025+ holdout ONCE for the final verdict — sign-off on issue #18."),
    ])


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--start", default="2017-08-01")
    p.add_argument("--end", default="2025-01-01")
    p.add_argument("--out", default="docs/report/tamad-strat-report.pdf")
    args = p.parse_args()

    results = compute(args.start, args.end)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with PdfPages(out) as pdf:
        page_title(pdf, results, args.start, args.end)
        page_claim(pdf, results)
        page_ladder(pdf)
        for interval in INTERVALS:
            page_equity(pdf, results, interval)
        page_costs(pdf, results)
        page_portfolios(pdf, results)
        page_next(pdf)
    print(f"report written to {out}")


if __name__ == "__main__":
    main()
