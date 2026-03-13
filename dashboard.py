"""
WAIMS Readiness Watchlist
Streamlit web application for athlete monitoring data visualization
"""

import os
import pickle
import sqlite3
import re
import textwrap
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from athlete_profile_tab import athlete_profile_tab, create_radar_chart
from athlete_view import athlete_home_view
from coach_command_center import coach_command_center
from correlation_explorer import correlation_explorer_tab
from auth import (render_login_page, render_user_badge, is_authenticated,
                  current_role, current_athlete_player_id, can_see, data_access, get_visible_tabs)

try:
    from data_quality import DataQualityProcessor, show_data_quality_report
    HAVE_DATA_QUALITY = True
except ImportError:
    HAVE_DATA_QUALITY = False

try:
    from model_validation import show_validation_framework_streamlit
    HAVE_MODEL_VALIDATION = True
except ImportError:
    HAVE_MODEL_VALIDATION = False

try:
    from improved_gauges import create_player_card_compact, create_simple_battery
    from research_citations import show_research_foundation
    HAVE_IMPROVED_GAUGES = True
except ImportError:
    HAVE_IMPROVED_GAUGES = False

# ==============================================================================
# PAGE CONFIG
# ==============================================================================

HERE      = Path(__file__).resolve().parent
LOGO_PATH = HERE / "assets" / "branding" / "waims_run_man_logo.png"
if not LOGO_PATH.exists():
    LOGO_PATH = HERE.parent / "assets" / "branding" / "waims_run_man_logo.png"

