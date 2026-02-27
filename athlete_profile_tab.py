"""
Athlete Profile Tab - Individual athlete dashboards with radar charts
"""

import os
from datetime import datetime, timedelta

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# ==============================================================================
# PHOTO HELPERS
# ==============================================================================

def athlete_photo_block(ath_key: str):
    """
    Display athlete photo with upload option.
    Expects filename convention like: assets/photos/ath_001.jpg (or .png/.jpeg)
    """
    os.makedirs(PHOTOS_DIR, exist_ok=True)

    ath_key = str(ath_key).lower()  # enforce ath_001 convention

    if "athlete_photo_paths" not in st.session_state:
        st.session_state.athlete_photo_paths = {}

    local_photo = st.session_state.athlete_photo_paths.get(ath_key) or _find_local_photo(ath_key)

    # Display: local photo -> placeholder
    if local_photo and os.path.exists(local_photo):
        st.image(local_photo, use_container_width=True, caption=ath_key)
    else:
        st.image(
            "https://via.placeholder.com/200x250/2E86AB/FFFFFF?text=" + ath_key.replace("_", "+"),
            use_container_width=True,
            caption=ath_key
        )

    # Upload under the image
    with st.expander("Upload / update photo"):
        uploaded = st.file_uploader(
            "Choose a JPG/PNG",
            type=["jpg", "jpeg", "png"],
            key=f"photo_uploader_{ath_key}"
        )

        if uploaded is not None:
            _, ext = os.path.splitext(uploaded.name.lower())
            if ext not in [".jpg", ".jpeg", ".png"]:
                ext = ".jpg"

            save_path = os.path.join(PHOTOS_DIR, f"{ath_key}{ext}")
            with open(save_path, "wb") as f:
                f.write(uploaded.getbuffer())

            st.session_state.athlete_photo_paths[ath_key] = save_path
            st.success("Photo updated.")
        

# ==============================================================================
# EXISTING CODE
# ==============================================================================

def create_radar_chart(athlete_data, athlete_name):
    """
    Create radar chart for athlete's multi-dimensional assessment
    """
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

    categories = ['Sleep\nQuality', 'Physical\nReadiness', 'Mental\nWellness',
                  'Load\nBalance', 'Neuromuscular']
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
                range=[0, 100],
                tickvals=[25, 50, 75, 100],
                ticktext=['25', '50', '75', '100']
            )
        ),
        showlegend=False,
        title=f"{athlete_name}'s Performance Profile",
        height=400
    )

    return fig

