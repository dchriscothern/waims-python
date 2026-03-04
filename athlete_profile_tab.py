"""
Athlete Profile Tab — clean, professional layout
Includes GPS / Kinexon section (player load, accel count, decel count)
"""

import os
from datetime import datetime, timedelta

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

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


# ==============================================================================
# GAUGE / CHART HELPERS
# ==============================================================================

def create_gauge_chart(value, title, min_val=0, max_val=100, thresholds=[60, 80]):
    """
    Needle-style readiness gauge — clean arc with colour bands,
    thin needle, large centred score. Matches the screenshot aesthetic.
    """
    try:
        v = float(value)
    except Exception:
        v = 0.0
    v = max(float(min_val), min(float(max_val), v))
    y_start, g_start = thresholds

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=v,
        title={
            "text": title,
            "font": {"size": 13, "color": "#6b7280", "family": "Georgia, serif"},
        },
        number={
            "suffix": "/100",
            "font": {"size": 38, "color": "#111827", "family": "Georgia, serif"},
            "valueformat": ".0f",
        },
        gauge={
            "shape": "angular",
            "axis": {
                "range": [min_val, max_val],
                "tickvals": [0, 20, y_start, g_start, 100],
                "ticktext":  ["0", "20", str(y_start), str(g_start), "100"],
                "tickwidth": 1,
                "tickcolor": "#d1d5db",
                "tickfont":  {"size": 10, "color": "#9ca3af"},
            },
            # Needle only — thin transparent bar so the arc bands show
            "bar": {"color": "#1e293b", "thickness": 0.04},
            "bgcolor": "white",
            "borderwidth": 0,
            "steps": [
                {"range": [min_val,  y_start], "color": "#fecaca"},   # soft red
                {"range": [y_start,  g_start], "color": "#fef08a"},   # soft yellow
                {"range": [g_start,  max_val], "color": "#bbf7d0"},   # soft green
            ],
            "threshold": {
                "line": {"color": "#374151", "width": 3},
                "thickness": 0.85,
                "value": v,
            },
        },
    ))
    fig.update_layout(
        height=220,
        margin=dict(l=20, r=20, t=40, b=0),
        paper_bgcolor="white",
        font={"family": "Georgia, serif"},
    )
    return fig


def pill_meter(value, title, max_val=10, good_max=3, warn_max=7, invert=True, suffix=""):
    """
    Whistle-style pill meter — soft pastel bands, rounded pill, clean needle tick,
    value + status label top-right. Matches the screenshot aesthetic.
    """
    try:
        v = float(value)
    except Exception:
        v = 0.0
    v   = max(0.0, min(float(max_val), v))
    pct = (v / float(max_val)) * 100.0

    # Pastel palette — softer than the previous version
    RED    = "#ef4444";  RED_SOFT    = "#fecaca"
    AMBER  = "#f59e0b";  AMBER_SOFT  = "#fde68a"
    GREEN  = "#16a34a";  GREEN_SOFT  = "#bbf7d0"

    if invert:
        band1, band2, band3 = GREEN_SOFT, AMBER_SOFT, RED_SOFT
        if v <= good_max:
            val_color, status, status_bg = GREEN, "Low (better)", "#dcfce7"
        elif v <= warn_max:
            val_color, status, status_bg = AMBER, "Moderate",     "#fef9c3"
        else:
            val_color, status, status_bg = RED,   "High",         "#fee2e2"
        left_label, right_label = "Low (better)", "High"
    else:
        band1, band2, band3 = RED_SOFT, AMBER_SOFT, GREEN_SOFT
        if v >= warn_max:
            val_color, status, status_bg = GREEN, "High (better)", "#dcfce7"
        elif v >= good_max:
            val_color, status, status_bg = AMBER, "Moderate",      "#fef9c3"
        else:
            val_color, status, status_bg = RED,   "Low",           "#fee2e2"
        left_label, right_label = "Low", "High (better)"

    # Integer display if whole number, else 1dp
    display_val = f"{int(v)}" if v == int(v) else f"{v:.1f}"

    html = f"""
<div style="background:#ffffff; border:1px solid #e5e7eb; border-radius:14px;
    padding:16px 18px; box-shadow:0 1px 4px rgba(0,0,0,0.06);">
    <div style="display:flex; align-items:baseline; justify-content:space-between; margin-bottom:12px;">
        <span style="font-weight:700; font-size:14px; color:#111827;">{title}</span>
        <span style="font-weight:800; font-size:22px; color:#111827; font-family:Georgia,serif;">
            {display_val}<span style="font-size:13px; font-weight:600; color:#6b7280;">{suffix}</span>
        </span>
    </div>
    <div style="position:relative; height:16px; border-radius:999px; overflow:visible;
        background:transparent; margin-bottom:8px;">
        <!-- Banded pill -->
        <div style="display:flex; height:16px; border-radius:999px; overflow:hidden;
            border:1px solid rgba(0,0,0,0.06);">
            <div style="width:{(good_max/max_val)*100:.2f}%; background:{band1};"></div>
            <div style="width:{((warn_max-good_max)/max_val)*100:.2f}%; background:{band2};"></div>
            <div style="width:{((max_val-warn_max)/max_val)*100:.2f}%; background:{band3};"></div>
        </div>
        <!-- Needle tick -->
        <div style="position:absolute; left:calc({pct:.2f}% - 1.5px); top:-4px;
            width:3px; height:24px; background:#374151; border-radius:2px;
            box-shadow:0 1px 3px rgba(0,0,0,0.25);"></div>
    </div>
    <div style="display:flex; justify-content:space-between; font-size:11px; color:#9ca3af;
        font-weight:500; margin-top:2px;">
        <span>{left_label}</span>
        <span>{right_label}</span>
    </div>
</div>"""
    return html


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

