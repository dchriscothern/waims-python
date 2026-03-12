"""
WAIMS Python Demo - Data Generation Script
Generates 90 days of realistic WNBA athlete monitoring data

Creates SQLite database with:
- 12 players (2025 Wings roster simulation)
- 90 days of wellness, training load (incl. GPS/Kinexon), force plate data
- Availability table
- 5 injury events with realistic warning signs
- Ready for ML training and dashboard visualization
"""

import os
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

np.random.seed(42)

print("=" * 60)
print("WAIMS - Generating Athlete Monitoring Database")
print("=" * 60)

# ==============================================================================
# 1. CREATE DATABASE AND SCHEMA
# ==============================================================================

print("\n1. Creating database schema...")

conn   = sqlite3.connect("waims_demo.db")
cursor = conn.cursor()

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

# training_load now includes full GPS / Kinexon columns
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

cursor.execute('''
CREATE TABLE IF NOT EXISTS availability (
    avail_id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id TEXT,
    date DATE,
    status TEXT,           -- AVAILABLE / QUESTIONABLE / OUT
    practice_status TEXT,  -- Full / Limited / Non-contact / DNP
    FOREIGN KEY (player_id) REFERENCES players(player_id)
)
''')

conn.commit()
print("✓ Database schema created")

# ==============================================================================
# 2. ROSTER
# ==============================================================================

print("\n2. Generating player roster...")

players = pd.DataFrame({
    "player_id": [f"P{i:03d}" for i in range(1, 13)],
    # Anonymized for portfolio demo — positions/ages/injury history reflect
    # realistic WNBA roster composition but names are not real players
    "name": [
        "Player G1",
        "Player G2",
        "Player F1",
        "Player C1",
        "Player F2",
        "Player F3",
        "Player G3",
        "Player G4",
        "Player C2",
        "Player G5",
        "Player F4",
        "Player F5",
    ],
    "position": ["G", "G", "F", "C", "F", "F", "G", "G", "C", "G", "F", "F"],
    "age":      [23, 28, 27, 28, 32, 24, 24, 23, 26, 22, 29, 31],
    "injury_history_count": [3, 1, 4, 2, 3, 1, 1, 0, 1, 0, 2, 1],
    "status_active": [1] * 12,
})

players.to_sql("players", conn, if_exists="replace", index=False)
print(f"✓ Created roster: {len(players)} players")

# ==============================================================================
# 3. DATE RANGE  (90 days)
# ==============================================================================

print("\n3. Setting up 90-day date range...")

end_date   = datetime.now().date()
start_date = end_date - timedelta(days=89)
dates      = pd.date_range(start=start_date, end=end_date, freq="D")
print(f"   {start_date}  →  {end_date}  ({len(dates)} days)")

# ==============================================================================
# 4. WELLNESS
# ==============================================================================

print("\n4. Generating wellness data...")

