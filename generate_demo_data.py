"""
WAIMS Demo Data Generator — 2025 Dallas Wings inspired roster (anonymized)
All player IDs match the ath_key format used in athlete_profile_tab.py (ath_001 etc.)

Real roster mapped to anonymized IDs:
  ath_001 = Arike Ogunbowale    (G,  27, 5'7")
  ath_002 = Paige Bueckers      (G,  23, 6'0")
  ath_003 = NaLyssa Smith       (F,  25, 6'4")  — traded mid-season
  ath_004 = Myisha Hines-Allen  (F,  29, 6'1")
  ath_005 = DiJonai Carrington  (G/F,27, 6'0")
  ath_006 = Tyasha Harris       (G,  28, 5'9")
  ath_007 = Kaila Charles       (G/F,26, 6'1")
  ath_008 = Maddy Siegrist      (F,  24, 6'1")
  ath_009 = Aziaha James        (G,  22, 5'10")
  ath_010 = Yueru Li            (C,  24, 6'4")
  ath_011 = Teaira McCowan      (C,  29, 6'7")
  ath_012 = Luisa Geiselsoder   (F,  25, 6'3")

Run:  python generate_demo_data.py
Then: python train_models.py
Then: streamlit run dashboard.py
"""

import sqlite3
import numpy as np
import pandas as pd
from datetime import date, timedelta
import random

random.seed(42)
np.random.seed(42)

DB_PATH    = "waims_demo.db"
START_DATE = date(2025, 4, 28)   # Training camp
END_DATE   = date(2025, 7, 26)   # ~90 days
DATES      = [START_DATE + timedelta(days=i) for i in range((END_DATE - START_DATE).days + 1)]

# ==============================================================================
# ROSTER — anonymized, IDs match ath_key in athlete_profile_tab.py
# Cols: pid, anon_name, pos, age, ht_in, wt_lb, inj_hist,
#       cmj_base, rsi_base, sleep_base, yrs_exp, is_starter
# ==============================================================================

ROSTER = [
    # pid        name           pos    age ht   wt   inj  cmj   rsi    slp  exp  starter
    ("ath_001", "Player_01",   "G",    27, 67, 163,   1,  40.5, 0.52,  7.6,  7,  True ),  # Arike — high motor, high mileage
    ("ath_002", "Player_02",   "G",    23, 72, 170,   0,  41.2, 0.51,  8.2,  1,  True ),  # Bueckers — elite athlete, rookie
    ("ath_003", "Player_03",   "F",    25, 76, 185,   1,  33.5, 0.40,  7.5,  3,  True ),  # NaLyssa — powerful, injury flag
    ("ath_004", "Player_04",   "F",    29, 73, 180,   2,  31.8, 0.38,  7.2,  7,  True ),  # Hines-Allen — veteran, durable
    ("ath_005", "Player_05",   "G/F",  27, 72, 172,   1,  37.8, 0.47,  7.5,  5,  True ),  # Carrington — athletic wing
    ("ath_006", "Player_06",   "G",    28, 69, 158,   1,  37.0, 0.46,  7.0,  6,  False),  # T.Harris — veteran PG, back issues
    ("ath_007", "Player_07",   "G/F",  26, 73, 172,   1,  36.5, 0.45,  7.6,  4,  False),  # Kaila Charles — waived/re-signed
    ("ath_008", "Player_08",   "F",    24, 73, 175,   0,  34.0, 0.41,  7.8,  2,  False),  # Siegrist — efficient scorer
    ("ath_009", "Player_09",   "G",    22, 70, 160,   0,  38.5, 0.48,  8.1,  1,  False),  # Aziaha James — rookie
    ("ath_010", "Player_10",   "C",    24, 76, 205,   0,  28.8, 0.31,  7.9,  2,  True ),  # Yueru Li — mobile big
    ("ath_011", "Player_11",   "C",    29, 79, 225,   2,  26.5, 0.28,  7.3,  7,  False),  # McCowan — physical center
    ("ath_012", "Player_12",   "F",    25, 75, 185,   0,  32.0, 0.39,  7.7,  1,  False),  # Geiselsoder — versatile rookie
]

# ==============================================================================
# SCHEDULE CONTEXT
# ==============================================================================

