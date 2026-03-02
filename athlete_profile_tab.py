"""
Enhanced Athlete Profile Tab with Gauge Charts and Visual Indicators
Inspired by Apollo.io dashboard style
"""

import os
from datetime import datetime, timedelta

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# ==============================================================================
# VISUAL GAUGE HELPERS
# ==============================================================================

def create_gauge_chart(value, title, min_val=0, max_val=100, thresholds=[40, 70]):
    """
    Create a gauge chart similar to Apollo.io style
    
    Args:
        value: Current value (0-100)
        title: Chart title
        min_val: Minimum value
        max_val: Maximum value
        thresholds: [yellow_start, green_start] for color zones
    """
    
    # Determine color based on value
    if value >= thresholds[1]:
        color = "#10b981"  # Green
    elif value >= thresholds[0]:
        color = "#f59e0b"  # Yellow/Orange
    else:
        color = "#ef4444"  # Red
    
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = value,
        title = {'text': title, 'font': {'size': 14}},
        domain = {'x': [0, 1], 'y': [0, 1]},
        number = {'suffix': "%", 'font': {'size': 20}},
        gauge = {
            'axis': {'range': [min_val, max_val], 'tickwidth': 1, 'tickcolor': "gray"},
            'bar': {'color': color, 'thickness': 0.75},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "lightgray",
            'steps': [
                {'range': [0, thresholds[0]], 'color': '#fee2e2'},  # Light red
                {'range': [thresholds[0], thresholds[1]], 'color': '#fef3c7'},  # Light yellow
                {'range': [thresholds[1], 100], 'color': '#d1fae5'}  # Light green
            ],
            'threshold': {
                'line': {'color': "black", 'width': 2},
                'thickness': 0.75,
                'value': thresholds[1]
            }
        }
    ))
    
    fig.update_layout(
        height=180,
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="white",
        font={'family': "Arial"}
    )
    
    return fig

def create_battery_indicator(value, label):
    """
    Create a battery-style indicator (0-100%)
    Returns HTML for display
    """
    
    # Determine color and emoji
    if value >= 80:
        color = "#10b981"  # Green
        emoji = "🟢"
        battery_emoji = "🔋"
    elif value >= 60:
        color = "#f59e0b"  # Yellow
        emoji = "🟡"
        battery_emoji = "🔋"
    elif value >= 40:
        color = "#fb923c"  # Orange
        emoji = "🟠"
        battery_emoji = "🪫"
    else:
        color = "#ef4444"  # Red
        emoji = "🔴"
        battery_emoji = "🪫"
    
    # Create battery bar
    battery_width = int(value)
    
    html = f"""
    <div style="background-color: #f3f4f6; padding: 12px; border-radius: 8px; margin: 5px 0;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
            <span style="font-size: 14px; font-weight: 600;">{label}</span>
            <span style="font-size: 18px;">{battery_emoji} {emoji}</span>
        </div>
        <div style="background-color: #e5e7eb; height: 20px; border-radius: 10px; overflow: hidden; position: relative;">
            <div style="background: linear-gradient(90deg, {color} 0%, {color} 100%); 
                        height: 100%; 
                        width: {battery_width}%; 
                        transition: width 0.3s ease;
                        border-radius: 10px;">
            </div>
            <div style="position: absolute; 
                        top: 50%; 
                        left: 50%; 
                        transform: translate(-50%, -50%); 
                        font-size: 11px; 
                        font-weight: 700;
                        color: {'white' if battery_width > 50 else '#1f2937'};
                        text-shadow: 0 0 2px rgba(0,0,0,0.5);">
                {value:.0f}%
            </div>
        </div>
    </div>
    """
    
    return html

