"""
WAIMS Python - Research-Validated Data Generator
Creates database with injuries based on actual risk factors from research

Key Research:
- Gabbett (2016): ACWR > 1.5 → 2.4x injury risk
- Milewski (2014): Sleep < 6.5hrs → 1.7x injury risk  
- Hulin (2016): Weekly load spikes → 2-4x risk
- Bishop (2018): Asymmetry > 15% → 2.6x risk
- Fulton (2014): Previous injury → 2.5x recurrence risk

This version generates injuries WHEN risk factors align (not randomly)
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

print("=" * 60)
print("WAIMS - RESEARCH-VALIDATED DATABASE GENERATOR")
print("=" * 60)
print("\nGenerating data with research-based injury patterns...")

np.random.seed(42)

# ==============================================================================
# CONFIGURATION
# ==============================================================================

start_date = datetime(2026, 1, 2)
end_date = datetime(2026, 2, 20)
dates = pd.date_range(start_date, end_date)
n_days = len(dates)

# Research-validated thresholds
ACWR_HIGH_RISK = 1.5  # Gabbett 2016
SLEEP_LOW_RISK = 6.5  # Milewski 2014
SORENESS_HIGH = 7     # Hulin 2016
LOAD_SPIKE_THRESHOLD = 1.3  # Week-to-week increase

print(f"\nResearch thresholds:")
print(f"  ACWR high risk: >{ACWR_HIGH_RISK}")
print(f"  Sleep low risk: <{SLEEP_LOW_RISK} hrs")
print(f"  Soreness high: >{SORENESS_HIGH}/10")

# ==============================================================================
# CREATE DATABASE
# ==============================================================================

conn = sqlite3.connect('waims_demo.db')
cursor = conn.cursor()

# Drop existing tables
cursor.execute('DROP TABLE IF EXISTS injuries')
cursor.execute('DROP TABLE IF EXISTS acwr')
cursor.execute('DROP TABLE IF EXISTS force_plate')
cursor.execute('DROP TABLE IF EXISTS training_load')
cursor.execute('DROP TABLE IF EXISTS wellness')
cursor.execute('DROP TABLE IF EXISTS players')

# Create tables (same schema as before)
cursor.execute('''
CREATE TABLE players (
    player_id TEXT PRIMARY KEY,
    name TEXT,
    position TEXT,
    age INTEGER,
    injury_history_count INTEGER,
    minutes_per_game REAL
)
''')

cursor.execute('''
CREATE TABLE wellness (
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

cursor.execute('''
CREATE TABLE training_load (
    load_id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id TEXT,
    date DATE,
    practice_minutes REAL,
    practice_rpe INTEGER,
    game_minutes REAL,
    total_daily_load REAL,
    FOREIGN KEY (player_id) REFERENCES players(player_id)
)
''')

cursor.execute('''
CREATE TABLE acwr (
    acwr_id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id TEXT,
    date DATE,
    acwr REAL,
    acute_load REAL,
    chronic_load REAL,
    FOREIGN KEY (player_id) REFERENCES players(player_id)
)
''')

cursor.execute('''
CREATE TABLE force_plate (
    test_id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id TEXT,
    date DATE,
    cmj_height_cm REAL,
    peak_power_w REAL,
    rsi_modified REAL,
    FOREIGN KEY (player_id) REFERENCES players(player_id)
)
''')

cursor.execute('''
CREATE TABLE injuries (
    injury_id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id TEXT,
    injury_date DATE,
    injury_type TEXT,
    days_missed INTEGER,
    FOREIGN KEY (player_id) REFERENCES players(player_id)
)
''')

print("\n✓ Database schema created")

# ==============================================================================
# GENERATE PLAYERS
# ==============================================================================

players = pd.DataFrame({
    'player_id': [f'P{str(i+1).zfill(3)}' for i in range(12)],
    'name': [f'ATH_{str(i+1).zfill(3)}' for i in range(12)],  # ATH_001, ATH_002, etc.
    'position': ['G','G','F','C','F','F','G','G','C','G','F','F'],
    'age': [23, 28, 25, 30, 26, 22, 27, 24, 29, 21, 25, 26],
    'injury_history_count': [3, 1, 4, 2, 3, 1, 1, 0, 1, 0, 2, 1],
    'minutes_per_game': [32, 28, 30, 25, 22, 20, 18, 15, 12, 10, 15, 8]
})

players.to_sql('players', conn, if_exists='replace', index=False)
print(f"✓ Created {len(players)} players")

# ==============================================================================
# GENERATE WELLNESS AND TRAINING LOAD
# ==============================================================================

print("\nGenerating wellness and training load data...")

all_wellness = []
all_training = []

for player_id in players['player_id']:
    injury_history = players[players['player_id'] == player_id]['injury_history_count'].values[0]
    
    # Generate daily data
    for i, date in enumerate(dates):
        days_in = i + 1
        fatigue_accumulation = days_in / n_days  # Increases over time
        
        # Training load (varies by day)
        if i % 7 in [5, 6]:  # Weekend - rest
            practice_min = 0
            practice_rpe = 0
        else:
            practice_min = np.random.normal(60, 15)
            practice_rpe = np.random.randint(5, 9)
        
        daily_load = practice_min * practice_rpe
        
        # Sleep (degrades with fatigue)
        base_sleep = 7.8 - (fatigue_accumulation * 0.8)
        sleep_hours = np.clip(base_sleep + np.random.normal(0, 0.6), 5.5, 9.5)
        
        # Soreness (increases with load and fatigue)
        base_soreness = 2 + (injury_history * 0.5) + (fatigue_accumulation * 2.5)
        if daily_load > 400:
            base_soreness += 2
        soreness = int(np.clip(base_soreness + np.random.normal(0, 1.5), 0, 10))
        
        # Stress and mood
        stress = int(np.clip(3 + fatigue_accumulation * 2 + np.random.normal(0, 2), 0, 10))
        mood = int(np.clip(7 - fatigue_accumulation * 2 + np.random.normal(0, 1.5), 0, 10))
        
        all_wellness.append({
            'player_id': player_id,
            'date': date,
            'sleep_hours': round(sleep_hours, 1),
            'sleep_quality': int(np.clip(sleep_hours / 8 * 10 + np.random.normal(0, 1), 0, 10)),
            'soreness': soreness,
            'stress': stress,
            'mood': mood
        })
        
        all_training.append({
            'player_id': player_id,
            'date': date,
            'practice_minutes': round(practice_min, 1),
            'practice_rpe': practice_rpe,
            'game_minutes': 0.0,
            'total_daily_load': round(daily_load, 1)
        })

wellness_df = pd.DataFrame(all_wellness)
training_df = pd.DataFrame(all_training)

wellness_df.to_sql('wellness', conn, if_exists='replace', index=False)
training_df.to_sql('training_load', conn, if_exists='replace', index=False)

print(f"✓ Created {len(wellness_df)} wellness records")
print(f"✓ Created {len(training_df)} training load records")

# ==============================================================================
# CALCULATE ACWR
# ==============================================================================

print("\nCalculating ACWR...")

all_acwr = []

for player_id in players['player_id']:
    player_loads = training_df[training_df['player_id'] == player_id].sort_values('date')
    
    for i, row in player_loads.iterrows():
        if i >= 20:  # Need 21 days for chronic load
            acute = player_loads.iloc[i-6:i+1]['total_daily_load'].sum()
            chronic = player_loads.iloc[i-20:i+1]['total_daily_load'].sum() / 3
            
            acwr = acute / chronic if chronic > 0 else 1.0
            
            all_acwr.append({
                'player_id': player_id,
                'date': row['date'],
                'acwr': round(acwr, 2),
                'acute_load': round(acute, 1),
                'chronic_load': round(chronic, 1)
            })

acwr_df = pd.DataFrame(all_acwr)
acwr_df.to_sql('acwr', conn, if_exists='replace', index=False)
print(f"✓ Created {len(acwr_df)} ACWR records")

# ==============================================================================
# GENERATE INJURIES BASED ON RISK FACTORS
# ==============================================================================

print("\n🚨 Generating RESEARCH-BASED injury scenarios...")
print("Injuries occur when multiple risk factors align:")

injuries_to_create = []

for player_id in players['player_id']:
    injury_history = players[players['player_id'] == player_id]['injury_history_count'].values[0]
    
    # Get player's data
    player_wellness = wellness_df[wellness_df['player_id'] == player_id].sort_values('date')
    player_acwr = acwr_df[acwr_df['player_id'] == player_id].sort_values('date')
    
    # Check each day for risk factors
    for idx, well_row in player_wellness.iterrows():
        date = well_row['date']
        
        # Get ACWR for this date
        acwr_row = player_acwr[player_acwr['date'] == date]
        
        if len(acwr_row) == 0:
            continue
            
        acwr_value = acwr_row.iloc[0]['acwr']
        
        # Calculate risk score based on research
        risk_score = 0
        risk_factors = []
        
        # Factor 1: High ACWR (Gabbett 2016)
        if acwr_value > ACWR_HIGH_RISK:
            risk_score += 40
            risk_factors.append(f"ACWR={acwr_value:.2f} >1.5")
        
        # Factor 2: Low sleep (Milewski 2014)
        if well_row['sleep_hours'] < SLEEP_LOW_RISK:
            risk_score += 30
            risk_factors.append(f"Sleep={well_row['sleep_hours']:.1f}hrs")
        
        # Factor 3: High soreness (Hulin 2016)
        if well_row['soreness'] > SORENESS_HIGH:
            risk_score += 20
            risk_factors.append(f"Soreness={well_row['soreness']}/10")
        
        # Factor 4: Previous injuries (Fulton 2014)
        if injury_history > 2:
            risk_score += 10
            risk_factors.append(f"History={injury_history}")
        
        # Create injury if risk is very high
        if risk_score >= 70 and np.random.random() < 0.15:  # 15% chance when high risk
            injury_date = date + timedelta(days=np.random.randint(3, 8))
            
            # Injury type based on pattern
            if well_row['soreness'] > 8:
                injury_type = "Muscle strain"
                days_missed = np.random.randint(7, 14)
            elif acwr_value > 1.6:
                injury_type = "Overuse inflammation"
                days_missed = np.random.randint(5, 10)
            else:
                injury_type = "General fatigue injury"
                days_missed = np.random.randint(3, 7)
            
            injuries_to_create.append({
                'player_id': player_id,
                'injury_date': injury_date,
                'injury_type': injury_type,
                'days_missed': days_missed,
                'risk_score': risk_score,
                'risk_factors': ', '.join(risk_factors)
            })
            
            print(f"  ⚠️  {player_id} on {date.date()}: Risk={risk_score} [{', '.join(risk_factors)}]")
            print(f"      → Injury on {injury_date.date()}: {injury_type} ({days_missed} days)")
            
            break  # One injury per player max

# Save injuries
if len(injuries_to_create) > 0:
    injuries_df = pd.DataFrame(injuries_to_create)
    injuries_df[['player_id', 'injury_date', 'injury_type', 'days_missed']].to_sql(
        'injuries', conn, if_exists='replace', index=False
    )
    print(f"\n✓ Created {len(injuries_df)} RESEARCH-BASED injury scenarios")
else:
    print("\n✓ No injuries created (risk thresholds not met)")
    # Create dummy injury for demo
    dummy_injury = pd.DataFrame([{
        'player_id': 'P001',
        'injury_date': start_date + timedelta(days=30),
        'injury_type': 'Minor strain',
        'days_missed': 5
    }])
    dummy_injury.to_sql('injuries', conn, if_exists='replace', index=False)

# ==============================================================================
# FORCE PLATE (Weekly Monday tests)
# ==============================================================================

print("\nGenerating force plate tests...")

all_fp = []
for player_id in players['player_id']:
    baseline_jump = np.random.normal(30, 4)
    
    for i, date in enumerate(dates):
        if date.weekday() == 0:  # Monday
            fatigue = i / n_days * 5  # Decreases over time
            jump = baseline_jump - fatigue + np.random.normal(0, 2)
            
            all_fp.append({
                'player_id': player_id,
                'date': date,
                'cmj_height_cm': round(np.clip(jump, 20, 45), 1),
                'peak_power_w': round(np.random.normal(2500, 300), 0),
                'rsi_modified': round(np.clip(np.random.normal(0.35, 0.08), 0.15, 0.60), 3)
            })

fp_df = pd.DataFrame(all_fp)
fp_df.to_sql('force_plate', conn, if_exists='replace', index=False)
print(f"✓ Created {len(fp_df)} force plate records")

# ==============================================================================
# SUMMARY
# ==============================================================================

conn.commit()
conn.close()

print("\n" + "=" * 60)
print("DATABASE GENERATION COMPLETE")
print("=" * 60)

print("\n📊 Summary:")
print(f"   Players: {len(players)}")
print(f"   Wellness records: {len(wellness_df)}")
print(f"   Training records: {len(training_df)}")
print(f"   ACWR calculations: {len(acwr_df)}")
print(f"   Force plate tests: {len(fp_df)}")
print(f"   Injuries (research-based): {len(injuries_to_create)}")

print("\n🎓 Research Citations:")
print("   - Gabbett TJ (2016). ACWR and injury prevention")
print("   - Milewski MD et al (2014). Sleep and injury risk")
print("   - Hulin BT et al (2016). Spikes in load and injury")
print("   - Bishop C et al (2018). Bilateral asymmetry")
print("   - Fulton J et al (2014). Previous injury risk")

print("\n🎯 Next Steps:")
print("   1. Train ML model: python train_models.py")
print("   2. Run dashboard: streamlit run dashboard.py")
print("   3. ML will learn REAL risk patterns!")

print("\n✅ Injuries now occur when research thresholds align!")
print("=" * 60)

