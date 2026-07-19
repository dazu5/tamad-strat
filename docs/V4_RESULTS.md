# V4 as-documented audit

Grid: 2 x 2 x 2 x 6 x 2 x 2 = 192 configs · combos: BTC/ETH/SOL x 15m/30m/1h/4h · flat $1, zero costs · ranked by PF on TRAINING [2017-08-01 .. 2023-01-01); top 10 confirmed on TEST [2023-01-01 .. 2025-01-01) via the experiment runner. Selection never saw test. Holdout sealed.

## Training ranking (top 25)

|   rr | full_wick_required   |   c1_min_atr | zones     | session   | context      |   trade_count |   wins |   win_rate |   net_r |   expectancy_r |   profit_factor |   combos_pf_above_1 |
|-----:|:---------------------|-------------:|:----------|:----------|:-------------|--------------:|-------:|-----------:|--------:|---------------:|----------------:|--------------------:|
|    3 | False                |            1 | eq        | us_16_24  | continuation |           663 |    200 |      0.302 | 134.898 |          0.203 |           1.291 |                   9 |
|    3 | False                |            1 | ob        | us_16_24  | continuation |           496 |    147 |      0.296 |  92     |          0.185 |           1.264 |                   8 |
|    3 | False                |            1 | eq,sr,fvg | us_16_24  | continuation |           715 |    212 |      0.297 | 130.898 |          0.183 |           1.26  |                   8 |
|    3 | False                |            1 | fvg       | us_16_24  | continuation |           284 |     84 |      0.296 |  49.898 |          0.176 |           1.249 |                   8 |
|    3 | True                 |            1 | eq        | us_16_24  | continuation |           502 |    148 |      0.295 |  87.898 |          0.175 |           1.248 |                   8 |
|    3 | False                |            1 | eq        | nan       | continuation |          2017 |    592 |      0.294 | 348.898 |          0.173 |           1.245 |                  10 |
|    3 | False                |            1 |           | us_16_24  | continuation |           756 |    222 |      0.294 | 129.898 |          0.172 |           1.243 |                   8 |
|    3 | True                 |            1 | eq,sr,fvg | us_16_24  | continuation |           542 |    157 |      0.29  |  83.898 |          0.155 |           1.218 |                   8 |
|    3 | False                |            1 | ob        | nan       | continuation |          1440 |    415 |      0.288 | 220     |          0.153 |           1.215 |                  10 |
|    2 | False                |            1 | ob        | us_16_24  | continuation |           498 |    188 |      0.378 |  66     |          0.133 |           1.213 |                   9 |
|    3 | False                |            1 | eq,sr,fvg | nan       | continuation |          2218 |    639 |      0.288 | 335.898 |          0.151 |           1.213 |                  10 |
|    3 | True                 |            1 |           | us_16_24  | continuation |           576 |    166 |      0.288 |  85.898 |          0.149 |           1.21  |                   8 |
|    3 | False                |            1 | ob        | us_16_24  | nan          |          2104 |    605 |      0.288 | 313.369 |          0.149 |           1.209 |                   9 |
|    3 | False                |            1 |           | nan       | continuation |          2336 |    671 |      0.287 | 345.898 |          0.148 |           1.208 |                  10 |
|    3 | True                 |            1 | eq        | nan       | continuation |          1540 |    440 |      0.286 | 217.898 |          0.141 |           1.198 |                  10 |
|    2 | False                |            1 | fvg       | us_16_24  | continuation |           285 |    107 |      0.375 |  34.898 |          0.122 |           1.196 |                   9 |
|    3 | True                 |            1 | ob        | us_16_24  | nan          |          1584 |    452 |      0.285 | 221.369 |          0.14  |           1.196 |                  10 |
|    2 | False                |            1 | eq        | us_16_24  | continuation |           665 |    248 |      0.373 |  77.898 |          0.117 |           1.187 |                   8 |
|    3 | True                 |            1 | fvg       | us_16_24  | continuation |           217 |     62 |      0.286 |  28.898 |          0.133 |           1.186 |                   7 |
|    2 | True                 |            1 | eq        | us_16_24  | continuation |           504 |    187 |      0.371 |  55.898 |          0.111 |           1.176 |                   7 |
|    2 | True                 |            1 | fvg       | us_16_24  | continuation |           218 |     81 |      0.372 |  23.898 |          0.11  |           1.174 |                   8 |
|    3 | True                 |            1 | eq,sr,fvg | nan       | continuation |          1693 |    475 |      0.281 | 204.898 |          0.121 |           1.168 |                  10 |
|    2 | False                |            1 |           | us_16_24  | continuation |           759 |    280 |      0.369 |  79.898 |          0.105 |           1.167 |                   8 |
|    3 | True                 |            1 |           | nan       | continuation |          1785 |    500 |      0.28  | 212.898 |          0.119 |           1.166 |                   9 |
|    3 | False                |          nan |           | us_16_24  | continuation |          5459 |   1524 |      0.279 | 634.898 |          0.116 |           1.161 |                  12 |

## Bottom 5 (for contrast)

