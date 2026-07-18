import pandas as pd
import pytest

from tamad import data, skeleton


def test_holdout_lock_refuses_windows_touching_2025():
    with pytest.raises(SystemExit, match="HOLDOUT LOCK"):
        skeleton.run("BTCUSDT", "15m", "2024-06-01", "2025-02-01")


def test_end_to_end_path_on_synthetic_candles(monkeypatch):
    # deterministic candles containing one bullish Tamad setup + TP exit
    rows = [
        (100, 101, 99, 100.5),
        (100.5, 101, 99.5, 100),
        (100, 101, 95, 96),      # C1
        (96, 99, 94, 98.5),      # C2 (sweeps)
        (98.5, 99, 96.5, 97),    # C3 signal
        (97, 98, 96, 96.5),      # fill bar: fill 97, sl 94, tp 106
        (96.5, 107, 96, 106.5),  # tp touched
        (106.5, 107.5, 105, 107),  # green so no trailing triplet forms
    ]
    idx = pd.date_range("2022-01-01", periods=len(rows), freq="15min", tz="UTC")
    candles = pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=idx)
    candles["volume"] = 1.0
    monkeypatch.setattr(data, "get_candles", lambda *a, **k: candles)

    summary = skeleton.run("BTCUSDT", "15m", "2022-01-01", "2022-01-02")
    assert summary["setups"] == 1
    assert summary["trade_count"] == 1
    assert summary["exit_reasons"] == {"tp": 1}
    assert summary["net_r"] == pytest.approx(3.0)
