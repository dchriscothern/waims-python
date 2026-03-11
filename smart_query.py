"""
WAIMS - Smart Data Query Interface
Natural language-style queries — pattern matching, no API keys needed.

Supported queries:
  Wellness  — poor sleep · high risk · readiness · tired
  GPS/Load  — high load · low load · accel drop · decel drop · overload
  ACWR      — high acwr · workload
  Injuries  — injuries · hurt
  Position  — guards · forwards · centers · compare positions
  Player    — [name] trends
  Team      — team averages
"""

import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ==============================================================================
# PAGE CONFIG
# ==============================================================================

st.set_page_config(page_title="WAIMS Smart Query", page_icon="🔍", layout="wide")

# ==============================================================================
# DATABASE HELPERS
# ==============================================================================

DB = "waims_demo.db"

def _conn():
    return sqlite3.connect(DB)

def get_latest_date():
    conn = _conn()
    result = pd.read_sql_query("SELECT MAX(date) AS max_date FROM wellness", conn)
    conn.close()
    return result["max_date"].iloc[0]

def _has_gps():
    """Check whether GPS columns exist in training_load."""
    try:
        conn = _conn()
        cols = pd.read_sql_query("PRAGMA table_info(training_load)", conn)["name"].tolist()
        conn.close()
        return "player_load" in cols and "accel_count" in cols
    except Exception:
        return False

HAS_GPS = _has_gps()

def get_all_players():
    conn = _conn()
    df   = pd.read_sql_query("SELECT DISTINCT name FROM players ORDER BY name", conn)
    conn.close()
    return df["name"].tolist()

# ==============================================================================
# WELLNESS QUERIES
# ==============================================================================

def query_poor_sleep(threshold=6.5):
    d = get_latest_date()
    conn = _conn()
    df = pd.read_sql_query(f"""
        SELECT p.name, w.sleep_hours, w.soreness, w.stress, w.date
        FROM wellness w JOIN players p ON w.player_id = p.player_id
        WHERE w.date = '{d}' AND w.sleep_hours < {threshold}
        ORDER BY w.sleep_hours
    """, conn)
    conn.close()
    return df

def query_high_risk():
    d = get_latest_date()
    conn = _conn()
    df = pd.read_sql_query(f"""
        SELECT p.name, w.sleep_hours, w.soreness, a.acwr,
               p.injury_history_count,
               CASE
                   WHEN a.acwr > 1.5      THEN 'High ACWR'
                   WHEN w.sleep_hours < 6.5 THEN 'Poor Sleep'
                   WHEN w.soreness > 7    THEN 'High Soreness'
                   ELSE 'Multiple Factors'
               END AS primary_risk
        FROM wellness w
        JOIN players p ON w.player_id = p.player_id
        LEFT JOIN acwr a ON w.player_id = a.player_id AND w.date = a.date
        WHERE w.date = '{d}'
          AND (a.acwr > 1.5 OR w.sleep_hours < 6.5 OR w.soreness > 7)
        ORDER BY a.acwr DESC
    """, conn)
    conn.close()
    return df

def query_readiness_scores():
    d = get_latest_date()
    conn = _conn()
    df = pd.read_sql_query(f"""
        SELECT p.name, w.sleep_hours, w.soreness, w.stress, w.mood,
               ((w.sleep_hours/8.0*30) +
                ((10-w.soreness)/10.0*25) +
                ((10-w.stress)/10.0*25) +
                (w.mood/10.0*20)) AS readiness_score
        FROM wellness w JOIN players p ON w.player_id = p.player_id
        WHERE w.date = '{d}'
        ORDER BY readiness_score
    """, conn)
    conn.close()
    return df

def query_team_averages():
    d = get_latest_date()
    conn = _conn()
    df = pd.read_sql_query(f"""
        SELECT AVG(sleep_hours) AS avg_sleep, AVG(soreness) AS avg_soreness,
               AVG(stress) AS avg_stress, AVG(mood) AS avg_mood, COUNT(*) AS player_count
        FROM wellness WHERE date = '{d}'
    """, conn)
    conn.close()
    return df

