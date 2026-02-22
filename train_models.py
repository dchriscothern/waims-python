"""
WAIMS Python Demo - ML Model Training
Trains injury risk predictor and readiness scorer

Models:
1. Injury Risk Predictor: XGBoost classifier
2. Readiness Score: Composite algorithm

Output: Trained models saved to models/
"""

import pandas as pd
import numpy as np
import sqlite3
import pickle
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
import warnings
warnings.filterwarnings('ignore')

print("=" * 60)
print("WAIMS - Training ML Models")
print("=" * 60)

# ==============================================================================
# 1. LOAD DATA
# ==============================================================================

print("\n1. Loading data from database...")

conn = sqlite3.connect('waims_demo.db')

# Load data directly with joins
df = pd.read_sql_query('''
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
        f.rsi_modified
    FROM players p
    LEFT JOIN wellness w ON p.player_id = w.player_id
    LEFT JOIN training_load t ON p.player_id = t.player_id AND w.date = t.date
    LEFT JOIN acwr a ON p.player_id = a.player_id AND w.date = a.date
    LEFT JOIN force_plate f ON p.player_id = f.player_id AND w.date = f.date
    WHERE w.date IS NOT NULL
''', conn)

# Add injury labels manually
injuries = pd.read_sql_query('SELECT * FROM injuries', conn)
df['injured_within_7days'] = 0

for _, inj in injuries.iterrows():
    inj_date = pd.to_datetime(inj['injury_date'])
    warning_start = inj_date - pd.Timedelta(days=7)
    
    mask = (
        (df['player_id'] == inj['player_id']) &
        (pd.to_datetime(df['date']) >= warning_start) &
        (pd.to_datetime(df['date']) <= inj_date)
    )
    df.loc[mask, 'injured_within_7days'] = 1

print(f"✓ Loaded {len(df)} records")
print(f"  Players: {df['player_id'].nunique()}")
print(f"  Date range: {df['date'].min()} to {df['date'].max()}")

# ==============================================================================
# 2. FEATURE ENGINEERING
# ==============================================================================

print("\n2. Engineering features...")

# Fill missing values
df['acwr'] = df['acwr'].fillna(1.0)
df['cmj_height_cm'] = df.groupby('player_id')['cmj_height_cm'].ffill()
df['rsi_modified'] = df['rsi_modified'].fillna(0.35)

# Create rolling features
df = df.sort_values(['player_id', 'date'])

for col in ['sleep_hours', 'soreness', 'practice_minutes']:
    df[f'{col}_7day_avg'] = df.groupby('player_id')[col].transform(
        lambda x: x.rolling(7, min_periods=1).mean()
    )
    df[f'{col}_7day_std'] = df.groupby('player_id')[col].transform(
        lambda x: x.rolling(7, min_periods=1).std()
    )

# Wellness composite
df['wellness_score'] = (
    df['sleep_hours'] * 1.5 +
    (10 - df['soreness']) +
    (10 - df['stress']) +
    df['mood']
)

print(f"✓ Created {len(df.columns)} features")

# ==============================================================================
# 3. TRAIN INJURY RISK MODEL
# ==============================================================================

print("\n3. Training Injury Risk Predictor...")

# Select features for model
feature_cols = [
    'age', 'injury_history_count',
    'sleep_hours', 'soreness', 'stress',
    'practice_minutes', 'practice_rpe', 'game_minutes',
    'acwr', 'cmj_height_cm', 'asymmetry_percent',
    'sleep_hours_7day_avg', 'soreness_7day_avg', 'practice_minutes_7day_avg',
    'wellness_score'
]

# Prepare data
df_model = df[feature_cols + ['injured_within_7days']].dropna()

X = df_model[feature_cols]
y = df_model['injured_within_7days']

print(f"   Training samples: {len(X)}")
print(f"   Injury cases: {y.sum()}")
print(f"   Non-injury cases: {(y == 0).sum()}")

# Split data
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# Scale features
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# Train RandomForest model
model = RandomForestClassifier(
    n_estimators=100,
    max_depth=8,
    random_state=42,
    class_weight='balanced'  # Handle imbalance
)

model.fit(X_train_scaled, y_train)

# Evaluate
y_pred = model.predict(X_test_scaled)
y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]

print("\n   Model Performance:")
print(classification_report(y_test, y_pred, target_names=['No Injury', 'Injury']))

try:
    auc = roc_auc_score(y_test, y_pred_proba)
    print(f"   AUC-ROC: {auc:.3f}")
