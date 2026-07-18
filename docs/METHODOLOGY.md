# Quant Validation Methodology

Distilled from four Revelio Trading case studies:
- **TJR / smart-money** — falsification (`4uqeKO6KcJk`) + improvement (`8FJbpSY0R3o`)
- **FX Alex G / Set-and-Forget** — falsification (`nFIJ0z8_01w`) + improvement (`HzVSi9ux1NU`)

This file is the process reference for the Tamad-Strat project. Strategy rules live in `STRATEGY_SPEC.md`. Exact on-screen tables and rule cards (frame-extracted; the numbers the narration never spoke) live in `REVELIO_REFERENCE.md`.

## Phase 0 — Sanity-check the claim (before writing any code)

If the strategy comes with performance claims (win rate, RR, returns), run a **Monte Carlo simulation** of those claims first. Claimed 65% WR at 1:4 RR compounds $10k into trillions in a decade — a claim that implausible sets the interpretive frame for everything after. Cheap, fast, and quantifies the bar.

## Phase 1 — Codify

- Extract rules from the source exactly as taught. Contradictions get resolved by explicit decision; every vague concept ("swing", "zone", "much larger") becomes a named parameter.
- The codified strategy must be able to LOSE — if rules can be reinterpreted after the fact, the edge is unfalsifiable and untestable.

## Phase 2 — Falsify with a steelman

- **Version ladder:** minimal core → each component added separately → full framework. Measures each rule's marginal contribution instead of judging the strategy as a blob.
- **Best-case bias on purpose:** in-sample-optimized parameters, zero transaction costs. If it fails with every advantage, the verdict is conclusive and unarguable.
- **Broad matrix:** all assets × timeframes × ~10 years. A few cherry-picked examples create the illusion of an edge.
- Compare against doing nothing (buy-and-hold benchmark) and against the claim.

## Phase 3 — Diagnose (clues, not just verdicts)

- Slice results by every dimension: asset, timeframe, session, month, entry type, TP level hit rates.
- Do the **R-multiple math** on the trade-management structure (partial TPs can silently cap the payoff; full-close 1:3 needs 25% WR to break even).
- Explain failures mechanistically (e.g. weekly bias vs 5m execution = timeframe distance too large).
- **Overfitting refusals:** never drop the worst performers without a market-logic reason; ignore slices with too few trades to be statistically meaningful (a 37-trade pattern "barely moves the needle").

## Phase 4 — Repair and rebuild

- **Logic-first repairs:** replace obviously-broken parameterizations (fixed pip widths → ATR-scaled; age-based level expiry → breaks-vs-rejections). Then TEST them — and if the data says the "more logical" version is worse, keep the original. Logic proposes, data disposes.
- **Ablation (the core rebuild tool):** every rule is a pill. Enumerate on/off (or multi-setting) combinations of ALL rules — the Set-and-Forget study ran 200 configurations — and rank by **profit factor** (quality metric; trade count = quantity, return = consequence), computed on the **portfolio frame at flat risk with costs excluded** during the search. The winner there had *everything off* (PF 1.196): complexity was the disease. Robustness signal: the all-off variant ranked high across EVERY session setting (#1 overlap, #5 asia, #16 all), not just in its winning slot — a real edge shows up everywhere, an artifact shows up once.
- **Selection discipline:** select configurations on a TRAINING period only (2016–2021), keep a locked TEST period (2022–2026) — with 200 configs, some win by pure luck. Confirm the chosen configs hold on the test set.
- **Market-logic veto on selection:** Asia session ranked #2 in training and was still rejected (lowest liquidity — fragile edge).

## Phase 5 — Robustness checks (overfitting detectors)

- **Breadth over peaks:** an edge should be profitable across MOST timeframes and MOST assets (14/16 pairs), not carried by one or two lucky slices. One spectacular slice + many negative ones = overfitting signature.
- **Gradients over cliffs:** monotonic patterns (PF improving smoothly as TF decreases) indicate structure; isolated spikes indicate luck.
- **Stability preference:** prefer the stable configuration over the peak-return one; prefer higher TFs where costs bite less.
- **Pre-commitment:** where a choice is debatable, fix it BEFORE looking at results (Revelio chose GBPUSD's 1:1 exit blind).

## Phase 6 — Exits, risk, portfolio

- Exits deserve their own exploration phase (12 structures tested in the TJR rebuild: a fixed-RR ladder 0.5R–3R, full-close at each TP level, the original partials with and without break-even, and trailing; trailing 1R steps beat partials on every trending asset, lost only on mean-reverting GBPUSD). Exits matter as much as entries.
- **Volatility drag:** −50% needs +100% to recover. Counter with **high-watermark sizing** (risk % of peak equity, not current) — tested at 2% / 1% HWM / 0.5% HWM; final pick is drawdown tolerance, i.e. personal preference, NOT return optimization.
- **Drawdown-parity portfolio sizing:** set per-asset risk so each asset in isolation targets the same max drawdown (~20%).
- Asset expansion must fit the strategy's MECHANISM: trend-following logic gained from directional assets (gold/BTC/indices); S/R-retest logic did NOT (indices drift and rarely retest levels). Expansion is a hypothesis, not a default.

## Phase 7 — Optional ML layer

- ML **filters** the strategy's trades; it never generates signals. Random forest over pre-trade features (volatility, session, day, trend state — 200+ features, ~3.7k trades in the TJR study).
- Two gates for any ML finding: (1) market-logic veto — "works when raining" gets discarded; (2) survives the locked test period. Expected outcome: almost everything dies. The one TJR survivor: index longs ≫ shorts → long-only indices.

## Phase 8 — Reality checks (last, always)

- Apply real venue costs (spreads, commissions, swap) only at the end — measure the edge first, then whether costs kill it (TJR rebuild: 26,058% → 8,639% after costs).
- **Contribution per asset:** every asset must be profitable after costs; no lucky-market carry.
- **Equity-curve pain:** returns by year, flat/negative stretches, regime shifts (Set-and-Forget's edge concentrated post-2020 — and its first TWO years were negative: −4.35% then −13.35%, with the ~30% max drawdown landing in that stretch). Can the trader psychologically survive the path? A real edge can open with two losing years; a strategy cannot be judged on its first.

## Our additions (stricter than the videos)

- A final untouched holdout (~last 18–24 months) frozen until ALL decisions — including asset/TF/exit selection, which the TJR videos made in-sample — are locked.
- `graphify save-result` feedback loop on research questions, and every experiment config + result persisted for reproducibility.

## The one-line thesis

**Every rule must earn its place.** Complexity doesn't create an edge — it creates the illusion of control.
