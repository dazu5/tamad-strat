"""Read-only dashboard over the results store.

Launch:
    streamlit run tamad/dashboard.py

Lists every persisted run with key metrics, compares selected runs side
by side, and shows equity curves (yearly returns and max drawdown
visible) plus exit-reason counts. Strictly read-only against the store;
launching runs from the UI arrives with issue #12.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from tamad import experiments, metrics


def yearly_returns_r(trades: pd.DataFrame) -> pd.Series:
    """Net R per calendar year of exit."""
    exit_time = pd.to_datetime(trades["exit_time"], utc=True)
    return trades.groupby(exit_time.dt.year)["r_multiple"].sum()


def launch_panel() -> None:
    """Sidebar form: tweak a config and launch it as a detached run.

    The holdout lock applies here exactly as in the headless runner: a
    window touching 2025-01-01+ is refused before anything starts.
    """
    import subprocess
    import sys

    with st.sidebar:
        st.header("Launch a run")
        with st.form("launch"):
            symbol = st.text_input("Symbol", "BTCUSDT")
            interval = st.selectbox("Interval", ["5m", "15m", "30m", "1h", "2h", "4h"], index=1)
            start = st.text_input("Start", "2017-08-01")
            end = st.text_input("End", "2023-01-01")
            sweep = st.checkbox("Require ideal sweep", False)
            c1 = st.number_input("C1 min ATR (0 = off)", value=0.0, step=0.5)
            zone_kinds = st.multiselect("Zones", ["swing", "sr", "fvg", "ob", "div"])
            submitted = st.form_submit_button("Launch")
        if submitted:
            config = experiments.RunConfig(
                symbol=symbol, interval=interval, start=start, end=end,
                sweep_required=sweep, c1_min_atr=c1 or None,
                zones=tuple(zone_kinds),
            )
            if experiments.split_label(start, end) == "holdout":
                st.error("HOLDOUT LOCK: this window touches 2025-01-01 or later. "
                         "Runs there require the recorded sign-off on issue #18.")
                return
            experiments.mark_pending(config)
            cmd = [sys.executable, "-m", "tamad.experiments",
                   "--symbol", symbol, "--interval", interval,
                   "--start", start, "--end", end]
            if sweep:
                cmd.append("--sweep-required")
            if c1:
                cmd += ["--c1-min-atr", str(c1)]
            if zone_kinds:
                cmd += ["--zones", ",".join(zone_kinds)]
            subprocess.Popen(cmd)
            st.success(f"Launched {config.config_hash()} — appears in the run "
                       "list when finished.")

        pending = experiments.list_pending()
        if not pending.empty:
            st.subheader("In progress")
            st.dataframe(pending, use_container_width=True)


def render() -> None:
    st.set_page_config(page_title="Tamad-Strat runs", layout="wide")
    st.title("Tamad-Strat — experiment runs")
    launch_panel()

    runs = experiments.list_runs()
    if runs.empty:
        st.info("No persisted runs yet. Execute experiments via tamad.matrix "
                "or tamad.experiments first.")
        return

    st.subheader("All runs")
    st.dataframe(runs, use_container_width=True)

    picked = st.multiselect(
        "Compare runs (config hashes)", list(runs["config_hash"]), key="picked"
    )
    if not picked:
        return
    compare = runs[runs["config_hash"].isin(picked)]
    st.subheader("Side by side")
    st.dataframe(compare.set_index("config_hash").T, use_container_width=True)

    for config_hash in picked:
        row = runs[runs["config_hash"] == config_hash].iloc[0]
        st.subheader(f"{row['symbol']} {row['interval']} — {config_hash}")
        try:
            trades = experiments.load_trades(config_hash)
        except FileNotFoundError:
            st.warning("No trades stored for this run (zero-trade result).")
            continue
        curve = metrics.equity_curve(trades)
        st.line_chart(curve.rename("net R"))
        left, right = st.columns(2)
        with left:
            st.metric("Max drawdown", f"{metrics.max_drawdown_r(trades):.1f} R")
            st.write("Yearly net R", yearly_returns_r(trades).to_frame("net_r"))
        with right:
            st.write("Exit reasons", trades["exit_reason"].value_counts().to_frame("count"))


if __name__ == "__main__" or st.runtime.exists():
    render()
