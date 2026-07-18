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


DETECTORS = {
    "swing": swing_zones,
    "sr": sr_zones,
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