def create_metric_card(label, value, status, icon="📊"):
    """
    Create a colored metric card with icon
    """
    
    if status == "good":
        bg_color = "#d1fae5"
        border_color = "#10b981"
        text_color = "#065f46"
    elif status == "warning":
        bg_color = "#fef3c7"
        border_color = "#f59e0b"
        text_color = "#92400e"
    else:  # bad
        bg_color = "#fee2e2"
        border_color = "#ef4444"
        text_color = "#991b1b"
    
    html = f"""
    <div style="background-color: {bg_color}; 
                border-left: 4px solid {border_color}; 
                padding: 12px; 
                border-radius: 6px; 
                margin: 8px 0;">
        <div style="display: flex; align-items: center; justify-content: space-between;">
            <div>
                <div style="font-size: 12px; color: {text_color}; opacity: 0.8; margin-bottom: 2px;">
                    {label}
                </div>
                <div style="font-size: 24px; font-weight: 700; color: {text_color};">
                    {value}
                </div>
            </div>
            <div style="font-size: 32px;">
                {icon}
            </div>
        </div>
    </div>
    """
    
    return html

def create_speedometer(value, title, max_val=10, higher_is_better=False):
    """
    Half-circle speedometer gauge with improved colors + correct direction.
    - For soreness/stress: lower_is_better => higher_is_better=False (default)
    - For mood: higher_is_better=True
    """

    # Clamp value safely
    try:
        v = float(value)
    except Exception:
        v = 0.0
    v = max(0.0, min(float(max_val), v))

    # Define zones on 0..max_val (default 10)
    # You can tweak these if you want (e.g., 0-2-5-10)
    z1 = 0
    z2 = max_val * 0.30   # ~3 on 10-pt scale
    z3 = max_val * 0.70   # ~7 on 10-pt scale
    z4 = max_val

    # Colors (modern, readable)
    GREEN = "#16a34a"
    AMBER = "#f59e0b"
    RED   = "#ef4444"

    # Soft zone fills
    GREEN_BG = "rgba(22,163,74,0.18)"
    AMBER_BG = "rgba(245,158,11,0.20)"
    RED_BG   = "rgba(239,68,68,0.18)"

    # Pick bar color by direction
    if higher_is_better:
        # high = good
        if v >= z3:
            bar_color = GREEN
        elif v >= z2:
            bar_color = AMBER
        else:
            bar_color = RED
        steps = [
            {"range": [z1, z2], "color": RED_BG},
            {"range": [z2, z3], "color": AMBER_BG},
            {"range": [z3, z4], "color": GREEN_BG},
        ]
        # optional "target" marker at good zone start
        threshold_value = z3
    else:
        # low = good
        if v <= z2:
            bar_color = GREEN
        elif v <= z3:
            bar_color = AMBER
        else:
            bar_color = RED
        steps = [
            {"range": [z1, z2], "color": GREEN_BG},
            {"range": [z2, z3], "color": AMBER_BG},
            {"range": [z3, z4], "color": RED_BG},
        ]
        threshold_value = z2

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=v,
            number={"font": {"size": 22}},
            title={"text": title, "font": {"size": 13}},
            gauge={
                "shape": "angular",  # keeps it speedometer-like
                "axis": {
                    "range": [0, max_val],
                    "tickwidth": 1,
                    "tickcolor": "rgba(0,0,0,0.35)",
                    "tickfont": {"size": 10},
                },
                "bar": {"color": bar_color, "thickness": 0.70},
                "bgcolor": "white",
                "borderwidth": 1,
                "bordercolor": "rgba(0,0,0,0.10)",
                "steps": steps,
                "threshold": {
                    "line": {"color": "rgba(0,0,0,0.55)", "width": 3},
                    "thickness": 0.75,
                    "value": threshold_value,
                },
            },
        )
    )

    fig.update_layout(
        height=170,
        margin=dict(l=8, r=8, t=34, b=8),
        paper_bgcolor="white",
        font={"family": "Arial"},
    )

    return fig

# ==============================================================================
# PHOTO HELPERS (SIMPLIFIED FOR STREAMLIT CLOUD)
# ==============================================================================

PHOTOS_DIR = "assets/photos"