def query_position_comparison():
    d = get_latest_date()
    conn = _conn()
    df = pd.read_sql_query(f"""
        SELECT p.position,
               AVG(w.sleep_hours) AS avg_sleep,
               AVG(w.soreness) AS avg_soreness,
               AVG(w.stress) AS avg_stress,
               AVG(w.mood) AS avg_mood,
               COUNT(*) AS count
        FROM wellness w JOIN players p ON w.player_id = p.player_id
        WHERE w.date = '{d}'
        GROUP BY p.position ORDER BY p.position
    """, conn)
    conn.close()
    return df

def query_by_position(position):
    d = get_latest_date()
    conn = _conn()
    df = pd.read_sql_query(f"""
        SELECT p.name, p.position, w.sleep_hours, w.soreness, w.mood, w.stress
        FROM wellness w JOIN players p ON w.player_id = p.player_id
        WHERE w.date = '{d}' AND p.position = '{position}'
        ORDER BY p.name
    """, conn)
    conn.close()
    return df

def query_injuries(days_back=30):
    cutoff = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    conn = _conn()
    df = pd.read_sql_query(f"""
        SELECT p.name, i.injury_date, i.injury_type, i.days_missed
        FROM injuries i JOIN players p ON i.player_id = p.player_id
        WHERE i.injury_date >= '{cutoff}'
        ORDER BY i.injury_date DESC
    """, conn)
    conn.close()
    return df

def query_high_acwr():
    d = get_latest_date()
    conn = _conn()
    df = pd.read_sql_query(f"""
        SELECT p.name, a.acwr, a.acute_load, a.chronic_load,
               CASE
                   WHEN a.acwr > 1.5 THEN 'High Risk'
                   WHEN a.acwr > 1.3 THEN 'Moderate Risk'
                   WHEN a.acwr < 0.8 THEN 'Detraining'
                   ELSE 'Optimal'
               END AS status
        FROM acwr a JOIN players p ON a.player_id = p.player_id
        WHERE a.date = '{d}' AND a.acwr > 1.3
        ORDER BY a.acwr DESC
    """, conn)
    conn.close()
    return df

def query_player_trends(player_name, days_back=14):
    cutoff = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    conn = _conn()
    df = pd.read_sql_query(f"""
        SELECT w.date, w.sleep_hours, w.soreness, w.stress, w.mood
        FROM wellness w JOIN players p ON w.player_id = p.player_id
        WHERE p.name = '{player_name}' AND w.date >= '{cutoff}'
        ORDER BY w.date
    """, conn)
    conn.close()
    return df

# ==============================================================================
# GPS QUERIES  (only run if GPS columns exist)
# ==============================================================================

def query_gps_today():
    """Return today's GPS metrics for all players, with z-score status."""
    d = get_latest_date()
    conn = _conn()
    df = pd.read_sql_query(f"""
        SELECT p.name, p.position,
               t.player_load, t.accel_count, t.decel_count,
               t.total_distance_km, t.hsr_distance_m, t.sprint_distance_m,
               t.game_minutes, t.practice_minutes, t.practice_rpe
        FROM training_load t JOIN players p ON t.player_id = p.player_id
        WHERE t.date = '{d}'
        ORDER BY t.player_load DESC
    """, conn)
    conn.close()
    return df

def query_gps_history(player_name, days_back=14):
    cutoff = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    conn = _conn()
    df = pd.read_sql_query(f"""
        SELECT t.date, t.player_load, t.accel_count, t.decel_count,
               t.total_distance_km, t.hsr_distance_m
        FROM training_load t JOIN players p ON t.player_id = p.player_id
        WHERE p.name = '{player_name}' AND t.date >= '{cutoff}'
        ORDER BY t.date
    """, conn)
    conn.close()
    return df

