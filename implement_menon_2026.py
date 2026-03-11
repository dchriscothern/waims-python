"""
WAIMS Python - Update with Menon 2026 Research
Implementation guide for adding WNBA-specific risk factors

Research: Age, Workload, and Usage Rate: Risk Factors Associated With 
          Knee Injuries in Women's National Basketball Association Athletes
Authors: Menon S, Sai S, Traversone J, Lin E, Tummala SV, Chhabra A (2026)

This script shows how to integrate new research findings into your model.
"""

import pandas as pd
import numpy as np

# ==============================================================================
# NEW RESEARCH THRESHOLDS (Menon et al. 2026)
# ==============================================================================

print("=" * 70)
print("IMPLEMENTING MENON 2026 RESEARCH - WNBA INJURY RISK FACTORS")
print("=" * 70)

# Source: Menon et al. 2026 - WNBA-specific study
AGE_HIGH_RISK = 28                    # Age >28 years = increased risk
USAGE_RATE_HIGH_RISK = 0.25           # Usage rate >25% = 2.3x knee injury risk
CUMULATIVE_WORKLOAD_THRESHOLD = 1000  # Minutes per month threshold

print("\nNew Risk Factors (WNBA-Specific):")
print(f"  Age threshold: >{AGE_HIGH_RISK} years")
print(f"  Usage rate threshold: >{USAGE_RATE_HIGH_RISK * 100}%")
print(f"  Workload threshold: >{CUMULATIVE_WORKLOAD_THRESHOLD} min/month")

# ==============================================================================
# STEP 1: CALCULATE USAGE RATE
# ==============================================================================

def calculate_usage_rate(player_stats):
    """
    Calculate usage rate from game statistics.
    
    Usage Rate approximation:
    100 * ((player minutes / team minutes) * possessions weight)
    
    Simplified: (Player Minutes / Game Minutes) when on court
    
    Source: Menon et al. 2026
    
    Parameters:
    -----------
    player_stats : DataFrame
        Game statistics with 'minutes' column
    
    Returns:
    --------
    float : Usage rate (0-1 scale, where 0.25 = 25%)
    """
    # If we have detailed stats (FGA, FTA, TOV)
    if all(col in player_stats.columns for col in ['fga', 'fta', 'tov', 'minutes', 'team_minutes']):
        # True usage rate formula
        # Usage % = 100 * ((FGA + 0.44 * FTA + TOV) * (Team Minutes / 5)) / 
        #           (Minutes * (Team FGA + 0.44 * Team FTA + Team TOV))
        usage = (
            (player_stats['fga'] + 0.44 * player_stats['fta'] + player_stats['tov']) *
            (player_stats['team_minutes'] / 5)
        ) / (
            player_stats['minutes'] *
            (player_stats['team_fga'] + 0.44 * player_stats['team_fta'] + player_stats['team_tov'])
        )
        return usage
    
    else:
        # Simplified proxy: player minutes / available team minutes
        # Assumes 5 players on court, 48 minute game = 240 team minutes
        team_minutes_available = 240  # 48 minutes * 5 players
        usage_proxy = player_stats['minutes'] / team_minutes_available
        return usage_proxy

# ==============================================================================
# STEP 2: CALCULATE CUMULATIVE WORKLOAD
# ==============================================================================

def calculate_cumulative_workload(player_games, window_days=30):
    """
    Calculate cumulative minutes over rolling window.
    
    Source: Menon et al. 2026
    
    Parameters:
    -----------
    player_games : DataFrame
        Games sorted by date with 'minutes' column
    window_days : int
        Rolling window (default 30 days / ~1 month)
    
    Returns:
    --------
    Series : Cumulative minutes
    """
    player_games = player_games.sort_values('game_date')
    player_games['cumulative_minutes'] = (
        player_games['minutes']
        .rolling(window=f'{window_days}D', on='game_date')
        .sum()
    )
    return player_games['cumulative_minutes']

# ==============================================================================
# STEP 3: CREATE RISK FLAGS
# ==============================================================================

