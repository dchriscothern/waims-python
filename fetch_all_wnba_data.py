"""
WAIMS Python - Multi-Team WNBA Data Pipeline
Fetches game data for ALL 12 WNBA teams across multiple seasons

This creates a much larger, more robust training dataset for ML models.

Usage:
    python fetch_all_wnba_data.py
"""

import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import sys

print("=" * 70)
print("WAIMS - MULTI-TEAM WNBA DATA PIPELINE")
print("=" * 70)

# ==============================================================================
# CONFIGURATION
# ==============================================================================

SEASONS = [2023, 2024, 2025]  # Years to fetch
ALL_TEAMS = [
    'ATL',  # Atlanta Dream
    'CHI',  # Chicago Sky
    'CON',  # Connecticut Sun
    'DAL',  # Dallas Wings
    'IND',  # Indiana Fever
    'LA',   # Los Angeles Sparks
    'LV',   # Las Vegas Aces
    'MIN',  # Minnesota Lynx
    'NY',   # New York Liberty
    'PHX',  # Phoenix Mercury
    'SEA',  # Seattle Storm
    'WAS'   # Washington Mystics
]

print(f"\nConfiguration:")
print(f"  Seasons: {SEASONS}")
print(f"  Teams: {len(ALL_TEAMS)} (all WNBA)")
print(f"  Expected records: ~17,000 player-games")

# ==============================================================================
# STEP 1: CHECK WEHOOP AVAILABILITY
# ==============================================================================

print("\n" + "=" * 70)
print("STEP 1: Checking wehoop package...")
print("=" * 70)

try:
    from wehoop.wnba import load_wnba_player_box
    print("✓ wehoop package found")
except ImportError:
    print("\n❌ wehoop not installed!")
    print("\nInstall with:")
    print("  pip install wehoop")
    print("\nExiting...")
    sys.exit(1)

# ==============================================================================
# STEP 2: FETCH GAME DATA
# ==============================================================================

print("\n" + "=" * 70)
print("STEP 2: Fetching WNBA game data from ESPN API...")
print("=" * 70)

all_games = []

for season in SEASONS:
    print(f"\n📅 Season {season}:")
    
    try:
        # Fetch all games for this season
        games = load_wnba_player_box(seasons=season)
        
        print(f"  ✓ Retrieved {len(games)} player-game records")
        
        # Filter to valid teams (some records may have bad data)
        games = games[games['team_short_display_name'].isin(ALL_TEAMS)]
        
        print(f"  ✓ Filtered to {len(games)} valid records")
        
        all_games.append(games)
        
    except Exception as e:
        print(f"  ❌ Error fetching {season}: {e}")
        print(f"  Continuing with other seasons...")
        continue

if len(all_games) == 0:
    print("\n❌ No data fetched! Check your internet connection.")
    sys.exit(1)

# Combine all seasons
print(f"\n📊 Combining data from {len(all_games)} seasons...")
df_games = pd.concat(all_games, ignore_index=True)

print(f"✓ Total records: {len(df_games)}")
print(f"  Date range: {df_games['game_date'].min()} to {df_games['game_date'].max()}")
print(f"  Unique players: {df_games['athlete_display_name'].nunique()}")
print(f"  Teams: {df_games['team_short_display_name'].nunique()}")

# ==============================================================================
# STEP 3: FEATURE ENGINEERING
# ==============================================================================

print("\n" + "=" * 70)
print("STEP 3: Engineering features...")
print("=" * 70)

# Convert date
df_games['game_date'] = pd.to_datetime(df_games['game_date'])

# Calculate game load proxy
df_games['game_load'] = (
    df_games['minutes'] * 
    (1 + df_games['total_rebounds'] / 10 + 
     (df_games['steals'] + df_games['blocks']) / 5)
)

# Sort by player and date
df_games = df_games.sort_values(['athlete_display_name', 'game_date'])

print("Creating schedule features...")

# Feature 1: Days since last game
df_games['days_since_last_game'] = df_games.groupby('athlete_display_name')['game_date'].diff().dt.days
df_games['days_since_last_game'] = df_games['days_since_last_game'].fillna(999)

# Feature 2: Back-to-back games
df_games['back_to_back'] = (df_games['days_since_last_game'] == 1).astype(int)

# Feature 3: Games in last 7 days
df_games['games_in_7d'] = df_games.groupby('athlete_display_name')['game_date'].transform(
    lambda x: x.rolling('7D', on=x).count()
)

# Feature 4: Minutes trend (7-game rolling average)
df_games['minutes_7game_avg'] = df_games.groupby('athlete_display_name')['minutes'].transform(
    lambda x: x.rolling(7, min_periods=1).mean()
)

# Feature 5: Load trend
df_games['load_7game_avg'] = df_games.groupby('athlete_display_name')['game_load'].transform(
    lambda x: x.rolling(7, min_periods=1).mean()
)

