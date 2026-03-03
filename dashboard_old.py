"""
WAIMS Readiness Watchlist
Streamlit web application for athlete monitoring data visualization

Usage:
    streamlit run dashboard.py
"""

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
    conn         = sqlite3.connect("waims_demo.db")
    players      = pd.read_sql_query("SELECT * FROM players",       conn)
    wellness     = pd.read_sql_query("SELECT * FROM wellness",      conn)
    training_load= pd.read_sql_query("SELECT * FROM training_load", conn)
    force_plate  = pd.read_sql_query("SELECT * FROM force_plate",   conn)
    injuries     = pd.read_sql_query("SELECT * FROM injuries",      conn)
    acwr         = pd.read_sql_query("SELECT * FROM acwr",          conn)

    wellness["date"]      = pd.to_datetime(wellness["date"])
    training_load["date"] = pd.to_datetime(training_load["date"])
    force_plate["date"]   = pd.to_datetime(force_plate["date"])
    acwr["date"]          = pd.to_datetime(acwr["date"])
    if len(injuries) > 0:
        injuries["injury_date"] = pd.to_datetime(injuries["injury_date"])

    conn.close()
    return players, wellness, training_load, force_plate, injuries, acwr


try:
    players, wellness, training_load, force_plate, injuries, acwr = load_data()
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
        # Absolute fallback
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

def enhanced_todays_readiness_tab(wellness_df, players_df, fp_df, end_date):
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

    def get_fp_row(pid):
        row = latest_fp[latest_fp["player_id"] == pid]
        return row.iloc[0].to_dict() if len(row) > 0 else None

    # Classify every player using full z-score model (wellness + force plate)
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

    # Summary cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(create_summary_card("Ready",     green_count,         "#10b981", "🟢"), unsafe_allow_html=True)
    with c2:
        st.markdown(create_summary_card("Monitor",   yellow_count,        "#f59e0b", "🟡"), unsafe_allow_html=True)
    with c3:
        st.markdown(create_summary_card("At Risk",   red_count,           "#ef4444", "🔴"), unsafe_allow_html=True)
    with c4:
        st.markdown(create_summary_card("Avg Sleep", f"{avg_sleep:.1f}h", "#3b82f6", sleep_icon), unsafe_allow_html=True)

    st.caption(f"Force plate data available for {fp_coverage}/{len(today_wellness)} athletes today. CMJ/RSI deviations weighted higher than subjective wellness.")
    st.markdown("---")

    # Also compute legacy readiness score for display purposes
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
                bg = "#d1fae5" if player["readiness_score"] >= 80 else ("#fef3c7" if player["readiness_score"] >= 60 else "#fee2e2")
                fp_row = get_fp_row(player["player_id"])
                cmj_str = f"{fp_row['cmj_height_cm']:.1f} cm" if fp_row else "—"
                rsi_str = f"{fp_row['rsi_modified']:.2f}"     if fp_row else "—"
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
                    f'</div>'
                    f'</div>'
                )
                st.markdown(_html_oneliner(row_html), unsafe_allow_html=True)

    else:
        for _, player in today_wellness.iterrows():
            emoji   = "🟢" if player["readiness_score"] >= 80 else ("🟡" if player["readiness_score"] >= 60 else "🔴")
            fp_row  = get_fp_row(player["player_id"])
            with st.expander(f"{emoji} **{player['name']}** ({player['position']}) — Score: {player['readiness_score']:.0f}/100"):
                colA, colB = st.columns([2, 1])
                with colA:
                    st.markdown("**Key Metrics**")
                    st.markdown(f"**Sleep:** {create_mini_battery(player['sleep_pct'])}", unsafe_allow_html=True)
                    st.caption(f"{player['sleep_hours']:.1f} hours")
                    st.markdown(f"**Physical:** {create_mini_battery(player['physical_pct'])}", unsafe_allow_html=True)
                    st.caption(f"Soreness: {player['soreness']:.0f}/10")
                    st.markdown(f"**Mental:** {create_mini_battery(player['mental_pct'])}", unsafe_allow_html=True)
                    st.caption(f"Mood: {player['mood']:.0f}/10")
                    st.markdown(f"**Stress:** {create_mini_battery(player['stress_pct'])}", unsafe_allow_html=True)
                    st.caption(f"Stress: {player['stress']:.0f}/10")
                with colB:
                    st.markdown("**Raw Values**")
                    st.metric("Sleep",         f"{player['sleep_hours']:.1f} hrs")
                    st.metric("Soreness",      f"{player['soreness']:.0f}/10")
                    st.metric("Stress",        f"{player['stress']:.0f}/10")
                    st.metric("Mood",          f"{player['mood']:.0f}/10")
                    if fp_row:
                        st.metric("CMJ Height",  f"{fp_row['cmj_height_cm']:.1f} cm")
                        st.metric("RSI-Modified",f"{fp_row['rsi_modified']:.2f}")
                    else:
                        st.caption("No force plate data today")

                st.markdown("---")
                st.markdown("**Flags:**")
                for note in player["flag_notes"]:
                    st.write(f"• {note}")

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
# SMART QUERY FUNCTIONS (TAB 7)
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
    comparison = df.groupby("position").agg({"sleep_hours": "mean", "soreness": "mean", "stress": "mean", "mood": "mean", "player_id": "count"}).round(1)
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
    date_range = st.sidebar.date_input("Date Range", value=(max_date - timedelta(days=7), max_date), min_value=min_date, max_value=max_date)
    start_date, end_date = date_range if len(date_range) == 2 else (max_date, max_date)