st.set_page_config(
    page_title="WAIMS Readiness Watchlist",
    page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else "🏀",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ==============================================================================
# LOAD DATA
# ==============================================================================

@st.cache_data
def load_data():
    conn          = sqlite3.connect("waims_demo.db")
    players       = pd.read_sql_query("SELECT * FROM players",        conn)
    wellness      = pd.read_sql_query("SELECT * FROM wellness",       conn)
    training_load = pd.read_sql_query("SELECT * FROM training_load",  conn)
    force_plate   = pd.read_sql_query("SELECT * FROM force_plate",    conn)
    injuries      = pd.read_sql_query("SELECT * FROM injuries",       conn)
    acwr          = pd.read_sql_query("SELECT * FROM acwr",           conn)
    try:
        availability = pd.read_sql_query("SELECT * FROM availability", conn)
        availability["date"] = pd.to_datetime(availability["date"])
    except Exception:
        availability = pd.DataFrame()

    wellness["date"]       = pd.to_datetime(wellness["date"])
    training_load["date"]  = pd.to_datetime(training_load["date"])
    force_plate["date"]    = pd.to_datetime(force_plate["date"])
    acwr["date"]           = pd.to_datetime(acwr["date"])
    if len(injuries) > 0:
        injuries["injury_date"] = pd.to_datetime(injuries["injury_date"])
        if "return_date" in injuries.columns:
            injuries["return_date"] = pd.to_datetime(injuries["return_date"])

    conn.close()
    return players, wellness, training_load, force_plate, injuries, acwr, availability


try:
    players, wellness, training_load, force_plate, injuries, acwr, availability = load_data()
except Exception as e:
    st.error(f"Error loading database: {e}")
    st.info("Make sure waims_demo.db is in the current directory")
    st.stop()

# ==============================================================================
# HELPERS
# ==============================================================================

def _html_oneliner(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def create_mini_battery(value, show_label=True):
    """Emoji + percentage only -- no battery bar."""
    color = "#10b981" if value >= 80 else ("#f59e0b" if value >= 60 else "#ef4444")
    emoji = "🟢"       if value >= 80 else ("🟡"       if value >= 60 else "🔴")
    if show_label:
        html = (
            f'<div style="display:flex;align-items:center;gap:8px;">'
            f'<span style="font-size:18px;">{emoji}</span>'
            f'<span style="font-size:13px;font-weight:700;color:{color};">{value:.0f}%</span>'
            f'</div>'
        )
    else:
        html = (
            f'<div style="display:inline-flex;align-items:center;gap:4px;">'
            f'<span style="font-size:16px;">{emoji}</span>'
            f'<span style="font-size:12px;font-weight:700;color:{color};">{value:.0f}</span>'
            f'</div>'
        )
    return html


def create_summary_card(label, count, color, icon):
    html = (
        f'<div style="background:linear-gradient(135deg,{color}15 0%,{color}05 100%);'
        f'border-left:4px solid {color};padding:20px;border-radius:10px;text-align:center;">'
        f'<div style="font-size:48px;margin-bottom:8px;">{icon}</div>'
        f'<div style="font-size:36px;font-weight:700;color:{color};margin-bottom:4px;">{count}</div>'
        f'<div style="font-size:14px;color:#6b7280;font-weight:600;">{label}</div>'
        f'</div>'
    )
    return _html_oneliner(html)


def calculate_readiness_score(row):
    """Unified formula -- mirrors train_models.py. Rescaled 0-100. Walsh 2021 thresholds."""
    sleep_hrs = row.get("sleep_hours", 7.5)
    sleep_q   = row.get("sleep_quality", 7)
    sleep_s   = min(15, (sleep_hrs / 8.0) * 10 + (sleep_q / 10) * 5)
    sore_s    = ((10 - row.get("soreness", 4)) / 10) * 10
    mood_s    = (row.get("mood", 7) / 10) * 5
    stress_s  = ((10 - row.get("stress", 4)) / 10) * 5
    cmj       = row.get("cmj_height_cm")
    pos       = str(row.get("position", "F"))
    bench     = 38 if "G" in pos else (30 if "C" in pos else 34)
    cmj_s     = min(15, (cmj / bench) * 15) if cmj and cmj > 0 else 11
    rsi       = row.get("rsi_modified")
    rsi_s     = min(10, (rsi / 0.45) * 10) if rsi and rsi > 0 else 8
    sched_s   = 10
    if row.get("is_back_to_back", 0): sched_s -= 4
    if row.get("days_rest", 3) <= 1:  sched_s -= 2
    sched_s   = max(0, sched_s)
    raw = sleep_s + sore_s + mood_s + stress_s + cmj_s + rsi_s + sched_s
    return round(min(100, raw * (100 / 70)), 1)


def get_status_color(score):
    if score >= 80:
        return "🟢", "green"
    elif score >= 60:
        return "🟡", "orange"
    else:
        return "🔴", "red"


# ==============================================================================
# GPS HELPER -- z-score flag for a single metric
# ==============================================================================

def _gps_zscore_flag(player_id, col, today_val, training_load_df, ref_date):
    """Returns (emoji, z_score_or_None) based on personal baseline."""
    hist = training_load_df[
        (training_load_df["player_id"] == player_id) &
        (training_load_df["date"] < ref_date) &
        (training_load_df[col] > 0)
    ].tail(30)[col]
    if len(hist) < 5:
        return "🟡", None
    z = (today_val - hist.mean()) / max(hist.std(), 0.1)
    if z <= -2.0:
        return "🔴", z
    elif z <= -1.0:
        return "🟡", z
    else:
        return "🟢", z


def get_gps_row(player_id, training_load_df, ref_date):
    """Return today's GPS row for a player as a dict, or None."""
    row = training_load_df[
        (training_load_df["player_id"] == player_id) &
        (training_load_df["date"] == pd.to_datetime(ref_date))
    ]
    return row.iloc[0].to_dict() if len(row) > 0 else None


def build_gps_flag_notes(player_id, gps_row, training_load_df, ref_date):
    if gps_row is None:
        return []
    notes = []
    decel_val = gps_row.get("decel_count")
    if decel_val is not None:
        decel_emoji, decel_z = _gps_zscore_flag(player_id, "decel_count", decel_val, training_load_df, ref_date)
        if decel_emoji == "🔴" and decel_z is not None:
            notes.append(f"Decel count {decel_val:.0f} -- {abs(decel_z):.1f}σ below personal baseline "
                        f"(cross-reference CMJ/RSI: if also reduced, combined signal warrants action)")
        elif decel_emoji == "🟡" and decel_z is not None:
            notes.append(f"Decel count {decel_val:.0f} -- {abs(decel_z):.1f}σ below personal baseline (monitor)")

    for col, label in [("player_load", "Player Load"), ("accel_count", "Accel Count")]:
        val = gps_row.get(col)
        if val is None:
            continue
        emoji, z = _gps_zscore_flag(player_id, col, val, training_load_df, ref_date)
        if emoji == "🔴" and z is not None:
            notes.append(f"{label} {val:.0f} -- {abs(z):.1f}σ below baseline")
        elif emoji == "🟡" and z is not None:
            notes.append(f"{label} {val:.0f} -- {abs(z):.1f}σ below baseline (mild)")
    return notes


# ==============================================================================
# SHARED Z-SCORE CLASSIFIER  (wellness + CMJ/RSI)
# ==============================================================================

def classify_player_full(player_id, today_wellness_row, today_fp_row, wellness_df, fp_df, ref_date):
    w_history  = wellness_df[(wellness_df["player_id"] == player_id) & (wellness_df["date"] < ref_date)].tail(30)
    fp_history = fp_df[(fp_df["player_id"] == player_id) & (fp_df["date"] < ref_date)].tail(30)

    flags = 0
    notes = []

    if len(w_history) >= 7:
        def wz(col, val, min_std):
            m = w_history[col].mean()
            s = max(w_history[col].std(), min_std)
            return (val - m) / s

        sleep_z = wz("sleep_hours", today_wellness_row["sleep_hours"], 0.3)
        sor_z   = wz("soreness",    today_wellness_row["soreness"],    0.5)
        str_z   = wz("stress",      today_wellness_row["stress"],      0.5)
        mood_z  = wz("mood",        today_wellness_row["mood"],        0.5)

        if today_wellness_row["sleep_hours"] < 7.0:
            flags += 2
            notes.append(f"Sleep {today_wellness_row['sleep_hours']:.1f} hrs -- below safety floor")
        elif sleep_z < -1.5:
            flags += 1
            notes.append(f"Sleep {today_wellness_row['sleep_hours']:.1f} hrs -- {abs(sleep_z):.1f}σ below her norm")

        if today_wellness_row["soreness"] > 7:
            flags += 2
            notes.append(f"Soreness {today_wellness_row['soreness']:.0f}/10 -- above safety ceiling")
        elif sor_z > 1.5:
            flags += 1
            notes.append(f"Soreness {today_wellness_row['soreness']:.0f}/10 -- {sor_z:.1f}σ above her norm")

        if today_wellness_row["stress"] > 7:
            flags += 2
            notes.append(f"Stress {today_wellness_row['stress']:.0f}/10 -- above safety ceiling")
        elif str_z > 1.5:
            flags += 1
            notes.append(f"Stress {today_wellness_row['stress']:.0f}/10 -- {str_z:.1f}σ above her norm")

        if mood_z < -1.5:
            flags += 1
            notes.append(f"Mood {today_wellness_row['mood']:.0f}/10 -- {abs(mood_z):.1f}σ below her norm")
    else:
        if today_wellness_row["sleep_hours"] < 7.0:
            flags += 2; notes.append("Sleep below safety floor (insufficient history for z-score)")
        if today_wellness_row["soreness"] > 7:
            flags += 2; notes.append("Soreness above safety ceiling (insufficient history for z-score)")

    if today_fp_row is not None and len(fp_history) >= 5:
        cmj_val = today_fp_row.get("cmj_height_cm")
        rsi_val = today_fp_row.get("rsi_modified")

        if cmj_val is not None:
            cmj_mean = fp_history["cmj_height_cm"].mean()
            cmj_std  = max(fp_history["cmj_height_cm"].std(), 0.5)
            cmj_z    = (cmj_val - cmj_mean) / cmj_std
            if cmj_z <= -2.0:
                flags += 3
                notes.append(f"CMJ {cmj_val:.1f} cm -- {abs(cmj_z):.1f}σ below baseline (severe neuromuscular fatigue)")
            elif cmj_z <= -1.0:
                flags += 2
                notes.append(f"CMJ {cmj_val:.1f} cm -- {abs(cmj_z):.1f}σ below baseline (neuromuscular fatigue)")

        if rsi_val is not None:
            rsi_mean = fp_history["rsi_modified"].mean()
            rsi_std  = max(fp_history["rsi_modified"].std(), 0.01)
            rsi_z    = (rsi_val - rsi_mean) / rsi_std
            if rsi_z <= -2.0:
                flags += 3
                notes.append(f"RSI {rsi_val:.2f} -- {abs(rsi_z):.1f}σ below baseline (reduced reactive strength)")
            elif rsi_z <= -1.0:
                flags += 2
                notes.append(f"RSI {rsi_val:.2f} -- {abs(rsi_z):.1f}σ below baseline")

    if not notes:
        notes.append("No flags -- within normal range across all metrics including force plate")

    status = "green" if flags == 0 else ("yellow" if flags <= 3 else "red")
    return status, flags, notes

# ==============================================================================
# TAB 1: TODAY'S READINESS
# ==============================================================================

def enhanced_todays_readiness_tab(wellness_df, players_df, fp_df, training_load_df, end_date):
    st.header("Today's Readiness Status")
    st.caption(f"📅 {end_date.strftime('%B %d, %Y')}")

    _qa1, _qa2, _qa3 = st.columns(3)
    with _qa1:
        if st.button("Email At-Risk Players", width='stretch', key="qa_email_top"):
            st.info("At-risk player list will populate once data loads below.")
    with _qa2:
        st.download_button(
            "Export Today's Report (CSV)",
            data="name,status\nLoading...",
            file_name=f"readiness_{pd.Timestamp(end_date).strftime('%Y%m%d')}.csv",
            mime="text/csv",
            width='stretch',
            key="qa_export_top"
        )
    with _qa3:
        if st.button("Create Training Alert", width='stretch', key="qa_alert_top"):
            st.info("Training alert will populate once data loads below.")
    st.markdown("---")

    today_wellness = wellness_df[wellness_df["date"] == pd.to_datetime(end_date)].copy()
    cols = ["player_id", "name"] + (["position"] if "position" in players_df.columns else [])
    today_wellness = today_wellness.merge(players_df[cols], on="player_id", how="left")
    if "position" not in today_wellness.columns:
        today_wellness["position"] = ""

    if len(today_wellness) == 0:
        st.info("No data available for selected date")
        return

    latest_fp  = fp_df[fp_df["date"] == pd.to_datetime(end_date)]
    ref_date   = pd.to_datetime(end_date)

    has_gps = "player_load" in training_load_df.columns
    gps_coverage = 0
    if has_gps:
        today_gps = training_load_df[training_load_df["date"] == ref_date]
        gps_coverage = len(today_gps["player_id"].unique())

    def get_fp_row(pid):
        row = latest_fp[latest_fp["player_id"] == pid]
        return row.iloc[0].to_dict() if len(row) > 0 else None

    results = today_wellness.apply(
        lambda r: pd.Series(
            classify_player_full(r["player_id"], r, get_fp_row(r["player_id"]), wellness_df, fp_df, ref_date),
            index=["zscore_status", "flag_count", "flag_notes"],
        ),
        axis=1,
    )
    today_wellness = pd.concat([today_wellness, results], axis=1)

    green_count  = (today_wellness["zscore_status"] == "green").sum()
    yellow_count = (today_wellness["zscore_status"] == "yellow").sum()
    red_count    = (today_wellness["zscore_status"] == "red").sum()
    avg_sleep    = today_wellness["sleep_hours"].mean()
    sleep_icon   = "🟢" if avg_sleep >= 8 else ("🟡" if avg_sleep >= 7 else "🔴")
    fp_coverage  = len(latest_fp["player_id"].unique())

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(create_summary_card("Ready",     green_count,         "#10b981", "🟢"), unsafe_allow_html=True)
    with c2:
        st.markdown(create_summary_card("Monitor",   yellow_count,        "#f59e0b", "🟡"), unsafe_allow_html=True)
    with c3:
        st.markdown(create_summary_card("At Risk",   red_count,           "#ef4444", "🔴"), unsafe_allow_html=True)
    with c4:
        st.markdown(create_summary_card("Avg Sleep", f"{avg_sleep:.1f}h", "#3b82f6", sleep_icon), unsafe_allow_html=True)

    coverage_parts = [f"Force plate: {fp_coverage}/{len(today_wellness)} athletes"]
    if has_gps:
        coverage_parts.append(f"GPS/Kinexon: {gps_coverage}/{len(today_wellness)} athletes")
    st.caption(" · ".join(coverage_parts) + ". CMJ/RSI deviations weighted higher than subjective wellness.")
    st.markdown("---")

    today_wellness["readiness_score"] = today_wellness.apply(calculate_readiness_score, axis=1)
    today_wellness["sleep_pct"]    = (today_wellness["sleep_hours"] / 8 * 100).clip(0, 100)
    today_wellness["physical_pct"] = ((10 - today_wellness["soreness"]) / 10 * 100)
    today_wellness["mental_pct"]   = (today_wellness["mood"] / 10 * 100)
    today_wellness["stress_pct"]   = ((10 - today_wellness["stress"]) / 10 * 100)
    today_wellness["status"]       = today_wellness["zscore_status"].map(
        {"green": "🟢 Ready", "yellow": "🟡 Monitor", "red": "🔴 At Risk"}
    )
    today_wellness["status_color"] = today_wellness["zscore_status"].map(
        {"green": "green", "yellow": "orange", "red": "red"}
    )
    today_wellness = today_wellness.sort_values("flag_count", ascending=False)

    st.subheader("Player Details")
    view_mode = st.radio("View mode:", ["Compact (Battery View)", "Detailed (Full Metrics)"], horizontal=True, label_visibility="collapsed")

    if view_mode == "Compact (Battery View)":
        if HAVE_IMPROVED_GAUGES:
            for _, player in today_wellness.iterrows():
                metrics = {
                    "sleep":    player["sleep_pct"],
                    "physical": player["physical_pct"],
                    "mental":   player["mental_pct"],
                    "stress":   player["stress_pct"],
                }
                st.markdown(
                    create_player_card_compact(player["name"], player["position"], player["readiness_score"], metrics),
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                _html_oneliner(textwrap.dedent("""
                    <style>
                    .player-row{display:flex;align-items:center;padding:12px;margin:8px 0;background:#fff;
                                border-radius:8px;border:1px solid #e5e7eb;}
                    .player-name{font-size:16px;font-weight:600;min-width:120px;}
                    .player-position{font-size:12px;color:#6b7280;min-width:40px;}
                    .battery-container{display:flex;gap:12px;flex:1;}
                    .battery-item{flex:1;text-align:center;}
                    .battery-label{font-size:11px;color:#6b7280;margin-bottom:4px;}
                    </style>
                """)),
                unsafe_allow_html=True,
            )
            for _, player in today_wellness.iterrows():
                bg      = "#d1fae5" if player["readiness_score"] >= 80 else ("#fef3c7" if player["readiness_score"] >= 60 else "#fee2e2")
                fp_row  = get_fp_row(player["player_id"])
                gps_row = get_gps_row(player["player_id"], training_load_df, ref_date) if has_gps else None

                cmj_str   = f"{fp_row['cmj_height_cm']:.1f} cm"  if fp_row  else "--"
                rsi_str   = f"{fp_row['rsi_modified']:.2f}"       if fp_row  else "--"

                if gps_row and has_gps:
                    load_emoji, _ = _gps_zscore_flag(player["player_id"], "player_load", gps_row.get("player_load", 0), training_load_df, ref_date)
                    accel_emoji, _= _gps_zscore_flag(player["player_id"], "accel_count", gps_row.get("accel_count", 0), training_load_df, ref_date)
                    decel_emoji, _= _gps_zscore_flag(player["player_id"], "decel_count", gps_row.get("decel_count", 0), training_load_df, ref_date)
                    load_str  = f"{load_emoji} {gps_row.get('player_load', 0):.0f}"
                    accel_str = f"{accel_emoji} {gps_row.get('accel_count', 0):.0f}"
                    decel_str = f"{decel_emoji} {gps_row.get('decel_count', 0):.0f}"
                else:
                    load_str = accel_str = decel_str = "--"

                gps_cells = (
                    f'<div class="battery-item"><div class="battery-label">Load</div>'
                    f'<span style="font-size:12px;font-weight:700;">{load_str}</span></div>'
                    f'<div class="battery-item"><div class="battery-label">Accels</div>'
                    f'<span style="font-size:12px;font-weight:700;">{accel_str}</span></div>'
                    f'<div class="battery-item"><div class="battery-label">Decels</div>'
                    f'<span style="font-size:12px;font-weight:700;">{decel_str}</span></div>'
                ) if has_gps else ""

                row_html = (
                    f'<div class="player-row">'
                    f'<div style="display:flex;align-items:center;gap:12px;min-width:280px;">'
                    f'<span class="player-name">{player["name"]}</span>'
                    f'<span class="player-position">{player["position"]}</span>'
                    f'<span style="background-color:{bg};padding:4px 12px;border-radius:12px;font-size:14px;font-weight:600;">{player["status"]}</span>'
                    f'</div>'
                    f'<div class="battery-container">'
                    f'<div class="battery-item"><div class="battery-label">Sleep</div>{create_mini_battery(player["sleep_pct"], show_label=False)}</div>'
                    f'<div class="battery-item"><div class="battery-label">Physical</div>{create_mini_battery(player["physical_pct"], show_label=False)}</div>'
                    f'<div class="battery-item"><div class="battery-label">Mental</div>{create_mini_battery(player["mental_pct"], show_label=False)}</div>'
                    f'<div class="battery-item"><div class="battery-label">Stress</div>{create_mini_battery(player["stress_pct"], show_label=False)}</div>'
                    f'<div class="battery-item"><div class="battery-label">CMJ</div><span style="font-size:12px;font-weight:700;">{cmj_str}</span></div>'
                    f'<div class="battery-item"><div class="battery-label">RSI</div><span style="font-size:12px;font-weight:700;">{rsi_str}</span></div>'
                    f'{gps_cells}'
                    f'</div>'
                    f'</div>'
                )
                st.markdown(_html_oneliner(row_html), unsafe_allow_html=True)

    else:
        for _, player in today_wellness.iterrows():
            emoji   = "🟢" if player["readiness_score"] >= 80 else ("🟡" if player["readiness_score"] >= 60 else "🔴")
            fp_row  = get_fp_row(player["player_id"])
            gps_row = get_gps_row(player["player_id"], training_load_df, ref_date) if has_gps else None

            with st.expander(f"{emoji} **{player['name']}** ({player['position']}) -- Score: {player['readiness_score']:.0f}/100"):
                colA, colB, colC = st.columns([2, 1, 1])

                with colA:
                    st.markdown("**Wellness Metrics**")
                    st.markdown(f"**Sleep:** {create_mini_battery(player['sleep_pct'])}", unsafe_allow_html=True)
                    st.caption(f"{player['sleep_hours']:.1f} hours")
                    st.markdown(f"**Physical:** {create_mini_battery(player['physical_pct'])}", unsafe_allow_html=True)
                    st.caption(f"Soreness: {player['soreness']:.0f}/10")
                    st.markdown(f"**Mental:** {create_mini_battery(player['mental_pct'])}", unsafe_allow_html=True)
                    st.caption(f"Mood: {player['mood']:.0f}/10")
                    st.markdown(f"**Stress:** {create_mini_battery(player['stress_pct'])}", unsafe_allow_html=True)
                    st.caption(f"Stress: {player['stress']:.0f}/10")

                with colB:
                    st.markdown("**Force Plate**")
                    if fp_row:
                        st.metric("CMJ Height",   f"{fp_row['cmj_height_cm']:.1f} cm")
                        st.metric("RSI-Modified", f"{fp_row['rsi_modified']:.2f}")
                    else:
                        st.caption("No force plate data today")
                    st.markdown("**Raw Wellness**")
                    st.metric("Sleep",    f"{player['sleep_hours']:.1f} hrs")
                    st.metric("Soreness", f"{player['soreness']:.0f}/10")
                    st.metric("Stress",   f"{player['stress']:.0f}/10")
                    st.metric("Mood",     f"{player['mood']:.0f}/10")

                with colC:
                    st.markdown("**GPS / Kinexon**")
                    if gps_row and has_gps:
                        pl_val    = gps_row.get("player_load", 0)
                        ac_val    = gps_row.get("accel_count", 0)
                        dc_val    = gps_row.get("decel_count", 0)

                        pl_emoji, pl_z = _gps_zscore_flag(player["player_id"], "player_load", pl_val, training_load_df, ref_date)
                        ac_emoji, ac_z = _gps_zscore_flag(player["player_id"], "accel_count", ac_val, training_load_df, ref_date)
                        dc_emoji, dc_z = _gps_zscore_flag(player["player_id"], "decel_count", dc_val, training_load_df, ref_date)

                        pl_delta = f"{pl_z:+.1f}σ" if pl_z is not None else "--"
                        ac_delta = f"{ac_z:+.1f}σ" if ac_z is not None else "--"
                        dc_delta = f"{dc_z:+.1f}σ" if dc_z is not None else "--"

                        st.metric("Player Load",  f"{pl_emoji} {pl_val:.0f}",  delta=pl_delta, delta_color="off")
                        st.metric("Accel Count",  f"{ac_emoji} {ac_val:.0f}",  delta=ac_delta, delta_color="off")
                        st.metric("Decel Count",  f"{dc_emoji} {dc_val:.0f}",  delta=dc_delta, delta_color="off")

                        if gps_row.get("game_minutes", 0) > 0:
                            st.caption(f"Game day -- {gps_row['game_minutes']:.0f} min played")
                        elif gps_row.get("practice_minutes", 0) > 0:
                            st.caption(f"Practice -- {gps_row['practice_minutes']:.0f} min @ RPE {gps_row.get('practice_rpe', 0):.1f}")
                    else:
                        st.caption("No GPS data today")

                st.markdown("---")
                st.markdown("**Flags:**")
                for note in player["flag_notes"]:
                    st.write(f"• {note}")
                if gps_row and has_gps:
                    gps_notes = build_gps_flag_notes(player["player_id"], gps_row, training_load_df, ref_date)
                    for note in gps_notes:
                        st.write(f"• 📡 {note}")

# ==============================================================================
# TAB 5: AVAILABILITY & INJURIES
# ==============================================================================

def availability_injuries_tab(availability_df, injuries_df, players_df, end_date):
    st.header("Availability & Injury Tracker")
    latest_date = pd.to_datetime(end_date)

    st.subheader("Today's Availability")

    if len(availability_df) > 0:
        today_av = (
            availability_df[availability_df["date"] == latest_date]
            .merge(players_df[["player_id", "name", "position"]], on="player_id", how="left")
        )
        if len(today_av) > 0:
            out_count          = (today_av["status"] == "OUT").sum()
            questionable_count = (today_av["status"] == "QUESTIONABLE").sum()
            available_count    = (today_av["status"] == "AVAILABLE").sum()

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Available",     available_count)
            c2.metric("Questionable",  questionable_count)
            c3.metric("Out",           out_count)
            c4.metric("Availability %", f"{(available_count / len(today_av) * 100):.0f}%")
            st.markdown("---")

            for _, row in today_av.sort_values("status").iterrows():
                color = {"AVAILABLE": "#10b981", "QUESTIONABLE": "#f59e0b", "OUT": "#ef4444"}.get(row["status"], "#6b7280")
                bg    = {"AVAILABLE": "#d1fae5",  "QUESTIONABLE": "#fef3c7",  "OUT": "#fee2e2"}.get(row["status"], "#f3f4f6")
                html  = _html_oneliner(
                    f'<div style="display:flex;align-items:center;justify-content:space-between;'
                    f'background:{bg};border-left:5px solid {color};padding:12px 16px;'
                    f'border-radius:6px;margin:5px 0;">'
                    f'<div>'
                    f'<span style="font-weight:700;font-size:14px;color:#1f2937;">{row["name"]}</span>'
                    f'<span style="font-size:12px;color:#6b7280;margin-left:10px;">{row["position"]}</span>'
                    f'</div>'
                    f'<div style="display:flex;gap:20px;align-items:center;">'
                    f'<span style="font-size:12px;color:#6b7280;">Practice: <b>{row["practice_status"]}</b></span>'
                    f'<span style="font-size:13px;font-weight:800;color:{color};">{row["status"]}</span>'
                    f'</div>'
                    f'</div>'
                )
                st.markdown(html, unsafe_allow_html=True)
        else:
            st.info("No availability data for selected date.")
    else:
        st.info("No availability table found. Run generate_demo_data.py to populate.")

    st.markdown("---")
    st.subheader("Season Availability %")
    st.caption("Days available out of total days in season. Target: >85%")

    if len(availability_df) > 0:
        season_av = (
            availability_df.groupby("player_id")
            .apply(lambda x: pd.Series({
                "days_available":    (x["status"] == "AVAILABLE").sum(),
                "days_questionable": (x["status"] == "QUESTIONABLE").sum(),
                "days_out":          (x["status"] == "OUT").sum(),
                "total_days":        len(x),
            }), include_groups=False)
            .reset_index()
            .merge(players_df[["player_id", "name", "position"]], on="player_id")
        )
        season_av["availability_pct"] = (season_av["days_available"] / season_av["total_days"] * 100).round(1)
        season_av = season_av.sort_values("availability_pct")

        bar_colors = season_av["availability_pct"].apply(
            lambda x: "#10b981" if x >= 85 else ("#f59e0b" if x >= 70 else "#ef4444")
        ).tolist()

        fig = go.Figure(go.Bar(
            x=season_av["availability_pct"],
            y=season_av["name"],
            orientation="h",
            marker_color=bar_colors,
            text=season_av["availability_pct"].apply(lambda x: f"{x:.1f}%"),
            textposition="outside",
        ))
        fig.add_vline(x=85, line_dash="dash", line_color="#6b7280",
                      annotation_text="85% target", annotation_position="top right")
        fig.update_layout(
            height=380, margin=dict(l=10, r=60, t=20, b=20),
            xaxis=dict(range=[0, 110], title="Availability %"),
            yaxis=dict(title=""),
        )
        st.plotly_chart(fig, width='stretch')

    st.markdown("---")
    st.subheader("Injury Log")

    if len(injuries_df) > 0:
        inj_display = injuries_df.merge(players_df[["player_id", "name"]], on="player_id")

        for _, inj in inj_display.iterrows():
            ret = (inj["return_date"].strftime("%b %d")
                   if "return_date" in inj.index and pd.notna(inj["return_date"]) else "TBD")
            with st.expander(
                f"🚨 **{inj['name']}** -- {inj['injury_type']} · "
                f"{inj['injury_date'].strftime('%b %d, %Y')} · {inj.get('severity', '')}"
            ):
                c1, c2, c3 = st.columns(3)
                c1.metric("Injury Date", inj["injury_date"].strftime("%B %d, %Y"))
                c2.metric("Days Missed", inj["days_missed"])
                c3.metric("Return Date", ret)

                st.markdown("**Wellness 7 Days Before Injury:**")
                pre = wellness[
                    (wellness["player_id"] == inj["player_id"]) &
                    (wellness["date"] >= inj["injury_date"] - timedelta(days=7)) &
                    (wellness["date"] <= inj["injury_date"])
                ].sort_values("date")

                if len(pre) > 0:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=pre["date"], y=pre["sleep_hours"], name="Sleep (hrs)",  mode="lines+markers", line=dict(color="#2E86AB", width=2)))
                    fig.add_trace(go.Scatter(x=pre["date"], y=pre["soreness"],    name="Soreness /10", mode="lines+markers", line=dict(color="#ef4444", width=2), yaxis="y2"))
                    fig.update_layout(
                        yaxis =dict(title="Sleep Hours"),
                        yaxis2=dict(title="Soreness", overlaying="y", side="right"),
                        height=260, hovermode="x unified",
                    )
                    st.plotly_chart(fig, width='stretch')
    else:
        st.success("No injuries recorded this season")

