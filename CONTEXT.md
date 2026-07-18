# Tamad-Strat — Domain Glossary

Use these terms exactly in issue titles, test names, interfaces, and reports. Definitions defer to `docs/STRATEGY_SPEC.md` where fuller detail exists.

## The pattern

- **Tamad-Strat** — the 3-candle reversal strategy under validation: red-green-red = bullish setup, green-red-green = bearish setup.
- **C1 / C2 / C3** — the three candles of a setup, oldest to newest; C3 is the signal candle whose close triggers entry.
- **Red / green / doji** — close below / above / equal to open. A doji anywhere in the triplet invalidates the pattern.
- **Hold rule** — bullish: C3 close ≥ C2 open (wick below allowed); bearish mirror. The pattern's invalidation condition.
- **Ideal sweep** — C2's wick takes C1's extreme (bull: C2 low < C1 low). A pattern pill, off in V0.
- **Pattern extreme** — the lowest (bull) / highest (bear) price the three candles tapped, wicks included. The stop-loss level.
- **Taught exit** — SL at the pattern extreme, TP at exactly 3× risk, full close, no management.

## Zones and context

- **Significant area (zone)** — a price region that qualifies a setup: recent swing, FVG, order block, RSI divergence, or S/R. Each is a detector behind the shared zone interface.
- **Confluence** — the set (and count) of zones a setup falls in, under an explicit tolerance. "More confluence = better" is a claim under test, not an assumption.
- **Same-TF mode** — pattern spotted and traded on the same timeframe (5m, 15m, or 1h).
- **HTF-bias mode (V3)** — a 4h/1d pattern sets direction only; a lower-TF setup triggers; TP extends to the higher timeframe's 3R target.

## Experiment vocabulary

- **Version ladder** — V0 (naked pattern) → V0s (+ sweep) → V1.x (one zone type each) → V2 (full confluence as taught) → V3 (HTF-bias). Measures marginal contribution per rule.
- **Pill** — any independently togglable rule (sweep, C1 size, each zone type, session filter, HTF bias), after the ablation metaphor.
- **Ablation** — enumerating pill combinations and ranking by profit factor; every rule must earn its place.
- **Steelman protocol** — falsification runs use best-case settings (in-sample parameters, zero costs) so a failure is conclusive.
- **Walking skeleton** — the first thin end-to-end path (issue #2): data → detection → simulation → metrics on one market.
- **Run config / config hash** — the declarative description of one experiment; the hash keys the results store and guarantees reproducibility.
- **Results store** — persisted record of every run (config, trade list, metrics), including negative results.
- **Training / test / holdout** — through 2022-12-31 / 2023-01-01–2024-12-31 / 2025-01-01–present. Selection only on training; test confirms; holdout untouched until sign-off on #18 (the **holdout lock**).

## Metrics

- **Profit factor (PF)** — gross profit ÷ gross loss; the quality metric used for ranking. Trade count is quantity; return is a consequence.
- **Expectancy (R)** — mean R-multiple per trade; R = entry-to-SL distance. At the taught 1:3 exit, **breakeven win rate = 25%**.
- **Return / maxDD** — the risk-adjusted selection metric for portfolio decisions.
- **Small-sample flag** — a slice with too few trades to support conclusions; flagged and excluded from verdicts.
- **High watermark sizing** — risk a % of peak equity rather than current equity (counters volatility drag).
- **Drawdown parity** — per-asset risk set so each asset in isolation targets the same max drawdown.

## The claim under test

**60% win rate at 1:3 RR over 300+ journaled trades** (flat $1 risk) — the Discord group's measured baseline (spec §1b). Implies ~+1.4R expectancy; V0's job is to measure how much of it lives in the mechanical rules.
