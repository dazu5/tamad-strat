import subprocess

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from tamad import data, experiments

APP = "tamad/dashboard.py"


@pytest.fixture
def empty_store(tmp_path, monkeypatch):
    monkeypatch.setattr(experiments, "STORE_DIR", tmp_path / "results")
    return tmp_path / "results"


def test_cli_runs_and_clears_pending(empty_store, monkeypatch):
    rows = [
        (100, 101, 99, 100.5), (100.5, 101, 99.5, 100),
        (100, 101, 95, 96), (96, 99, 94, 98.5),
        (98.5, 99, 96.5, 97), (97, 98, 96, 96.5),
        (96.5, 107, 96, 106.5), (106.5, 107.5, 105, 107),
    ]
    idx = pd.date_range("2022-01-01", periods=len(rows), freq="15min", tz="UTC")
    candles = pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=idx)
    candles["volume"] = 1.0
    monkeypatch.setattr(data, "candles", lambda *a, **k: candles)

    config = experiments.RunConfig(symbol="BTCUSDT", interval="15m",
                                   start="2022-01-01", end="2022-06-30")
    experiments.mark_pending(config)
    assert len(experiments.list_pending()) == 1

    experiments.main(["--symbol", "BTCUSDT", "--interval", "15m",
                      "--start", "2022-01-01", "--end", "2022-06-30"])
    assert experiments.list_pending().empty          # finished + cleared
    assert len(experiments.list_runs()) == 1


def test_launch_button_spawns_detached_run(empty_store, monkeypatch):
    spawned = []
    monkeypatch.setattr(subprocess, "Popen", lambda cmd, **kw: spawned.append(cmd))
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    at.text_input[0].set_value("ETHUSDT")     # symbol
    at.text_input[1].set_value("2021-01-01")  # start
    at.text_input[2].set_value("2022-01-01")  # end
    at.button[0].set_value(True)              # form submit
    at.run()
    assert not at.exception
    assert len(spawned) == 1
    assert "ETHUSDT" in spawned[0]
    assert len(experiments.list_pending()) == 1      # visible as in-progress


def test_holdout_window_is_blocked_in_the_ui(empty_store, monkeypatch):
    spawned = []
    monkeypatch.setattr(subprocess, "Popen", lambda cmd, **kw: spawned.append(cmd))
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    at.text_input[2].set_value("2025-06-01")  # end inside the holdout
    at.button[0].set_value(True)
    at.run()
    assert not at.exception
    assert spawned == []                      # nothing launched
    assert any("HOLDOUT" in e.value for e in at.error)