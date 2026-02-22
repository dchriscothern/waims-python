"""
Example: Adding Back-to-Back Games Feature to ML Model
Shows how to extend the model with schedule factors
"""

import pandas as pd
import numpy as np
import sqlite3
from sklearn.ensemble import RandomForestClassifier

# ==============================================================================
# LOAD DATA
# ==============================================================================

conn = sqlite3.connect('waims_demo.db')

# Get training load data
training = pd.read_sql_query("""
    SELECT player_id, date, game_minutes, practice_minutes
    FROM training_load
    ORDER BY player_id, date
""", conn)

# ==============================================================================
# ENGINEER SCHEDULE FEATURES
# ==============================================================================

print("Creating schedule features...")

# Feature 1: Back-to-back games
training['is_game'] = training['game_minutes'] > 0
training['back_to_back'] = training.groupby('player_id')['is_game'].shift(1).fillna(0)

# Feature 2: Games in last 7 days
training['games_last_7d'] = training.groupby('player_id')['is_game'].rolling(7).sum().reset_index(0, drop=True)

# Feature 3: Days since last game
def days_since_last_game(group):
    game_dates = group[group['is_game']]['date']
    days_since = []
    for date in group['date']:
        prior_games = game_dates[game_dates < date]
        if len(prior_games) > 0:
            days = (pd.to_datetime(date) - pd.to_datetime(prior_games.iloc[-1])).days
        else:
            days = 999  # No prior games
        days_since.append(days)
    return days_since

training['days_since_last_game'] = training.groupby('player_id').apply(
    days_since_last_game
).explode().values

# Feature 4: Travel (would need game schedule data)
# For demo, simulate based on game frequency
training['travel_proxy'] = (training['games_last_7d'] * np.random.uniform(0.8, 1.2, len(training))).round(1)

print("✓ Schedule features created")

# ==============================================================================
# COMBINE WITH OTHER FEATURES
# ==============================================================================

# Load wellness and other data
wellness = pd.read_sql_query("SELECT * FROM wellness", conn)
acwr = pd.read_sql_query("SELECT * FROM acwr", conn)

# Merge everything
df = training.merge(wellness, on=['player_id', 'date'], how='left')
df = df.merge(acwr, on=['player_id', 'date'], how='left')

# ==============================================================================
# DEFINE FEATURE SET
# ==============================================================================

features = [
    # Original features
    'sleep_hours',
    'soreness',
    'stress',
    'acwr',
    
    # NEW: Schedule factors
    'back_to_back',          # ← Boolean: played yesterday?
    'games_last_7d',         # ← Game density
    'days_since_last_game',  # ← Rest days
    'travel_proxy'           # ← Travel fatigue
]

print(f"\nFeature set: {len(features)} features")
print("Original: 4")
print("Added: 4 schedule factors")

# ==============================================================================
# TRAIN MODEL
# ==============================================================================

# Create target (simulated for demo)
df['injury_next_7d'] = 0  # Would come from actual injury table

# Drop NaN
df_clean = df[features + ['injury_next_7d']].dropna()

X = df_clean[features]
y = df_clean['injury_next_7d']

# Train
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X, y)

# ==============================================================================
# FEATURE IMPORTANCE
# ==============================================================================

importance = pd.DataFrame({
    'feature': features,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)

print("\n📊 Feature Importance (after adding schedule factors):")
print(importance.to_string(index=False))

# ==============================================================================
# EXAMPLE PREDICTION
# ==============================================================================

print("\n🎯 Example Prediction:")

# Player with high risk due to schedule
example = pd.DataFrame({
    'sleep_hours': [6.2],
    'soreness': [7],
    'stress': [6],
    'acwr': [1.6],
    'back_to_back': [1],        # ← Played yesterday!
    'games_last_7d': [4],        # ← Heavy schedule
    'days_since_last_game': [1], # ← No rest
    'travel_proxy': [3.5]        # ← Travel fatigue
})

risk = model.predict_proba(example)[0][1] * 100

print(f"Player status:")
print(f"  - Back-to-back game: YES")
print(f"  - Games in 7 days: 4")
print(f"  - Sleep: 6.2 hrs")
print(f"  - ACWR: 1.6")
print(f"  → Injury risk: {risk:.0f}%")

print("\n✅ Model now considers schedule factors!")

conn.close()
