"""Significant-area detectors behind one shared contract (issues #8-#10).

Every detector returns a zones frame with columns:
    kind   - detector name ("swing_low", "swing_high", "sr", ...)
    lower  - zone price floor
    upper  - zone price ceiling
    born   - first bar time the zone is KNOWN (no lookahead: a pivot with
             right=R confirms only R bars after its extreme)
    died   - bar time the zone expires (age-based in this slice)

`active_at` filters zones alive at a timestamp; `confluence` returns the
zones containing a price (with an explicit pad tolerance). Setup polarity
is enforced geometrically: a bullish setup qualifies against zones that
contain its pattern low, a bearish one against zones containing its
pattern high.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from tamad.pattern import atr

ZONE_COLUMNS = ["kind", "lower", "upper", "born", "died"]


@dataclass(frozen=True)
class ZoneConfig:
    swing_left: int = 6
    swing_right: int = 2
    swing_zone_atr: float = 0.25     # zone half-width in ATR multiples
    swing_max_age: int = 500         # bars a swing zone stays active
    sr_min_touches: int = 3
    sr_cluster_atr: float = 0.5      # pivots within this ATR distance cluster
    sr_max_age: int = 5000
    fvg_min_atr: float = 0.0         # minimum gap height in ATR multiples
    fvg_max_age: int = 1000
    ob_displacement_atr: float = 1.5  # body size that counts as displacement
    ob_max_age: int = 1000
    rsi_period: int = 14
    div_lookback: int = 60           # max bars between the two pivots
    div_max_age: int = 500
    atr_period: int = 14


def _empty_zones() -> pd.DataFrame:
    return pd.DataFrame(columns=ZONE_COLUMNS)


def _pivot_indices(values: np.ndarray, left: int, right: int, is_low: bool) -> list[int]:
    """Strict pivot extremes: bar i beats every bar within [i-left, i+right].

    Vectorized: compare each bar against the best of its left window and
    the best of its right window (strict on both sides).
    """
    s = pd.Series(values)
    if is_low:
        best_left = s.rolling(left).min().shift(1)
        best_right = s.rolling(right).min().shift(-right)
        mask = (s < best_left) & (s < best_right)
    else:
        best_left = s.rolling(left).max().shift(1)
        best_right = s.rolling(right).max().shift(-right)
        mask = (s > best_left) & (s > best_right)
    return list(np.flatnonzero(mask.fillna(False).to_numpy()))


def swing_zones(candles: pd.DataFrame, cfg: ZoneConfig = ZoneConfig()) -> pd.DataFrame:
    atr_series = atr(candles, cfg.atr_period).bfill()
    rows = []
    for is_low, kind, series in (
        (True, "swing_low", candles["low"].to_numpy()),
        (False, "swing_high", candles["high"].to_numpy()),
    ):
        for i in _pivot_indices(series, cfg.swing_left, cfg.swing_right, is_low):
            confirm = i + cfg.swing_right
            width = cfg.swing_zone_atr * float(atr_series.iloc[i])
            died_idx = min(confirm + cfg.swing_max_age, len(candles) - 1)
            rows.append({
                "kind": kind,
                "lower": float(series[i]) - width,
                "upper": float(series[i]) + width,
                "born": candles.index[confirm],
                "died": candles.index[died_idx],
            })
    return pd.DataFrame(rows, columns=ZONE_COLUMNS) if rows else _empty_zones()


def sr_zones(candles: pd.DataFrame, cfg: ZoneConfig = ZoneConfig()) -> pd.DataFrame:
    """Support/resistance: clusters of >= sr_min_touches pivot prices.

    Pivots (both polarities) are clustered in time order; a cluster whose
    touch count reaches the threshold becomes a zone, born at the
    confirming pivot's confirmation bar.
    """
    atr_series = atr(candles, cfg.atr_period).bfill()
    lows = candles["low"].to_numpy()
    highs = candles["high"].to_numpy()
    pivots = [(i, float(lows[i])) for i in
              _pivot_indices(lows, cfg.swing_left, cfg.swing_right, True)]
    pivots += [(i, float(highs[i])) for i in
               _pivot_indices(highs, cfg.swing_left, cfg.swing_right, False)]
    pivots.sort()

    clusters: list[dict] = []
    rows = []
    for i, price in pivots:
        tol = cfg.sr_cluster_atr * float(atr_series.iloc[i])
        target = None
        for cluster in clusters:
            center = sum(cluster["prices"]) / len(cluster["prices"])
            if abs(price - center) <= tol:
                target = cluster
                break
        if target is None:
            clusters.append({"prices": [price], "born_zone": False})
            continue
        target["prices"].append(price)
        if len(target["prices"]) >= cfg.sr_min_touches and not target["born_zone"]:
            target["born_zone"] = True
            confirm = i + cfg.swing_right
            died_idx = min(confirm + cfg.sr_max_age, len(candles) - 1)
            if confirm >= len(candles):
                continue
            rows.append({
                "kind": "sr",
                "lower": min(target["prices"]),
                "upper": max(target["prices"]),
                "born": candles.index[confirm],
                "died": candles.index[died_idx],
            })
    return pd.DataFrame(rows, columns=ZONE_COLUMNS) if rows else _empty_zones()


def fvg_zones(candles: pd.DataFrame, cfg: ZoneConfig = ZoneConfig()) -> pd.DataFrame:
    """Fair value gaps: three-bar imbalances.

    Bullish: bar i's low sits above bar i-2's high -> zone spans the gap,
    born at bar i (the bar that completes the pattern). The zone dies when
    a later bar trades through the entire gap (fully filled) or after
    fvg_max_age bars. Gaps under fvg_min_atr x ATR are ignored.
    """
    highs = candles["high"].to_numpy()
    lows = candles["low"].to_numpy()
    atr_series = atr(candles, cfg.atr_period).bfill().fillna(0.0).to_numpy()
    n = len(candles)
    rows = []
    for i in range(2, n):
        for bull in (True, False):
            if bull:
                lower, upper = highs[i - 2], lows[i]
            else:
                lower, upper = highs[i], lows[i - 2]
            if upper - lower <= cfg.fvg_min_atr * atr_series[i] or upper <= lower:
                continue
            died_idx = min(i + cfg.fvg_max_age, n - 1)
            # fully filled when price trades through the whole gap again
            for j in range(i + 1, died_idx + 1):
                filled = lows[j] <= lower if bull else highs[j] >= upper
                if filled:
                    died_idx = j
                    break
            rows.append({
                "kind": "fvg_bull" if bull else "fvg_bear",
                "lower": float(lower), "upper": float(upper),
                "born": candles.index[i], "died": candles.index[died_idx],
            })
    return pd.DataFrame(rows, columns=ZONE_COLUMNS) if rows else _empty_zones()


def ob_zones(candles: pd.DataFrame, cfg: ZoneConfig = ZoneConfig()) -> pd.DataFrame:
    """Order blocks: the last opposite candle before a displacement bar.

    Bullish: a green bar whose body >= ob_displacement_atr x ATR promotes
    the most recent red bar (within 3 bars) to a zone from its low to its
    body top, born at the displacement bar. Bearish mirrors. Age-based
    expiry.
    """
    opens = candles["open"].to_numpy()
    closes = candles["close"].to_numpy()
    highs = candles["high"].to_numpy()
    lows = candles["low"].to_numpy()
    body = closes - opens
    atr_series = atr(candles, cfg.atr_period).bfill().fillna(0.0).to_numpy()
    n = len(candles)
    rows = []
    for j in range(1, n):
        threshold = cfg.ob_displacement_atr * atr_series[j]
        if threshold <= 0 or abs(body[j]) < threshold:
            continue
        bull = body[j] > 0
        source = None
        for i in range(j - 1, max(j - 4, -1), -1):
            if (body[i] < 0) if bull else (body[i] > 0):
                source = i
                break
        if source is None:
            continue
        died_idx = min(j + cfg.ob_max_age, n - 1)
        if bull:
            lower, upper = float(lows[source]), float(max(opens[source], closes[source]))
            kind = "ob_bull"
        else:
            lower, upper = float(min(opens[source], closes[source])), float(highs[source])
            kind = "ob_bear"
        rows.append({
            "kind": kind, "lower": lower, "upper": upper,
            "born": candles.index[j], "died": candles.index[died_idx],
        })
    return pd.DataFrame(rows, columns=ZONE_COLUMNS) if rows else _empty_zones()


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Wilder's RSI."""
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    rs = gain / loss.replace(0, float("nan"))
    out = 100 - 100 / (1 + rs)
    return out.fillna(50.0).where(~close.diff().isna(), other=float("nan"))