def _personal_gps_zscores(today_df):
    """
    Add z-score status columns to today's GPS df using each player's 30-day history.
    Returns df with added columns: load_flag, accel_flag, decel_flag
    """
    cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    d      = get_latest_date()
    conn   = _conn()
    hist   = pd.read_sql_query(f"""
        SELECT t.player_load, t.accel_count, t.decel_count,
               p.name
        FROM training_load t JOIN players p ON t.player_id = p.player_id
        WHERE t.date >= '{cutoff}' AND t.date < '{d}'
    """, conn)
    conn.close()

    baselines = hist.groupby("name").agg(
        load_mean=("player_load", "mean"), load_std=("player_load", "std"),
        accel_mean=("accel_count", "mean"), accel_std=("accel_count", "std"),
        decel_mean=("decel_count", "mean"), decel_std=("decel_count", "std"),
    ).reset_index()
    baselines["load_std"]  = baselines["load_std"].clip(lower=5)
    baselines["accel_std"] = baselines["accel_std"].clip(lower=1)
    baselines["decel_std"] = baselines["decel_std"].clip(lower=1)

    merged = today_df.merge(baselines, on="name", how="left")

    def _flag(val, mean, std):
        if pd.isna(mean) or pd.isna(std):
            return "🟡"
        z = (val - mean) / std
        return "🔴" if z <= -2 else ("🟡" if z <= -1 else "🟢")

    merged["load_flag"]  = merged.apply(lambda r: _flag(r["player_load"],  r["load_mean"],  r["load_std"]),  axis=1)
    merged["accel_flag"] = merged.apply(lambda r: _flag(r["accel_count"], r["accel_mean"], r["accel_std"]), axis=1)
    merged["decel_flag"] = merged.apply(lambda r: _flag(r["decel_count"], r["decel_mean"], r["decel_std"]), axis=1)
    return merged

# ==============================================================================
# PATTERN MATCHING
# ==============================================================================

def parse_query(user_input):
    u = user_input.lower().strip()

    # GPS queries
    if HAS_GPS:
        if any(w in u for w in ["high load", "overload", "player load"]):
            return "gps_high_load", {}
        if any(w in u for w in ["low load", "load drop", "low gps"]):
            return "gps_low_load", {}
        if any(w in u for w in ["accel drop", "low accel", "acceleration drop"]):
            return "gps_accel_drop", {}
        if any(w in u for w in ["decel drop", "low decel", "deceleration drop"]):
            return "gps_decel_drop", {}
        if any(w in u for w in ["gps today", "gps data", "kinexon", "today's gps"]):
            return "gps_today", {}

    # Wellness
    if any(w in u for w in ["poor sleep", "bad sleep", "tired", "not sleeping"]):
        return "poor_sleep", {}
    if any(w in u for w in ["high risk", "at risk", "injury risk", "risky"]):
        return "high_risk", {}
    if any(w in u for w in ["readiness", "ready", "who can play"]):
        return "readiness", {}
    if any(w in u for w in ["acwr", "workload", "overloaded", "training load"]):
        return "high_acwr", {}
    if any(w in u for w in ["injury", "injuries", "hurt", "injured"]):
        return "injuries", {}

    # Position
    if "guard" in u:
        return "position", {"position": "G"}
    if "forward" in u:
        return "position", {"position": "F"}
    if "center" in u:
        return "position", {"position": "C"}
    if any(w in u for w in ["compare position", "position comparison"]):
        return "position_comparison", {}

    # Team
    if any(w in u for w in ["team average", "average", "overall team"]):
        return "team_averages", {}

    # Player-specific
    for player in get_all_players():
        if player.lower() in u:
            if any(w in u for w in ["trend", "history", "over time", "gps"]):
                return "player_trends", {"player_name": player}
            return "player_info", {"player_name": player}

    return "unknown", {}

# ==============================================================================
# RESPONSE GENERATION
# ==============================================================================

