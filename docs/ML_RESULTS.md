# ML layer (#19) — random forest as a trade filter

Revelio Phase 7, run on the final configuration's own trades (survivor pills + trail_1R, pooled BTC/ETH/SOL per interval) and on a sanity pool (C1≥1×ATR only, taught 1:3 exit). Forest: 300 trees, min leaf 30, seed 42, trained ONLY on trades exiting ≤ 2022-12-31. 28 pre-trade features (pattern anatomy in ATR units, stop width, volatility regime, session/day, trend location, RSI, zone membership). Feature builder is fixture-proven lookahead-free. Full outputs: `results/ml/candidates_*.json`, `results/ml/confirmed_*.json`.

Pipeline: importances → candidate thresholds (training quantiles only) → **market-logic veto** → single test-window touch (2023–24) with and without costs.

## ⚠ Reliability flag: the rediscovery check FAILED

The acceptance criteria require the sanity pool's forest to re-find the filters ablation already proved (OB zone, US session). It did not — `in_ob` ranked 23–25, `hour` 17–18, `confluence_count` ~20 of 31 features, in every study.

Two readings, both recorded:

1. **Metric artifact (the likely dominant cause).** Impurity-based RF importance is structurally biased toward continuous features: a binary like `in_ob` can split once; `vol_ratio` offers hundreds of candidate splits and soaks up impurity credit. The proven filters are binary/coarse, the features that outranked them are all continuous — exactly the pattern this bias predicts.
2. **Signal size.** The OB/US lift is a ~1pp win-rate shift on a minority of setups — small against noisy continuous features when the target is per-trade win/loss.

**Consequence:** the importance *ranking* is NOT treated as evidence of where the edge lives. It was used only to shortlist candidates, every one of which then had to pass the veto and the test gate on its own. A permutation-importance rerun is the obvious methodological upgrade if this layer is ever revisited.

## Candidates and the veto pass

Training-window candidates per pool are in `results/ml/candidates_*.json`. Veto decisions (before any test data was touched):

| Candidate | Appears in | Decision | Reason |
|---|---|---|---|
| `c3_front_wick_atr <=` (clean hold candle) | 5 of 6 studies, always `<=` | **CONFIRM** | A long counter-probe on the signal candle means the level is being contested; a clean hold is a decisive reversal. Direction consistent everywhere. |
| `risk_pct <=` (tight 3-bar structure) | all 3 final pools, always `<=` | **CONFIRM** | Compression → coiled structure; also directly tests the cost paradox (tight stops are what costs punish). |
| `c1_atr_mult >=` (stronger climax) | 15m + 1h final, 1h sanity | **CONFIRM** | The proven pill, deeper — larger capitulation candle. |
| `vol_ratio` | 5 studies, direction FLIPS (5m final `>=`, all others `<=`) | **VETO** | No single mechanism can explain both directions. Breadth-over-spikes rule. |
| `c3_range_atr` | 5 studies, direction FLIPS (5m/15m `>=`, 1h + sanities `<=`) | **VETO** | Same flip problem. |
| `dow >= 2` (1h) | one study | **VETO** | Weekday numerology — the canonical "works when it rains". |
| `ret20_atr >=`, `dist_lo20/hi20`, `atr_pct <=`, `ema*`, `rsi14` | one pool each | parked | Single-pool appearances, no breadth; not worth spending the test set on. |

## Test confirmation (2023–24, final pool, pooled assets)

| Interval | Rule | Retention | Test PF base → filtered | With costs base → filtered | Verdict |
|---|---|---|---|---|---|
| 5m | `c3_front_wick_atr <= 0.083` | 28% | 1.590 → 1.657 | 0.059 → 0.021 | weak confirm pre-cost (+4%); train PF 5.89 was mostly overfit |
| 5m | `risk_pct <= 0.117` | 46% | 1.590 → **1.952** | 0.059 → 0.020 | **confirms pre-cost (+23%)**; worsens costs |
| 15m | `risk_pct <= 0.234` | 38% | 1.386 → 1.553 | 0.294 → 0.119 | confirms pre-cost (+12%); worsens costs |
| 15m | `c3_front_wick_atr <= 0.157` | 35% | 1.386 → 1.505 | 0.294 → 0.229 | confirms pre-cost (+9%) |
| 15m | `c1_atr_mult >= 1.27` | 52% | 1.386 → 1.537 | 0.294 → 0.354 | confirms pre-cost (+11%); mildly helps after-cost |
| 1h | `c3_front_wick_atr <= 0.150` | 31% | 1.308 → **1.610** | 0.730 → **0.879** | **confirms (+23%), and the only rule that improves the after-cost PF** |
| 1h | `c1_atr_mult >= 1.72` | 23% | 1.308 → 0.909 | 0.730 → 0.544 | **DIES on test** — train PF 3.10 was an extreme-threshold overfit; the gate worked |
| 1h | `risk_pct <= 0.843` | 58% | 1.308 → 1.506 | 0.730 → 0.708 | confirms pre-cost (+15%) |

## Long/short asymmetry (the TJR-survivor analog)

No survivor. Per asset × side, train and test (in `results/ml/confirmed_*.json`): both sides carry edge on BTC/ETH at 5m; the strongest cells (ETH 1h shorts test PF 3.00, n=36) are too small for a claim; SOL is the weakest asset on both sides. Unlike TJR's long-only indices, this pattern's edge is roughly side-symmetric — consistent with a genuine reversal mechanism rather than a trend proxy.

## What the layer actually found

1. **The edge concentrates in the tightest structures.** `risk_pct <=` confirmed out-of-sample on all three intervals (+12–23% PF). This is the project's most consequential negative result: **the pre-cost edge and the cost-doom are the same phenomenon.** Tight three-bar patterns are both where the alpha lives and what makes 0.22% round trips cost 0.7–1.4R. The "just widen the stops" fix would trade away edge in proportion to the cost it saves — measured, not assumed.
2. **A clean hold candle is a real refinement.** `c3_front_wick_atr <=` confirmed on all three intervals pre-cost, and on 1h it is the only rule that also moved the after-cost PF the right way (0.73 → 0.88). Still below breakeven — it does not change the venue verdict.
3. **The costs verdict stands.** No filter, alone or implied stacking, crosses PF 1.0 after spot-taker costs. The path remains execution (maker/futures), not entry selection.
4. **The gates earned their keep.** One rule died on test (1h `c1_atr_mult >= 1.72`), two families died at the veto for direction-flipping, and the importance ranking itself was caught and flagged by the rediscovery check.
