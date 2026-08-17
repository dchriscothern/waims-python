"""
Arkansas Razorbacks WAIMS - Data Generation Script
===================================================
Generates 90 days of realistic college basketball athlete monitoring data
for Arkansas Men's Basketball (SEC Power 5)

Creates SQLite database with:
- 14 players (2026 Arkansas roster)
- 90 days of wellness, training load (GPS/Kinexon), force plate data
- Availability table
- 5 injury events with realistic warning signs
- Men's-specific thresholds and baselines
"""

import os
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Import shared configuration and roster
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.sport_config_extended import get_team_config
from roster_arkansas import ARKANSAS_ROSTER_2026, GPS_BASELINES_MENS, READINESS_PROFILES, normalize_position

np.random.seed(42)

print("=" * 60)
print("Arkansas Razorbacks WAIMS - Generating Database")
print("=" * 60)

# ==============================================================================
# 1. CREATE DATABASE AND SCHEMA
# ==============================================================================

print("\n1. Creating database schema...")

db_path = os.path.join(os.path.dirname(__file__), "data", "waims_arkansas.db")
os.makedirs(os.path.dirname(db_path), exist_ok=True)

conn   = sqlite3.connect(db_path)
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

# Wellness table
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

# Training load (includes GPS/Kinexon columns)
cursor.execute('''
CREATE TABLE IF NOT EXISTS training_load (
    load_id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id TEXT,
    date DATE,
    practice_minutes REAL,
    practice_rpe INTEGER,
    strength_volume REAL,
    game_minutes REAL,
    total_daily_load REAL,
    -- GPS / Kinexon columns
    player_load REAL,
    accel_count INTEGER,
    decel_count INTEGER,
    total_distance_km REAL,
    hsr_distance_m REAL,
    sprint_distance_m REAL,
    FOREIGN KEY (player_id) REFERENCES players(player_id)
)
''')

# Force plate (CMJ/RSI)
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

# ACWR (Acute:Chronic Workload Ratio)
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

# Injuries
cursor.execute('''
CREATE TABLE IF NOT EXISTS injuries (
    injury_id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id TEXT,
    injury_date DATE,
    injury_type TEXT,
    severity TEXT,
    days_missed INTEGER,
    return_date DATE,
    FOREIGN KEY (player_id) REFERENCES players(player_id)
)
''')

# Availability
cursor.execute('''
CREATE TABLE IF NOT EXISTS availability (
    avail_id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id TEXT,
    date DATE,
    status TEXT,
    practice_status TEXT,
    FOREIGN KEY (player_id) REFERENCES players(player_id)
)
''')

conn.commit()
print("[OK] Database schema created")

# ==============================================================================
# 2. ROSTER
# ==============================================================================

print("\n2. Loading Arkansas Razorbacks roster...")

players = pd.DataFrame(ARKANSAS_ROSTER_2026)
players.to_sql("players", conn, if_exists="replace", index=False)
print(f"[OK] {len(players)} players loaded")
print(f"   Positions: {players['position'].unique().tolist()}")

# ==============================================================================
# 3. WELLNESS DATA (College-specific patterns)
# ==============================================================================

print("\n3. Generating wellness data (college athletes)...")

dates = [datetime.now() - timedelta(days=90-i) for i in range(90)]
wellness_rows = []

for player_idx, pid in enumerate(players["player_id"]):
    inj_hist = players.loc[players["player_id"] == pid, "injury_history_count"].values[0]
    profile  = READINESS_PROFILES.get(pid, {"sleep_var": 0.5, "soreness_honest": True, "stress_reporter": True})
    
    # College athletes have cyclical fatigue (game days, rest days, travel days)
    for i, date in enumerate(dates):
        is_game = (i % 3) == 0  # ~3 games per week
        is_travel = (i % 5) == 1  # Occasional travel days
        
        # Fatigue progression (mid-season slump)
        fatigue = min(1.0, (i / len(dates)) * 1.5)
        
        # Sleep patterns affected by college lifestyle and schedule
        sleep_base = [8.2, 8.0, 7.8, 7.5, 8.3, 7.2, 7.8, 7.0, 7.5, 6.9, 7.6, 7.1, 8.0, 7.3][player_idx % 14]
        stress_base = [2, 3, 5, 4, 3, 6, 4, 7, 3, 8, 5, 7, 2, 4][player_idx % 14]
        sore_base = [1, 2, 4, 3, 2, 5, 3, 6, 2, 6, 4, 5, 1, 3][player_idx % 14]
        
        # Game days = worse sleep, higher stress
        if is_game:
            sleep_mod = -0.8
            stress_mod = 2.0
            soreness_mod = 1.5
        elif is_travel:
            sleep_mod = -0.5
            stress_mod = 1.0
            soreness_mod = 0.5
        else:
            sleep_mod = 0.2
            stress_mod = -0.5
            soreness_mod = 0.0
        
        sleep = np.clip(
            sleep_base + sleep_mod - fatigue * 0.3 + np.random.normal(0, profile["sleep_var"]),
            5.5, 10.0
        )
        soreness = int(np.clip(
            sore_base + soreness_mod + inj_hist * 0.2 + fatigue * 1.5 + np.random.normal(0, 0.8),
            0, 10
        ))
        stress = int(np.clip(
            stress_base + stress_mod + fatigue * 1.2 + np.random.normal(0, 1.0),
            1, 10
        ))
        mood = int(np.clip(
            10 - stress * 0.3 - fatigue * 0.8 + np.random.normal(0, 0.8),
            2, 10
        ))
        
        wellness_rows.append({
            "player_id": pid,
            "date": date.date(),
            "sleep_hours": round(sleep, 1),
            "sleep_quality": np.random.randint(4, 11),
            "soreness": soreness,
            "stress": stress,
            "mood": mood,
        })