# ==============================================================================
# TAB 6: GPS & LOAD
# ==============================================================================

def gps_load_tab(training_load_df, players_df, end_date):
    st.header("GPS & Load Monitoring")
    st.caption("Kinexon tracking -- distance, high-speed running, sprint, accel/decel, player load.")

    if "total_distance_km" not in training_load_df.columns:
        st.warning("GPS fields not found. Run generate_demo_data.py to populate them.")
        return

    latest_date = training_load_df["date"].max()
    today_load  = (
        training_load_df[training_load_df["date"] == latest_date]
        .merge(players_df[["player_id", "name", "position"]], on="player_id", how="left")
    )

    if len(today_load) == 0:
        st.info("No GPS data for latest date.")
        return

    st.subheader("Team Summary -- Today")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Avg Distance",    f"{today_load['total_distance_km'].mean():.1f} km")
    c2.metric("Avg HSR",         f"{today_load['hsr_distance_m'].mean():.0f} m")
    c3.metric("Avg Sprint",      f"{today_load['sprint_distance_m'].mean():.0f} m")
    c4.metric("Avg Player Load", f"{today_load['player_load'].mean():.0f}")
    c5.metric("Avg Accels",      f"{today_load['accel_count'].mean():.0f}")
    st.markdown("---")

    st.subheader("Individual GPS -- Today")

    def gps_flag(player_id, col, today_val):
        hist = training_load_df[
            (training_load_df["player_id"] == player_id) &
            (training_load_df["date"] < latest_date) &
            (training_load_df[col] > 0)
        ].tail(30)[col]
        if len(hist) < 5: return "🟡"
        z = (today_val - hist.mean()) / max(hist.std(), 0.1)
        return "🔴" if z <= -2.0 else ("🟡" if z <= -1.0 else "🟢")

    for _, row in today_load.sort_values("player_load", ascending=False).iterrows():
        l_flag = gps_flag(row["player_id"], "player_load",        row["player_load"])
        d_flag = gps_flag(row["player_id"], "total_distance_km",  row["total_distance_km"])
        h_flag = gps_flag(row["player_id"], "hsr_distance_m",     row["hsr_distance_m"])

        with st.expander(
            f"{l_flag} **{row['name']}** ({row['position']})  --  "
            f"Load: {row['player_load']:.0f}  ·  Dist: {row['total_distance_km']:.1f} km  ·  HSR: {row['hsr_distance_m']:.0f} m"
        ):
            g1, g2, g3, g4, g5, g6 = st.columns(6)
            g1.metric("Distance",    f"{row['total_distance_km']:.1f} km")
            g2.metric("HSR",         f"{row['hsr_distance_m']:.0f} m")
            g3.metric("Sprint",      f"{row['sprint_distance_m']:.0f} m")
            g4.metric("Accels",      f"{row['accel_count']}")
            g5.metric("Decels",      f"{row['decel_count']}")
            g6.metric("Player Load", f"{row['player_load']:.0f}")
            if row["game_minutes"] > 0:
                st.caption(f"Game day -- {row['game_minutes']:.0f} min played")
            else:
                st.caption(f"Practice -- {row['practice_minutes']:.0f} min @ RPE {row['practice_rpe']:.1f}")

    st.markdown("---")
    st.subheader("14-Day GPS Trends")
    athlete_list = sorted(players_df["name"].tolist())
    sel = st.multiselect("Select athletes", athlete_list, default=athlete_list[:4], key="gps_trend_select")

    if sel:
        sel_ids  = players_df[players_df["name"].isin(sel)]["player_id"].tolist()
        cutoff   = latest_date - pd.Timedelta(days=14)
        trend_df = (
            training_load_df[
                (training_load_df["player_id"].isin(sel_ids)) &
                (training_load_df["date"] >= cutoff)
            ]
            .merge(players_df[["player_id", "name"]], on="player_id")
            .sort_values(["player_id", "date"])
        )

        COLORS = ["#2E86AB", "#A23B72", "#F18F01", "#C73E1D", "#3B1F2B", "#44BBA4"]

        def gps_chart(metric_col, title, y_label):
            fig = go.Figure()
            for i, name in enumerate(sel):
                sub = trend_df[trend_df["name"] == name]
                fig.add_trace(go.Scatter(
                    x=sub["date"], y=sub[metric_col],
                    mode="lines+markers", name=name,
                    line=dict(color=COLORS[i % len(COLORS)], width=2),
                ))
            fig.update_layout(
                title=title, height=280,
                yaxis=dict(title=y_label),
                hovermode="x unified",
                margin=dict(l=10, r=10, t=40, b=10),
                legend=dict(orientation="h", y=-0.3),
            )
            return fig

        t1, t2 = st.columns(2)
        with t1:
            st.plotly_chart(gps_chart("total_distance_km", "Total Distance (km)", "km"), width='stretch')
        with t2:
            st.plotly_chart(gps_chart("hsr_distance_m", "High-Speed Running (m, >18 km/h)", "m"), width='stretch')

        t3, t4 = st.columns(2)
        with t3:
            st.plotly_chart(gps_chart("player_load", "Player Load", "AU"), width='stretch')
        with t4:
            fig = go.Figure()
            for i, name in enumerate(sel):
                sub = trend_df[trend_df["name"] == name]
                fig.add_trace(go.Bar(
                    x=sub["date"], y=sub["accel_count"],
                    name=name, marker_color=COLORS[i % len(COLORS)], opacity=0.75,
                ))
            fig.update_layout(
                title="Accel Count", height=280, barmode="group",
                hovermode="x unified",
                margin=dict(l=10, r=10, t=40, b=10),
                legend=dict(orientation="h", y=-0.3),
            )
            st.plotly_chart(fig, width='stretch')

    st.markdown("---")
    st.subheader("Player Load ACWR")
    st.caption("Acute:Chronic workload ratio using GPS player load. Optimal zone: 0.8–1.3")

    acwr_gps_rows = []
    for pid in players_df["player_id"].tolist():
        p_loads = (
            training_load_df[training_load_df["player_id"] == pid]
            .sort_values("date")[["date", "player_load"]]
        )
        if len(p_loads) >= 14:
            acute_mean   = p_loads.tail(7)["player_load"].mean()
            chronic_mean = p_loads.tail(28)["player_load"].mean()
            ratio        = acute_mean / chronic_mean if chronic_mean > 0 else 1.0
            pname        = players_df[players_df["player_id"] == pid]["name"].values[0]
            acwr_gps_rows.append({"name": pname, "acwr_gps": round(ratio, 2)})

    if acwr_gps_rows:
        acwr_df    = pd.DataFrame(acwr_gps_rows).sort_values("acwr_gps", ascending=False)
        bar_colors = acwr_df["acwr_gps"].apply(
            lambda x: "#10b981" if 0.8 <= x <= 1.3 else ("#f59e0b" if x <= 1.5 else "#ef4444")
        ).tolist()
        fig = go.Figure(go.Bar(
            x=acwr_df["name"], y=acwr_df["acwr_gps"],
            marker_color=bar_colors,
            text=acwr_df["acwr_gps"].apply(lambda x: f"{x:.2f}"),
            textposition="outside",
        ))
        fig.add_hline(y=0.8, line_dash="dash", line_color="#10b981", annotation_text="0.8 low")
        fig.add_hline(y=1.3, line_dash="dash", line_color="#f59e0b", annotation_text="1.3 caution")
        fig.add_hline(y=1.5, line_dash="dash", line_color="#ef4444", annotation_text="1.5 high risk")
        fig.update_layout(
            height=320,
            yaxis=dict(title="Player Load ACWR", range=[0, 2.2]),
            margin=dict(l=10, r=10, t=20, b=10),
        )
        st.plotly_chart(fig, width='stretch')