def athlete_photo_block(ath_key: str):
    """Display athlete photo (static files only for Streamlit Cloud)"""
    ath_key = str(ath_key).lower()
    
    # Try to find local photo
    for ext in (".jpg", ".jpeg", ".png"):
        photo_path = f"{PHOTOS_DIR}/{ath_key}{ext}"
        if os.path.exists(photo_path):
            st.image(photo_path, use_container_width=True)
            return
    
    # Show placeholder if no photo found
    st.image(
        f"https://via.placeholder.com/200x250/2E86AB/FFFFFF?text={ath_key.replace('_', '+')}",
        use_container_width=True
    )

# ==============================================================================
# RADAR CHART
# ==============================================================================

def create_radar_chart(athlete_data, athlete_name):
    """Create radar chart for athlete's multi-dimensional assessment"""
    
    sleep_score = (athlete_data['sleep_hours'] / 8) * 100
    physical_score = ((10 - athlete_data['soreness']) / 10) * 100
    mental_score = (athlete_data['mood'] / 10) * 100

    acwr = athlete_data.get('acwr', 1.0)
    if 0.8 <= acwr <= 1.3:
        load_score = 100
    elif acwr < 0.8:
        load_score = max(0, 100 - ((0.8 - acwr) * 100))
    else:
        load_score = max(0, 100 - ((acwr - 1.3) * 50))

    cmj = athlete_data.get('cmj_height_cm', 30)
    neuro_score = min(100, (cmj / 40) * 100)

    categories = ['Sleep', 'Physical', 'Mental', 'Load', 'Neuro']
    values = [sleep_score, physical_score, mental_score, load_score, neuro_score]

    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        name=athlete_name,
        fillcolor='rgba(46, 134, 171, 0.3)',
        line=dict(color='rgb(46, 134, 171)', width=2)
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100]
            )
        ),
        showlegend=False,
        title=f"{athlete_name}'s Profile",
        height=300,
        margin=dict(l=40, r=40, t=40, b=20)
    )

    return fig

# ==============================================================================
# MAIN ATHLETE PROFILE TAB
# ==============================================================================