def get_phase(d):
    delta = (d - START_DATE).days
    if delta < 14:   return "training_camp"
    elif delta < 28: return "preseason"
    else:            return "regular_season"

GAME_DAYS = set()
for i, d in enumerate(DATES):
    phase = get_phase(d)
    if phase == "preseason" and i % 5 == 0:
        GAME_DAYS.add(d)
    elif phase == "regular_season":
        if d.weekday() in (1, 3, 5) and random.random() < 0.75:
            GAME_DAYS.add(d)

BACK_TO_BACK = set()
game_list = sorted(GAME_DAYS)
for i in range(1, len(game_list)):
    if (game_list[i] - game_list[i-1]).days == 1:
        BACK_TO_BACK.add(game_list[i])

# Travel days (day after away game — approx 40% of games are away)
TRAVEL_DAYS = set()
for i, gd in enumerate(game_list):
    if random.random() < 0.40:
        travel = gd + timedelta(days=1)
        if travel <= END_DATE:
            TRAVEL_DAYS.add(travel)

print(f"Generating {len(DATES)} days x {len(ROSTER)} players")
print(f"Game days: {len(GAME_DAYS)} | Back-to-backs: {len(BACK_TO_BACK)} | Travel days: {len(TRAVEL_DAYS)}")

# ==============================================================================
# HELPERS
# ==============================================================================

def clamp(val, lo, hi): return max(lo, min(hi, val))

def fatigue_score(day_idx, recent_game_count, is_b2b, is_travel):
    base = 1.0 - (recent_game_count * 0.055)
    if day_idx < 14: base -= (day_idx / 14) * 0.12   # camp ramp
    if is_b2b:       base -= 0.12
    if is_travel:    base -= 0.06
    return clamp(base, 0.35, 1.0)

# ==============================================================================
# BUILD ALL TABLES
# ==============================================================================

players_rows       = []
wellness_rows      = []
training_load_rows = []
force_plate_rows   = []
acwr_rows          = []
injury_rows        = []
availability_rows  = []

injury_id = 1

