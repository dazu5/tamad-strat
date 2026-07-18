# Tamad-Strat — Strategy Specification

Source: rules as taught in the Discord group (captured 2026-07-18, exits/markets/multi-TF clarified same day) + pattern sketch (`pattern-sketch.png`).

## 1. Overview

- **Type:** 3-candle reversal pattern at significant levels
- **Execution timeframes:** 5m, 15m, 1h — trade the pattern on the TF where it appears
- **Higher timeframes (4h, 1d):** not traded directly; a pattern there acts as directional **bias** for a lower-TF setup with an extended TP (see §4)
- **Markets:** mainly crypto (basket TBD); forex as secondary/robustness set
- **Direction:** both long and short (mirrored rules)

## 1b. Claimed performance (the hypothesis under test)

The group reports **60% win rate at 1:3 RR**, tested at a consistent **$1 flat risk per trade** (good instinct — flat risk isolates expectancy from compounding).

Phase-0 Monte Carlo verdict (2026-07-18): 60% @ 1:3 = **+1.40R expectancy per trade** (breakeven is 25%). If true, compounding at just 1% risk yields ~31× per YEAR at 250 trades/yr with a median max drawdown of ~8% — a world-historic edge; a losing decade would sit 25+ sigma below the mean, i.e. impossible. Small-sample context: a manual test of ~50 trades has a ±13.6-point CI around a measured 60%, and hindsight bias in manual chart-counting inflates win rates further. Treat 60% as an upper anchor, not an expectation; the strategy is still profitable at anything above ~25% WR (plus costs), and a true 35–40% at 1:3 would already be excellent.

## 2. Rules as taught

1. Color pattern: **red-green-red = bullish setup**, **green-red-green = bearish setup**.
2. Bullish rules (left to right, C1 → C2 → C3, C3 = present candle):
   - a. C1 red, C2 green, C3 red.
   - b. *Ideal*: the green C2 **sweeps** C1 (deferred — parameter to add later).
   - c. C3 must **never close below C2's open** (wick/sweep below is allowed).
   - d. **Entry the moment C3 closes.**
   - e. The pattern must fall in a **significant area**: (1) recent swing, (2) FVG, (3) order block, (4) RSI divergence, (5) support/resistance. There is **no separate trend precondition** — the significant area IS the context.
3. **Stop loss:** the lowest price the 3-candle pattern tapped (wicks included).
4. **Take profit:** fixed **1:3 RR**, full position close (no partials).
5. Candle size doesn't strictly matter, but the preferred starting variant requires **C1 to be a much larger candle** (climax); drop the size filter if it starves the trade count.
6. Bearish setup is the exact mirror.

## 3. Formalized (codable) definitions

Candle color: green ⇔ `close > open`; red ⇔ `close < open`. (Doji `close == open`: treatment undecided — see §5.)

**Bullish setup at bar t** (C1 = t−2, C2 = t−1, C3 = t):

| Condition | Rule |
|---|---|
| Colors | C1 red, C2 green, C3 red |
| Hold rule | `C3.close >= C2.open` (C3.low may dip below — "can sweep") |
| Ideal sweep (parameter, off in V0) | `C2.low < C1.low` |
| C1 size filter (parameter, on at start) | C1 body "much larger" — proposed: `C1.body >= k × ATR(14)`, k in a small grid; drop if trade count collapses |
| Context | pattern located at ≥1 significant area (§5) |
| Entry | long at C3 close (in backtest: fill at open of bar t+1) |
| Stop loss | `SL = min(C1.low, C2.low, C3.low)` |
| Take profit | `R = entry − SL`; `TP = entry + 3R`, full close |

**Bearish setup at bar t:** C1 green, C2 red, C3 green; `C3.close <= C2.open` (wick above allowed); ideal sweep `C2.high > C1.high`; C1 size filter mirrored; short at C3 close; `SL = max(C1.high, C2.high, C3.high)`; `TP = entry − 3R`.

