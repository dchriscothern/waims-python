"""
WAIMS Python Demo - ML Model Training
Trains injury risk predictor and readiness scorer.
Includes per-player z-score deviation features AND GPS/Kinexon metrics
(player_load, accel_count, decel_count) as primary signals.
"""

import os
import pickle
import warnings

import numpy as np
import pandas as pd
import sqlite3
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

print("=" * 60)
print("WAIMS - Training ML Models")
print("=" * 60)

# ==============================================================================
# 1. LOAD DATA
# ==============================================================================

print("\n1. Loading data from database...")

DB_PATH = "waims_demo.db"
conn = sqlite3.connect(DB_PATH)

# Graceful fallback — schedule table exists only when generate_database.py is run.
# Falls back to zero-filled schedule columns if only generate_demo_data.py was run.
_tables = [r[0] for r in conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table'"
).fetchall()]
_has_schedule = "schedule" in _tables

if _has_schedule:
    print("  Schedule table found — including back-to-back, travel, rest features")
    _schedule_join = "LEFT JOIN schedule s ON w.date = s.date"
    _schedule_cols = """
        COALESCE(s.is_back_to_back, 0)                        AS is_back_to_back,
        COALESCE(s.days_rest, 3)                              AS days_rest,
        COALESCE(s.travel_flag, 0)                            AS travel_flag,
        COALESCE(s.time_zone_diff, 0)                         AS time_zone_diff,
        CASE WHEN s.game_type = 'Unrivaled' THEN 1 ELSE 0 END AS unrivaled_flag"""
else:
    print("  WARNING: No schedule table — run generate_database.py for full pipeline")
    print("  Continuing without schedule context (defaulting all to 0)")
    _schedule_join = ""
    _schedule_cols = """
        0 AS is_back_to_back,
        3 AS days_rest,
        0 AS travel_flag,
        0 AS time_zone_diff,
        0 AS unrivaled_flag"""

df = pd.read_sql_query(
    f"""
    SELECT
        p.player_id, p.name, p.position, p.age, p.injury_history_count,
        w.date,
        w.sleep_hours, w.sleep_quality, w.soreness, w.stress, w.mood,
        t.practice_minutes, t.practice_rpe, t.total_daily_load, t.game_minutes,
        t.player_load, t.accel_count, t.decel_count,
        t.total_distance_km, t.hsr_distance_m, t.sprint_distance_m,
        a.acwr,
        f.cmj_height_cm, f.rsi_modified,
        {_schedule_cols}
    FROM players p
    LEFT JOIN wellness w       ON p.player_id = w.player_id
    LEFT JOIN training_load t  ON p.player_id = t.player_id AND w.date = t.date
    LEFT JOIN acwr a           ON p.player_id = a.player_id AND w.date = a.date
    LEFT JOIN force_plate f    ON p.player_id = f.player_id AND w.date = f.date
    {_schedule_join}
    WHERE w.date IS NOT NULL
    """,
    conn,
)

injuries = pd.read_sql_query("SELECT * FROM injuries", conn)

df["injured_within_7days"] = 0
for _, inj in injuries.iterrows():
    inj_date      = pd.to_datetime(inj["injury_date"])
    warning_start = inj_date - pd.Timedelta(days=7)
    mask = (
        (df["player_id"] == inj["player_id"])
        & (pd.to_datetime(df["date"]) >= warning_start)
        & (pd.to_datetime(df["date"]) <= inj_date)
    )
    df.loc[mask, "injured_within_7days"] = 1

print(f"✓ Loaded {len(df)} records")
print(f"  Players    : {df['player_id'].nunique()}")
print(f"  Date range : {df['date'].min()} → {df['date'].max()}")

# Check GPS coverage
gps_cols = ["player_load", "accel_count", "decel_count"]
gps_present = all(c in df.columns and df[c].notna().sum() > 0 for c in gps_cols)
print(f"  GPS data   : {'✓ available' if gps_present else '✗ not found — GPS features will be skipped'}")

