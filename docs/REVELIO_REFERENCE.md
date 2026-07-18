# Revelio Reference — on-screen data extracted from video frames

The transcripts in `METHODOLOGY.md` captured only speech. This file holds the on-screen tables and rule cards extracted via frame analysis (2026-07-18), with exact numbers the narration never spoke aloud. Cite this file, not memory, when quoting Revelio's results.

## Video 1 — TJR falsification (`4uqeKO6KcJk`)

### V1 full results matrix (sweep + BOS, 3-partial-TP structure, Jan 2016 – May 2026, no costs)

| Pair | TF | Trades | Win rate | Return |
|---|---|---|---|---|
| GBPUSD | M5 | 1,339 | 50.1% | +17.5% |
| GBPUSD | M15 | 648 | 54.5% | +115.7% |
| GBPUSD | H1 | 147 | 42.9% | −23.9% |
| EURUSD | M5 | 1,356 | 48.0% | −25.2% |
| EURUSD | M15 | 585 | 48.2% | −9.5% |
| EURUSD | H1 | 141 | 52.5% | −1.3% |
| USDJPY | M5 | 1,283 | 48.7% | +19.2% |
| USDJPY | M15 | 468 | 54.1% | +34.7% |
| USDJPY | H1 | 118 | 56.8% | +34.1% |
| GBPJPY | M5 | 1,459 | 49.0% | +14.5% |
| GBPJPY | M15 | 545 | 50.8% | +41.9% |
| GBPJPY | H1 | 121 | 54.5% | +23.8% |

Benchmark shown: V1 +20% vs S&P 500 buy-and-hold +306% over the same period (15×).

### His results schema (visible in the raw dataframe)

`asset, timeframe, trade_count, wins, losses, win_rate, total_r, profit_factor, exit_sl_count, exit_be_count, tp1_hit_count, tp2_hit_count, tp3_hit_count` — a good template for our results store (ours swaps the TP-hit columns for exit-reason counts).

## Video 2 — TJR rebuild (`8FJbpSY0R3o`)

### Take-profit hit rates (all V1 trades, 2016–2026)

TP1 (≥1R): **49.9%** · TP2 (≥2R): **26.2%** · TP3 (≥3R): **17.6%**

### Exit structures tested (word-cloud screen; 11 of the 12 visible)

Fixed 0.5R · Fixed 1R · Fixed 1.5R · Fixed 2R · Fixed 3R · Full exit at TP1 · Full exit at TP2 · Full exit at TP3 · Original TJR structure · Original structure, no BE · Trailing Stop. (12th not captured on screen.)

### Trailing stop vs original structure, per asset (exact)

| Asset | Return before → after | MaxDD before → after | Ret/DD before → after | Verdict |
|---|---|---|---|---|
| XAUUSD | 345% → 477% | 33% → 42% | 10.3 → 11.5 | Better |
| BTCUSD | 56% → 173% | 8% → 10% | 6.8 → 16.5 | Much better |
| SPX | 20% → 36% | 11% → 12% | 1.9 → 2.9 | Better |
| NDX | 43% → 54% | 18% → 19% | 2.3 → 2.8 | Better |
| GBPUSD | 116% → 101% | 16% → 16% | 7.3 → 6.4 | Worse → GBPUSD got fixed 1:1 instead |

### Drawdown-parity sizing (final risk per trade, targeting ~20% standalone maxDD)

XAUUSD **0.5%** · BTCUSD **2.0%** · SPX **1.5%** · NDX **1.5%** · GBPUSD **1.5%** → standalone maxDDs all land at 21–22%. (Transcript only mentioned gold and BTC; the 1.5% tier is frame-only data.)

### Final portfolio test

**2,942 trades.** Before costs: +26,058.62% (~71%/yr), maxDD 24.92%, Return/DD 1,045.8. After IC Markets costs: +8,639.28% (~54%/yr), maxDD 29.24%.

### Dollar contribution after costs ($10k start)