else:
    start_date = end_date = datetime.today().date()

selected_players = st.sidebar.multiselect("Select Players", options=players["name"].tolist(), default=players["name"].tolist()[:5])
st.sidebar.markdown("---")
st.sidebar.info("**Data Source:** SQLite Database\n**Records:** 1,637 data points\n**Period:** 50 days of monitoring")

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

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📊 Today's Readiness",
    "👤 Athlete Profiles",
    "📈 Trends",
    "💪 Jump Testing",
    "🚨 Availability & Injuries",
    "🤖 Forecast",
    "🔍 Ask the Watchlist",
])

# ==============================================================================
# TAB 1
# ==============================================================================

with tab1:
    enhanced_todays_readiness_tab(wellness, players, force_plate, end_date)

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
            trend_df["sleep_roll"]    = trend_df.groupby("player_id")["sleep_hours"].transform(lambda x: x.rolling(7, min_periods=2).mean())
            trend_df["soreness_roll"] = trend_df.groupby("player_id")["soreness"].transform(lambda x: x.rolling(7, min_periods=2).mean())
            trend_df["mood_roll"]     = trend_df.groupby("player_id")["mood"].transform(lambda x: x.rolling(7, min_periods=2).mean())
            trend_df["stress_roll"]   = trend_df.groupby("player_id")["stress"].transform(lambda x: x.rolling(7, min_periods=2).mean())

            COLORS = ["#2E86AB", "#A23B72", "#F18F01", "#C73E1D", "#3B1F2B", "#44BBA4"]

            def dual_trace_chart(df, raw_col, roll_col, title, yrange=None):
                fig = go.Figure()
                for i, name in enumerate(selected):
                    c   = COLORS[i % len(COLORS)]
                    sub = df[df["name"] == name]
                    fig.add_trace(go.Scatter(x=sub["date"], y=sub[raw_col],  mode="lines+markers", name=name, line=dict(color=c, width=1, dash="dot"), marker=dict(size=4), opacity=0.4, legendgroup=name, showlegend=False))
                    fig.add_trace(go.Scatter(x=sub["date"], y=sub[roll_col], mode="lines",          name=name, line=dict(color=c, width=3),                                               legendgroup=name, showlegend=True))
                fig.update_layout(title=title, height=260, margin=dict(l=10, r=10, t=40, b=20), hovermode="x unified", yaxis=dict(range=yrange) if yrange else {}, legend=dict(orientation="h", y=-0.2))
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
        today_fp    = force_plate[force_plate["date"] == latest_date].merge(players[["player_id", "name", "position"]], on="player_id", how="left")

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
            trend_df = force_plate[(force_plate["player_id"].isin(sel_ids)) & (force_plate["date"] >= week_ago)].merge(players[["player_id", "name"]], on="player_id")
            if len(trend_df) > 0:
                fig = px.line(trend_df, x="date", y="cmj_height_cm", color="name", markers=True, title="CMJ Height (cm) — Personal Trend", labels={"cmj_height_cm": "CMJ (cm)", "name": "Athlete"})
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No force plate data available.")

# ==============================================================================
# TAB 5: INJURIES
# ==============================================================================

with tab5:
    st.header("Injury Tracking")
    if len(injuries) > 0:
        injuries_display = injuries.merge(players[["player_id", "name"]], on="player_id")
        for _, inj in injuries_display.iterrows():
            with st.expander(f"🚨 **{inj['name']}** - {inj['injury_type']} ({inj['injury_date'].strftime('%Y-%m-%d')})"):
                c1, c2 = st.columns(2)
                c1.metric("Injury Date", inj["injury_date"].strftime("%B %d, %Y"))
                c2.metric("Days Missed", inj["days_missed"])
                st.markdown("**Wellness 7 Days Before Injury:**")
                pre_injury = wellness[
                    (wellness["player_id"] == inj["player_id"]) &
                    (wellness["date"] >= inj["injury_date"] - timedelta(days=7)) &
                    (wellness["date"] <= inj["injury_date"])
                ].sort_values("date")
                if len(pre_injury) > 0:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=pre_injury["date"], y=pre_injury["sleep_hours"], name="Sleep Hours",  mode="lines+markers"))
                    fig.add_trace(go.Scatter(x=pre_injury["date"], y=pre_injury["soreness"],    name="Soreness",     mode="lines+markers", yaxis="y2"))
                    fig.update_layout(yaxis=dict(title="Sleep Hours"), yaxis2=dict(title="Soreness (0-10)", overlaying="y", side="right"), height=300)
                    st.plotly_chart(fig, use_container_width=True)
    else:
        st.success("No injuries recorded")