# ==============================================================================
# 2. FEATURE ENGINEERING
# ==============================================================================

print("\n2. Engineering features...")

# ── Fill nulls ─────────────────────────────────────────────────────────────────
df["acwr"]          = df["acwr"].fillna(1.0)
df["cmj_height_cm"] = df.groupby("player_id")["cmj_height_cm"].ffill().fillna(30.0)
df["rsi_modified"]  = df["rsi_modified"].fillna(0.35)

if gps_present:
    df["player_load"] = df["player_load"].fillna(df.groupby("player_id")["player_load"].transform("median"))
    df["accel_count"] = df["accel_count"].fillna(df.groupby("player_id")["accel_count"].transform("median"))
    df["decel_count"] = df["decel_count"].fillna(df.groupby("player_id")["decel_count"].transform("median"))
    df["total_distance_km"] = df["total_distance_km"].fillna(df.groupby("player_id")["total_distance_km"].transform("median"))
    df["hsr_distance_m"]    = df["hsr_distance_m"].fillna(0)
    df["sprint_distance_m"] = df["sprint_distance_m"].fillna(0)

# Schedule context null-fill (default to normal practice day if no game scheduled)
for sc_col, sc_default in [("is_back_to_back",0),("days_rest",3),("travel_flag",0),
                            ("time_zone_diff",0),("unrivaled_flag",0)]:
    if sc_col in df.columns:
        df[sc_col] = df[sc_col].fillna(sc_default)

df = df.sort_values(["player_id", "date"])

# ── 7-day rolling averages ─────────────────────────────────────────────────────
rolling_cols = ["sleep_hours", "soreness", "practice_minutes", "cmj_height_cm", "rsi_modified"]
if gps_present:
    rolling_cols += ["player_load", "accel_count", "decel_count"]

for col in rolling_cols:
    df[f"{col}_7day_avg"] = df.groupby("player_id")[col].transform(
        lambda x: x.rolling(7, min_periods=1).mean()
    )
    df[f"{col}_7day_std"] = df.groupby("player_id")[col].transform(
        lambda x: x.rolling(7, min_periods=1).std().fillna(0)
    )

# ── Per-player z-score deviations (expanding baseline, shifted by 1 — no leakage) ──
Z_COLS = {
    "sleep_hours":   0.30,
    "soreness":      0.50,
    "stress":        0.50,
    "mood":          0.50,
    "cmj_height_cm": 0.50,
    "rsi_modified":  0.01,
}
if gps_present:
    Z_COLS.update({
        "player_load": 10.0,   # AU
        "accel_count":  2.0,
        "decel_count":  2.0,
    })

for col, min_std in Z_COLS.items():
    if col not in df.columns:
        continue
    roll_mean = df.groupby("player_id")[col].transform(
        lambda x: x.shift(1).expanding(min_periods=5).mean()
    )
    roll_std = df.groupby("player_id")[col].transform(
        lambda x: x.shift(1).expanding(min_periods=5).std().clip(lower=min_std)
    )
    df[f"{col}_zscore"] = ((df[col] - roll_mean) / roll_std).fillna(0)

# ── Hard-floor binary flags ────────────────────────────────────────────────────
# Sleep floor: updated from <6.5 (Milewski 2014) to <7.0
# Walsh et al. 2021 (BJSM expert consensus): 7-9hrs recommended for elite athletes
# 2025 meta-analysis (OR=1.34): <8hrs associated with elevated injury risk
# Female athletes: compounded by hormonal variability (Charest & Grandner 2020)
df["flag_sleep_floor"]   = (df["sleep_hours"] < 7.0).astype(int)
df["flag_soreness_ceil"] = (df["soreness"] > 7).astype(int)
df["flag_stress_ceil"]   = (df["stress"] > 7).astype(int)
df["flag_acwr_spike"]    = (df["acwr"] > 1.5).astype(int)

