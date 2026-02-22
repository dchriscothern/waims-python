"""
WAIMS Python - Interactive Dashboard
Streamlit web application for athlete monitoring data visualization

Usage:
    streamlit run dashboard.py
"""

import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ==============================================================================
# PAGE CONFIG
# ==============================================================================

st.set_page_config(
    page_title="WAIMS - Athlete Monitoring",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# LOAD DATA
# ==============================================================================

@st.cache_data
def load_data():
    """Load data from SQLite database"""
    conn = sqlite3.connect('waims_demo.db')
    
    # Load all tables
    players = pd.read_sql_query("SELECT * FROM players", conn)
    wellness = pd.read_sql_query("SELECT * FROM wellness", conn)
    training_load = pd.read_sql_query("SELECT * FROM training_load", conn)
    force_plate = pd.read_sql_query("SELECT * FROM force_plate", conn)
    injuries = pd.read_sql_query("SELECT * FROM injuries", conn)
    
    # Convert dates
    wellness['date'] = pd.to_datetime(wellness['date'])
    training_load['date'] = pd.to_datetime(training_load['date'])
    force_plate['date'] = pd.to_datetime(force_plate['date'])
    if len(injuries) > 0:
        injuries['injury_date'] = pd.to_datetime(injuries['injury_date'])
    
    conn.close()
    
    return players, wellness, training_load, force_plate, injuries

# Load data
try:
    players, wellness, training_load, force_plate, injuries = load_data()
except Exception as e:
    st.error(f"Error loading database: {e}")
    st.info("Make sure waims_demo.db is in the current directory")
    st.stop()

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def calculate_readiness_score(row):
    """Calculate simple readiness score (0-100)"""
    score = 0
    score += (row['sleep_hours'] / 8) * 30  # 30 points for sleep
    score += ((10 - row['soreness']) / 10) * 25  # 25 points for low soreness
    score += ((10 - row['stress']) / 10) * 25  # 25 points for low stress
    score += (row['mood'] / 10) * 20  # 20 points for mood
    return round(score, 0)

def get_status_color(score):
    """Get color based on readiness score"""
    if score >= 80:
        return "🟢", "green"
    elif score >= 60:
        return "🟡", "orange"
    else:
        return "🔴", "red"

# ==============================================================================
# SIDEBAR
# ==============================================================================

st.sidebar.title("🏀 WAIMS Dashboard")
st.sidebar.markdown("**Athlete Monitoring System**")
st.sidebar.markdown("---")

# Date range filter
if len(wellness) > 0:
    min_date = wellness['date'].min().date()
    max_date = wellness['date'].max().date()
    
    date_range = st.sidebar.date_input(
        "Date Range",
        value=(max_date - timedelta(days=7), max_date),
        min_value=min_date,
        max_value=max_date
    )
    
    if len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date = end_date = max_date

# Player filter
selected_players = st.sidebar.multiselect(
    "Select Players",
    options=players['name'].tolist(),
    default=players['name'].tolist()[:5]  # Default to first 5
)

st.sidebar.markdown("---")
st.sidebar.info("""
**Data Source:** SQLite Database  
**Records:** 1,637 data points  
**Period:** 50 days of monitoring
""")

# ==============================================================================
# MAIN DASHBOARD
# ==============================================================================

# Title
st.title("🏀 WAIMS Athlete Monitoring Dashboard")
st.markdown(f"**Date:** {end_date.strftime('%B %d, %Y')}")

# ==============================================================================
# TAB 1: TODAY'S READINESS
# ==============================================================================

tab1, tab2, tab3, tab4 = st.tabs(["📊 Today's Readiness", "📈 Trends", "💪 Force Plate", "🚨 Injuries"])

with tab1:
    st.header("Today's Readiness Status")
    
    # Get today's data
    today_wellness = wellness[wellness['date'] == pd.to_datetime(end_date)]
    today_wellness = today_wellness.merge(players[['player_id', 'name']], on='player_id')
    
    if len(today_wellness) > 0:
        # Calculate readiness scores
        today_wellness['readiness_score'] = today_wellness.apply(calculate_readiness_score, axis=1)
        today_wellness = today_wellness.sort_values('readiness_score')
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        green_count = len(today_wellness[today_wellness['readiness_score'] >= 80])
        yellow_count = len(today_wellness[(today_wellness['readiness_score'] >= 60) & 
                                          (today_wellness['readiness_score'] < 80)])
        red_count = len(today_wellness[today_wellness['readiness_score'] < 60])
        avg_sleep = today_wellness['sleep_hours'].mean()
        
        col1.metric("🟢 Ready", green_count, help="Score ≥ 80")
        col2.metric("🟡 Monitor", yellow_count, help="Score 60-79")
        col3.metric("🔴 At Risk", red_count, help="Score < 60")
        col4.metric("😴 Avg Sleep", f"{avg_sleep:.1f} hrs")
        
        st.markdown("---")
        
        # Player table
        st.subheader("Player Details")
        
        for _, player in today_wellness.iterrows():
            emoji, color = get_status_color(player['readiness_score'])
            
            with st.expander(f"{emoji} **{player['name']}** - Score: {player['readiness_score']}/100"):
                col1, col2, col3 = st.columns(3)
                
                col1.metric("Sleep", f"{player['sleep_hours']:.1f} hrs")
                col1.metric("Soreness", f"{player['soreness']}/10")
                
                col2.metric("Stress", f"{player['stress']}/10")
                col2.metric("Mood", f"{player['mood']}/10")
                
                col3.metric("Sleep Quality", f"{player['sleep_quality']}/10")
                
                # Flags
                flags = []
                if player['sleep_hours'] < 6.5:
                    flags.append("⚠️ Poor Sleep")
                if player['soreness'] >= 7:
                    flags.append("⚠️ High Soreness")
                if player['stress'] >= 7:
                    flags.append("⚠️ High Stress")
                
                if flags:
                    st.warning(" | ".join(flags))
    else:
        st.info("No data available for selected date")

# ==============================================================================
# TAB 2: TRENDS
# ==============================================================================

with tab2:
    st.header("Wellness Trends")
    
    if selected_players:
        # Filter data
        wellness_filtered = wellness[
            (wellness['date'] >= pd.to_datetime(start_date)) &
            (wellness['date'] <= pd.to_datetime(end_date))
        ].merge(players[['player_id', 'name']], on='player_id')
        
        wellness_filtered = wellness_filtered[wellness_filtered['name'].isin(selected_players)]
        
        if len(wellness_filtered) > 0:
            # Sleep trends
            st.subheader("Sleep Hours Over Time")
            fig = px.line(
                wellness_filtered,
                x='date',
                y='sleep_hours',
                color='name',
                markers=True,
                title="Daily Sleep Hours"
            )
            fig.add_hline(y=7, line_dash="dash", line_color="orange", 
                         annotation_text="7 hrs (minimum)")
            fig.add_hline(y=8, line_dash="dash", line_color="green", 
                         annotation_text="8 hrs (target)")
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
            
            # Soreness trends
            st.subheader("Soreness Levels")
            fig = px.line(
                wellness_filtered,
                x='date',
                y='soreness',
                color='name',
                markers=True,
                title="Daily Soreness (0-10)"
            )
            fig.add_hline(y=7, line_dash="dash", line_color="red", 
                         annotation_text="High soreness threshold")
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
            
            # Training load
            st.subheader("Training Load")
            
            load_filtered = training_load[
                (training_load['date'] >= pd.to_datetime(start_date)) &
                (training_load['date'] <= pd.to_datetime(end_date))
            ].merge(players[['player_id', 'name']], on='player_id')
            
            load_filtered = load_filtered[load_filtered['name'].isin(selected_players)]
            
            if len(load_filtered) > 0:
                fig = px.bar(
                    load_filtered,
                    x='date',
                    y='practice_minutes',
                    color='name',
                    title="Practice Minutes by Day",
                    barmode='group'
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data for selected players and date range")
    else:
        st.info("Please select at least one player from the sidebar")

# ==============================================================================
# TAB 3: FORCE PLATE
# ==============================================================================

with tab3:
    st.header("Force Plate Testing")
    
    if selected_players and len(force_plate) > 0:
        fp_filtered = force_plate[
            (force_plate['date'] >= pd.to_datetime(start_date)) &
            (force_plate['date'] <= pd.to_datetime(end_date))
        ].merge(players[['player_id', 'name']], on='player_id')
        
        fp_filtered = fp_filtered[fp_filtered['name'].isin(selected_players)]
        
        if len(fp_filtered) > 0:
            # Jump height trends
            st.subheader("CMJ Jump Height Trends")
            fig = px.line(
                fp_filtered,
                x='date',
                y='cmj_height_cm',
                color='name',
                markers=True,
                title="Counter Movement Jump Height (cm)"
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
            
            # RSI trends
            st.subheader("Reactive Strength Index (Modified)")
            fig = px.line(
                fp_filtered,
                x='date',
                y='rsi_modified',
                color='name',
                markers=True,
                title="RSI-Modified"
            )
            fig.add_hline(y=0.35, line_dash="dash", line_color="green", 
                         annotation_text="Target (0.35+)")
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
            
            # Latest results table
            st.subheader("Latest Test Results")
            latest = fp_filtered.sort_values('date', ascending=False).groupby('name').first().reset_index()
            st.dataframe(
                latest[['name', 'date', 'cmj_height_cm', 'rsi_modified']],
                hide_index=True,
                use_container_width=True
            )
        else:
            st.info("No force plate data for selected players and date range")
    else:
        st.info("No force plate data available or no players selected")

# ==============================================================================
# TAB 4: INJURIES
# ==============================================================================

with tab4:
    st.header("Injury Tracking")
    
    if len(injuries) > 0:
        st.subheader("Injury Log")
        
        injuries_display = injuries.merge(players[['player_id', 'name']], on='player_id')
        
        for _, inj in injuries_display.iterrows():
            with st.expander(f"🚨 **{inj['name']}** - {inj['injury_type']} ({inj['injury_date'].strftime('%Y-%m-%d')})"):
                col1, col2 = st.columns(2)
                col1.metric("Injury Date", inj['injury_date'].strftime('%B %d, %Y'))
                col2.metric("Days Missed", inj['days_missed'])
                
                # Show wellness leading up to injury
                st.markdown("**Wellness 7 Days Before Injury:**")
                
                injury_date = inj['injury_date']
                week_before = injury_date - timedelta(days=7)
                
                pre_injury = wellness[
                    (wellness['player_id'] == inj['player_id']) &
                    (wellness['date'] >= week_before) &
                    (wellness['date'] <= injury_date)
                ].sort_values('date')
                
                if len(pre_injury) > 0:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=pre_injury['date'],
                        y=pre_injury['sleep_hours'],
                        name='Sleep Hours',
                        mode='lines+markers'
                    ))
                    fig.add_trace(go.Scatter(
                        x=pre_injury['date'],
                        y=pre_injury['soreness'],
                        name='Soreness',
                        mode='lines+markers',
                        yaxis='y2'
                    ))
                    fig.update_layout(
                        yaxis=dict(title='Sleep Hours'),
                        yaxis2=dict(title='Soreness (0-10)', overlaying='y', side='right'),
                        height=300
                    )
                    st.plotly_chart(fig, use_container_width=True)
    else:
        st.success("✅ No injuries recorded")

# ==============================================================================
# FOOTER
# ==============================================================================

st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p><strong>WAIMS</strong> - Athlete Monitoring System | Built with Python, Streamlit, SQLite</p>
    <p>Demo System - 1,637 integrated data points across 50 days</p>
</div>
""", unsafe_allow_html=True)