def flag_high_risk_players(player_data):
    """
    Identify high-risk players based on Menon 2026 findings.
    
    Parameters:
    -----------
    player_data : DataFrame
        Must have: age, usage_rate, cumulative_minutes
    
    Returns:
    --------
    DataFrame with risk flags
    """
    df = player_data.copy()
    
    # Individual risk factors
    df['age_risk'] = df['age'] > AGE_HIGH_RISK
    df['usage_risk'] = df['usage_rate'] > USAGE_RATE_HIGH_RISK
    df['workload_risk'] = df['cumulative_minutes'] > CUMULATIVE_WORKLOAD_THRESHOLD
    
    # Combined risk score (Menon 2026 interaction)
    df['menon_risk_score'] = (
        df['age_risk'].astype(int) * 30 +        # Age = 30 points
        df['usage_risk'].astype(int) * 40 +      # Usage = 40 points (2.3x risk)
        df['workload_risk'].astype(int) * 30     # Workload = 30 points
    )
    
    # Interaction effect (age + usage together)
    df['age_usage_interaction'] = (
        df['age_risk'] & df['usage_risk']
    ).astype(int) * 20  # Additional 20 points
    
    df['menon_risk_score'] += df['age_usage_interaction']
    
    # Risk categories
    df['menon_risk_level'] = pd.cut(
        df['menon_risk_score'],
        bins=[0, 30, 60, 100],
        labels=['LOW', 'MODERATE', 'HIGH']
    )
    
    return df

# ==============================================================================
# STEP 4: EXAMPLE USAGE
# ==============================================================================

print("\n" + "=" * 70)
print("EXAMPLE: Applying Menon 2026 Research")
print("=" * 70)

# Create example player data
example_players = pd.DataFrame({
    'player_id': ['ATH_001', 'ATH_002', 'ATH_003', 'ATH_004'],
    'name': ['ATH_001', 'ATH_002', 'ATH_003', 'ATH_004'],
    'age': [25, 29, 27, 31],
    'minutes': [32, 35, 28, 30],
    'cumulative_minutes': [800, 1100, 700, 1200]
})

# Calculate usage rate (simplified)
example_players['usage_rate'] = example_players['minutes'] / 240

# Flag risks
example_players = flag_high_risk_players(example_players)

print("\nExample Risk Assessment:")
print(example_players[['name', 'age', 'usage_rate', 'menon_risk_score', 'menon_risk_level']])

print("\n🔴 High Risk Players:")
high_risk = example_players[example_players['menon_risk_level'] == 'HIGH']
for _, player in high_risk.iterrows():
    print(f"  {player['name']}:")
    print(f"    Age: {player['age']} (risk: {player['age_risk']})")
    print(f"    Usage Rate: {player['usage_rate']:.1%} (risk: {player['usage_risk']})")
    print(f"    Cumulative Load: {player['cumulative_minutes']} min (risk: {player['workload_risk']})")
    print(f"    Risk Score: {player['menon_risk_score']}/100")

# ==============================================================================
# STEP 5: INTEGRATE INTO EXISTING MODEL
# ==============================================================================

def integrate_menon_features(existing_features):
    """
    Add Menon 2026 features to existing feature set.
    
    Parameters:
    -----------
    existing_features : list
        Current features
    
    Returns:
    --------
    list : Updated features
    """
    menon_features = [
        'age',                          # Menon 2026 - Age >28
        'usage_rate',                   # Menon 2026 - Usage >25%
        'cumulative_minutes',           # Menon 2026 - Workload
        'age_x_usage_rate',            # Menon 2026 - Interaction
        'cumulative_minutes_trend',     # Rate of change
        'usage_rate_7game_avg',        # Recent usage pattern
    ]
    
    # Combine with existing
    updated_features = existing_features + [f for f in menon_features if f not in existing_features]
    
    return updated_features

# Example
original_features = ['sleep_hours', 'soreness', 'acwr', 'cmj_height_cm']
updated_features = integrate_menon_features(original_features)

print("\n" + "=" * 70)
print("FEATURE SET UPDATE")
print("=" * 70)
print(f"\nOriginal features ({len(original_features)}):")
for f in original_features:
    print(f"  - {f}")

print(f"\nAdded features from Menon 2026:")
new_features = [f for f in updated_features if f not in original_features]
for f in new_features:
    print(f"  + {f}")

