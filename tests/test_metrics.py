import pandas as pd
import pytest

from tamad.metrics import summarize


def trades_from_r(rs):
    return pd.DataFrame({"r_multiple": rs, "pnl": rs})


def test_summary_hand_computed():
    # 3 wins of +3R, 5 losses of -1R, 2 scratches
    trades = trades_from_r([3, 3, 3, -1, -1, -1, -1, -1, 0, 0])
    s = summarize(trades)
    assert s["trade_count"] == 10
    assert s["wins"] == 3
    assert s["losses"] == 5
    assert s["win_rate"] == pytest.approx(0.3)
    assert s["net_r"] == pytest.approx(4.0)          # 9 - 5
    assert s["expectancy_r"] == pytest.approx(0.4)   # 4 / 10
    assert s["profit_factor"] == pytest.approx(9 / 5)


def test_no_losses_gives_infinite_profit_factor():
    s = summarize(trades_from_r([3, 3]))
    assert s["profit_factor"] == float("inf")
    assert s["win_rate"] == 1.0


def test_empty_trades_summary_is_zeroed():
    s = summarize(pd.DataFrame({"r_multiple": [], "pnl": []}))
    assert s["trade_count"] == 0
    assert s["net_r"] == 0.0


def test_equity_curve_cumulates_r_over_exit_time():
    from tamad.metrics import equity_curve
    idx = pd.date_range("2022-01-01", periods=4, freq="1D", tz="UTC")
    trades = pd.DataFrame({"exit_time": idx, "r_multiple": [3.0, -1.0, -1.0, 3.0]})
    curve = equity_curve(trades)
    assert list(curve.values) == [3.0, 2.0, 1.0, 4.0]
    assert curve.index[-1] == idx[-1]


def test_max_drawdown_r_measures_peak_to_trough():
    from tamad.metrics import max_drawdown_r
    idx = pd.date_range("2022-01-01", periods=6, freq="1D", tz="UTC")
    trades = pd.DataFrame(
        {"exit_time": idx, "r_multiple": [3.0, 3.0, -1.0, -1.0, -1.0, 3.0]}
    )
    assert max_drawdown_r(trades) == 3.0   # peak 6R, trough 3R