# GPS drop flags (≤ −1σ = objective fatigue signal)
if gps_present:
    df["flag_load_drop"]  = (df["player_load_zscore"] <= -1.0).astype(int)
    df["flag_accel_drop"] = (df["accel_count_zscore"]  <= -1.0).astype(int)
    df["flag_decel_drop"] = (df["decel_count_zscore"]  <= -1.0).astype(int)

# ── Composite wellness score ───────────────────────────────────────────────────
df["wellness_score"] = (
    df["sleep_hours"] * 1.5
    + (10 - df["soreness"])
    + (10 - df["stress"])
    + df["mood"]
)

print(f"✓ Created {len(df.columns)} features (z-scores + GPS + flags)")

# ==============================================================================
# 3. FEATURE LIST
# ==============================================================================

feature_cols = [
    # Demographics
    "age", "injury_history_count",
    # Raw wellness
    "sleep_hours", "soreness", "stress", "mood",
    # Training
    "practice_minutes", "practice_rpe", "game_minutes",
    "total_daily_load",  # ACWR demoted — used as flag only (see Impellizzeri et al. 2020)
    # Force plate
    "cmj_height_cm", "rsi_modified",
    # 7-day rolling averages
    "sleep_hours_7day_avg", "soreness_7day_avg",
    "practice_minutes_7day_avg", "cmj_height_cm_7day_avg",
    # Wellness z-scores (primary signal)
    "sleep_hours_zscore", "soreness_zscore", "stress_zscore",
    "mood_zscore", "cmj_height_cm_zscore", "rsi_modified_zscore",
    # Hard-floor flags
    "flag_sleep_floor", "flag_soreness_ceil",
    "flag_stress_ceil", "flag_acwr_spike",  # ACWR spike flag only
    # Schedule context (Morikawa 2022, condensed schedule studies)
    "is_back_to_back", "days_rest", "travel_flag", "time_zone_diff", "unrivaled_flag",
    # Composite
    "wellness_score",
]

# Add GPS features only if present in database
if gps_present:
    feature_cols += [
        # Raw GPS
        "player_load", "accel_count", "decel_count",
        "total_distance_km", "hsr_distance_m",
        # GPS rolling averages
        "player_load_7day_avg", "accel_count_7day_avg", "decel_count_7day_avg",
        # GPS z-scores
        "player_load_zscore", "accel_count_zscore", "decel_count_zscore",
        # GPS drop flags
        "flag_load_drop", "flag_accel_drop", "flag_decel_drop",
    ]
    print(f"   GPS features included: player_load, accel_count, decel_count + z-scores + flags")
else:
    print("   GPS features skipped (columns not found in DB)")

# ==============================================================================
# 4. TRAIN INJURY RISK MODEL
# ==============================================================================

print("\n3. Training Injury Risk Predictor...")

df_model = df[feature_cols + ["injured_within_7days"]].dropna()
X = df_model[feature_cols]
y = df_model["injured_within_7days"]

print(f"   Training samples : {len(X)}")
print(f"   Injury cases     : {y.sum()}")
print(f"   Non-injury cases : {(y == 0).sum()}")
print(f"   Feature count    : {len(feature_cols)}")

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

scaler         = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled  = scaler.transform(X_test)

model = RandomForestClassifier(
    n_estimators=200,
    max_depth=8,
    min_samples_leaf=5,
    random_state=42,
    class_weight="balanced",
)
model.fit(X_train_scaled, y_train)

y_pred       = model.predict(X_test_scaled)
y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]

print("\n   Model Performance:")
print(classification_report(y_test, y_pred, target_names=["No Injury", "Injury"]))

try:
    auc = roc_auc_score(y_test, y_pred_proba)
    print(f"   AUC-ROC: {auc:.3f}")
except Exception:
    auc = None
    print("   AUC-ROC: Could not calculate (insufficient positive samples in test set)")

