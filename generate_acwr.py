"""
Generate ACWR (Acute:Chronic Workload Ratio) data
Run this once to add ACWR table to waims_demo.db
"""

import sqlite3
import pandas as pd
import numpy as np

print("=" * 60)
print("Generating ACWR Data")
print("=" * 60)

conn = sqlite3.connect('waims_demo.db')

# Load training load
print("\n1. Loading training load data...")
training_load = pd.read_sql_query("SELECT * FROM training_load", conn)
training_load['date'] = pd.to_datetime(training_load['date'])
training_load = training_load.sort_values(['player_id', 'date'])

print(f"   Found {len(training_load)} training records")
print(f"   Players: {training_load['player_id'].nunique()}")

# Calculate ACWR for each player
print("\n2. Calculating ACWR...")
acwr_data = []

for player_id in training_load['player_id'].unique():
    player_data = training_load[training_load['player_id'] == player_id].copy()
    
    for idx, row in player_data.iterrows():
        # Get last 7 days (acute)
        acute_end = row['date']
        acute_start = acute_end - pd.Timedelta(days=7)
        acute_data = player_data[
            (player_data['date'] >= acute_start) & 
            (player_data['date'] <= acute_end)
        ]
        acute_load = acute_data['total_daily_load'].sum()
        
        # Get last 28 days (chronic)
        chronic_start = acute_end - pd.Timedelta(days=28)
        chronic_data = player_data[
            (player_data['date'] >= chronic_start) & 
            (player_data['date'] <= acute_end)
        ]
        chronic_load = chronic_data['total_daily_load'].sum() / 4  # Average per week
        
        # Calculate ACWR
        if chronic_load > 0:
            acwr_value = acute_load / chronic_load
        else:
            acwr_value = 1.0
        
        acwr_data.append({
            'player_id': player_id,
            'date': row['date'],
            'acwr': round(acwr_value, 3),
            'acute_load': round(acute_load, 1),
            'chronic_load': round(chronic_load * 4, 1)  # Total 4-week load
        })

# Create dataframe and save
print("\n3. Saving to database...")
acwr_df = pd.DataFrame(acwr_data)
acwr_df.to_sql('acwr', conn, if_exists='replace', index=False)

print("\n" + "=" * 60)
print("✓ ACWR Table Created Successfully!")
print("=" * 60)
print(f"\nRecords: {len(acwr_df)}")
print(f"Players: {acwr_df['player_id'].nunique()}")
print(f"Date range: {acwr_df['date'].min()} to {acwr_df['date'].max()}")
print(f"ACWR range: {acwr_df['acwr'].min():.2f} - {acwr_df['acwr'].max():.2f}")

# Show sample
print("\nSample data:")
print(acwr_df.head(5))

# Show risk distribution
high_risk = len(acwr_df[acwr_df['acwr'] > 1.5])
optimal = len(acwr_df[(acwr_df['acwr'] >= 0.8) & (acwr_df['acwr'] <= 1.3)])
low = len(acwr_df[acwr_df['acwr'] < 0.8])

print(f"\nACWR Distribution:")
print(f"  High Risk (>1.5): {high_risk} records ({high_risk/len(acwr_df)*100:.1f}%)")
print(f"  Optimal (0.8-1.3): {optimal} records ({optimal/len(acwr_df)*100:.1f}%)")
print(f"  Low (<0.8): {low} records ({low/len(acwr_df)*100:.1f}%)")

conn.close()

print("\n✓ Done! You can now run dashboard.py")
print("=" * 60)
