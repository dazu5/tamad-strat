import pandas as pd

from tamad import pills


def fake_run_factory(counts_by_variant):
    def fake_run(config, unlock_holdout=False):
        if config.sweep_required and config.c1_min_atr is not None:
            variant = "both"
        elif config.sweep_required:
            variant = "sweep"
        elif config.c1_min_atr is not None:
            variant = "c1"
        else:
            variant = "v0"
        n = counts_by_variant[variant]
        return {
            "config_hash": f"{variant}{config.c1_min_atr}",
            "split": "train",
            "config": config.__dict__ if hasattr(config, "__dict__") else {},
            "setups": n,
            "metrics": {"trade_count": n, "wins": n // 3, "losses": n - n // 3,
                        "win_rate": 1 / 3, "net_r": 0.0, "expectancy_r": 0.0,
                        "profit_factor": 1.0},
            "cached": False,
        }
    return fake_run


def test_compare_runs_every_variant_per_combo(monkeypatch):
    monkeypatch.setattr(
        pills.experiments, "run",
        fake_run_factory({"v0": 1000, "sweep": 400, "c1": 300, "both": 100}),
    )
    table = pills.compare(["BTCUSDT"], ["15m"], "2018-01-01", "2023-01-01",
                          c1_grid=(1.0, 2.0))
    # variants: v0, sweep, c1@1.0, c1@2.0, both@1.0, both@2.0
    assert len(table) == 6
    assert set(table["variant"]) == {"v0", "sweep", "c1@1.0", "c1@2.0",
                                     "both@1.0", "both@2.0"}


def test_collapse_flag_marks_starved_variants(monkeypatch):
    monkeypatch.setattr(
        pills.experiments, "run",
        fake_run_factory({"v0": 1000, "sweep": 400, "c1": 50, "both": 20}),
    )
    table = pills.compare(["BTCUSDT"], ["15m"], "2018-01-01", "2023-01-01",
                          c1_grid=(1.5,))
    v0_count = table.loc[table["variant"] == "v0", "trade_count"].iloc[0]
    c1 = table[table["variant"] == "c1@1.5"].iloc[0]
    assert c1["retention"] == 50 / v0_count
    assert bool(c1["collapsed"])            # under 10% of V0's sample
    sweep = table[table["variant"] == "sweep"].iloc[0]
    assert not bool(sweep["collapsed"])     # 40% retained
