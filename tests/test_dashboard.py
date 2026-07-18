import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from tamad import dashboard, data, experiments
from tamad.experiments import RunConfig

APP = "tamad/dashboard.py"


def test_yearly_returns_groups_by_exit_year():
    trades = pd.DataFrame({
        "exit_time": pd.to_datetime(["2022-03-01", "2022-09-01", "2023-01-15"], utc=True),
        "r_multiple": [3.0, -1.0, 3.0],
    })
    yearly = dashboard.yearly_returns_r(trades)
    assert yearly[2022] == 2.0
    assert yearly[2023] == 3.0


@pytest.fixture
def seeded_store(tmp_path, monkeypatch):
    monkeypatch.setattr(experiments, "STORE_DIR", tmp_path / "results")
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
    monkeypatch.setattr(data, "candles", lambda *a, **k: candles)
    record = experiments.run(RunConfig(
        symbol="BTCUSDT", interval="15m", start="2022-01-01", end="2022-06-30"))
    return record


def test_dashboard_smoke_renders_seeded_store(seeded_store):
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    assert not at.exception
    assert any("All runs" in h.value for h in at.subheader)


def test_dashboard_smoke_renders_empty_store(tmp_path, monkeypatch):
    monkeypatch.setattr(experiments, "STORE_DIR", tmp_path / "empty")
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    assert not at.exception
    assert len(at.info) == 1