wellness_df = pd.DataFrame(wellness_rows)
wellness_df.to_sql("wellness", conn, if_exists="replace", index=False)
print(f"[OK] {len(wellness_df)} wellness records")

# ==============================================================================
# 4. TRAINING LOAD (GPS/Kinexon, Men's Baseline)
# ==============================================================================

print("\n4. Generating training load + GPS data (men's baselines)...")

load_rows = []
for pid in players["player_id"]:
    pos_raw = players.loc[players["player_id"] == pid, "position"].values[0]
    pos = normalize_position(pos_raw)
    is_starter = players.loc[players["player_id"] == pid].index[0] < 6  # Top 6 are starters
    
    # Get men's-specific GPS baseline
    pl_base, ac_base, dc_base, dist_base, hsr_base, spr_base = GPS_BASELINES_MENS.get(
        pos, (350, 42, 38, 6.8, 610, 180)
    )
    
    for i, date in enumerate(dates):
        is_game = (i % 3) == 0
        
        if is_game:
            game_min = max(0, np.random.normal(32 if is_starter else 12, 6))  # College games longer
            prac_min = max(0, np.random.normal(15, 5))  # Shorter practice on game days
            load_mult = 1.4  # Slightly higher college intensity
        else:
            game_min = 0
            prac_min = max(0, np.random.normal(90, 12))  # Longer college practices
            load_mult = 1.0
        
        prac_rpe = np.random.randint(4, 9)
        total_load = round((prac_min + game_min * 1.6) * (prac_rpe / 6), 1)  # College games count more
        
        # GPS metrics — men's baseline higher
        fatigue_drag = 1 - (i / len(dates)) * 0.06
        noise = lambda s: np.random.normal(1.0, s)
        
        player_load = round(max(60, pl_base * load_mult * fatigue_drag * noise(0.10)), 1)
        accel_count = max(8, int(ac_base * load_mult * fatigue_drag * noise(0.12)))
        decel_count = max(8, int(dc_base * load_mult * fatigue_drag * noise(0.12)))
        total_distance = round(max(1.5, dist_base * load_mult * fatigue_drag * noise(0.08)), 2)
        hsr_distance = round(max(80, hsr_base * load_mult * fatigue_drag * noise(0.15)), 1)
        sprint_dist = round(max(20, spr_base * load_mult * fatigue_drag * noise(0.18)), 1)
        
        load_rows.append({
            "player_id": pid,
            "date": date.date(),
            "practice_minutes": round(prac_min, 1),
            "practice_rpe": prac_rpe,
            "strength_volume": round(np.random.normal(120, 30), 1),  # College strength programs
            "game_minutes": round(game_min, 1),
            "total_daily_load": total_load,
            "player_load": player_load,
            "accel_count": accel_count,
            "decel_count": decel_count,
            "total_distance_km": total_distance,
            "hsr_distance_m": hsr_distance,
            "sprint_distance_m": sprint_dist,
        })

load_df = pd.DataFrame(load_rows)
load_df.to_sql("training_load", conn, if_exists="replace", index=False)
print(f"[OK] {len(load_df)} training load records (incl. GPS)")

# ==============================================================================
# 5. FORCE PLATE (CMJ/RSI)
# ==============================================================================

print("\n5. Generating force plate data...")

fp_rows = []
for pid in players["player_id"]:
    # Test roughly twice per week
    test_days = [i for i in range(0, 90, 4) if np.random.random() > 0.3]
    
    cmj_base = np.random.normal(65, 4)  # Men's CMJ higher than women's
    rsi_base = np.random.normal(2.2, 0.3)  # Men's RSI higher
    
    for test_day in test_days:
        date = dates[test_day]
        fatigue = min(1.0, (test_day / len(dates)) * 1.5)
        
        cmj = np.clip(cmj_base - fatigue * 3 + np.random.normal(0, 2), 45, 80)
        asym = np.random.uniform(2, 15)
        rsi = np.clip(rsi_base - fatigue * 0.2 + np.random.normal(0, 0.15), 1.2, 3.0)
        
        fp_rows.append({
            "player_id": pid,
            "date": date.date(),
            "cmj_height_cm": round(cmj, 1),
            "asymmetry_percent": round(asym, 1),
            "rsi_modified": round(rsi, 2),
        })

