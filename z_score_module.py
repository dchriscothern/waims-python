"""
Z-Score Module for Personalized Athlete Monitoring
Compares current values to individual baseline (not population average)
"""

import pandas as pd
import numpy as np
import streamlit as st

def calculate_athlete_baselines(wellness_df, player_id, lookback_days=30):
    """
    Calculate personal baseline statistics for an athlete
    
    Args:
        wellness_df: DataFrame with wellness data
        player_id: Athlete ID
        lookback_days: Days to use for baseline (default 30)
    
    Returns:
        dict: {metric: {'mean': X, 'std': Y}}
    """
    
    # Get athlete's recent history
    athlete_data = wellness_df[wellness_df['player_id'] == player_id].copy()
    athlete_data = athlete_data.sort_values('date', ascending=False).head(lookback_days)
    
    if len(athlete_data) < 7:
        # Not enough data for baseline
        return None
    
    baselines = {
        'sleep_hours': {
            'mean': athlete_data['sleep_hours'].mean(),
            'std': athlete_data['sleep_hours'].std() or 0.5  # Avoid division by zero
        },
        'soreness': {
            'mean': athlete_data['soreness'].mean(),
            'std': athlete_data['soreness'].std() or 1.0
        },
        'stress': {
            'mean': athlete_data['stress'].mean(),
            'std': athlete_data['stress'].std() or 1.0
        },
        'mood': {
            'mean': athlete_data['mood'].mean(),
            'std': athlete_data['mood'].std() or 1.0
        },
        'sleep_quality': {
            'mean': athlete_data['sleep_quality'].mean(),
            'std': athlete_data['sleep_quality'].std() or 1.0
        }
    }
    
    return baselines

def calculate_z_score(current_value, baseline_mean, baseline_std):
    """
    Calculate z-score
    
    Returns:
        float: z-score (negative = below baseline, positive = above)
    """
    
    if baseline_std == 0:
        baseline_std = 0.5  # Prevent division by zero
    
    z_score = (current_value - baseline_mean) / baseline_std
    return z_score

def interpret_z_score(z_score, metric_type="higher_better"):
    """
    Interpret z-score with color coding
    
    Args:
        z_score: float
        metric_type: "higher_better" (sleep, mood) or "lower_better" (soreness, stress)
    
    Returns:
        tuple: (status, color, emoji, interpretation)
    """
    
    if metric_type == "higher_better":
        # For sleep, mood (higher is better)
        if z_score >= 1.0:
            return ("Excellent", "#10b981", "🟢", "Above personal average")
        elif z_score >= 0:
            return ("Normal", "#3b82f6", "🔵", "Near personal average")
        elif z_score >= -1.0:
            return ("Below Average", "#f59e0b", "🟡", "Below personal average")
        else:
            return ("Concerning", "#ef4444", "🔴", "Well below personal average")
    
    else:  # lower_better
        # For soreness, stress (lower is better)
        if z_score <= -1.0:
            return ("Excellent", "#10b981", "🟢", "Below personal average")
        elif z_score <= 0:
            return ("Normal", "#3b82f6", "🔵", "Near personal average")
        elif z_score <= 1.0:
            return ("Elevated", "#f59e0b", "🟡", "Above personal average")
        else:
            return ("Concerning", "#ef4444", "🔴", "Well above personal average")

def create_z_score_display(metric_name, current_value, z_score, metric_type="higher_better", unit=""):
    """
    Create visual display for z-score comparison
    
    Returns HTML showing current value vs personal baseline
    """
    
    status, color, emoji, interpretation = interpret_z_score(z_score, metric_type)
    
    # Z-score bar (centered at 0)
    # Map z-score to percentage for display (-3 to +3 = 0% to 100%)
    bar_position = min(100, max(0, ((z_score + 3) / 6) * 100))
    
    html = f"""
    <div style="background: white; 
                border: 2px solid {color}40; 
                border-radius: 10px; 
                padding: 14px;
                margin: 10px 0;">
        
        <!-- Header -->
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
            <span style="font-size: 13px; font-weight: 700; color: #1f2937;">
                {metric_name}
            </span>
            <span style="font-size: 16px; font-weight: 800; color: {color};">
                {emoji} {current_value:.1f}{unit}
            </span>
        </div>
        
        <!-- Z-Score Bar -->
        <div style="position: relative; margin-bottom: 8px;">
            <div style="background: linear-gradient(to right, 
                        #ef4444 0%, #f59e0b 33%, #3b82f6 50%, #10b981 67%, #10b981 100%);
                        height: 24px;
                        border-radius: 12px;
                        opacity: 0.2;">
            </div>
            
            <!-- Center line (baseline) -->
            <div style="position: absolute; top: 0; left: 50%; width: 2px; height: 24px; 
                        background: #1f2937; opacity: 0.4;"></div>
            
            <!-- Current position marker -->
            <div style="position: absolute; 
                        top: -4px; 
                        left: {bar_position}%; 
                        transform: translateX(-50%);
                        width: 4px; 
                        height: 32px; 
                        background: {color};
                        border-radius: 2px;
                        box-shadow: 0 2px 8px {color}80;"></div>
        </div>
        
        <!-- Labels -->
        <div style="display: flex; justify-content: space-between; font-size: 10px; color: #6b7280; margin-bottom: 8px;">
            <span>-3σ</span>
            <span style="font-weight: 700;">Baseline (0)</span>
            <span>+3σ</span>
        </div>
        
        <!-- Status -->
        <div style="background: {color}15; 
                    padding: 8px 12px; 
                    border-radius: 6px;
                    border-left: 3px solid {color};">
            <div style="font-size: 12px; font-weight: 700; color: {color}; margin-bottom: 2px;">
                {status} (z = {z_score:+.2f})
            </div>
            <div style="font-size: 11px; color: #374151;">
                {interpretation}
            </div>
        </div>
    </div>
    """
    
    return html

