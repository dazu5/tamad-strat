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
- [x] Zones #8–#10: OB best single zone; V2-as-taught filters nothing; confluence stacking flat — `docs/ZONES_RESULTS.md`
- [x] HTF-bias #13: hurts at every distance — `docs/V3_RESULTS.md`
- [x] Ablation #14: survivor = C1≥1×ATR + OB zone + US session; 9/10 picks confirmed on test — `docs/ABLATION_RESULTS.md`
- [x] Exits #15: trail_1R chosen (best OOS) — `docs/EXITS_RESULTS.md`, `docs/EXITS_TEST_RESULTS.md`
- [x] Forex #16: taught exit fails on FX; partial trailing transfer — `docs/FOREX_RESULTS.md`
- [x] Risk #17: parity sizing holds OOS — `docs/RISK_RESULTS.md`
- [x] Costs (#18 AFK part): **costs annihilate every timeframe** (median 0.2–1.4 R/trade) — `docs/COSTS_RESULTS.md`
- [x] ML layer #19 (Revelio Phase 7): rediscovery check tripped (impurity bias, flagged); OOS survivors = tight-stop + clean-C3 refinements pre-cost; **the edge lives in the tightest structures — the cost-doom is intrinsic**; costs verdict unchanged — `docs/ML_RESULTS.md`
- [x] Official doc codified #20: rules match our formalization; doc claims 52%@2RR / 46%@3RR (not the folk 60%) — `docs/OFFICIAL_DOC.md`
- [x] **V4 as-documented audit #22: the continuation reframe is CONFIRMED out-of-sample** — the pill swept the training top-10 and held on test (best PF 1.121, n=1,145; on/off ablation 1.121 vs 1.064); doc claims measured AT breakeven (25.2% vs claimed 46%); both-wick rule and 2RR fail OOS; 4h book positive after costs on both venues (PF 1.39–1.64, n=39 — small) — `docs/V4_RESULTS.md`
- [ ] **⛔ AWAITING HOLDOUT SIGN-OFF on issue #18** — the one-shot 2025+ validation runs only after the maintainer's recorded approval