wellness_rows = []
for pid in players["player_id"]:
    inj_hist = players.loc[players["player_id"] == pid, "injury_history_count"].values[0]
    for i, date in enumerate(dates):
        # Fatigue oscillates with recovery — not purely cumulative
        # Creates realistic mix: some players always green, some always amber,
        # 2-3 red on any given day. Uses sine wave so fatigue peaks mid-week
        # and recovers on rest days rather than grinding to 1.0 by day 90.
        day_of_week  = date.dayofweek          # 0=Mon … 6=Sun
        week_num     = i // 7
        base_fatigue = 0.25 + 0.15 * np.sin(week_num * 0.8)   # gentle season arc
        daily_fatigue = base_fatigue + 0.2 * np.sin(day_of_week * np.pi / 3.5)
        fatigue = float(np.clip(daily_fatigue + np.random.normal(0, 0.05), 0.0, 0.85))

        player_idx = list(players["player_id"]).index(pid)

        # Per-player archetypes: 4 healthy sleepers, 5 moderate, 3 chronically under-recovered
        # With oscillating fatigue this produces ~4 READY / 5 MONITOR / 3 PROTECT on typical day
        sleep_base  = [8.5, 8.2, 7.5, 7.8, 8.6, 7.0, 8.0, 7.2, 8.3, 6.8, 6.9, 8.0][player_idx % 12]
        stress_base = [2,   3,   6,   4,   2,   7,   3,   6,   2,   7,   8,   3  ][player_idx % 12]
        sore_base   = [1,   2,   5,   3,   1,   6,   2,   5,   1,   4,   6,   2  ][player_idx % 12]

        # Mild oscillating fatigue — creates day-to-day variation without grinding everyone down
        sleep    = np.clip(sleep_base - fatigue * 0.5 + np.random.normal(0, 0.5), 4.5, 9.5)
        soreness = int(np.clip(sore_base + inj_hist * 0.3 + fatigue * 2.0 + np.random.normal(0, 1.0), 0, 10))
        stress   = int(np.clip(stress_base + fatigue * 1.5 + np.random.normal(0, 1.0), 1, 10))
        mood     = int(np.clip(10 - stress * 0.3 - fatigue * 1.0 + np.random.normal(0, 0.8), 2, 10))
        wellness_rows.append({
            "player_id":     pid,
            "date":          date.date(),
            "sleep_hours":   round(sleep, 1),
            "sleep_quality": np.random.randint(4, 11),
            "soreness":      soreness,
            "stress":        stress,
            "mood":          mood,
        })
wellness_df = pd.DataFrame(wellness_rows)
wellness_df.to_sql("wellness", conn, if_exists="replace", index=False)
print(f"✓ {len(wellness_df)} wellness records")

# ==============================================================================
# 5. TRAINING LOAD  (incl. GPS / Kinexon)
# ==============================================================================

print("\n5. Generating training load + GPS data...")

# Position-based GPS baselines (realistic WNBA values)
GPS_BASELINES = {
    # pos: (player_load, accels, decels, distance_km, hsr_m, sprint_m)
    "G": (320, 42, 38, 6.8, 620, 180),
    "F": (295, 36, 33, 6.2, 510, 140),
    "C": (265, 28, 26, 5.4, 380, 90),
}

load_rows = []
for pid in players["player_id"]:
    pos        = players.loc[players["player_id"] == pid, "position"].values[0]
    is_starter = players.loc[players["player_id"] == pid].index[0] < 4
    pl_base, ac_base, dc_base, dist_base, hsr_base, spr_base = GPS_BASELINES[pos]

    for i, date in enumerate(dates):
        is_game = (i % 3) == 0

        if is_game:
            game_min  = max(0, np.random.normal(28 if is_starter else 15, 5))
            prac_min  = max(0, np.random.normal(20, 5))
            load_mult = 1.3   # higher load on game days
        else:
            game_min  = 0
            prac_min  = max(0, np.random.normal(65, 10))
            load_mult = 1.0

        prac_rpe      = np.random.randint(4, 9)
        total_load    = round((prac_min + game_min * 1.5) * (prac_rpe / 6), 1)

        # GPS metrics — correlated with total load, with individual noise
        fatigue_drag  = 1 - (i / len(dates)) * 0.08   # slight seasonal drift down
        noise         = lambda s: np.random.normal(1.0, s)

        player_load    = round(max(50,  pl_base  * load_mult * fatigue_drag * noise(0.12)), 1)
        accel_count    = max(5,  int(ac_base  * load_mult * fatigue_drag * noise(0.15)))
        decel_count    = max(5,  int(dc_base  * load_mult * fatigue_drag * noise(0.15)))
        total_distance = round(max(1.0, dist_base * load_mult * fatigue_drag * noise(0.10)), 2)
        hsr_distance   = round(max(50,  hsr_base  * load_mult * fatigue_drag * noise(0.18)), 1)
        sprint_dist    = round(max(10,  spr_base  * load_mult * fatigue_drag * noise(0.20)), 1)

        load_rows.append({
            "player_id":        pid,
            "date":             date.date(),
            "practice_minutes": round(prac_min, 1),
            "practice_rpe":     prac_rpe,
            "strength_volume":  round(np.random.normal(100, 30), 1),
            "game_minutes":     round(game_min, 1),
            "total_daily_load": total_load,
            # GPS
            "player_load":      player_load,
            "accel_count":      accel_count,
            "decel_count":      decel_count,
            "total_distance_km": total_distance,
            "hsr_distance_m":   hsr_distance,
            "sprint_distance_m": sprint_dist,
        })

