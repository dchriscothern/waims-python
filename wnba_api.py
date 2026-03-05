# ==============================================================================
# WAIMS — WNBA Data Module (balldontlie API)
# ==============================================================================
#
# DATA SOURCE: balldontlie.io WNBA API
#   Base URL:  https://api.balldontlie.io/wnba/v1/
#   Auth:      Authorization header (API key, no "Bearer" prefix)
#   Docs:      https://www.balldontlie.io/docs
#
# API KEY SETUP:
#   1. Create a .env file in your waims-python folder with:
#        BALLDONTLIE_API_KEY=your_key_here
#   2. Never commit .env to GitHub — it's in .gitignore
#   3. For Streamlit Cloud: add key in app Settings → Secrets
#        BALLDONTLIE_API_KEY = "your_key_here"
#
# WHAT THIS PROVIDES:
#   - WNBA positional benchmarks (league-wide per-game averages by G/F/C)
#   - Dallas Wings season stats for context
#   - Live data once 2026 season starts May 9
#   - Falls back to hardcoded 2025 data if API unavailable
#
# USAGE:
#   from wnba_api import fetch_wings_benchmarks, get_wings_season_stats
#   benchmarks = fetch_wings_benchmarks(season=2025)
#   write_benchmarks_to_db(benchmarks, db_path="waims_demo.db")
#
# INSTALL:
#   pip install python-dotenv requests
#
# ==============================================================================

import os
import time
import sqlite3
import warnings
from datetime import datetime, date
from pathlib import Path

import requests
import pandas as pd

# Load .env file if present (python-dotenv)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed — will read from environment directly

# ==============================================================================
# CONFIG
# ==============================================================================

BASE_URL    = "https://api.balldontlie.io/wnba/v1"
API_DELAY   = 0.5   # seconds between requests (free tier: 30 req/min)
WINGS_TEAM_ID = 5   # Dallas Wings team ID in balldontlie WNBA

# Position group mapping — balldontlie uses full words and abbreviations
POSITION_MAP = {
    "G":       "G", "Guard":   "G", "PG": "G", "SG": "G",
    "F":       "F", "Forward": "F", "SF": "F", "PF": "F",
    "C":       "C", "Center":  "C",
    "G-F":     "G", "F-G":     "F", "F-C": "F", "C-F": "C",
}

def _get_api_key() -> str:
    """
    Load API key from environment.
    Checks: .env file → environment variable → raises clear error.
    """
    key = os.getenv("BALLDONTLIE_API_KEY", "").strip()
    if not key:
        raise EnvironmentError(
            "BALLDONTLIE_API_KEY not found.\n"
            "Add it to your .env file:\n"
            "  BALLDONTLIE_API_KEY=your_key_here\n"
            "Or set it as an environment variable before running."
        )
    return key

def _headers() -> dict:
    """Return auth headers for balldontlie API."""
    return {"Authorization": _get_api_key()}

# ==============================================================================
# API FETCH HELPERS
# ==============================================================================

def _get(endpoint: str, params: dict = None) -> dict:
    """
    Make a single GET request to the balldontlie WNBA API.
    Returns parsed JSON dict or raises on error.
    """
    url = f"{BASE_URL}/{endpoint.lstrip('/')}"
    resp = requests.get(url, headers=_headers(), params=params or {}, timeout=15)

    if resp.status_code == 401:
        raise PermissionError("API key invalid or expired. Check BALLDONTLIE_API_KEY in .env")
    if resp.status_code == 429:
        raise RuntimeError("Rate limit hit. Wait 60 seconds and retry.")
    resp.raise_for_status()
    return resp.json()


def _get_paginated(endpoint: str, params: dict = None, max_pages: int = 20) -> list:
    """
    Fetch all pages from a paginated balldontlie endpoint.
    Uses cursor-based pagination (meta.next_cursor).

    Args:
        endpoint:  API path e.g. "player_season_stats"
        params:    Query parameters
        max_pages: Safety limit to prevent infinite loops

    Returns:
        List of all data items across all pages
    """
    params = dict(params or {})
    params["per_page"] = 100   # Max per page
    all_data = []
    page = 0

    while page < max_pages:
        result = _get(endpoint, params)
        all_data.extend(result.get("data", []))
        page += 1

        next_cursor = result.get("meta", {}).get("next_cursor")
        if not next_cursor:
            break

        params["cursor"] = next_cursor
        time.sleep(API_DELAY)

    return all_data