importance_df = (
    pd.DataFrame({"feature": feature_cols, "importance": model.feature_importances_})
    .sort_values("importance", ascending=False)
)
print("\n   Top 12 Most Important Features:")
for _, row in importance_df.head(12).iterrows():
    print(f"     {row['feature']:<38} {row['importance']:.4f}")

os.makedirs("models", exist_ok=True)
with open("models/injury_risk_model.pkl", "wb") as f:
    pickle.dump({
        "model":        model,
        "scaler":       scaler,
        "feature_cols": feature_cols,
        "gps_present":  gps_present,
    }, f)
print("\n✓ Model saved: models/injury_risk_model.pkl")

# ==============================================================================
# 5. READINESS SCORER  (z-score aware + GPS modifier)
# ==============================================================================

print("\n4. Creating Readiness Scorer...")


def calculate_readiness_score(row):
    """
    Evidence-based readiness score 0-100.

    Weight allocation based on current research consensus for women's basketball:
      - Subjective wellness (sleep + soreness + mood + stress): 35 pts
        Source: Espasa-Labrador et al. 2023 (women's basketball SR), Saw et al. 2016 (56-study SR)
      - Force plate / neuromuscular (CMJ + RSI): 25 pts
        Source: Labban et al. 2024 (CMJ SR+MA), Bishop et al. 2023 framework
      - GPS / external load z-scores: 20 pts via modifier
        Source: Jaspers et al. 2017 (SR), Petway et al. 2020 (basketball-specific)
      - Schedule context (back-to-back, travel, days rest): 10 pts via modifier
        Source: condensed schedule studies, Morikawa 2022
      - Personal z-score deviation modifier: ±10 pts
        Source: Cormack et al. 2008 (CMJ fatigue monitoring), Foster 1998 (session RPE)

    NOTE: ACWR intentionally excluded as scoring component — used as contextual flag only.
    Evidence: Impellizzeri et al. 2020 (critique), 2025 meta-analysis (22 cohort studies)
    recommends ACWR "with caution as a tool", not as a standalone predictor.
    """
    score = 0

    # ── SUBJECTIVE WELLNESS (35 pts) ──────────────────────────────────────────
    # Sleep 15 pts — strongest individual predictor (Watson et al. 2020/2021, Saw et al. 2016)
    sleep_score = min(15, (row["sleep_hours"] / 8.0) * 10 + (row.get("sleep_quality", 5) / 10) * 5)
    score += sleep_score

    # Soreness 10 pts inverse — Espasa-Labrador 2023: soreness among top daily wellness signals
    score += ((10 - row["soreness"]) / 10) * 10

    # Mood 5 pts + Stress 5 pts — Saw et al. 2016: mood and stress predictive but lower weight than sleep/soreness
    score += (row["mood"]             / 10) * 5
    score += ((10 - row["stress"])    / 10) * 5

    # ── FORCE PLATE / NEUROMUSCULAR (25 pts) ──────────────────────────────────
    # CMJ height 15 pts — Cormack 2008: established fatigue marker; Labban 2024 SR confirms daily sensitivity
    cmj = row.get("cmj_height_cm", np.nan)
    score += min(15, (cmj / 32) * 15) if not pd.isna(cmj) else 10  # 32cm = solid baseline for WNBA

    # RSI-modified 10 pts — Bishop 2023: RSI captures movement strategy (not just height)
    rsi = row.get("rsi_modified", np.nan)
    score += min(10, (rsi / 0.45) * 10) if not pd.isna(rsi) else 7  # 0.45 = good WNBA benchmark

    # ── SCHEDULE CONTEXT baseline (10 pts) ────────────────────────────────────
    # Start full and deduct for schedule stress
    schedule_pts = 10
    if row.get("is_back_to_back", 0):
        schedule_pts -= 4   # Back-to-back: meaningful fatigue risk (condensed schedule literature)
    if row.get("travel_flag", 0):
        tz_diff = abs(row.get("time_zone_diff", 0))
        schedule_pts -= min(3, tz_diff * 1.5)  # Time zone penalty scales with difference
    if row.get("days_rest", 3) <= 1:
        schedule_pts -= 2   # Less than 2 days rest
    if row.get("unrivaled_flag", 0):
        schedule_pts -= 2   # Unrivaled-to-WNBA transition: clinical estimate only
                                    # No published research — 72ft court vs 94ft WNBA, 3v3 vs 5v5
                                    # Flag for prospective validation with actual transition data
    score += max(0, schedule_pts)

    # ── PERSONAL DEVIATION MODIFIER (±10 pts) ─────────────────────────────────
    # How is TODAY vs this player's own baseline? (z-score from expanding window)
    # Cormack 2008, Foster 1998: intra-individual comparison more sensitive than population norms
    modifier = 0
    wellness_z_checks = [
        ("sleep_hours_zscore",    "positive_good", 3),
        ("soreness_zscore",       "negative_good", 3),
        ("stress_zscore",         "negative_good", 2),
        ("mood_zscore",           "positive_good", 2),
        ("cmj_height_cm_zscore",  "positive_good", 3),  # CMJ drop = strong signal
        ("rsi_modified_zscore",   "positive_good", 2),
    ]
    for z_col, direction, max_penalty in wellness_z_checks:
        z = row.get(z_col, 0) or 0
        if direction == "positive_good":
            if z < -2.0:   modifier -= min(max_penalty, max_penalty)
            elif z < -1.5: modifier -= min(max_penalty - 1, max_penalty)
            elif z < -1.0: modifier -= 1
        else:  # negative_good
            if z > 2.0:    modifier -= min(max_penalty, max_penalty)
            elif z > 1.5:  modifier -= min(max_penalty - 1, max_penalty)
            elif z > 1.0:  modifier -= 1

    # GPS z-score modifier (Jaspers 2017, Petway 2020 basketball)
    for z_col in ["player_load_zscore", "accel_count_zscore", "decel_count_zscore"]:
        z = row.get(z_col, 0) or 0
        if z <= -2.0:   modifier -= 2
        elif z <= -1.0: modifier -= 1

    # ACWR contextual flag only — apply small penalty only at extremes
    # NOT scored normally; flagged for display only (Impellizzeri 2020)
    acwr = row.get("acwr", 1.0) or 1.0
    if acwr > 1.8:   modifier -= 3  # Extreme spike only
    elif acwr < 0.6: modifier -= 2  # Extreme underload (detraining signal)

    score = max(0, min(100, score + modifier))
    return round(score, 1)