except:
    print("   AUC-ROC: Could not calculate (insufficient positive samples)")

# Feature importance
feature_importance = pd.DataFrame({
    'feature': feature_cols,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)

print("\n   Top 5 Most Important Features:")
for idx, row in feature_importance.head(5).iterrows():
    print(f"     {row['feature']}: {row['importance']:.3f}")

# Save model
import os
os.makedirs('models', exist_ok=True)

with open('models/injury_risk_model.pkl', 'wb') as f:
    pickle.dump({
        'model': model,
        'scaler': scaler,
        'feature_cols': feature_cols
    }, f)

print("\n✓ Model saved: models/injury_risk_model.pkl")

# ==============================================================================
# 4. CREATE READINESS SCORER
# ==============================================================================

print("\n4. Creating Readiness Scorer...")

def calculate_readiness_score(row):
    """
    Calculate readiness score (0-100) based on multiple factors
    
    Components:
    - Sleep (30%): Hours and quality
    - Soreness (25%): Inverse of soreness level
    - Wellness (20%): Mood and stress
    - Load (15%): ACWR status
    - Neuromuscular (10%): CMJ performance
    """
    
    score = 0
    
    # Sleep component (30 points)
    sleep_score = min(30, (row['sleep_hours'] / 8.0) * 15 + (row['sleep_quality'] / 10) * 15)
    score += sleep_score
    
    # Soreness component (25 points) - inverse
    soreness_score = ((10 - row['soreness']) / 10) * 25
    score += soreness_score
    
    # Wellness component (20 points)
    mood_score = (row['mood'] / 10) * 10
    stress_score = ((10 - row['stress']) / 10) * 10
    score += mood_score + stress_score
    
    # Load component (15 points) - optimal ACWR
    if pd.isna(row['acwr']):
        acwr_score = 10
    elif 0.8 <= row['acwr'] <= 1.3:
        acwr_score = 15  # Optimal range
    elif row['acwr'] < 0.8:
        acwr_score = 10  # Detraining
    elif row['acwr'] > 1.5:
        acwr_score = 5   # High risk
    else:
        acwr_score = 12  # Moderate
    score += acwr_score
    
    # Neuromuscular component (10 points)
    if not pd.isna(row['cmj_height_cm']):
        # Assume baseline ~30cm, normalized
        cmj_score = min(10, (row['cmj_height_cm'] / 30) * 10)
    else:
        cmj_score = 7  # Neutral if missing
    score += cmj_score
    
    return round(score, 1)

# Apply to all data
df['readiness_score'] = df.apply(calculate_readiness_score, axis=1)

print(f"✓ Calculated readiness scores")
print(f"   Mean score: {df['readiness_score'].mean():.1f}")
print(f"   Range: {df['readiness_score'].min():.1f} - {df['readiness_score'].max():.1f}")

# Save readiness function
with open('models/readiness_scorer.pkl', 'wb') as f:
    pickle.dump({
        'function': calculate_readiness_score
    }, f)

print("✓ Scorer saved: models/readiness_scorer.pkl")

# ==============================================================================
# 5. SAVE PROCESSED DATASET
# ==============================================================================

print("\n5. Saving processed dataset...")

# Add predictions to dataset
X_all_scaled = scaler.transform(df[feature_cols].fillna(0))
df['injury_risk_score'] = model.predict_proba(X_all_scaled)[:, 1]

# Save to database
df.to_sql('ml_predictions', conn, if_exists='replace', index=False)
print("✓ Predictions saved to database")

# Export to CSV for dashboard
df.to_csv('data/processed_data.csv', index=False)
print("✓ Exported to: data/processed_data.csv")

# ==============================================================================
# 6. SUMMARY
# ==============================================================================

print("\n" + "=" * 60)
print("MODEL TRAINING COMPLETE")
print("=" * 60)

print("\n📊 Models Created:")
print("   1. Injury Risk Predictor (RandomForest)")
print("      - AUC: ", end="")
try:
    print(f"{auc:.3f}")
except:
    print("N/A")
print(f"      - Features: {len(feature_cols)}")
print("   2. Readiness Scorer (Algorithm)")
print(f"      - Score range: 0-100")

print("\n💾 Saved Files:")
print("   models/injury_risk_model.pkl")
print("   models/readiness_scorer.pkl")
print("   data/processed_data.csv")

print("\n🎯 Next Step:")
print("   Run dashboard: streamlit run dashboard.py")

conn.close()

print("\n" + "=" * 60)
