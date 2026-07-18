"""Experiment runner: declarative configs, persisted reproducible results.

Every run persists under `results/` keyed by a deterministic config hash:
a committed JSON record (config, split label, metrics) plus the full
trade list as parquet under `results/raw/` (gitignored). Re-running an
identical config is served from the store — same hash, one entry.

Split labeling follows the canonical boundaries in CLAUDE.md:
training through 2022-12-31, test 2023-01-01 .. 2024-12-31, holdout from
2025-01-01. Any window touching the holdout raises HoldoutLockedError
unless `unlock_holdout=True` is passed explicitly — that flag is recorded
in the persisted record (issue #18 sign-off governs its use).

Negative results persist exactly like positive ones: they are findings.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import MISSING, asdict, dataclass, fields
from pathlib import Path

import numpy as np
import pandas as pd

from tamad import data, engine, metrics, pattern, zones as zones_mod

STORE_DIR = Path(__file__).resolve().parent.parent / "results"

TRAIN_END = pd.Timestamp("2023-01-01", tz="UTC")     # exclusive
HOLDOUT_START = pd.Timestamp("2025-01-01", tz="UTC")  # inclusive


class HoldoutLockedError(RuntimeError):
    pass


@dataclass(frozen=True)
class RunConfig:
    symbol: str
    interval: str
    start: str
    end: str
    rr: float = 3.0
    risk_per_trade: float = 1.0
    # pattern pills (issue #7) — off in V0
    sweep_required: bool = False
    c1_min_atr: float | None = None
    # significant-area context (issues #8-#10) — none in V0
    zones: tuple[str, ...] = ()
    zone_pad_atr: float = 0.25

    def config_hash(self) -> str:
        """Stable across future field additions: default values are excluded,
        so a config's hash never changes when new defaulted fields appear."""
        payload = {}
        for f in fields(self):
            value = getattr(self, f.name)
            default = f.default if f.default is not MISSING else None
            if value != default:
                payload[f.name] = list(value) if isinstance(value, tuple) else value
        canonical = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()[:12]


def _filter_by_zones(setups: pd.DataFrame, candles: pd.DataFrame,
                     config: RunConfig) -> pd.DataFrame:
    """Keep setups whose pattern extreme sits inside an active zone.

    The qualifying price is the setup's SL level — by construction the
    pattern extreme (low for bulls, high for bears), which is the price
    the reversal claims is significant. Pad tolerance is zone_pad_atr x
    ATR at the signal bar.
    """
    if setups.empty:
        return setups
    zones_df = zones_mod.detect(candles, config.zones)
    if zones_df.empty:
        return setups.iloc[0:0]
    pad = (pattern.atr(candles).bfill() * config.zone_pad_atr).fillna(0.0)

    # sweep line over time: maintain the set of alive zones per signal bar
    # instead of filtering the full zone frame per setup
    zs = zones_df.sort_values("born").reset_index(drop=True)
    born = (pd.to_datetime(zs["born"], utc=True)
            .astype("datetime64[ns, UTC]").astype("int64").to_numpy())
    died = (pd.to_datetime(zs["died"], utc=True)
            .astype("datetime64[ns, UTC]").astype("int64").to_numpy())
    lower = zs["lower"].to_numpy()
    upper = zs["upper"].to_numpy()
    order = np.argsort(died, kind="stable")

    keep = []
    alive: set[int] = set()
    next_born = 0
    next_dead = 0
    for t, s in setups.sort_index().iterrows():
        t_ns = t.value
        while next_born < len(zs) and born[next_born] <= t_ns:
            alive.add(next_born)
            next_born += 1
        while next_dead < len(order) and died[order[next_dead]] <= t_ns:
            alive.discard(int(order[next_dead]))
            next_dead += 1
        price = float(s["sl"])
        tol = float(pad.get(t, 0.0))
        keep.append(any(lower[i] - tol <= price <= upper[i] + tol for i in alive))
    return setups.sort_index()[keep]


def split_label(start, end) -> str:
    start, end = data.to_utc(start), data.to_utc(end)
    if end > HOLDOUT_START:
        return "holdout"
    if end <= TRAIN_END:
        return "train"
    if start >= TRAIN_END:
        return "test"
    return "train+test"


def run(config: RunConfig, unlock_holdout: bool = False) -> dict:
    split = split_label(config.start, config.end)
    if split == "holdout" and not unlock_holdout:
        raise HoldoutLockedError(
            "window touches the holdout (2025-01-01+); requires the explicit "
            "unlock recorded via issue #18 sign-off"
        )

    record_file = Path(STORE_DIR) / f"{config.config_hash()}.json"
    if record_file.exists():
        record = json.loads(record_file.read_text(encoding="utf-8"))
        record["cached"] = True
        return record

    candles = data.candles(config.symbol, config.interval, config.start, config.end)
    setups = pattern.detect(candles, pattern.PatternConfig(rr=config.rr))
    if config.sweep_required:
        setups = setups[setups["sweep"]]
    if config.c1_min_atr is not None:
        setups = setups[setups["c1_atr_mult"] >= config.c1_min_atr]
    if config.zones:
        setups = _filter_by_zones(setups, candles, config)
    trades = engine.simulate(setups, candles, rr=config.rr,
                             risk_per_trade=config.risk_per_trade)

    record = {
        "config": asdict(config),
        "config_hash": config.config_hash(),
        "split": split,
        "holdout_unlocked": bool(unlock_holdout),
        "setups": int(len(setups)),
        "metrics": metrics.summarize(trades),
        "cached": False,
    }
    record_file.parent.mkdir(parents=True, exist_ok=True)
    raw_dir = Path(STORE_DIR) / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    if len(trades):
        trades.to_parquet(raw_dir / f"{config.config_hash()}.parquet")
    record_file.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return record


def list_runs() -> pd.DataFrame:
    rows = []
    for f in sorted(Path(STORE_DIR).glob("*.json")):
        r = json.loads(f.read_text(encoding="utf-8"))
        rows.append({
            "config_hash": r["config_hash"],
            "split": r["split"],
            **{k: r["config"][k] for k in ("symbol", "interval", "start", "end")},
            **{k: r["metrics"][k] for k in
               ("trade_count", "win_rate", "net_r", "expectancy_r", "profit_factor")},
        })
    return pd.DataFrame(rows)


def load_trades(config_hash: str) -> pd.DataFrame:
    return pd.read_parquet(Path(STORE_DIR) / "raw" / f"{config_hash}.parquet")
