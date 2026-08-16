"""
Arkansas Razorbacks WAIMS - ML Model Training
==============================================
Trains injury risk predictor and readiness scorer using college basketball data.
Uses GPS/Kinexon metrics and men-specific population characteristics.
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

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.sport_config_extended import get_team_config

warnings.filterwarnings("ignore")

print("=" * 60)
print("Arkansas Razorbacks WAIMS - Training ML Models")
print("=" * 60)

# ==============================================================================
# 1. LOAD DATA
# ==============================================================================

print("\n1. Loading data from database...")

db_path = os.path.join(os.path.dirname(__file__), "data", "waims_arkansas.db")

if not os.path.exists(db_path):
    print(f"[ERROR] Database not found: {db_path}")
    print("Run: python generate_database_arkansas.py")
    exit(1)

conn = sqlite3.connect(db_path)

# Check for schedule table (college-specific, optional)
_tables = [r[0] for r in conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table'"
).fetchall()]
_has_schedule = "schedule" in _tables

if _has_schedule:
    print("  Schedule table found — including B2B, travel, rest features")
    _schedule_join = "LEFT JOIN schedule s ON w.date = s.date"
    _schedule_cols = """
        COALESCE(s.is_back_to_back, 0)                        AS is_back_to_back,
        COALESCE(s.days_rest, 3)                              AS days_rest,
        COALESCE(s.travel_flag, 0)                            AS travel_flag,
        COALESCE(s.time_zone_diff, 0)                         AS time_zone_diff,
        0                                                      AS unrivaled_flag"""
else:
    print("  No schedule table — defaulting schedule context to zero")
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
    inj_date = pd.to_datetime(inj["injury_date"])
    warning_start = inj_date - pd.Timedelta(days=7)
    mask = (
        (df["player_id"] == inj["player_id"])
        & (pd.to_datetime(df["date"]) >= warning_start)
        & (pd.to_datetime(df["date"]) <= inj_date)
    )
    df.loc[mask, "injured_within_7days"] = 1

print(f"[OK] Loaded {len(df)} records")
print(f"  Players: {df['player_id'].nunique()}")
print(f"  Injuries (within 7-day windows): {int(df['injured_within_7days'].sum())}")

# ==============================================================================
# 2. FEATURE ENGINEERING
# ==============================================================================

print("\n2. Engineering features...")

# Convert date columns
df["date"] = pd.to_datetime(df["date"])

# Fill missing values appropriately
df["cmj_height_cm"] = df.groupby("player_id")["cmj_height_cm"].transform(
    lambda x: x.fillna(x.mean())
)
df["rsi_modified"] = df.groupby("player_id")["rsi_modified"].transform(
    lambda x: x.fillna(x.mean())
)
df["acwr"] = df["acwr"].fillna(1.0)

# Initialize baseline and z-score columns
df["cmj_30d_baseline"] = 0.0
df["rsi_30d_baseline"] = 0.0
df["cmj_zscore"] = 0.0
df["rsi_zscore"] = 0.0

# Rolling z-score baselines (per player)
df = df.sort_values(["player_id", "date"]).reset_index(drop=True)
for player_id in df["player_id"].unique():
    player_mask = df["player_id"] == player_id
    player_indices = df[player_mask].index
    
    cmj_values = df.loc[player_indices, "cmj_height_cm"].values
    rsi_values = df.loc[player_indices, "rsi_modified"].values
    
    # Calculate rolling mean
    cmj_rolling_mean = pd.Series(cmj_values).rolling(30, min_periods=1).mean().values
    rsi_rolling_mean = pd.Series(rsi_values).rolling(30, min_periods=1).mean().values
    
    # Calculate rolling std
    cmj_rolling_std = pd.Series(cmj_values).rolling(30, min_periods=1).std().values + 0.1
    rsi_rolling_std = pd.Series(rsi_values).rolling(30, min_periods=1).std().values + 0.1
    
    # Set baselines
    df.loc[player_indices, "cmj_30d_baseline"] = cmj_rolling_mean
    df.loc[player_indices, "rsi_30d_baseline"] = rsi_rolling_mean
    
    # Calculate z-scores
    df.loc[player_indices, "cmj_zscore"] = (cmj_values - cmj_rolling_mean) / cmj_rolling_std
    df.loc[player_indices, "rsi_zscore"] = (rsi_values - rsi_rolling_mean) / rsi_rolling_std

# Fill NaN z-scores with 0
df[["cmj_zscore", "rsi_zscore"]] = df[["cmj_zscore", "rsi_zscore"]].fillna(0)

# Add position mapping
position_map = {
    "PG": 1, "SG": 2, "SF": 3, "PF": 4, "C": 5,
    "G": 1.5, "F": 3.5, "B": 4.5
}
df["position_code"] = df["position"].map(position_map).fillna(3)

# Target variable (injury flag)
df["injury_risk"] = df["injured_within_7days"].astype(int)

print(f"[OK] Features engineered")
print(f"  Injury cases (positive): {df['injury_risk'].sum()}")
print(f"  Healthy cases (negative): {(1 - df['injury_risk']).sum()}")

# ==============================================================================
# 3. PREPARE TRAINING DATA
# ==============================================================================

print("\n3. Preparing training data...")

feature_cols = [
    "age", "injury_history_count", "position_code",
    "sleep_hours", "sleep_quality", "soreness", "stress", "mood",
    "practice_minutes", "practice_rpe", "total_daily_load", "game_minutes",
    "player_load", "accel_count", "decel_count",
    "total_distance_km", "hsr_distance_m", "sprint_distance_m",
    "acwr",
    "cmj_height_cm", "cmj_zscore", "rsi_modified", "rsi_zscore",
    "is_back_to_back", "days_rest", "travel_flag", "time_zone_diff", "unrivaled_flag",
]

# Ensure all features exist
missing_cols = [col for col in feature_cols if col not in df.columns]
if missing_cols:
    for col in missing_cols:
        df[col] = 0

X = df[feature_cols].fillna(0)
y = df["injury_risk"]

# Remove rows with insufficient data
valid_idx = (X.notna().sum(axis=1) >= len(feature_cols) - 5)
X = X[valid_idx]
y = y[valid_idx]

print(f"[OK] Training data: {len(X)} samples, {len(feature_cols)} features")

# ==============================================================================
# 4. TRAIN/TEST SPLIT (by player, no data leakage)
# ==============================================================================

print("\n4. Train/test split (by player)...")

players_list = df[valid_idx]["player_id"].unique()
train_size = int(len(players_list) * 0.7)
train_players = players_list[:train_size]

train_mask = df[valid_idx]["player_id"].isin(train_players).values
X_train = X[train_mask]
X_test = X[~train_mask]
y_train = y[train_mask]
y_test = y[~train_mask]

print(f"  Train: {len(X_train)} samples ({len(np.unique(df[valid_idx][train_mask]['player_id']))} players)")
print(f"  Test:  {len(X_test)} samples ({len(np.unique(df[valid_idx][~train_mask]['player_id']))} players)")

# ==============================================================================
# 5. SCALE FEATURES
# ==============================================================================

print("\n5. Scaling features...")

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

print("[OK] StandardScaler fitted")

# ==============================================================================
# 6. TRAIN RANDOM FOREST
# ==============================================================================

print("\n6. Training Random Forest classifier...")

rf_model = RandomForestClassifier(
    n_estimators=100,
    max_depth=12,
    min_samples_split=10,
    min_samples_leaf=5,
    max_features="sqrt",
    class_weight="balanced",
    random_state=42,
    n_jobs=-1,
)

rf_model.fit(X_train_scaled, y_train)

print("[OK] Model trained")

# ==============================================================================
# 7. EVALUATE
# ==============================================================================

print("\n7. Model evaluation...")

y_train_pred = rf_model.predict(X_train_scaled)
y_test_pred = rf_model.predict(X_test_scaled)
y_test_proba = rf_model.predict_proba(X_test_scaled)[:, 1]

train_auc = roc_auc_score(y_train, rf_model.predict_proba(X_train_scaled)[:, 1])
test_auc = roc_auc_score(y_test, y_test_proba)

print(f"\n  Train AUC: {train_auc:.3f}")
print(f"  Test AUC:  {test_auc:.3f}")

print(f"\n  Test set classification report:")
print(classification_report(y_test, y_test_pred, digits=3))

# ==============================================================================
# 8. FEATURE IMPORTANCE
# ==============================================================================

print("\n8. Feature importance (top 10)...")

importances = pd.DataFrame({
    "feature": feature_cols,
    "importance": rf_model.feature_importances_,
}).sort_values("importance", ascending=False)

for idx, row in importances.head(10).iterrows():
    print(f"   {row['feature']:25s} {row['importance']:.4f}")

# ==============================================================================
# 9. SAVE MODEL & SCALER
# ==============================================================================

print("\n9. Saving models...")

models_dir = os.path.join(os.path.dirname(__file__), "models")
os.makedirs(models_dir, exist_ok=True)

model_path = os.path.join(models_dir, "injury_risk_model.pkl")
scaler_path = os.path.join(models_dir, "feature_scaler.pkl")

with open(model_path, "wb") as f:
    pickle.dump(rf_model, f)

with open(scaler_path, "wb") as f:
    pickle.dump(scaler, f)

print(f"[OK] Model saved: {model_path}")
print(f"[OK] Scaler saved: {scaler_path}")

# ==============================================================================
# SUMMARY
# ==============================================================================

print("\n" + "=" * 60)
print("ARKANSAS RAZORBACKS WAIMS - MODEL TRAINING COMPLETE")
print("=" * 60)

print(f"\n[PERFORMANCE]")
print(f"   Train AUC: {train_auc:.3f}")
print(f"   Test AUC:  {test_auc:.3f}")

print(f"\n[FILES]")
print(f"   Model:  {model_path}")
print(f"   Scaler: {scaler_path}")

print(f"\n[OK] Ready for dashboard deployment")
print("=" * 60)

conn.close()
