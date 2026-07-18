import pandas as pd
import pytest

from tamad import backbone, data


def synthetic(symbol, interval, start, end):
    idx = pd.date_range("2020-08-11", "2020-08-13", freq="5min", tz="UTC", inclusive="left")
    df = pd.DataFrame(
        {"open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": 3.0}, index=idx
    )
    df.index.name = "time"
    return df


def test_sync_refuses_to_cross_the_holdout_boundary():
    with pytest.raises(SystemExit, match="HOLDOUT"):
        backbone.sync("BTCUSDT", end="2025-06-01")


def test_sync_accepts_its_own_tz_aware_default_boundary(monkeypatch):
    monkeypatch.setattr(data, "get_candles", synthetic)
    df = backbone.sync("BTCUSDT")   # end defaults to the tz-aware holdout stamp
    assert not df.empty


def test_coverage_report_lists_symbol_range_and_gaps(monkeypatch):
    monkeypatch.setattr(data, "get_candles", synthetic)
    report = backbone.coverage_report(["BTCUSDT"])
    assert "BTCUSDT" in report
    assert "2020-08-11" in report
    assert "2024-12-31" not in report.split("BTCUSDT")[0]  # boundary note, not fake data
    assert "holdout" in report.lower()


def test_spot_check_passes_when_resample_matches_native(monkeypatch):
    base = synthetic("BTCUSDT", "5m", None, None)
    native = data.resample_ohlcv(base, "15m")

    def fake_get(symbol, interval, start, end):
        return base if interval == "5m" else native

    monkeypatch.setattr(data, "get_candles", fake_get)
    assert backbone.spot_check("BTCUSDT", "15m", "2020-08-11", "2020-08-12") is True


def test_spot_check_fails_on_mismatch(monkeypatch):
    base = synthetic("BTCUSDT", "5m", None, None)
    native = data.resample_ohlcv(base, "15m")
    native.iloc[0, native.columns.get_loc("high")] += 1.0

    def fake_get(symbol, interval, start, end):
        return base if interval == "5m" else native

    monkeypatch.setattr(data, "get_candles", fake_get)
    assert backbone.spot_check("BTCUSDT", "15m", "2020-08-11", "2020-08-12") is False