# ==============================================================================
# SMART QUERY FUNCTIONS
# ==============================================================================

def get_latest_date():
    return wellness["date"].max()

def query_poor_sleep(threshold=7.0):
    latest_date = get_latest_date()
    df = wellness[wellness["date"] == latest_date].copy()
    df = df[df["sleep_hours"] < threshold].merge(players[["player_id", "name"]], on="player_id")
    return df[["name", "sleep_hours", "soreness", "stress"]].sort_values("sleep_hours")

def query_high_risk():
    latest_date = get_latest_date()
    df = wellness[wellness["date"] == latest_date].copy()
    df = df.merge(players[["player_id", "name", "injury_history_count"]], on="player_id")
    df["high_risk"] = (df["sleep_hours"] < 7.0) | (df["soreness"] > 7) | (df["stress"] > 7)
    return df[df["high_risk"]][["name", "sleep_hours", "soreness", "stress", "injury_history_count"]]

def query_readiness_scores():
    latest_date = get_latest_date()
    df = wellness[wellness["date"] == latest_date].copy()
    df = df.merge(players[["player_id", "name"]], on="player_id")
    df["readiness_score"] = df.apply(calculate_readiness_score, axis=1)
    return df[["name", "sleep_hours", "soreness", "stress", "mood", "readiness_score"]].sort_values("readiness_score")

def query_position_comparison():
    latest_date = get_latest_date()
    df   = wellness[wellness["date"] == latest_date].copy()
    keep = ["player_id", "name"] + (["position"] if "position" in players.columns else [])
    df   = df.merge(players[keep], on="player_id")
    if "position" not in df.columns:
        df["position"] = "NA"
    comparison = df.groupby("position").agg({
        "sleep_hours": "mean", "soreness": "mean",
        "stress": "mean", "mood": "mean", "player_id": "count",
    }).round(1)
    comparison.columns = ["avg_sleep", "avg_soreness", "avg_stress", "avg_mood", "count"]
    return comparison.reset_index()

def parse_query(user_input):
    user_input = user_input.lower().strip()
    if any(w in user_input for w in ["poor sleep", "bad sleep", "tired", "sleep"]):
        return "poor_sleep"
    elif any(w in user_input for w in ["high risk", "at risk", "injury risk"]):
        return "high_risk"
    elif any(w in user_input for w in ["readiness", "ready"]):
        return "readiness"
    elif "compare position" in user_input or "position comparison" in user_input:
        return "position_comparison"
    elif any(w in user_input for w in ["back to back", "back-to-back", "b2b", "schedule", "rest"]):
        return "back_to_back"
    return "unknown"

def generate_smart_response(query_type):
    if query_type == "poor_sleep":
        df = query_poor_sleep()
        if len(df) == 0:
            return "No players had poor sleep (<7 hrs) last night.", None
        st.subheader(f"{len(df)} Players with Poor Sleep")
        st.dataframe(df, width='stretch')
        response = f"**{len(df)} players** had poor sleep:\n\n" + "".join(f"- {r['name']}: {r['sleep_hours']:.1f} hrs\n" for _, r in df.iterrows())
        response += "\nResearch: Sleep <7 hrs → elevated injury risk (Walsh 2021 BJSM consensus, 2025 meta-analysis OR=1.34)"
        return response, df
    elif query_type == "high_risk":
        df = query_high_risk()
        if len(df) == 0:
            return "No players currently showing high injury risk indicators.", None
        st.subheader(f"{len(df)} Players at Elevated Risk")
        st.dataframe(df, width='stretch')
        response = f"**{len(df)} players** showing elevated risk:\n\n" + "".join(f"- {r['name']}: Sleep {r['sleep_hours']:.1f} hrs, Soreness {r['soreness']}/10\n" for _, r in df.iterrows())
        return response, df
    elif query_type == "readiness":
        df = query_readiness_scores()
        st.subheader("Readiness Scores")
        st.dataframe(df, width='stretch')
        green  = len(df[df["readiness_score"] >= 80])
        yellow = len(df[(df["readiness_score"] >= 60) & (df["readiness_score"] < 80)])
        red    = len(df[df["readiness_score"] < 60])
        return f"🟢 Ready: {green} | 🟡 Monitor: {yellow} | 🔴 At Risk: {red}", df
    elif query_type == "position_comparison":
        df = query_position_comparison()
        st.subheader("Position Comparison")
        fig = px.bar(df, x="position", y=["avg_sleep", "avg_soreness"], barmode="group", title="Metrics by Position")
        st.plotly_chart(fig, width='stretch')
        st.dataframe(df, width='stretch')
        return "Position comparison complete", df
    elif query_type == "back_to_back":
        latest_date = get_latest_date()
        try:
            from pathlib import Path as _p
            import sqlite3 as _sq
            conn = _sq.connect("waims_demo.db")
            sched = pd.read_sql_query(
                f"SELECT * FROM schedule WHERE date >= date('{latest_date.strftime('%Y-%m-%d')}', '-7 days')",
                conn)
            conn.close()
            sched["date"] = pd.to_datetime(sched["date"])
            b2b = sched[sched["is_back_to_back"] == 1]
            if len(b2b) > 0:
                response = f"**{len(b2b)} back-to-back game(s)** in the next 7 days:\n\n"
                for _, row in b2b.iterrows():
                    response += f"- {row['date'].strftime('%b %d')} vs {row.get('opponent','TBD')} — B2B game\n"
                response += "\nConsider lighter sessions before B2B nights. Load Projection (Forecast tab) shows readiness impact."
                st.subheader("Upcoming Back-to-Backs")
                st.dataframe(b2b[["date","opponent","days_rest"]].rename(columns={"days_rest":"Days Rest"}), width="stretch")
                return response, b2b
            else:
                return "No back-to-back games in the next 7 days. Schedule looks manageable.", None
        except Exception:
            return "Schedule data not available — run generate_database.py to populate schedule table.", None
    else:
        return "Try: 'poor sleep', 'high risk', 'readiness', 'compare positions', or 'back to back'", None


# ==============================================================================
# DATE
# ==============================================================================

if len(wellness) > 0:
    end_date = pd.Timestamp(wellness["date"].max())
else:
    end_date = pd.Timestamp(datetime.today())

try:
    _pcsv = pd.read_csv("data/processed_data.csv")
    _pcsv["date"] = pd.to_datetime(_pcsv["date"]).dt.date
    ml_predictions = _pcsv[["player_id", "date", "readiness_score", "injury_risk_score"]].copy()
except Exception:
    ml_predictions = pd.DataFrame(columns=["player_id", "date", "readiness_score", "injury_risk_score"])

start_date = end_date

# ==============================================================================
# AUTH GATE
# ==============================================================================

if not is_authenticated():
    render_login_page()
    st.stop()

# User badge in sidebar
render_user_badge()

# ==============================================================================
# MAIN DASHBOARD
# ==============================================================================

role = current_role()

# Role-aware title strip
role_color = {
    "head_coach": "#1e3a5f", "asst_coach": "#2563eb",
    "sport_scientist": "#059669", "medical": "#7c3aed", "gm": "#b45309",
    "athlete": "#0f766e",
}.get(role, "#6b7280")
role_label = {
    "head_coach": "Head Coach", "asst_coach": "Asst. Coach",
    "sport_scientist": "Sport Scientist", "medical": "Medical / AT",
    "gm": "General Manager", "athlete": "Athlete"
}.get(role, role)

st.markdown(
    f'<div style="display:flex;align-items:center;gap:14px;margin-bottom:6px;">'
    f'<span style="font-size:24px;font-weight:800;color:#1e3a5f;">🏀 WAIMS</span>'
    f'<span style="background:{role_color};color:white;padding:3px 12px;border-radius:12px;'
    f'font-size:12px;font-weight:700;">{role_label}</span>'
    f'<span style="font-size:13px;color:#64748b;">{end_date.strftime("%B %d, %Y")}</span>'
    f'</div>',
    unsafe_allow_html=True
)

# GMs get a focused banner instead of full tab nav
if role == "gm":
    st.info("**Executive View** — You can see roster availability and the Command Center summary. "
            "Detailed wellness, force plate, and raw load data are restricted to performance staff.")
elif role == "athlete":
    st.info("**Athlete View** — This page shows only your own readiness, trends, and recovery guidance.")

# Build visible tab list for this role
visible = get_visible_tabs()   # list of (key, label)
tab_keys   = [v[0] for v in visible]
tab_labels = [v[1] for v in visible]

rendered_tabs = st.tabs(tab_labels)
tab_map = dict(zip(tab_keys, rendered_tabs))

if "ath" in tab_map:
    with tab_map["ath"]:
        athlete_home_view(
            current_athlete_player_id(),
            wellness,
            players,
            force_plate,
            training_load,
            end_date,
        )

# ── Command Center ────────────────────────────────────────────────────────────
if "cc" in tab_map:
    with tab_map["cc"]:
        if role == "gm":
            # GM sees readiness summary only — no raw wellness, no minutes detail
            st.subheader("Roster Availability Summary")
            st.caption("Executive view — traffic lights and availability only.")
            today = wellness[wellness["date"] == pd.to_datetime(end_date)].copy()
            today = today.merge(players[["player_id", "name", "position"]], on="player_id", how="left")
            today["readiness_score"] = (
                (today["sleep_hours"] / 8) * 30
                + ((10 - today["soreness"]) / 10) * 25
                + ((10 - today["stress"]) / 10) * 25
                + (today["mood"] / 10) * 20
            )
            today["status"] = today["readiness_score"].apply(
                lambda x: "🟢 Ready" if x >= 80 else ("🟡 Monitor" if x >= 60 else "🔴 Protect"))
            st.dataframe(
                today[["name", "position", "status"]].sort_values("name"),
                hide_index=True, width='stretch'
            )
            st.caption("Detailed wellness scores, load data, and force plate metrics are restricted to performance staff.")
        else:
            coach_command_center(wellness, players, force_plate, training_load, acwr, end_date,
                                 ml_predictions=ml_predictions)

# ── Today's Readiness ─────────────────────────────────────────────────────────
if "rd" in tab_map:
    with tab_map["rd"]:
        da = data_access()
        if not da["show_raw_wellness"]:
            st.warning("Raw wellness data (sleep, soreness, stress, mood) is restricted to Performance and Medical staff.")
        else:
            enhanced_todays_readiness_tab(wellness, players, force_plate, training_load, end_date)

# ── Athlete Profiles ──────────────────────────────────────────────────────────
if "ap" in tab_map:
    with tab_map["ap"]:
        athlete_profile_tab(wellness, training_load, acwr, force_plate, players, injuries)

