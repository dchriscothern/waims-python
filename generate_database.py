"""
WAIMS Python Demo - Data Generation Script
Generates 50 days of realistic WNBA athlete monitoring data

Creates SQLite database with:
- 12 players (2025 Wings roster simulation)
- 50 days of wellness, training load, force plate data
- 5 injury events with realistic warning signs
- Ready for ML training and dashboard visualization
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Set random seed for reproducibility
np.random.seed(42)

print("=" * 60)
print("WAIMS - Generating Athlete Monitoring Database")
print("=" * 60)

# ==============================================================================
# 1. CREATE DATABASE AND SCHEMA
# ==============================================================================

print("\n1. Creating database schema...")

conn = sqlite3.connect('waims_demo.db')
cursor = conn.cursor()

# Players table
cursor.execute('''
CREATE TABLE IF NOT EXISTS players (
    player_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    position TEXT,
    age INTEGER,
    injury_history_count INTEGER,
    status_active INTEGER DEFAULT 1
)
''')

# Wellness table (daily subjective measures)
cursor.execute('''
CREATE TABLE IF NOT EXISTS wellness (
    wellness_id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id TEXT,
    date DATE,
    sleep_hours REAL,
    sleep_quality INTEGER,
    soreness INTEGER,
    stress INTEGER,
    mood INTEGER,
    FOREIGN KEY (player_id) REFERENCES players(player_id)
)
''')

# Training load table (daily external load)
cursor.execute('''
CREATE TABLE IF NOT EXISTS training_load (
    load_id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id TEXT,
    date DATE,
    practice_minutes REAL,
    practice_rpe INTEGER,
    strength_volume REAL,
    game_minutes REAL,
    FOREIGN KEY (player_id) REFERENCES players(player_id)
)
''')

# Force plate table (weekly neuromuscular testing)
cursor.execute('''
CREATE TABLE IF NOT EXISTS force_plate (
    test_id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id TEXT,
    date DATE,
    cmj_height_cm REAL,
    asymmetry_percent REAL,
    rsi_modified REAL,
    FOREIGN KEY (player_id) REFERENCES players(player_id)
)
''')

# ACWR table (acute:chronic workload ratio)
cursor.execute('''
CREATE TABLE IF NOT EXISTS acwr (
    acwr_id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id TEXT,
    date DATE,
    acwr REAL,
    acute_load REAL,
    chronic_load REAL,
    FOREIGN KEY (player_id) REFERENCES players(player_id)
)
''')

# Injuries table
cursor.execute('''
CREATE TABLE IF NOT EXISTS injuries (
    injury_id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id TEXT,
    injury_date DATE,
    injury_type TEXT,
    days_missed INTEGER,
    FOREIGN KEY (player_id) REFERENCES players(player_id)
)
''')

conn.commit()
print("✓ Database schema created")

# ==============================================================================
# 2. GENERATE ROSTER (2025 Wings simulation)
# ==============================================================================

print("\n2. Generating player roster...")

players = pd.DataFrame({
    'player_id': [f'P{i:03d}' for i in range(1, 13)],
    'name': [
        'Paige Bueckers',      # P001 - Franchise player
        'Arike Ogunbowale',    # P002 - Veteran guard
        'Satou Sabally',       # P003 - All-Star forward
        'Teaira McCowan',      # P004 - Starting center
        'Natasha Howard',      # P005 - Rotation forward
        'Maddy Siegrist',      # P006 - Rising star
        'Jacy Sheldon',        # P007 - Rotation guard
        'Lou Lopez Senechal',  # P008 - Bench guard
        'Stephanie Soares',    # P009 - Backup center
        'Jaelyn Brown',        # P010 - Young prospect
        'Kalani Brown',        # P011 - Rotation forward
        'Monique Billings'     # P012 - Versatile forward
    ],
    'position': ['G', 'G', 'F', 'C', 'F', 'F', 'G', 'G', 'C', 'G', 'F', 'F'],
    'age': [23, 28, 27, 28, 32, 24, 24, 23, 26, 22, 29, 31],
    'injury_history_count': [3, 1, 4, 2, 3, 1, 1, 0, 1, 0, 2, 1],
    'status_active': [1] * 12
})

players.to_sql('players', conn, if_exists='replace', index=False)
print(f"✓ Created roster: {len(players)} players")

# ==============================================================================
# 3. GENERATE TIME SERIES DATA (50 days)
# ==============================================================================

print("\n3. Generating 50 days of monitoring data...")

# Date range (ending today)
end_date = datetime.now().date()
start_date = end_date - timedelta(days=49)
dates = pd.date_range(start=start_date, end=end_date, freq='D')

print(f"   Date range: {start_date} to {end_date}")

# ==============================================================================
# 4. WELLNESS DATA
# ==============================================================================

print("\n4. Generating wellness data...")

wellness_data = []

for player_id in players['player_id']:
    injury_history = players[players['player_id'] == player_id]['injury_history_count'].values[0]
    
    for i, date in enumerate(dates):
        # Progressive fatigue through season
        fatigue_factor = i / len(dates)
        
        # Base values with individual variation
        base_sleep = 7.5 - (fatigue_factor * 1.0) + np.random.normal(0, 0.5)
        sleep_hours = np.clip(base_sleep, 5.0, 9.5)
        
        base_soreness = 3 + (injury_history * 0.5) + (fatigue_factor * 2) + np.random.normal(0, 1.5)
        soreness = int(np.clip(base_soreness, 0, 10))
        
        wellness_data.append({
            'player_id': player_id,
            'date': date.date(),
            'sleep_hours': round(sleep_hours, 1),
            'sleep_quality': np.random.randint(5, 11),
            'soreness': soreness,
            'stress': np.random.randint(2, 8),
            'mood': np.random.randint(5, 10)
        })

wellness_df = pd.DataFrame(wellness_data)
wellness_df.to_sql('wellness', conn, if_exists='replace', index=False)
print(f"✓ Created {len(wellness_df)} wellness records")

# ==============================================================================
# 5. TRAINING LOAD DATA
# ==============================================================================

print("\n5. Generating training load data...")

load_data = []

for player_id in players['player_id']:
    position = players[players['player_id'] == player_id]['position'].values[0]
    
    # Starters get more minutes
    is_starter = players[players['player_id'] == player_id].index[0] < 4
    
    for i, date in enumerate(dates):
        # Determine if game day (every 2-3 days)
        is_game_day = (i % 3) == 0
        
        if is_game_day:
            game_minutes = np.random.normal(28, 5) if is_starter else np.random.normal(15, 7)
            game_minutes = max(0, game_minutes)
            practice_minutes = np.random.normal(20, 5)
        else:
            game_minutes = 0
            practice_minutes = np.random.normal(60, 10)
        
        load_data.append({
            'player_id': player_id,
            'date': date.date(),
            'practice_minutes': round(max(0, practice_minutes), 1),
            'practice_rpe': np.random.randint(4, 9),
            'strength_volume': round(np.random.normal(100, 30), 1),
            'game_minutes': round(game_minutes, 1)
        })

load_df = pd.DataFrame(load_data)
load_df.to_sql('training_load', conn, if_exists='replace', index=False)
print(f"✓ Created {len(load_df)} training load records")

# ==============================================================================
# 6. CALCULATE ACWR
# ==============================================================================

print("\n6. Calculating ACWR (Acute:Chronic Workload Ratio)...")

acwr_data = []

for player_id in players['player_id']:
    player_loads = load_df[load_df['player_id'] == player_id].sort_values('date')
    
    for i in range(21, len(player_loads)):  # Need 21 days for chronic load
        acute = player_loads.iloc[i-6:i+1]['practice_minutes'].sum()  # Last 7 days
        chronic = player_loads.iloc[i-20:i+1]['practice_minutes'].sum() / 3  # Last 21 days / 3
        
        acwr = acute / chronic if chronic > 0 else 0
        
        acwr_data.append({
            'player_id': player_id,
            'date': player_loads.iloc[i]['date'],
            'acwr': round(acwr, 2),
            'acute_load': round(acute, 1),
            'chronic_load': round(chronic, 1)
        })

acwr_df = pd.DataFrame(acwr_data)
acwr_df.to_sql('acwr', conn, if_exists='replace', index=False)
print(f"✓ Created {len(acwr_df)} ACWR records")

# ==============================================================================
# 7. FORCE PLATE DATA (Weekly testing - Mondays)
# ==============================================================================

print("\n7. Generating force plate data...")

fp_data = []

for player_id in players['player_id']:
    position = players[players['player_id'] == player_id]['position'].values[0]
    
    # Baseline jump height varies by position
    baseline_cmj = 30 + (5 if position == 'G' else 0) + np.random.normal(0, 3)
    
    # Weekly tests (Mondays)
    test_dates = [d for d in dates if d.weekday() == 0]
    
    for i, date in enumerate(test_dates):
        # Progressive decline through season
        fatigue_effect = -(i / len(test_dates)) * 2
        
        cmj = baseline_cmj + fatigue_effect + np.random.normal(0, 2)
        
        fp_data.append({
            'player_id': player_id,
            'date': date.date(),
            'cmj_height_cm': round(max(20, cmj), 1),
            'asymmetry_percent': round(abs(np.random.normal(5, 4)), 1),
            'rsi_modified': round(np.clip(np.random.normal(0.35, 0.08), 0.15, 0.60), 3)
        })

fp_df = pd.DataFrame(fp_data)
fp_df.to_sql('force_plate', conn, if_exists='replace', index=False)
print(f"✓ Created {len(fp_df)} force plate records")

# ==============================================================================
# 8. CREATE REALISTIC INJURIES
# ==============================================================================

print("\n8. Creating injury scenarios...")

injuries = [
    {'player_id': 'P001', 'injury_date': start_date + timedelta(days=12), 
     'injury_type': 'Knee inflammation', 'days_missed': 7},
    {'player_id': 'P003', 'injury_date': start_date + timedelta(days=25), 
     'injury_type': 'Ankle sprain', 'days_missed': 14},
    {'player_id': 'P002', 'injury_date': start_date + timedelta(days=35), 
     'injury_type': 'Hamstring strain', 'days_missed': 10},
    {'player_id': 'P004', 'injury_date': start_date + timedelta(days=40), 
     'injury_type': 'Back spasm', 'days_missed': 5},
    {'player_id': 'P005', 'injury_date': start_date + timedelta(days=45), 
     'injury_type': 'Shoulder issue', 'days_missed': 3}
]

injuries_df = pd.DataFrame(injuries)
injuries_df.to_sql('injuries', conn, if_exists='replace', index=False)
print(f"✓ Created {len(injuries_df)} injury records")

# Add warning signs before injuries
print("   Adding pre-injury warning signs...")

for injury in injuries:
    pid = injury['player_id']
    inj_date = injury['injury_date']
    
    # Spike load 5-7 days before injury
    for days_before in range(5, 8):
        warning_date = inj_date - timedelta(days=days_before)
        
        # Update load to be elevated
        conn.execute('''
            UPDATE training_load 
            SET practice_minutes = practice_minutes * 1.4
            WHERE player_id = ? AND date = ?
        ''', (pid, warning_date))
        
        # Update wellness to show deterioration
        conn.execute('''
            UPDATE wellness 
            SET sleep_hours = sleep_hours * 0.85,
                soreness = MIN(soreness + 2, 10)
            WHERE player_id = ? AND date = ?
        ''', (pid, warning_date))

conn.commit()
print("   ✓ Added realistic warning patterns")

# ==============================================================================
# 9. CREATE ANALYTICAL VIEWS
# ==============================================================================

print("\n9. Creating analytical views...")

# Combined view for ML
cursor.execute('''
CREATE VIEW IF NOT EXISTS player_daily_view AS
SELECT 
    p.player_id,
    p.name,
    p.position,
    p.age,
    p.injury_history_count,
    w.date,
    w.sleep_hours,
    w.sleep_quality,
    w.soreness,
    w.stress,
    w.mood,
    t.practice_minutes,
    t.practice_rpe,
    t.strength_volume,
    t.game_minutes,
    a.acwr,
    f.cmj_height_cm,
    f.asymmetry_percent,
    f.rsi_modified,
    CASE WHEN i.injury_id IS NOT NULL THEN 1 ELSE 0 END as injured_within_7days
FROM players p
LEFT JOIN wellness w ON p.player_id = w.player_id
LEFT JOIN training_load t ON p.player_id = t.player_id AND w.date = t.date
LEFT JOIN acwr a ON p.player_id = a.player_id AND w.date = a.date
LEFT JOIN force_plate f ON p.player_id = f.player_id AND w.date = f.date
LEFT JOIN injuries i ON p.player_id = i.player_id 
    AND w.date BETWEEN date(i.injury_date, '-7 days') AND i.injury_date
''')

conn.commit()
print("✓ Created analytical views")

# ==============================================================================
# 10. SUMMARY STATISTICS
# ==============================================================================

print("\n" + "=" * 60)
print("DATABASE GENERATION COMPLETE")
print("=" * 60)

# Get counts
player_count = cursor.execute("SELECT COUNT(*) FROM players").fetchone()[0]
wellness_count = cursor.execute("SELECT COUNT(*) FROM wellness").fetchone()[0]
load_count = cursor.execute("SELECT COUNT(*) FROM training_load").fetchone()[0]
acwr_count = cursor.execute("SELECT COUNT(*) FROM acwr").fetchone()[0]
fp_count = cursor.execute("SELECT COUNT(*) FROM force_plate").fetchone()[0]
injury_count = cursor.execute("SELECT COUNT(*) FROM injuries").fetchone()[0]

print(f"\n📊 Database Statistics:")
print(f"   Players:       {player_count}")
print(f"   Wellness:      {wellness_count} records")
print(f"   Training Load: {load_count} records")
print(f"   ACWR:          {acwr_count} records")
print(f"   Force Plate:   {fp_count} records")
print(f"   Injuries:      {injury_count} events")
print(f"   Total:         {wellness_count + load_count + acwr_count + fp_count + injury_count:,} data points")

print(f"\n✅ Database saved as: waims_demo.db")
print(f"📁 Size: {os.path.getsize('waims_demo.db') / 1024:.1f} KB")

print("\n🎯 Next Steps:")
print("   1. Train ML models: python train_models.py")
print("   2. Run dashboard: streamlit run dashboard.py")

conn.close()

print("\n" + "=" * 60)
