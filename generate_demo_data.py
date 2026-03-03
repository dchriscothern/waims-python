"""
WAIMS Demo Data Generator — Dallas Wings inspired roster (anonymized)
Generates 90 days of realistic WNBA training camp + regular season data.

Roster based on 2025 Dallas Wings positional profiles:
  - Names anonymized (Player_01 … Player_12)
  - Ages, positions, body types match real roster archetypes
  - CMJ/RSI, GPS, wellness values tuned to WNBA norms

Run:  python generate_demo_data.py
"""

import sqlite3
import numpy as np
import pandas as pd
from datetime import date, timedelta
import random

random.seed(42)
np.random.seed(42)

# ==============================================================================
# CONFIG
# ==============================================================================

DB_PATH    = "waims_demo.db"
START_DATE = date(2025, 4, 28)   # Training camp opens
END_DATE   = date(2025, 7, 26)   # ~90 days through regular season
DATES      = [START_DATE + timedelta(days=i) for i in range((END_DATE - START_DATE).days + 1)]

# ==============================================================================
# ROSTER  (anonymized Dallas Wings archetypes)
# Positions: G=Guard, G/F=Wing, F=Forward, C=Center
# CMJ baseline: Guards 36-42cm, Wings 33-38cm, Forwards 30-35cm, Centers 27-32cm
# RSI baseline: Guards 0.45-0.55, Wings 0.40-0.50, Forwards 0.35-0.44, Centers 0.28-0.36
# ==============================================================================

ROSTER = [
    # pid    anon_name      pos    age  ht_in  wt_lb  inj_hist  cmj_base  rsi_base  sleep_base  note
    ("P01", "Player_01",   "G",    25,   72,   165,     0,       41.5,     0.52,      7.8,   "Elite scorer, high motor"),   # Arike archetype
    ("P02", "Player_02",   "G",    23,   72,   170,     0,       40.2,     0.50,      8.1,   "Rookie franchise guard"),      # Bueckers archetype
    ("P03", "Player_03",   "F",    25,   76,   185,     1,       33.8,     0.40,      7.5,   "Power forward, strong post"),  # NaLyssa archetype
    ("P04", "Player_04",   "F",    29,   73,   180,     2,       32.5,     0.38,      7.2,   "Veteran wing, injury prone"),  # Hines-Allen archetype
    ("P05", "Player_05",   "G/F",  26,   73,   172,     1,       37.0,     0.46,      7.6,   "Versatile wing defender"),     # Kaila Charles archetype
    ("P06", "Player_06",   "F",    27,   75,   190,     1,       31.2,     0.37,      7.4,   "Athletic forward, 3&D"),       # Joyner Holmes archetype
    ("P07", "Player_07",   "C",    24,   76,   205,     0,       28.5,     0.30,      7.9,   "Rim protector, mobile big"),   # Yueru Li archetype
    ("P08", "Player_08",   "G",    28,   70,   158,     2,       38.5,     0.48,      6.9,   "Veteran PG, high mileage"),
    ("P09", "Player_09",   "G/F",  22,   74,   168,     0,       39.0,     0.49,      8.2,   "Young wing, high upside"),
    ("P10", "Player_10",   "F",    31,   74,   188,     3,       30.0,     0.35,      7.0,   "Veteran forward, injury hist"),
    ("P11", "Player_11",   "C",    26,   77,   215,     1,       27.0,     0.29,      7.6,   "Backup center, physical"),
    ("P12", "Player_12",   "G",    24,   71,   163,     0,       39.8,     0.50,      7.7,   "Shooting guard, spot-up"),
]

# Season schedule context — affects load patterns
# Training camp: days 0-13, Pre-season: 14-27, Regular season: 28+
def get_phase(d):
    delta = (d - START_DATE).days
    if delta < 14:   return "training_camp"
    elif delta < 28: return "preseason"
    else:            return "regular_season"

# Game days (approximate WNBA schedule — ~3 games/week in reg season)
GAME_DAYS = set()
for i, d in enumerate(DATES):
    if get_phase(d) == "preseason" and i % 5 == 0:
        GAME_DAYS.add(d)
    elif get_phase(d) == "regular_season":
        # Games roughly Tue/Thu/Sat pattern
        if d.weekday() in (1, 3, 5) and random.random() < 0.75:
            GAME_DAYS.add(d)

# Back-to-backs (consecutive game days)
BACK_TO_BACK = set()
game_list = sorted(GAME_DAYS)
for i in range(1, len(game_list)):
    if (game_list[i] - game_list[i-1]).days == 1:
        BACK_TO_BACK.add(game_list[i])

print(f"Generating {len(DATES)} days of data for {len(ROSTER)} players")
print(f"Game days: {len(GAME_DAYS)}  |  Back-to-backs: {len(BACK_TO_BACK)}")

