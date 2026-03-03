"""
WAIMS Python Demo - ML Model Training
Trains injury risk predictor and readiness scorer
Now includes per-player z-score deviation features as primary signal.
"""

import os
import pickle
import warnings

import numpy as np
import pandas as pd
import sqlite3
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

conn = sqlite3.connect("waims_demo.db")

df = pd.read_sql_query(
    """
    SELECT
        p.player_id, p.name, p.position, p.age, p.injury_history_count,
        w.date,
        w.sleep_hours, w.sleep_quality, w.soreness, w.stress, w.mood,
        t.practice_minutes, t.practice_rpe, t.total_daily_load, t.game_minutes,
        a.acwr,
        f.cmj_height_cm, f.rsi_modified
    FROM players p
    LEFT JOIN wellness w       ON p.player_id = w.player_id
    LEFT JOIN training_load t  ON p.player_id = t.player_id AND w.date = t.date
    LEFT JOIN acwr a           ON p.player_id = a.player_id AND w.date = a.date
    LEFT JOIN force_plate f    ON p.player_id = f.player_id AND w.date = f.date
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
print(f"  Players: {df['player_id'].nunique()}")
print(f"  Date range: {df['date'].min()} to {df['date'].max()}")

# ==============================================================================
# 2. FEATURE ENGINEERING
# ==============================================================================

print("\n2. Engineering features...")

df["acwr"]          = df["acwr"].fillna(1.0)
df["cmj_height_cm"] = df.groupby("player_id")["cmj_height_cm"].ffill()
df["rsi_modified"]  = df["rsi_modified"].fillna(0.35)

df = df.sort_values(["player_id", "date"])

# Rolling averages and std (absolute, 7-day)
for col in ["sleep_hours", "soreness", "practice_minutes", "cmj_height_cm", "rsi_modified"]:
    df[f"{col}_7day_avg"] = df.groupby("player_id")[col].transform(
        lambda x: x.rolling(7, min_periods=1).mean()
    )
    df[f"{col}_7day_std"] = df.groupby("player_id")[col].transform(
        lambda x: x.rolling(7, min_periods=1).std().fillna(0)
    )

# ── Per-player z-score deviations (30-day expanding baseline) ─────────────────
# For each row, z = (today - player_mean_up_to_yesterday) / player_std_up_to_yesterday
# Using expanding window shifted by 1 so there's no data leakage

Z_COLS = {
    "sleep_hours": 0.3,   # min std floors
    "soreness":    0.5,
    "stress":      0.5,
    "mood":        0.5,
    "cmj_height_cm": 0.5,
    "rsi_modified":  0.01,
}

for col, min_std in Z_COLS.items():
    roll_mean = df.groupby("player_id")[col].transform(
        lambda x: x.shift(1).expanding(min_periods=5).mean()
    )
    roll_std = df.groupby("player_id")[col].transform(
        lambda x: x.shift(1).expanding(min_periods=5).std().clip(lower=min_std)
    )
    df[f"{col}_zscore"] = ((df[col] - roll_mean) / roll_std).fillna(0)

# Hard-floor binary flags (safety thresholds — always relevant regardless of baseline)
df["flag_sleep_floor"]    = (df["sleep_hours"] < 6.5).astype(int)
df["flag_soreness_ceil"]  = (df["soreness"] > 7).astype(int)
df["flag_stress_ceil"]    = (df["stress"] > 7).astype(int)
df["flag_acwr_spike"]     = (df["acwr"] > 1.5).astype(int)

# Composite wellness score (kept for readiness scorer)
df["wellness_score"] = (
    df["sleep_hours"] * 1.5
    + (10 - df["soreness"])
    + (10 - df["stress"])
    + df["mood"]
)

print(f"✓ Created {len(df.columns)} features (including z-score deviations)")

# ==============================================================================
# 3. TRAIN INJURY RISK MODEL
# ==============================================================================

print("\n3. Training Injury Risk Predictor...")

feature_cols = [
    # Demographics / history
    "age", "injury_history_count",
    # Raw values (still informative for hard floors)
    "sleep_hours", "soreness", "stress", "mood",
    "practice_minutes", "practice_rpe", "game_minutes",
    "acwr", "cmj_height_cm", "rsi_modified",
    # 7-day rolling averages
    "sleep_hours_7day_avg", "soreness_7day_avg",
    "practice_minutes_7day_avg", "cmj_height_cm_7day_avg",
    # Z-score deviations from personal baseline  ← new primary signal
    "sleep_hours_zscore", "soreness_zscore", "stress_zscore",
    "mood_zscore", "cmj_height_cm_zscore", "rsi_modified_zscore",
    # Hard-floor binary flags
    "flag_sleep_floor", "flag_soreness_ceil",
    "flag_stress_ceil", "flag_acwr_spike",
    # Composite
    "wellness_score",
]

df_model = df[feature_cols + ["injured_within_7days"]].dropna()
X = df_model[feature_cols]
y = df_model["injured_within_7days"]

print(f"   Training samples : {len(X)}")
print(f"   Injury cases     : {y.sum()}")
print(f"   Non-injury cases : {(y == 0).sum()}")

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

scaler          = StandardScaler()
X_train_scaled  = scaler.fit_transform(X_train)
X_test_scaled   = scaler.transform(X_test)

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
    print("   AUC-ROC: Could not calculate (insufficient positive samples)")

importance_df = (
    pd.DataFrame({"feature": feature_cols, "importance": model.feature_importances_})
    .sort_values("importance", ascending=False)
)
print("\n   Top 10 Most Important Features:")
for _, row in importance_df.head(10).iterrows():
    print(f"     {row['feature']:<35} {row['importance']:.4f}")

os.makedirs("models", exist_ok=True)

with open("models/injury_risk_model.pkl", "wb") as f:
    pickle.dump({"model": model, "scaler": scaler, "feature_cols": feature_cols}, f)

print("\n✓ Model saved: models/injury_risk_model.pkl")

# ==============================================================================
# 4. READINESS SCORER — z-score aware
# ==============================================================================

print("\n4. Creating Readiness Scorer...")


def calculate_readiness_score(row):
    """
    Readiness score 0–100.
    Absolute components set the baseline; z-score deviations apply a personal modifier.
    """
    score = 0

    # Sleep (30 pts absolute)
    sleep_score = min(30, (row["sleep_hours"] / 8.0) * 15 + (row.get("sleep_quality", 5) / 10) * 15)
    score += sleep_score

    # Soreness (25 pts inverse)
    score += ((10 - row["soreness"]) / 10) * 25

    # Mood + Stress (20 pts)
    score += (row["mood"] / 10) * 10
    score += ((10 - row["stress"]) / 10) * 10

    # ACWR (15 pts)
    acwr = row.get("acwr", 1.0) or 1.0
    if 0.8 <= acwr <= 1.3:
        score += 15
    elif acwr < 0.8:
        score += 10
    elif acwr > 1.5:
        score += 5
    else:
        score += 12

    # CMJ neuromuscular (10 pts)
    cmj = row.get("cmj_height_cm", np.nan)
    score += min(10, (cmj / 30) * 10) if not pd.isna(cmj) else 7

    # Personal deviation modifier (±10 pts)
    # Each metric >1.5σ below/above norm nudges score down
    modifier = 0
    for z_col, direction in [
        ("sleep_hours_zscore",    "positive_good"),
        ("soreness_zscore",       "negative_good"),
        ("stress_zscore",         "negative_good"),
        ("mood_zscore",           "positive_good"),
        ("cmj_height_cm_zscore",  "positive_good"),
    ]:
        z = row.get(z_col, 0) or 0
        if direction == "positive_good" and z < -1.5:
            modifier -= 2
        elif direction == "negative_good" and z > 1.5:
            modifier -= 2

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
# 5. SAVE PREDICTIONS
# ==============================================================================

print("\n5. Saving processed dataset...")

X_all_scaled           = scaler.transform(df[feature_cols].fillna(0))
df["injury_risk_score"] = model.predict_proba(X_all_scaled)[:, 1]

df.to_sql("ml_predictions", conn, if_exists="replace", index=False)
print("✓ Predictions saved to database")

os.makedirs("data", exist_ok=True)
df.to_csv("data/processed_data.csv", index=False)
print("✓ Exported to: data/processed_data.csv")

# ==============================================================================
# 6. SUMMARY
# ==============================================================================

print("\n" + "=" * 60)
print("MODEL TRAINING COMPLETE")
print("=" * 60)
print(f"\n  Injury Risk Predictor  — AUC: {auc:.3f if auc else 'N/A'}  |  Features: {len(feature_cols)}")
print(f"  Readiness Scorer       — Range: 0–100 (with personal deviation modifier)")
print(f"\n  Saved:")
print(f"    models/injury_risk_model.pkl")
print(f"    models/readiness_scorer.pkl")
print(f"    data/processed_data.csv")
print(f"\n  Run: streamlit run dashboard.py")

conn.close()
print("\n" + "=" * 60)
