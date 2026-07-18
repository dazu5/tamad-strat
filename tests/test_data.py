import pandas as pd
import pytest

from tamad import data


@pytest.fixture
def fake_source(tmp_path, monkeypatch):
    """Redirect the cache to a temp dir and count network fetches."""
    monkeypatch.setattr(data, "CACHE_DIR", tmp_path)
    calls = []

    def fake_fetch(symbol, interval, year, month):
        calls.append((year, month))
        if (year, month) == (2022, 3):   # simulate a month with no data
            return None
        idx = pd.date_range(f"{year}-{month:02d}-01", periods=100, freq="15min", tz="UTC")
        df = pd.DataFrame(
            {"open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": 10.0},
            index=idx,
        )
        df.index.name = "time"
        return df

    monkeypatch.setattr(data, "_fetch_month", fake_fetch)
    return calls


def test_cache_hit_makes_no_network_calls(fake_source):
    data.get_candles("BTCUSDT", "15m", "2022-01-01", "2022-02-01")
    assert fake_source == [(2022, 1)]
    data.get_candles("BTCUSDT", "15m", "2022-01-01", "2022-02-01")
    assert fake_source == [(2022, 1)]   # second call served from parquet


def test_window_is_half_open_and_trimmed(fake_source):
    df = data.get_candles("BTCUSDT", "15m", "2022-01-01 01:00", "2022-01-01 05:00")
    assert df.index[0] == pd.Timestamp("2022-01-01 01:00", tz="UTC")
    assert df.index[-1] < pd.Timestamp("2022-01-01 05:00", tz="UTC")


def test_months_without_data_are_skipped(fake_source):
    df = data.get_candles("BTCUSDT", "15m", "2022-02-01", "2022-05-01")
    assert (2022, 3) in fake_source
    assert not df.empty


def test_resample_derives_aligned_htf():
    idx = pd.date_range("2022-01-01", periods=8, freq="15min", tz="UTC")
    df = pd.DataFrame(
        {
            "open": [1, 2, 3, 4, 5, 6, 7, 8],
            "high": [2, 3, 4, 5, 6, 7, 8, 9],
            "low": [0, 1, 2, 3, 4, 5, 6, 7],
            "close": [1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5, 8.5],
            "volume": [1] * 8,
        },
        index=idx,
    )
    hourly = data.resample_ohlcv(df, "1h")
    assert len(hourly) == 2
    assert hourly.iloc[0]["open"] == 1
    assert hourly.iloc[0]["high"] == 5
    assert hourly.iloc[0]["low"] == 0
    assert hourly.iloc[0]["close"] == 4.5
    assert hourly.iloc[0]["volume"] == 4


def test_find_gaps_reports_holes():
    idx = pd.date_range("2022-01-01", periods=4, freq="15min", tz="UTC")
    idx = idx.delete(2)  # drop one bar
    df = pd.DataFrame({"open": 1.0, "high": 1, "low": 1, "close": 1, "volume": 1}, index=idx)
    gaps = data.find_gaps(df, "15m")
    assert len(gaps) == 1
    assert gaps.iloc[0]["missing_bars"] == 1
