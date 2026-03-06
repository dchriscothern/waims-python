"""
Athlete Profile Tab — clean, professional layout
Includes GPS / Kinexon section (player load, accel count, decel count)
"""

import os
import pickle
from datetime import datetime, timedelta
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

try:
    from improved_gauges import create_clean_speedometer, create_recommendation_box
    from z_score_module import (
        calculate_athlete_baselines,
        calculate_z_score,
        create_z_score_display,
        add_z_score_alerts,
    )
    from research_context import injury_mechanism_insight_box
    HAVE_ENHANCED_MODULES = True
except ImportError:
    HAVE_ENHANCED_MODULES = False

# ── Load shared readiness scorer pkl ─────────────────────────────────────────
# Same pkl as coach_command_center — single source of truth.
# Falls back to formula if pkl not yet trained (first run before train_models.py).
_READINESS_FN = None
try:
    _scorer_path = Path("models/readiness_scorer.pkl")
    if _scorer_path.exists():
        with open(_scorer_path, "rb") as _f:
            _scorer_data = pickle.load(_f)
            _READINESS_FN = _scorer_data.get("function")
except Exception:
    _READINESS_FN = None


# ==============================================================================
# SHARED READINESS CALCULATOR — single source of truth
# Mirrors train_models.py calculate_readiness_score exactly.
# Used by both athlete_profile_tab and coach_command_center via pkl scorer.
# ==============================================================================

def _calculate_readiness(row_dict):
    """
    Single readiness calculation — loads pkl scorer when available,
    falls back to identical formula. CMJ/RSI/Schedule all included.
    Rescaled ×100/70 so output spans 0–100 correctly.
    """
    if _READINESS_FN is not None:
        try:
            return _READINESS_FN(row_dict)
        except Exception:
            pass

    # Fallback — mirrors train_models.py calculate_readiness_score
    sleep_hrs = row_dict.get("sleep_hours", 7.5)
    sleep_q   = row_dict.get("sleep_quality", 7)
    sleep_s   = min(15, (sleep_hrs / 8.0) * 10 + (sleep_q / 10) * 5)
    sore_s    = ((10 - row_dict.get("soreness", 4)) / 10) * 10
    mood_s    = (row_dict.get("mood", 7) / 10) * 5
    stress_s  = ((10 - row_dict.get("stress", 4)) / 10) * 5

    cmj   = row_dict.get("cmj_height_cm")
    pos   = str(row_dict.get("position", row_dict.get("pos", "F")))
    bench = 38 if "G" in pos else (30 if "C" in pos else 34)
    cmj_s = min(15, (cmj / bench) * 15) if cmj and cmj > 0 else 11
    rsi   = row_dict.get("rsi_modified")
    rsi_s = min(10, (rsi / 0.45) * 10) if rsi and rsi > 0 else 8

    sched_s = 10
    if row_dict.get("is_back_to_back", 0): sched_s -= 4
    if row_dict.get("days_rest", 3) <= 1:  sched_s -= 2
    if row_dict.get("travel_flag", 0):
        sched_s -= min(3, abs(row_dict.get("time_zone_diff", 0)) * 1.5)
    if row_dict.get("unrivaled_flag", 0):  sched_s -= 2
    sched_s = max(0, sched_s)

    raw = sleep_s + sore_s + mood_s + stress_s + cmj_s + rsi_s + sched_s
    return round(min(100, raw * (100 / 70)), 1)


# ==============================================================================
# GAUGE / CHART HELPERS
# ==============================================================================

def create_gauge_chart(value, title, min_val=0, max_val=100, thresholds=[60, 80]):
    """
    Readiness gauge using Plotly — correct needle via scatter trace trick.
    Returns a Plotly figure (not HTML) so caller uses st.plotly_chart.
    """
    import math
    try:
        v = float(value)
    except Exception:
        v = 0.0
    v = max(float(min_val), min(float(max_val), v))
    y_start, g_start = thresholds

    # Build arc segments as filled pie slices masked to a donut
    # 180° gauge: 0=left, 100=right, mapped to 180°→0° in standard math angles
    def pct_to_rad(pct):
        return math.pi - (pct / 100.0) * math.pi

    def arc_points(start_pct, end_pct, r_outer=1.0, r_inner=0.65, n=40):
        pts_x, pts_y = [], []
        for i in range(n + 1):
            t = start_pct + (end_pct - start_pct) * i / n
            a = pct_to_rad(t)
            pts_x.append(r_outer * math.cos(a))
            pts_y.append(r_outer * math.sin(a))
        for i in range(n, -1, -1):
            t = start_pct + (end_pct - start_pct) * i / n
            a = pct_to_rad(t)
            pts_x.append(r_inner * math.cos(a))
            pts_y.append(r_inner * math.sin(a))
        pts_x.append(pts_x[0])
        pts_y.append(pts_y[0])
        return pts_x, pts_y

    zones = [
        (0,       y_start,  "#e05252"),
        (y_start, g_start,  "#f5c842"),
        (g_start, 85,       "#c8e6a0"),
        (85,      100,      "#5ec48a"),
    ]

    fig = go.Figure()

    # Gray background ring
    bx, by = arc_points(0, 100, 1.05, 0.62)
    fig.add_trace(go.Scatter(x=bx, y=by, fill="toself",
                             fillcolor="#e5e7eb", line=dict(width=0),
                             hoverinfo="skip", showlegend=False))

    # Colored zones
    for start, end, color in zones:
        ax, ay = arc_points(start, end)
        fig.add_trace(go.Scatter(x=ax, y=ay, fill="toself",
                                 fillcolor=color, line=dict(width=0),
                                 hoverinfo="skip", showlegend=False))

    # Needle — thin line from center to arc edge
    needle_pct = (v - min_val) / (max_val - min_val) * 100
    angle = pct_to_rad(needle_pct)
    nx, ny = 0.88 * math.cos(angle), 0.88 * math.sin(angle)

    # Needle as a very thin filled triangle
    perp = angle + math.pi / 2
    base = 0.04
    bx1 = base * math.cos(perp)
    by1 = base * math.sin(perp)

    fig.add_trace(go.Scatter(
        x=[nx, -bx1, bx1, nx],
        y=[ny, -by1, by1, ny],
        fill="toself", fillcolor="#1e293b",
        line=dict(width=0), hoverinfo="skip", showlegend=False,
    ))

    # Center cap
    theta = [i * 2 * math.pi / 40 for i in range(41)]
    fig.add_trace(go.Scatter(
        x=[0.07 * math.cos(t) for t in theta],
        y=[0.07 * math.sin(t) for t in theta],
        fill="toself", fillcolor="#1e293b",
        line=dict(width=0), hoverinfo="skip", showlegend=False,
    ))
    fig.add_trace(go.Scatter(
        x=[0.035 * math.cos(t) for t in theta],
        y=[0.035 * math.sin(t) for t in theta],
        fill="toself", fillcolor="white",
        line=dict(width=0), hoverinfo="skip", showlegend=False,
    ))

    # Tick labels at arc edge
    for label, pct in [("0", 0), ("20", 20), (str(y_start), y_start),
                        (str(g_start), g_start), ("100", 100)]:
        a = pct_to_rad(pct)
        tx, ty = 1.18 * math.cos(a), 1.18 * math.sin(a)
        fig.add_annotation(x=tx, y=ty, text=label, showarrow=False,
                           font=dict(size=10, color="#9ca3af"))

    # Recommendation text
    if v >= g_start:
        rec = "✅ Full training cleared"
    elif v >= y_start:
        rec = "👀 Monitor closely today"
    else:
        rec = "🚨 50% volume reduction recommended"

    fig.add_annotation(x=0, y=-0.28, text=f"<b>{int(v)}</b>/100",
                       showarrow=False,
                       font=dict(size=28, color="#111827", family="Georgia, serif"))
    fig.add_annotation(x=0, y=-0.52, text=rec,
                       showarrow=False,
                       font=dict(size=11, color="#6b7280"))

    fig.update_layout(
        xaxis=dict(range=[-1.3, 1.3], visible=False, scaleanchor="y"),
        yaxis=dict(range=[-0.7, 1.2], visible=False),
        height=320,
        margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="white",
        plot_bgcolor="white",
        title=dict(text=title, font=dict(size=12, color="#9ca3af"), x=0.5),
    )
    return fig



