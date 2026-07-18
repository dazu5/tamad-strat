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
