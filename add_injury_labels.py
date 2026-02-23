"""
WAIMS Python - Add Public Injury Labels
Integrates publicly reported WNBA injuries into the training dataset

This script shows you how to add real injury data from public sources.

IMPORTANT: Only use publicly available information!
- WNBA official injury reports
- Team press releases  
- Box score DNP-Injury listings
- ProSportsTransactions.com

DO NOT use protected health information or internal team data.

Usage:
    1. Create injuries.csv with public injury data
    2. Run: python add_injury_labels.py
"""

import pandas as pd
import sqlite3
from datetime import datetime, timedelta

print("=" * 70)
print("WAIMS - ADD PUBLIC INJURY LABELS")
print("=" * 70)

# ==============================================================================
# STEP 1: LOAD PUBLIC INJURY DATA
# ==============================================================================

print("\n" + "=" * 70)
print("STEP 1: Loading public injury data...")
print("=" * 70)

# Check if injury file exists
import os
if not os.path.exists('public_injuries.csv'):
    print("\n❌ File not found: public_injuries.csv")
    print("\nCreate this file first with the following format:")
    print("""
player_name,injury_date,injury_type,days_missed,source
Satou Sabally,2024-08-15,Shoulder,14,WNBA Official Report
Arike Ogunbowale,2024-07-22,Ankle,3,Dallas Wings Press Release
Breanna Stewart,2024-06-10,Foot,7,WNBA Injury Report
    """)
    print("\n📋 Required columns:")
    print("  - player_name: Full name as it appears in box scores")
    print("  - injury_date: YYYY-MM-DD format")
    print("  - injury_type: Ankle, Knee, Shoulder, etc.")
    print("  - days_missed: Number of games missed")
    print("  - source: Where you found this information")
    
    print("\n💡 Example sources:")
    print("  - WNBA Official Injury Report")
    print("  - Team Press Release")
    print("  - ProSportsTransactions.com")
    print("  - ESPN Injury Report")
    
    print("\n⚠️  ONLY PUBLIC DATA!")
    print("  ✓ Publicly reported injuries")
    print("  ✓ Official team announcements")
    print("  ✗ Medical records")
    print("  ✗ Internal team data")
    
    # Create example file
    example = pd.DataFrame({
        'player_name': ['Example Player'],
        'injury_date': ['2024-06-15'],
        'injury_type': ['Ankle'],
        'days_missed': [7],
        'source': ['WNBA Official Report']
    })
    example.to_csv('public_injuries_EXAMPLE.csv', index=False)
    print(f"\n✓ Created example file: public_injuries_EXAMPLE.csv")
    print("  Edit this file with real public injury data, then rename to public_injuries.csv")
    
    import sys
    sys.exit(0)

# Load injury data
injuries = pd.read_csv('public_injuries.csv')
print(f"✓ Loaded {len(injuries)} injury records")

# Validate columns
required_cols = ['player_name', 'injury_date', 'injury_type', 'days_missed', 'source']
missing = [col for col in required_cols if col not in injuries.columns]
if missing:
    print(f"\n❌ Missing required columns: {missing}")
    print(f"Required: {required_cols}")
    import sys
    sys.exit(1)

# Convert dates
injuries['injury_date'] = pd.to_datetime(injuries['injury_date'])

print(f"\n📊 Injury data summary:")
print(f"  Players affected: {injuries['player_name'].nunique()}")
print(f"  Date range: {injuries['injury_date'].min().date()} to {injuries['injury_date'].max().date()}")
print(f"  Injury types: {injuries['injury_type'].nunique()} ({', '.join(injuries['injury_type'].unique()[:5])}...)")
print(f"  Total days missed: {injuries['days_missed'].sum()}")

# ==============================================================================
# STEP 2: LOAD GAME DATA
# ==============================================================================

print("\n" + "=" * 70)
print("STEP 2: Loading game data...")
print("=" * 70)

conn = sqlite3.connect('waims_demo.db')

# Check if wehoop data exists
tables = pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table'", conn)
if 'wehoop_all_teams' not in tables['name'].values:
    print("\n❌ Table not found: wehoop_all_teams")
    print("Run this first: python fetch_all_wnba_data.py")
    import sys
    sys.exit(1)

games = pd.read_sql_query("SELECT * FROM wehoop_all_teams", conn)
games['game_date'] = pd.to_datetime(games['game_date'])

print(f"✓ Loaded {len(games)} game records")

# ==============================================================================
# STEP 3: CREATE INJURY LABELS
# ==============================================================================

print("\n" + "=" * 70)
print("STEP 3: Creating injury labels...")
print("=" * 70)

# Create injury label for each game
# Label = 1 if player gets injured in next 7 days, 0 otherwise

print("Labeling games with injury risk...")

games['injured_within_7days'] = 0

label_count = 0

for idx, injury in injuries.iterrows():
    player = injury['player_name']
    injury_date = injury['injury_date']
    
    # Find games for this player in 7 days before injury
    lookback_date = injury_date - timedelta(days=7)
    
    mask = (
        (games['athlete_display_name'] == player) &
        (games['game_date'] >= lookback_date) &
        (games['game_date'] < injury_date)
    )
    
    games.loc[mask, 'injured_within_7days'] = 1
    labels_added = mask.sum()
    label_count += labels_added
    
    if labels_added > 0:
        print(f"  ✓ {player}: {labels_added} games labeled before {injury_date.date()}")

print(f"\n✓ Created labels:")
print(f"  Games with injury risk: {games['injured_within_7days'].sum()}")
print(f"  Games without injury: {(games['injured_within_7days'] == 0).sum()}")
print(f"  Injury rate: {(games['injured_within_7days'].sum() / len(games)) * 100:.2f}%")

# ==============================================================================
# STEP 4: SAVE TO DATABASE
# ==============================================================================

print("\n" + "=" * 70)
print("STEP 4: Saving labeled data...")
print("=" * 70)

# Update database
games.to_sql('wehoop_all_teams', conn, if_exists='replace', index=False)

print("✓ Updated wehoop_all_teams table with injury labels")

# Also save as CSV
games.to_csv('games_with_injury_labels.csv', index=False)
print("✓ Saved backup: games_with_injury_labels.csv")

conn.close()

# ==============================================================================
# STEP 5: SUMMARY & NEXT STEPS
# ==============================================================================

print("\n" + "=" * 70)
print("✅ INJURY LABELING COMPLETE!")
print("=" * 70)

print(f"\n📊 Final Dataset:")
print(f"   Total games: {len(games):,}")
print(f"   Injury cases: {games['injured_within_7days'].sum()}")
print(f"   Non-injury cases: {(games['injured_within_7days'] == 0).sum()}")
print(f"   Injury rate: {(games['injured_within_7days'].sum() / len(games)) * 100:.2f}%")

print(f"\n🎯 Next Steps:")
print(f"   1. Train ML model on real injury patterns")
print(f"      → python train_models_multiteam.py")
print(f"   2. Model will learn from {injuries['player_name'].nunique()} real injury events")
print(f"   3. Much more accurate predictions!")

print(f"\n📚 What You Used:")
for source in injuries['source'].unique():
    count = (injuries['source'] == source).sum()
    print(f"   - {source}: {count} injuries")

print("\n" + "=" * 70)