# ==============================================================================
# TAB 3: TRENDS
# ==============================================================================

if "tr" in tab_map:
    with tab_map["tr"]:
        st.header("Trends & Load")
        st.caption("Raw daily values (faint) with 7-day rolling average (bold). Subjective + objective signals side by side.")

        if len(wellness) > 0:
            athlete_list = sorted(players["name"].tolist())
            col_sel, col_days = st.columns([2, 1])
            with col_sel:
                selected = st.multiselect("Select athletes", athlete_list, default=athlete_list[:4], key="trends_athlete_select")
            with col_days:
                lookback = st.selectbox("Window", [7, 14, 21, 30], index=1, key="trends_window")

            if selected:
                sel_ids = players[players["name"].isin(selected)]["player_id"].tolist()
                cutoff  = wellness["date"].max() - pd.Timedelta(days=lookback)

                trend_w = (
                    wellness[(wellness["player_id"].isin(sel_ids)) & (wellness["date"] >= cutoff)]
                    .merge(players[["player_id","name"]], on="player_id")
                    .sort_values(["player_id","date"])
                )
                for col in ["sleep_hours","soreness","mood","stress"]:
                    trend_w[f"{col.split('_')[0]}_roll"] = trend_w.groupby("player_id")[col].transform(
                        lambda x: x.rolling(7, min_periods=2).mean()
                    )

                trend_fp = pd.DataFrame()
                if len(force_plate) > 0 and "cmj_height_cm" in force_plate.columns:
                    trend_fp = (
                        force_plate[(force_plate["player_id"].isin(sel_ids)) & (force_plate["date"] >= cutoff)]
                        .merge(players[["player_id","name"]], on="player_id")
                        .sort_values(["player_id","date"])
                    )
                    if len(trend_fp) > 0:
                        trend_fp["cmj_roll"] = trend_fp.groupby("player_id")["cmj_height_cm"].transform(
                            lambda x: x.rolling(7, min_periods=2).mean()
                        )

                trend_gps = pd.DataFrame()
                if len(training_load) > 0 and "player_load" in training_load.columns:
                    trend_gps = (
                        training_load[(training_load["player_id"].isin(sel_ids)) & (training_load["date"] >= cutoff)]
                        .merge(players[["player_id","name"]], on="player_id")
                        .sort_values(["player_id","date"])
                    )
                    if len(trend_gps) > 0:
                        trend_gps["load_roll"] = trend_gps.groupby("player_id")["player_load"].transform(
                            lambda x: x.rolling(7, min_periods=2).mean()
                        )

                trend_acwr = pd.DataFrame()
                if len(acwr) > 0:
                    trend_acwr = (
                        acwr[(acwr["player_id"].isin(sel_ids)) & (acwr["date"] >= cutoff)]
                        .merge(players[["player_id","name"]], on="player_id")
                        .sort_values(["player_id","date"])
                    )

                COLORS = ["#2E86AB","#A23B72","#F18F01","#C73E1D","#3B1F2B","#44BBA4"]

                def dual_trace_chart(df, raw_col, roll_col, title, yrange=None, color_override=None):
                    fig = go.Figure()
                    for i, name in enumerate(selected):
                        c   = color_override or COLORS[i % len(COLORS)]
                        sub = df[df["name"] == name]
                        if len(sub) == 0:
                            continue
                        fig.add_trace(go.Scatter(x=sub["date"], y=sub[raw_col], mode="lines+markers",
                            name=name, line=dict(color=c, width=1, dash="dot"),
                            marker=dict(size=4), opacity=0.4, legendgroup=name, showlegend=False))
                        fig.add_trace(go.Scatter(x=sub["date"], y=sub[roll_col], mode="lines",
                            name=name, line=dict(color=c, width=3),
                            legendgroup=name, showlegend=True))
                    fig.update_layout(title=title, height=240, margin=dict(l=10,r=10,t=40,b=20),
                                      hovermode="x unified", yaxis=dict(range=yrange) if yrange else {},
                                      legend=dict(orientation="h", y=-0.25))
                    return fig

                st.markdown("#### 🛌 Subjective Wellness")
                st.caption("Saw et al. 2016 (56-study SR): sleep and soreness are strongest daily wellness predictors.")
                r1, r2 = st.columns(2)
                with r1:
                    st.plotly_chart(dual_trace_chart(trend_w, "sleep_hours","sleep_roll","Sleep Hours",[4,10]), width='stretch')
                with r2:
                    st.plotly_chart(dual_trace_chart(trend_w, "soreness","soreness_roll","Soreness (0–10)",[0,10]), width='stretch')
                r3, r4 = st.columns(2)
                with r3:
                    st.plotly_chart(dual_trace_chart(trend_w, "mood","mood_roll","Mood (0–10)",[0,10]), width='stretch')
                with r4:
                    st.plotly_chart(dual_trace_chart(trend_w, "stress","stress_roll","Stress (0–10)",[0,10]), width='stretch')

                st.markdown("#### 💪 Objective Load Signals")
                st.caption("Cormack 2008 + Labban 2024 SR: CMJ is the most sensitive daily neuromuscular fatigue marker. Player load provides external training context.")
                r5, r6 = st.columns(2)
                with r5:
                    if len(trend_fp) > 0:
                        st.plotly_chart(dual_trace_chart(trend_fp, "cmj_height_cm","cmj_roll","CMJ Height (cm)",[15,45]), width='stretch')
                    else:
                        st.info("No force plate data in selected window.")
                with r6:
                    if len(trend_gps) > 0:
                        st.plotly_chart(dual_trace_chart(trend_gps, "player_load","load_roll","Player Load (AU)",[0,None]), width='stretch')
                    else:
                        st.info("No GPS data in selected window.")

                st.markdown("#### ⚠️ ACWR -- Contextual Flag Only")
                st.caption("Impellizzeri et al. 2020 + 2025 meta-analysis (22 cohort studies): ACWR should be used 'with caution as a tool', not as a standalone predictor. Shown here for context only -- not used in readiness scoring.")
                if len(trend_acwr) > 0:
                    fig_acwr = go.Figure()
                    for i, name in enumerate(selected):
                        sub = trend_acwr[trend_acwr["name"] == name]
                        if len(sub) == 0:
                            continue
                        c = COLORS[i % len(COLORS)]
                        fig_acwr.add_trace(go.Scatter(x=sub["date"], y=sub["acwr"],
                            mode="lines+markers", name=name,
                            line=dict(color=c, width=2), marker=dict(size=5)))
                    fig_acwr.add_hrect(y0=0.8, y1=1.3, fillcolor="#dcfce7", opacity=0.3,
                        line_width=0, annotation_text="Safe zone (0.8–1.3)", annotation_position="top left")
                    fig_acwr.add_hline(y=1.5, line_dash="dash", line_color="#ef4444",
                        annotation_text="Spike threshold (1.5)", annotation_position="right")
                    fig_acwr.update_layout(title="ACWR (context only)", height=220,
                        margin=dict(l=10,r=10,t=40,b=20), hovermode="x unified",
                        yaxis=dict(range=[0, 2.5]),
                        legend=dict(orientation="h", y=-0.3))
                    st.plotly_chart(fig_acwr, width='stretch')
                else:
                    st.info("No ACWR data available.")
            else:
                st.info("Select at least one athlete above.")
        else:
            st.info("No wellness data available.")

        st.markdown("---")
        gps_load_tab(training_load, players, end_date)

# ==============================================================================
# TAB 4: JUMP TESTING
# ==============================================================================

if "jt" in tab_map:
    with tab_map["jt"]:
        st.header("Jump Testing & Neuromuscular Readiness")
        st.caption("Flags based on deviation from each athlete's personal baseline, not population targets.")

        if len(force_plate) > 0:
            latest_date = force_plate["date"].max()
            today_fp    = force_plate[force_plate["date"] == latest_date].merge(
                players[["player_id", "name", "position"]], on="player_id", how="left"
            )

            def jump_zscore_status(player_id, today_cmj, today_rsi):
                history = force_plate[(force_plate["player_id"] == player_id) & (force_plate["date"] < latest_date)].tail(30)
                flags   = []
                if len(history) < 5:
                    cmj_status = "🔴" if today_cmj < 25 else ("🟡" if today_cmj < 30 else "🟢")
                    rsi_status = "🔴" if today_rsi < 0.25 else ("🟡" if today_rsi < 0.35 else "🟢")
                    return cmj_status, rsi_status, ["Insufficient history -- absolute thresholds used"]

                cmj_mean = history["cmj_height_cm"].mean()
                cmj_std  = max(history["cmj_height_cm"].std(), 0.5)
                cmj_z    = (today_cmj - cmj_mean) / cmj_std
                if cmj_z <= -2.0:
                    cmj_status = "🔴"; flags.append(f"CMJ {today_cmj:.1f} cm -- {abs(cmj_z):.1f}σ below her norm ({cmj_mean:.1f} cm avg)")
                elif cmj_z <= -1.0:
                    cmj_status = "🟡"; flags.append(f"CMJ {today_cmj:.1f} cm -- {abs(cmj_z):.1f}σ below her norm ({cmj_mean:.1f} cm avg)")
                else:
                    cmj_status = "🟢"

                rsi_mean = history["rsi_modified"].mean()
                rsi_std  = max(history["rsi_modified"].std(), 0.01)
                rsi_z    = (today_rsi - rsi_mean) / rsi_std
                if rsi_z <= -2.0:
                    rsi_status = "🔴"; flags.append(f"RSI {today_rsi:.2f} -- {abs(rsi_z):.1f}σ below her norm ({rsi_mean:.2f} avg)")
                elif rsi_z <= -1.0:
                    rsi_status = "🟡"; flags.append(f"RSI {today_rsi:.2f} -- {abs(rsi_z):.1f}σ below her norm ({rsi_mean:.2f} avg)")
                else:
                    rsi_status = "🟢"

                return cmj_status, rsi_status, flags if flags else ["Within normal range for this athlete"]

            today_fp[["cmj_status", "rsi_status", "jump_flags"]] = today_fp.apply(
                lambda r: pd.Series(jump_zscore_status(r["player_id"], r["cmj_height_cm"], r["rsi_modified"])), axis=1
            )
            today_fp["flag_count"] = today_fp.apply(lambda r: (r["cmj_status"] != "🟢") + (r["rsi_status"] != "🟢"), axis=1)
            today_fp = today_fp.sort_values("flag_count", ascending=False)

            c1, c2, c3 = st.columns(3)
            c1.metric("Athletes Tested", len(today_fp))
            c2.metric("CMJ Flags", (today_fp["cmj_status"] != "🟢").sum())
            c3.metric("RSI Flags", (today_fp["rsi_status"] != "🟢").sum())
            st.markdown("---")

            for _, row in today_fp.iterrows():
                with st.expander(f"{row['cmj_status']} {row['rsi_status']}  **{row['name']}**  -- CMJ {row['cmj_height_cm']:.1f} cm  ·  RSI {row['rsi_modified']:.2f}"):
                    ca, cb = st.columns(2)
                    ca.metric("CMJ Height",   f"{row['cmj_height_cm']:.1f} cm")
                    cb.metric("RSI-Modified", f"{row['rsi_modified']:.2f}")
                    if "asymmetry_index" in row:
                        st.caption(f"Asymmetry index: {row['asymmetry_index']:.1f}%")
                    st.markdown("**Assessment:**")
                    for note in row["jump_flags"]:
                        st.write(f"• {note}")

            st.markdown("---")
            st.subheader("Team CMJ -- 7-Day Trend")
            athlete_list = sorted(players["name"].tolist())
            sel_jump = st.multiselect("Select athletes", athlete_list, default=athlete_list[:3], key="jump_trend_select")
            if sel_jump:
                sel_ids  = players[players["name"].isin(sel_jump)]["player_id"].tolist()
                week_ago = latest_date - pd.Timedelta(days=7)
                trend_df = force_plate[
                    (force_plate["player_id"].isin(sel_ids)) & (force_plate["date"] >= week_ago)
                ].merge(players[["player_id", "name"]], on="player_id")
                if len(trend_df) > 0:
                    fig = px.line(trend_df, x="date", y="cmj_height_cm", color="name", markers=True,
                                  title="CMJ Height (cm) -- Personal Trend",
                                  labels={"cmj_height_cm": "CMJ (cm)", "name": "Athlete"})
                    st.plotly_chart(fig, width='stretch')
        else:
            st.info("No force plate data available.")

# ==============================================================================
# TAB 5: AVAILABILITY & INJURIES
# ==============================================================================