df["readiness_score"] = df.apply(calculate_readiness_score, axis=1)

print(f"✓ Readiness scores calculated")
print(f"   Mean  : {df['readiness_score'].mean():.1f}")
print(f"   Range : {df['readiness_score'].min():.1f} – {df['readiness_score'].max():.1f}")

with open("models/readiness_scorer.pkl", "wb") as f:
    pickle.dump({"function": calculate_readiness_score}, f)
print("✓ Scorer saved: models/readiness_scorer.pkl")

# ==============================================================================
# 6. SAVE PREDICTIONS
# ==============================================================================

print("\n5. Saving processed dataset...")

X_all_scaled            = scaler.transform(df[feature_cols].fillna(0))
df["injury_risk_score"] = model.predict_proba(X_all_scaled)[:, 1]

df.to_sql("ml_predictions", conn, if_exists="replace", index=False)
print("✓ Predictions saved to database (ml_predictions table)")

os.makedirs("data", exist_ok=True)
df.to_csv("data/processed_data.csv", index=False)
print("✓ Exported: data/processed_data.csv")

# ==============================================================================
# 7. SUMMARY
# ==============================================================================

print("\n" + "=" * 60)
print("MODEL TRAINING COMPLETE")
print("=" * 60)
auc_str = f"{auc:.3f}" if auc is not None else "N/A"
print(f"\n  Injury Risk Predictor  — AUC: {auc_str}  |  Features: {len(feature_cols)}")
print(f"  GPS features included  — {gps_present}")
print(f"  Readiness Scorer       — Range: 0–100 (wellness + force plate + GPS modifier)")
print(f"\n  Saved to:")
print(f"    models/injury_risk_model.pkl")
print(f"    models/readiness_scorer.pkl")
print(f"    data/processed_data.csv")
print(f"\n  Run: streamlit run dashboard.py")

