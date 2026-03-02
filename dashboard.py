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

from athlete_profile_tab import athlete_profile_tab, create_radar_chart  # create_radar_chart ok to keep

# ==============================================================================
# PAGE CONFIG + BRANDING (MUST COME BEFORE ANY OTHER st.* CALLS)
# ==============================================================================

HERE = Path(__file__).resolve().parent
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
    """Load data from SQLite database"""
    conn = sqlite3.connect("waims_demo.db")

    players = pd.read_sql_query("SELECT * FROM players", conn)
    wellness = pd.read_sql_query("SELECT * FROM wellness", conn)
    training_load = pd.read_sql_query("SELECT * FROM training_load", conn)
    force_plate = pd.read_sql_query("SELECT * FROM force_plate", conn)
    injuries = pd.read_sql_query("SELECT * FROM injuries", conn)
    acwr = pd.read_sql_query("SELECT * FROM acwr", conn)

    wellness["date"] = pd.to_datetime(wellness["date"])
    training_load["date"] = pd.to_datetime(training_load["date"])
    force_plate["date"] = pd.to_datetime(force_plate["date"])
    acwr["date"] = pd.to_datetime(acwr["date"])
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
# ENHANCED TAB 1: Battery Indicators
# ==============================================================================

def _html_oneliner(s: str) -> str:
    """Collapse whitespace so Streamlit doesn't interpret indented HTML as a Markdown code block."""
    return re.sub(r"\s+", " ", s).strip()


def create_mini_battery(value, show_label=True):
    """Create a compact battery indicator (HTML)"""
    if value >= 80:
        color = "#10b981"
        bg_color = "#d1fae5"
        emoji = "🟢"
    elif value >= 60:
        color = "#f59e0b"
        bg_color = "#fef3c7"
        emoji = "🟡"
    else:
        color = "#ef4444"
        bg_color = "#fee2e2"
        emoji = "🔴"

    battery_width = int(value)

    if show_label:
        html = f"""
        <div style="display:flex;align-items:center;gap:8px;">
          <div style="background:linear-gradient(to right,{bg_color} 0%,#f3f4f6 100%);
                      height:20px;width:100px;border-radius:10px;overflow:hidden;
                      position:relative;border:1px solid {color}40;">
            <div style="background:linear-gradient(135deg,{color} 0%,{color}dd 100%);
                        height:100%;width:{battery_width}%;border-radius:10px;
                        box-shadow:inset 0 1px 3px rgba(0,0,0,0.1);"></div>
          </div>
          <span style="font-size:14px;font-weight:700;min-width:35px;color:{color};">{value:.0f}%</span>
          <span style="font-size:16px;">{emoji}</span>
        </div>
        """
    else:
        html = f"""
        <div style="display:inline-flex;align-items:center;gap:4px;">
          <div style="background:{bg_color};height:16px;width:70px;border-radius:8px;
                      overflow:hidden;border:1px solid {color}60;">
            <div style="background:linear-gradient(135deg,{color} 0%,{color}dd 100%);
                        height:100%;width:{battery_width}%;border-radius:8px;"></div>
          </div>
          <span style="font-size:12px;font-weight:700;color:{color};">{value:.0f}</span>
        </div>
        """
    return _html_oneliner(html)


def create_summary_card(label, count, color, icon):
    html = f"""
    <div style="background:linear-gradient(135deg,{color}15 0%,{color}05 100%);
                border-left:4px solid {color};padding:20px;border-radius:10px;text-align:center;">
      <div style="font-size:48px;margin-bottom:8px;">{icon}</div>
      <div style="font-size:36px;font-weight:700;color:{color};margin-bottom:4px;">{count}</div>
      <div style="font-size:14px;color:#6b7280;font-weight:600;">{label}</div>
    </div>
    """
    return _html_oneliner(html)


