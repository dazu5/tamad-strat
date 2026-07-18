# Risk & portfolio engineering

Survivor config + trail_1R exit · zero costs · parity calibrated on training only, applied unseen to test.

## 5m-based portfolio

| asset   | sizing             |     train_return |   train_maxdd |   test_return |   test_maxdd |
|:--------|:-------------------|-----------------:|--------------:|--------------:|-------------:|
| BTCUSDT | fixed 1%           |      1.39062e+06 |          21.7 |        2117.6 |         28   |
| BTCUSDT | HWM 1%             |      1.84316e+06 |          24   |        2521.2 |         32   |
| BTCUSDT | HWM 0.5%           |  49476.1         |          12   |         428.6 |         16   |
| BTCUSDT | HWM parity (0.83%) | 616799           |          20   |        1446.5 |         26.7 |
| ETHUSDT | fixed 1%           |   2743.2         |          41.3 |        1965.3 |         22.9 |
| ETHUSDT | HWM 1%             |   3461.7         |          50   |        2311.7 |         25   |
| ETHUSDT | HWM 0.5%           |    535.1         |          25   |         411.7 |         12.5 |
| ETHUSDT | HWM parity (0.40%) |    343.5         |          20   |         271.7 |         10   |
| SOLUSDT | fixed 1%           |     67.2         |          39   |          41   |         18   |
| SOLUSDT | HWM 1%             |     86.1         |          49   |          49.4 |         18   |
| SOLUSDT | HWM 0.5%           |     36.7         |          24.5 |          22.5 |          9   |
| SOLUSDT | HWM parity (0.41%) |     29.1         |          20   |          18   |          7.3 |

### Portfolio (parity-sized, TEST window only)

- return: 6698.2% · maxDD: 27.0%
- contribution: BTCUSDT: $455,126, ETHUSDT: $171,459, SOLUSDT: $43,230

## 15m-based portfolio

| asset   | sizing             |   train_return |   train_maxdd |   test_return |   test_maxdd |
|:--------|:-------------------|---------------:|--------------:|--------------:|-------------:|
| BTCUSDT | fixed 1%           |          154.6 |          24.1 |          40.9 |         12.3 |
| BTCUSDT | HWM 1%             |          168.5 |          26   |          43.9 |         13   |
| BTCUSDT | HWM 0.5%           |           69.5 |          13   |          20.1 |          6.5 |
| BTCUSDT | HWM parity (0.77%) |          118.7 |          20   |          32.5 |         10   |
| ETHUSDT | fixed 1%           |          228.5 |          16.3 |          35.9 |         23   |
| ETHUSDT | HWM 1%             |          246.6 |          17   |          39.5 |         26   |
| ETHUSDT | HWM 0.5%           |           89.9 |           8.5 |          18.3 |         13   |
| ETHUSDT | HWM parity (1.18%) |          325.7 |          20   |          47.8 |         30.6 |
| SOLUSDT | fixed 1%           |           57.1 |          11.5 |          46.2 |         16.6 |
| SOLUSDT | HWM 1%             |           60.7 |          12   |          49.6 |         18   |
| SOLUSDT | HWM 0.5%           |           27.3 |           6   |          22.5 |          9   |
| SOLUSDT | HWM parity (1.67%) |          117.2 |          20   |          94   |         30   |

### Portfolio (parity-sized, TEST window only)

- return: 278.2% · maxDD: 31.5%
- contribution: BTCUSDT: $5,795, ETHUSDT: $7,291, SOLUSDT: $14,734
