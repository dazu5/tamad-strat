"""Forex candles from Dukascopy's public datafeed (#16).

Serves GBPUSD/EURUSD through the same candle interface as crypto:
`forex.candles(symbol, interval, start, end)` returns UTC OHLCV, with
higher timeframes resampled from the 1m base. Dukascopy publishes one
LZMA-compressed bi5 file of 1-minute BID candles per day; each row is
big-endian (seconds_offset:i4, open:i4, close:i4, low:i4, high:i4,
volume:f4) with prices scaled by 1e5 for these pairs. The month in the
URL is ZERO-indexed. Daily files cache as parquet like the crypto store.

Weekend days legitimately have no data; 404s are skipped. The holdout
boundary applies exactly as in the crypto backbone.
"""

from __future__ import annotations

import lzma
import struct
from pathlib import Path

import pandas as pd
import requests

from tamad import data as crypto_data

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "forex"
_URL = ("https://datafeed.dukascopy.com/datafeed/{symbol}/{year}/{month:02d}/"
        "{day:02d}/BID_candles_min_1.bi5")
_ROW = struct.Struct(">iiiiif")
PRICE_SCALE = 1e5


def _parse_day(raw: bytes, day_start: pd.Timestamp) -> pd.DataFrame:
    payload = lzma.decompress(raw)
    rows = []
    for offset in range(0, len(payload), _ROW.size):
        secs, o, c, lo, hi, vol = _ROW.unpack_from(payload, offset)
        rows.append((day_start + pd.Timedelta(seconds=secs),
                     o / PRICE_SCALE, hi / PRICE_SCALE,
                     lo / PRICE_SCALE, c / PRICE_SCALE, vol))
    df = pd.DataFrame(rows, columns=["time", "open", "high", "low", "close",
                                     "volume"]).set_index("time")
    return df


_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def _fetch_day(symbol: str, day: pd.Timestamp) -> pd.DataFrame | None:
    url = _URL.format(symbol=symbol, year=day.year, month=day.month - 1,
                      day=day.day)
    for attempt in range(3):
        resp = requests.get(url, timeout=60, headers=_HEADERS)
        if resp.status_code == 404 or (resp.ok and not resp.content):
            return None
        if resp.ok:
            return _parse_day(resp.content, day)
        if resp.status_code in (429, 503):
            import time
            time.sleep(2 * (attempt + 1))
            continue
        resp.raise_for_status()
    resp.raise_for_status()
    return None


def get_candles(symbol: str, start, end) -> pd.DataFrame:
    """1m candles for [start, end), daily-cached."""
    start = crypto_data.to_utc(start)
    end = crypto_data.to_utc(end)
    frames = []
    for day in pd.date_range(start.normalize(), (end - pd.Timedelta(1, "ns")).normalize(),
                             freq="1D"):
        cache_file = Path(CACHE_DIR) / symbol / f"{day.date()}.parquet"
        if cache_file.exists():
            frames.append(pd.read_parquet(cache_file))
            continue
        df = _fetch_day(symbol, day)
        if df is None or df.empty:
            continue
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(cache_file)
        frames.append(df)
    if not frames:
        raise ValueError(f"no forex data for {symbol} in [{start}, {end})")
    out = pd.concat(frames).sort_index()
    out = out[~out.index.duplicated(keep="first")]
    return out.loc[(out.index >= start) & (out.index < end)]


def candles(symbol: str, interval: str, start, end) -> pd.DataFrame:
    """Same contract as data.candles, resampling up from the 1m base."""
    base = get_candles(symbol, start, end)
    if interval == "1m":
        return base
    return crypto_data.resample_ohlcv(base, interval)