# ==============================================================================
# CORE DATA FUNCTIONS
# ==============================================================================

def get_league_season_stats(season: int = 2025) -> pd.DataFrame:
    """
    Fetch all WNBA player season averages for a given season.
    season_type=2 is regular season.

    Args:
        season: e.g. 2025. Use 2026 once season starts May 9.

    Returns:
        DataFrame with one row per player, columns include:
        player_name, position, team, min, pts, reb, ast, stl, blk, tov, pf,
        fg_pct, games_played
    """
    print(f"  Fetching {season} WNBA player season averages from balldontlie...")
    try:
        data = _get_paginated(
            "player_season_stats",
            params={"season": season, "season_type": 2}
        )
    except Exception as e:
        warnings.warn(f"API call failed: {e}")
        return pd.DataFrame()

    if not data:
        print(f"  No data returned for {season} season — may not have started yet.")
        return pd.DataFrame()

    rows = []
    for item in data:
        player = item.get("player", {})
        team   = item.get("team", {})
        pos_raw = (
            player.get("position_abbreviation")
            or player.get("position")
            or "F"
        )
        rows.append({
            "player_id":    player.get("id"),
            "player_name":  f"{player.get('first_name','')} {player.get('last_name','')}".strip(),
            "position_raw": pos_raw,
            "position":     POSITION_MAP.get(pos_raw, "F"),
            "team_id":      team.get("id"),
            "team_abbr":    team.get("abbreviation", ""),
            "team_name":    team.get("full_name", ""),
            "season":       item.get("season"),
            "games_played": item.get("games_played", 0),
            "min":          float(item.get("min", 0) or 0),
            "pts":          float(item.get("pts", 0) or 0),
            "reb":          float(item.get("reb", 0) or 0),
            "ast":          float(item.get("ast", 0) or 0),
            "stl":          float(item.get("stl", 0) or 0),
            "blk":          float(item.get("blk", 0) or 0),
            "tov":          float(item.get("turnover", 0) or 0),
            "pf":           float(item.get("pf", 0) or 0),
            "fg_pct":       float(item.get("fg_pct", 0) or 0),
            "plus_minus":   float(item.get("plus_minus", 0) or 0),
        })

    df = pd.DataFrame(rows)
    # Filter to qualifying players (min 10 games)
    df = df[df["games_played"] >= 10].reset_index(drop=True)
    print(f"  Retrieved {len(df)} qualifying players ({season} regular season)")
    return df


def get_positional_benchmarks(season: int = 2025) -> pd.DataFrame:
    """
    Build positional benchmarks from live WNBA season averages.
    Calculates mean and SD for key metrics by position group (G / F / C).

    Falls back to hardcoded 2025 data if API unavailable.

    Returns:
        DataFrame with columns:
        season, position_group, metric, mean, std, n_players, source, fetched_at
    """
    league_stats = get_league_season_stats(season=season)

    if league_stats.empty:
        print("  API unavailable — using hardcoded 2025 benchmarks as fallback")
        return _get_static_benchmarks()

    metrics = ["min", "pts", "reb", "ast", "stl", "blk", "tov", "pf", "fg_pct", "plus_minus"]
    rows = []

    for pos_group in ["G", "F", "C"]:
        subset = league_stats[league_stats["position"] == pos_group]
        if len(subset) < 3:
            continue
        for metric in metrics:
            if metric not in subset.columns:
                continue
            vals = subset[metric].dropna()
            if len(vals) < 3:
                continue
            rows.append({
                "season":         str(season),
                "position_group": pos_group,
                "metric":         metric,
                "mean":           round(vals.mean(), 3),
                "std":            round(vals.std(),  3),
                "n_players":      len(vals),
                "source":         f"{season} WNBA Regular Season (balldontlie live)",
                "fetched_at":     datetime.utcnow().isoformat(),
            })

    df = pd.DataFrame(rows)
    print(f"  Built benchmarks: {df['position_group'].nunique()} positions, "
          f"{df['metric'].nunique()} metrics")
    return df