| Asset | Net PnL | Share |
|---|---|---|
| XAUUSD | $200,897.75 | 23.25% |
| BTCUSD | $197,057.02 | 22.81% |
| SPX | $192,696.27 | 22.30% |
| GBPUSD | $182,348.91 | 21.11% |
| NDX | $90,927.73 | 10.52% |

## Video 4 — Set-and-Forget rebuild (`HzVSi9ux1NU`)

### Ablation grid (exact settings)

| Rule | Settings | Count |
|---|---|---|
| 1. Higher-timeframe bias | off, pair (Alex's W+D / D+4H), weekly, daily, 4-hour | ×5 |
| 2. Trend on the traded chart | on, off | ×2 |
| 3. Candlestick pattern entry | on, off | ×2 |
| 4. Retest of the level | on, off | ×2 |
| 5. Trading session | Asia, London, New York, overlap, all | ×5 |

5×2×2×2×5 = **200 configurations**, ranked by profit factor on the **portfolio frame, costs excluded, 2% risk per trade**.

### Ablation ranking (whole-period table, top rows)

| Rank | PF | Bias | Trend | Pattern | Retest | Session |
|---|---|---|---|---|---|---|
| 1 | 1.196 | off | off | off | off | overlap |
| 2 | 1.193 | off | on | on | on | asia |
| 3 | 1.153 | off | off | off | on | overlap |
| 4 | 1.139 | H4 | on | on | on | asia |
| 5 | 1.137 | off | off | off | off | asia |

Mid-table (ranks ~90–121) sits at PF 0.87–0.93 and is dominated by bias-on configurations. Training-set ranks (narrated): all-off asia #2, all-off overlap #6, all-off all-sessions #9.

### The final Set-and-Forget strategy (8-card recap, verbatim)

1. **Areas of interest** — daily timeframe, drawn exactly as Alex teaches: 5–60 pips wide, 2-year expiration.
2. **Entry timeframes** — 2H, 1H, 30M, 15M charts; pick the one you prefer — they take similar trades.
3. **Sessions** — all sessions, 24/5.
4. **The entry** — first candle that closes inside a daily area. No trend, no bias, no pattern, no retest. Buy at support, sell at resistance.
5. **Stop loss** — 5 pips below the support for buys, 5 pips above the resistance for sells.
6. **Take profit** — nearest daily swing point. If the target pays less than 2× the risk, skip the trade. More than 4× the risk: cap it at 4.
7. **One trade per pair** — only one open trade per pair at a time.
8. **Risk** — personal preference; his choice: 0.5% of the highest value ever reached (high-water mark).

### Year-by-year returns (net of costs, 0.5% HWM; $10,000 → $59,271)

2016 −4.35% · 2017 −13.35% · 2018 +1.01% · 2019 +10.89% · 2020 +8.05% · 2021 +28.07% · 2022 +17.72% · 2023 +33.54% · 2024 +14.24% · 2025 +102.46% · 2026 +26.89% (partial). Max drawdown ~−30%, hit during the losing 2017 stretch.

**Note: the two negative years were the FIRST two.** A real edge can open with two losing years — expectation-setting for any live deployment, and a caution against judging a strategy on its first year.

## Implications for Tamad-Strat

- **Win-rate context for the group's claim:** TJR's V1 win rates run 43–57% where a "win" is TP1 at 1:1. A 60% win rate at a full 1:3 target would be far outside anything in these four studies — V0 measures it directly.
- **Sample-size expectations:** his forex combos produced ~120–1,460 trades per pair/TF over 10 years; our 5m/15m/1h crypto scans should land in similar orders of magnitude, which sets realistic small-sample thresholds (#6).
- **Results-store columns:** adopt his schema shape plus config hash (issue #5); count exit reasons the way he counts TP hits.
- **Exit menu for issue #15:** his 12-structure sweep maps to our fixed-RR ladder (0.5R–4R), full-close variants, no-BE variant, and trailing — already reflected in the issue.
- **Ranking discipline:** PF ranking during search runs on a portfolio frame at flat risk with costs excluded; costs and sizing come after selection, exactly as our phases order it.
