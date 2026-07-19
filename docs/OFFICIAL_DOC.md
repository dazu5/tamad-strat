# The official documentation, codified (#20)

Source: `docs/official/TAMAD_STRATEGY.docx` (the group's official write-up, obtained 2026-07-19; Taglish, 13 embedded diagrams). This file is the canonical transcription; cite it, not memory. Where it conflicts with folklore from chat, **this document wins**.

## The rules as officially written

1. **Pattern**: three consecutive candles. Bullish = RED–GREEN–RED → LONG; bearish = GREEN–RED–GREEN → SHORT. Framing: "kung ano yung kulay ng middle candle, yan ang bias" — the middle candle's color IS the trade direction.
2. **Validity — both-wick rule**: "All three candles should have a wick both high and low for it to be valid." (New to us; `full_wick` flag on setups.)
3. **The orange line (hold rule)**: the line sits at the C1-close / C2-open level. The third candle's **body must not close past it; the wick may** ("okay lang lumagpas ang wick basta hindi lumagpas ang body"). Identical to our coded `C3 close >= C2 open` (bull) / `<= ` (bear).
4. **Entry**: at the closing price of the third candle, only once all criteria confirm.
5. **Stop loss**: at the extreme wick of the three candles (highest for shorts, lowest for longs — the doc's long section says "pinakamataas" but its diagrams place the stop at the lowest wick; transcription corrects the obvious copy-paste).
6. **Take profit**: fixed **2RR or 3RR**, full close — "depende kung saan ka madalas nakaka TP", i.e. pick by your own backtest.
7. **Key levels** (the pattern must form at one): support/resistance (any swing below/above current price), **pullback/retracement**, **equilibrium = 50% of the range**, fair value gaps. Diagrams show the bullish pattern forming at the 50% retracement *inside a bullish trend* — i.e. a continuation entry.
8. **Timeframes**: minimum **15m**; traded set 15m/30m/1h/4h ("kunan mo ng data kung saan ka mas maraming tumatama"); daily/weekly/monthly patterns are **HTF bias only**.
9. **HTF alignment**: if a higher-timeframe narrative or structure map exists, don't oppose it.

## The official claims

| Claim | Win rate | Target | Breakeven WR | Implied expectancy |
|---|---|---|---|---|
| Official doc | **52%** | 2RR | 33.3% | +0.56 R/trade |
| Official doc | **46%** | 3RR | 25.0% | +0.84 R/trade |
| Group journal (folk) | 60% | 3RR | 25.0% | +1.40 R/trade |

The doc claims **less** than the group journals — and explicitly says "e-backtest muna and kunan ng data… mag-iiba pa rin yan depende sa nag-trade." No sample size is stated. Run `python -m tamad.claims --official` for the full plausibility table.

## Delta table vs what we validated (issues #2–#19)

| Doc element | Our pipeline | Status |
|---|---|---|
| Colors, direction, middle-candle bias | identical | ✅ tested |
| Orange-line hold rule (body in, wick free) | identical (`c >= c2_o`) | ✅ tested |
| SL at 3-candle extreme wick | identical | ✅ tested |
| Entry at C3 close (next-bar-open fill) | identical | ✅ tested |
| 3RR full close | identical | ✅ tested |
| **2RR full close** | never tested | 🔶 V4 (#22) |
| **Both-wick validity** | never tested | 🔶 V4 (#22), flag via #20 |
| S/R + FVG key levels | swing/sr/fvg detectors | ✅ tested (filter nothing as-taught) |
| **Equilibrium (50% of range)** | no detector | 🔶 #21 |
| Pullback/retracement context | never explicit | 🔶 #21 continuation pill |
| **15m minimum TF** | we traded 5m (out-of-spec) | 🔶 V4 uses 15m/30m/1h/4h |
| 30m and 4h as traded TFs | never tested | 🔶 V4 (#22) |
| Daily+ = bias only | tested (#13: hurts) | ✅ tested |
| Sweep rule | not in the doc | ✅ we falsified folklore |
| C1 climax size | not in the doc | ➕ our own discovery |

## Image inventory (embedded in the docx)

1–2: bearish setup diagram + execution (orange line, SL at highest wick, 3RR tool) · 3, 5: bearish chart examples · 4, 6: bullish equivalents · 7–8: bullish execution · 9: **equilibrium/50%-of-range with the pattern at a pullback in a bullish trend** · 10–13: S/R and FVG key-level examples.
