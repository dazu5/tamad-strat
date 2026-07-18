import pandas as pd
import pytest

from tamad import matrix


def make_trades(n, side=1, r=3.0, start="2022-01-01", freq="6h"):
    idx = pd.date_range(start, periods=n, freq=freq, tz="UTC")
    return pd.DataFrame({
        "entry_time": idx,
        "side": side,
        "r_multiple": [r if i % 2 == 0 else -1.0 for i in range(n)],
        "pnl": [r if i % 2 == 0 else -1.0 for i in range(n)],
    })


def test_breakdown_by_direction_groups_and_summarizes():
    trades = pd.concat([make_trades(40, side=1), make_trades(10, side=-1)])
    out = matrix.breakdown(trades, "direction")
    assert set(out.index) == {"long", "short"}
    assert out.loc["long", "trade_count"] == 40
    assert out.loc["short", "trade_count"] == 10


def test_small_samples_are_flagged():
    trades = pd.concat([make_trades(40, side=1), make_trades(10, side=-1)])
    out = matrix.breakdown(trades, "direction")
    assert not out.loc["long", "small_sample"]
    assert out.loc["short", "small_sample"]        # 10 < 30


def test_breakdown_by_session_buckets_utc_hours():
    trades = make_trades(24, freq="1h")            # one trade per hour of the day
    out = matrix.breakdown(trades, "session")
    assert set(out.index) == {"asia_00_08", "europe_08_16", "us_16_24"}
    assert out["trade_count"].sum() == 24
    assert (out["trade_count"] == 8).all()


def test_breakdown_by_month():
    trades = make_trades(60, freq="1D")            # spans Jan-Mar
    out = matrix.breakdown(trades, "month")
    assert out.loc["2022-01", "trade_count"] == 31


def test_run_matrix_covers_every_combination(monkeypatch):
    calls = []

    def fake_run(config, unlock_holdout=False):
        calls.append((config.symbol, config.interval))
        return {"config_hash": "x", "split": "train", "config": {
            "symbol": config.symbol, "interval": config.interval,
            "start": config.start, "end": config.end},
            "setups": 5,
            "metrics": {"trade_count": 3, "wins": 1, "losses": 2, "win_rate": 1 / 3,
                        "net_r": 1.0, "expectancy_r": 0.33, "profit_factor": 1.5},
            "cached": False}

    monkeypatch.setattr(matrix.experiments, "run", fake_run)
    table = matrix.run_matrix(["A", "B"], ["5m", "15m", "1h"], "2022-01-01", "2022-02-01")
    assert len(calls) == 6
    assert len(table) == 6
    assert {"symbol", "interval", "win_rate", "profit_factor"} <= set(table.columns)