Payoff note: fixed 1:3 full-close ⇒ **breakeven win rate = 25%** before costs. That's the bar the pattern must clear; Revelio's partial-scaling pathology does not apply here, but low hit rates on 3R are expected — exit exploration stays on the roadmap.

Market-structure reading (bullish): C1 = selling climax into the level, C2 = reclaim (ideally after sweeping C1's low = liquidity grab), C3 = weak pullback that holds above the reclaim origin → entry on the pullback close, i.e. a higher-low retest entered at a discount instead of chasing C2.

## 4. Multi-timeframe usage

- **Same-TF mode (core):** 5m, 15m, 1h are each scanned and traded independently — spot it on a TF, trade it on that TF.
- **HTF-bias mode (variant):** a valid pattern on 4h/1d is not traded directly; it sets directional bias. Find a same-direction setup on 5m/15m/1h; SL from the lower-TF pattern as usual, but **TP extends to the higher-TF target** (the 4h/1d pattern's 3R level) → much larger effective RR on lower-TF risk.
- Hypothesis to test explicitly: Revelio found HTF bias *hurts* when the TF distance is too large (weekly vs 5m). 4h→5m spans ~48×; 1d→1h ~24×. Measure, don't assume.

## 5. Remaining parameterization work (no longer user questions — build decisions)

### Pattern geometry
- **Doji handling** — is `close == open` red, green, or pattern-invalidating? (Proposed: invalidating; test sensitivity.)
- **C1 "much larger"** — exact k×ATR threshold (grid), and the trade-count floor below which we drop the filter.

### Significant areas (each is its own sub-model)
- **Recent swing:** pivot definition (bars left/right), recency window, proximity tolerance.
- **FVG:** 3-candle gap definition, minimum gap size, filled/unfilled status, same-TF vs higher-TF gaps.
- **Order block:** definition (last opposite candle before displacement?), displacement threshold, freshness/mitigation.
- **RSI divergence:** RSI period, pivot detection on price and RSI, regular vs hidden, max lookback.
- **Support/Resistance:** level construction (prior swing highs/lows? touch count?), zone width.
- **"Falls in" tolerance:** which part of the pattern must touch the zone, and how close counts as "in".
- **Confluence logic:** is ONE area enough? Do multiple areas help? (Testable — in the TJR analysis, high-confluence setups were the *worst*.)

### Portfolio / execution defaults (to fix before V0)
- Crypto basket (e.g., BTC, ETH + 1–3 liquid alts) and forex robustness pairs.
- Risk per trade (default 1% of equity, per Revelio baseline), max concurrent positions per asset, session/volatility filters (crypto trades 24/7 — likely none, but test).
- Data source, history depth (target ≥8–10 years where the asset existed), fee/spread model per venue (applied only in the final phase).

## 6. Planned version ladder (marginal-contribution testing)

- **V0** — naked pattern (colors + hold rule + C1 size filter) + taught exit (SL pattern low, fixed 1:3), no confluence. Baseline: does the pattern alone have edge?
- **V0s** — V0 + sweep parameter (rule b) on/off.
- **V1.x** — each significant-area filter added **one at a time** (V1.swing, V1.fvg, V1.ob, V1.div, V1.sr) to measure marginal contribution.
- **V2** — combined confluence as taught in the group.
- **V3** — HTF-bias mode (4h/1d bias + LTF trigger + extended TP).
- **Then:** exit-structure exploration (taught 1:3 vs trailing vs alternatives) → asset/TF selection on return/maxDD and stability → optional ML trade-quality filter (train/test split + market-logic veto) → costs → final untouched holdout validation.

Steelman-first protocol: initial falsification runs use in-sample-optimized parameters and zero transaction costs (best case on purpose). A final time slice (target: last ~18–24 months of data) stays untouched until all decisions are frozen.