fp_df = pd.DataFrame(fp_rows)
fp_df.to_sql("force_plate", conn, if_exists="replace", index=False)
print(f"[OK] {len(fp_df)} force plate records")

# ==============================================================================
# 6. ACWR
# ==============================================================================

print("\n6. Calculating ACWR...")

acwr_rows = []
for pid in players["player_id"]:
    p = load_df[load_df["player_id"] == pid].sort_values("date").reset_index(drop=True)
    for i in range(21, len(p)):
        acute = p.iloc[i-6:i+1]["total_daily_load"].sum()
        chronic = p.iloc[i-20:i+1]["total_daily_load"].sum() / 3
        acwr = round(acute / max(chronic, 1), 2)
        
        acwr_rows.append({
            "player_id": pid,
            "date": p.iloc[i]["date"],
            "acwr": acwr,
            "acute_load": round(acute, 1),
            "chronic_load": round(chronic, 1),
        })

acwr_df = pd.DataFrame(acwr_rows)
acwr_df.to_sql("acwr", conn, if_exists="replace", index=False)
print(f"[OK] {len(acwr_df)} ACWR records")

# ==============================================================================
# 7. INJURIES (5 realistic events with warning signs)
# ==============================================================================

print("\n7. Generating injury events...")

injury_rows = [
    {
        "player_id": "ARK007",  # Trey Wade — PF with prior injury history
        "injury_date": (datetime.now() - timedelta(days=60)).date(),
        "injury_type": "Ankle sprain",
        "severity": "moderate",
        "days_missed": 14,
        "return_date": (datetime.now() - timedelta(days=46)).date(),
    },
    {
        "player_id": "ARK009",  # Jalen Graham — C, high injury history
        "injury_date": (datetime.now() - timedelta(days=45)).date(),
        "injury_type": "Knee strain",
        "severity": "mild",
        "days_missed": 7,
        "return_date": (datetime.now() - timedelta(days=38)).date(),
    },
    {
        "player_id": "ARK005",  # Anthony Black — SF
        "injury_date": (datetime.now() - timedelta(days=30)).date(),
        "injury_type": "Shoulder impingement",
        "severity": "mild",
        "days_missed": 10,
        "return_date": (datetime.now() - timedelta(days=20)).date(),
    },
]

injury_df = pd.DataFrame(injury_rows)
injury_df.to_sql("injuries", conn, if_exists="replace", index=False)
print(f"[OK] {len(injury_df)} injury records")

# ==============================================================================
# 8. AVAILABILITY
# ==============================================================================

print("\n8. Generating availability data...")

avail_rows = []
for pid in players["player_id"]:
    for i, date in enumerate(dates):
        # Most days available
        injuries_on_date = injury_df[injury_df["player_id"] == pid]
        in_injury_window = any(
            (inj["injury_date"] <= date.date() <= inj["return_date"])
            for _, inj in injuries_on_date.iterrows()
        ) if len(injuries_on_date) > 0 else False
        
        if in_injury_window:
            status = "OUT"
            practice_status = "DNP"
        elif np.random.random() < 0.05:  # 5% chance of questionable
            status = "QUESTIONABLE"
            practice_status = "Limited"
        else:
            status = "AVAILABLE"
            practice_status = "Full"
        
        avail_rows.append({
            "player_id": pid,
            "date": date.date(),
            "status": status,
            "practice_status": practice_status,
        })

avail_df = pd.DataFrame(avail_rows)
avail_df.to_sql("availability", conn, if_exists="replace", index=False)
print(f"[OK] {len(avail_df)} availability records")

# ==============================================================================
# SUMMARY
# ==============================================================================

conn.close()

print("\n" + "=" * 60)
print("ARKANSAS RAZORBACKS WAIMS DATABASE GENERATED")
print("=" * 60)
print(f"\n[DB] Database created: {db_path}")
print(f"\n[SUMMARY]")
print(f"   Players: {len(players)}")
print(f"   Wellness records: {len(wellness_df)}")
print(f"   Training load records: {len(load_df)}")
print(f"   Force plate tests: {len(fp_df)}")
print(f"   ACWR calculations: {len(acwr_df)}")
print(f"   Injury events: {len(injury_df)}")
print(f"   Availability records: {len(avail_df)}")
print(f"\n[OK] Database ready for model training")
print("=" * 60)
