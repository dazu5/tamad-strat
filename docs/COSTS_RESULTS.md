# Costs applied to the final configuration

Survivor pills + trail_1R · Binance spot model: 0.10%/side + 0.02% spread = 0.22% of notional per round trip · cost in R = 0.22% x fill / risk-distance · holdout still locked.

## Per asset and interval

| interval   | asset   |   trades |   net_r_zero_cost |   net_r_with_costs |   pf_zero_cost |   pf_with_costs |   median_cost_r |
|:-----------|:--------|---------:|------------------:|-------------------:|---------------:|----------------:|----------------:|
| 5m         | BTCUSDT |     2677 |              2602 |            -9428.6 |          2.952 |           0.159 |           1.426 |
| 5m         | ETHUSDT |     2569 |               720 |            -4881.4 |          1.541 |           0.173 |           1.098 |
| 5m         | SOLUSDT |     1258 |               104 |            -1299.8 |          1.157 |           0.272 |           0.7   |
| 15m        | BTCUSDT |      689 |               151 |             -628.1 |          1.433 |           0.329 |           0.66  |
| 15m        | ETHUSDT |      680 |               167 |             -414.3 |          1.488 |           0.461 |           0.511 |
| 15m        | SOLUSDT |      373 |                90 |             -100.7 |          1.503 |           0.68  |           0.363 |
| 1h         | BTCUSDT |      232 |                23 |              -61.4 |          1.187 |           0.662 |           0.293 |
| 1h         | ETHUSDT |      195 |                68 |                4.8 |          1.773 |           1.037 |           0.263 |
| 1h         | SOLUSDT |      111 |                 3 |              -24.4 |          1.047 |           0.719 |           0.185 |

## Parity portfolio on the TEST window, with costs

- **5m**: test return -119.7%, maxDD 119.7% · BTCUSDT: $-7,296, ETHUSDT: $-2,799, SOLUSDT: $-1,870
- **15m**: test return -65.7%, maxDD 66.2% · BTCUSDT: $-1,680, ETHUSDT: $-1,939, SOLUSDT: $-2,956
- **1h**: test return -44.5%, maxDD 70.9% · BTCUSDT: $-2,515, ETHUSDT: $19, SOLUSDT: $-1,959