for (pid, name, pos, age, ht, wt, inj_hist,
     cmj_base, rsi_base, sleep_base, yrs_exp, is_starter) in ROSTER:

    rng = np.random.default_rng(sum(ord(c) for c in pid))

    players_rows.append({
        "player_id":            pid,
        "name":                 name,
        "position":             pos,
        "age":                  age,
        "height_inches":        ht,
        "weight_lbs":           wt,
        "injury_history_count": inj_hist,
        "years_experience":     yrs_exp,
        "is_starter":           int(is_starter),
    })

    daily_loads   = []
    injured_until = None   # tracks return-to-play date

    for day_idx, d in enumerate(DATES):
        phase     = get_phase(d)
        is_game   = d in GAME_DAYS
        is_b2b    = d in BACK_TO_BACK
        is_travel = d in TRAVEL_DAYS
        d_str     = d.isoformat()

        recent_games = sum(1 for gd in GAME_DAYS if 0 < (d - gd).days <= 7)
        fatigue      = fatigue_score(day_idx, recent_games, is_b2b, is_travel)

        # ── AVAILABILITY STATUS ───────────────────────────────────────
        if injured_until and d <= injured_until:
            avail_status = "OUT"
            avail_pct    = 0
        elif injured_until and d <= injured_until + timedelta(days=5):
            avail_status = "QUESTIONABLE"
            avail_pct    = 50
        else:
            injured_until = None
            if is_b2b and inj_hist >= 2:
                avail_status = "QUESTIONABLE"
                avail_pct    = 75
            else:
                avail_status = "AVAILABLE"
                avail_pct    = 100

        availability_rows.append({
            "player_id":       pid,
            "date":            d_str,
            "status":          avail_status,
            "availability_pct":avail_pct,
            "practice_status": "Full" if avail_pct == 100 else ("Limited" if avail_pct > 0 else "DNP"),
        })

        # ── WELLNESS ──────────────────────────────────────────────────
        sleep_adj = sleep_base * fatigue
        if is_b2b:    sleep_adj -= 0.9
        if is_travel: sleep_adj -= 0.5
        if is_game:   sleep_adj -= 0.3
        if age > 27:  sleep_adj -= 0.15
        sleep_hours   = clamp(rng.normal(sleep_adj, 0.55), 4.5, 10.0)
        sleep_quality = clamp(rng.normal(sleep_hours / 10 * 7 + 1, 0.8), 1, 10)

        soreness_base = 3.5 + (1 - fatigue) * 4.5
        if is_b2b:        soreness_base += 1.8
        if is_game:       soreness_base += 0.9
        if inj_hist >= 2: soreness_base += 0.6
        soreness = clamp(rng.normal(soreness_base, 1.0), 1, 10)

        stress_base = 3.0 + (1 - fatigue) * 2.5
        if phase == "training_camp": stress_base += 0.8
        if is_game:                  stress_base -= 0.3   # game day focus
        stress = clamp(rng.normal(stress_base, 1.0), 1, 10)

        mood_base = 7.2 * fatigue
        if is_game:   mood_base += 0.6
        if is_b2b:    mood_base -= 0.9
        if is_travel: mood_base -= 0.4
        mood = clamp(rng.normal(mood_base, 0.9), 1, 10)

        # HRV: higher is better, degrades with fatigue/age
        hrv_base = 68 - (1 - fatigue) * 22 - (age - 22) * 0.6
        hrv      = clamp(rng.normal(hrv_base, 5), 30, 98)

        wellness_rows.append({
            "player_id":    pid,
            "date":         d_str,
            "sleep_hours":  round(sleep_hours, 2),
            "sleep_quality":round(sleep_quality, 1),
            "soreness":     round(soreness, 1),
            "stress":       round(stress, 1),
            "mood":         round(mood, 1),
            "hrv":          round(hrv, 1),
        })

        # ── TRAINING LOAD + GPS ───────────────────────────────────────
        if avail_status == "OUT":
            # Injured — rehab load only
            practice_mins = clamp(rng.normal(25, 8), 0, 45)
            practice_rpe  = clamp(rng.normal(3.5, 0.5), 1, 5)
            game_mins     = 0
            game_rpe      = 0
            dist_km       = clamp(rng.normal(1.8, 0.4), 0.5, 3.0)
            hsr_m         = clamp(rng.normal(80,  30),  0,   200)
            sprint_m      = clamp(rng.normal(20,  10),  0,   60)
            accel         = int(clamp(rng.normal(8, 3),  2, 20))
            decel         = int(clamp(rng.normal(7, 3),  2, 18))
            p_load        = clamp(rng.normal(120, 25),  40, 220)
        elif is_game:
            practice_mins = 0
            practice_rpe  = 0
            base_mins     = 34 if is_starter else 18
            game_mins     = clamp(rng.normal(base_mins, 5), 0, 40)
            if pos == "C": game_mins = clamp(rng.normal(base_mins - 6, 5), 0, 32)
            game_rpe      = clamp(rng.normal(7.8, 0.7), 5, 10)
            dist_km       = clamp(rng.normal(6.8, 0.7), 4.0, 9.5)
            hsr_m         = clamp(rng.normal(920, 130), 300, 1600)
            sprint_m      = clamp(rng.normal(230, 55),  50,  480)
            accel         = int(clamp(rng.normal(42, 7),  20, 72))
            decel         = int(clamp(rng.normal(38, 7),  18, 68))
            p_load        = clamp(rng.normal(640, 65),  380, 920)
        else:
            load_map = {"training_camp": (112, 7.2), "preseason": (90, 6.6), "regular_season": (75, 6.0)}
            base_m, base_rpe = load_map[phase]
            practice_mins = clamp(rng.normal(base_m * fatigue, 12), 20, 135)
            practice_rpe  = clamp(rng.normal(base_rpe, 0.8), 3, 9)
            game_mins = 0; game_rpe = 0
            dist_km   = clamp(rng.normal(5.0 * fatigue, 0.7), 1.5, 8.0)
            hsr_m     = clamp(rng.normal(580 * fatigue, 110), 80, 1200)
            sprint_m  = clamp(rng.normal(145 * fatigue, 45),  10, 380)
            accel     = int(clamp(rng.normal(30 * fatigue, 6), 6, 62))
            decel     = int(clamp(rng.normal(28 * fatigue, 6), 5, 58))
            p_load    = clamp(rng.normal(440 * fatigue, 65), 100, 800)

        total_daily_load = round((practice_mins * practice_rpe + game_mins * game_rpe), 1)
        daily_loads.append(total_daily_load)

        training_load_rows.append({
            "player_id":          pid,
            "date":               d_str,
            "practice_minutes":   round(practice_mins, 1),
            "practice_rpe":       round(practice_rpe, 1),
            "game_minutes":       round(game_mins, 1),
            "game_rpe":           round(game_rpe, 1) if game_mins > 0 else 0,
            "total_daily_load":   total_daily_load,
            # Kinexon GPS
            "total_distance_km":  round(dist_km, 2),
            "hsr_distance_m":     round(hsr_m, 0),
            "sprint_distance_m":  round(sprint_m, 0),
            "accel_count":        accel,
            "decel_count":        decel,
            "player_load":        round(p_load, 1),
        })

        # ── ACWR ──────────────────────────────────────────────────────
        if day_idx >= 7:
            acute   = np.mean(daily_loads[-7:])
            chronic = np.mean(daily_loads[max(0, day_idx - 28):day_idx]) if day_idx >= 14 else acute
            acwr_val = round(acute / chronic, 3) if chronic > 0 else 1.0
        else:
            acwr_val = round(rng.normal(1.05, 0.08), 3)

        acwr_rows.append({
            "player_id": pid,
            "date":      d_str,
            "acwr":      clamp(acwr_val, 0.4, 2.2),
        })

        # ── FORCE PLATE (skipped ~15% non-game days, always on game days) ──
        if not is_game and rng.random() < 0.15:
            continue

        cmj_adj = cmj_base * fatigue
        if is_b2b:    cmj_adj *= 0.92
        if is_game:   cmj_adj *= 0.97
        if is_travel: cmj_adj *= 0.96
        if day_idx < 14: cmj_adj *= (0.88 + day_idx * 0.009)   # camp ramp

        cmj_height = clamp(rng.normal(cmj_adj, cmj_base * 0.04), cmj_base * 0.68, cmj_base * 1.12)
        rsi_adj    = rsi_base * fatigue
        if is_b2b:    rsi_adj *= 0.90
        if is_travel: rsi_adj *= 0.94
        rsi_val  = clamp(rng.normal(rsi_adj, rsi_base * 0.05), rsi_base * 0.62, rsi_base * 1.14)
        asym     = clamp(abs(rng.normal(4.2, 2.8)), 0, 20)
        ft_ms    = clamp(rng.normal(cmj_height * 9.1, 8), 190, 490)
        ct_ms    = clamp(rng.normal(238, 22), 175, 325)

        force_plate_rows.append({
            "player_id":       pid,
            "date":            d_str,
            "cmj_height_cm":   round(cmj_height, 2),
            "rsi_modified":    round(rsi_val, 3),
            "asymmetry_index": round(asym, 1),
            "flight_time_ms":  round(ft_ms, 0),
            "contact_time_ms": round(ct_ms, 0),
        })

    # ── INJURIES ──────────────────────────────────────────────────────
    inj_types = {
        "G":   ["Ankle Sprain", "Hamstring Strain", "Knee Contusion"],
        "G/F": ["Ankle Sprain", "Hip Flexor Strain", "Knee Contusion"],
        "F":   ["Quad Strain",  "Hip Flexor Strain", "Back Tightness"],
        "C":   ["Back Tightness","Knee Contusion",   "Foot Soreness"],
    }
    inj_chance = 0.12 + inj_hist * 0.10 + (0.05 if age > 27 else 0)
    if rng.random() < inj_chance:
        inj_day    = int(rng.integers(30, len(DATES) - 15))
        inj_date   = (START_DATE + timedelta(days=inj_day))
        days_missed= int(clamp(rng.normal(8, 4), 2, 21))
        return_date= inj_date + timedelta(days=days_missed)
        inj_type   = str(rng.choice(inj_types.get(pos, ["Ankle Sprain"])))
        injury_rows.append({
            "injury_id":   f"INJ_{injury_id:03d}",
            "player_id":   pid,
            "injury_date": inj_date.isoformat(),
            "return_date": return_date.isoformat(),
            "injury_type": inj_type,
            "body_part":   inj_type.split()[0],
            "severity":    "Mild" if days_missed < 5 else ("Moderate" if days_missed < 14 else "Severe"),
            "days_missed": days_missed,
            "mechanism":   "Non-contact",
        })
        injury_id += 1

        # Back-fill availability for injured period
        for av_row in availability_rows:
            if av_row["player_id"] == pid:
                row_date = date.fromisoformat(av_row["date"])
                if inj_date <= row_date <= return_date:
                    av_row["status"]          = "OUT"
                    av_row["availability_pct"]= 0
                    av_row["practice_status"] = "DNP"
                elif return_date < row_date <= return_date + timedelta(days=5):
                    av_row["status"]          = "QUESTIONABLE"
                    av_row["availability_pct"]= 50
                    av_row["practice_status"] = "Limited"