load_df = pd.DataFrame(load_rows)
load_df.to_sql("training_load", conn, if_exists="replace", index=False)
print(f"✓ {len(load_df)} training load records (incl. GPS columns)")

# ==============================================================================
# 6. ACWR
# ==============================================================================

print("\n6. Calculating ACWR...")

acwr_rows = []
for pid in players["player_id"]:
    p = load_df[load_df["player_id"] == pid].sort_values("date").reset_index(drop=True)
    for i in range(21, len(p)):
        acute   = p.iloc[i-6:i+1]["total_daily_load"].sum()
        chronic = p.iloc[i-20:i+1]["total_daily_load"].sum() / 3
        acwr_rows.append({
            "player_id":    pid,
            "date":         p.iloc[i]["date"],
            "acwr":         round(acute / chronic, 2) if chronic > 0 else 1.0,
            "acute_load":   round(acute, 1),
            "chronic_load": round(chronic, 1),
        })

acwr_df = pd.DataFrame(acwr_rows)
acwr_df.to_sql("acwr", conn, if_exists="replace", index=False)
print(f"✓ {len(acwr_df)} ACWR records")

# ==============================================================================
# 7. FORCE PLATE  (weekly, Mondays)
# ==============================================================================

print("\n7. Generating force plate data...")

CMJ_BASE = {"G": 38, "F": 34, "C": 30}  # WNBA-appropriate: guards highest, centers lower

fp_rows = []
for pid in players["player_id"]:
    pos          = players.loc[players["player_id"] == pid, "position"].values[0]
    baseline_cmj = CMJ_BASE[pos] + np.random.normal(0, 2)
    test_dates   = [d for d in dates if d.weekday() == 0]   # Mondays
    for i, date in enumerate(test_dates):
        fatigue_effect = -(i / len(test_dates)) * 2
        cmj = max(18, baseline_cmj + fatigue_effect + np.random.normal(0, 1.5))
        fp_rows.append({
            "player_id":        pid,
            "date":             date.date(),
            "cmj_height_cm":    round(cmj, 1),
            "asymmetry_percent": round(abs(np.random.normal(5, 3)), 1),
            "rsi_modified":     round(np.clip(np.random.normal(0.35, 0.07), 0.15, 0.60), 3),
        })

fp_df = pd.DataFrame(fp_rows)
fp_df.to_sql("force_plate", conn, if_exists="replace", index=False)
print(f"✓ {len(fp_df)} force plate records")

# ==============================================================================
# 8. INJURIES  (5 events with pre-injury warning patterns)
# ==============================================================================

print("\n8. Creating injury scenarios...")

injuries_list = [
    {"player_id": "P001", "injury_date": start_date + timedelta(days=14),
     "injury_type": "Knee inflammation", "severity": "Moderate", "days_missed": 7},
    {"player_id": "P003", "injury_date": start_date + timedelta(days=28),
     "injury_type": "Ankle sprain",      "severity": "Moderate", "days_missed": 14},
    {"player_id": "P002", "injury_date": start_date + timedelta(days=42),
     "injury_type": "Hamstring strain",  "severity": "Mild",     "days_missed": 10},
    {"player_id": "P004", "injury_date": start_date + timedelta(days=58),
     "injury_type": "Back spasm",        "severity": "Mild",     "days_missed": 5},
    {"player_id": "P005", "injury_date": start_date + timedelta(days=72),
     "injury_type": "Shoulder issue",    "severity": "Mild",     "days_missed": 3},
]

for inj in injuries_list:
    inj["return_date"] = inj["injury_date"] + timedelta(days=inj["days_missed"])

inj_df = pd.DataFrame(injuries_list)
inj_df.to_sql("injuries", conn, if_exists="replace", index=False)

