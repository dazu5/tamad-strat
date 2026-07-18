"""Candle store: one interface to OHLCV data regardless of source.

Crypto comes from Binance's public bulk archive (data.binance.vision),
cached locally as parquet, one file per symbol/interval/month. Higher
timeframes derive from the base interval by resampling so multi-TF logic
always works on aligned data.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pandas as pd
import requests

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "cache"
_VISION_URL = (
    "https://data.binance.vision/data/spot/monthly/klines/"
    "{symbol}/{interval}/{symbol}-{interval}-{year}-{month:02d}.zip"
)
_KLINE_COLS = [
    "open_time", "open", "high", "low", "close", "volume",
    "close_time", "quote_volume", "trades",
    "taker_buy_base", "taker_buy_quote", "ignore",
]
OHLCV = ["open", "high", "low", "close", "volume"]

_INTERVAL_MS = {
    "1m": 60_000, "5m": 300_000, "15m": 900_000, "30m": 1_800_000,
    "1h": 3_600_000, "2h": 7_200_000, "4h": 14_400_000,
    "1d": 86_400_000, "1w": 604_800_000,
}
_RESAMPLE_RULE = {
    "5m": "5min", "15m": "15min", "30m": "30min",
    "1h": "1h", "2h": "2h", "4h": "4h", "1d": "1D", "1w": "1W",
}


def _parse_klines(raw: bytes) -> pd.DataFrame:
    df = pd.read_csv(io.BytesIO(raw), header=None, names=_KLINE_COLS)
    if df.iloc[0]["open_time"] == "open_time":  # some archive files carry a header row
        df = df.iloc[1:].reset_index(drop=True)
    ts = pd.to_numeric(df["open_time"])
    # Binance vision files switched from ms to microsecond stamps in 2025.
    unit = "us" if ts.iloc[0] > 10**14 else "ms"
    df.index = pd.to_datetime(ts, unit=unit, utc=True)
    df.index.name = "time"
    return df[OHLCV].astype(float)


def _fetch_month(symbol: str, interval: str, year: int, month: int) -> pd.DataFrame | None:
    url = _VISION_URL.format(symbol=symbol, interval=interval, year=year, month=month)
    resp = requests.get(url, timeout=60)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        raw = zf.read(zf.namelist()[0])
    return _parse_klines(raw)


def get_candles(
    symbol: str,
    interval: str,
    start: str | pd.Timestamp,
    end: str | pd.Timestamp,
) -> pd.DataFrame:
    """Return UTC-indexed OHLCV candles for [start, end).

    Months download on first use and cache as parquet; months with no data
    on the exchange (before listing / current partial month) are skipped.
    """
    if interval not in _INTERVAL_MS:
        raise ValueError(f"unsupported interval: {interval}")
    start = pd.Timestamp(start, tz="UTC")
    end = pd.Timestamp(end, tz="UTC")
    frames = []
    last = end - pd.Timedelta(1, "ns")
    for period in pd.period_range(
        pd.Period(year=start.year, month=start.month, freq="M"),
        pd.Period(year=last.year, month=last.month, freq="M"),
    ):
        cache_file = Path(CACHE_DIR) / symbol / interval / f"{period.year}-{period.month:02d}.parquet"
        if cache_file.exists():
            frames.append(pd.read_parquet(cache_file))
            continue
        df = _fetch_month(symbol, interval, period.year, period.month)
        if df is None:
            continue
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(cache_file)
        frames.append(df)
    if not frames:
        raise ValueError(f"no data for {symbol} {interval} in [{start}, {end})")
    out = pd.concat(frames).sort_index()
    out = out[~out.index.duplicated(keep="first")]
    return out.loc[(out.index >= start) & (out.index < end)]


def resample_ohlcv(df: pd.DataFrame, interval: str) -> pd.DataFrame:
    """Derive a higher timeframe from base candles (empty bins drop out)."""
    rule = _RESAMPLE_RULE[interval]
    out = df.resample(rule, label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    )
    return out.dropna(subset=["open"])


def find_gaps(df: pd.DataFrame, interval: str) -> pd.DataFrame:
    """Report holes: rows where the next bar arrives late.

    Empty frame = contiguous series.
    """
    step = pd.Timedelta(milliseconds=_INTERVAL_MS[interval])
    deltas = df.index.to_series().diff().iloc[1:]
    late = deltas[deltas > step]
    return pd.DataFrame({
        "gap_starts_after": late.index - late,
        "missing_bars": (late / step - 1).astype(int),
    }).reset_index(drop=True)