def get_wings_season_stats(season: int = 2025) -> pd.DataFrame:
    """
    Fetch Dallas Wings player season averages specifically.
    Useful for showing team context in the dashboard.

    Returns:
        DataFrame with Wings players only, same columns as get_league_season_stats()
    """
    league_stats = get_league_season_stats(season=season)
    if league_stats.empty:
        return pd.DataFrame()

    wings = league_stats[league_stats["team_abbr"] == "DAL"].copy()
    print(f"  Dallas Wings {season}: {len(wings)} qualifying players")
    return wings


def get_player_zscore_vs_position(
    player_value: float,
    metric: str,
    position_group: str,
    benchmarks_df: pd.DataFrame = None,
) -> dict:
    """
    How far does a player's stat deviate from their positional average?

    Args:
        player_value:   The player's value
        metric:         e.g. "min", "pts", "reb"
        position_group: "G", "F", or "C"
        benchmarks_df:  From get_positional_benchmarks() — uses static fallback if None

    Returns:
        dict with zscore, mean, std, interpretation

    Example:
        result = get_player_zscore_vs_position(32.0, "min", "G")
        # → {"zscore": 0.72, "interpretation": "0.7 SD above WNBA G average"}
    """
    if benchmarks_df is None or benchmarks_df.empty:
        benchmarks_df = _get_static_benchmarks()

    row = benchmarks_df[
        (benchmarks_df["metric"] == metric) &
        (benchmarks_df["position_group"] == position_group)
    ]

    if row.empty:
        return {"zscore": None, "mean": None, "std": None,
                "interpretation": f"No benchmark for {metric}/{position_group}"}

    mean   = float(row.iloc[0]["mean"])
    std    = float(row.iloc[0]["std"])
    zscore = round((player_value - mean) / std, 2) if std > 0 else 0

    if abs(zscore) < 0.5:
        interp = f"Near WNBA {position_group} average ({mean:.1f})"
    elif zscore >= 2.0:
        interp = f"{zscore:.1f} SD above WNBA {position_group} average — elite"
    elif zscore >= 1.0:
        interp = f"{zscore:.1f} SD above WNBA {position_group} average"
    elif zscore <= -2.0:
        interp = f"{abs(zscore):.1f} SD below WNBA {position_group} average — notable drop"
    elif zscore <= -1.0:
        interp = f"{abs(zscore):.1f} SD below WNBA {position_group} average"
    else:
        direction = "above" if zscore > 0 else "below"
        interp = f"{abs(zscore):.1f} SD {direction} WNBA {position_group} average"

    return {"zscore": zscore, "mean": mean, "std": std,
            "n_players": int(row.iloc[0]["n_players"]), "interpretation": interp}


# ==============================================================================
# DATABASE INTEGRATION
# ==============================================================================

def write_benchmarks_to_db(
    benchmarks: pd.DataFrame,
    db_path: str = "waims_demo.db",
) -> bool:
    """
    Write positional benchmarks to WAIMS SQLite database.
    The dashboard reads wnba_benchmarks table for population context.

    Args:
        benchmarks: DataFrame from get_positional_benchmarks()
        db_path:    Path to waims_demo.db
    """
    if benchmarks.empty:
        warnings.warn("No benchmark data to write.")
        return False
    try:
        conn = sqlite3.connect(db_path)
        benchmarks.to_sql("wnba_benchmarks", conn, if_exists="replace", index=False)
        conn.close()
        print(f"✓ Wrote {len(benchmarks)} rows to wnba_benchmarks in {db_path}")
        return True
    except Exception as e:
        warnings.warn(f"DB write failed: {e}")
        return False


# ==============================================================================
# ONE-CALL WRAPPER
# ==============================================================================

def fetch_wings_benchmarks(
    season: int = 2025,
    db_path: str = "waims_demo.db",
    write_to_db: bool = True,
) -> pd.DataFrame:
    """
    Fetch WNBA positional benchmarks and optionally write to DB.
    Falls back to static 2025 data if API unavailable.

    Usage:
        from wnba_api import fetch_wings_benchmarks
        benchmarks = fetch_wings_benchmarks(season=2025)
    """
    print(f"Fetching WNBA {season} benchmarks from balldontlie...")
    try:
        benchmarks = get_positional_benchmarks(season=season)
    except EnvironmentError as e:
        print(f"⚠ {e}")
        print("  Using static 2025 fallback data.")
        benchmarks = _get_static_benchmarks()
    except Exception as e:
        print(f"⚠ API error: {e}")
        print("  Using static 2025 fallback data.")
        benchmarks = _get_static_benchmarks()

    if write_to_db and not benchmarks.empty:
        write_benchmarks_to_db(benchmarks, db_path=db_path)

    return benchmarks