def generate_response(query_type, params):

    # ── GPS responses ──────────────────────────────────────────────────────────
    if query_type == "gps_today":
        df = query_gps_today()
        if len(df) == 0:
            return "No GPS data for today.", None
        flagged = _personal_gps_zscores(df)
        st.subheader("📡 GPS / Kinexon — Today")
        display_cols = ["name", "position", "load_flag", "player_load",
                        "accel_flag", "accel_count", "decel_flag", "decel_count",
                        "total_distance_km", "hsr_distance_m"]
        available = [c for c in display_cols if c in flagged.columns]
        st.dataframe(flagged[available].rename(columns={
            "load_flag": "Load", "accel_flag": "Accel", "decel_flag": "Decel"
        }), width='stretch')
        response = f"Today's GPS data for {len(df)} athletes. 🔴 = > 2σ below personal baseline  ·  🟡 = > 1σ below"
        return response, flagged

    if query_type in ("gps_high_load", "gps_low_load", "gps_accel_drop", "gps_decel_drop"):
        df = query_gps_today()
        if len(df) == 0:
            return "No GPS data for today.", None
        flagged = _personal_gps_zscores(df)

        if query_type == "gps_high_load":
            subset = flagged[flagged["player_load"] > flagged["player_load"].median()]
            title  = "High Player Load — Today"
            note   = "Players above team median load today."
        elif query_type == "gps_low_load":
            subset = flagged[flagged["load_flag"].isin(["🔴", "🟡"])]
            title  = "Low Player Load (vs Personal Baseline) — Today"
            note   = "Players showing load drops vs their personal 30-day norm."
        elif query_type == "gps_accel_drop":
            subset = flagged[flagged["accel_flag"].isin(["🔴", "🟡"])]
            title  = "Accel Count Drop (vs Personal Baseline) — Today"
            note   = "May indicate protective movement — early fatigue signal."
        else:
            subset = flagged[flagged["decel_flag"].isin(["🔴", "🟡"])]
            title  = "Decel Count Drop (vs Personal Baseline) — Today"
            note   = "Reduced direction-change braking — watch for injury risk."

        if len(subset) == 0:
            return f"✅ No athletes flagged for {title.split('—')[0].strip()}.", None

        st.subheader(f"📡 {title}")
        st.caption(note)
        display_cols = ["name", "position", "player_load", "load_flag",
                        "accel_count", "accel_flag", "decel_count", "decel_flag"]
        available = [c for c in display_cols if c in subset.columns]
        st.dataframe(subset[available], width='stretch')

        fig = go.Figure(go.Bar(
            x=subset["name"], y=subset["player_load"],
            marker_color=subset["load_flag"].map({"🟢": "#10b981", "🟡": "#f59e0b", "🔴": "#ef4444"}),
            text=subset["player_load"].apply(lambda v: f"{v:.0f}"),
            textposition="outside",
        ))
        fig.update_layout(title="Player Load", height=280,
                          yaxis=dict(title="AU"), margin=dict(t=40, b=10))
        st.plotly_chart(fig, width='stretch')

        response = f"**{len(subset)} athletes** flagged. 🔴 = severe drop (>2σ)  ·  🟡 = moderate drop (>1σ)"
        return response, subset

    # ── Wellness responses ─────────────────────────────────────────────────────
    if query_type == "poor_sleep":
        df = query_poor_sleep()
        if len(df) == 0:
            return "✅ No players had poor sleep (<6.5 hrs) last night.", None
        st.subheader(f"⚠️ {len(df)} Players with Poor Sleep")
        st.dataframe(df, width='stretch')
        response = f"**{len(df)} players** had poor sleep:\n\n"
        for _, r in df.iterrows():
            response += f"- **{r['name']}**: {r['sleep_hours']:.1f} hrs · Soreness {r['soreness']}/10\n"
        response += "\n📚 **Research:** Sleep <6.5 hrs → 1.7× injury risk (Milewski 2014)"
        return response, df

    if query_type == "high_risk":
        df = query_high_risk()
        if len(df) == 0:
            return "✅ No players currently showing high injury risk indicators.", None
        st.subheader(f"🚨 {len(df)} Players at Elevated Risk")
        st.dataframe(df, width='stretch')
        response = f"**{len(df)} players** showing elevated risk:\n\n"
        for _, r in df.iterrows():
            response += f"- **{r['name']}** ({r['primary_risk']}) — ACWR {r['acwr']:.2f} · Sleep {r['sleep_hours']:.1f} hrs\n"
        response += "\n💡 Consider modified training or rest day"
        return response, df

    if query_type == "readiness":
        df = query_readiness_scores()
        st.subheader("📊 Readiness Scores")
        st.dataframe(df, width='stretch')
        green  = len(df[df["readiness_score"] >= 80])
        yellow = len(df[(df["readiness_score"] >= 60) & (df["readiness_score"] < 80)])
        red    = len(df[df["readiness_score"] < 60])
        response = f"🟢 Ready: **{green}**  ·  🟡 Monitor: **{yellow}**  ·  🔴 At Risk: **{red}**"
        return response, df

    if query_type == "high_acwr":
        df = query_high_acwr()
        if len(df) == 0:
            return "✅ All players have ACWR in optimal range (0.8–1.3).", None
        st.subheader(f"⚠️ {len(df)} Players with Elevated ACWR")
        st.dataframe(df, width='stretch')
        response = f"**{len(df)} players** with ACWR > 1.3:\n\n"
        for _, r in df.iterrows():
            response += f"- **{r['name']}**: ACWR {r['acwr']:.2f} ({r['status']})\n"
        response += "\n📚 **Research:** ACWR >1.5 = 2.4× injury risk (Gabbett 2016)"
        return response, df

    if query_type == "injuries":
        df = query_injuries()
        if len(df) == 0:
            return "✅ No injuries recorded in the past 30 days.", None
        st.subheader("🏥 Recent Injuries (Past 30 Days)")
        st.dataframe(df, width='stretch')
        response = f"**{len(df)} injuries** in past 30 days:\n\n"
        for _, r in df.iterrows():
            response += f"- **{r['name']}**: {r['injury_type']} ({r['days_missed']} days) — {r['injury_date']}\n"
        return response, df

    if query_type == "position":
        pos       = params["position"]
        df        = query_by_position(pos)
        pos_names = {"G": "Guards", "F": "Forwards", "C": "Centers"}
        st.subheader(f"📊 {pos_names[pos]}")
        st.dataframe(df, width='stretch')
        response = f"**{pos_names[pos]}** ({len(df)} players):\n- Avg sleep: {df['sleep_hours'].mean():.1f} hrs\n- Avg soreness: {df['soreness'].mean():.1f}/10"
        return response, df

    if query_type == "position_comparison":
        df = query_position_comparison()
        st.subheader("📊 Position Comparison")
        fig = px.bar(df, x="position", y=["avg_sleep", "avg_soreness", "avg_stress"],
                     barmode="group", title="Metrics by Position")
        st.plotly_chart(fig, width='stretch')
        st.dataframe(df, width='stretch')
        return "Position comparison complete.", df

    if query_type == "team_averages":
        df  = query_team_averages()
        row = df.iloc[0]
        response = (
            f"**Team Averages** ({row['player_count']} players):\n"
            f"- Sleep: {row['avg_sleep']:.1f} hrs\n"
            f"- Soreness: {row['avg_soreness']:.1f}/10\n"
            f"- Stress: {row['avg_stress']:.1f}/10\n"
            f"- Mood: {row['avg_mood']:.1f}/10"
        )
        return response, df

    if query_type == "player_trends":
        name = params["player_name"]
        df   = query_player_trends(name)
        if len(df) == 0:
            return f"No recent data for {name}.", None
        st.subheader(f"📈 Wellness Trends — {name}")
        fig = px.line(df, x="date", y=["sleep_hours", "soreness", "stress", "mood"],
                      title=f"{name} — 14-Day Wellness")
        st.plotly_chart(fig, width='stretch')

        if HAS_GPS:
            gps_df = query_gps_history(name)
            if len(gps_df) > 0:
                st.subheader(f"📡 GPS Trends — {name}")
                fig2 = go.Figure()
                fig2.add_trace(go.Scatter(x=gps_df["date"], y=gps_df["player_load"],
                                          name="Player Load", mode="lines+markers",
                                          line=dict(color="#2E86AB", width=2)))
                fig2.add_trace(go.Scatter(x=gps_df["date"], y=gps_df["accel_count"],
                                          name="Accel Count", mode="lines+markers",
                                          line=dict(color="#A23B72", width=2), yaxis="y2"))
                fig2.add_trace(go.Scatter(x=gps_df["date"], y=gps_df["decel_count"],
                                          name="Decel Count", mode="lines+markers",
                                          line=dict(color="#F18F01", width=2, dash="dot"), yaxis="y2"))
                fig2.update_layout(
                    height=280,
                    yaxis =dict(title="Player Load (AU)"),
                    yaxis2=dict(title="Accel / Decel", overlaying="y", side="right"),
                    hovermode="x unified",
                    margin=dict(l=10, r=10, t=20, b=30),
                    legend=dict(orientation="h", y=-0.3),
                )
                st.plotly_chart(fig2, width='stretch')

        response = f"**{name}** — 14-day avg: Sleep {df['sleep_hours'].mean():.1f} hrs · Soreness {df['soreness'].mean():.1f}/10"
        return response, df

    # Unknown
    gps_examples = (
        "\n**GPS / Load:**\n- 'gps today'\n- 'high load'\n- 'low load'\n- 'accel drop'\n- 'decel drop'"
        if HAS_GPS else ""
    )
    return f"""❓ I didn't understand that. Try:

**Wellness:**
- "poor sleep"  ·  "high risk"  ·  "readiness"  ·  "injuries"
{gps_examples}
**ACWR / Load:**
- "high acwr"  ·  "workload"

**Position:**
- "guards"  ·  "forwards"  ·  "compare positions"

**Player:**
- "[name] trends"
""", None