conn.close()
print("\n" + "=" * 60)

# ==============================================================================
# 8. MODEL IMPROVEMENT LOOP — ESPN GAME DATA INTEGRATION
# ==============================================================================
# Runs automatically if espn_data.py has been run and game_results /
# game_box_scores tables exist in the DB. Skips gracefully if not.
#
# THREE IMPROVEMENTS:
#   A. Back-to-back validation — quantify actual performance drop vs assumption
#   B. Pre-injury pattern detection — what did monitoring look like before injury
#   C. Readiness score validation — correlate score with actual game performance
# ==============================================================================

import sqlite3 as _sqlite3
import warnings as _warnings

def _load_table(conn, table):
    try:
        df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
        df["date"] = pd.to_datetime(df.get("date", pd.Series(dtype="datetime64[ns]")))
        return df
    except Exception:
        return pd.DataFrame()

try:
    _conn2 = _sqlite3.connect(DB_PATH)
    _game_results = _load_table(_conn2, "game_results")
    _game_boxes   = _load_table(_conn2, "game_box_scores")
    _schedule_df  = _load_table(_conn2, "schedule")
    _conn2.close()

    # Ensure date columns are datetime throughout Section 8
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for _ddf in [_game_results, _game_boxes, _schedule_df]:
        if not _ddf.empty and "date" in _ddf.columns:
            _ddf["date"] = pd.to_datetime(_ddf["date"], errors="coerce")

    if _game_boxes.empty:
        print("\n[Model Improvement] No game_box_scores table found.")
        print("  Run: python espn_data.py  then  fetch_wings_all_time()")
        print("  Skipping outcome validation — model trained on monitoring data only.")
    else:
        print(f"\n[Model Improvement] Game data found: {len(_game_boxes)} player-game rows")

        # ── A. BACK-TO-BACK VALIDATION ─────────────────────────────────────────
        # Quantifies actual performance drop on back-to-backs vs rest days.
        # Replaces the hardcoded -4pt readiness penalty with data-driven evidence.
        # If no significant drop found, penalty should be reduced.
        print("\n  A. Back-to-Back Performance Validation")

        if not _schedule_df.empty and "is_back_to_back" in _schedule_df.columns:
            _schedule_df["date"] = pd.to_datetime(_schedule_df["date"])
            _b2b = _game_boxes.merge(
                _schedule_df[["date", "is_back_to_back", "days_rest"]],
                on="date", how="left"
            )
            _b2b["rest_cat"] = _b2b["days_rest"].fillna(3).apply(
                lambda x: "back_to_back" if x <= 1 else ("short_rest" if x == 2 else "normal_rest")
            )

            _b2b_summary = (
                _b2b.groupby("rest_cat")[["pts", "reb", "ast", "minutes"]]
                .agg(mean=("pts", "mean"), count=("pts", "count"))
                .round(2)
            )

            # Proper aggregation
            _b2b_agg = _b2b.groupby("rest_cat").agg(
                pts_mean    = ("pts", "mean"),
                pts_std     = ("pts", "std"),
                min_mean    = ("minutes", "mean"),
                games       = ("pts", "count"),
            ).round(2).reset_index()

            print("     Rest Category     | Avg Pts | Avg Min | N Games")
            print("     " + "-" * 50)
            for _, row in _b2b_agg.iterrows():
                print(f"     {row['rest_cat']:<20} | {row['pts_mean']:>7.1f} | "
                      f"{row['min_mean']:>7.1f} | {int(row['games']):>7}")

            # Calculate actual penalty vs assumed
            _normal = _b2b_agg[_b2b_agg["rest_cat"] == "normal_rest"]["pts_mean"].values
            _b2b_v  = _b2b_agg[_b2b_agg["rest_cat"] == "back_to_back"]["pts_mean"].values

            if len(_normal) > 0 and len(_b2b_v) > 0:
                _actual_drop_pct = (_normal[0] - _b2b_v[0]) / _normal[0] * 100
                print(f"\n     Actual back-to-back performance drop: {_actual_drop_pct:.1f}%")
                if abs(_actual_drop_pct) < 5:
                    print("     NOTE: Drop < 5% — consider reducing back-to-back penalty in readiness scorer")
                elif _actual_drop_pct > 15:
                    print("     NOTE: Drop > 15% — current -4pt penalty may be too conservative, consider increase")
                else:
                    print("     NOTE: 5-15% drop — current -4pt penalty appears reasonable")

            _b2b_agg["source"] = "ESPN game data"
            _b2b_agg["fetched_at"] = datetime.now().isoformat()
            try:
                _c = _sqlite3.connect(DB_PATH)
                _b2b_agg.to_sql("back_to_back_analysis", _c, if_exists="replace", index=False)
                _c.close()
                print("     ✓ Saved to back_to_back_analysis table")
            except Exception as _e:
                print(f"     ⚠ Could not save: {_e}")
        else:
            print("     ⚠ Schedule table missing days_rest — run generate_database.py first")

        # ── B. PRE-INJURY PATTERN DETECTION ────────────────────────────────────
        # What did monitoring look like in the 7 days before each injury?
        # This is the most valuable signal for injury prediction model improvement.
        print("\n  B. Pre-Injury Pattern Detection")

        try:
            _inj_conn = _sqlite3.connect(DB_PATH)
            _injuries = pd.read_sql_query("SELECT * FROM injuries", _inj_conn)
            _inj_conn.close()
            _injuries["date"] = pd.to_datetime(_injuries.get("date", _injuries.get("injury_date")))
        except Exception:
            _injuries = pd.DataFrame()

        if _injuries.empty:
            print("     ⚠ No injuries table found — skipping pre-injury analysis")
        elif df.empty:
            print("     ⚠ No monitoring data — skipping pre-injury analysis")
        else:
            _pre_inj_rows = []
            _monitoring_cols = [c for c in ["sleep_hours", "soreness_0_10", "mood_0_10",
                                             "stress_0_10", "cmj_height_cm", "player_load"]
                                if c in df.columns]

            for _, inj in _injuries.iterrows():
                pid      = inj.get("player_id")
                inj_date = inj.get("date")
                if pd.isna(inj_date) or pd.isna(pid):
                    continue

                # Get 7-day window before injury
                window_start = inj_date - pd.Timedelta(days=7)
                pre_inj = df[
                    (df["player_id"] == pid) &
                    (df["date"] >= window_start) &
                    (df["date"] < inj_date)
                ]

                if len(pre_inj) < 3:
                    continue   # Not enough data

                row = {"player_id": pid, "injury_date": inj_date,
                       "injury_type": inj.get("injury_type", "unknown"),
                       "days_of_data": len(pre_inj)}

                for col in _monitoring_cols:
                    row[f"pre_inj_avg_{col}"] = pre_inj[col].mean()
                    row[f"pre_inj_trend_{col}"] = (
                        pre_inj[col].iloc[-1] - pre_inj[col].iloc[0]
                        if len(pre_inj) >= 2 else 0
                    )

                _pre_inj_rows.append(row)

            if _pre_inj_rows:
                _pre_inj_df = pd.DataFrame(_pre_inj_rows)
                print(f"     Found {len(_pre_inj_df)} injuries with 3+ days pre-injury monitoring data")

                # Show key patterns
                for col in ["sleep_hours", "soreness_0_10", "cmj_height_cm"]:
                    avg_col = f"pre_inj_avg_{col}"
                    if avg_col in _pre_inj_df.columns:
                        print(f"     Avg {col} pre-injury: {_pre_inj_df[avg_col].mean():.2f}")

                try:
                    _c = _sqlite3.connect(DB_PATH)
                    _pre_inj_df.to_sql("pre_injury_patterns", _c, if_exists="replace", index=False)
                    _c.close()
                    print("     ✓ Saved to pre_injury_patterns table")
                    print("     NOTE: Use this table to retune model feature weights next season")
                except Exception as _e:
                    print(f"     ⚠ Could not save: {_e}")
            else:
                print("     Not enough pre-injury monitoring windows (need 3+ days before each injury)")
                print("     This improves as real monitoring data accumulates over the season")

        # ── C. READINESS SCORE VALIDATION ──────────────────────────────────────
        # Does our readiness score actually correlate with game performance?
        # A readiness score of 65 should predict worse performance than 85.
        # If correlation is weak, formula weights need retuning.
        print("\n  C. Readiness Score Validation")

        if "readiness_score" not in df.columns:
            print("     ⚠ No readiness_score in monitoring data — skipping")
        elif _game_boxes.empty:
            print("     ⚠ No game data — run espn_data.py first")
        else:
            # Join readiness scores to same-day game performance
            _readiness_on_game_days = df[["player_id", "date", "readiness_score"]].copy()
            _game_perf = _game_boxes[["player_id", "date", "pts", "minutes",
                                       "plus_minus", "reb", "ast"]].copy()
            _game_perf["player_id"] = _game_perf["player_id"].astype(str)
            _readiness_on_game_days["player_id"] = _readiness_on_game_days["player_id"].astype(str)

            _validated = _game_perf.merge(_readiness_on_game_days, on=["player_id", "date"], how="inner")

            if len(_validated) < 10:
                print(f"     Only {len(_validated)} game-day readiness matches found")
                print("     Need more overlapping game + monitoring dates for validation")
                print("     This improves as real 2026 season data accumulates")
            else:
                _corr_pts = _validated["readiness_score"].corr(_validated["pts"])
                _corr_min = _validated["readiness_score"].corr(_validated["minutes"])
                _corr_pm  = _validated["readiness_score"].corr(_validated["plus_minus"])

                print(f"     Readiness score correlations with game performance:")
                print(f"       vs Points:      r = {_corr_pts:.3f}")
                print(f"       vs Minutes:     r = {_corr_min:.3f}")
                print(f"       vs Plus/Minus:  r = {_corr_pm:.3f}")

                if abs(_corr_pts) < 0.15:
                    print("     ⚠ Weak correlation with points — formula may need retuning")
                    print("       Consider: are force plate weights too high vs wellness?")
                elif abs(_corr_pts) >= 0.30:
                    print("     ✓ Meaningful correlation — readiness score has predictive validity")
                else:
                    print("     Moderate correlation — acceptable for this sample size")

                try:
                    _c = _sqlite3.connect(DB_PATH)
                    _validated.to_sql("readiness_validation", _c, if_exists="replace", index=False)
                    _c.close()
                    print("     ✓ Saved to readiness_validation table")
                except Exception as _e:
                    print(f"     ⚠ Could not save: {_e}")

        print("\n[Model Improvement] Complete")
        print("  Tables written: back_to_back_analysis, pre_injury_patterns, readiness_validation")
        print("  Use these to retune model weights after 2026 season data accumulates")

except Exception as _outer_e:
    print(f"\n[Model Improvement] Skipped — {_outer_e}")
    print("  This is non-critical — main model training completed successfully above")