def pill_meter(value, title, max_val=10, good_max=3, warn_max=7, invert=True, suffix=""):
    """
    3-band pill meter matching the reference screenshot.
    Full GREEN→AMBER→RED (or RED→AMBER→GREEN) gradient always visible.
    Dark needle tick marks the current value position.
    """
    try:
        v = float(value)
    except Exception:
        v = 0.0
    v   = max(0.0, min(float(max_val), v))
    pct = (v / float(max_val)) * 100.0

    g1 = (good_max / max_val) * 100.0
    g2 = (warn_max / max_val) * 100.0

    if invert:
        # Low = good (soreness, stress): GREEN left → AMBER middle → RED right
        gradient = (
            f"linear-gradient(to right,"
            f"#5ec48a 0%,#5ec48a {g1:.1f}%,"
            f"#f5c842 {g1:.1f}%,#f5c842 {g2:.1f}%,"
            f"#e05252 {g2:.1f}%,#e05252 100%)"
        )
        left_label, right_label = "Low (better)", "High"
    else:
        # High = good (mood): RED left → AMBER middle → GREEN right
        gradient = (
            f"linear-gradient(to right,"
            f"#e05252 0%,#e05252 {g1:.1f}%,"
            f"#f5c842 {g1:.1f}%,#f5c842 {g2:.1f}%,"
            f"#5ec48a {g2:.1f}%,#5ec48a 100%)"
        )
        left_label, right_label = "Low", "High (better)"

    display_val = f"{int(v)}" if v == int(v) else f"{v:.1f}"

    return (
        f'<div style="background:#ffffff;border:1px solid #e5e7eb;border-radius:14px;'
        f'padding:16px 18px;box-shadow:0 1px 4px rgba(0,0,0,0.06);margin-bottom:0;">'
        f'<div style="display:flex;align-items:baseline;justify-content:space-between;margin-bottom:12px;">'
        f'<span style="font-weight:700;font-size:15px;color:#111827;">{title}</span>'
        f'<span style="font-weight:800;font-size:26px;color:#111827;font-family:Georgia,serif;line-height:1;">'
        f'{display_val}<span style="font-size:14px;font-weight:500;color:#9ca3af;">{suffix}</span>'
        f'</span></div>'
        f'<div style="position:relative;height:18px;border-radius:999px;margin-bottom:8px;background:{gradient};">'
        f'<div style="position:absolute;left:calc({pct:.1f}% - 2px);top:-5px;'
        f'width:4px;height:28px;background:#374151;border-radius:2px;'
        f'box-shadow:0 1px 4px rgba(0,0,0,0.4);"></div>'
        f'</div>'
        f'<div style="display:flex;justify-content:space-between;font-size:11px;color:#9ca3af;font-weight:500;">'
        f'<span>{left_label}</span><span>{right_label}</span>'
        f'</div></div>'
    )

def create_metric_card(label, value, status):
    colors = {
        "good":    ("#10b981", "#d1fae5"),
        "warning": ("#f59e0b", "#fef3c7"),
        "bad":     ("#ef4444", "#fee2e2"),
    }
    border, bg = colors.get(status, ("#6b7280", "#f3f4f6"))
    html = (
        f'<div style="background:{bg};border-left:4px solid {border};'
        f'padding:14px 16px;border-radius:6px;margin:4px 0;">'
        f'<div style="font-size:11px;color:{border};font-weight:600;letter-spacing:0.05em;'
        f'text-transform:uppercase;margin-bottom:4px;">{label}</div>'
        f'<div style="font-size:24px;font-weight:800;color:#1f2937;">{value}</div>'
        f'</div>'
    )
    return html


