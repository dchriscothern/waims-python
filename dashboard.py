"""
WAIMS Readiness Watchlist
Streamlit web application for athlete monitoring data visualization

Usage:
    streamlit run dashboard.py
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
from coach_command_center import coach_command_center
from correlation_explorer import correlation_explorer_tab

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
    initial_sidebar_state="expanded",
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
    """Emoji + percentage only — no battery bar."""
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
    score  = (row["sleep_hours"] / 8) * 30
    score += ((10 - row["soreness"]) / 10) * 25
    score += ((10 - row["stress"])   / 10) * 25
    score += (row["mood"] / 10) * 20
    return round(score, 0)


def get_status_color(score):
    if score >= 80:
        return "🟢", "green"
    elif score >= 60:
        return "🟡", "orange"
    else:
        return "🔴", "red"


# ==============================================================================
# GPS HELPER — z-score flag for a single metric
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
    """
    Returns a list of flag strings for load/accel/decel deviations.
    Uses z-scores vs personal 30-day baseline.
    """
    if gps_row is None:
        return []
    notes = []
    checks = [
        ("player_load",  "Player Load",  "low"),
        ("accel_count",  "Accel Count",  "low"),
        ("decel_count",  "Decel Count",  "low"),
    ]
    for col, label, direction in checks:
        val = gps_row.get(col)
        if val is None:
            continue
        emoji, z = _gps_zscore_flag(player_id, col, val, training_load_df, ref_date)
        if emoji == "🔴" and z is not None:
            notes.append(f"{label} {val:.0f} — {abs(z):.1f}σ below baseline (high fatigue signal)")
        elif emoji == "🟡" and z is not None:
            notes.append(f"{label} {val:.0f} — {abs(z):.1f}σ below baseline")
    return notes


# ==============================================================================
# SHARED Z-SCORE CLASSIFIER  (wellness + CMJ/RSI)
# ==============================================================================

def classify_player_full(player_id, today_wellness_row, today_fp_row, wellness_df, fp_df, ref_date):
    """
    Returns (status: 'green'|'yellow'|'red', flags: int, notes: list[str])
    Incorporates both wellness z-scores and force plate z-scores.
    CMJ/RSI flags weighted higher as objective signals.
    """
    w_history  = wellness_df[(wellness_df["player_id"] == player_id) & (wellness_df["date"] < ref_date)].tail(30)
    fp_history = fp_df[(fp_df["player_id"] == player_id) & (fp_df["date"] < ref_date)].tail(30)

    flags = 0
    notes = []

    # ── Wellness z-scores ─────────────────────────────────────────────
    if len(w_history) >= 7:
        def wz(col, val, min_std):
            m = w_history[col].mean()
            s = max(w_history[col].std(), min_std)
            return (val - m) / s

        sleep_z = wz("sleep_hours", today_wellness_row["sleep_hours"], 0.3)
        sor_z   = wz("soreness",    today_wellness_row["soreness"],    0.5)
        str_z   = wz("stress",      today_wellness_row["stress"],      0.5)
        mood_z  = wz("mood",        today_wellness_row["mood"],        0.5)

        if today_wellness_row["sleep_hours"] < 6.5:
            flags += 2
            notes.append(f"Sleep {today_wellness_row['sleep_hours']:.1f} hrs — below safety floor")
        elif sleep_z < -1.5:
            flags += 1
            notes.append(f"Sleep {today_wellness_row['sleep_hours']:.1f} hrs — {abs(sleep_z):.1f}σ below her norm")

        if today_wellness_row["soreness"] > 7:
            flags += 2
            notes.append(f"Soreness {today_wellness_row['soreness']:.0f}/10 — above safety ceiling")
        elif sor_z > 1.5:
            flags += 1
            notes.append(f"Soreness {today_wellness_row['soreness']:.0f}/10 — {sor_z:.1f}σ above her norm")

        if today_wellness_row["stress"] > 7:
            flags += 2
            notes.append(f"Stress {today_wellness_row['stress']:.0f}/10 — above safety ceiling")
        elif str_z > 1.5:
            flags += 1
            notes.append(f"Stress {today_wellness_row['stress']:.0f}/10 — {str_z:.1f}σ above her norm")

        if mood_z < -1.5:
            flags += 1
            notes.append(f"Mood {today_wellness_row['mood']:.0f}/10 — {abs(mood_z):.1f}σ below her norm")
    else:
        if today_wellness_row["sleep_hours"] < 6.5:
            flags += 2; notes.append("Sleep below safety floor (insufficient history for z-score)")
        if today_wellness_row["soreness"] > 7:
            flags += 2; notes.append("Soreness above safety ceiling (insufficient history for z-score)")

    # ── Force plate z-scores (objective — weighted higher) ────────────
    if today_fp_row is not None and len(fp_history) >= 5:
        cmj_val = today_fp_row.get("cmj_height_cm")
        rsi_val = today_fp_row.get("rsi_modified")

        if cmj_val is not None:
            cmj_mean = fp_history["cmj_height_cm"].mean()
            cmj_std  = max(fp_history["cmj_height_cm"].std(), 0.5)
            cmj_z    = (cmj_val - cmj_mean) / cmj_std
            if cmj_z <= -2.0:
                flags += 3
                notes.append(f"CMJ {cmj_val:.1f} cm — {abs(cmj_z):.1f}σ below baseline (severe neuromuscular fatigue)")
            elif cmj_z <= -1.0:
                flags += 2
                notes.append(f"CMJ {cmj_val:.1f} cm — {abs(cmj_z):.1f}σ below baseline (neuromuscular fatigue)")

        if rsi_val is not None:
            rsi_mean = fp_history["rsi_modified"].mean()
            rsi_std  = max(fp_history["rsi_modified"].std(), 0.01)
            rsi_z    = (rsi_val - rsi_mean) / rsi_std
            if rsi_z <= -2.0:
                flags += 3
                notes.append(f"RSI {rsi_val:.2f} — {abs(rsi_z):.1f}σ below baseline (reduced reactive strength)")
            elif rsi_z <= -1.0:
                flags += 2
                notes.append(f"RSI {rsi_val:.2f} — {abs(rsi_z):.1f}σ below baseline")

    if not notes:
        notes.append("No flags — within normal range across all metrics including force plate")

    status = "green" if flags == 0 else ("yellow" if flags <= 3 else "red")
    return status, flags, notes

# ==============================================================================
# TAB 1: TODAY'S READINESS
# ==============================================================================

def enhanced_todays_readiness_tab(wellness_df, players_df, fp_df, training_load_df, end_date):
    st.header("Today's Readiness Status")
    st.caption(f"📅 {end_date.strftime('%B %d, %Y')}")

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

    # GPS coverage check
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

    today_wellness["readiness_score"] = (
        (today_wellness["sleep_hours"] / 8) * 30
        + ((10 - today_wellness["soreness"]) / 10) * 25
        + ((10 - today_wellness["stress"])   / 10) * 25
        + (today_wellness["mood"] / 10) * 20
    )
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

                cmj_str   = f"{fp_row['cmj_height_cm']:.1f} cm"  if fp_row  else "—"
                rsi_str   = f"{fp_row['rsi_modified']:.2f}"       if fp_row  else "—"

                # GPS z-score flags for compact badge
                if gps_row and has_gps:
                    load_emoji, _ = _gps_zscore_flag(player["player_id"], "player_load", gps_row.get("player_load", 0), training_load_df, ref_date)
                    accel_emoji, _= _gps_zscore_flag(player["player_id"], "accel_count", gps_row.get("accel_count", 0), training_load_df, ref_date)
                    decel_emoji, _= _gps_zscore_flag(player["player_id"], "decel_count", gps_row.get("decel_count", 0), training_load_df, ref_date)
                    load_str  = f"{load_emoji} {gps_row.get('player_load', 0):.0f}"
                    accel_str = f"{accel_emoji} {gps_row.get('accel_count', 0):.0f}"
                    decel_str = f"{decel_emoji} {gps_row.get('decel_count', 0):.0f}"
                else:
                    load_str = accel_str = decel_str = "—"

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
        # ── Detailed view ────────────────────────────────────────────
        for _, player in today_wellness.iterrows():
            emoji   = "🟢" if player["readiness_score"] >= 80 else ("🟡" if player["readiness_score"] >= 60 else "🔴")
            fp_row  = get_fp_row(player["player_id"])
            gps_row = get_gps_row(player["player_id"], training_load_df, ref_date) if has_gps else None

            with st.expander(f"{emoji} **{player['name']}** ({player['position']}) — Score: {player['readiness_score']:.0f}/100"):
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

                        pl_delta = f"{pl_z:+.1f}σ" if pl_z is not None else "—"
                        ac_delta = f"{ac_z:+.1f}σ" if ac_z is not None else "—"
                        dc_delta = f"{dc_z:+.1f}σ" if dc_z is not None else "—"

                        st.metric("Player Load",  f"{pl_emoji} {pl_val:.0f}",  delta=pl_delta, delta_color="off")
                        st.metric("Accel Count",  f"{ac_emoji} {ac_val:.0f}",  delta=ac_delta, delta_color="off")
                        st.metric("Decel Count",  f"{dc_emoji} {dc_val:.0f}",  delta=dc_delta, delta_color="off")

                        # Yesterday's load session note
                        if gps_row.get("game_minutes", 0) > 0:
                            st.caption(f"Game day — {gps_row['game_minutes']:.0f} min played")
                        elif gps_row.get("practice_minutes", 0) > 0:
                            st.caption(f"Practice — {gps_row['practice_minutes']:.0f} min @ RPE {gps_row.get('practice_rpe', 0):.1f}")
                    else:
                        st.caption("No GPS data today")

                st.markdown("---")
                st.markdown("**Flags:**")
                # Wellness + force plate flags
                for note in player["flag_notes"]:
                    st.write(f"• {note}")
                # GPS flags (separate, appended)
                if gps_row and has_gps:
                    gps_notes = build_gps_flag_notes(player["player_id"], gps_row, training_load_df, ref_date)
                    for note in gps_notes:
                        st.write(f"• 📡 {note}")

    st.markdown("---")
    st.markdown("### Quick Actions")
    qa1, qa2, qa3 = st.columns(3)
    with qa1:
        if st.button("Email At-Risk Players", use_container_width=True):
            at_risk = today_wellness[today_wellness["zscore_status"] == "red"]["name"].tolist()
            st.info(f"Would email: {', '.join(at_risk)}" if at_risk else "No at-risk players today!")
    with qa2:
        csv = today_wellness[["name", "position", "readiness_score", "status", "sleep_hours", "soreness", "stress", "mood"]].to_csv(index=False)
        st.download_button("Export Today's Report (CSV)", data=csv, file_name=f"readiness_{end_date.strftime('%Y%m%d')}.csv", mime="text/csv", use_container_width=True)
    with qa3:
        if st.button("Create Training Alert", use_container_width=True):
            st.info(f"Training modifications recommended for {red_count + yellow_count} players")

# ==============================================================================
# TAB 5: AVAILABILITY & INJURIES
# ==============================================================================

def availability_injuries_tab(availability_df, injuries_df, players_df, end_date):
    st.header("Availability & Injury Tracker")
    latest_date = pd.to_datetime(end_date)

    # ── TODAY'S AVAILABILITY BOARD ────────────────────────────────────
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

    # ── SEASON AVAILABILITY % ─────────────────────────────────────────
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
            }))
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
        st.plotly_chart(fig, use_container_width=True)

    # ── INJURY LOG ────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Injury Log")

    if len(injuries_df) > 0:
        inj_display  = injuries_df.merge(players_df[["player_id", "name"]], on="player_id")
        sev_colors   = {"Mild": "#f59e0b", "Moderate": "#ef4444", "Severe": "#7c3aed"}

        for _, inj in inj_display.iterrows():
            ret = (inj["return_date"].strftime("%b %d")
                   if "return_date" in inj.index and pd.notna(inj["return_date"]) else "TBD")
            with st.expander(
                f"🚨 **{inj['name']}** — {inj['injury_type']} · "
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
                    st.plotly_chart(fig, use_container_width=True)
    else:
        st.success("No injuries recorded this season")

# ==============================================================================
# TAB 6: GPS & LOAD
# ==============================================================================

def gps_load_tab(training_load_df, players_df, end_date):
    st.header("GPS & Load Monitoring")
    st.caption("Kinexon tracking — distance, high-speed running, sprint, accel/decel, player load.")

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

    # ── TEAM SUMMARY ──────────────────────────────────────────────────
    st.subheader("Team Summary — Today")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Avg Distance",    f"{today_load['total_distance_km'].mean():.1f} km")
    c2.metric("Avg HSR",         f"{today_load['hsr_distance_m'].mean():.0f} m")
    c3.metric("Avg Sprint",      f"{today_load['sprint_distance_m'].mean():.0f} m")
    c4.metric("Avg Player Load", f"{today_load['player_load'].mean():.0f}")
    c5.metric("Avg Accels",      f"{today_load['accel_count'].mean():.0f}")
    st.markdown("---")

    # ── PLAYER GPS TABLE ──────────────────────────────────────────────
    st.subheader("Individual GPS — Today")

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
            f"{l_flag} **{row['name']}** ({row['position']})  —  "
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
                st.caption(f"Game day — {row['game_minutes']:.0f} min played")
            else:
                st.caption(f"Practice — {row['practice_minutes']:.0f} min @ RPE {row['practice_rpe']:.1f}")

    st.markdown("---")

    # ── 14-DAY GPS TRENDS ─────────────────────────────────────────────
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
            st.plotly_chart(gps_chart("total_distance_km", "Total Distance (km)", "km"), use_container_width=True)
        with t2:
            st.plotly_chart(gps_chart("hsr_distance_m", "High-Speed Running (m, >18 km/h)", "m"), use_container_width=True)

        t3, t4 = st.columns(2)
        with t3:
            st.plotly_chart(gps_chart("player_load", "Player Load", "AU"), use_container_width=True)
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
            st.plotly_chart(fig, use_container_width=True)

    # ── PLAYER LOAD ACWR ──────────────────────────────────────────────
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
        st.plotly_chart(fig, use_container_width=True)

# ==============================================================================
# SMART QUERY FUNCTIONS
# ==============================================================================

def get_latest_date():
    return wellness["date"].max()

def query_poor_sleep(threshold=6.5):
    latest_date = get_latest_date()
    df = wellness[wellness["date"] == latest_date].copy()
    df = df[df["sleep_hours"] < threshold].merge(players[["player_id", "name"]], on="player_id")
    return df[["name", "sleep_hours", "soreness", "stress"]].sort_values("sleep_hours")

def query_high_risk():
    latest_date = get_latest_date()
    df = wellness[wellness["date"] == latest_date].copy()
    df = df.merge(players[["player_id", "name", "injury_history_count"]], on="player_id")
    df["high_risk"] = (df["sleep_hours"] < 6.5) | (df["soreness"] > 7) | (df["stress"] > 7)
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
    if any(w in user_input for w in ["poor sleep", "bad sleep", "tired"]):
        return "poor_sleep"
    elif any(w in user_input for w in ["high risk", "at risk", "injury risk"]):
        return "high_risk"
    elif any(w in user_input for w in ["readiness", "ready"]):
        return "readiness"
    elif "compare position" in user_input or "position comparison" in user_input:
        return "position_comparison"
    return "unknown"

def generate_smart_response(query_type):
    if query_type == "poor_sleep":
        df = query_poor_sleep()
        if len(df) == 0:
            return "No players had poor sleep (<6.5 hrs) last night.", None
        st.subheader(f"{len(df)} Players with Poor Sleep")
        st.dataframe(df, use_container_width=True)
        response = f"**{len(df)} players** had poor sleep:\n\n" + "".join(f"- {r['name']}: {r['sleep_hours']:.1f} hrs\n" for _, r in df.iterrows())
        response += "\nResearch: Sleep <6.5 hrs increases injury risk 1.7× (Milewski 2014)"
        return response, df
    elif query_type == "high_risk":
        df = query_high_risk()
        if len(df) == 0:
            return "No players currently showing high injury risk indicators.", None
        st.subheader(f"{len(df)} Players at Elevated Risk")
        st.dataframe(df, use_container_width=True)
        response = f"**{len(df)} players** showing elevated risk:\n\n" + "".join(f"- {r['name']}: Sleep {r['sleep_hours']:.1f} hrs, Soreness {r['soreness']}/10\n" for _, r in df.iterrows())
        return response, df
    elif query_type == "readiness":
        df = query_readiness_scores()
        st.subheader("Readiness Scores")
        st.dataframe(df, use_container_width=True)
        green  = len(df[df["readiness_score"] >= 80])
        yellow = len(df[(df["readiness_score"] >= 60) & (df["readiness_score"] < 80)])
        red    = len(df[df["readiness_score"] < 60])
        return f"🟢 Ready: {green} | 🟡 Monitor: {yellow} | 🔴 At Risk: {red}", df
    elif query_type == "position_comparison":
        df = query_position_comparison()
        st.subheader("Position Comparison")
        fig = px.bar(df, x="position", y=["avg_sleep", "avg_soreness"], barmode="group", title="Metrics by Position")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df, use_container_width=True)
        return "Position comparison complete", df
    else:
        return "Try: 'poor sleep', 'high risk', 'readiness', or 'compare positions'", None

# ==============================================================================
# SIDEBAR
# ==============================================================================

if LOGO_PATH.exists():
    st.sidebar.image(str(LOGO_PATH), width=60)

st.sidebar.title("🏀 Roster & Dates")
st.sidebar.markdown("**How to use**\n1. Pick a **date range**\n2. Select **players**\n3. The Watchlist updates automatically")

if len(wellness) > 0:
    min_date   = wellness["date"].min().date()
    max_date   = wellness["date"].max().date()
    date_range = st.sidebar.date_input(
        "Date Range",
        value=(max_date - timedelta(days=7), max_date),
        min_value=min_date, max_value=max_date,
    )
    start_date, end_date = date_range if len(date_range) == 2 else (max_date, max_date)
else:
    start_date = end_date = datetime.today().date()

selected_players = st.sidebar.multiselect(
    "Select Players",
    options=players["name"].tolist(),
    default=players["name"].tolist()[:5],
)
st.sidebar.markdown("---")
st.sidebar.info("**Data Source:** SQLite Database\n**Records:** ~10,000+ data points\n**Period:** 90 days of monitoring")

if HAVE_IMPROVED_GAUGES:
    st.sidebar.markdown("---")
    if st.sidebar.button("📚 View Research Foundation", use_container_width=True):
        with st.expander("Research Foundation", expanded=True):
            show_research_foundation()

# ==============================================================================
# MAIN DASHBOARD
# ==============================================================================

st.title("🏀 WAIMS READINESS WATCHLIST")
st.markdown(f"**Date:** {end_date.strftime('%B %d, %Y')}")

tab0, tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
    "🏀 Command Center",
    "📊 Today's Readiness",
    "👤 Athlete Profiles",
    "📈 Trends",
    "💪 Jump Testing",
    "🚨 Availability & Injuries",
    "📡 GPS & Load",
    "🤖 Forecast",
    "🔍 Ask the Watchlist",
    "🔬 Correlations",
])

# ==============================================================================
# TAB 1
# ==============================================================================

with tab0:
    coach_command_center(wellness, players, force_plate, training_load, acwr, end_date)

# ==============================================================================
# TAB 1 — TODAY'S READINESS (analyst view)
# ==============================================================================

with tab1:
    # Pass training_load so the tab can render GPS metrics
    enhanced_todays_readiness_tab(wellness, players, force_plate, training_load, end_date)

# ==============================================================================
# TAB 2
# ==============================================================================

with tab2:
    athlete_profile_tab(wellness, training_load, acwr, force_plate, players, injuries)

# ==============================================================================
# TAB 3: TRENDS
# ==============================================================================

with tab3:
    st.header("Wellness Trends")
    st.caption("Raw daily values (faint) with 7-day rolling average (bold). Useful for spotting drift across the week.")

    if len(wellness) > 0:
        athlete_list = sorted(players["name"].tolist())
        col_sel, col_days = st.columns([2, 1])
        with col_sel:
            selected = st.multiselect("Select athletes", athlete_list, default=athlete_list[:4], key="trends_athlete_select")
        with col_days:
            lookback = st.selectbox("Window", [7, 14, 21, 30], index=1, key="trends_window")

        if selected:
            sel_ids  = players[players["name"].isin(selected)]["player_id"].tolist()
            cutoff   = wellness["date"].max() - pd.Timedelta(days=lookback)
            trend_df = (
                wellness[(wellness["player_id"].isin(sel_ids)) & (wellness["date"] >= cutoff)]
                .merge(players[["player_id", "name"]], on="player_id")
                .sort_values(["player_id", "date"])
            )
            for col in ["sleep_hours", "soreness", "mood", "stress"]:
                trend_df[f"{col.split('_')[0]}_roll"] = trend_df.groupby("player_id")[col].transform(
                    lambda x: x.rolling(7, min_periods=2).mean()
                )

            COLORS = ["#2E86AB", "#A23B72", "#F18F01", "#C73E1D", "#3B1F2B", "#44BBA4"]

            def dual_trace_chart(df, raw_col, roll_col, title, yrange=None):
                fig = go.Figure()
                for i, name in enumerate(selected):
                    c   = COLORS[i % len(COLORS)]
                    sub = df[df["name"] == name]
                    fig.add_trace(go.Scatter(x=sub["date"], y=sub[raw_col],  mode="lines+markers", name=name, line=dict(color=c, width=1, dash="dot"), marker=dict(size=4), opacity=0.4, legendgroup=name, showlegend=False))
                    fig.add_trace(go.Scatter(x=sub["date"], y=sub[roll_col], mode="lines",          name=name, line=dict(color=c, width=3),             legendgroup=name, showlegend=True))
                fig.update_layout(title=title, height=260, margin=dict(l=10, r=10, t=40, b=20),
                                  hovermode="x unified", yaxis=dict(range=yrange) if yrange else {},
                                  legend=dict(orientation="h", y=-0.2))
                return fig

            r1, r2 = st.columns(2)
            with r1:
                st.plotly_chart(dual_trace_chart(trend_df, "sleep_hours", "sleep_roll",    "Sleep Hours",    [4, 10]), use_container_width=True)
            with r2:
                st.plotly_chart(dual_trace_chart(trend_df, "soreness",    "soreness_roll", "Soreness (0–10)",[0, 10]), use_container_width=True)
            r3, r4 = st.columns(2)
            with r3:
                st.plotly_chart(dual_trace_chart(trend_df, "mood",   "mood_roll",   "Mood (0–10)",   [0, 10]), use_container_width=True)
            with r4:
                st.plotly_chart(dual_trace_chart(trend_df, "stress", "stress_roll", "Stress (0–10)", [0, 10]), use_container_width=True)
        else:
            st.info("Select at least one athlete above.")
    else:
        st.info("No wellness data available.")

# ==============================================================================
# TAB 4: JUMP TESTING
# ==============================================================================

with tab4:
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
                return cmj_status, rsi_status, ["Insufficient history — absolute thresholds used"]

            cmj_mean = history["cmj_height_cm"].mean()
            cmj_std  = max(history["cmj_height_cm"].std(), 0.5)
            cmj_z    = (today_cmj - cmj_mean) / cmj_std
            if cmj_z <= -2.0:
                cmj_status = "🔴"; flags.append(f"CMJ {today_cmj:.1f} cm — {abs(cmj_z):.1f}σ below her norm ({cmj_mean:.1f} cm avg)")
            elif cmj_z <= -1.0:
                cmj_status = "🟡"; flags.append(f"CMJ {today_cmj:.1f} cm — {abs(cmj_z):.1f}σ below her norm ({cmj_mean:.1f} cm avg)")
            else:
                cmj_status = "🟢"

            rsi_mean = history["rsi_modified"].mean()
            rsi_std  = max(history["rsi_modified"].std(), 0.01)
            rsi_z    = (today_rsi - rsi_mean) / rsi_std
            if rsi_z <= -2.0:
                rsi_status = "🔴"; flags.append(f"RSI {today_rsi:.2f} — {abs(rsi_z):.1f}σ below her norm ({rsi_mean:.2f} avg)")
            elif rsi_z <= -1.0:
                rsi_status = "🟡"; flags.append(f"RSI {today_rsi:.2f} — {abs(rsi_z):.1f}σ below her norm ({rsi_mean:.2f} avg)")
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
            with st.expander(f"{row['cmj_status']} {row['rsi_status']}  **{row['name']}**  — CMJ {row['cmj_height_cm']:.1f} cm  ·  RSI {row['rsi_modified']:.2f}"):
                ca, cb = st.columns(2)
                ca.metric("CMJ Height",   f"{row['cmj_height_cm']:.1f} cm")
                cb.metric("RSI-Modified", f"{row['rsi_modified']:.2f}")
                if "asymmetry_index" in row:
                    st.caption(f"Asymmetry index: {row['asymmetry_index']:.1f}%")
                st.markdown("**Assessment:**")
                for note in row["jump_flags"]:
                    st.write(f"• {note}")

        st.markdown("---")
        st.subheader("Team CMJ — 7-Day Trend")
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
                              title="CMJ Height (cm) — Personal Trend",
                              labels={"cmj_height_cm": "CMJ (cm)", "name": "Athlete"})
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No force plate data available.")

# ==============================================================================
# TAB 5: AVAILABILITY & INJURIES
# ==============================================================================

with tab5:
    availability_injuries_tab(availability, injuries, players, end_date)

# ==============================================================================
# TAB 6: GPS & LOAD
# ==============================================================================

with tab6:
    gps_load_tab(training_load, players, end_date)

# ==============================================================================
# TAB 7: FORECAST
# ==============================================================================

with tab7:
    st.header("Readiness Forecasts")
    st.caption("Flags players showing unusual deviation from their personal baseline — wellness + force plate + GPS combined.")

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
            .merge(players[["player_id", "name", "age", "injury_history_count"]], on="player_id", how="left")
        )

        if len(recent_data) > 0:
            def full_risk(row):
                status, flags, notes = classify_player_full(
                    row["player_id"], row,
                    get_fp_row_fc(row["player_id"]),
                    wellness, force_plate, ref_date,
                )

                # ── GPS flags appended to notes ───────────────────────
                if has_gps_fc:
                    gps_row = get_gps_row(row["player_id"], training_load, ref_date)
                    gps_notes = build_gps_flag_notes(row["player_id"], gps_row, training_load, ref_date)
                    # Each GPS flag adds 1 to the flag count (lower weight than CMJ)
                    flags += len(gps_notes)
                    notes.extend([f"📡 {n}" for n in gps_notes])

                risk_score = min(100, flags * 15)
                risk_emoji = "🔴 High" if risk_score >= 60 else ("🟡 Moderate" if risk_score >= 20 else "🟢 Low")
                return pd.Series({"risk_score": risk_score, "flag_notes": notes, "risk_emoji": risk_emoji})

            recent_data[["risk_score", "flag_notes", "risk_emoji"]] = recent_data.apply(full_risk, axis=1)
            recent_data = recent_data.sort_values("risk_score", ascending=False)

            fp_coverage  = len(latest_fp["player_id"].unique())
            gps_cov_str  = ""
            if has_gps_fc:
                today_gps_fc = training_load[training_load["date"] == ref_date]
                gps_cov      = len(today_gps_fc["player_id"].unique())
                gps_cov_str  = f" · GPS/Kinexon: {gps_cov}/{len(recent_data)} athletes"

            st.caption(
                f"Force plate: {fp_coverage}/{len(recent_data)} athletes{gps_cov_str}. "
                "CMJ/RSI deviations weighted higher; GPS load/accel/decel deviations also flagged."
            )
            st.markdown("**Athletes to check in with:**")

            for _, player in recent_data.head(6).iterrows():
                fp_row  = get_fp_row_fc(player["player_id"])
                gps_row = get_gps_row(player["player_id"], training_load, ref_date) if has_gps_fc else None

                with st.expander(f"{player['risk_emoji']}  **{player['name']}**  — Risk Score: {player['risk_score']:.0f}/100"):

                    # Row 1: wellness + force plate
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

                    # Row 2: GPS metrics
                    if gps_row and has_gps_fc:
                        st.markdown("**GPS / Kinexon**")
                        g1, g2, g3 = st.columns(3)
                        pl_val = gps_row.get("player_load", 0)
                        ac_val = gps_row.get("accel_count", 0)
                        dc_val = gps_row.get("decel_count", 0)

                        pl_emoji, pl_z = _gps_zscore_flag(player["player_id"], "player_load", pl_val, training_load, ref_date)
                        ac_emoji, ac_z = _gps_zscore_flag(player["player_id"], "accel_count", ac_val, training_load, ref_date)
                        dc_emoji, dc_z = _gps_zscore_flag(player["player_id"], "decel_count", dc_val, training_load, ref_date)

                        g1.metric("Player Load", f"{pl_emoji} {pl_val:.0f}", delta=f"{pl_z:+.1f}σ" if pl_z else "—", delta_color="off")
                        g2.metric("Accel Count", f"{ac_emoji} {ac_val:.0f}", delta=f"{ac_z:+.1f}σ" if ac_z else "—", delta_color="off")
                        g3.metric("Decel Count", f"{dc_emoji} {dc_val:.0f}", delta=f"{dc_z:+.1f}σ" if dc_z else "—", delta_color="off")

                    st.markdown("**Why she's here:**")
                    for note in player["flag_notes"]:
                        st.write(f"• {note}")
        else:
            st.info("No data available for the most recent day.")
    else:
        st.info("Add wellness + training load data to show forecast watchouts.")

    st.markdown("---")
    st.caption(
        "Risk scoring: hard safety floors (sleep <6.5 hrs, soreness/stress >7) always flag. "
        "Personal deviations >1.5σ from 30-day baseline add flags. "
        "CMJ/RSI drops weighted ×1.5 vs subjective metrics. "
        "GPS load/accel/decel drops >1σ below personal baseline add flags. "
        "Gathercole et al. (2015) · Milewski et al. (2014) · Gabbett (2016)"
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
# TAB 8: ASK THE WATCHLIST
# ==============================================================================

with tab8:
    st.header("🔍 Ask the Watchlist")
    st.markdown("Ask questions about your players — instant answers.")

    if "query_to_run" not in st.session_state:
        st.session_state.query_to_run = ""

    c1, c2 = st.columns([2, 1])
    with c1:
        st.markdown("**How to use:** Type `poor sleep`, `high risk`, `readiness`, or `compare positions`")
        user_query = st.text_input(
            "Ask a question",
            placeholder="e.g., 'poor sleep' or 'high risk players'",
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
    with c2:
        st.markdown("### Quick Buttons")
        if st.button("Poor Sleep", use_container_width=True):
            st.session_state.query_to_run = "poor sleep"; st.rerun()
        if st.button("High Risk",  use_container_width=True):
            st.session_state.query_to_run = "high risk";  st.rerun()
        if st.button("Readiness",  use_container_width=True):
            st.session_state.query_to_run = "readiness";  st.rerun()

# ==============================================================================
# TAB 9 — CORRELATION EXPLORER
# ==============================================================================

with tab9:
    correlation_explorer_tab(wellness, training_load, force_plate, acwr, injuries, players)

# ==============================================================================
# FOOTER
# ==============================================================================

st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#666;'>"
    "<p><strong>WAIMS</strong> — Athlete Monitoring System | Python · Streamlit · SQLite</p>"
    "<p>Dallas Wings inspired demo — 90 days · 12 players · ~10,000+ data points</p>"
    "</div>",
    unsafe_allow_html=True,
)
