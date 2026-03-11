"""
WAIMS Python - Fetch Real WNBA Data via wehoop
Downloads 2025 season game statistics from ESPN API

Usage:
    python fetch_wehoop_data.py
"""

import pandas as pd
import sqlite3
from datetime import datetime

print("=" * 60)
print("WAIMS - Fetching Real WNBA Game Data")
print("=" * 60)

try:
    from wehoop.wnba import load_wnba_player_box
    print("\n✓ wehoop package found")
except ImportError:
    print("\n❌ wehoop not installed")
    print("Install with: pip install wehoop")
    print("\nContinuing with simulated data only...")
    exit(0)

# ==============================================================================
# FETCH 2025 SEASON DATA
# ==============================================================================

print("\n1. Fetching 2025 WNBA season data from ESPN API...")

try:
    # Get 2025 season player box scores
    games_2025 = load_wnba_player_box(seasons=2025)
    print(f"✓ Retrieved {len(games_2025)} game records from 2025 season")
    
    # Filter to recent games (last 50 days to match our simulated data)
    games_2025['game_date'] = pd.to_datetime(games_2025['game_date'])
    cutoff_date = games_2025['game_date'].max() - pd.Timedelta(days=50)
    recent_games = games_2025[games_2025['game_date'] >= cutoff_date].copy()
    
    print(f"✓ Filtered to {len(recent_games)} games from last 50 days")
    
except Exception as e:
    print(f"❌ Error fetching data: {e}")
    print("Continuing with simulated data only...")
    exit(0)

# ==============================================================================
# PROCESS GAME DATA
# ==============================================================================

print("\n2. Processing game statistics...")

# Calculate game load proxy
recent_games['game_load'] = (
    recent_games['minutes'] * 
    (1 + recent_games['total_rebounds'] / 10 + 
     (recent_games['steals'] + recent_games['blocks']) / 5)
)

# Select relevant columns
game_data = recent_games[[
    'athlete_display_name',
    'team_short_display_name',
    'game_date',
    'minutes',
    'points',
    'total_rebounds',
    'assists',
    'steals',
    'blocks',
    'turnovers',
    'plus_minus',
    'game_load'
]].copy()

game_data = game_data.rename(columns={
    'athlete_display_name': 'player_name',
    'team_short_display_name': 'team',
    'game_date': 'date'
})

print(f"✓ Processed {len(game_data)} game records")

# ==============================================================================
# SAVE TO CSV FOR REFERENCE
# ==============================================================================

print("\n3. Saving wehoop data...")

# Save as CSV
output_file = 'wehoop_2025_games.csv'
game_data.to_csv(output_file, index=False)
print(f"✓ Saved to: {output_file}")

# ==============================================================================
# ADD TO DATABASE (Optional - creates separate table)
# ==============================================================================

print("\n4. Adding to database...")

conn = sqlite3.connect('waims_demo.db')

# Create wehoop_games table
game_data.to_sql('wehoop_games', conn, if_exists='replace', index=False)

print(f"✓ Added 'wehoop_games' table to database")

# Get some stats
conn_check = sqlite3.connect('waims_demo.db')
wehoop_count = pd.read_sql_query("SELECT COUNT(*) as cnt FROM wehoop_games", conn_check).iloc[0]['cnt']
teams = pd.read_sql_query("SELECT DISTINCT team FROM wehoop_games", conn_check)
date_range = pd.read_sql_query("""
    SELECT MIN(date) as start, MAX(date) as end FROM wehoop_games
""", conn_check)

conn.close()
conn_check.close()

# ==============================================================================
# SUMMARY
# ==============================================================================

print("\n" + "=" * 60)
print("WEHOOP DATA INTEGRATION COMPLETE")
print("=" * 60)

print(f"\n📊 Summary:")
print(f"   Records: {wehoop_count}")
print(f"   Teams: {len(teams)}")
print(f"   Date range: {date_range['start'].values[0]} to {date_range['end'].values[0]}")
print(f"\n📁 Files created:")
print(f"   - wehoop_2025_games.csv")
print(f"   - waims_demo.db (updated with wehoop_games table)")

print(f"\n💡 Usage:")
print(f"   The dashboard will now show real game statistics")
print(f"   Run: streamlit run dashboard.py")

print("\n✓ Real WNBA data now integrated!")
print("=" * 60)


