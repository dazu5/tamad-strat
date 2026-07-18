import pandas as pd

from tamad.experiments import _apply_bias


def htf_setups(rows):
    """rows: (time, side, tp)"""
    df = pd.DataFrame(
        {"side": [r[1] for r in rows], "tp": [r[2] for r in rows]},
        index=pd.DatetimeIndex([pd.Timestamp(r[0], tz="UTC") for r in rows]),
    )
    return df


def ltf_setups(rows):
    """rows: (time, side)"""
    return pd.DataFrame(
        {"side": [r[1] for r in rows], "sl": 90.0, "entry": 100.0},
        index=pd.DatetimeIndex([pd.Timestamp(r[0], tz="UTC") for r in rows]),
    )


HTF = htf_setups([("2022-01-01 00:00", 1, 120.0)])   # bull bias, 4h bars


def test_same_side_inside_window_kept_opposite_dropped():
    ltf = ltf_setups([
        ("2022-01-01 06:00", 1),    # long inside bias window -> kept
        ("2022-01-01 07:00", -1),   # short inside bull bias -> dropped
    ])
    out = _apply_bias(ltf, HTF, "4h", bias_max_age=12, tp_mode="own")
    assert len(out) == 1
    assert out.iloc[0]["side"] == 1


def test_outside_window_dropped():
    ltf = ltf_setups([("2022-01-03 01:00", 1)])   # 12 x 4h = 48h window ends Jan 3 00:00
    out = _apply_bias(ltf, HTF, "4h", bias_max_age=12, tp_mode="own")
    assert out.empty


def test_htf_tp_mode_attaches_override():
    ltf = ltf_setups([("2022-01-01 06:00", 1)])
    out = _apply_bias(ltf, HTF, "4h", bias_max_age=12, tp_mode="htf")
    assert out.iloc[0]["tp_override"] == 120.0
    own = _apply_bias(ltf, HTF, "4h", bias_max_age=12, tp_mode="own")
    assert "tp_override" not in own.columns


def test_latest_htf_signal_wins():
    flipped = htf_setups([
        ("2022-01-01 00:00", 1, 120.0),
        ("2022-01-01 08:00", -1, 80.0),   # bias flips short
    ])
    ltf = ltf_setups([
        ("2022-01-01 06:00", 1),    # under the bull regime -> kept
        ("2022-01-01 10:00", 1),    # bear regime now -> dropped
        ("2022-01-01 11:00", -1),   # matches bear regime -> kept
    ])
    out = _apply_bias(ltf, flipped, "4h", bias_max_age=12, tp_mode="own")
    assert list(out["side"]) == [1, -1]