def athlete_profile_tab(wellness, training_load, acwr, force_plate, players, injuries=None):
    """Enhanced athlete profile with Apollo.io-style gauges and indicators"""

    st.header("👤 Athlete Profiles")
    st.markdown("Select an athlete to view their complete performance profile")

    # Athlete selector
    athlete_names = sorted(players['name'].tolist())
    selected_athlete = st.selectbox("Select Athlete", athlete_names)

    if not selected_athlete:
        st.info("Please select an athlete to view their profile")
        return

    # Get athlete data
    athlete_info = players[players['name'] == selected_athlete].iloc[0]
    athlete_id = athlete_info['player_id']

    # Make athlete key
    pid_num = pd.to_numeric(athlete_id, errors="coerce")
    if pd.notnull(pid_num):
        ath_key = f"ath_{int(pid_num):03d}"
    else:
        ath_key = str(athlete_id).strip().lower()

    # Get latest data
    latest_date = wellness['date'].max()
    latest_wellness = wellness[
        (wellness['player_id'] == athlete_id) &
        (wellness['date'] == latest_date)
    ]

    if len(latest_wellness) == 0:
        st.warning(f"No recent data for {selected_athlete}")
        return

    latest_wellness = latest_wellness.iloc[0]

    # Get ACWR data
    latest_acwr_data = acwr[
        (acwr['player_id'] == athlete_id) &
        (acwr['date'] == latest_date)
    ]
    if len(latest_acwr_data) > 0:
        latest_acwr = latest_acwr_data.iloc[0]['acwr']
    else:
        latest_acwr = 1.0

    # Get force plate data
    latest_force = force_plate[
        (force_plate['player_id'] == athlete_id) &
        (force_plate['date'] == latest_date)
    ]
    if len(latest_force) > 0:
        latest_cmj = latest_force.iloc[0]['cmj_height_cm']
        latest_rsi = latest_force.iloc[0]['rsi_modified']
    else:
        latest_cmj = None
        latest_rsi = None

    # Calculate readiness score
    readiness = (
        (latest_wellness['sleep_hours'] / 8) * 30 +
        ((10 - latest_wellness['soreness']) / 10) * 25 +
        ((10 - latest_wellness['stress']) / 10) * 25 +
        (latest_wellness['mood'] / 10) * 20
    )

    # ==================================================================
    # HEADER: Photo + Key Metrics
    # ==================================================================
    
    col1, col2, col3 = st.columns([1, 2, 2])

    with col1:
        st.markdown("### Profile")
        athlete_photo_block(ath_key)
        
        st.markdown(f"**{athlete_info.get('position', '')}** • Age {athlete_info.get('age', '')}")
        st.caption(f"Injury history: {athlete_info.get('injury_history_count', 0)} previous")

    with col2:
        st.markdown("### Overall Readiness")
        
        # Big gauge for overall readiness
        fig = create_gauge_chart(readiness, "Readiness Score", thresholds=[60, 80])
        st.plotly_chart(fig, use_container_width=True, key=f"gauge_readiness_{athlete_id}")
        
        # Training recommendation
        if readiness >= 80:
            st.success("✅ Full training cleared")
        elif readiness >= 60:
            st.info("⚠️ Monitor closely")
        else:
            st.warning("🚨 50% volume reduction recommended")

    with col3:
        st.markdown("### Performance Profile")
        
        # Radar chart
        radar_data = {
            'sleep_hours': latest_wellness['sleep_hours'],
            'soreness': latest_wellness['soreness'],
            'mood': latest_wellness['mood'],
            'stress': latest_wellness['stress'],
            'acwr': latest_acwr,
            'cmj_height_cm': latest_cmj if latest_cmj else 30
        }
        
        fig = create_radar_chart(radar_data, selected_athlete)
        st.plotly_chart(fig, use_container_width=True, key=f"radar_{athlete_id}")

    # ==================================================================
    # BATTERY INDICATORS (Apollo.io style)
    # ==================================================================

    st.markdown("---")
    st.markdown("### 🔋 Key Metrics")

    col1, col2, col3 = st.columns(3)

    with col1:
        # Sleep battery
        sleep_pct = min(100, (latest_wellness['sleep_hours'] / 8) * 100)
        st.markdown(create_battery_indicator(sleep_pct, "Sleep Quality"), unsafe_allow_html=True)
        
        # Physical readiness
        physical_pct = ((10 - latest_wellness['soreness']) / 10) * 100
        st.markdown(create_battery_indicator(physical_pct, "Physical Readiness"), unsafe_allow_html=True)

    with col2:
        # Mental wellness
        mental_pct = (latest_wellness['mood'] / 10) * 100
        st.markdown(create_battery_indicator(mental_pct, "Mental Wellness"), unsafe_allow_html=True)
        
        # Stress (inverted - low is good)
        stress_pct = ((10 - latest_wellness['stress']) / 10) * 100
        st.markdown(create_battery_indicator(stress_pct, "Stress Management"), unsafe_allow_html=True)

    with col3:
        # Load balance (ACWR)
        if 0.8 <= latest_acwr <= 1.3:
            acwr_pct = 100
        elif latest_acwr < 0.8:
            acwr_pct = max(0, latest_acwr / 0.8 * 100)
        else:
            acwr_pct = max(0, 100 - (latest_acwr - 1.3) * 50)
        st.markdown(create_battery_indicator(acwr_pct, "Load Balance"), unsafe_allow_html=True)
        
        # Neuromuscular
        if latest_cmj:
            neuro_pct = min(100, (latest_cmj / 40) * 100)
            st.markdown(create_battery_indicator(neuro_pct, "Neuromuscular"), unsafe_allow_html=True)

    # ==================================================================
    # METRIC CARDS (Detailed Values)
    # ==================================================================

    st.markdown("---")
    st.markdown("### 📊 Detailed Metrics")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        # Sleep card
        if latest_wellness['sleep_hours'] >= 7.5:
            status = "good"
        elif latest_wellness['sleep_hours'] >= 6.5:
            status = "warning"
        else:
            status = "bad"
        st.markdown(
            create_metric_card("Sleep Hours", f"{latest_wellness['sleep_hours']:.1f} hrs", status, "😴"),
            unsafe_allow_html=True
        )

    with col2:
        # Soreness card
        if latest_wellness['soreness'] <= 4:
            status = "good"
        elif latest_wellness['soreness'] <= 7:
            status = "warning"
        else:
            status = "bad"
        st.markdown(
            create_metric_card("Soreness", f"{latest_wellness['soreness']:.0f}/10", status, "😫"),
            unsafe_allow_html=True
        )

    with col3:
        # Mood card
        if latest_wellness['mood'] >= 7:
            status = "good"
        elif latest_wellness['mood'] >= 5:
            status = "warning"
        else:
            status = "bad"
        st.markdown(
            create_metric_card("Mood", f"{latest_wellness['mood']:.0f}/10", status, "😊"),
            unsafe_allow_html=True
        )

    with col4:
        # ACWR card
        if 0.8 <= latest_acwr <= 1.3:
            status = "good"
        elif latest_acwr < 0.8 or (1.3 < latest_acwr <= 1.5):
            status = "warning"
        else:
            status = "bad"
        st.markdown(
            create_metric_card("ACWR", f"{latest_acwr:.2f}", status, "📈"),
            unsafe_allow_html=True
        )

    # ==================================================================
    # SPEEDOMETER GAUGES
    # ==================================================================

    st.markdown("---")
    st.markdown("### 🎯 Wellness Indicators")

    col1, col2, col3 = st.columns(3)

    with col1:
        fig = create_speedometer(latest_wellness['soreness'], "Soreness Level", 10)
        st.plotly_chart(fig, use_container_width=True, key=f"speed_sore_{athlete_id}")

    with col2:
        fig = create_speedometer(latest_wellness['stress'], "Stress Level", 10)
        st.plotly_chart(fig, use_container_width=True, key=f"speed_stress_{athlete_id}")

    with col3:
        fig = create_speedometer(latest_wellness['mood'], "Mood Score", 10)
        st.plotly_chart(fig, use_container_width=True, key=f"speed_mood_{athlete_id}")

    # ==================================================================
    # 7-DAY TRENDS
    # ==================================================================

    st.markdown("---")
    st.markdown("### 📈 7-Day Trends")

    week_ago = latest_date - timedelta(days=7)
    weekly_wellness = wellness[
        (wellness['player_id'] == athlete_id) &
        (wellness['date'] >= week_ago) &
        (wellness['date'] <= latest_date)
    ].sort_values('date')

    if len(weekly_wellness) > 0:
        # Combined trend chart
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=weekly_wellness['date'],
            y=weekly_wellness['sleep_hours'],
            mode='lines+markers',
            name='Sleep (hrs)',
            line=dict(color='#2E86AB', width=2)
        ))
        
        # Normalize soreness to 0-10 scale for comparison
        fig.add_trace(go.Scatter(
            x=weekly_wellness['date'],
            y=weekly_wellness['soreness'],
            mode='lines+markers',
            name='Soreness (0-10)',
            line=dict(color='#A23B72', width=2)
        ))
        
        fig.update_layout(
            title=f"{selected_athlete} - Weekly Trends",
            yaxis_title="Value",
            xaxis_title="Date",
            height=300,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Insufficient data for 7-day trends")

    # Research references
    with st.expander("📚 Research References"):
        st.markdown("""
        **Thresholds used in this profile:**
        - **Sleep:** <6.5 hours = 1.7x injury risk (Milewski et al. 2014)
        - **ACWR:** >1.5 = 2.4x injury risk (Gabbett 2016)
        - **Soreness:** >7 requires monitoring (Hulin et al. 2016)
        """)