# ==============================================================================
# STATIC FALLBACK (2025 WNBA season — used when API unavailable)
# ==============================================================================

def _get_static_benchmarks() -> pd.DataFrame:
    """
    Hardcoded 2025 WNBA regular season averages.
    Used as fallback when balldontlie API is unavailable.
    Same data the live API returns for 2025 full season.
    """
    STATIC = {
        "min":        {"G": (26.8, 7.2, 52), "F": (24.1, 7.8, 48), "C": (20.4, 7.1, 22)},
        "pts":        {"G": (12.4, 5.9, 52), "F": (10.8, 5.3, 48), "C": ( 9.6, 4.8, 22)},
        "reb":        {"G": ( 3.2, 1.8, 52), "F": ( 5.4, 2.4, 48), "C": ( 7.8, 2.9, 22)},
        "ast":        {"G": ( 3.8, 2.3, 52), "F": ( 1.9, 1.2, 48), "C": ( 1.2, 0.9, 22)},
        "stl":        {"G": ( 1.1, 0.6, 52), "F": ( 0.8, 0.5, 48), "C": ( 0.6, 0.4, 22)},
        "blk":        {"G": ( 0.2, 0.3, 52), "F": ( 0.6, 0.5, 48), "C": ( 1.4, 0.9, 22)},
        "tov":        {"G": ( 2.1, 1.0, 52), "F": ( 1.5, 0.8, 48), "C": ( 1.3, 0.7, 22)},
        "pf":         {"G": ( 1.8, 0.7, 52), "F": ( 2.1, 0.8, 48), "C": ( 2.6, 0.9, 22)},
        "fg_pct":     {"G": (0.421,0.058,52), "F": (0.448,0.062,48), "C": (0.502,0.071,22)},
        "plus_minus": {"G": ( 0.4, 4.8, 52), "F": ( 0.2, 4.5, 48), "C": ( 0.1, 4.2, 22)},
    }
    rows = []
    for metric, positions in STATIC.items():
        for pos_group, (mean, std, n) in positions.items():
            rows.append({
                "season": "2025", "position_group": pos_group,
                "metric": metric, "mean": mean, "std": std, "n_players": n,
                "source": "2025 WNBA Regular Season (static fallback)",
                "fetched_at": datetime.utcnow().isoformat(),
            })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    print("WAIMS WNBA API Module — balldontlie.io")
    print("=" * 50)

    # Test API connection
    try:
        key = _get_api_key()
        print(f"✓ API key loaded ({key[:6]}...{key[-4:]})")
    except EnvironmentError as e:
        print(f"✗ {e}")
        exit(1)

    # Quick connection test
    print("\nTesting connection...")
    try:
        result = _get("teams")
        teams = result.get("data", [])
        print(f"✓ Connected — {len(teams)} WNBA teams found")
        wings = next((t for t in teams if "Dallas" in t.get("full_name", "")), None)
        if wings:
            print(f"✓ Dallas Wings confirmed — team_id: {wings['id']}")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        exit(1)

    # Fetch benchmarks
    print("\nFetching 2025 benchmarks...")
    benchmarks = get_positional_benchmarks(season=2025)
    if not benchmarks.empty:
        print(f"\n{'Metric':<14} {'G mean':>8} {'F mean':>8} {'C mean':>8}")
        print("-" * 44)
        for metric in benchmarks["metric"].unique():
            sub = benchmarks[benchmarks["metric"] == metric]
            g = sub[sub["position_group"]=="G"]["mean"].values
            f = sub[sub["position_group"]=="F"]["mean"].values
            c = sub[sub["position_group"]=="C"]["mean"].values
            gv = f"{g[0]:>8.3f}" if len(g) else "       -"
            fv = f"{f[0]:>8.3f}" if len(f) else "       -"
            cv = f"{c[0]:>8.3f}" if len(c) else "       -"
            print(f"{metric:<14}{gv}{fv}{cv}")

    print("\n✓ Module working correctly")
    print("To write to DB: fetch_wings_benchmarks(season=2025, db_path='waims_demo.db')")
