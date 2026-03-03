"""
Athlete Profile Tab — clean, professional layout
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
    try:
        v = float(value)
    except Exception:
        v = 0.0
    v = max(float(min_val), min(float(max_val), v))
    y_start, g_start = thresholds

    if v >= g_start:
        status_color = "#10b981"
    elif v >= y_start:
        status_color = "#f59e0b"
    else:
        status_color = "#ef4444"

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=v,
        title={"text": title, "font": {"size": 14}},
        number={"suffix": "%", "font": {"size": 26, "color": "#111827"}},
        gauge={
            "shape": "angular",
            "axis": {
                "range": [min_val, max_val],
                "tickvals": [min_val, (min_val + max_val) / 2, max_val],
                "tickwidth": 1,
                "tickcolor": "rgba(17,24,39,0.35)",
                "tickfont": {"size": 10, "color": "rgba(17,24,39,0.65)"},
            },
            "bar": {"color": status_color, "thickness": 1.0},
            "bgcolor": "#f3f4f6",
            "borderwidth": 0,
            "steps": [
                {"range": [min_val, y_start], "color": "rgba(239,68,68,0.12)"},
                {"range": [y_start, g_start], "color": "rgba(245,158,11,0.12)"},
                {"range": [g_start, max_val], "color": "rgba(16,185,129,0.12)"},
            ],
        },
    ))
    fig.update_layout(height=190, margin=dict(l=10, r=10, t=44, b=0), paper_bgcolor="white", font={"family": "Arial"})
    return fig


def pill_meter(value, title, max_val=10, good_max=3, warn_max=7, invert=True, suffix=""):
    try:
        v = float(value)
    except Exception:
        v = 0.0
    v = max(0.0, min(float(max_val), v))
    pct = (v / float(max_val)) * 100.0

    GREEN, AMBER, RED = "#16a34a", "#f59e0b", "#ef4444"
    GREEN_BG, AMBER_BG, RED_BG = "rgba(22,163,74,0.18)", "rgba(245,158,11,0.20)", "rgba(239,68,68,0.18)"

    if invert:
        band1, band2, band3 = GREEN_BG, AMBER_BG, RED_BG
        val_color, status = (GREEN, "GOOD") if v <= good_max else ((AMBER, "CAUTION") if v <= warn_max else (RED, "HIGH"))
        legend = f"Good ≤{good_max}{suffix}  ·  Caution ≤{warn_max}{suffix}  ·  High >{warn_max}{suffix}"
    else:
        band1, band2, band3 = RED_BG, AMBER_BG, GREEN_BG
        val_color, status = (GREEN, "GOOD") if v >= warn_max else ((AMBER, "CAUTION") if v >= good_max else (RED, "LOW"))
        legend = f"Low <{good_max}{suffix}  ·  Caution <{warn_max}{suffix}  ·  Good ≥{warn_max}{suffix}"

    html = (
        f'<div style="background:#fff;border:1px solid rgba(0,0,0,0.08);border-radius:10px;padding:12px;">'
        f'<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">'
        f'<span style="font-weight:700;font-size:13px;color:#111827;">{title}</span>'
        f'<span style="font-weight:800;font-size:13px;color:{val_color};">{v:.1f}{suffix} <span style="font-weight:600;opacity:0.75;">{status}</span></span>'
        f'</div>'
        f'<div style="position:relative;height:14px;border-radius:999px;overflow:hidden;border:1px solid rgba(0,0,0,0.08);">'
        f'<div style="display:flex;height:100%;">'
        f'<div style="width:{(good_max/max_val)*100:.2f}%;background:{band1};"></div>'
        f'<div style="width:{((warn_max-good_max)/max_val)*100:.2f}%;background:{band2};"></div>'
        f'<div style="width:{((max_val-warn_max)/max_val)*100:.2f}%;background:{band3};"></div>'
        f'</div>'
        f'<div style="position:absolute;left:calc({pct:.2f}% - 1px);top:-6px;width:2px;height:26px;background:{val_color};border-radius:2px;"></div>'
        f'</div>'
        f'<div style="margin-top:6px;font-size:11px;color:#6b7280;">{legend}</div>'
        f'</div>'
    )
    return html


def create_metric_card(label, value, status):
    """Clean metric card — no icons, no emojis."""
    colors = {
        "good":    ("#10b981", "#d1fae5"),
        "warning": ("#f59e0b", "#fef3c7"),
        "bad":     ("#ef4444", "#fee2e2"),
    }
    border, bg = colors.get(status, ("#6b7280", "#f3f4f6"))
    html = (
        f'<div style="background:{bg};border-left:4px solid {border};'
        f'padding:14px 16px;border-radius:6px;margin:4px 0;">'
        f'<div style="font-size:11px;color:{border};font-weight:600;letter-spacing:0.05em;text-transform:uppercase;margin-bottom:4px;">{label}</div>'
        f'<div style="font-size:24px;font-weight:800;color:#1f2937;">{value}</div>'
        f'</div>'
    )
    return html


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

    cmj = athlete_data.get("cmj_height_cm", 30)
    neuro_score = min(100, (cmj / 40) * 100)

    categories = ["Sleep", "Physical", "Mental", "Load", "Neuro"]
    values     = [sleep_score, physical_score, mental_score, load_score, neuro_score]

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
    latest_wellness = wellness[(wellness["player_id"] == athlete_id) & (wellness["date"] == latest_date)]

    if len(latest_wellness) == 0:
        st.warning(f"No recent data for {selected_athlete}")
        return

    latest_wellness = latest_wellness.iloc[0]

    latest_acwr_data = acwr[(acwr["player_id"] == athlete_id) & (acwr["date"] == latest_date)]
    latest_acwr = float(latest_acwr_data.iloc[0]["acwr"]) if len(latest_acwr_data) > 0 else 1.0

    latest_force = force_plate[(force_plate["player_id"] == athlete_id) & (force_plate["date"] == latest_date)]
    latest_cmj   = latest_force.iloc[0]["cmj_height_cm"] if len(latest_force) > 0 else None
    latest_rsi   = latest_force.iloc[0]["rsi_modified"]   if len(latest_force) > 0 else None

    # ── CMJ + RSI z-scores vs player's 30-day force plate baseline ────────────
    cmj_z = rsi_z = None
    if latest_cmj is not None and latest_rsi is not None:
        fp_history = force_plate[
            (force_plate["player_id"] == athlete_id) &
            (force_plate["date"] < latest_date)
        ].tail(30)
        if len(fp_history) >= 5:
            cmj_mean = fp_history["cmj_height_cm"].mean()
            cmj_std  = max(fp_history["cmj_height_cm"].std(), 0.5)
            cmj_z    = (latest_cmj - cmj_mean) / cmj_std

            rsi_mean = fp_history["rsi_modified"].mean()
            rsi_std  = max(fp_history["rsi_modified"].std(), 0.01)
            rsi_z    = (latest_rsi - rsi_mean) / rsi_std

    # ── Readiness score (includes CMJ modifier if available) ──────────────────
    readiness = (
        (latest_wellness["sleep_hours"] / 8) * 30
        + ((10 - latest_wellness["soreness"]) / 10) * 25
        + ((10 - latest_wellness["stress"]) / 10) * 25
        + (latest_wellness["mood"] / 10) * 20
    )
    # CMJ/RSI z-score modifier (±5 pts each, objective fatigue signal)
    if cmj_z is not None:
        readiness += max(-5, min(5, cmj_z * 2.5))
    if rsi_z is not None:
        readiness += max(-5, min(5, rsi_z * 2.5))
    readiness = max(0, min(100, readiness))

    # ------------------------------------------------------------------
    # HEADER ROW
    # ------------------------------------------------------------------
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
            "sleep_hours":   latest_wellness["sleep_hours"],
            "soreness":      latest_wellness["soreness"],
            "mood":          latest_wellness["mood"],
            "stress":        latest_wellness["stress"],
            "acwr":          latest_acwr,
            "cmj_height_cm": latest_cmj if latest_cmj else 30,
        }
        fig = create_radar_chart(radar_data, selected_athlete)
        st.plotly_chart(fig, use_container_width=True, key=f"radar_{athlete_id}")

    # ------------------------------------------------------------------
    # METRIC CARDS — 6 across including CMJ + RSI
    # ------------------------------------------------------------------
    st.markdown("---")
    st.markdown("### Key Metrics")

    c1, c2, c3, c4, c5, c6 = st.columns(6)

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

    # ------------------------------------------------------------------
    # WELLNESS INDICATORS (pill meters)
    # ------------------------------------------------------------------
    st.markdown("---")
    st.markdown("### Wellness Indicators")

    w1, w2, w3 = st.columns(3)
    with w1:
        st.markdown(pill_meter(latest_wellness["soreness"], "Soreness", max_val=10, good_max=3, warn_max=7, invert=True,  suffix="/10"), unsafe_allow_html=True)
    with w2:
        st.markdown(pill_meter(latest_wellness["stress"],   "Stress",   max_val=10, good_max=3, warn_max=7, invert=True,  suffix="/10"), unsafe_allow_html=True)
    with w3:
        st.markdown(pill_meter(latest_wellness["mood"],     "Mood",     max_val=10, good_max=4, warn_max=7, invert=False, suffix="/10"), unsafe_allow_html=True)

    # ------------------------------------------------------------------
    # PERSONAL BASELINE (Z-SCORES) — wellness + CMJ/RSI
    # ------------------------------------------------------------------
    if HAVE_ENHANCED_MODULES:
        baselines = calculate_athlete_baselines(wellness, athlete_id, lookback_days=30)

        if baselines:
            st.markdown("---")
            st.markdown("### Personal Baseline Comparison")
            st.caption("Current values vs this athlete's 30-day average. Force plate provides objective fatigue signal.")

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

            # Smart alerts
            alerts = add_z_score_alerts(
                dict(latest_wellness),
                baselines,
                {"sleep": 6.5, "soreness": 7, "acwr": 1.5},
            )
            # Add CMJ/RSI alerts manually
            if cmj_z is not None and cmj_z <= -2.0:
                alerts.append({"type": "critical", "metric": "CMJ", "message": f"CMJ {latest_cmj:.1f} cm — {abs(cmj_z):.1f}σ below baseline (severe neuromuscular fatigue)", "color": "#ef4444"})
            elif cmj_z is not None and cmj_z <= -1.0:
                alerts.append({"type": "warning", "metric": "CMJ", "message": f"CMJ {latest_cmj:.1f} cm — {abs(cmj_z):.1f}σ below baseline (neuromuscular fatigue)", "color": "#f59e0b"})
            if rsi_z is not None and rsi_z <= -2.0:
                alerts.append({"type": "critical", "metric": "RSI", "message": f"RSI {latest_rsi:.2f} — {abs(rsi_z):.1f}σ below baseline (reduced reactive strength)", "color": "#ef4444"})
            elif rsi_z is not None and rsi_z <= -1.0:
                alerts.append({"type": "warning", "metric": "RSI", "message": f"RSI {latest_rsi:.2f} — {abs(rsi_z):.1f}σ below baseline", "color": "#f59e0b"})

            if alerts:
                st.markdown("**Alerts**")
                for a in alerts:
                    if a["type"] == "critical":
                        st.error(a["message"])
                    elif a["type"] == "warning":
                        st.warning(a["message"])
                    else:
                        st.info(a["message"])

    # ------------------------------------------------------------------
    # 7-DAY TRENDS
    # ------------------------------------------------------------------
    st.markdown("---")
    st.markdown("### 7-Day Trends")

    week_ago = latest_date - timedelta(days=7)
    weekly   = wellness[
        (wellness["player_id"] == athlete_id)
        & (wellness["date"] >= week_ago)
        & (wellness["date"] <= latest_date)
    ].sort_values("date")

    weekly_fp = force_plate[
        (force_plate["player_id"] == athlete_id)
        & (force_plate["date"] >= week_ago)
        & (force_plate["date"] <= latest_date)
    ].sort_values("date")

    if len(weekly) > 0:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=weekly["date"], y=weekly["sleep_hours"], mode="lines+markers", name="Sleep (hrs)",     line=dict(color="#2E86AB", width=2)))
        fig.add_trace(go.Scatter(x=weekly["date"], y=weekly["soreness"],    mode="lines+markers", name="Soreness (0–10)", line=dict(color="#A23B72", width=2)))
        if len(weekly_fp) > 0:
            fig.add_trace(go.Scatter(x=weekly_fp["date"], y=weekly_fp["cmj_height_cm"], mode="lines+markers", name="CMJ (cm)",  line=dict(color="#F18F01", width=2, dash="dot"), yaxis="y2"))
            fig.add_trace(go.Scatter(x=weekly_fp["date"], y=weekly_fp["rsi_modified"],  mode="lines+markers", name="RSI-Mod",   line=dict(color="#44BBA4", width=2, dash="dot"), yaxis="y2"))
        fig.update_layout(
            title=f"{selected_athlete} — Weekly Trends",
            yaxis=dict(title="Wellness"),
            yaxis2=dict(title="Force Plate", overlaying="y", side="right"),
            height=320,
            hovermode="x unified",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Insufficient data for 7-day trends")

    # ------------------------------------------------------------------
    # BASKETBALL-SPECIFIC RISK CONTEXT
    # ------------------------------------------------------------------
    if HAVE_ENHANCED_MODULES:
        st.markdown("---")
        st.markdown("### Basketball-Specific Risk Context")
        context = st.radio(
            "Next activity:", ["Practice", "Competition"],
            horizontal=True, key=f"context_{athlete_id}",
        )
        injury_mechanism_insight_box(
            {
                "sleep_hours":   latest_wellness["sleep_hours"],
                "soreness":      latest_wellness["soreness"],
                "acwr":          latest_acwr,
                "cmj_zscore":    cmj_z,
                "rsi_zscore":    rsi_z,
                "cmj_height_cm": latest_cmj,
                "rsi_modified":  latest_rsi,
            },
            context.lower(),
        )

    with st.expander("Research References"):
        st.markdown(
            "- **Sleep:** <6.5 hrs → 1.7× injury risk (Milewski et al. 2014)\n"
            "- **ACWR:** >1.5 → 2.4× injury risk (Gabbett 2016)\n"
            "- **Soreness:** >7 requires monitoring (Hulin et al. 2016)\n"
            "- **CMJ/RSI:** Neuromuscular fatigue indicator — Gathercole et al. (2015)"
        )
