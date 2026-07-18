import pandas as pd
import pytest

from tamad import costs


def test_cost_in_r_scales_with_notional_to_risk_ratio():
    trades = pd.DataFrame({
        "fill": [100.0], "sl": [98.0],           # risk distance 2 -> notional 50x
        "r_multiple": [3.0], "pnl": [3.0],
    })
    model = costs.CostModel(fee_pct_per_side=0.001, spread_pct=0.0002)
    out = costs.apply(trades, model)
    expected_cost = 0.0022 * 100.0 / 2.0         # 0.11 R
    assert out.iloc[0]["cost_r"] == pytest.approx(expected_cost)
    assert out.iloc[0]["r_multiple"] == pytest.approx(3.0 - expected_cost)
    assert out.iloc[0]["pnl"] == out.iloc[0]["r_multiple"]


def test_tight_stops_pay_more_in_r():
    trades = pd.DataFrame({
        "fill": [100.0, 100.0], "sl": [99.0, 90.0],
        "r_multiple": [3.0, 3.0], "pnl": [3.0, 3.0],
    })
    out = costs.apply(trades, costs.BINANCE_SPOT)
    assert out.iloc[0]["cost_r"] > out.iloc[1]["cost_r"] * 9


def test_zero_model_changes_nothing():
    trades = pd.DataFrame({
        "fill": [100.0], "sl": [98.0], "r_multiple": [-1.0], "pnl": [-1.0],
    })
    out = costs.apply(trades, costs.ZERO)
    assert out.iloc[0]["r_multiple"] == -1.0
