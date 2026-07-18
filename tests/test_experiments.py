import pandas as pd
import pytest

from tamad import data, experiments
from tamad.experiments import RunConfig


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(experiments, "STORE_DIR", tmp_path / "results")
    # deterministic candles with one bullish setup + tp exit (from skeleton test)
    rows = [
        (100, 101, 99, 100.5),
        (100.5, 101, 99.5, 100),
        (100, 101, 95, 96),
        (96, 99, 94, 98.5),
        (98.5, 99, 96.5, 97),
        (97, 98, 96, 96.5),
        (96.5, 107, 96, 106.5),
        (106.5, 107.5, 105, 107),
    ]
    idx = pd.date_range("2022-01-01", periods=len(rows), freq="15min", tz="UTC")
    candles = pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=idx)
    candles["volume"] = 1.0
    def sliced(symbol, interval, start, end):
        return candles.loc[
            (candles.index >= data.to_utc(start)) & (candles.index < data.to_utc(end))
        ]
    monkeypatch.setattr(data, "get_candles", sliced)
    return tmp_path / "results"


CFG = dict(symbol="BTCUSDT", interval="15m", start="2022-01-01", end="2022-06-30")


def test_config_hash_is_deterministic_and_order_independent():
    a = RunConfig(**CFG)
    b = RunConfig(**dict(reversed(list(CFG.items()))))
    assert a.config_hash() == b.config_hash()


def test_run_persists_config_trades_and_metrics(store):
    record = experiments.run(RunConfig(**CFG))
    assert record["metrics"]["trade_count"] == 1
    assert record["split"] == "train"
    listing = experiments.list_runs()
    assert len(listing) == 1
    assert listing.iloc[0]["config_hash"] == record["config_hash"]


def test_identical_config_is_served_from_store_not_rerun(store, monkeypatch):
    experiments.run(RunConfig(**CFG))
    def boom(*a, **k):
        raise AssertionError("engine should not run again for a cached config")
    monkeypatch.setattr(experiments.engine, "simulate", boom)
    record = experiments.run(RunConfig(**CFG))     # served from store
    assert record["cached"] is True
    assert len(experiments.list_runs()) == 1


def test_split_labels_follow_canonical_boundaries(store):
    test_cfg = RunConfig(**{**CFG, "start": "2023-02-01", "end": "2024-11-30"})
    assert experiments.run(test_cfg)["split"] == "test"
    spanning = RunConfig(**{**CFG, "start": "2022-06-01", "end": "2023-06-01"})
    assert experiments.run(spanning)["split"] == "train+test"


def test_holdout_window_requires_explicit_unlock(store):
    locked = RunConfig(**{**CFG, "start": "2024-06-01", "end": "2025-03-01"})
    with pytest.raises(experiments.HoldoutLockedError):
        experiments.run(locked)
    record = experiments.run(locked, unlock_holdout=True)   # explicit, recorded
    assert record["split"] == "holdout"
    assert record["holdout_unlocked"] is True


def test_negative_results_persist_like_any_run(store):
    record = experiments.run(RunConfig(**{**CFG, "end": "2022-01-01 01:00"}))
    assert record["metrics"]["trade_count"] == 0
    assert len(experiments.list_runs()) == 1


def test_pill_values_change_the_config_hash():
    base = RunConfig(**CFG)
    assert base.config_hash() != RunConfig(**CFG, sweep_required=True).config_hash()
    assert base.config_hash() != RunConfig(**CFG, c1_min_atr=1.5).config_hash()


def test_sweep_pill_filters_non_sweep_setups(store):
    # the fixture's single setup HAS a sweep (C2 low 94 < C1 low 95),
    # so sweep_required keeps it and a high C1 bar drops it
    kept = experiments.run(RunConfig(**CFG, sweep_required=True))
    assert kept["metrics"]["trade_count"] == 1
    dropped = experiments.run(RunConfig(**CFG, c1_min_atr=99.0))
    assert dropped["metrics"]["trade_count"] == 0