print("✓ Created schedule features:")
print("  - days_since_last_game")
print("  - back_to_back")
print("  - games_in_7d")
print("  - minutes_7game_avg")
print("  - load_7game_avg")

# ==============================================================================
# STEP 4: SAVE TO DATABASE
# ==============================================================================

print("\n" + "=" * 70)
print("STEP 4: Saving to database...")
print("=" * 70)

conn = sqlite3.connect('waims_demo.db')

# Save as new table
df_games.to_sql('wehoop_all_teams', conn, if_exists='replace', index=False)

print(f"✓ Created table: wehoop_all_teams")
print(f"  Records: {len(df_games)}")

# ==============================================================================
# STEP 5: SAVE TO CSV (BACKUP)
# ==============================================================================

print("\n" + "=" * 70)
print("STEP 5: Creating CSV backup...")
print("=" * 70)

csv_file = 'wehoop_all_teams_2023-2025.csv'
df_games.to_csv(csv_file, index=False)

print(f"✓ Saved: {csv_file}")
print(f"  Size: {len(df_games)} rows × {len(df_games.columns)} columns")

# ==============================================================================
# STEP 6: SUMMARY STATISTICS
# ==============================================================================

print("\n" + "=" * 70)
print("SUMMARY STATISTICS")
print("=" * 70)

# Team breakdown
team_counts = df_games.groupby('team_short_display_name').size().sort_values(ascending=False)
print("\n📊 Records by Team:")
for team, count in team_counts.items():
    print(f"  {team}: {count}")

# Back-to-back stats
b2b_count = df_games['back_to_back'].sum()
b2b_pct = (b2b_count / len(df_games)) * 100
print(f"\n🔄 Back-to-Back Games:")
print(f"  Total: {b2b_count} ({b2b_pct:.1f}% of games)")

# Minutes distribution
print(f"\n⏱️  Minutes Played:")
print(f"  Mean: {df_games['minutes'].mean():.1f}")
print(f"  Median: {df_games['minutes'].median():.1f}")
print(f"  Max: {df_games['minutes'].max():.1f}")

# Game load distribution
print(f"\n💪 Game Load:")
print(f"  Mean: {df_games['game_load'].mean():.1f}")
print(f"  Median: {df_games['game_load'].median():.1f}")
print(f"  75th percentile: {df_games['game_load'].quantile(0.75):.1f}")

conn.close()

# ==============================================================================
# STEP 7: INJURY DATA GUIDANCE
# ==============================================================================

print("\n" + "=" * 70)
print("NEXT STEP: ADD INJURY DATA")
print("=" * 70)

print("""
You now have game data for ALL WNBA teams (2023-2025).
To complete the training dataset, you need injury labels.

📋 Public Injury Data Sources:

1. WNBA Official Injury Reports
   - URL: wnba.com/news/injury-report
   - Updated before every game
   - Shows: Out, Questionable, Doubtful status
   
2. ProSportsTransactions
   - URL: prosportstransactions.com/basketball
   - Searchable by team/player/date
   - Cross-reference with official reports

3. Team Websites
   - Each team posts injury updates
   - Check news/press releases sections

⚠️  IMPORTANT - Only Use Public Data:
   ✓ Publicly reported injuries (dates, general type)
   ✓ DNP-Injury from box scores
   ✓ Official team announcements
   ✗ Medical records (HIPAA protected)
   ✗ Internal team data (confidential)

📝 Next Steps:
   1. Compile public injury reports for 2023-2025
   2. Create injuries.csv with columns:
      - player_name
      - injury_date
      - injury_type (ankle, knee, etc.)
      - days_missed
   3. Run: python add_injury_labels.py
   4. Retrain model with real injury patterns!

💡 Estimated Injuries (2023-2025):
   - ~15-20 injuries per team per season
   - 12 teams × 3 seasons × 15 = ~540 injuries
   - Much better training data than 8 simulated injuries!
""")

# ==============================================================================
# FINAL SUMMARY
# ==============================================================================

print("\n" + "=" * 70)
print("✅ MULTI-TEAM DATA FETCH COMPLETE!")
print("=" * 70)

print(f"\n📊 What You Have:")
print(f"   Database table: wehoop_all_teams")
print(f"   CSV backup: {csv_file}")
print(f"   Total records: {len(df_games):,}")
print(f"   Players: {df_games['athlete_display_name'].nunique()}")
print(f"   Teams: {len(ALL_TEAMS)}")
print(f"   Seasons: {len(SEASONS)}")
print(f"   Date range: {df_games['game_date'].min().strftime('%Y-%m-%d')} to {df_games['game_date'].max().strftime('%Y-%m-%d')}")

print(f"\n🎯 Next Actions:")
print(f"   1. Add public injury data (see guidance above)")
print(f"   2. Run: python train_models_multiteam.py")
print(f"   3. Much better ML model with real patterns!")

print("\n" + "=" * 70)
