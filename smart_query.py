"""
WAIMS - Smart Data Query Interface
Natural language-style queries WITHOUT AI - uses pattern matching and rules

Perfect for demos - no API keys needed, instant responses, $0 cost

User can type questions like:
- "poor sleep"
- "high risk"
- "tired players"
- "injuries this month"
"""

import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import re

# ==============================================================================
# CONFIGURATION
# ==============================================================================

st.set_page_config(
    page_title="WAIMS Smart Query",
    page_icon="🔍",
    layout="wide"
)

# ==============================================================================
# DATABASE FUNCTIONS
# ==============================================================================

def get_latest_date():
    """Get most recent date in database."""
    conn = sqlite3.connect('waims_demo.db')
    result = pd.read_sql_query("SELECT MAX(date) as max_date FROM wellness", conn)
    conn.close()
    return result['max_date'].iloc[0]

def query_poor_sleep(threshold=6.5):
    """Find players with poor sleep."""
    latest_date = get_latest_date()
    conn = sqlite3.connect('waims_demo.db')
    
    query = f"""
    SELECT 
        p.name,
        w.sleep_hours,
        w.soreness,
        w.stress,
        w.date
    FROM wellness w
    JOIN players p ON w.player_id = p.player_id
    WHERE w.date = '{latest_date}'
    AND w.sleep_hours < {threshold}
    ORDER BY w.sleep_hours
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def query_high_risk():
    """Find players at high injury risk."""
    latest_date = get_latest_date()
    conn = sqlite3.connect('waims_demo.db')
    
    query = f"""
    SELECT 
        p.name,
        w.sleep_hours,
        w.soreness,
        a.acwr,
        p.injury_history_count,
        CASE 
            WHEN a.acwr > 1.5 THEN 'High ACWR'
            WHEN w.sleep_hours < 6.5 THEN 'Poor Sleep'
            WHEN w.soreness > 7 THEN 'High Soreness'
            ELSE 'Multiple Factors'
        END as primary_risk
    FROM wellness w
    JOIN players p ON w.player_id = p.player_id
    LEFT JOIN acwr a ON w.player_id = a.player_id AND w.date = a.date
    WHERE w.date = '{latest_date}'
    AND (a.acwr > 1.5 OR w.sleep_hours < 6.5 OR w.soreness > 7)
    ORDER BY a.acwr DESC
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def query_by_position(position):
    """Get stats by position."""
    latest_date = get_latest_date()
    conn = sqlite3.connect('waims_demo.db')
    
    query = f"""
    SELECT 
        p.name,
        p.position,
        w.sleep_hours,
        w.soreness,
        w.mood,
        w.stress
    FROM wellness w
    JOIN players p ON w.player_id = p.player_id
    WHERE w.date = '{latest_date}'
    AND p.position = '{position}'
    ORDER BY p.name
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def query_injuries(days_back=30):
    """Get recent injuries."""
    cutoff_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    conn = sqlite3.connect('waims_demo.db')
    
    query = f"""
    SELECT 
        p.name,
        i.injury_date,
        i.injury_type,
        i.days_missed
    FROM injuries i
    JOIN players p ON i.player_id = p.player_id
    WHERE i.injury_date >= '{cutoff_date}'
    ORDER BY i.injury_date DESC
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def query_player_trends(player_name, days_back=14):
    """Get wellness trends for a player."""
    cutoff_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    conn = sqlite3.connect('waims_demo.db')
    
    query = f"""
    SELECT 
        w.date,
        w.sleep_hours,
        w.soreness,
        w.stress,
        w.mood
    FROM wellness w
    JOIN players p ON w.player_id = p.player_id
    WHERE p.name = '{player_name}'
    AND w.date >= '{cutoff_date}'
    ORDER BY w.date
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def query_readiness_scores():
    """Calculate current readiness scores."""
    latest_date = get_latest_date()
    conn = sqlite3.connect('waims_demo.db')
    
    query = f"""
    SELECT 
        p.name,
        w.sleep_hours,
        w.soreness,
        w.stress,
        w.mood,
        ((w.sleep_hours / 8.0 * 30) + 
         ((10 - w.soreness) / 10.0 * 25) + 
         ((10 - w.stress) / 10.0 * 25) + 
         (w.mood / 10.0 * 20)) as readiness_score
    FROM wellness w
    JOIN players p ON w.player_id = p.player_id
    WHERE w.date = '{latest_date}'
    ORDER BY readiness_score
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def query_team_averages():
    """Get team average metrics."""
    latest_date = get_latest_date()
    conn = sqlite3.connect('waims_demo.db')
    
    query = f"""
    SELECT 
        AVG(w.sleep_hours) as avg_sleep,
        AVG(w.soreness) as avg_soreness,
        AVG(w.stress) as avg_stress,
        AVG(w.mood) as avg_mood,
        COUNT(*) as player_count
    FROM wellness w
    WHERE w.date = '{latest_date}'
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def query_position_comparison():
    """Compare metrics by position."""
    latest_date = get_latest_date()
    conn = sqlite3.connect('waims_demo.db')
    
    query = f"""
    SELECT 
        p.position,
        AVG(w.sleep_hours) as avg_sleep,
        AVG(w.soreness) as avg_soreness,
        AVG(w.stress) as avg_stress,
        AVG(w.mood) as avg_mood,
        COUNT(*) as count
    FROM wellness w
    JOIN players p ON w.player_id = p.player_id
    WHERE w.date = '{latest_date}'
    GROUP BY p.position
    ORDER BY p.position
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def query_high_acwr():
    """Find players with high ACWR."""
    latest_date = get_latest_date()
    conn = sqlite3.connect('waims_demo.db')
    
    query = f"""
    SELECT 
        p.name,
        a.acwr,
        a.acute_load,
        a.chronic_load,
        CASE 
            WHEN a.acwr > 1.5 THEN 'High Risk'
            WHEN a.acwr > 1.3 THEN 'Moderate Risk'
            WHEN a.acwr < 0.8 THEN 'Detraining'
            ELSE 'Optimal'
        END as status
    FROM acwr a
    JOIN players p ON a.player_id = p.player_id
    WHERE a.date = '{latest_date}'
    AND a.acwr > 1.3
    ORDER BY a.acwr DESC
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_all_players():
    """Get list of all players."""
    conn = sqlite3.connect('waims_demo.db')
    df = pd.read_sql_query("SELECT DISTINCT name FROM players ORDER BY name", conn)
    conn.close()
    return df['name'].tolist()

# ==============================================================================
# PATTERN MATCHING
# ==============================================================================

def parse_query(user_input):
    """
    Parse user input and determine what they want.
    Returns: (query_type, params)
    """
    user_input = user_input.lower().strip()
    
    # Poor sleep patterns
    if any(word in user_input for word in ['poor sleep', 'bad sleep', 'tired', 'not sleeping', 'sleep <', 'sleep under']):
        return 'poor_sleep', {}
    
    # High risk patterns
    if any(word in user_input for word in ['high risk', 'at risk', 'injury risk', 'risky', 'danger']):
        return 'high_risk', {}
    
    # Readiness patterns
    if any(word in user_input for word in ['readiness', 'ready', 'who can practice', 'who can play']):
        return 'readiness', {}
    
    # ACWR patterns
    if any(word in user_input for word in ['acwr', 'workload', 'overload', 'training load']):
        return 'high_acwr', {}
    
    # Injury patterns
    if any(word in user_input for word in ['injury', 'injuries', 'hurt', 'injured']):
        return 'injuries', {}
    
    # Position patterns
    if 'guard' in user_input:
        return 'position', {'position': 'G'}
    if 'forward' in user_input:
        return 'position', {'position': 'F'}
    if 'center' in user_input:
        return 'position', {'position': 'C'}
    
    # Comparison patterns
    if any(word in user_input for word in ['compare position', 'position comparison', 'guards vs', 'compare guards']):
        return 'position_comparison', {}
    
    # Team average patterns
    if any(word in user_input for word in ['team average', 'average', 'overall team']):
        return 'team_averages', {}
    
    # Specific player patterns
    all_players = get_all_players()
    for player in all_players:
        if player.lower() in user_input:
            if 'trend' in user_input or 'history' in user_input or 'over time' in user_input:
                return 'player_trends', {'player_name': player}
            else:
                return 'player_info', {'player_name': player}
    
    # Default
    return 'unknown', {}

# ==============================================================================
# RESPONSE GENERATION
# ==============================================================================

def generate_response(query_type, params):
    """Generate response based on query type."""
    
    if query_type == 'poor_sleep':
        df = query_poor_sleep()
        if len(df) == 0:
            return "✅ Great news! No players had poor sleep (<6.5 hrs) last night.", None
        
        st.subheader(f"⚠️ {len(df)} Players with Poor Sleep")
        st.dataframe(df, use_container_width=True)
        
        response = f"**{len(df)} players** had poor sleep (<6.5 hours):\n\n"
        for _, row in df.iterrows():
            response += f"- **{row['name']}**: {row['sleep_hours']:.1f} hours (Soreness: {row['soreness']}/10)\n"
        
        response += "\n📚 **Research:** Sleep <6.5 hours increases injury risk 1.7x (Milewski 2014)"
        return response, df
    
    elif query_type == 'high_risk':
        df = query_high_risk()
        if len(df) == 0:
            return "✅ No players currently showing high injury risk indicators.", None
        
        st.subheader(f"🚨 {len(df)} Players at Elevated Risk")
        st.dataframe(df, use_container_width=True)
        
        response = f"**{len(df)} players** showing elevated injury risk:\n\n"
        for _, row in df.iterrows():
            response += f"- **{row['name']}** ({row['primary_risk']})\n"
            response += f"  - ACWR: {row['acwr']:.2f}, Sleep: {row['sleep_hours']:.1f}hrs, Soreness: {row['soreness']}/10\n"
        
        response += "\n💡 **Recommendation:** Consider modified training or rest day"
        return response, df
    
    elif query_type == 'readiness':
        df = query_readiness_scores()
        
        st.subheader("📊 Readiness Scores")
        
        # Color code by score
        def color_score(val):
            if val >= 80:
                return 'background-color: #d4edda'
            elif val >= 60:
                return 'background-color: #fff3cd'
            else:
                return 'background-color: #f8d7da'
        
        styled_df = df.style.applymap(color_score, subset=['readiness_score'])
        st.dataframe(styled_df, use_container_width=True)
        
        green = len(df[df['readiness_score'] >= 80])
        yellow = len(df[(df['readiness_score'] >= 60) & (df['readiness_score'] < 80)])
        red = len(df[df['readiness_score'] < 60])
        
        response = f"**Readiness Status:**\n\n"
        response += f"🟢 **Ready ({green}):** Score ≥80\n"
        response += f"🟡 **Monitor ({yellow}):** Score 60-79\n"
        response += f"🔴 **Needs Attention ({red}):** Score <60\n"
        
        if red > 0:
            low_readiness = df[df['readiness_score'] < 60]
            response += f"\n**Players needing attention:**\n"
            for _, row in low_readiness.iterrows():
                response += f"- {row['name']}: {row['readiness_score']:.0f}/100\n"
        
        return response, df
    
    elif query_type == 'high_acwr':
        df = query_high_acwr()
        if len(df) == 0:
            return "✅ All players have ACWR in optimal range (0.8-1.3)", None
        
        st.subheader(f"⚠️ {len(df)} Players with Elevated ACWR")
        st.dataframe(df, use_container_width=True)
        
        response = f"**{len(df)} players** with ACWR >1.3:\n\n"
        for _, row in df.iterrows():
            response += f"- **{row['name']}**: ACWR {row['acwr']:.2f} ({row['status']})\n"
        
        response += "\n📚 **Research:** ACWR >1.5 = 2.4x injury risk (Gabbett 2016)"
        return response, df
    
    elif query_type == 'injuries':
        df = query_injuries()
        if len(df) == 0:
            return "✅ No injuries recorded in the past 30 days", None
        
        st.subheader(f"🏥 Recent Injuries (Past 30 Days)")
        st.dataframe(df, use_container_width=True)
        
        response = f"**{len(df)} injuries** in past 30 days:\n\n"
        for _, row in df.iterrows():
            response += f"- **{row['name']}**: {row['injury_type']} ({row['days_missed']} days missed)\n"
            response += f"  - Date: {row['injury_date']}\n"
        
        return response, df
    
    elif query_type == 'position':
        position = params['position']
        df = query_by_position(position)
        
        position_names = {'G': 'Guards', 'F': 'Forwards', 'C': 'Centers'}
        st.subheader(f"📊 {position_names[position]} Stats")
        st.dataframe(df, use_container_width=True)
        
        avg_sleep = df['sleep_hours'].mean()
        avg_soreness = df['soreness'].mean()
        
        response = f"**{position_names[position]}** ({len(df)} players):\n\n"
        response += f"- Average sleep: {avg_sleep:.1f} hours\n"
        response += f"- Average soreness: {avg_soreness:.1f}/10\n"
        
        return response, df
    
    elif query_type == 'position_comparison':
        df = query_position_comparison()
        
        st.subheader("📊 Position Comparison")
        
        # Create bar chart
        fig = px.bar(df, x='position', y=['avg_sleep', 'avg_soreness', 'avg_stress'], 
                     barmode='group', title='Metrics by Position')
        st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(df, use_container_width=True)
        
        response = "**Position Comparison:**\n\n"
        for _, row in df.iterrows():
            pos_names = {'G': 'Guards', 'F': 'Forwards', 'C': 'Centers'}
            response += f"**{pos_names.get(row['position'], row['position'])}:**\n"
            response += f"- Sleep: {row['avg_sleep']:.1f} hrs\n"
            response += f"- Soreness: {row['avg_soreness']:.1f}/10\n"
            response += f"- Stress: {row['avg_stress']:.1f}/10\n\n"
        
        return response, df
    
    elif query_type == 'team_averages':
        df = query_team_averages()
        row = df.iloc[0]
        
        response = f"**Team Averages** ({row['player_count']} players):\n\n"
        response += f"- Sleep: {row['avg_sleep']:.1f} hours\n"
        response += f"- Soreness: {row['avg_soreness']:.1f}/10\n"
        response += f"- Stress: {row['avg_stress']:.1f}/10\n"
        response += f"- Mood: {row['avg_mood']:.1f}/10\n"
        
        return response, df
    
    elif query_type == 'player_trends':
        player_name = params['player_name']
        df = query_player_trends(player_name)
        
        if len(df) == 0:
            return f"No recent data found for {player_name}", None
        
        st.subheader(f"📈 Trends for {player_name}")
        
        # Create line chart
        fig = px.line(df, x='date', y=['sleep_hours', 'soreness', 'stress', 'mood'],
                     title=f'{player_name} - 14 Day Trends')
        st.plotly_chart(fig, use_container_width=True)
        
        response = f"**{player_name} - Past 14 Days:**\n\n"
        response += f"- Average sleep: {df['sleep_hours'].mean():.1f} hours\n"
        response += f"- Average soreness: {df['soreness'].mean():.1f}/10\n"
        response += f"- Trend: "
        
        if df['sleep_hours'].iloc[-1] < df['sleep_hours'].iloc[0]:
            response += "Sleep declining ⬇️\n"
        else:
            response += "Sleep improving ⬆️\n"
        
        return response, df
    
    else:
        return """❓ I didn't understand that question. Try asking:
        