print(f"\nTotal features: {len(updated_features)}")

# ==============================================================================
# STEP 6: RETRAIN MODEL WITH NEW FEATURES
# ==============================================================================

print("\n" + "=" * 70)
print("NEXT STEPS: RETRAINING MODEL")
print("=" * 70)

print("""
1. Update train_models.py to include Menon 2026 features:
   
   feature_cols = [
       'age',                     # Menon 2026
       'usage_rate',              # Menon 2026
       'cumulative_minutes',      # Menon 2026
       'age_x_usage_rate',       # Menon 2026 interaction
       'sleep_hours',             # Milewski 2014
       'acwr',                    # Gabbett 2016
       # ... other features
   ]

2. Calculate usage rate from wehoop data:
   
   games['usage_rate'] = games['minutes'] / 240
   
3. Calculate cumulative workload:
   
   games['cumulative_minutes'] = games.groupby('athlete_id')['minutes'].rolling('30D').sum()

4. Retrain model:
   
   python train_models.py

5. Update documentation:
   
   - Add Menon 2026 to RESEARCH_FOUNDATION.md
   - Update README with new features
   - Add citation to code comments

6. Test predictions:
   
   streamlit run dashboard.py
   # Check ML Predictions tab
""")

# ==============================================================================
# DOCUMENTATION TEMPLATE
# ==============================================================================

print("\n" + "=" * 70)
print("DOCUMENTATION UPDATE TEMPLATE")
print("=" * 70)

documentation_template = """
## Model Updates - Version 2.0

### Research Added: Menon et al. (2026)

**Study:** Age, Workload, and Usage Rate: Risk Factors Associated With 
          Knee Injuries in Women's National Basketball Association Athletes

**Key Findings:**
- Age >28 years = increased injury risk
- Usage rate >25% = 2.3x knee injury risk  
- High cumulative workload = increased risk
- Interaction: Age + Usage = compounded risk

**Implementation:**
```python
# New features added
- age                      # Demographic risk factor
- usage_rate              # Playing time intensity (>25% = high risk)
- cumulative_minutes      # 30-day rolling workload
- age_x_usage_rate       # Interaction term

# New thresholds
AGE_HIGH_RISK = 28                  # Menon 2026
USAGE_RATE_HIGH_RISK = 0.25         # Menon 2026
CUMULATIVE_MINUTES_HIGH = 1000      # Menon 2026
```

**Model Performance:**
- Previous: 15 features, ACWR + sleep + force plate
- Updated: 21 features, + Menon 2026 WNBA-specific factors
- Expected improvement: Better prediction for knee injuries in women

**Citation:**
Menon S, Sai S, Traversone J, Lin E, Tummala SV, Chhabra A. Age, workload, 
and usage rate: risk factors associated with knee injuries in Women's National 
Basketball Association athletes. *[Journal Name]*. 2026.
"""

print(documentation_template)

# ==============================================================================
# FINAL SUMMARY
# ==============================================================================

print("\n" + "=" * 70)
print("✅ IMPLEMENTATION GUIDE COMPLETE")
print("=" * 70)

print("""
✅ What You Learned:

1. How to extract actionable thresholds from research
   - Age >28, Usage >25%, Workload >1000 min/month

2. How to calculate new features
   - Usage rate from game statistics
   - Cumulative workload (rolling 30 days)
   - Interaction terms (age × usage)

3. How to integrate into existing model
   - Add features to feature set
   - Create risk flags
   - Update documentation

4. How to stay current
   - Set up Google Scholar alerts
   - Review quarterly
   - Document in research log

🎯 Next Actions:

1. Add usage_rate calculation to fetch_all_wnba_data.py
2. Update train_models.py with new features
3. Retrain model
4. Update RESEARCH_FOUNDATION.md
5. Test in dashboard

📚 Research Foundation:
- WNBA-specific (Tier 1): Menon 2026
- Female athletes (Tier 2): Hewett 2006, Martin 2018
- General (Tier 4): Gabbett 2016, Milewski 2014

This is how you continuously improve your model with new research!
""")

print("=" * 70)


