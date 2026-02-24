"""
WAIMS Python - Basketball-Reference WNBA Data Scraper
Scrapes real WNBA game statistics from Basketball-Reference.com

This is a custom data pipeline that doesn't rely on broken packages.

Usage:
    python scrape_wnba_data.py

Data Source: https://www.basketball-reference.com/wnba/
Legal: Public data, respectful scraping with rate limiting
"""

import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import sqlite3
from datetime import datetime

print("=" * 70)
print("WAIMS - BASKETBALL-REFERENCE WNBA SCRAPER")
print("=" * 70)

# ==============================================================================
# CONFIGURATION
# ==============================================================================

SEASONS = [2023, 2024, 2025]
BASE_URL = "https://www.basketball-reference.com"
RATE_LIMIT_SECONDS = 3  # Be respectful to the website

print(f"\nConfiguration:")
print(f"  Data Source: Basketball-Reference.com")
print(f"  Seasons: {SEASONS}")
print(f"  Rate Limit: {RATE_LIMIT_SECONDS} seconds between requests")

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def get_page(url, max_retries=3):
    """
    Fetch a page with retry logic and rate limiting.
    """
    for attempt in range(max_retries):
        try:
            print(f"  Fetching: {url}")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Educational Research Project)'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Rate limiting
            time.sleep(RATE_LIMIT_SECONDS)
            
            return response.text
            
        except Exception as e:
            print(f"  Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(5)
            else:
                print(f"  ❌ Failed to fetch {url}")
                return None
    
    return None

def scrape_season_stats(season):
    """
    Scrape player per-game stats for a season.
    """
    url = f"{BASE_URL}/wnba/years/{season}_per_game.html"
    html = get_page(url)
    
    if not html:
        return None
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # Find the stats table
    table = soup.find('table', {'id': 'per_game_stats'})
    
    if not table:
        print(f"  ❌ Could not find stats table for {season}")
        return None
    
    # Parse table
    rows = []
    for tr in table.find('tbody').find_all('tr'):
        # Skip header rows
        if tr.find('th', {'scope': 'row'}):
            row_data = {}
            
            # Player name
            player_cell = tr.find('td', {'data-stat': 'player'})
            if player_cell and player_cell.find('a'):
                row_data['player_name'] = player_cell.find('a').text
                row_data['player_url'] = player_cell.find('a')['href']
            else:
                continue
            
            # Stats
            stats_to_extract = [
                'age', 'team_id', 'g', 'gs', 'mp_per_g',
                'fg_per_g', 'fga_per_g', 'fg_pct',
                'fg3_per_g', 'fg3a_per_g', 'fg3_pct',
                'ft_per_g', 'fta_per_g', 'ft_pct',
                'orb_per_g', 'drb_per_g', 'trb_per_g',
                'ast_per_g', 'stl_per_g', 'blk_per_g',
                'tov_per_g', 'pf_per_g', 'pts_per_g'
            ]
            
            for stat in stats_to_extract:
                cell = tr.find('td', {'data-stat': stat})
                if cell and cell.text:
                    try:
                        row_data[stat] = float(cell.text)
                    except:
                        row_data[stat] = cell.text
            
            row_data['season'] = season
            rows.append(row_data)
    
    df = pd.DataFrame(rows)
    print(f"  ✓ Scraped {len(df)} player records for {season}")
    
    return df

# ==============================================================================
# SCRAPE DATA
# ==============================================================================

print("\n" + "=" * 70)
print("SCRAPING WNBA DATA")
print("=" * 70)

all_seasons = []

for season in SEASONS:
    print(f"\n📅 Season {season}:")
    
    df = scrape_season_stats(season)
    
    if df is not None and len(df) > 0:
        all_seasons.append(df)
    else:
        print(f"  ⚠️  No data retrieved for {season}")

if len(all_seasons) == 0:
    print("\n❌ No data scraped!")
    print("This could be due to:")
    print("  1. Internet connection issues")
    print("  2. Website structure changed")
    print("  3. Rate limiting")
    exit(1)

# Combine all seasons
df_all = pd.concat(all_seasons, ignore_index=True)

print(f"\n✓ Total records scraped: {len(df_all)}")
print(f"  Players: {df_all['player_name'].nunique()}")
print(f"  Seasons: {df_all['season'].nunique()}")

# ==============================================================================
# CALCULATE ADDITIONAL METRICS
# ==============================================================================

print("\n" + "=" * 70)
print("CALCULATING METRICS")
print("=" * 70)

# Usage rate proxy (minutes per game / 48 minutes)
df_all['usage_rate_proxy'] = df_all['mp_per_g'] / 48

# Cumulative workload (games × minutes)
df_all['cumulative_minutes'] = df_all['g'] * df_all['mp_per_g']

# Workload per month (approximate WNBA season = 4 months)
df_all['minutes_per_month'] = df_all['cumulative_minutes'] / 4

print("✓ Calculated usage metrics")
print(f"  Average minutes per game: {df_all['mp_per_g'].mean():.1f}")
print(f"  Average usage rate: {df_all['usage_rate_proxy'].mean():.2%}")

# ==============================================================================
# SAVE DATA
# ==============================================================================

print("\n" + "=" * 70)
print("SAVING DATA")
print("=" * 70)

# Save to CSV
csv_file = 'basketball_reference_wnba_2023-2025.csv'
df_all.to_csv(csv_file, index=False)
print(f"✓ Saved: {csv_file}")

# Save to database
conn = sqlite3.connect('waims_demo.db')
df_all.to_sql('basketball_reference_stats', conn, if_exists='replace', index=False)
print(f"✓ Created table: basketball_reference_stats")

# Summary stats
summary = pd.read_sql_query("""
    SELECT 
        season,
        COUNT(DISTINCT player_name) as players,
        COUNT(*) as records,
        ROUND(AVG(mp_per_g), 1) as avg_mpg,
        ROUND(AVG(pts_per_g), 1) as avg_ppg
    FROM basketball_reference_stats
    GROUP BY season
    ORDER BY season
""", conn)

print("\n📊 Summary by Season:")
print(summary.to_string(index=False))

conn.close()

# ==============================================================================
# MENON 2026 RISK FACTOR ANALYSIS
# ==============================================================================

print("\n" + "=" * 70)
print("MENON 2026 RISK FACTORS")
print("=" * 70)

# Identify high-risk players based on Menon 2026
high_risk = df_all[
    (df_all['age'] > 28) & 
    (df_all['usage_rate_proxy'] > 0.25)
].copy()

print(f"\n⚠️  High-Risk Players (Age >28, Usage >25%):")
print(f"  Total: {len(high_risk)} player-seasons")

if len(high_risk) > 0:
    print("\n  Top 10 by Minutes:")
    top_risk = high_risk.nlargest(10, 'cumulative_minutes')[
        ['player_name', 'season', 'team_id', 'age', 'mp_per_g', 'usage_rate_proxy']
    ]
    print(top_risk.to_string(index=False))

# ==============================================================================
# FINAL SUMMARY
# ==============================================================================

print("\n" + "=" * 70)
print("✅ SCRAPING COMPLETE!")
print("=" * 70)

print(f"\n📊 What You Have:")
print(f"   CSV file: {csv_file}")
print(f"   Database table: basketball_reference_stats")
print(f"   Total records: {len(df_all):,}")
print(f"   Unique players: {df_all['player_name'].nunique()}")
print(f"   Seasons: {', '.join(map(str, SEASONS))}")

print(f"\n🎯 Next Steps:")
print(f"   1. Use this real data to train your ML model")
print(f"   2. Add public injury data (WNBA.com injury reports)")
print(f"   3. Retrain: python train_models.py")
print(f"   4. Much more credible model with real data!")

print(f"\n📝 Data Source:")
print(f"   Basketball-Reference.com (public statistics)")
print(f"   Respectfully scraped with rate limiting")

print("\n" + "=" * 70)
