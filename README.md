# Tamad-Strat

A simple 3-candle reversal strategy (red-green-red bullish / green-red-green bearish) traded in our Discord group, being put through a full quant validation pipeline:

**codify → falsify (steelman backtest) → follow the clues → optimize → validate out-of-sample**

Methodology modeled on Revelio Trading's TJR strategy analysis, with stricter out-of-sample discipline (final untouched holdout period, walk-forward where feasible).

## Project layout

- `docs/STRATEGY_SPEC.md` — the strategy rules as taught, formalized definitions, deferred parameters, and open questions
- `docs/METHODOLOGY.md` — the validation process, distilled from four Revelio Trading case studies
- `docs/pattern-sketch.png` — original pattern sketch (bullish setup after a down move)

PRD: [issue #1](https://github.com/dazu5/tamad-strat/issues/1) — eight modules (data, pattern, zones, engine, metrics, experiments, risk, dashboard), custom event-driven Python engine, full test coverage.

Implementation plan: [issues #2–#18](https://github.com/dazu5/tamad-strat/issues) — 17 tracer-bullet vertical slices in dependency order, from the walking skeleton (#2) to the HITL holdout unlock + final verdict (#18). Crypto basket: BTC, ETH, SOL.

Claimed baseline under test: 60% win rate at 1:3 RR over 300+ journaled trades (see spec §1b).

## Status

- [x] Rules captured, ambiguities catalogued
- [x] Open questions resolved (exits, markets, C1 size, multi-TF roles)
- [x] Research: methodology distilled from all four Revelio videos
- [x] PRD written and filed as issue #1
- [x] PRD broken into 17 tracer-bullet issues (#2–#18)
- [x] Walking skeleton, claim checker, data backbone, experiment runner (#2–#5)
- [x] **V0 verdict (#6): the naked pattern has no edge** — 97,535 trades, WR pinned at the 25% breakeven, `docs/V0_RESULTS.md`
- [x] Pattern pills (#7): sweep adds nothing; C1≥1×ATR modest lift — `docs/PILLS_RESULTS.md`
- [x] Dashboard browse + launch (#11, #12)
- [ ] Zone experiments #8–#10 (campaign running), HTF-bias #13 (campaign running)
- [ ] Ablation #14 → exits #15 → forex #16 → risk #17 → costs + holdout sign-off #18
