import math

import pytest

from tamad.claims import check_claim


def test_expectancy_and_breakeven_match_closed_form():
    result = check_claim(win_rate=0.60, rr=3.0, n_trades=300)
    assert result["expectancy_r"] == pytest.approx(0.60 * 3 - 0.40)   # +1.4
    assert result["breakeven_wr"] == pytest.approx(0.25)


def test_wr_confidence_interval_matches_binomial_formula():
    result = check_claim(win_rate=0.60, rr=3.0, n_trades=300)
    half = 1.96 * math.sqrt(0.6 * 0.4 / 300)
    assert result["wr_ci95"] == pytest.approx((0.6 - half, 0.6 + half), rel=1e-6)


def test_flat_risk_moments_match_closed_form():
    # X = +3 w.p. 0.6, -1 w.p. 0.4 -> E=1.4, E[X^2]=5.8, var=3.84
    result = check_claim(win_rate=0.60, rr=3.0, n_trades=300)
    assert result["flat_expected_net_r"] == pytest.approx(1.4 * 300)
    assert result["flat_sd_net_r"] == pytest.approx(math.sqrt(300 * 3.84), rel=1e-6)


def test_simulation_is_deterministic_under_seed():
    a = check_claim(win_rate=0.60, rr=3.0, n_trades=300, seed=7)
    b = check_claim(win_rate=0.60, rr=3.0, n_trades=300, seed=7)
    assert a["compound_median_multiple"] == b["compound_median_multiple"]
    assert a["compound_median_maxdd"] == b["compound_median_maxdd"]


def test_positive_edge_compounds_upward():
    result = check_claim(win_rate=0.60, rr=3.0, n_trades=300, seed=1)
    assert result["compound_median_multiple"] > 1.0


def test_negative_edge_compounds_downward():
    result = check_claim(win_rate=0.20, rr=3.0, n_trades=300, seed=1)
    assert result["expectancy_r"] < 0
    assert result["compound_median_multiple"] < 1.0