# Pre-injury warning patterns — spike load, drop sleep/GPS in 5–7 days before
print("   Adding pre-injury warning signs...")
for inj in injuries_list:
    pid      = inj["player_id"]
    inj_date = inj["injury_date"]
    for days_before in range(5, 8):
        warn_date = inj_date - timedelta(days=days_before)
        # Wellness deterioration
        conn.execute(
            "UPDATE wellness SET sleep_hours = sleep_hours * 0.85, "
            "soreness = MIN(soreness + 2, 10) "
            "WHERE player_id = ? AND date = ?",
            (pid, warn_date),
        )
        # Load spike
        conn.execute(
            "UPDATE training_load SET practice_minutes = practice_minutes * 1.4, "
            "total_daily_load = total_daily_load * 1.4 "
            "WHERE player_id = ? AND date = ?",
            (pid, warn_date),
        )
        # GPS drops (fatigue signal before injury)
        conn.execute(
            "UPDATE training_load SET "
            "player_load  = player_load  * 0.82, "
            "accel_count  = CAST(accel_count  * 0.78 AS INTEGER), "
            "decel_count  = CAST(decel_count  * 0.78 AS INTEGER) "
            "WHERE player_id = ? AND date = ?",
            (pid, warn_date),
        )

conn.commit()
print(f"✓ {len(injuries_list)} injuries + warning patterns added")

# ==============================================================================
# 9. AVAILABILITY
# ==============================================================================

print("\n9. Generating availability data...")

avail_rows = []
# Build a set of (player_id, date) that are injury-out windows
injury_windows = set()
for inj in injuries_list:
    pid  = inj["player_id"]
    for d in range(inj["days_missed"]):
        injury_windows.add((pid, inj["injury_date"] + timedelta(days=d)))

for pid in players["player_id"]:
    for date in dates:
        d = date.date()
        if (pid, d) in injury_windows:
            status         = "OUT"
            practice_status = "DNP"
        elif np.random.random() < 0.08:
            status         = "QUESTIONABLE"
            practice_status = "Limited"
        else:
            status         = "AVAILABLE"
            practice_status = "Full"
        avail_rows.append({
            "player_id":      pid,
            "date":           d,
            "status":         status,
            "practice_status": practice_status,
        })

avail_df = pd.DataFrame(avail_rows)
avail_df.to_sql("availability", conn, if_exists="replace", index=False)
print(f"✓ {len(avail_df)} availability records")

# ==============================================================================
# 10. ANALYTICAL VIEW
# ==============================================================================

print("\n10. Creating analytical view...")

cursor.execute("DROP VIEW IF EXISTS player_daily_view")
cursor.execute('''
CREATE VIEW player_daily_view AS
SELECT
    p.player_id, p.name, p.position, p.age, p.injury_history_count,
    w.date,
    w.sleep_hours, w.sleep_quality, w.soreness, w.stress, w.mood,
    t.practice_minutes, t.practice_rpe, t.game_minutes, t.total_daily_load,
    t.player_load, t.accel_count, t.decel_count,
    t.total_distance_km, t.hsr_distance_m, t.sprint_distance_m,
    a.acwr,
    f.cmj_height_cm, f.asymmetry_percent, f.rsi_modified,
    CASE WHEN i.injury_id IS NOT NULL THEN 1 ELSE 0 END AS injured_within_7days
FROM players p
LEFT JOIN wellness w       ON p.player_id = w.player_id
LEFT JOIN training_load t  ON p.player_id = t.player_id  AND w.date = t.date
LEFT JOIN acwr a           ON p.player_id = a.player_id  AND w.date = a.date
LEFT JOIN force_plate f    ON p.player_id = f.player_id  AND w.date = f.date
LEFT JOIN injuries i       ON p.player_id = i.player_id
    AND w.date BETWEEN date(i.injury_date, "-7 days") AND i.injury_date
''')
conn.commit()
print("✓ Analytical view created")

# ==============================================================================

