# Tamad-Strat — Strategy Specification

Source: rules as taught in the Discord group (captured 2026-07-18) + pattern sketch (`pattern-sketch.png`).

## 1. Overview

- **Type:** 3-candle reversal pattern at significant levels
- **Timeframes:** 1h, 15m, 5m (role of each TF to be clarified — independent scans vs. multi-TF interaction)
- **Markets:** TBD (what the group trades it on)
- **Direction:** both long and short (mirrored rules)

## 2. Rules as taught (verbatim intent)

1. Color pattern: **red-green-red = bullish setup**, **green-red-green = bearish setup**.
2. Detected on 1h, 15m, and 5m timeframes.
3. Bullish rules (left to right, C1 → C2 → C3, C3 = present candle):
   - a. C1 red, C2 green, C3 red.
   - b. *Ideal*: the green C2 **sweeps** C1 (deferred — to be added as a parameter later).
   - c. C3 must **never close below C2's open** (wick/sweep below is allowed).
   - d. **Entry the moment C3 closes.**
   - e. The pattern must fall in a **significant area** from a previous move: (1) recent swing, (2) FVG, (3) order block, (4) RSI divergence, (5) support/resistance.
4. Bearish setup is the exact mirror.

## 3. Formalized (codable) definitions

Candle color: green ⇔ `close > open`; red ⇔ `close < open`. (Doji `close == open`: treatment undecided — see open questions.)

**Bullish setup at bar t** (C1 = t−2, C2 = t−1, C3 = t):

| Condition | Rule |
|---|---|
| Colors | C1 red, C2 green, C3 red |
| Hold rule | `C3.close >= C2.open` (C3.low may dip below — "can sweep") |
| Ideal sweep (parameter, off in V0) | `C2.low < C1.low` |
| Context | pattern located at a significant area after a preceding down move |
| Entry | long at C3 close (in backtest: fill at open of bar t+1) |

**Bearish setup at bar t:** C1 green, C2 red, C3 green; `C3.close <= C2.open` (wick above allowed); ideal sweep `C2.high > C1.high`; preceding up move into a significant area; short at C3 close.

Market-structure reading (bullish): C1 = selling climax into the level, C2 = reclaim (ideally after sweeping C1's low = liquidity grab), C3 = weak pullback that holds above the reclaim origin → entry on the pullback close, i.e. a higher-low retest entered at a discount instead of chasing C2.

## 4. Deferred parameters (explicitly postponed by the group)

- Sweep condition (rule b): `C2.low < C1.low` (bull) / `C2.high > C1.high` (bear) — test as on/off filter and measure marginal contribution.

## 5. Assumptions disguised as rules — must be parameterized before coding

Every item below changes which trades fire. Each needs an explicit definition + value (or a small grid to test).

### Pattern geometry
- **Doji handling** — is `close == open` red, green, or pattern-invalidating?
- **Candle sizes** — sketch shows C1 large (climax) and C3 small. Is there any minimum/relative size rule (e.g., C1 body ≥ k×ATR, C3 body < C2 body), or is size irrelevant?
- **C2 vs C1 relationship** — must C2 close back inside/above C1's body (reclaim), or is any green candle fine?
- **C3 position** — any constraint vs C1/C2 ranges beyond rule c (e.g., C3 must stay inside C2's range)?

### Context / trend
- **"Previous move"** — how is the preceding down/up move defined? Lookback bars, minimum magnitude (ATR multiple / % move), swing count?

### Significant areas (each is its own sub-model)
- **Recent swing:** pivot definition (bars left/right), recency window, proximity tolerance to the level.
- **FVG:** 3-candle gap definition, minimum gap size, filled/unfilled status, same-TF or higher-TF gaps.
- **Order block:** which definition (last opposite candle before displacement?), displacement threshold, freshness/mitigation.
- **RSI divergence:** RSI period, pivot detection on price and RSI, regular vs hidden, max lookback between pivots.
- **Support/Resistance:** how levels are constructed (prior swing highs/lows? touch count?), zone width.
- **"Falls in" tolerance:** which part of the pattern must touch the zone (C2 wick? C3 close? any candle?), and how close counts as "in".
- **Confluence logic:** is ONE area enough? Do multiple areas make a setup "better"? (Testable claim — in the TJR analysis, high-confluence setups were the *worst*. Measure, don't assume.)

### Execution / management (currently unspecified — biggest gap)
- **Stop loss:** not defined. Candidates to test: below C2 low / pattern low / sweep wick, ATR-based.
- **Take profit:** not defined. What does the group actually use? (Fixed R? partials? trail?) Exits get their own exploration phase regardless.
- **Risk per trade, max concurrent positions, session/volatility filters:** not defined.
- **Multi-TF role:** are 1h/15m/5m three independent strategies, or does a higher TF supply the zones for a lower-TF trigger?

## 6. Planned version ladder (marginal-contribution testing)

- **V0** — naked pattern only (colors + hold rule + entry), simple fixed exit grid, no confluence. Baseline: does the pattern alone have any edge?
- **V0s** — V0 + sweep parameter (rule b) on/off.
- **V1.x** — each significant-area filter added **one at a time** (V1.swing, V1.fvg, V1.ob, V1.div, V1.sr) to measure each filter's marginal contribution.
- **V2** — combined confluence as taught in the group.
- **Then:** exit-structure exploration → asset/TF selection on return/maxDD and stability → optional ML trade-quality filter (train/test split + market-logic veto) → costs → final untouched holdout validation.

Steelman-first protocol: initial falsification runs use in-sample-optimized parameters and zero transaction costs (best case on purpose). A final time slice (target: last ~18–24 months of data) stays untouched until all decisions are frozen.