# ==============================================================================
# HELPERS
# ==============================================================================

def clamp(val, lo, hi):
    return max(lo, min(hi, val))

def noisy(base, sd, lo, hi):
    return clamp(np.random.normal(base, sd), lo, hi)

def fatigue_trend(day_idx, game_days_last_7):
    """Returns a fatigue multiplier 0-1 (1=fresh, 0=exhausted)."""
    base = 1.0 - (game_days_last_7 * 0.06)
    # Camp ramp-up fatigue
    if day_idx < 14:
        base -= (day_idx / 14) * 0.15
    return clamp(base, 0.4, 1.0)

# ==============================================================================
# BUILD TABLES
# ==============================================================================

players_rows      = []
wellness_rows     = []
training_load_rows= []
force_plate_rows  = []
acwr_rows         = []
injury_rows       = []

injury_id = 1

for (pid, name, pos, age, ht, wt, inj_hist,
     cmj_base, rsi_base, sleep_base, note) in ROSTER:

    # Per-player random seed for reproducibility
    p_seed = sum(ord(c) for c in pid)
    rng    = np.random.default_rng(p_seed)

    players_rows.append({
        "player_id":            pid,
        "name":                 name,
        "position":             pos,
        "age":                  age,
        "height_inches":        ht,
        "weight_lbs":           wt,
        "injury_history_count": inj_hist,
        "notes":                note,
    })

    # Rolling load for ACWR
    daily_loads = []

    for day_idx, d in enumerate(DATES):
        phase      = get_phase(d)
        is_game    = d in GAME_DAYS
        is_b2b     = d in BACK_TO_BACK
        d_str      = d.isoformat()

        # Games in last 7 days (fatigue context)
        recent_games = sum(1 for gd in GAME_DAYS if 0 < (d - gd).days <= 7)
        fatigue      = fatigue_trend(day_idx, recent_games)

        # ── WELLNESS ──────────────────────────────────────────────────
        # Sleep degrades with fatigue, b2b, and late games
        sleep_sd    = 0.6
        sleep_adj   = sleep_base * fatigue
        if is_b2b:   sleep_adj -= 0.8
        if is_game:  sleep_adj -= 0.3
        # Veteran players sleep less consistently
        if age > 28: sleep_adj -= 0.2
        sleep_hours = clamp(rng.normal(sleep_adj, sleep_sd), 4.5, 10.0)

        sleep_quality = clamp(rng.normal(sleep_hours / 10 * 7 + 1, 0.8), 1, 10)

        soreness_base = 4.0 + (1 - fatigue) * 4.0
        if is_b2b:        soreness_base += 1.5
        if is_game:       soreness_base += 0.8
        if inj_hist >= 2: soreness_base += 0.5
        soreness = clamp(rng.normal(soreness_base, 1.0), 1, 10)

        stress_base = 3.5 + (1 - fatigue) * 2.5
        if phase == "training_camp": stress_base += 0.5
        stress = clamp(rng.normal(stress_base, 1.0), 1, 10)

        mood_base = 7.0 * fatigue
        if is_game:   mood_base += 0.5  # elevated on game days
        if is_b2b:    mood_base -= 0.8
        mood = clamp(rng.normal(mood_base, 0.9), 1, 10)

        hrv_base = 65 - (1 - fatigue) * 20 - (age - 22) * 0.5
        hrv = clamp(rng.normal(hrv_base, 5), 35, 95)

        wellness_rows.append({
            "player_id":     pid,
            "date":          d_str,
            "sleep_hours":   round(sleep_hours, 2),
            "sleep_quality": round(sleep_quality, 1),
            "soreness":      round(soreness, 1),
            "stress":        round(stress, 1),
            "mood":          round(mood, 1),
            "hrv":           round(hrv, 1),
        })

        # ── TRAINING LOAD ─────────────────────────────────────────────
        if is_game:
            practice_mins = 0
            practice_rpe  = 0
            game_mins     = clamp(rng.normal(28, 6), 0, 40) if pos != "C" else clamp(rng.normal(18, 5), 0, 32)
            # Starters play more
            if pid in ("P01", "P02", "P03"):
                game_mins = clamp(rng.normal(34, 4), 20, 40)
            game_rpe = clamp(rng.normal(7.5, 0.8), 5, 10)
        else:
            if phase == "training_camp":
                practice_mins = clamp(rng.normal(110, 15), 60, 140)
                practice_rpe  = clamp(rng.normal(7.0, 0.7), 4, 10)
            elif phase == "preseason":
                practice_mins = clamp(rng.normal(90, 12), 45, 120)
                practice_rpe  = clamp(rng.normal(6.5, 0.8), 4, 10)
            else:
                practice_mins = clamp(rng.normal(75, 12), 30, 105)
                practice_rpe  = clamp(rng.normal(6.0, 0.8), 3, 9)
            game_mins = 0
            game_rpe  = 0

        total_daily_load = round((practice_mins * practice_rpe + game_mins * game_rpe), 1)
        daily_loads.append(total_daily_load)

        training_load_rows.append({
            "player_id":        pid,
            "date":             d_str,
            "practice_minutes": round(practice_mins, 1),
            "practice_rpe":     round(practice_rpe, 1),
            "game_minutes":     round(game_mins, 1),
            "game_rpe":         round(game_rpe, 1) if game_mins > 0 else 0,
            "total_daily_load": total_daily_load,
            # GPS fields
            "total_distance_km":     round(clamp(rng.normal(6.2 if is_game else 4.8, 0.8), 2.0, 9.5), 2),
            "hsr_distance_m":        round(clamp(rng.normal(820 if is_game else 560, 120), 100, 1600), 0),
            "sprint_distance_m":     round(clamp(rng.normal(210 if is_game else 130, 50), 20, 480), 0),
            "accel_count":           int(clamp(rng.normal(38 if is_game else 28, 7), 8, 70)),
            "decel_count":           int(clamp(rng.normal(35 if is_game else 26, 7), 8, 65)),
            "player_load":           round(clamp(rng.normal(580 if is_game else 420, 70), 150, 900), 1),
        })

        # ── ACWR ──────────────────────────────────────────────────────
        if day_idx >= 7:
            acute  = np.mean(daily_loads[-7:])
            chronic= np.mean(daily_loads[max(0, day_idx-28):day_idx]) if day_idx >= 14 else acute
            acwr_val = round(acute / chronic, 3) if chronic > 0 else 1.0
        else:
            acwr_val = round(rng.normal(1.05, 0.08), 3)

        acwr_rows.append({
            "player_id": pid,
            "date":      d_str,
            "acwr":      clamp(acwr_val, 0.4, 2.2),
        })

        # ── FORCE PLATE ───────────────────────────────────────────────
        # Skip rest days ~15% of the time (not tested every day)
        if rng.random() < 0.15 and not is_game:
            continue

        # CMJ degrades with fatigue and b2b
        cmj_adj = cmj_base * fatigue
        if is_b2b:  cmj_adj *= 0.93
        if is_game: cmj_adj *= 0.97
        # Camp ramp — first 2 weeks are lower as body adapts
        if day_idx < 14: cmj_adj *= (0.90 + day_idx * 0.007)

        cmj_height = clamp(rng.normal(cmj_adj, cmj_base * 0.04), cmj_base * 0.70, cmj_base * 1.12)

        # RSI follows CMJ pattern but more sensitive to fatigue
        rsi_adj = rsi_base * fatigue
        if is_b2b:  rsi_adj *= 0.91
        rsi_val = clamp(rng.normal(rsi_adj, rsi_base * 0.05), rsi_base * 0.65, rsi_base * 1.15)

        # Asymmetry index (% difference L vs R) — flags potential injury risk
        asym = clamp(abs(rng.normal(4.5, 2.5)), 0, 18)

        force_plate_rows.append({
            "player_id":       pid,
            "date":            d_str,
            "cmj_height_cm":   round(cmj_height, 2),
            "rsi_modified":    round(rsi_val, 3),
            "asymmetry_index": round(asym, 1),
            "flight_time_ms":  round(clamp(rng.normal(cmj_height * 9.0, 8), 200, 480), 0),
            "contact_time_ms": round(clamp(rng.normal(240, 20), 180, 320), 0),
        })

    # ── INJURIES ──────────────────────────────────────────────────────
    # Simulate 1-2 realistic injuries per high-risk player across the season
    injury_types_by_pos = {
        "G":   ["Ankle Sprain", "Hamstring Strain", "Knee Contusion"],
        "G/F": ["Ankle Sprain", "Hip Flexor Strain", "Knee Contusion"],
        "F":   ["Quad Strain", "Hip Flexor Strain", "Back Tightness"],
        "C":   ["Back Tightness", "Knee Contusion", "Foot Soreness"],
    }
    inj_types = injury_types_by_pos.get(pos, ["Ankle Sprain"])

    # Higher inj_hist → higher chance of in-season injury
    inj_chance = 0.15 + inj_hist * 0.12
    if rng.random() < inj_chance:
        # Injury happens in regular season (day 28+)
        inj_day  = rng.integers(30, len(DATES) - 15)
        inj_date = (START_DATE + timedelta(days=int(inj_day))).isoformat()
        days_missed = int(clamp(rng.normal(8, 4), 2, 21))
        injury_rows.append({
            "injury_id":   f"INJ_{injury_id:03d}",
            "player_id":   pid,
            "injury_date": inj_date,
            "injury_type": rng.choice(inj_types),
            "body_part":   inj_types[0].split()[0],
            "severity":    "Mild" if days_missed < 5 else ("Moderate" if days_missed < 14 else "Severe"),
            "days_missed": days_missed,
            "mechanism":   "Non-contact",
        })
        injury_id += 1