# ==============================================================================
# GPS Z-SCORE HELPER
# ==============================================================================

# WNBA population benchmarks (static 2025, upgrades to live API when available)
try:
    from wnba_api import get_player_zscore_vs_position, _get_static_benchmarks
    _wnba_benchmarks = _get_static_benchmarks()
    HAVE_WNBA_BENCHMARKS = True
except Exception:
    HAVE_WNBA_BENCHMARKS = False
    _wnba_benchmarks = None

def _gps_zscore(player_id, col, today_val, training_load_df, ref_date):
    """
    Returns (emoji, z_score_or_None).
    Low values flag for GPS load/accel/decel (lower than baseline = fatigue signal).
    """
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


# ==============================================================================
# PHOTO HELPER
# ==============================================================================

PHOTOS_DIR = "assets/photos"

def athlete_photo_block(ath_key: str):
    ath_key = str(ath_key).lower()
    for ext in (".jpg", ".jpeg", ".png"):
        path = f"{PHOTOS_DIR}/{ath_key}{ext}"
        if os.path.exists(path):
            st.image(path, use_container_width=True)
            return
    st.image(
        f"https://via.placeholder.com/200x250/2E86AB/FFFFFF?text={ath_key.replace('_', '+')}",
        use_container_width=True,
    )


# ==============================================================================
# RADAR CHART
# ==============================================================================

def create_radar_chart(athlete_data, athlete_name, position='F'):
    sleep_score    = (athlete_data["sleep_hours"] / 8) * 100
    physical_score = ((10 - athlete_data["soreness"]) / 10) * 100
    mental_score   = (athlete_data["mood"] / 10) * 100

    # Load score uses RSI + player load z-score — NOT ACWR
    # ACWR demoted to contextual flag (Impellizzeri 2020, 2025 meta-analysis)
    rsi_val  = athlete_data.get("rsi_modified", 0.35)
    load_z   = athlete_data.get("player_load_zscore", 0)
    rsi_score = min(100, (rsi_val / 0.45) * 100)
    load_mod  = max(-20, min(0, load_z * -5)) if load_z < -1 else 0
    load_score = max(0, min(100, rsi_score + load_mod))

    cmj         = athlete_data.get("cmj_height_cm", 30)
    # Position-matched WNBA baseline — aligns with train_models.py
    _cmj_bench  = 38 if "G" in str(position) else (30 if "C" in str(position) else 34)
    neuro_score = min(100, (cmj / _cmj_bench) * 100)

    # GPS score — player load normalised to position baseline
    gps_score = min(100, athlete_data.get("gps_load_pct", 75))

    categories = ["Sleep", "Physical", "Mental", "Load", "Neuro", "GPS"]
    values     = [sleep_score, physical_score, mental_score, load_score, neuro_score, gps_score]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values, theta=categories, fill="toself", name=athlete_name,
        fillcolor="rgba(46,134,171,0.25)", line=dict(color="rgb(46,134,171)", width=2),
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=False,
        title=f"{athlete_name} — Performance Profile",
        height=300,
        margin=dict(l=40, r=40, t=40, b=20),
    )
    return fig


# ==============================================================================
# MAIN TAB
# ==============================================================================