# ==============================================================================
# WRITE TO DATABASE
# ==============================================================================

print("\nWriting to database...")
conn = sqlite3.connect(DB_PATH)
c    = conn.cursor()

c.executescript("""
DROP TABLE IF EXISTS players;
DROP TABLE IF EXISTS wellness;
DROP TABLE IF EXISTS training_load;
DROP TABLE IF EXISTS force_plate;
DROP TABLE IF EXISTS acwr;
DROP TABLE IF EXISTS injuries;
DROP TABLE IF EXISTS availability;
DROP TABLE IF EXISTS ml_predictions;

CREATE TABLE players (
    player_id             TEXT PRIMARY KEY,
    name                  TEXT,
    position              TEXT,
    age                   INTEGER,
    height_inches         INTEGER,
    weight_lbs            INTEGER,
    injury_history_count  INTEGER,
    years_experience      INTEGER,
    is_starter            INTEGER
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
    return_date TEXT,
    injury_type TEXT,
    body_part   TEXT,
    severity    TEXT,
    days_missed INTEGER,
    mechanism   TEXT
);

CREATE TABLE availability (
    player_id        TEXT,
    date             TEXT,
    status           TEXT,
    availability_pct INTEGER,
    practice_status  TEXT
);
""")

pd.DataFrame(players_rows).to_sql("players",        conn, if_exists="append", index=False)
pd.DataFrame(wellness_rows).to_sql("wellness",       conn, if_exists="append", index=False)
pd.DataFrame(training_load_rows).to_sql("training_load", conn, if_exists="append", index=False)
pd.DataFrame(force_plate_rows).to_sql("force_plate", conn, if_exists="append", index=False)
pd.DataFrame(acwr_rows).to_sql("acwr",               conn, if_exists="append", index=False)
pd.DataFrame(injury_rows).to_sql("injuries",         conn, if_exists="append", index=False)
pd.DataFrame(availability_rows).to_sql("availability",conn, if_exists="append", index=False)