def enhanced_todays_readiness_tab(wellness_df, players_df, end_date):
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

    today_wellness["readiness_score"] = (
        (today_wellness["sleep_hours"] / 8) * 30
        + ((10 - today_wellness["soreness"]) / 10) * 25
        + ((10 - today_wellness["stress"]) / 10) * 25
        + (today_wellness["mood"] / 10) * 20
    )

    def get_status(score):
        if score >= 80:
            return "🟢 Ready", "green"
        elif score >= 60:
            return "🟡 Monitor", "orange"
        else:
            return "🔴 At Risk", "red"

    today_wellness["status"], today_wellness["status_color"] = zip(
        *today_wellness["readiness_score"].apply(get_status)
    )

    today_wellness["sleep_pct"] = (today_wellness["sleep_hours"] / 8 * 100).clip(0, 100)
    today_wellness["physical_pct"] = ((10 - today_wellness["soreness"]) / 10 * 100)
    today_wellness["mental_pct"] = (today_wellness["mood"] / 10 * 100)
    today_wellness["stress_pct"] = ((10 - today_wellness["stress"]) / 10 * 100)

    today_wellness = today_wellness.sort_values("readiness_score")

    green_count = len(today_wellness[today_wellness["readiness_score"] >= 80])
    yellow_count = len(
        today_wellness[
            (today_wellness["readiness_score"] >= 60) & (today_wellness["readiness_score"] < 80)
        ]
    )
    red_count = len(today_wellness[today_wellness["readiness_score"] < 60])
    avg_sleep = today_wellness["sleep_hours"].mean()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(create_summary_card("Ready", green_count, "#10b981", "🟢"), unsafe_allow_html=True)
    with c2:
        st.markdown(create_summary_card("Monitor", yellow_count, "#f59e0b", "🟡"), unsafe_allow_html=True)
    with c3:
        st.markdown(create_summary_card("At Risk", red_count, "#ef4444", "🔴"), unsafe_allow_html=True)
    with c4:
        st.markdown(create_summary_card("Avg Sleep", f"{avg_sleep:.1f}h", "#3b82f6", "😴"), unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("Player Details")

    view_mode = st.radio(
        "View mode:",
        ["Compact (Battery View)", "Detailed (Full Metrics)"],
        horizontal=True,
        label_visibility="collapsed",
    )

    if view_mode == "Compact (Battery View)":
        st.markdown(
            textwrap.dedent(
                """
                <style>
                .player-row{display:flex;align-items:center;padding:12px;margin:8px 0;background:#fff;
                            border-radius:8px;border:1px solid #e5e7eb;transition:box-shadow .2s;}
                .player-row:hover{box-shadow:0 4px 6px rgba(0,0,0,.1);}
                .player-name{font-size:16px;font-weight:600;min-width:120px;}
                .player-position{font-size:12px;color:#6b7280;min-width:40px;}
                .player-status{font-size:14px;font-weight:600;min-width:90px;}
                .battery-container{display:flex;gap:12px;flex:1;}
                .battery-item{flex:1;text-align:center;}
                .battery-label{font-size:11px;color:#6b7280;margin-bottom:4px;}
                </style>
                """
            ).strip(),
            unsafe_allow_html=True,
        )

        for _, player in today_wellness.iterrows():
            if player["readiness_score"] >= 80:
                status_bg = "#d1fae5"
            elif player["readiness_score"] >= 60:
                status_bg = "#fef3c7"
            else:
                status_bg = "#fee2e2"

            row_html = f"""
            <div class="player-row">
              <div style="display:flex;align-items:center;gap:12px;min-width:280px;">
                <span class="player-name">{player['name']}</span>
                <span class="player-position">{player['position']}</span>
                <span class="player-status" style="background-color:{status_bg};padding:4px 12px;border-radius:12px;">
                  {player['status']}
                </span>
              </div>

              <div class="battery-container">
                <div class="battery-item">
                  <div class="battery-label">💤 Sleep</div>
                  {create_mini_battery(player['sleep_pct'], show_label=False)}
                </div>
                <div class="battery-item">
                  <div class="battery-label">💪 Physical</div>
                  {create_mini_battery(player['physical_pct'], show_label=False)}
                </div>
                <div class="battery-item">
                  <div class="battery-label">😊 Mental</div>
                  {create_mini_battery(player['mental_pct'], show_label=False)}
                </div>
                <div class="battery-item">
                  <div class="battery-label">😌 Stress</div>
                  {create_mini_battery(player['stress_pct'], show_label=False)}
                </div>
              </div>

              <div style="min-width:120px;text-align:center;">
                <div style="font-size:24px;font-weight:700;color:{player['status_color']};">{player['readiness_score']:.0f}</div>
                <div style="font-size:11px;color:#6b7280;">Overall Score</div>
              </div>
            </div>
            """
            st.markdown(_html_oneliner(row_html), unsafe_allow_html=True)

    else:
        for _, player in today_wellness.iterrows():
            if player["readiness_score"] >= 80:
                emoji = "🟢"
            elif player["readiness_score"] >= 60:
                emoji = "🟡"
            else:
                emoji = "🔴"

            with st.expander(
                f"{emoji} **{player['name']}** ({player['position']}) - Score: {player['readiness_score']:.0f}/100"
            ):
                colA, colB = st.columns([2, 1])

                with colA:
                    st.markdown("**Key Metrics (Battery View)**")
                    st.markdown(f"**💤 Sleep Quality:** {create_mini_battery(player['sleep_pct'])}", unsafe_allow_html=True)
                    st.caption(f"{player['sleep_hours']:.1f} hours")

                    st.markdown(f"**💪 Physical Readiness:** {create_mini_battery(player['physical_pct'])}", unsafe_allow_html=True)
                    st.caption(f"Soreness: {player['soreness']:.0f}/10")

                    st.markdown(f"**😊 Mental Wellness:** {create_mini_battery(player['mental_pct'])}", unsafe_allow_html=True)
                    st.caption(f"Mood: {player['mood']:.0f}/10")

                    st.markdown(f"**😌 Stress Management:** {create_mini_battery(player['stress_pct'])}", unsafe_allow_html=True)
                    st.caption(f"Stress: {player['stress']:.0f}/10")

                with colB:
                    st.markdown("**Raw Values**")
                    st.metric("Sleep", f"{player['sleep_hours']:.1f} hrs")
                    st.metric("Soreness", f"{player['soreness']:.0f}/10")
                    st.metric("Stress", f"{player['stress']:.0f}/10")
                    st.metric("Mood", f"{player['mood']:.0f}/10")
                    st.metric("Sleep Quality", f"{player['sleep_quality']:.0f}/10")

                st.markdown("---")
                flags = []
                if player["sleep_hours"] < 6.5:
                    flags.append("⚠️ **Poor Sleep** (<6.5 hrs)")
                if player["soreness"] >= 7:
                    flags.append("⚠️ **High Soreness** (≥7)")
                if player["stress"] >= 7:
                    flags.append("⚠️ **High Stress** (≥7)")

                if flags:
                    st.markdown("**⚠️ Alerts:**")
                    for flag in flags:
                        st.warning(flag)
                else:
                    st.success("✅ No alerts - athlete is in good standing")

    st.markdown("---")
    st.markdown("### 🎯 Quick Actions")

    qa1, qa2, qa3 = st.columns(3)

    with qa1:
        if st.button("📧 Email At-Risk Players", use_container_width=True):
            at_risk = today_wellness[today_wellness["readiness_score"] < 60]["name"].tolist()
            if at_risk:
                st.info(f"Would email: {', '.join(at_risk)}")
            else:
                st.success("No at-risk players today!")

    with qa2:
        csv = today_wellness[
            ["name", "position", "readiness_score", "status", "sleep_hours", "soreness", "stress", "mood"]
        ].to_csv(index=False)
        st.download_button(
            "📊 Export Today's Report (CSV)",
            data=csv,
            file_name=f"readiness_{end_date.strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with qa3:
        if st.button("🔔 Create Training Alert", use_container_width=True):
            st.info(f"Training modifications recommended for {red_count + yellow_count} players")

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def calculate_readiness_score(row):
    score = 0
    score += (row["sleep_hours"] / 8) * 30
    score += ((10 - row["soreness"]) / 10) * 25
    score += ((10 - row["stress"]) / 10) * 25
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
# SMART QUERY FUNCTIONS (TAB 7)
# ==============================================================================

def get_latest_date():
    return wellness["date"].max()

def query_poor_sleep(threshold=6.5):
    latest_date = get_latest_date()
    df = wellness[wellness["date"] == latest_date].copy()
    df = df[df["sleep_hours"] < threshold]
    df = df.merge(players[["player_id", "name"]], on="player_id")
    return df[["name", "sleep_hours", "soreness", "stress"]].sort_values("sleep_hours")

def query_high_risk():
    latest_date = get_latest_date()
    df = wellness[wellness["date"] == latest_date].copy()
    df = df.merge(players[["player_id", "name", "injury_history_count"]], on="player_id")
    df["high_risk"] = (df["sleep_hours"] < 6.5) | (df["soreness"] > 7) | (df["stress"] > 7)
    df = df[df["high_risk"]]
    return df[["name", "sleep_hours", "soreness", "stress", "injury_history_count"]]

def query_readiness_scores():
    latest_date = get_latest_date()
    df = wellness[wellness["date"] == latest_date].copy()
    df = df.merge(players[["player_id", "name"]], on="player_id")
    df["readiness_score"] = df.apply(calculate_readiness_score, axis=1)
    return df[["name", "sleep_hours", "soreness", "stress", "mood", "readiness_score"]].sort_values("readiness_score")

def query_position_comparison():
    latest_date = get_latest_date()
    df = wellness[wellness["date"] == latest_date].copy()
    keep = ["player_id", "name"] + (["position"] if "position" in players.columns else [])
    df = df.merge(players[keep], on="player_id")
    if "position" not in df.columns:
        df["position"] = "NA"

    comparison = (
        df.groupby("position")
        .agg({"sleep_hours": "mean", "soreness": "mean", "stress": "mean", "mood": "mean", "player_id": "count"})
        .round(1)
    )
    comparison.columns = ["avg_sleep", "avg_soreness", "avg_stress", "avg_mood", "count"]
    return comparison.reset_index()

def parse_query(user_input):
    user_input = user_input.lower().strip()

    if any(word in user_input for word in ["poor sleep", "bad sleep", "tired", "not sleeping"]):
        return "poor_sleep"
    elif any(word in user_input for word in ["high risk", "at risk", "injury risk"]):
        return "high_risk"
    elif any(word in user_input for word in ["readiness", "ready"]):
        return "readiness"
    elif "compare position" in user_input or "position comparison" in user_input:
        return "position_comparison"
    else:
        return "unknown"

def generate_smart_response(query_type):
    if query_type == "poor_sleep":
        df = query_poor_sleep()
        if len(df) == 0:
            return "✅ Great news! No players had poor sleep (<6.5 hrs) last night.", None

        st.subheader(f"⚠️ {len(df)} Players with Poor Sleep")
        st.dataframe(df, use_container_width=True)

        response = f"**{len(df)} players** had poor sleep:\n\n"
        for _, row in df.iterrows():
            response += f"- {row['name']}: {row['sleep_hours']:.1f} hours\n"
        response += "\n📚 Research: Sleep <6.5 hrs increases injury risk 1.7x (Milewski 2014)"
        return response, df

    elif query_type == "high_risk":
        df = query_high_risk()
        if len(df) == 0:
            return "✅ No players currently showing high injury risk indicators.", None

        st.subheader(f"🚨 {len(df)} Players at Elevated Risk")
        st.dataframe(df, use_container_width=True)

        response = f"**{len(df)} players** showing elevated risk:\n\n"
        for _, row in df.iterrows():
            response += f"- {row['name']}: Sleep {row['sleep_hours']:.1f}hrs, Soreness {row['soreness']}/10\n"
        return response, df

    elif query_type == "readiness":
        df = query_readiness_scores()
        st.subheader("📊 Readiness Scores")
        st.dataframe(df, use_container_width=True)

        green = len(df[df["readiness_score"] >= 80])
        yellow = len(df[(df["readiness_score"] >= 60) & (df["readiness_score"] < 80)])
        red = len(df[df["readiness_score"] < 60])

        response = f"🟢 Ready: {green} | 🟡 Monitor: {yellow} | 🔴 At Risk: {red}"
        return response, df

    elif query_type == "position_comparison":
        df = query_position_comparison()
        st.subheader("📊 Position Comparison")
        fig = px.bar(df, x="position", y=["avg_sleep", "avg_soreness"], barmode="group", title="Metrics by Position")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df, use_container_width=True)
        return "Position comparison complete", df

    else:
        return "❓ Try: 'poor sleep', 'high risk', 'readiness', or 'compare positions'", None

# ==============================================================================
# SIDEBAR
# ==============================================================================

if LOGO_PATH.exists():
    st.sidebar.image(str(LOGO_PATH), width=60)  # smaller than 100

st.sidebar.title("🏀 Roster & Dates")

st.sidebar.markdown(
    """
**How to use**
1. Pick a **date range**
2. Select **players** (or leave as **All**)
3. The Watchlist updates automatically
"""
)

if len(wellness) > 0:
    min_date = wellness["date"].min().date()
    max_date = wellness["date"].max().date()

    date_range = st.sidebar.date_input(
        "Date Range",
        value=(max_date - timedelta(days=7), max_date),
        min_value=min_date,
        max_value=max_date,
    )

    if len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date = end_date = max_date
else:
    start_date = end_date = datetime.today().date()

selected_players = st.sidebar.multiselect(
    "Select Players",
    options=players["name"].tolist(),
    default=players["name"].tolist()[:5],
)

st.sidebar.markdown("---")
st.sidebar.info(
    """
**Data Source:** SQLite Database  
**Records:** 1,637 data points  
**Period:** 50 days of monitoring
"""
)

# ==============================================================================
# MAIN DASHBOARD
# ==============================================================================

st.title("🏀 WAIMS READINESS WATCHLIST")
st.markdown(f"**Date:** {end_date.strftime('%B %d, %Y')}")

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(
    [
        "📊 Today's Readiness",
        "👤 Athlete Profiles",
        "📈 Trends",
        "💪 Jump Testing",
        "🚨 Availability & Injuries",
        "🤖 Forecast",
        "🔍 Ask the Watchlist",
    ]
)

# ==============================================================================
# TAB 1: TODAY'S READINESS (Enhanced only — no duplicate rendering)
# ==============================================================================

with tab1:
    enhanced_todays_readiness_tab(wellness, players, end_date)

# ==============================================================================
# TAB 2: Athlete Profiles
# ==============================================================================

with tab2:
    athlete_profile_tab(wellness, training_load, acwr, force_plate, players, injuries)

# ==============================================================================
# TAB 3: Trends
# ==============================================================================

with tab3:
    st.header("Wellness Trends")

    if selected_players:
        wellness_filtered = wellness[
            (wellness["date"] >= pd.to_datetime(start_date)) & (wellness["date"] <= pd.to_datetime(end_date))
        ].merge(players[["player_id", "name"]], on="player_id")

        wellness_filtered = wellness_filtered[wellness_filtered["name"].isin(selected_players)]

        if len(wellness_filtered) > 0:
            st.subheader("Sleep Hours Over Time")
            fig = px.line(
                wellness_filtered,
                x="date",
                y="sleep_hours",
                color="name",
                markers=True,
                title="Daily Sleep Hours",
            )
            fig.add_hline(y=7, line_dash="dash", line_color="orange", annotation_text="7 hrs (minimum)")
            fig.add_hline(y=8, line_dash="dash", line_color="green", annotation_text="8 hrs (target)")
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("Soreness Levels")
            fig = px.line(
                wellness_filtered,
                x="date",
                y="soreness",
                color="name",
                markers=True,
                title="Daily Soreness (0-10)",
            )
            fig.add_hline(y=7, line_dash="dash", line_color="red", annotation_text="High soreness threshold")
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("Training Load")
            load_filtered = training_load[
                (training_load["date"] >= pd.to_datetime(start_date)) & (training_load["date"] <= pd.to_datetime(end_date))
            ].merge(players[["player_id", "name"]], on="player_id")

            load_filtered = load_filtered[load_filtered["name"].isin(selected_players)]

            if len(load_filtered) > 0:
                fig = px.bar(
                    load_filtered,
                    x="date",
                    y="practice_minutes",
                    color="name",
                    title="Practice Minutes by Day",
                    barmode="group",
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data for selected players and date range")
    else:
        st.info("Please select at least one player from the sidebar")

# ==============================================================================
# TAB 4: FORCE PLATE
# ==============================================================================

with tab4:
    st.header("Force Plate Testing")

    if selected_players and len(force_plate) > 0:
        fp_filtered = force_plate[
            (force_plate["date"] >= pd.to_datetime(start_date)) & (force_plate["date"] <= pd.to_datetime(end_date))
        ].merge(players[["player_id", "name"]], on="player_id")

        fp_filtered = fp_filtered[fp_filtered["name"].isin(selected_players)]

        if len(fp_filtered) > 0:
            st.subheader("CMJ Jump Height Trends")
            fig = px.line(fp_filtered, x="date", y="cmj_height_cm", color="name", markers=True, title="CMJ Height (cm)")
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("Reactive Strength Index (Modified)")
            fig = px.line(fp_filtered, x="date", y="rsi_modified", color="name", markers=True, title="RSI-Modified")
            fig.add_hline(y=0.35, line_dash="dash", line_color="green", annotation_text="Target (0.35+)")
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("Latest Test Results")
            latest = fp_filtered.sort_values("date", ascending=False).groupby("name").first().reset_index()
            st.dataframe(latest[["name", "date", "cmj_height_cm", "rsi_modified"]], hide_index=True, use_container_width=True)
        else:
            st.info("No force plate data for selected players and date range")
    else:
        st.info("No force plate data available or no players selected")

# ==============================================================================
# TAB 5: INJURIES
# ==============================================================================

with tab5:
    st.header("Injury Tracking")

    if len(injuries) > 0:
        st.subheader("Injury Log")

        injuries_display = injuries.merge(players[["player_id", "name"]], on="player_id")

        for _, inj in injuries_display.iterrows():
            with st.expander(
                f"🚨 **{inj['name']}** - {inj['injury_type']} ({inj['injury_date'].strftime('%Y-%m-%d')})"
            ):
                c1, c2 = st.columns(2)
                c1.metric("Injury Date", inj["injury_date"].strftime("%B %d, %Y"))
                c2.metric("Days Missed", inj["days_missed"])

                st.markdown("**Wellness 7 Days Before Injury:**")

                injury_date = inj["injury_date"]
                week_before = injury_date - timedelta(days=7)

                pre_injury = wellness[
                    (wellness["player_id"] == inj["player_id"])
                    & (wellness["date"] >= week_before)
                    & (wellness["date"] <= injury_date)
                ].sort_values("date")

                if len(pre_injury) > 0:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=pre_injury["date"], y=pre_injury["sleep_hours"], name="Sleep Hours", mode="lines+markers"))
                    fig.add_trace(
                        go.Scatter(
                            x=pre_injury["date"],
                            y=pre_injury["soreness"],
                            name="Soreness",
                            mode="lines+markers",
                            yaxis="y2",
                        )
                    )
                    fig.update_layout(
                        yaxis=dict(title="Sleep Hours"),
                        yaxis2=dict(title="Soreness (0-10)", overlaying="y", side="right"),
                        height=300,
                    )
                    st.plotly_chart(fig, use_container_width=True)
    else:
        st.success("✅ No injuries recorded")