if "inj" in tab_map:
    with tab_map["inj"]:
        availability_injuries_tab(availability, injuries, players, end_date)

# ==============================================================================
# TAB 6: FORECAST
# ==============================================================================

if "fc" in tab_map:
    with tab_map["fc"]:
        st.header("Forecast & Load Projection")

        st.markdown(
            '<div style="background:#f0f9ff;border-left:4px solid #0284c7;border-radius:0 8px 8px 0;'
            'padding:12px 18px;margin-bottom:16px;">'
            '<div style="font-size:12px;color:#1e293b;line-height:1.6;">'
            '<b>Load Projection:</b> Select a player and scenario -- see projected readiness '
            'tomorrow and a specific staff recommendation. &nbsp;|&nbsp; '
            '<b>7-Day Risk:</b> ML model flags players showing injury warning patterns from the last 90 days. '
            'Not a guarantee -- a signal to act on. &nbsp;|&nbsp; '
            '<b>Risk score 90/100</b> means high-density warning cluster, same pattern seen before '
            'injuries in training data.'
            '</div></div>',
            unsafe_allow_html=True,
        )

        st.markdown("---")
        st.markdown("### Load Projection")
        st.caption(
            "If a player takes a full game load tonight, where does her readiness land tomorrow? "
            "Adjustments based on female-specific basketball recovery evidence: "
            "Pernigoni et al. 2024 (44-study basketball SR), Goulart et al. 2022 (female SR/meta-analysis), "
            "Charest et al. 2021 (NBA B2B sleep/travel), Walsh 2021 BJSM (sleep consensus). "
            "Note: female players show substantially faster CMJ/neuromuscular recovery than male literature."
        )

        proj_player = st.selectbox("Select player to project", players["name"].tolist(), key="forecast_proj_player")
        load_scenario = st.radio("Tonight's scenario",
                                  ["Rest / Practice only", "Typical game load (~28 min)",
                                   "Heavy game load (~36 min)", "Back-to-back game"],
                                  horizontal=True, key="forecast_scenario")

        proj_pid = players[players["name"] == proj_player].iloc[0]["player_id"]
        proj_pos = players[players["name"] == proj_player].iloc[0]["position"]

        w_proj = wellness[(wellness["player_id"] == proj_pid) &
                           (pd.to_datetime(wellness["date"]) == pd.to_datetime(wellness["date"]).max())]
        if len(w_proj) > 0:
            wp = w_proj.iloc[0]

            load_effects = {
                "Rest / Practice only":        {"sleep_adj": +0.1, "sore_adj": -0.3, "stress_adj": -0.5, "b2b": 0},
                "Typical game load (~28 min)": {"sleep_adj": -0.2, "sore_adj": +0.8, "stress_adj": +0.3, "b2b": 0},
                "Heavy game load (~36 min)":   {"sleep_adj": -0.4, "sore_adj": +1.5, "stress_adj": +0.5, "b2b": 0},
                "Back-to-back game":           {"sleep_adj": -0.7, "sore_adj": +2.5, "stress_adj": +1.5, "b2b": 1},
            }
            fx = load_effects[load_scenario]

            proj_sleep    = max(4.5, min(9.5, float(wp["sleep_hours"]) + fx["sleep_adj"]))
            proj_soreness = max(0,   min(10,  float(wp["soreness"])    + fx["sore_adj"]))
            proj_stress   = max(1,   min(10,  float(wp["stress"])      + fx["stress_adj"]))
            proj_mood     = max(1,   min(10,  float(wp["mood"])        - fx["stress_adj"] * 0.3))

            fp_proj  = force_plate[(force_plate["player_id"] == proj_pid)].sort_values("date").tail(1)
            cmj_proj = float(fp_proj.iloc[0]["cmj_height_cm"]) if len(fp_proj) > 0 else None
            rsi_proj = float(fp_proj.iloc[0]["rsi_modified"])  if len(fp_proj) > 0 else None

            cmj_degradation = {"Rest / Practice only": 0, "Typical game load (~28 min)": -0.5,
                               "Heavy game load (~36 min)": -1.5, "Back-to-back game": -2.5}
            if cmj_proj:
                cmj_proj = max(18, cmj_proj + cmj_degradation[load_scenario])

            proj_row = {
                "sleep_hours": proj_sleep, "sleep_quality": wp.get("sleep_quality", 7),
                "soreness": proj_soreness, "stress": proj_stress, "mood": proj_mood,
                "cmj_height_cm": cmj_proj, "rsi_modified": rsi_proj,
                "position": proj_pos,
                "is_back_to_back": fx["b2b"], "days_rest": 0 if fx["b2b"] else 1,
            }
            tomorrow_score = calculate_readiness_score(proj_row)
            today_score    = calculate_readiness_score(dict(wp) | {"position": proj_pos,
                                                                     "cmj_height_cm": cmj_proj,
                                                                     "rsi_modified": rsi_proj})

            delta     = tomorrow_score - today_score
            delta_str = f"+{delta:.0f}" if delta > 0 else f"{delta:.0f}"
            tmr_status = "READY" if tomorrow_score >= 80 else ("MONITOR" if tomorrow_score >= 60 else "PROTECT")
            tmr_color  = "#16a34a" if tomorrow_score >= 80 else ("#d97706" if tomorrow_score >= 60 else "#dc2626")

            p1, p2, p3 = st.columns(3)
            p1.metric("Today's Readiness",  f"{today_score:.0f}%")
            p2.metric("Projected Tomorrow", f"{tomorrow_score:.0f}%", delta=delta_str)
            p3.metric("Tomorrow Status",    tmr_status)

            mins_4d_proj = None
            if "practice_minutes" in training_load.columns:
                tl_4d = training_load[
                    (training_load["player_id"] == proj_pid) &
                    (pd.to_datetime(training_load["date"]) > pd.Timestamp(end_date) - pd.Timedelta(days=4))
                ]
                if len(tl_4d) > 0:
                    mins_4d_proj = round(
                        tl_4d.get("game_minutes", pd.Series([0]*len(tl_4d))).fillna(0).sum() +
                        tl_4d.get("practice_minutes", pd.Series([0]*len(tl_4d))).fillna(0).sum(), 0
                    )

            if tmr_status == "PROTECT":
                if mins_4d_proj and mins_4d_proj > 90:
                    min_cap = "20–24 minutes maximum"
                    drill_note = "Remove from full-court sprints and late-game crunch situations"
                else:
                    min_cap = "22–26 minutes"
                    drill_note = "Limit explosive acceleration drills in warmup"
                rec_color = "#dc2626"; rec_bg = "#fef2f2"; rec_icon = "⚠"; rec_head = "Restrict Tonight"
                rec_body  = (f"Cap {proj_player} at {min_cap} tonight. {drill_note}. "
                            f"Check in individually before practice -- ask about sleep and leg fatigue. "
                            f"Projected readiness tomorrow: {tomorrow_score:.0f}% (PROTECT).")
            elif tmr_status == "MONITOR":
                if mins_4d_proj and mins_4d_proj > 100:
                    min_cap = "26–30 minutes"
                    drill_note = "Reduce high-intensity interval reps in practice; prioritise skill work"
                else:
                    min_cap = "standard minutes with close monitoring"
                    drill_note = "Watch warmup quality -- if movement looks laboured, reduce early"
                rec_color = "#d97706"; rec_bg = "#fffbeb"; rec_icon = "◑"; rec_head = "Monitor Closely"
                rec_body  = (f"{proj_player}: {drill_note}. Target {min_cap} tonight. "
                            f"Re-check soreness in warmup -- if ≥7/10, pull back further. "
                            f"Projected readiness tomorrow: {tomorrow_score:.0f}% (MONITOR).")
            else:
                rec_color = "#16a34a"; rec_bg = "#f0fdf4"; rec_icon = "✓"; rec_head = "Clear for Full Load"
                rec_body  = (f"{proj_player} is projected to recover well. "
                            f"No restrictions needed tonight -- full minutes available. "
                            f"Projected readiness tomorrow: {tomorrow_score:.0f}% ({tmr_status}).")

            st.markdown(
                f'<div style="background:{rec_bg};border-left:4px solid {rec_color};'
                f'border-radius:0 8px 8px 0;padding:14px 18px;margin-top:8px;">'
                f'<div style="font-size:11px;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:{rec_color};margin-bottom:6px;">{rec_icon} Staff Recommendation</div>'
                f'<div style="font-size:13px;font-weight:700;color:#0f172a;margin-bottom:4px;">{rec_head}</div>'
                f'<div style="font-size:12px;color:#1e293b;line-height:1.6;">{rec_body}</div>'
                + (f'<div style="font-size:11px;color:#94a3b8;margin-top:6px;">Load context: {mins_4d_proj:.0f} min in last 4 days</div>' if mins_4d_proj is not None else "")
                + '</div>',
                unsafe_allow_html=True
            )
        else:
            st.info("No current wellness data for projection.")

        st.markdown("---")
        st.markdown("### 7-Day Injury Risk (ML Model)")
        st.caption(
            "Random Forest model trained on 90-day monitoring history. "
            "Flags players whose current wellness + force plate + GPS pattern matches "
            "pre-injury windows in training data. Not a guarantee -- a signal to act on."
        )
        if len(ml_predictions) > 0:
            ml_today = ml_predictions[
                pd.to_datetime(ml_predictions["date"]) == pd.Timestamp(end_date)
            ].merge(players[["player_id","name","position"]], on="player_id", how="left"
            ).sort_values("injury_risk_score", ascending=False)

            if len(ml_today) > 0:
                ml_cols = st.columns(4)
                for i, (_, row) in enumerate(ml_today.iterrows()):
                    risk_pct = row["injury_risk_score"] * 100
                    ready    = row["readiness_score"] * 100 if row["readiness_score"] <= 1 else row["readiness_score"]
                    if risk_pct >= 60:
                        risk_label, risk_color, risk_bg = "INJURY WATCH", "#dc2626", "#fee2e2"
                    elif risk_pct >= 30:
                        risk_label, risk_color, risk_bg = "WATCH CLOSELY", "#d97706", "#fef3c7"
                    else:
                        risk_label, risk_color, risk_bg = "LOW RISK", "#16a34a", "#dcfce7"
                    with ml_cols[i % 4]:
                        st.markdown(
                            f'<div style="background:{risk_bg};border-left:4px solid {risk_color};'
                            f'border-radius:0 8px 8px 0;padding:10px 14px;margin-bottom:8px;">'
                            f'<div style="font-weight:800;font-size:13px;color:#0f172a;">{row["name"]}</div>'
                            f'<div style="font-size:10px;font-weight:700;color:{risk_color};letter-spacing:0.06em;margin:2px 0;">{risk_label}</div>'
                            f'<div style="font-size:11px;color:#475569;">Today: {ready:.0f}% · Risk: {risk_pct:.0f}/100</div>'
                            f'</div>',
                            unsafe_allow_html=True
                        )
            else:
                st.info("No ML predictions found for today. Run `python train_models.py` to generate.")
        else:
            st.info("ML model not yet trained. Run `python train_models.py` then restart.")

        st.markdown("---")
        if len(wellness) > 0:
            latest_date = wellness["date"].max()
            ref_date    = pd.to_datetime(latest_date)
            latest_fp   = force_plate[force_plate["date"] == latest_date]
            has_gps_fc  = "player_load" in training_load.columns

            def get_fp_row_fc(pid):
                row = latest_fp[latest_fp["player_id"] == pid]
                return row.iloc[0].to_dict() if len(row) > 0 else None

            recent_data = (
                wellness[wellness["date"] == latest_date]
                .copy()
                .merge(players[["player_id", "name", "position", "age", "injury_history_count"]], on="player_id", how="left")
            )

            if len(recent_data) > 0:
                def full_risk(row):
                    status, flags, notes = classify_player_full(
                        row["player_id"], row, get_fp_row_fc(row["player_id"]),
                        wellness, force_plate, ref_date,
                    )
                    if has_gps_fc:
                        gps_row = get_gps_row(row["player_id"], training_load, ref_date)
                        gps_notes = build_gps_flag_notes(row["player_id"], gps_row, training_load, ref_date)
                        flags += len(gps_notes)
                        notes.extend([f"📡 {n}" for n in gps_notes])
                    risk_score = min(100, flags * 15)
                    risk_level = "High" if risk_score >= 60 else ("Moderate" if risk_score >= 20 else "Low")
                    risk_emoji = "🔴" if risk_score >= 60 else ("🟡" if risk_score >= 20 else "🟢")
                    return pd.Series({"risk_score": risk_score, "flag_notes": notes,
                                       "risk_emoji": risk_emoji, "risk_level": risk_level})

                recent_data[["risk_score", "flag_notes", "risk_emoji", "risk_level"]] = recent_data.apply(full_risk, axis=1)
                recent_data = recent_data.sort_values("risk_score", ascending=False)

                fp_coverage = len(latest_fp["player_id"].unique())
                gps_cov_str = ""
                if has_gps_fc:
                    today_gps_fc = training_load[training_load["date"] == ref_date]
                    gps_cov      = len(today_gps_fc["player_id"].unique())
                    gps_cov_str  = f" · GPS/Kinexon: {gps_cov}/{len(recent_data)} athletes"

                st.caption(
                    f"Force plate: {fp_coverage}/{len(recent_data)} athletes{gps_cov_str}. "
                    "CMJ/RSI deviations weighted 1.5× vs subjective metrics. "
                    "Risk score: each warning flag = 15 pts. Gathercole 2015 · Walsh 2021 · Gabbett 2016."
                )

                high_risk = recent_data[recent_data["risk_score"] >= 60]
                if len(high_risk) > 0:
                    st.markdown(
                        '<div style="background:#fef2f2;border:1px solid #fca5a5;border-radius:8px;'
                        'padding:12px 16px;margin-bottom:12px;">'
                        '<div style="font-size:11px;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:#991b1b;margin-bottom:8px;">Action Required This Week</div>'
                        + "".join(
                            f'<div style="font-size:13px;color:#1e293b;margin-bottom:4px;">'
                            f'<b>{row["name"]}</b> -- Risk {row["risk_score"]:.0f}/100 · '
                            f'{", ".join(str(n) for n in row["flag_notes"][:2])}</div>'
                            for _, row in high_risk.iterrows()
                        )
                        + '</div>',
                        unsafe_allow_html=True
                    )

                st.markdown("**Full watchlist -- expand each player for details:**")

                for _, player in recent_data.head(6).iterrows():
                    fp_row  = get_fp_row_fc(player["player_id"])
                    gps_row = get_gps_row(player["player_id"], training_load, ref_date) if has_gps_fc else None
                    top_flag = str(player["flag_notes"][0]) if len(player["flag_notes"]) > 0 else "multiple signals"
                    expander_title = (
                        f"{player['risk_emoji']} **{player['name']}** ({player.get('position','')})  --  "
                        f"{player['risk_level']} risk ({player['risk_score']:.0f}/100)  ·  {top_flag}"
                    )
                    with st.expander(expander_title):
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Sleep",    f"{player['sleep_hours']:.1f} hrs")
                        c2.metric("Soreness", f"{player['soreness']:.0f}/10")
                        c3.metric("Stress",   f"{player['stress']:.0f}/10")
                        if fp_row:
                            c4.metric("CMJ", f"{fp_row['cmj_height_cm']:.1f} cm")
                            ca, cb = st.columns(2)
                            ca.metric("RSI-Modified", f"{fp_row['rsi_modified']:.2f}")
                            cb.metric("Force Plate",  "Available")
                        else:
                            c4.metric("CMJ", "No data")

                        if gps_row and has_gps_fc:
                            st.markdown("**GPS / Kinexon**")
                            g1, g2, g3 = st.columns(3)
                            pl_val = gps_row.get("player_load", 0)
                            ac_val = gps_row.get("accel_count", 0)
                            dc_val = gps_row.get("decel_count", 0)
                            pl_emoji, pl_z = _gps_zscore_flag(player["player_id"], "player_load", pl_val, training_load, ref_date)
                            ac_emoji, ac_z = _gps_zscore_flag(player["player_id"], "accel_count", ac_val, training_load, ref_date)
                            dc_emoji, dc_z = _gps_zscore_flag(player["player_id"], "decel_count", dc_val, training_load, ref_date)
                            g1.metric("Player Load", f"{pl_emoji} {pl_val:.0f}", delta=f"{pl_z:+.1f}σ" if pl_z else "--", delta_color="off")
                            g2.metric("Accel Count", f"{ac_emoji} {ac_val:.0f}", delta=f"{ac_z:+.1f}σ" if ac_z else "--", delta_color="off")
                            g3.metric("Decel Count", f"{dc_emoji} {dc_val:.0f}", delta=f"{dc_z:+.1f}σ" if dc_z else "--", delta_color="off")

                        st.markdown("**Why she's here:**")
                        for note in player["flag_notes"]:
                            st.write(f"• {note}")
            else:
                st.info("No data available for the most recent day.")
        else:
            st.info("Add wellness + training load data to show forecast watchouts.")

        if "practice_minutes" in training_load.columns:
            st.markdown("---")
            st.markdown("### Minutes Load -- Last 8 Days")
            st.caption("Practice + game minutes combined. Coaches use 4-day and 8-day windows "
                       "to gauge cumulative load. High values (>120 min/4d or >220 min/8d) "
                       "warrant minutes restrictions regardless of wellness scores.")

            mins_rows = []
            for _, p in players.iterrows():
                pid_m = p["player_id"]
                tl_8  = training_load[
                    (training_load["player_id"] == pid_m) &
                    (pd.to_datetime(training_load["date"]) > pd.Timestamp(end_date) - pd.Timedelta(days=8)) &
                    (pd.to_datetime(training_load["date"]) <= pd.Timestamp(end_date))
                ].copy()
                tl_4  = tl_8[pd.to_datetime(tl_8["date"]) > pd.Timestamp(end_date) - pd.Timedelta(days=4)]

                if len(tl_8) > 0:
                    total_8 = (tl_8.get("game_minutes", pd.Series([0]*len(tl_8))).fillna(0).sum() +
                               tl_8.get("practice_minutes", pd.Series([0]*len(tl_8))).fillna(0).sum())
                    total_4 = (tl_4.get("game_minutes", pd.Series([0]*len(tl_4))).fillna(0).sum() +
                               tl_4.get("practice_minutes", pd.Series([0]*len(tl_4))).fillna(0).sum()) if len(tl_4) > 0 else 0
                    games_8 = int((tl_8.get("game_minutes", pd.Series([0]*len(tl_8))).fillna(0) > 5).sum())
                    load_4_flag = "🔴 High" if total_4 > 120 else ("🟡 Mod" if total_4 > 80 else "🟢 OK")
                    load_8_flag = "🔴 High" if total_8 > 220 else ("🟡 Mod" if total_8 > 160 else "🟢 OK")
                    mins_rows.append({
                        "Player":     p["name"],
                        "Pos":        p.get("position", ""),
                        "Min (4d)":   f"{total_4:.0f}",
                        "4d Load":    load_4_flag,
                        "Min (8d)":   f"{total_8:.0f}",
                        "8d Load":    load_8_flag,
                        "Games (8d)": games_8,
                    })

            if mins_rows:
                mins_df = pd.DataFrame(mins_rows).sort_values("Min (8d)", ascending=False)
                st.dataframe(mins_df, width='stretch', hide_index=True)
                st.caption("Thresholds: 4d >120 min = high; 8d >220 min = high. "
                           "Clinical estimates -- no published WNBA-specific cumulative load thresholds.")

        st.markdown("---")
        st.caption(
            "Risk scoring: hard safety floors (sleep <7 hrs, soreness/stress >7) always flag. "
            "Personal deviations >1.5σ from 30-day baseline add flags. "
            "CMJ/RSI drops weighted ×1.5 vs subjective metrics. "
            "GPS load/accel/decel drops >1σ below personal baseline add flags. "
            "Gathercole et al. (2015) · Walsh et al. 2021 (BJSM sleep consensus) · Gabbett (2016)"
        )

        with st.expander("Model details (staff)"):
            model_path = "models/injury_risk_model.pkl"
            if os.path.exists(model_path):
                st.success("Forecast model available")
                try:
                    with open(model_path, "rb") as f:
                        pickle.load(f)
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Algorithm", "RandomForest")
                    c2.metric("Status",    "Ready")
                    c3.metric("Model file","injury_risk_model.pkl")
                    st.info("Features: sleep, soreness, stress, training load, ACWR, CMJ, RSI, player load, accel/decel + z-score deviations from personal baseline.")
                except Exception as e:
                    st.error(f"Error loading model: {e}")
            else:
                st.warning("Forecast model not yet trained")
                st.code("python train_models.py", language="bash")