# ==============================================================================
# 10b. SCHEDULE TABLE — 2026 Dallas Wings (real dates + context flags)
# Reference: wings.wnba.com/news/wings-announce-2026-schedule (Jan 21, 2026)
# Unrivaled players: G1 (Breeze BC), G2 (Mist BC) — anonymized for demo
# Unrivaled 2026 ran Jan 5 – ~Mar 4; WNBA camp ~Apr 28
# ==============================================================================

print("\n10b. Building schedule table...")

cursor.execute("DROP TABLE IF EXISTS schedule")
cursor.execute("""
CREATE TABLE schedule (
    game_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    date            TEXT NOT NULL,
    opponent        TEXT,
    location        TEXT,   -- 'home' or 'away'
    venue           TEXT,   -- stadium name
    is_back_to_back INTEGER DEFAULT 0,
    days_rest       INTEGER DEFAULT 1,
    travel_flag     INTEGER DEFAULT 0,   -- 1 = travel day (away game)
    game_type       TEXT DEFAULT 'WNBA', -- WNBA / Unrivaled / EuroLeague / practice
    time_zone_diff  INTEGER DEFAULT 0,   -- hours vs Dallas (CT)
    fiba_break      INTEGER DEFAULT 0    -- 1 = during FIBA World Cup break
)
""")

# ── 2026 Dallas Wings Schedule (all 44 games) ─────────────────────────────────
# Source: official Wings announcement, Jan 21 2026
# Location codes: H=home (College Park Center/AAC), A=away
# Back-to-backs and long road trips flagged per schedule notes
# Time zone differences from Dallas (CT): ET=+1, PT=-1, MT=0, CT=0, Toronto=+1