def athlete_profile_tab(wellness, training_load, acwr, force_plate, players):
    """
    Complete athlete profile tab with photo, radar chart, and metrics
    """

    st.header("👤 Athlete Profiles")
    st.markdown("Select an athlete to view their complete performance profile")

    # Athlete selector (this returns a NAME)
    athlete_names = sorted(players['name'].tolist())
    selected_athlete = st.selectbox("Select Athlete", athlete_names)

    if not selected_athlete:
        st.info("Please select an athlete to view their profile")
        return

    # Get athlete data
    athlete_info = players[players['name'] == selected_athlete].iloc[0]
    athlete_id = athlete_info['player_id']

    # Map player_id -> ath_001 convention for filenames
    try:
        ath_key = f"ath_{int(athlete_id):03d}"
    except Exception:
        ath_key = str(athlete_id).lower()

    # ==================================================================
    # LAYOUT: Photo + Quick Stats  (INSIDE THE FUNCTION)
    # ==================================================================
    col1, col2, col3 = st.columns([1, 2, 2])

    with col1:
        st.markdown("### Profile")
        athlete_photo_block(ath_key)

        st.markdown(f"**Position:** {athlete_info.get('position', '')}")
        st.markdown(f"**Age:** {athlete_info.get('age', '')}")
        st.markdown(f"**Injury History:** {athlete_info.get('injury_history_count', 0)} previous")

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
    latest_acwr = acwr[
        (acwr['player_id'] == athlete_id) &
        (acwr['date'] == latest_date)
    ]
    if len(latest_acwr) > 0:
        latest_acwr = latest_acwr.iloc[0]['acwr']
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
        
    # Basic info
    st.markdown(f"**Position:** {athlete_info['position']}")
    st.markdown(f"**Age:** {athlete_info['age']}")
    st.markdown(f"**Injury History:** {athlete_info['injury_history_count']} previous")
    with col2:
        st.markdown("### Today's Status")
        
        # Calculate readiness score
        readiness = (
            (latest_wellness['sleep_hours'] / 8) * 30 +
            ((10 - latest_wellness['soreness']) / 10) * 25 +
            ((10 - latest_wellness['stress']) / 10) * 25 +
            (latest_wellness['mood'] / 10) * 20
        )
        
        # Status color
        if readiness >= 80:
            status_color = "🟢"
            status_text = "Ready"
            status_bg = "#d4edda"
        elif readiness >= 60:
            status_color = "🟡"
            status_text = "Monitor"
            status_bg = "#fff3cd"
        else:
            status_color = "🔴"
            status_text = "At Risk"
            status_bg = "#f8d7da"
        
        st.markdown(
            f"""
            <div style="background-color: {status_bg}; padding: 10px; border-radius: 8px; text-align: center;">
                <h1 style="margin: 0;">{status_color}</h1>
                <h2 style="margin: 10px 0;">{status_text}</h2>
                <h3 style="margin: 0;">Readiness: {readiness:.0f}/100</h3>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        st.markdown("---")
        
        # Key metrics in compact cards
        metric_col1, metric_col2 = st.columns(2)
        
        with metric_col1:
            st.metric("💤 Sleep", f"{latest_wellness['sleep_hours']:.1f} hrs",
                     delta=f"Target: 8.0 hrs",
                     delta_color="inverse" if latest_wellness['sleep_hours'] < 7 else "normal")
            st.metric("😫 Soreness", f"{latest_wellness['soreness']:.0f}/10",
                     delta=f"Threshold: 7",
                     delta_color="inverse" if latest_wellness['soreness'] > 7 else "normal")
        
        with metric_col2:
            st.metric("😊 Mood", f"{latest_wellness['mood']:.0f}/10")
            st.metric("😰 Stress", f"{latest_wellness['stress']:.0f}/10",
                     delta=f"Threshold: 7",
                     delta_color="inverse" if latest_wellness['stress'] > 7 else "normal")
    
    with col3:
        st.markdown("### Performance Profile")
        
        # Prepare data for radar chart
        radar_data = {
            'sleep_hours': latest_wellness['sleep_hours'],
            'soreness': latest_wellness['soreness'],
            'mood': latest_wellness['mood'],
            'stress': latest_wellness['stress'],
            'acwr': latest_acwr,
            'cmj_height_cm': latest_cmj if latest_cmj else 30
        }
        
        # Create and display radar chart
        fig = create_radar_chart(radar_data, selected_athlete)
        st.plotly_chart(fig, use_container_width=True)
    
    # ==================================================================
    # WORKLOAD SECTION
    # ==================================================================
    
    st.markdown("---")
    st.markdown("### 📊 Workload Management")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # ACWR status
        if latest_acwr > 1.5:
            acwr_status = "🔴 High Risk"
            acwr_color = "#f8d7da"
        elif latest_acwr > 1.3:
            acwr_status = "🟡 Elevated"
            acwr_color = "#fff3cd"
        elif latest_acwr < 0.8:
            acwr_status = "🟡 Detraining"
            acwr_color = "#fff3cd"
        else:
            acwr_status = "🟢 Optimal"
            acwr_color = "#d4edda"
        
        st.markdown(
            f"""
            <div style="background-color: {acwr_color}; padding: 15px; border-radius: 8px;">
                <h4 style="margin: 0;">ACWR: {latest_acwr:.2f}</h4>
                <p style="margin: 5px 0;">{acwr_status}</p>
                <small>Optimal: 0.8-1.3</small>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    with col2:
        # Recent training load
        recent_load = training_load[
            (training_load['player_id'] == athlete_id) &
            (training_load['date'] == latest_date)
        ]
        
        if len(recent_load) > 0:
            load = recent_load.iloc[0]['total_daily_load']
            st.metric("Total Daily Load", f"{load:.0f} AU",
                     help="Arbitrary Units based on duration × RPE")
        else:
            st.metric("Total Daily Load", "N/A")
    
    with col3:
        # Neuromuscular readiness
        if latest_cmj and latest_rsi:
            st.metric("CMJ Height", f"{latest_cmj:.1f} cm")
            st.metric("RSI-Modified", f"{latest_rsi:.2f}",
                     delta="Target: 0.35+",
                     delta_color="normal" if latest_rsi >= 0.35 else "inverse")
        else:
            st.info("No recent force plate data")
    
    # ==================================================================
    # TRENDS SECTION
    # ==================================================================
    
    st.markdown("---")
    st.markdown("### 📈 7-Day Trends")
    
    # Get last 7 days of data
    week_ago = latest_date - timedelta(days=7)
    weekly_wellness = wellness[
        (wellness['player_id'] == athlete_id) &
        (wellness['date'] >= week_ago) &
        (wellness['date'] <= latest_date)
    ].sort_values('date')
    
    if len(weekly_wellness) > 0:
        tab1, tab2, tab3 = st.tabs(["Sleep & Recovery", "Wellness", "Load"])
        
        with tab1:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=weekly_wellness['date'],
                y=weekly_wellness['sleep_hours'],
                mode='lines+markers',
                name='Sleep Hours',
                line=dict(color='#2E86AB', width=3)
            ))
            fig.add_hline(y=7, line_dash="dash", line_color="orange", 
                         annotation_text="7 hrs (minimum)")
            fig.add_hline(y=8, line_dash="dash", line_color="green", 
                         annotation_text="8 hrs (target)")
            fig.update_layout(
                title=f"{selected_athlete} - Sleep Pattern",
                yaxis_title="Hours",
                xaxis_title="Date",
                height=300
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Soreness
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=weekly_wellness['date'],
                y=weekly_wellness['soreness'],
                mode='lines+markers',
                name='Soreness',
                line=dict(color='#A23B72', width=3),
                fill='tozeroy',
                fillcolor='rgba(162, 59, 114, 0.2)'
            ))
            fig2.add_hline(y=7, line_dash="dash", line_color="red",
                          annotation_text="High threshold")
            fig2.update_layout(
                title=f"{selected_athlete} - Soreness Levels",
                yaxis_title="Soreness (0-10)",
                xaxis_title="Date",
                height=300
            )
            st.plotly_chart(fig2, use_container_width=True)
        
        with tab2:
            # Mood and stress
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=weekly_wellness['date'],
                y=weekly_wellness['mood'],
                mode='lines+markers',
                name='Mood',
                line=dict(color='#2E86AB')
            ))
            fig.add_trace(go.Scatter(
                x=weekly_wellness['date'],
                y=weekly_wellness['stress'],
                mode='lines+markers',
                name='Stress',
                line=dict(color='#A23B72')
            ))
            fig.update_layout(
                title=f"{selected_athlete} - Mood & Stress",
                yaxis_title="Score (0-10)",
                xaxis_title="Date",
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with tab3:
            # ACWR trend
            weekly_acwr = acwr[
                (acwr['player_id'] == athlete_id) &
                (acwr['date'] >= week_ago) &
                (acwr['date'] <= latest_date)
            ].sort_values('date')
            
            if len(weekly_acwr) > 0:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=weekly_acwr['date'],
                    y=weekly_acwr['acwr'],
                    mode='lines+markers',
                    name='ACWR',
                    line=dict(color='#2E86AB', width=3)
                ))
                fig.add_hrect(y0=0.8, y1=1.3, fillcolor="green", opacity=0.1,
                             annotation_text="Optimal Zone", annotation_position="top left")
                fig.add_hline(y=1.5, line_dash="dash", line_color="red",
                             annotation_text="High Risk (1.5)")
                fig.update_layout(
                    title=f"{selected_athlete} - ACWR Trend",
                    yaxis_title="ACWR",
                    xaxis_title="Date",
                    height=400
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No ACWR data for this period")
    else:
        st.warning("Insufficient data for 7-day trends")
    
    # ==================================================================
    # ALERTS & RECOMMENDATIONS
    # ==================================================================
    
    st.markdown("---")
    st.markdown("### ⚠️ Alerts & Recommendations")
    
    alerts = []
    recommendations = []
    
    # Check for risk factors
    if latest_wellness['sleep_hours'] < 6.5:
        alerts.append("🌙 **Poor Sleep** - Below injury risk threshold (6.5 hrs)")
        recommendations.append("Consult with Player around sleep")
    
    if latest_wellness['soreness'] > 7:
        alerts.append("😫 **High Soreness** - Elevated muscle fatigue")
        recommendations.append("Focus on recovery modalities (massage, cold therapy)")
    
    if latest_wellness['stress'] > 7:
        alerts.append("😰 **High Stress** - Elevated psychological load")
        recommendations.append("Consider mental health check-in or stress management")
    
    if latest_acwr > 1.5:
        alerts.append("📊 **High ACWR** - Spike in training load")
        recommendations.append("Reduce training volume or intensity by 20-30%")
    elif latest_acwr < 0.8:
        alerts.append("📊 **Low ACWR** - Possible detraining")
        recommendations.append("Gradually increase training load if cleared medically")
    
    if latest_rsi and latest_rsi < 0.30:
        alerts.append("💪 **Low Neuromuscular Performance** - CMJ/RSI below baseline")
        recommendations.append("Check for fatigue, consider additional recovery time")
    
    if athlete_info['injury_history_count'] > 2:
        alerts.append(f"🏥 **Injury History** - {athlete_info['injury_history_count']} previous injuries")
        recommendations.append("Monitor closely for re-injury risk factors")
    
    # Display alerts
    if alerts:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Current Alerts:**")
            for alert in alerts:
                st.warning(alert)
        
        with col2:
            st.markdown("**Recommendations:**")
            for rec in recommendations:
                st.info(f"💡 {rec}")
    else:
        st.success("✅ No current alerts - athlete is in good standing!")
    
    # Research references
    with st.expander("📚 Research References"):
        st.markdown("""
        **Thresholds used in this profile:**
        
        - **Sleep:** <6.5 hours = 1.7x injury risk (Milewski et al. 2014)
        - **ACWR:** >1.5 = 2.4x injury risk (Gabbett 2016)
        - **Soreness:** >7 requires monitoring (Hulin et al. 2016)
        - **RSI-Modified:** <0.30 indicates reduced neuromuscular function
        
        All metrics are based on peer-reviewed sports science research.
        """)