def create_hybrid_score(absolute_score, z_score_penalty=0, absolute_threshold=True):
    """
    Hybrid scoring: Use absolute thresholds BUT apply z-score penalty
    
    Args:
        absolute_score: 0-100 score from absolute thresholds
        z_score_penalty: If athlete is >2σ below baseline, apply penalty
        absolute_threshold: If True, override with absolute safety threshold
    
    Example:
        - Sleep = 7.2 hrs (absolute score: 90)
        - But athlete normally sleeps 9 hrs (z = -3.6)
        - Apply penalty: 90 - 15 = 75 (still "good" but flagged as deviation)
    """
    
    final_score = absolute_score
    
    # Apply z-score penalty for large deviations
    if z_score_penalty < -2.0:
        # More than 2 std deviations below personal baseline
        penalty = min(20, abs(z_score_penalty) * 5)
        final_score = max(0, absolute_score - penalty)
    
    return final_score

def add_z_score_alerts(current_wellness, baselines, research_thresholds):
    """
    Combine z-scores with research thresholds for smarter alerts
    
    Args:
        current_wellness: Today's wellness metrics
        baselines: Personal baseline dict
        research_thresholds: Dict of research-based absolute thresholds
    
    Returns:
        list: Smart alerts combining both approaches
    """
    
    alerts = []
    
    # Sleep
    sleep_z = calculate_z_score(
        current_wellness['sleep_hours'],
        baselines['sleep_hours']['mean'],
        baselines['sleep_hours']['std']
    )
    
    # Absolute threshold (research)
    if current_wellness['sleep_hours'] < 6.5:
        alerts.append({
            'type': 'critical',
            'metric': 'Sleep',
            'message': f"Sleep <6.5 hrs (research threshold) - 1.7x injury risk",
            'color': '#ef4444'
        })
    # Z-score deviation (personal)
    elif sleep_z < -2.0:
        alerts.append({
            'type': 'warning',
            'metric': 'Sleep',
            'message': f"Sleep {current_wellness['sleep_hours']:.1f} hrs is unusually low for this athlete (z={sleep_z:.1f})",
            'color': '#f59e0b'
        })
    
    # Soreness
    soreness_z = calculate_z_score(
        current_wellness['soreness'],
        baselines['soreness']['mean'],
        baselines['soreness']['std']
    )
    
    if current_wellness['soreness'] > 7:
        alerts.append({
            'type': 'warning',
            'metric': 'Soreness',
            'message': f"Soreness >7 (research threshold) - requires monitoring",
            'color': '#f59e0b'
        })
    elif soreness_z > 2.0:
        alerts.append({
            'type': 'info',
            'metric': 'Soreness',
            'message': f"Soreness {current_wellness['soreness']:.0f}/10 is unusually high for this athlete",
            'color': '#3b82f6'
        })
    
    return alerts

# ==============================================================================
# USAGE EXAMPLES
# ==============================================================================

"""
# Example 1: Calculate baselines for an athlete
baselines = calculate_athlete_baselines(wellness, player_id="ATH_001", lookback_days=30)

# Example 2: Display z-score for sleep
current_sleep = 7.2
sleep_z = calculate_z_score(
    current_sleep, 
    baselines['sleep_hours']['mean'],
    baselines['sleep_hours']['std']
)

st.markdown(
    create_z_score_display(
        metric_name="Sleep Duration",
        current_value=current_sleep,
        z_score=sleep_z,
        metric_type="higher_better",
        unit=" hrs"
    ),
    unsafe_allow_html=True
)

# Example 3: Smart alerts (research + personal)
alerts = add_z_score_alerts(
    current_wellness=latest_wellness,
    baselines=baselines,
    research_thresholds={'sleep': 6.5, 'soreness': 7, 'acwr': 1.5}
)

for alert in alerts:
    if alert['type'] == 'critical':
        st.error(alert['message'])
    elif alert['type'] == 'warning':
        st.warning(alert['message'])
    else:
        st.info(alert['message'])
"""