**Quick Checks:**
- "poor sleep"
- "high risk"
- "readiness scores"
- "injuries"

**Position Specific:**
- "guards"
- "forwards" 
- "centers"
- "compare positions"

**Player Specific:**
- "ATH_001 trends"
- "ATH_003 history"

**Workload:**
- "high ACWR"
- "overload"

**Team:**
- "team averages"
        """, None

# ==============================================================================
# STREAMLIT UI
# ==============================================================================

st.title("🔍 WAIMS Smart Query Interface")
st.markdown("Ask questions about your data - **instant answers!**")

# Sidebar with How to Use at top, then quick buttons
with st.sidebar:
    st.header("💡 How to Use")
    
    st.markdown("**Type naturally:**")
    st.markdown("""
    - "Who's tired?"
    - "Show me high risk"
    - "Guards vs forwards"
    - "ATH_001 trends"
    """)
    
    st.divider()
    
    st.header("⚡ Quick Queries")
    
    if st.button("🌙 Poor Sleep", use_container_width=True):
        st.session_state.query = "poor sleep"
    
    if st.button("🚨 High Risk Players", use_container_width=True):
        st.session_state.query = "high risk"
    
    if st.button("✅ Readiness Scores", use_container_width=True):
        st.session_state.query = "readiness"
    
    if st.button("💪 High ACWR", use_container_width=True):
        st.session_state.query = "high acwr"
    
    if st.button("🏥 Recent Injuries", use_container_width=True):
        st.session_state.query = "injuries"
    
    if st.button("📊 Position Comparison", use_container_width=True):
        st.session_state.query = "compare positions"
    
    if st.button("📈 Team Averages", use_container_width=True):
        st.session_state.query = "team averages"
    
    st.divider()
    
    st.caption("⚡ Instant responses")
    st.caption("💰 $0 cost")
    st.caption("🔒 100% local")

# Initialize session state
if 'query' not in st.session_state:
    st.session_state.query = ""

# Always show text input
query_input = st.text_input("Ask a question:", placeholder="e.g., 'Who had poor sleep?' or 'Show me high risk players'")

# Check if button was clicked (overrides text input)
if st.session_state.query:
    query_input = st.session_state.query
    st.session_state.query = ""  # Clear after use

if query_input:
    st.divider()
    
    # Parse query
    query_type, params = parse_query(query_input)
    
    # Show what we understood
    st.info(f"🔍 **Understood as:** {query_type.replace('_', ' ').title()}")
    
    # Generate response
    response, data = generate_response(query_type, params)
    
    # Display response
    st.markdown(response)
    
    # Export option
    if data is not None and len(data) > 0:
        st.divider()
        csv = data.to_csv(index=False)
        st.download_button(
            label="📥 Download Results (CSV)",
            data=csv,
            file_name=f"waims_query_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

# Footer
st.divider()
st.caption("🔐 **100% Local** - Your data never leaves your computer")