def div_zones(candles: pd.DataFrame, cfg: ZoneConfig = ZoneConfig()) -> pd.DataFrame:
    """Regular RSI divergence at price pivots.

    Bullish: consecutive price swing lows within div_lookback bars where
    price makes a lower low but RSI makes a higher low. The zone wraps the
    second pivot's extreme (swing_zone_atr half-width), born at its
    confirmation bar. Bearish mirrors on highs. Age-based expiry.
    """
    atr_series = atr(candles, cfg.atr_period).bfill()
    rsi_series = rsi(candles["close"], cfg.rsi_period)
    n = len(candles)
    rows = []
    for is_low, kind, series in (
        (True, "div_bull", candles["low"].to_numpy()),
        (False, "div_bear", candles["high"].to_numpy()),
    ):
        pivots = _pivot_indices(series, cfg.swing_left, cfg.swing_right, is_low)
        for a, b in zip(pivots, pivots[1:]):
            if b - a > cfg.div_lookback:
                continue
            price_worse = series[b] < series[a] if is_low else series[b] > series[a]
            rsi_a, rsi_b = float(rsi_series.iloc[a]), float(rsi_series.iloc[b])
            rsi_better = rsi_b > rsi_a if is_low else rsi_b < rsi_a
            if not (price_worse and rsi_better):
                continue
            confirm = b + cfg.swing_right
            if confirm >= n:
                continue
            width = cfg.swing_zone_atr * float(atr_series.iloc[b])
            died_idx = min(confirm + cfg.div_max_age, n - 1)
            rows.append({
                "kind": kind,
                "lower": float(series[b]) - width,
                "upper": float(series[b]) + width,
                "born": candles.index[confirm],
                "died": candles.index[died_idx],
            })
    return pd.DataFrame(rows, columns=ZONE_COLUMNS) if rows else _empty_zones()


DETECTORS = {
    "swing": swing_zones,
    "sr": sr_zones,
    "fvg": fvg_zones,
    "ob": ob_zones,
    "div": div_zones,
}


def detect(candles: pd.DataFrame, kinds: tuple[str, ...],
           cfg: ZoneConfig = ZoneConfig()) -> pd.DataFrame:
    frames = [DETECTORS[k](candles, cfg) for k in kinds]
    frames = [f for f in frames if not f.empty]
    return pd.concat(frames, ignore_index=True) if frames else _empty_zones()


def active_at(zones_df: pd.DataFrame, t: pd.Timestamp) -> pd.DataFrame:
    if zones_df.empty:
        return zones_df
    return zones_df[(zones_df["born"] <= t) & (zones_df["died"] > t)]


def confluence(zones_df: pd.DataFrame, t: pd.Timestamp, price: float,
               pad: float = 0.0) -> pd.DataFrame:
    alive = active_at(zones_df, t)
    if alive.empty:
        return alive
    return alive[(alive["lower"] - pad <= price) & (price <= alive["upper"] + pad)]