conn.commit()
conn.close()

# ==============================================================================
# SUMMARY
# ==============================================================================

total_rows = (len(wellness_rows) + len(training_load_rows) +
              len(force_plate_rows) + len(acwr_rows) + len(availability_rows))

print("\n" + "=" * 60)
print("DEMO DATA GENERATION COMPLETE")
print("=" * 60)
print(f"  Players         : {len(players_rows)}")
print(f"  Wellness        : {len(wellness_rows):,}")
print(f"  Training load   : {len(training_load_rows):,}  (incl. GPS)")
print(f"  Force plate     : {len(force_plate_rows):,}")
print(f"  ACWR            : {len(acwr_rows):,}")
print(f"  Availability    : {len(availability_rows):,}")
print(f"  Injuries        : {len(injury_rows)}")
print(f"  Total rows      : {total_rows:,}")
print(f"  Date range      : {START_DATE} → {END_DATE} ({len(DATES)} days)")
print(f"  Game days       : {len(GAME_DAYS)}  Back-to-backs: {len(BACK_TO_BACK)}  Travel days: {len(TRAVEL_DAYS)}")
print()
print("  Player IDs (match ath_key in athlete_profile_tab.py):")
for pid, name, pos, age, *_ in ROSTER:
    print(f"    {pid}  →  {name}  ({pos}, age {age})")
print()
print("  New tables/fields:")
print("    availability: status, availability_pct, practice_status")
print("    training_load: total_distance_km, hsr_distance_m,")
print("                   sprint_distance_m, accel_count, decel_count, player_load")
print("    wellness: hrv")
print("    force_plate: asymmetry_index, flight_time_ms, contact_time_ms")
print("    injuries: return_date added")
print()
print("  Next steps:")
print("    python train_models.py")
print("    streamlit run dashboard.py")
print("=" * 60)