# ==============================================================================
# WRITE TO DATABASE
# ==============================================================================

print("\nWriting to database...")
conn = sqlite3.connect(DB_PATH)
c    = conn.cursor()

# Drop and recreate all tables cleanly
c.executescript("""
DROP TABLE IF EXISTS players;
DROP TABLE IF EXISTS wellness;
DROP TABLE IF EXISTS training_load;
DROP TABLE IF EXISTS force_plate;
DROP TABLE IF EXISTS acwr;
DROP TABLE IF EXISTS injuries;
DROP TABLE IF EXISTS ml_predictions;

CREATE TABLE players (
    player_id             TEXT PRIMARY KEY,
    name                  TEXT,
    position              TEXT,
    age                   INTEGER,
    height_inches         INTEGER,
    weight_lbs            INTEGER,
    injury_history_count  INTEGER,
    notes                 TEXT
);

CREATE TABLE wellness (
    player_id     TEXT,
    date          TEXT,
    sleep_hours   REAL,
    sleep_quality REAL,
    soreness      REAL,
    stress        REAL,
    mood          REAL,
    hrv           REAL
);

CREATE TABLE training_load (
    player_id           TEXT,
    date                TEXT,
    practice_minutes    REAL,
    practice_rpe        REAL,
    game_minutes        REAL,
    game_rpe            REAL,
    total_daily_load    REAL,
    total_distance_km   REAL,
    hsr_distance_m      REAL,
    sprint_distance_m   REAL,
    accel_count         INTEGER,
    decel_count         INTEGER,
    player_load         REAL
);

CREATE TABLE force_plate (
    player_id        TEXT,
    date             TEXT,
    cmj_height_cm    REAL,
    rsi_modified     REAL,
    asymmetry_index  REAL,
    flight_time_ms   REAL,
    contact_time_ms  REAL
);

CREATE TABLE acwr (
    player_id TEXT,
    date      TEXT,
    acwr      REAL
);

CREATE TABLE injuries (
    injury_id   TEXT PRIMARY KEY,
    player_id   TEXT,
    injury_date TEXT,
    injury_type TEXT,
    body_part   TEXT,
    severity    TEXT,
    days_missed INTEGER,
    mechanism   TEXT
);
""")