|   rr | full_wick_required   |   c1_min_atr | zones   | session   | context      |   trade_count |   wins |   win_rate |     net_r |   expectancy_r |   profit_factor |   combos_pf_above_1 |
|-----:|:---------------------|-------------:|:--------|:----------|:-------------|--------------:|-------:|-----------:|----------:|---------------:|----------------:|--------------------:|
|    2 | True                 |          nan | eq      | us_16_24  | nan          |         17534 |   5712 |      0.326 |  -402.454 |         -0.023 |           0.966 |                   5 |
|    2 | True                 |            1 | sr      | nan       | continuation |           739 |    241 |      0.326 |   -17.102 |         -0.023 |           0.966 |                   5 |
|    3 | True                 |          nan | fvg     | us_16_24  | nan          |          8858 |   2155 |      0.243 |  -242.823 |         -0.027 |           0.964 |                   4 |
|    2 | False                |          nan |         | nan       | nan          |         53877 |  17518 |      0.325 | -1329.13  |         -0.025 |           0.963 |                   4 |
|    2 | False                |          nan | eq      | us_16_24  | nan          |         20520 |   6652 |      0.324 |  -567.454 |         -0.028 |           0.959 |                   4 |

## Test confirmation of the training top 10

|   rr | full_wick_required   |   c1_min_atr | zones     | session   | context      |   trade_count |   wins |   losses |   win_rate |   net_r |   expectancy_r |   profit_factor |
|-----:|:---------------------|-------------:|:----------|:----------|:-------------|--------------:|-------:|---------:|-----------:|--------:|---------------:|----------------:|
|    3 | False                |            1 | eq        | us_16_24  | continuation |           346 |     90 |      256 |      0.26  |   11.42 |          0.033 |           1.045 |
|    3 | False                |            1 | ob        | us_16_24  | continuation |           257 |     66 |      191 |      0.257 |    4.42 |          0.017 |           1.023 |
|    3 | False                |            1 | eq,sr,fvg | us_16_24  | continuation |           377 |     99 |      278 |      0.263 |   16.42 |          0.044 |           1.059 |
|    3 | False                |            1 | fvg       | us_16_24  | continuation |           152 |     41 |      111 |      0.27  |    9.42 |          0.062 |           1.085 |
|    3 | True                 |            1 | eq        | us_16_24  | continuation |           256 |     61 |      195 |      0.238 |  -12    |         -0.047 |           0.938 |
|    3 | False                |            1 | eq        | nan       | continuation |          1145 |    312 |      833 |      0.272 |  100.42 |          0.088 |           1.121 |
|    3 | False                |            1 |           | us_16_24  | continuation |           399 |    108 |      291 |      0.271 |   30.42 |          0.076 |           1.105 |
|    3 | True                 |            1 | eq,sr,fvg | us_16_24  | continuation |           279 |     66 |      213 |      0.237 |  -15    |         -0.054 |           0.93  |
|    3 | False                |            1 | ob        | nan       | continuation |           826 |    220 |      606 |      0.266 |   51.42 |          0.062 |           1.085 |
|    2 | False                |            1 | ob        | us_16_24  | continuation |           257 |     81 |      176 |      0.315 |  -15.58 |         -0.061 |           0.911 |

## The doc's own claims vs measured TEST win rates

| config                             |   rr |   claimed_wr |   measured_wr |   trades |   breakeven_wr |   profit_factor |
|:-----------------------------------|-----:|-------------:|--------------:|---------:|---------------:|----------------:|
| doc-minimal (wick rule only)       |    2 |         0.52 |         0.338 |    20483 |          0.333 |           1.019 |
| doc-minimal (wick rule only)       |    3 |         0.46 |         0.252 |    16501 |          0.25  |           1.012 |
| doc-full (wick + eq/sr/fvg levels) |    2 |         0.52 |         0.339 |    20050 |          0.333 |           1.026 |
| doc-full (wick + eq/sr/fvg levels) |    3 |         0.46 |         0.255 |    16538 |          0.25  |           1.028 |

## Continuation pill ablation on the best confirmed config

| context      | window   |   trades |   win_rate |   net_r |   profit_factor |
|:-------------|:---------|---------:|-----------:|--------:|----------------:|
| continuation | train    |     2017 |      0.294 | 348.898 |           1.245 |
| continuation | test     |     1145 |      0.272 | 100.42  |           1.121 |
| off          | train    |     7866 |      0.27  | 620.281 |           1.108 |
| off          | test     |     4180 |      0.262 | 198.044 |           1.064 |

## Venue costs on the best confirmed config (TEST, pooled assets)

| interval   |   trades |   pf_zero_cost |   pf_binance_spot |   pf_mexc_futures |
|:-----------|---------:|---------------:|------------------:|------------------:|
| 15m        |      621 |          1.077 |             0.246 |             0.608 |
| 30m        |      313 |          1.173 |             0.497 |             0.869 |
| 1h         |      172 |          1.063 |             0.571 |             0.857 |
| 4h         |       39 |          1.768 |             1.393 |             1.635 |