def create_radar_chart(athlete_data, athlete_name):
    sleep_score    = (athlete_data["sleep_hours"] / 8) * 100
    physical_score = ((10 - athlete_data["soreness"]) / 10) * 100
    mental_score   = (athlete_data["mood"] / 10) * 100

    acwr_val = athlete_data.get("acwr", 1.0)
    if 0.8 <= acwr_val <= 1.3:
        load_score = 100
    elif acwr_val < 0.8:
        load_score = max(0, 100 - ((0.8 - acwr_val) * 100))
    else:
        load_score = max(0, 100 - ((acwr_val - 1.3) * 50))

    cmj         = athlete_data.get("cmj_height_cm", 30)
    neuro_score = min(100, (cmj / 40) * 100)

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

    # ── READINESS SCORE (wellness + CMJ/RSI modifier) ─────────────────────────
    readiness = (
        (latest_wellness["sleep_hours"] / 8) * 30
        + ((10 - latest_wellness["soreness"]) / 10) * 25
        + ((10 - latest_wellness["stress"]) / 10) * 25
        + (latest_wellness["mood"] / 10) * 20
    )
    if cmj_z is not None:
        readiness += max(-5, min(5, cmj_z * 2.5))
    if rsi_z is not None:
        readiness += max(-5, min(5, rsi_z * 2.5))
    readiness = max(0, min(100, readiness))

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

    with col2:
        st.markdown("**Overall Readiness**")
        if HAVE_ENHANCED_MODULES:
            fig = create_clean_speedometer(readiness, "Readiness Score", thresholds=[60, 80])
            st.plotly_chart(fig, use_container_width=True, key=f"gauge_readiness_{athlete_id}")
            st.markdown(create_recommendation_box(readiness, context="competition"), unsafe_allow_html=True)
        else:
            fig = create_gauge_chart(readiness, "Readiness Score", thresholds=[60, 80])
            st.plotly_chart(fig, use_container_width=True, key=f"gauge_readiness_{athlete_id}")
            if readiness >= 80:
                st.success("Full training cleared")
            elif readiness >= 60:
                st.info("Monitor closely")
            else:
                st.warning("50% volume reduction recommended")

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
        fig = create_radar_chart(radar_data, selected_athlete)
        st.plotly_chart(fig, use_container_width=True, key=f"radar_{athlete_id}")

    # ==========================================================================
    # KEY METRIC CARDS  (8 across: wellness + force plate + GPS)
    # ==========================================================================
    st.markdown("---")
    st.markdown("### Key Metrics")

    c1, c2, c3, c4, c5, c6, c7, c8 = st.columns(8)

    with c1:
        hrs = latest_wellness["sleep_hours"]
        s   = "good" if hrs >= 7.5 else ("warning" if hrs >= 6.5 else "bad")
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
        s = "good" if 0.8 <= latest_acwr <= 1.3 else ("warning" if latest_acwr <= 1.5 else "bad")
        st.markdown(create_metric_card("ACWR", f"{latest_acwr:.2f}", s), unsafe_allow_html=True)

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
                {"sleep": 6.5, "soreness": 7, "acwr": 1.5},
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

    with st.expander("Research References"):
        st.markdown(
            "- **Sleep:** <6.5 hrs → 1.7× injury risk (Milewski et al. 2014)\n"
            "- **ACWR:** >1.5 → 2.4× injury risk (Gabbett 2016)\n"
            "- **Soreness:** >7 requires monitoring (Hulin et al. 2016)\n"
            "- **CMJ/RSI:** Neuromuscular fatigue indicator — Gathercole et al. (2015)\n"
            "- **Accels/Decels:** Direction-change load; drops may indicate protective movement strategies"
        )