wings_2026 = [
    # May
    ("2026-05-09", "Indiana Fever",      "away", "Gainbridge Fieldhouse",    0, 0, 1, "WNBA", 1, 0),
    ("2026-05-12", "Atlanta Dream",      "home", "College Park Center",      0, 3, 0, "WNBA", 0, 0),
    ("2026-05-14", "Minnesota Lynx",     "home", "College Park Center",      0, 2, 0, "WNBA", 0, 0),
    ("2026-05-18", "Washington Mystics", "home", "College Park Center",      0, 4, 0, "WNBA", 1, 0),
    ("2026-05-20", "Chicago Sky",        "away", "Wintrust Arena",           0, 2, 1, "WNBA", 1, 0),
    ("2026-05-22", "Atlanta Dream",      "away", "State Farm Arena",         0, 2, 1, "WNBA", 1, 0),
    ("2026-05-24", "New York Liberty",   "away", "Barclays Center",          0, 2, 1, "WNBA", 1, 0),
    ("2026-05-28", "Las Vegas Aces",     "home", "College Park Center",      0, 4, 0, "WNBA", 2, 0),
    # June
    ("2026-06-01", "Seattle Storm",      "home", "College Park Center",      0, 4, 0, "WNBA", 2, 0),
    ("2026-06-05", "Los Angeles Sparks", "away", "Crypto.com Arena",         0, 4, 1, "WNBA",-1, 0),
    ("2026-06-09", "Minnesota Lynx",     "away", "Target Center",            0, 4, 1, "WNBA", 0, 0),
    ("2026-06-11", "Phoenix Mercury",    "home", "College Park Center",      0, 2, 0, "WNBA", 1, 0),
    ("2026-06-13", "Portland Fire",      "away", "Moda Center",              0, 2, 1, "WNBA",-1, 0),
    ("2026-06-15", "Las Vegas Aces",     "home", "College Park Center",      0, 2, 0, "WNBA", 2, 0),
    ("2026-06-17", "Golden State Valkyries","away","Chase Center",           0, 2, 1, "WNBA",-1, 0),
    ("2026-06-20", "Chicago Sky",        "home", "College Park Center",      0, 3, 0, "WNBA", 1, 0),
    ("2026-06-22", "Seattle Storm",      "away", "Climate Pledge Arena",     0, 2, 1, "WNBA",-1, 0),
    ("2026-06-25", "Las Vegas Aces",     "away", "Michelob Ultra Arena",     0, 3, 1, "WNBA", 2, 0),
    ("2026-06-28", "Minnesota Lynx",     "home", "College Park Center",      0, 3, 0, "WNBA", 0, 0),
    # July — road trip: CON, TOR, NYL, TOR (4 consecutive away)
    ("2026-07-02", "Connecticut Sun",    "away", "PeoplesBank Arena",        0, 4, 1, "WNBA", 1, 0),
    ("2026-07-05", "Toronto Tempo",      "away", "Coca-Cola Coliseum",       0, 3, 1, "WNBA", 1, 0),
    ("2026-07-07", "New York Liberty",   "away", "Barclays Center",          1, 2, 1, "WNBA", 1, 0),  # B2B
    ("2026-07-10", "Toronto Tempo",      "away", "Bell Centre Montreal",     1, 3, 1, "WNBA", 1, 0),  # B2B (note: MTL venue)
    ("2026-07-12", "Chicago Sky",        "home", "American Airlines Center", 0, 2, 0, "WNBA", 1, 0),  # AAC game
    ("2026-07-16", "New York Liberty",   "home", "College Park Center",      0, 4, 0, "WNBA", 1, 0),
    ("2026-07-19", "Los Angeles Sparks", "home", "College Park Center",      0, 3, 0, "WNBA", 1, 0),
    ("2026-07-22", "Portland Fire",      "away", "Moda Center",              0, 3, 1, "WNBA",-1, 0),
    ("2026-07-25", "Golden State Valkyries","away","Chase Center",           0, 3, 1, "WNBA",-1, 0),
    ("2026-07-29", "Atlanta Dream",      "home", "College Park Center",      0, 4, 0, "WNBA", 0, 0),
    ("2026-07-31", "Washington Mystics", "away", "Capital One Arena",        0, 2, 1, "WNBA", 1, 0),
    # August — homestand of 6: AAC, home, home, home, home, home
    ("2026-08-02", "Connecticut Sun",    "home", "College Park Center",      0, 2, 0, "WNBA", 1, 0),
    ("2026-08-05", "Washington Mystics", "away", "Capital One Arena",        0, 3, 1, "WNBA", 1, 0),
    ("2026-08-07", "Golden State Valkyries","home","American Airlines Center",0,2, 0, "WNBA", 1, 0),  # AAC
    ("2026-08-09", "Minnesota Lynx",     "away", "Target Center",            0, 2, 1, "WNBA", 0, 0),
    ("2026-08-12", "Toronto Tempo",      "home", "College Park Center",      0, 3, 0, "WNBA", 1, 0),
    ("2026-08-14", "Indiana Fever",      "away", "Gainbridge Fieldhouse",    0, 2, 1, "WNBA", 1, 0),
    ("2026-08-17", "Golden State Valkyries","away","Chase Center",           0, 3, 1, "WNBA",-1, 0),
    ("2026-08-20", "Indiana Fever",      "home", "American Airlines Center", 0, 3, 0, "WNBA", 1, 0),  # AAC
    ("2026-08-23", "Seattle Storm",      "home", "College Park Center",      0, 3, 0, "WNBA",-1, 0),
    ("2026-08-25", "Portland Fire",      "home", "College Park Center",      1, 2, 0, "WNBA",-1, 0),  # B2B
    ("2026-08-30", "Connecticut Sun",    "home", "College Park Center",      0, 5, 0, "WNBA", 1, 0),  # last pre-FIBA
    # FIBA Women's World Cup break: Aug 31 – Sep 16 (no games)
    # September — return from FIBA break
    ("2026-09-17", "Los Angeles Sparks", "home", "College Park Center",      0,18, 0, "WNBA",-1, 0),  # long rest after FIBA
    ("2026-09-19", "Phoenix Mercury",    "home", "College Park Center",      1, 2, 0, "WNBA", 1, 0),  # B2B
    ("2026-09-21", "Phoenix Mercury",    "away", "Footprint Center",         1, 2, 1, "WNBA", 1, 0),  # B2B
    ("2026-09-23", "Seattle Storm",      "away", "Climate Pledge Arena",     0, 2, 1, "WNBA",-1, 0),  # final game
]