# ==============================================================================
# TAB 7: INSIGHTS
# ==============================================================================

if "ins" in tab_map:
    with tab_map["ins"]:

            # ── SECTION A: ASK ────────────────────────────────────────────────────────
        st.markdown(
            """
            <div style="margin-bottom:6px;">
                <div style="font-family:Georgia,serif; font-size:20px; font-weight:700;
                    color:#0f172a; letter-spacing:-0.01em;">Ask a Question</div>
                <div style="font-size:13px; color:#64748b; margin-top:2px;">
                    Natural-language queries about your roster -- type or use your voice
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if "query_to_run" not in st.session_state:
            st.session_state.query_to_run = ""

        # ── VOICE INPUT (Web Speech API) ──────────────────────────────────────
        # Browser-native — no extra packages. Works in Chrome/Edge.
        # Captures speech, converts to text, writes to a hidden Streamlit
        # text element. Coach clicks mic, speaks, result auto-fills the query.
        import streamlit.components.v1 as _components
        _components.html("""
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
          <button id="micBtn" onclick="toggleVoice()" style="
            background:#1e3a5f;color:white;border:none;border-radius:8px;
            padding:8px 16px;font-size:13px;font-weight:700;cursor:pointer;
            display:flex;align-items:center;gap:8px;transition:background 0.2s;">
            🎙 Speak Your Question
          </button>
          <span id="micStatus" style="font-size:12px;color:#64748b;"></span>
          <span style="font-size:11px;color:#94a3b8;font-style:italic;">
            Voice Preview · Chrome only · Try: "who didn't sleep well" or "who should I protect today"
          </span>
        </div>
        <div id="voiceResult" style="display:none;background:#f0f9ff;border-left:4px solid #0284c7;
             border-radius:0 8px 8px 0;padding:8px 14px;font-size:13px;color:#0f172a;
             margin-bottom:8px;"></div>

        <script>
        let recognizing = false;
        let recognition;

        function toggleVoice() {
          if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            document.getElementById('micStatus').textContent =
              'Voice questions work in Chrome or Edge — open this page there to use the mic.';
            document.getElementById('micStatus').style.color = '#d97706';
            return;
          }

          if (recognizing) {
            recognition.stop();
            return;
          }

          const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
          recognition = new SpeechRecognition();
          recognition.lang = 'en-US';
          recognition.interimResults = false;
          recognition.maxAlternatives = 1;

          recognition.onstart = function() {
            recognizing = true;
            document.getElementById('micBtn').style.background = '#dc2626';
            document.getElementById('micBtn').innerHTML = '🔴 Listening... (click to stop)';
            document.getElementById('micStatus').textContent = '';
          };

          recognition.onresult = function(event) {
            const transcript = event.results[0][0].transcript;
            const confidence = Math.round(event.results[0][0].confidence * 100);

            // Show result
            const resultDiv = document.getElementById('voiceResult');
            resultDiv.style.display = 'block';
            resultDiv.innerHTML = '<b>Heard:</b> "' + transcript + '"'
              + ' <span style="color:#64748b;font-size:11px;">(' + confidence + '% confidence)</span>'
              + '<br><span style="font-size:11px;color:#0369a1;">Copy this into the search box below ↓</span>';

            // Try to populate the Streamlit text input
            // Streamlit text inputs are standard HTML inputs — find by placeholder
            const inputs = parent.document.querySelectorAll('input[type="text"]');
            for (let inp of inputs) {
              if (inp.placeholder && inp.placeholder.includes('poor sleep')) {
                inp.value = transcript;
                inp.dispatchEvent(new Event('input', { bubbles: true }));
                inp.dispatchEvent(new Event('change', { bubbles: true }));
                break;
              }
            }
          };

          recognition.onerror = function(event) {
            document.getElementById('micStatus').textContent = '⚠ ' + event.error;
            document.getElementById('micStatus').style.color = '#dc2626';
          };

          recognition.onend = function() {
            recognizing = false;
            document.getElementById('micBtn').style.background = '#1e3a5f';
            document.getElementById('micBtn').innerHTML = '🎙 Speak Your Question';
          };

          recognition.start();
        }
        </script>
        """, height=100)

        ask_col, btn_col = st.columns([3, 1])

        with ask_col:
            user_query = st.text_input(
                "Ask a question",
                placeholder="e.g., 'who had poor sleep?' · 'high risk players' · 'readiness'",
                key="smart_query_input",
                label_visibility="collapsed",
            )
            if st.session_state.query_to_run:
                user_query = st.session_state.query_to_run
                st.session_state.query_to_run = ""
            if user_query:
                query_type = parse_query(user_query)
                st.info(f"Understood as: {query_type.replace('_', ' ').title()}")
                response, data = generate_smart_response(query_type)
                st.markdown(response)
                if data is not None and len(data) > 0:
                    st.download_button(
                        "Download Results",
                        data=data.to_csv(index=False),
                        file_name=f"query_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                    )

        with btn_col:
            st.markdown(
                '<div style="font-size:12px; font-weight:600; color:#64748b; '
                'letter-spacing:0.08em; text-transform:uppercase; margin-bottom:6px;">Quick queries</div>',
                unsafe_allow_html=True,
            )
            if st.button("Poor Sleep",    width='stretch', key="qs_sleep"):
                st.session_state.query_to_run = "poor sleep";   st.rerun()
            if st.button("High Risk",     width='stretch', key="qs_risk"):
                st.session_state.query_to_run = "high risk";    st.rerun()
            if st.button("Readiness",     width='stretch', key="qs_ready"):
                st.session_state.query_to_run = "readiness";    st.rerun()
            if st.button("Back-to-Backs", width='stretch', key="qs_b2b"):
                st.session_state.query_to_run = "back to back"; st.rerun()

        st.markdown(
            '<hr style="border:none; border-top:1px solid #e2e8f0; margin:28px 0 20px;">',
            unsafe_allow_html=True,
        )

        # ── DATA QUALITY AUDIT ───────────────────────────────────────────────────
        st.markdown("---")
        if HAVE_DATA_QUALITY:
            dqp = DataQualityProcessor()
            try:
                dqp.process_wellness(wellness)
                dqp.process_force_plate(force_plate)
                dqp.process_gps(training_load)
            except Exception as _dq_err:
                pass
            show_data_quality_report(dqp)
            st.caption(
                "In production with real athlete data this log would show every imputation "
                "decision the system made. Zero actions here confirms the synthetic demo "
                "database has no quality issues — which is expected."
            )
        else:
            with st.expander("🔍 Data Quality Audit Log", expanded=False):
                st.info("data_quality.py not found — add it to your repo directory.")

        # ── VALIDATION PHILOSOPHY ────────────────────────────────────────────────
        st.markdown("---")
        # ── MODEL VALIDATION ─────────────────────────────────────────────────────
        if HAVE_MODEL_VALIDATION:
            show_validation_framework_streamlit()
        else:
            with st.expander("📐 Model Validation Framework", expanded=False):
                st.markdown("""
    **V1 (Current): Does the readiness score match coach intuition?**

    WAIMS does not currently operate as a trained injury classifier. The Forecast tab
    produces a heuristic risk score — not a validated predictive model. This is intentional.
    Without a full season of real-team injury events, formal classification validation
    would overstate confidence.

    The meaningful V1 question: *does the readiness ranking surface the athletes the coach
    was already watching?* V1 method: Spearman rank correlation vs coach assessment.
    Target: top/bottom 3 agreement on ≥70% of days.

    **Scope:** Non-contact soft tissue injuries primary target. Contact injuries explicitly
    excluded — no monitoring system is expected to predict collision events.
    """)
                st.info("model_validation.py not found — add it to your repo directory.")

        # ── EVIDENCE REVIEW ─────────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("### Evidence Review")
        st.caption(
            "Formal evidence review policy: no WAIMS threshold change without a "
            "meta-analysis or systematic review. Papers flagged weekly by GitHub Actions. "
            "Decide here -- decisions saved to research_log.json."
        )

        import json as _ej
        from pathlib import Path as _ep
        _log_path = _ep(__file__).parent / "research_log.json"

        st.markdown(
            '<div style="background:#fef3c7;border-left:4px solid #d97706;'
            'border-radius:0 8px 8px 0;padding:10px 14px;margin-bottom:12px;">'
            '<b>Decision ladder:</b> Pending &rarr; Watchlist &rarr; Integrated | Rejected &nbsp;|&nbsp; '
            'CANDIDATE = meta-analysis/SR eligible for threshold review &nbsp;|&nbsp; '
            'Single studies = Watchlist only'
            '</div>',
            unsafe_allow_html=True
        )

        if _log_path.exists():
            try:
                _all_papers = _ej.loads(_log_path.read_text(encoding="utf-8"))
            except Exception as _e:
                st.error(f"Could not read research_log.json: {_e}")
                _all_papers = []
        else:
            _all_papers = []
            st.info("No research_log.json yet. Run: `python research_monitor.py --days 30 --save`")

        if _all_papers:
            _n_pending    = sum(1 for p in _all_papers if p.get("decision","PENDING") == "PENDING")
            _n_candidate  = sum(1 for p in _all_papers if p.get("gate_status","") == "CANDIDATE"
                                and p.get("decision","PENDING") == "PENDING")
            _n_watchlist  = sum(1 for p in _all_papers if p.get("decision","") == "WATCHLIST")
            _n_integrated = sum(1 for p in _all_papers if p.get("decision","") == "INTEGRATED")
            _n_rejected   = sum(1 for p in _all_papers if p.get("decision","") == "REJECTED")

            _m1, _m2, _m3, _m4, _m5 = st.columns(5)
            _m1.metric("Total", len(_all_papers))
            _m2.metric("Pending", _n_pending,
                       delta=f"{_n_candidate} candidates" if _n_candidate else None,
                       delta_color="inverse")
            _m3.metric("Watchlist", _n_watchlist)
            _m4.metric("Integrated", _n_integrated)
            _m5.metric("Rejected", _n_rejected)
            st.markdown("---")

            _ev_col1, _ev_col2 = st.columns([2, 1])
            with _ev_col1:
                _filter = st.radio("Show:", ["Pending review", "Watchlist", "Integrated", "Rejected", "All"],
                                   horizontal=True, key="ev_filter")
            with _ev_col2:
                _sort = st.selectbox("Sort by:", ["Quality score", "Date found", "Gate status"], key="ev_sort")

            _filter_map = {
                "Pending review": lambda p: p.get("decision","PENDING") == "PENDING",
                "Watchlist":      lambda p: p.get("decision","") == "WATCHLIST",
                "Integrated":     lambda p: p.get("decision","") == "INTEGRATED",
                "Rejected":       lambda p: p.get("decision","") == "REJECTED",
                "All":            lambda p: True,
            }
            _shown = [p for p in _all_papers if _filter_map[_filter](p)]
            if "Quality" in _sort:
                _shown.sort(key=lambda p: p.get("quality_score",0), reverse=True)
            elif "Date" in _sort:
                _shown.sort(key=lambda p: p.get("date_found",""), reverse=True)
            else:
                _go = {"CANDIDATE":0,"REVIEW":1,"WATCHLIST":2,"BACKGROUND":3,"ASSESS":4}
                _shown.sort(key=lambda p: _go.get(p.get("gate_status",""),9))

            st.caption(f"Showing {len(_shown)} papers")

            for _idx, _p in enumerate(_shown):
                _gate  = _p.get("gate_status","?")
                _dec   = _p.get("decision","PENDING")
                _score = _p.get("quality_score",0)
                _bc = {"CANDIDATE":"#dc2626","REVIEW":"#d97706","ASSESS":"#0284c7","WATCHLIST":"#64748b"}.get(_gate,"#94a3b8")
                _dc = {"PENDING":"#64748b","WATCHLIST":"#d97706","INTEGRATED":"#16a34a","REJECTED":"#94a3b8"}.get(_dec,"#64748b")
                _lbl = " ".join(
                    f'<span style="background:#e2e8f0;color:#475569;padding:1px 5px;border-radius:3px;font-size:10px;">{l}</span>'
                    for l in _p.get("quality_labels",[])
                )
                st.markdown(
                    f'<div style="border:1px solid #e2e8f0;border-left:4px solid {_bc};'
                    f'border-radius:0 8px 8px 0;padding:12px 14px;margin-bottom:4px;background:white;">'
                    f'<div style="display:flex;justify-content:space-between;margin-bottom:5px;">'
                    f'<div><span style="font-size:11px;font-weight:700;color:{_bc};">[{_gate}]</span>'
                    f' &nbsp; {_lbl}'
                    f'<span style="font-size:10px;color:#94a3b8;margin-left:8px;">Score: {_score} | {_p.get("source","PubMed")}</span></div>'
                    f'<span style="font-size:11px;font-weight:700;color:{_dc};">{_dec}</span>'
                    f'</div>'
                    f'<div style="font-size:13px;font-weight:600;color:#0f172a;margin-bottom:3px;word-wrap:break-word;white-space:normal;">{_p.get("title","Unknown")[:200]}</div>'
                    f'<div style="font-size:11px;color:#475569;margin-bottom:4px;">{_p.get("authors","")} | <em>{_p.get("journal","")}</em> | {_p.get("pub_date","?")}</div>'
                    f'<div style="font-size:11px;background:#f0f9ff;padding:3px 8px;border-radius:3px;color:#0369a1;margin-bottom:3px;">WAIMS: {_p.get("waims_signal","?")}</div>'
                    f'<div style="font-size:11px;background:#fefce8;padding:3px 8px;border-radius:3px;color:#713f12;">{_p.get("gate_note","")[:120]}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )

                _b1, _b2, _b3, _b4, _blink = st.columns([1,1,1,1,2])
                _new_dec = _dec
                with _b1:
                    if st.button("Integrate", key=f"ev_int_{_idx}",
                                 type="primary" if _dec=="INTEGRATED" else "secondary",
                                 disabled=(_dec=="INTEGRATED")):
                        _new_dec = "INTEGRATED"
                with _b2:
                    if st.button("Watchlist", key=f"ev_wtch_{_idx}", disabled=(_dec=="WATCHLIST")):
                        _new_dec = "WATCHLIST"
                with _b3:
                    if st.button("Reject", key=f"ev_rej_{_idx}", disabled=(_dec=="REJECTED")):
                        _new_dec = "REJECTED"
                with _b4:
                    if st.button("Reset", key=f"ev_reset_{_idx}", disabled=(_dec=="PENDING")):
                        _new_dec = "PENDING"
                with _blink:
                    if _p.get("url"):
                        st.markdown(f'<a href="{_p["url"]}" target="_blank" style="font-size:12px;color:#0284c7;">View paper</a>', unsafe_allow_html=True)

                if _new_dec != _dec:
                    for _mp in _all_papers:
                        _mid = _mp.get("id") or _mp.get("pmid") or _mp.get("url","")
                        _pid = _p.get("id") or _p.get("pmid") or _p.get("url","")
                        if _mid == _pid:
                            _mp["decision"]      = _new_dec
                            _mp["decision_date"] = pd.Timestamp.now().strftime("%Y-%m-%d")
                            break
                    try:
                        _log_path.write_text(_ej.dumps(_all_papers, indent=2, ensure_ascii=False), encoding="utf-8")
                    except Exception as _se_early:
                        st.error(f"Save failed: {_se_early}")
                    st.rerun()

            _int_papers = [p for p in _all_papers if p.get("decision")=="INTEGRATED"]
            if _int_papers:
                st.markdown("---")
                with st.expander(f"Integration queue -- {len(_int_papers)} approved, awaiting code update"):
                    st.info(
                        "These papers are approved. To activate in WAIMS thresholds, "
                        "start a session with Claude and say: "
                        "'These papers are approved in my evidence log -- please integrate them into WAIMS.'"
                    )
                    for _ip in _int_papers:
                        st.markdown(
                            f"- **{_ip.get('title','?')[:80]}** "
                            f"({_ip.get('authors','').split(' et')[0]}, {_ip.get('pub_date','?')}) "
                            f"-- *{_ip.get('waims_signal','?')}*"
                        )

        # ── SECTION B: CORRELATIONS ───────────────────────────────────────────────
        st.markdown(
            """
            <div style="margin-bottom:16px;">
                <div style="font-family:Georgia,serif; font-size:20px; font-weight:700;
                    color:#0f172a; letter-spacing:-0.01em;">Signal Correlations</div>
                <div style="font-size:13px; color:#64748b; margin-top:2px;">
                    Hidden relationships across all monitoring metrics -- including ESPN game outcomes
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        correlation_explorer_tab(wellness, training_load, force_plate, acwr, injuries, players)




# ==============================================================================
# FOOTER
# ==============================================================================

st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#666;'>"
    "<p><strong>WAIMS</strong> -- Athlete Monitoring System | Python · Streamlit · SQLite</p>"
    "<p>Elite Women's Basketball demo -- 90 days · 12 players · ~10,000+ data points</p>"
    "</div>",
    unsafe_allow_html=True,
)