pd.DataFrame(players_rows).to_sql("players",       conn, if_exists="append", index=False)
pd.DataFrame(wellness_rows).to_sql("wellness",      conn, if_exists="append", index=False)
pd.DataFrame(training_load_rows).to_sql("training_load", conn, if_exists="append", index=False)
pd.DataFrame(force_plate_rows).to_sql("force_plate",conn, if_exists="append", index=False)
pd.DataFrame(acwr_rows).to_sql("acwr",              conn, if_exists="append", index=False)
pd.DataFrame(injury_rows).to_sql("injuries",        conn, if_exists="append", index=False)

conn.commit()
conn.close()

# ==============================================================================
# SUMMARY
# ==============================================================================

print("\n" + "=" * 60)
print("DEMO DATA GENERATION COMPLETE")
print("=" * 60)
print(f"  Players       : {len(players_rows)}")
print(f"  Wellness rows : {len(wellness_rows)}")
print(f"  Training load : {len(training_load_rows)}")
print(f"  Force plate   : {len(force_plate_rows)}")
print(f"  ACWR rows     : {len(acwr_rows)}")
print(f"  Injuries      : {len(injury_rows)}")
print(f"  Date range    : {START_DATE} → {END_DATE} ({len(DATES)} days)")
print(f"  Game days     : {len(GAME_DAYS)}  |  Back-to-backs: {len(BACK_TO_BACK)}")
print(f"\n  CMJ ranges by position:")
print(f"    Guards  : ~36–42 cm  (RSI ~0.45–0.55)")
print(f"    Wings   : ~33–39 cm  (RSI ~0.40–0.50)")
print(f"    Forwards: ~30–35 cm  (RSI ~0.35–0.44)")
print(f"    Centers : ~27–32 cm  (RSI ~0.28–0.36)")
print(f"\n  GPS fields added to training_load:")
print(f"    total_distance_km, hsr_distance_m, sprint_distance_m")
print(f"    accel_count, decel_count, player_load")
print(f"\n  New wellness fields: hrv")
print(f"  New force plate fields: asymmetry_index, flight_time_ms, contact_time_ms")
print(f"\n  Run: python train_models.py  then  streamlit run dashboard.py")
print("=" * 60)