# ==============================================================================
# TAB 6: FORECAST
# ==============================================================================

with tab6:
    st.header("🔮 Readiness Forecasts")
    st.caption("Quick look at who may need attention soon, based on recent trends.")

    import os
    import pickle

    model_path = "models/injury_risk_model.pkl"
    model_exists = os.path.exists(model_path)

    if len(wellness) > 0 and len(training_load) > 0:
        st.subheader("Today’s Watchouts")

        recent_data = wellness[wellness["date"] == wellness["date"].max()].copy()
        recent_data = recent_data.merge(
            training_load[training_load["date"] == training_load["date"].max()],
            on=["player_id", "date"],
            how="left",
        )
        recent_data = recent_data.merge(
            players[["player_id", "name", "age", "injury_history_count"]],
            on="player_id",
            how="left",
        )

        if len(recent_data) > 0:
            recent_data["risk_score"] = (
                (1 - recent_data["sleep_hours"] / 8) * 30
                + (recent_data["soreness"] / 10) * 30
                + (recent_data["stress"] / 10) * 20
                + (recent_data["injury_history_count"].fillna(0) / 5) * 20
            ).round(0)

            recent_data["risk_level"] = recent_data["risk_score"].apply(
                lambda x: "🔴 High" if x > 60 else ("🟡 Moderate" if x > 40 else "🟢 Low")
            )

            recent_data = recent_data.sort_values("risk_score", ascending=False)

            st.markdown("**Athletes to check in with:**")
            for _, player in recent_data.head(5).iterrows():
                with st.expander(
                    f"{player['risk_level']}  **{player['name']}**  (Score: {player['risk_score']:.0f}/100)"
                ):
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Sleep", f"{player['sleep_hours']:.1f} hrs")
                    c2.metric("Soreness", f"{player['soreness']}/10")
                    c3.metric("Stress", f"{player['stress']}/10")

                    st.markdown("**Why they’re here:**")
                    factors = []
                    if player["sleep_hours"] < 7:
                        factors.append("Low sleep")
                    if player["soreness"] >= 6:
                        factors.append("High soreness")
                    if player.get("injury_history_count", 0) > 2:
                        factors.append("Higher injury history")

                    if factors:
                        st.write("• " + "\n• ".join(factors))
                    else:
                        st.write("Trend-based watchout (no single red flag).")
        else:
            st.info("No data available for the most recent day.")
    else:
        st.info("Add wellness + training load data to show forecast watchouts.")

    st.markdown("---")

    with st.expander("Model details (staff)"):
        if model_exists:
            st.success("✓ Forecast model available")
            try:
                with open(model_path, "rb") as f:
                    model = pickle.load(f)

                c1, c2, c3 = st.columns(3)
                c1.metric("Algorithm", "RandomForest")
                c2.metric("Status", "Ready")
                c3.metric("Model file", "injury_risk_model.pkl")

                st.info(
                    "**Readiness Watchouts Model**  \n"
                    "Trained on historical patterns to flag potential watchouts.  \n\n"
                    "Uses features: sleep, soreness, stress, training load, ACWR, force plate metrics."
                )
            except Exception as e:
                st.error(f"Error loading model: {e}")
                st.info("Run: python train_models.py to train the model")
        else:
            st.warning("⚠️ Forecast model not yet trained")
            st.markdown(
                "**To train the model:**\n"
                "1. Open terminal in the waims-python folder  \n"
                "2. Run: `python train_models.py`  \n"
                "3. Refresh this page"
            )
            st.code("python train_models.py", language="bash")

