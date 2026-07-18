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
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from tamad import data, engine, metrics, pattern

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

    def config_hash(self) -> str:
        canonical = json.dumps(asdict(self), sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()[:12]


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

    candles = data.get_candles(config.symbol, config.interval, config.start, config.end)
    setups = pattern.detect(candles, pattern.PatternConfig(rr=config.rr))
    if config.sweep_required:
        setups = setups[setups["sweep"]]
    if config.c1_min_atr is not None:
        setups = setups[setups["c1_atr_mult"] >= config.c1_min_atr]
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
