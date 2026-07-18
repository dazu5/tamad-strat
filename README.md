# Tamad-Strat

A simple 3-candle reversal strategy (red-green-red bullish / green-red-green bearish) traded in our Discord group, being put through a full quant validation pipeline:

**codify → falsify (steelman backtest) → follow the clues → optimize → validate out-of-sample**

Methodology modeled on Revelio Trading's TJR strategy analysis, with stricter out-of-sample discipline (final untouched holdout period, walk-forward where feasible).

## Project layout

- `docs/STRATEGY_SPEC.md` — the strategy rules as taught, formalized definitions, deferred parameters, and open questions
- `docs/pattern-sketch.png` — original pattern sketch (bullish setup after a down move)

## Status

- [x] Rules captured, ambiguities catalogued
- [ ] Open questions resolved (exits, prior-trend definition, zone definitions, markets)
- [ ] Research: best backtesting/optimization approach
- [ ] Data acquisition
- [ ] V0 baseline backtest (naked pattern)
- [ ] Version ladder tests
- [ ] Exit-structure exploration
- [ ] Final out-of-sample validation