# ==============================================================================
# TAB 7: Ask the Watchlist
# ==============================================================================

with tab7:
    st.header("🔍 Ask the Watchlist")
    st.markdown("Ask questions about your players - **instant answers!**")

    if "query_to_run" not in st.session_state:
        st.session_state.query_to_run = ""

    c1, c2 = st.columns([2, 1])

    with c1:
        st.markdown(
            """
**💡 How to use**
Type naturally, for example:
- `poor sleep`
- `high risk`
- `readiness`
- `compare positions`
"""
        )

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
            st.info(f"🔍 **Understood as:** {query_type.replace('_', ' ').title()}")

            response, data = generate_smart_response(query_type)
            st.markdown(response)

            if data is not None and len(data) > 0:
                csv = data.to_csv(index=False)
                st.download_button(
                    "📥 Download Results",
                    data=csv,
                    file_name=f"query_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                )

    with c2:
        st.markdown("### ⚡ Quick Buttons")

        if st.button("🌙 Poor Sleep", use_container_width=True):
            st.session_state.query_to_run = "poor sleep"
            st.rerun()

        if st.button("🚨 High Risk", use_container_width=True):
            st.session_state.query_to_run = "high risk"
            st.rerun()

        if st.button("✅ Readiness", use_container_width=True):
            st.session_state.query_to_run = "readiness"
            st.rerun()

# ==============================================================================
# FOOTER
# ==============================================================================

st.markdown("---")
st.markdown(
    """
<div style='text-align: center; color: #666;'>
    <p><strong>WAIMS</strong> - Athlete Monitoring System | Built with Python, Streamlit, SQLite</p>
    <p>Demo System - 1,637 integrated data points across 50 days</p>
</div>
""",
    unsafe_allow_html=True,
)