def athlete_profile_tab(wellness, training_load, acwr, force_plate, players, injuries=None):
    st.header("Athlete Profiles")

    athlete_names    = sorted(players["name"].tolist())
    selected_athlete = st.selectbox("Select Athlete", athlete_names)

    if not selected_athlete:
        st.info("Please select an athlete to view their profile")
        return

    athlete_info = players[players["name"] == selected_athlete].iloc[0]
    athlete_id   = athlete_info["player_id"]

    pid_num = pd.to_numeric(athlete_id, errors="coerce")
    ath_key = f"ath_{int(pid_num):03d}" if pd.notnull(pid_num) else str(athlete_id).strip().lower()

    latest_date     = wellness["date"].max()
    ref_date        = pd.to_datetime(latest_date)
    latest_wellness = wellness[(wellness["player_id"] == athlete_id) & (wellness["date"] == latest_date)]

    if len(latest_wellness) == 0:
        st.warning(f"No recent data for {selected_athlete}")
        return

    latest_wellness = latest_wellness.iloc[0]

    # ── ACWR ──────────────────────────────────────────────────────────────────
    latest_acwr_data = acwr[(acwr["player_id"] == athlete_id) & (acwr["date"] == latest_date)]
    latest_acwr      = float(latest_acwr_data.iloc[0]["acwr"]) if len(latest_acwr_data) > 0 else 1.0

    # ── FORCE PLATE ───────────────────────────────────────────────────────────
    latest_force = force_plate[(force_plate["player_id"] == athlete_id) & (force_plate["date"] == latest_date)]
    latest_cmj   = latest_force.iloc[0]["cmj_height_cm"] if len(latest_force) > 0 else None
    latest_rsi   = latest_force.iloc[0]["rsi_modified"]   if len(latest_force) > 0 else None

    # CMJ + RSI z-scores
    cmj_z = rsi_z = None
    if latest_cmj is not None and latest_rsi is not None:
        fp_history = force_plate[
            (force_plate["player_id"] == athlete_id) &
            (force_plate["date"] < latest_date)
        ].tail(30)
        if len(fp_history) >= 5:
            cmj_z = (latest_cmj - fp_history["cmj_height_cm"].mean()) / max(fp_history["cmj_height_cm"].std(), 0.5)
            rsi_z = (latest_rsi - fp_history["rsi_modified"].mean())   / max(fp_history["rsi_modified"].std(),  0.01)

    # ── GPS / KINEXON ─────────────────────────────────────────────────────────
    has_gps  = "player_load" in training_load.columns
    gps_row  = None
    pl_z = ac_z = dc_z = None
    pl_emoji = ac_emoji = dc_emoji = "🟡"

    if has_gps:
        gps_match = training_load[
            (training_load["player_id"] == athlete_id) &
            (training_load["date"] == latest_date)
        ]
        if len(gps_match) > 0:
            gps_row = gps_match.iloc[0].to_dict()
            pl_emoji, pl_z = _gps_zscore(athlete_id, "player_load", gps_row["player_load"], training_load, ref_date)
            ac_emoji, ac_z = _gps_zscore(athlete_id, "accel_count", gps_row["accel_count"], training_load, ref_date)
            dc_emoji, dc_z = _gps_zscore(athlete_id, "decel_count", gps_row["decel_count"], training_load, ref_date)

    # ── READINESS SCORE — shared formula, identical to Command Center + train_models ──
    # Passes full row dict including CMJ, RSI, position, schedule context
    # Uses pkl scorer when available; falls back to same rescaled 70→100 formula
    _readiness_row = dict(latest_wellness)
    _readiness_row["position"] = athlete_info.get("position", "F")
    if latest_cmj is not None: _readiness_row["cmj_height_cm"] = latest_cmj
    if latest_rsi is not None: _readiness_row["rsi_modified"]  = latest_rsi
    if cmj_z is not None:      _readiness_row["cmj_height_cm_zscore"] = cmj_z
    if rsi_z is not None:      _readiness_row["rsi_modified_zscore"]  = rsi_z
    if pl_z is not None:       _readiness_row["player_load_zscore"]   = pl_z
    if ac_z is not None:       _readiness_row["accel_count_zscore"]   = ac_z
    readiness = _calculate_readiness(_readiness_row)

    # GPS load % for radar (normalise player_load to 0–100 vs position baseline)
    gps_load_pct = 75  # default
    if gps_row and pl_z is not None:
        gps_load_pct = max(0, min(100, 75 + pl_z * 12))

    # ==========================================================================
    # HEADER ROW
    # ==========================================================================
    col1, col2, col3 = st.columns([1, 2, 2])

    with col1:
        st.markdown("**Profile**")
        athlete_photo_block(ath_key)
        pos = athlete_info.get("position", "")
        age = athlete_info.get("age", "")
        inj = athlete_info.get("injury_history_count", 0)
        st.markdown(f"**{pos}** · Age {age}")
        st.caption(f"Injury history: {inj} previous")

        # ── WNBA population context — shown only when game data available ────
        # NOTE: GPS player_load (Kinexon units) cannot be directly compared to
        # WNBA minutes averages — different units entirely.
        # This line activates when balldontlie paid tier provides actual game
        # minutes data (fetch_wings_benchmarks with use_live_api=True).
        # Until then: personal z-score (pl_z above) is the correct load signal.
        if HAVE_WNBA_BENCHMARKS and False:  # disabled until game minutes available
            pass  # placeholder — enable when balldontlie paid tier connected

    with col2:
        st.markdown("**Overall Readiness**")
        if HAVE_ENHANCED_MODULES:
            fig = create_clean_speedometer(readiness, "Readiness Score", thresholds=[60, 80])
            st.plotly_chart(fig, use_container_width=True, key=f"gauge_readiness_{athlete_id}")
            st.markdown(create_recommendation_box(readiness, context="competition"), unsafe_allow_html=True)
        else:
            # create_gauge_chart returns a Plotly figure
            fig = create_gauge_chart(readiness, "Readiness Score", thresholds=[60, 80])
            st.plotly_chart(fig, use_container_width=True, key=f"gauge_readiness_{athlete_id}")

    with col3:
        st.markdown("**Performance Profile**")
        radar_data = {
            "sleep_hours":    latest_wellness["sleep_hours"],
            "soreness":       latest_wellness["soreness"],
            "mood":           latest_wellness["mood"],
            "stress":         latest_wellness["stress"],
            "acwr":           latest_acwr,
            "cmj_height_cm":  latest_cmj if latest_cmj else 30,
            "gps_load_pct":   gps_load_pct,
        }
        fig = create_radar_chart(radar_data, selected_athlete, position=athlete_info.get('position','F'))
        st.plotly_chart(fig, use_container_width=True, key=f"radar_{athlete_id}")

    # ==========================================================================
    # KEY METRIC CARDS  (8 across: wellness + force plate + GPS)
    # ==========================================================================
    st.markdown("---")
    st.markdown("### Key Metrics")

    c1, c2, c3, c4, c5, c6, c7, c8 = st.columns(8)

    with c1:
        hrs = latest_wellness["sleep_hours"]
        # Walsh 2021: ≥7.0 good, 6.0-6.9 warning, <6.0 bad
        s   = "good" if hrs >= 7.0 else ("warning" if hrs >= 6.0 else "bad")
        st.markdown(create_metric_card("Sleep", f"{hrs:.1f} hrs", s), unsafe_allow_html=True)

    with c2:
        sor = latest_wellness["soreness"]
        s   = "good" if sor <= 4 else ("warning" if sor <= 7 else "bad")
        st.markdown(create_metric_card("Soreness", f"{sor:.0f}/10", s), unsafe_allow_html=True)

    with c3:
        moo = latest_wellness["mood"]
        s   = "good" if moo >= 7 else ("warning" if moo >= 5 else "bad")
        st.markdown(create_metric_card("Mood", f"{moo:.0f}/10", s), unsafe_allow_html=True)

    with c4:
        # ACWR shown as context only — not scored (Impellizzeri 2020)
        s = "good" if 0.8 <= latest_acwr <= 1.3 else ("warning" if latest_acwr <= 1.5 else "bad")
        st.markdown(create_metric_card("ACWR ⚠", f"{latest_acwr:.2f}", s), unsafe_allow_html=True)

    with c5:
        if latest_cmj is not None:
            s = "bad" if (cmj_z is not None and cmj_z <= -2.0) else ("warning" if (cmj_z is not None and cmj_z <= -1.0) else "good")
            st.markdown(create_metric_card("CMJ", f"{latest_cmj:.1f} cm", s), unsafe_allow_html=True)
        else:
            st.markdown(create_metric_card("CMJ", "No data", "warning"), unsafe_allow_html=True)

    with c6:
        if latest_rsi is not None:
            s = "bad" if (rsi_z is not None and rsi_z <= -2.0) else ("warning" if (rsi_z is not None and rsi_z <= -1.0) else "good")
            st.markdown(create_metric_card("RSI-Mod", f"{latest_rsi:.2f}", s), unsafe_allow_html=True)
        else:
            st.markdown(create_metric_card("RSI-Mod", "No data", "warning"), unsafe_allow_html=True)

    with c7:
        if gps_row:
            pl_val = gps_row.get("player_load", 0)
            s = "bad" if pl_emoji == "🔴" else ("warning" if pl_emoji == "🟡" else "good")
            delta_str = f" ({pl_z:+.1f}σ)" if pl_z is not None else ""
            st.markdown(create_metric_card("Load", f"{pl_val:.0f}{delta_str}", s), unsafe_allow_html=True)
        else:
            st.markdown(create_metric_card("Load", "No GPS", "warning"), unsafe_allow_html=True)

    with c8:
        if gps_row:
            ac_val = gps_row.get("accel_count", 0)
            s = "bad" if ac_emoji == "🔴" else ("warning" if ac_emoji == "🟡" else "good")
            delta_str = f" ({ac_z:+.1f}σ)" if ac_z is not None else ""
            st.markdown(create_metric_card("Accels", f"{ac_val}{delta_str}", s), unsafe_allow_html=True)
        else:
            st.markdown(create_metric_card("Accels", "No GPS", "warning"), unsafe_allow_html=True)

    # ==========================================================================
    # WELLNESS INDICATORS (pill meters)
    # ==========================================================================
    st.markdown("---")
    st.markdown("### Wellness Indicators")

    w1, w2, w3 = st.columns(3)
    with w1:
        st.markdown(pill_meter(latest_wellness["soreness"], "Soreness", max_val=10, good_max=3, warn_max=7, invert=True,  suffix="/10"), unsafe_allow_html=True)
    with w2:
        st.markdown(pill_meter(latest_wellness["stress"],   "Stress",   max_val=10, good_max=3, warn_max=7, invert=True,  suffix="/10"), unsafe_allow_html=True)
    with w3:
        st.markdown(pill_meter(latest_wellness["mood"],     "Mood",     max_val=10, good_max=4, warn_max=7, invert=False, suffix="/10"), unsafe_allow_html=True)

    # ==========================================================================
    # GPS / KINEXON SECTION
    # ==========================================================================
    st.markdown("---")
    st.markdown("### GPS / Kinexon")

    if has_gps and gps_row:
        st.caption("Kinexon tracking — values vs personal 30-day baseline (z-score). "
                   "Drops in accels/decels at normal distance may indicate protective movement strategies.")

        g1, g2, g3, g4, g5, g6 = st.columns(6)

        def _gps_metric(col_widget, label, val, emoji, z):
            delta = f"{z:+.1f}σ" if z is not None else "—"
            col_widget.metric(label, f"{emoji} {val:.0f}", delta=delta, delta_color="off")

        _gps_metric(g1, "Player Load",      gps_row.get("player_load", 0),      pl_emoji, pl_z)
        _gps_metric(g2, "Accel Count",       gps_row.get("accel_count", 0),      ac_emoji, ac_z)
        _gps_metric(g3, "Decel Count",       gps_row.get("decel_count", 0),      dc_emoji, dc_z)

        # Distance metrics — display only, no z-score flag shown here
        g4.metric("Distance (km)",   f"{gps_row.get('total_distance_km', 0):.2f}")
        g5.metric("HSR (m)",         f"{gps_row.get('hsr_distance_m', 0):.0f}")
        g6.metric("Sprint (m)",      f"{gps_row.get('sprint_distance_m', 0):.0f}")

        # 14-day GPS trend chart for this athlete
        st.markdown("#### 14-Day GPS Trends")
        cutoff_gps = pd.to_datetime(latest_date) - pd.Timedelta(days=14)
        gps_trend  = training_load[
            (training_load["player_id"] == athlete_id) &
            (training_load["date"] >= cutoff_gps)
        ].sort_values("date")

        if len(gps_trend) > 0:
            COLORS = ["#2E86AB", "#A23B72", "#F18F01"]
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=gps_trend["date"], y=gps_trend["player_load"],
                name="Player Load", mode="lines+markers",
                line=dict(color=COLORS[0], width=2),
            ))
            fig.add_trace(go.Scatter(
                x=gps_trend["date"], y=gps_trend["accel_count"],
                name="Accel Count", mode="lines+markers",
                line=dict(color=COLORS[1], width=2), yaxis="y2",
            ))
            fig.add_trace(go.Scatter(
                x=gps_trend["date"], y=gps_trend["decel_count"],
                name="Decel Count", mode="lines+markers",
                line=dict(color=COLORS[2], width=2, dash="dot"), yaxis="y2",
            ))
            fig.update_layout(
                height=280,
                yaxis =dict(title="Player Load (AU)"),
                yaxis2=dict(title="Accel / Decel Count", overlaying="y", side="right"),
                hovermode="x unified",
                margin=dict(l=10, r=10, t=20, b=20),
                legend=dict(orientation="h", y=-0.25),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Insufficient GPS history for trend chart.")

        # GPS flag notes
        gps_flags = []
        for col_name, label in [("player_load", "Player Load"), ("accel_count", "Accel Count"), ("decel_count", "Decel Count")]:
            val = gps_row.get(col_name, 0)
            emoji, z = _gps_zscore(athlete_id, col_name, val, training_load, ref_date)
            if emoji == "🔴" and z is not None:
                gps_flags.append(f"📡 {label} {val:.0f} — {abs(z):.1f}σ below baseline (high fatigue signal)")
            elif emoji == "🟡" and z is not None:
                gps_flags.append(f"📡 {label} {val:.0f} — {abs(z):.1f}σ below baseline")

        if gps_flags:
            st.markdown("**GPS Flags:**")
            for flag in gps_flags:
                st.warning(flag)
        else:
            st.success("📡 All GPS metrics within personal normal range")

    else:
        st.info("No GPS data available for this athlete today." if has_gps else
                "GPS columns not found in database — run generate_database.py to add GPS data.")

    # ==========================================================================
    # PERSONAL BASELINE Z-SCORES (wellness + CMJ/RSI)
    # ==========================================================================
    if HAVE_ENHANCED_MODULES:
        baselines = calculate_athlete_baselines(wellness, athlete_id, lookback_days=30)

        if baselines:
            st.markdown("---")
            st.markdown("### Personal Baseline Comparison")
            st.caption("Current values vs this athlete's 30-day average. "
                       "Force plate provides objective fatigue signal.")

            z1, z2, z3 = st.columns(3)

            with z1:
                sleep_z = calculate_z_score(
                    latest_wellness["sleep_hours"],
                    baselines["sleep_hours"]["mean"],
                    baselines["sleep_hours"]["std"],
                )
                st.markdown(create_z_score_display("Sleep Duration", latest_wellness["sleep_hours"], sleep_z, "higher_better", " hrs"), unsafe_allow_html=True)
                soreness_z = calculate_z_score(
                    latest_wellness["soreness"],
                    baselines["soreness"]["mean"],
                    baselines["soreness"]["std"],
                )
                st.markdown(create_z_score_display("Soreness", latest_wellness["soreness"], soreness_z, "lower_better", "/10"), unsafe_allow_html=True)

            with z2:
                mood_z = calculate_z_score(
                    latest_wellness["mood"],
                    baselines["mood"]["mean"],
                    baselines["mood"]["std"],
                )
                st.markdown(create_z_score_display("Mood", latest_wellness["mood"], mood_z, "higher_better", "/10"), unsafe_allow_html=True)
                stress_z = calculate_z_score(
                    latest_wellness["stress"],
                    baselines["stress"]["mean"],
                    baselines["stress"]["std"],
                )
                st.markdown(create_z_score_display("Stress", latest_wellness["stress"], stress_z, "lower_better", "/10"), unsafe_allow_html=True)

            with z3:
                if cmj_z is not None:
                    st.markdown(create_z_score_display("CMJ Height", latest_cmj, cmj_z, "higher_better", " cm"), unsafe_allow_html=True)
                else:
                    st.info("CMJ: insufficient baseline data")
                if rsi_z is not None:
                    st.markdown(create_z_score_display("RSI-Modified", latest_rsi, rsi_z, "higher_better", ""), unsafe_allow_html=True)
                else:
                    st.info("RSI: insufficient baseline data")

            # Smart alerts (wellness + force plate)
            alerts = add_z_score_alerts(
                dict(latest_wellness),
                baselines,
                {"sleep": 7.0, "soreness": 7, "acwr": 1.5},  # Walsh 2021
            )
            if cmj_z is not None and cmj_z <= -2.0:
                alerts.append({"type": "critical", "metric": "CMJ",
                                "message": f"CMJ {latest_cmj:.1f} cm — {abs(cmj_z):.1f}σ below baseline (severe neuromuscular fatigue)",
                                "color": "#ef4444"})
            elif cmj_z is not None and cmj_z <= -1.0:
                alerts.append({"type": "warning", "metric": "CMJ",
                                "message": f"CMJ {latest_cmj:.1f} cm — {abs(cmj_z):.1f}σ below baseline (neuromuscular fatigue)",
                                "color": "#f59e0b"})
            if rsi_z is not None and rsi_z <= -2.0:
                alerts.append({"type": "critical", "metric": "RSI",
                                "message": f"RSI {latest_rsi:.2f} — {abs(rsi_z):.1f}σ below baseline (reduced reactive strength)",
                                "color": "#ef4444"})
            elif rsi_z is not None and rsi_z <= -1.0:
                alerts.append({"type": "warning", "metric": "RSI",
                                "message": f"RSI {latest_rsi:.2f} — {abs(rsi_z):.1f}σ below baseline",
                                "color": "#f59e0b"})

            if alerts:
                st.markdown("**Alerts**")
                for a in alerts:
                    if a["type"] == "critical":
                        st.error(a["message"])
                    elif a["type"] == "warning":
                        st.warning(a["message"])
                    else:
                        st.info(a["message"])

    # ==========================================================================
    # 7-DAY TRENDS  (wellness + force plate overlay)
    # ==========================================================================
    st.markdown("---")
    st.markdown("### 7-Day Wellness & Force Plate Trends")

    week_ago   = latest_date - timedelta(days=7)
    weekly     = wellness[
        (wellness["player_id"] == athlete_id) &
        (wellness["date"] >= week_ago) &
        (wellness["date"] <= latest_date)
    ].sort_values("date")
    weekly_fp  = force_plate[
        (force_plate["player_id"] == athlete_id) &
        (force_plate["date"] >= week_ago) &
        (force_plate["date"] <= latest_date)
    ].sort_values("date")

    if len(weekly) > 0:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=weekly["date"], y=weekly["sleep_hours"], mode="lines+markers",
                                 name="Sleep (hrs)", line=dict(color="#2E86AB", width=2)))
        fig.add_trace(go.Scatter(x=weekly["date"], y=weekly["soreness"], mode="lines+markers",
                                 name="Soreness (0–10)", line=dict(color="#A23B72", width=2)))
        if len(weekly_fp) > 0:
            fig.add_trace(go.Scatter(x=weekly_fp["date"], y=weekly_fp["cmj_height_cm"], mode="lines+markers",
                                     name="CMJ (cm)", line=dict(color="#F18F01", width=2, dash="dot"), yaxis="y2"))
            fig.add_trace(go.Scatter(x=weekly_fp["date"], y=weekly_fp["rsi_modified"], mode="lines+markers",
                                     name="RSI-Mod", line=dict(color="#44BBA4", width=2, dash="dot"), yaxis="y2"))
        fig.update_layout(
            title=f"{selected_athlete} — Weekly Trends",
            yaxis =dict(title="Wellness"),
            yaxis2=dict(title="Force Plate", overlaying="y", side="right"),
            height=320, hovermode="x unified",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Insufficient data for 7-day trends")

    # ==========================================================================
    # BASKETBALL-SPECIFIC RISK CONTEXT
    # ==========================================================================
    if HAVE_ENHANCED_MODULES:
        st.markdown("---")
        st.markdown("### Basketball-Specific Risk Context")
        context = st.radio(
            "Next activity:", ["Practice", "Competition"],
            horizontal=True, key=f"context_{athlete_id}",
        )
        injury_mechanism_insight_box(
            {
                "sleep_hours":    latest_wellness["sleep_hours"],
                "soreness":       latest_wellness["soreness"],
                "acwr":           latest_acwr,
                "cmj_zscore":     cmj_z,
                "rsi_zscore":     rsi_z,
                "cmj_height_cm":  latest_cmj,
                "rsi_modified":   latest_rsi,
                "player_load_z":  pl_z,
                "accel_count_z":  ac_z,
            },
            context.lower(),
        )

    # ── 7-DAY RISK + LOAD PROJECTION ─────────────────────────────────────────
    st.markdown("---")
    st.markdown("### Risk Outlook & Load Projection")
    st.caption("How is this player trending — and what happens to her readiness if she plays tonight?")

    rp_col1, rp_col2 = st.columns([1, 2])

    with rp_col1:
        # Build current risk score via classify_player_full if available
        try:
            from z_score_module import calculate_athlete_baselines, calculate_z_score
            from dashboard_helpers import classify_player_full  # may not exist — graceful fallback
        except ImportError:
            classify_player_full = None

        # Estimate injury risk from wellness + force plate signals
        risk_flags = 0
        risk_reasons = []
        sleep_v = float(latest_wellness.get("sleep_hours", 7.5))
        sore_v  = float(latest_wellness.get("soreness", 4))
        stress_v = float(latest_wellness.get("stress", 4))

        if sleep_v < 6.0:  risk_flags += 2; risk_reasons.append("critically short sleep")
        elif sleep_v < 7.0: risk_flags += 1; risk_reasons.append("short sleep")
        if sore_v > 7:      risk_flags += 1; risk_reasons.append("high soreness")
        if stress_v > 7:    risk_flags += 1; risk_reasons.append("high stress")
        if cmj_z is not None and cmj_z < -1.5: risk_flags += 2; risk_reasons.append("CMJ well below baseline")
        elif cmj_z is not None and cmj_z < -1.0: risk_flags += 1; risk_reasons.append("CMJ below baseline")
        if rsi_z is not None and rsi_z < -1.5: risk_flags += 2; risk_reasons.append("RSI well below baseline")
        elif rsi_z is not None and rsi_z < -1.0: risk_flags += 1; risk_reasons.append("RSI below baseline")

        profile_risk = min(100, risk_flags * 15)
        if profile_risk >= 60:
            risk_color, risk_level, risk_msg = "#dc2626", "HIGH RISK", "Prioritise recovery. Limit high-intensity work this week."
        elif profile_risk >= 30:
            risk_color, risk_level, risk_msg = "#d97706", "ELEVATED", "Monitor closely. Be ready to modify session on the fly."
        else:
            risk_color, risk_level, risk_msg = "#16a34a", "LOW RISK", "No elevated concern based on current signals."

        st.markdown(
            f'<div style="background:#f8fafc;border:2px solid {risk_color};border-radius:10px;'
            f'padding:16px;text-align:center;">'
            f'<div style="font-size:11px;font-weight:700;letter-spacing:0.12em;'
            f'text-transform:uppercase;color:#64748b;margin-bottom:4px;">7-Day Injury Risk</div>'
            f'<div style="font-size:42px;font-weight:800;color:{risk_color};line-height:1;">'
            f'{profile_risk}</div>'
            f'<div style="font-size:10px;color:#94a3b8;margin-bottom:8px;">out of 100</div>'
            f'<div style="font-size:11px;font-weight:700;color:{risk_color};'
            f'letter-spacing:0.08em;">{risk_level}</div>'
            f'<div style="font-size:11px;color:#475569;margin-top:6px;line-height:1.4;">'
            f'{risk_msg}</div>'
            + (f'<div style="font-size:10px;color:#94a3b8;margin-top:8px;">'
               f'Signals: {", ".join(risk_reasons)}</div>' if risk_reasons else "")
            + '</div>',
            unsafe_allow_html=True
        )
        st.caption("Score = count of active warning flags × 15. Each flag = one signal "
                   "outside safe threshold or >1σ below personal baseline. "
                   "Walsh 2021 · Gathercole 2015 · Gabbett 2016.")

    with rp_col2:
        st.markdown("**Load Projection — what happens to readiness after tonight?**")
        load_scenario_ap = st.radio(
            "Tonight's plan:",
            ["Rest / Practice only", "Typical game load (~28 min)",
             "Heavy game load (~36 min)", "Back-to-back game"],
            horizontal=False, key=f"load_scenario_{athlete_id}",
        )

        # Evidence-based adjustments — female basketball specific
        # Pernigoni 2024 (44-study basketball SR); Goulart 2022 (female meta);
        # Charest 2021 JCSM (B2B); Walsh 2021 BJSM (sleep)
        load_fx = {
            "Rest / Practice only":        {"sleep_adj": +0.1, "sore_adj": -0.3, "stress_adj": -0.5, "b2b": 0},
            "Typical game load (~28 min)": {"sleep_adj": -0.2, "sore_adj": +0.8, "stress_adj": +0.3, "b2b": 0},
            "Heavy game load (~36 min)":   {"sleep_adj": -0.4, "sore_adj": +1.5, "stress_adj": +0.5, "b2b": 0},
            "Back-to-back game":           {"sleep_adj": -0.7, "sore_adj": +2.5, "stress_adj": +1.5, "b2b": 1},
        }
        cmj_fx = {
            "Rest / Practice only": 0, "Typical game load (~28 min)": -0.5,
            "Heavy game load (~36 min)": -1.5, "Back-to-back game": -2.5,
        }
        fx = load_fx[load_scenario_ap]

        proj_sleep   = max(4.5, min(9.5, sleep_v + fx["sleep_adj"]))
        proj_soreness = max(0,  min(10,  sore_v  + fx["sore_adj"]))
        proj_stress  = max(1,  min(10,  stress_v + fx["stress_adj"]))
        proj_mood    = max(1,  min(10,  float(latest_wellness.get("mood", 7)) - fx["stress_adj"] * 0.3))
        proj_cmj     = max(18, latest_cmj + cmj_fx[load_scenario_ap]) if latest_cmj else None
        proj_rsi     = latest_rsi  # RSI held flat (female players: minimal 24h CMJ/RSI drop)

        ap_player_pos = players[players["player_id"] == athlete_id]["position"].values
        ap_player_pos = ap_player_pos[0] if len(ap_player_pos) > 0 else "F"

        proj_row = {
            "sleep_hours": proj_sleep, "sleep_quality": latest_wellness.get("sleep_quality", 7),
            "soreness": proj_soreness, "stress": proj_stress, "mood": proj_mood,
            "cmj_height_cm": proj_cmj, "rsi_modified": proj_rsi,
            "position": ap_player_pos, "is_back_to_back": fx["b2b"], "days_rest": 0 if fx["b2b"] else 1,
        }
        today_score_ap = readiness
        tomorrow_score = _calculate_readiness(proj_row)
        delta_ap = tomorrow_score - today_score_ap
        delta_str_ap = f"+{delta_ap:.0f}" if delta_ap > 0 else f"{delta_ap:.0f}"
        tmr_status = "READY" if tomorrow_score >= 80 else ("MONITOR" if tomorrow_score >= 60 else "PROTECT")
        tmr_color  = "#16a34a" if tomorrow_score >= 80 else ("#d97706" if tomorrow_score >= 60 else "#dc2626")

        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("Today", f"{today_score_ap:.0f}%")
        mc2.metric("Tomorrow (projected)", f"{tomorrow_score:.0f}%", delta=delta_str_ap)
        mc3.metric("Status", tmr_status)

        # Prescriptive recommendation — specific and actionable
        if tmr_status == "PROTECT":
            ap_rec_color, ap_rec_bg   = "#dc2626", "#fef2f2"
            ap_rec_head = "Restrict Tonight"
            ap_rec_body = (
                f"Cap at 20–26 minutes tonight depending on game situation. "
                f"Remove from high-intensity interval work in practice. "
                f"Check in before session — ask about sleep quality and leg fatigue specifically. "
                f"Projected readiness tomorrow: {tomorrow_score:.0f}% (PROTECT)."
            )
        elif tmr_status == "MONITOR":
            ap_rec_color, ap_rec_bg   = "#d97706", "#fffbeb"
            ap_rec_head = "Monitor Closely"
            ap_rec_body = (
                f"Standard minutes available but watch warmup movement quality. "
                f"If soreness ≥7/10 or movement looks laboured, reduce early. "
                f"Prioritise skill work over high-intensity conditioning reps. "
                f"Projected readiness tomorrow: {tomorrow_score:.0f}% (MONITOR)."
            )
        else:
            ap_rec_color, ap_rec_bg   = "#16a34a", "#f0fdf4"
            ap_rec_head = "Clear for Full Load"
            ap_rec_body = (
                f"No restrictions needed. Full minutes and full training available. "
                f"Projected readiness tomorrow: {tomorrow_score:.0f}% ({tmr_status})."
            )

        st.markdown(
            f'<div style="background:{ap_rec_bg};border-left:4px solid {ap_rec_color};'
            f'border-radius:0 8px 8px 0;padding:12px 16px;margin-top:6px;">'
            f'<div style="font-size:11px;font-weight:700;letter-spacing:0.1em;'
            f'text-transform:uppercase;color:{ap_rec_color};margin-bottom:4px;">Staff Recommendation</div>'
            f'<div style="font-size:13px;font-weight:700;color:#0f172a;margin-bottom:4px;">{ap_rec_head}</div>'
            f'<div style="font-size:12px;color:#1e293b;line-height:1.6;">{ap_rec_body}</div>'
            f'</div>',
            unsafe_allow_html=True
        )
        st.caption("Projections: Pernigoni 2024 (44-study basketball SR, female-specific CMJ recovery); "
                   "Goulart 2022 (female meta-analysis); Charest 2021 JCSM (B2B sleep/travel). "
                   "Minutes thresholds: Orlando Magic sport science framework (NBA practitioner 2024).")

    with st.expander("Research References"):
        st.markdown(
            "- **Sleep:** <7 hrs → elevated injury risk (Walsh et al. 2021 BJSM consensus; 2025 meta-analysis OR=1.34); <6 hrs = red flag. Female athletes: compounded by hormonal variability (Charest & Grandner 2020)\n"
            "- **ACWR ⚠ (contextual flag only):** Gabbett 2016 established >1.5 as high-risk zone, but Impellizzeri et al. 2020 (BJSM) identified statistical coupling flaws and 2025 meta-analysis (22 cohort studies) recommends 'use with caution' — not scored in readiness formula\n"
            "- **Soreness:** >7 requires monitoring (Hulin et al. 2016)\n"
            "- **CMJ/RSI:** Neuromuscular fatigue indicator — Gathercole et al. (2015)\n"
            "- **Accels/Decels:** Direction-change load; drops may indicate protective movement strategies\n"
            "- **Post-match recovery (female):** Pernigoni et al. 2024 (44-study basketball SR); no CMJ drop at 24h in female players (Delextrat); Goulart 2022 female meta-analysis\n"
            "- **B2B fatigue:** Charest et al. 2021 JCSM (NBA travel/circadian); Clark et al. 2025 PLOS One (108-study indoor sports SR)"
        )