# Unrivaled 2026 context — players who came in from Unrivaled
# G1 (Breeze BC) and G2 (Mist BC) played Jan 5 – Mar 4 Unrivaled season
# WNBA camp starts ~Apr 28 — ~55 day gap but different movement demands
unrivaled_context = [
    # Approximate Unrivaled game dates for tracking (3-on-3, 72ft court, 18s clock)
    ("2026-01-05", "Unrivaled Opening", "away", "Mohegan Sun Arena", 0, 0, 1, "Unrivaled", 1, 0),
    ("2026-01-09", "Unrivaled Week 2",  "away", "Mohegan Sun Arena", 0, 4, 1, "Unrivaled", 1, 0),
    ("2026-01-16", "Unrivaled Week 3",  "away", "Mohegan Sun Arena", 0, 7, 1, "Unrivaled", 1, 0),
    ("2026-01-23", "Unrivaled Week 4",  "away", "Mohegan Sun Arena", 0, 7, 1, "Unrivaled", 1, 0),
    ("2026-01-30", "Unrivaled Week 5",  "away", "Mohegan Sun Arena", 0, 7, 1, "Unrivaled", 1, 0),
    ("2026-02-06", "Unrivaled Week 6",  "away", "Mohegan Sun Arena", 0, 7, 1, "Unrivaled", 1, 0),
    ("2026-02-13", "Unrivaled Week 7",  "away", "Mohegan Sun Arena", 0, 7, 1, "Unrivaled", 1, 0),
    ("2026-02-20", "Unrivaled Week 8",  "away", "Mohegan Sun Arena", 0, 7, 1, "Unrivaled", 1, 0),
    ("2026-02-27", "Unrivaled Finals",  "away", "Mohegan Sun Arena", 0, 7, 1, "Unrivaled", 1, 0),
]

all_games = wings_2026 + unrivaled_context
cursor.executemany("""
    INSERT INTO schedule (date, opponent, location, venue, is_back_to_back,
        days_rest, travel_flag, game_type, time_zone_diff, fiba_break)
    VALUES (?,?,?,?,?,?,?,?,?,?)
""", all_games)

# Mark FIBA break games (Aug 31 – Sep 16)
cursor.execute("""
    UPDATE schedule SET fiba_break = 1
    WHERE date BETWEEN '2026-08-31' AND '2026-09-16'
""")

conn.commit()
print(f"✓ Schedule table: {len(all_games)} games ({len(wings_2026)} WNBA + {len(unrivaled_context)} Unrivaled)")
print("  Back-to-backs flagged: May 9 (none), July 7+10, Aug 25, Sept 19+21")
print("  AAC venue games: July 12, Aug 7, Aug 20")
print("  FIBA break: Aug 31 – Sep 16 (18 days rest before Sept 17 return)")

# 11. SUMMARY
# ==============================================================================

print("\n" + "=" * 60)
print("DATABASE GENERATION COMPLETE")
print("=" * 60)

counts = {
    "Players":       cursor.execute("SELECT COUNT(*) FROM players").fetchone()[0],
    "Wellness":      cursor.execute("SELECT COUNT(*) FROM wellness").fetchone()[0],
    "Training Load": cursor.execute("SELECT COUNT(*) FROM training_load").fetchone()[0],
    "ACWR":          cursor.execute("SELECT COUNT(*) FROM acwr").fetchone()[0],
    "Force Plate":   cursor.execute("SELECT COUNT(*) FROM force_plate").fetchone()[0],
    "Injuries":      cursor.execute("SELECT COUNT(*) FROM injuries").fetchone()[0],
    "Availability":  cursor.execute("SELECT COUNT(*) FROM availability").fetchone()[0],
}

total = sum(v for k, v in counts.items() if k != "Players")
for k, v in counts.items():
    print(f"   {k:<16} {v:>6}")
print(f"   {'Total records':<16} {total:>6,}")

db_kb = os.path.getsize("waims_demo.db") / 1024
print(f"\n✅ waims_demo.db  ({db_kb:.0f} KB)")
print("\n🎯 Next Steps:")
print("   1. python train_models.py")
print("   2. streamlit run dashboard.py")

conn.close()
print("\n" + "=" * 60)