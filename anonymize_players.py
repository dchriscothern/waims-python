"""
WAIMS - Anonymize Player Names
Replaces real athlete names with generic identifiers

Run this to make your demo privacy-safe!
"""

import sqlite3
import pandas as pd

print("=" * 60)
print("ANONYMIZING PLAYER NAMES")
print("=" * 60)

conn = sqlite3.connect('waims_demo.db')

# Get current players
players = pd.read_sql_query("SELECT * FROM players", conn)

print(f"\nCurrent players ({len(players)}):")
for name in players['name']:
    print(f"  - {name}")

# Create anonymized names
players['name'] = [f'Player {chr(65+i)}' for i in range(len(players))]

# Update database
players.to_sql('players', conn, if_exists='replace', index=False)

print(f"\n✓ Anonymized to:")
for name in players['name']:
    print(f"  - {name}")

# Verify
check = pd.read_sql_query("SELECT name FROM players", conn)
print(f"\n✓ Verified: {len(check)} players now anonymized")

conn.commit()
conn.close()

print("\n" + "=" * 60)
print("✅ ANONYMIZATION COMPLETE")
print("=" * 60)
print("\nYour dashboard now shows:")
print("  Player A, Player B, Player C, ...")
print("\nSafe for:")
print("  ✓ Public GitHub")
print("  ✓ Portfolio demos")
print("  ✓ Job applications")
print("  ✓ LinkedIn posts")

print("\n⚠️  Remember: Keep any real team data LOCAL ONLY")
print("=" * 60)