# ==============================================================================
# TAB 6: FORECAST
# ==============================================================================

with tab6:
    st.header("Readiness Forecasts")
    st.caption("Flags players showing unusual deviation from their personal baseline — wellness + force plate combined.")

    if len(wellness) > 0:
        latest_date = wellness["date"].max()
        ref_date    = pd.to_datetime(latest_date)
        latest_fp   = force_plate[force_plate["date"] == latest_date]

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
                risk_score = min(100, flags * 15)
                risk_emoji = "🔴 High" if risk_score >= 60 else ("🟡 Moderate" if risk_score >= 20 else "🟢 Low")
                return pd.Series({"risk_score": risk_score, "flag_notes": notes, "risk_emoji": risk_emoji})

            recent_data[["risk_score", "flag_notes", "risk_emoji"]] = recent_data.apply(full_risk, axis=1)
            recent_data = recent_data.sort_values("risk_score", ascending=False)

            fp_coverage = len(latest_fp["player_id"].unique())
            st.caption(f"Force plate data for {fp_coverage}/{len(recent_data)} athletes. CMJ/RSI deviations weighted higher than subjective metrics.")
            st.markdown("**Athletes to check in with:**")

            for _, player in recent_data.head(6).iterrows():
                fp_row = get_fp_row_fc(player["player_id"])
                with st.expander(f"{player['risk_emoji']}  **{player['name']}**  — Risk Score: {player['risk_score']:.0f}/100"):
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
                    st.markdown("**Why she's here:**")
                    for note in player["flag_notes"]:
                        st.write(f"• {note}")
        else:
            st.info("No data available for the most recent day.")
    else:
        st.info("Add wellness + training load data to show forecast watchouts.")

    st.markdown("---")
    st.caption("Risk scoring: hard safety floors (sleep <6.5 hrs, soreness/stress >7) always flag. Personal deviations >1.5σ from 30-day baseline add flags. CMJ/RSI drops weighted ×1.5 vs subjective metrics. Gathercole et al. (2015) · Milewski et al. (2014) · Gabbett (2016)")

    with st.expander("Model details (staff)"):
        import os, pickle
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
                st.info("Features: sleep, soreness, stress, training load, ACWR, CMJ, RSI + z-score deviations from personal baseline.")
            except Exception as e:
                st.error(f"Error loading model: {e}")
        else:
            st.warning("Forecast model not yet trained")
            st.code("python train_models.py", language="bash")

# ==============================================================================
# TAB 7: ASK THE WATCHLIST
# ==============================================================================

with tab7:
    st.header("🔍 Ask the Watchlist")
    st.markdown("Ask questions about your players — instant answers.")

    if "query_to_run" not in st.session_state:
        st.session_state.query_to_run = ""

    c1, c2 = st.columns([2, 1])
    with c1:
        st.markdown("**How to use:** Type `poor sleep`, `high risk`, `readiness`, or `compare positions`")
        user_query = st.text_input("Ask a question", placeholder="e.g., 'poor sleep' or 'high risk players'", key="smart_query_input", label_visibility="collapsed")
        if st.session_state.query_to_run:
            user_query = st.session_state.query_to_run
            st.session_state.query_to_run = ""
        if user_query:
            query_type = parse_query(user_query)
            st.info(f"Understood as: {query_type.replace('_', ' ').title()}")
            response, data = generate_smart_response(query_type)
            st.markdown(response)
            if data is not None and len(data) > 0:
                st.download_button("Download Results", data=data.to_csv(index=False), file_name=f"query_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", mime="text/csv")
    with c2:
        st.markdown("### Quick Buttons")
        if st.button("Poor Sleep",  use_container_width=True): st.session_state.query_to_run = "poor sleep";  st.rerun()
        if st.button("High Risk",   use_container_width=True): st.session_state.query_to_run = "high risk";   st.rerun()
        if st.button("Readiness",   use_container_width=True): st.session_state.query_to_run = "readiness";   st.rerun()

# ==============================================================================
# FOOTER
# ==============================================================================

st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#666;'>"
    "<p><strong>WAIMS</strong> — Athlete Monitoring System | Python · Streamlit · SQLite</p>"
    "<p>Demo System — 1,637 integrated data points across 50 days</p>"
    "</div>",
    unsafe_allow_html=True,
)