# ==============================================================================
# UI
# ==============================================================================

st.title("🔍 WAIMS Smart Query Interface")
st.markdown("Ask questions about your data — instant answers, no API keys needed.")

if not HAS_GPS:
    st.warning("⚠️ GPS columns not found in database. Run `python generate_database.py` to add GPS data.")

with st.sidebar:
    st.header("💡 How to Use")
    st.markdown("Type naturally:\n- 'Who's tired?'\n- 'accel drop'\n- 'high load'\n- 'ATH_001 trends'")
    st.divider()
    st.header("⚡ Quick Queries")

    quick = {
        "🌙 Poor Sleep":         "poor sleep",
        "🚨 High Risk":          "high risk",
        "✅ Readiness Scores":   "readiness",
        "💪 High ACWR":          "high acwr",
        "🏥 Recent Injuries":    "injuries",
        "📊 Position Comparison": "compare positions",
        "📈 Team Averages":      "team averages",
    }
    if HAS_GPS:
        quick.update({
            "📡 GPS Today":      "gps today",
            "⬇️ Low Load":       "low load",
            "⬇️ Accel Drop":     "accel drop",
            "⬇️ Decel Drop":     "decel drop",
        })

    for label, q in quick.items():
        if st.button(label, width='stretch'):
            st.session_state.query = q

    st.divider()
    st.caption("⚡ Instant  ·  💰 $0  ·  🔒 Local")

if "query" not in st.session_state:
    st.session_state.query = ""

query_input = st.text_input(
    "Ask a question:",
    placeholder="e.g. 'poor sleep'  ·  'accel drop'  ·  'gps today'",
)

if st.session_state.query:
    query_input = st.session_state.query
    st.session_state.query = ""

if query_input:
    st.divider()
    query_type, params = parse_query(query_input)
    st.info(f"🔍 Understood as: **{query_type.replace('_', ' ').title()}**")
    response, data = generate_response(query_type, params)
    st.markdown(response)

    if data is not None and len(data) > 0:
        st.divider()
        st.download_button(
            "📥 Download Results (CSV)",
            data=data.to_csv(index=False),
            file_name=f"waims_query_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
        )

st.divider()
st.caption("🔐 100% Local — your data never leaves your computer")



