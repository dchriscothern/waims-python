# ==============================================================================
# WAIMS — WNBA Data Module (balldontlie API)
# ==============================================================================
#
# DATA SOURCE: balldontlie.io WNBA API (free tier)
#   Base URL:  https://api.balldontlie.io/wnba/v1/
#   Auth:      Authorization header (API key, no "Bearer" prefix)
#   Docs:      https://www.balldontlie.io/docs
#
# FREE TIER ENDPOINTS USED:
#   /teams              — all WNBA teams (used for connection test)
#   /games              — game results by season/team
#   /stats              — per-game box scores (used to calculate season averages)
#
# NOTE ON TIERS:
#   player_season_stats is a PAID endpoint (All-Star $9.99/mo).
#   This module calculates season averages from free-tier /stats instead.
#   Same data, one extra aggregation step — works on free tier.
#
# API KEY SETUP:
#   1. Create .env file in waims-python folder:
#        BALLDONTLIE_API_KEY=your_key_here
#   2. Never commit .env to GitHub — it's listed in .gitignore
#   3. Streamlit Cloud: Settings → Secrets → BALLDONTLIE_API_KEY = "your_key"
#
# INSTALL:
#   pip install python-dotenv requests
#
# ==============================================================================

import os
import time
import sqlite3
import warnings
from datetime import datetime
from pathlib import Path

import requests
import pandas as pd

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # reads from environment directly if dotenv not installed

# ==============================================================================
# CONFIG
# ==============================================================================

BASE_URL       = "https://api.balldontlie.io/wnba/v1"
API_DELAY      = 0.5        # seconds between calls (free tier: 30 req/min)
WINGS_TEAM_ID  = 11         # Dallas Wings — confirmed from API March 2026
CACHE_HOURS    = 24         # How long to use cached DB data before re-fetching

POSITION_MAP = {
    "G": "G", "Guard": "G", "PG": "G", "SG": "G", "G-F": "G",
    "F": "F", "Forward": "F", "SF": "F", "PF": "F", "F-G": "F", "F-C": "F",
    "C": "C", "Center": "C", "C-F": "C",
}


def _get_api_key() -> str:
    key = os.getenv("BALLDONTLIE_API_KEY", "").strip()
    if not key:
        raise EnvironmentError(
            "BALLDONTLIE_API_KEY not found.\n"
            "Add to .env file:  BALLDONTLIE_API_KEY=your_key_here\n"
            "Or set as environment variable before running."
        )
    return key


def _headers() -> dict:
    return {"Authorization": _get_api_key()}


# ==============================================================================
# API HELPERS
# ==============================================================================

def _get(endpoint: str, params: dict = None) -> dict:
    """Single GET request — raises clear errors on auth/rate limit failures."""
    url = f"{BASE_URL}/{endpoint.lstrip('/')}"
    resp = requests.get(url, headers=_headers(), params=params or {}, timeout=15)
    if resp.status_code == 401:
        raise PermissionError("API key invalid. Check BALLDONTLIE_API_KEY in .env")
    if resp.status_code == 403:
        raise PermissionError(
            "Endpoint requires paid tier. "
            "This module uses only free-tier endpoints (/games, /stats)."
        )
    if resp.status_code == 429:
        raise RuntimeError("Rate limit hit — wait 60 seconds and retry.")
    resp.raise_for_status()
    return resp.json()


def _get_paginated(endpoint: str, params: dict = None, max_pages: int = 30) -> list:
    """Fetch all pages from a paginated endpoint using cursor pagination."""
    params = dict(params or {})
    params["per_page"] = 100
    all_data = []

    for _ in range(max_pages):
        result = _get(endpoint, params)
        all_data.extend(result.get("data", []))
        next_cursor = result.get("meta", {}).get("next_cursor")
        if not next_cursor:
            break
        params["cursor"] = next_cursor
        time.sleep(API_DELAY)

    return all_data


# ==============================================================================
# CORE DATA FUNCTIONS
# ==============================================================================

def get_all_game_stats(season: int = 2025) -> pd.DataFrame:
    """
    Fetch all per-game player box scores for a season from /stats.
    This is a free-tier endpoint — used to calculate season averages ourselves.

    Args:
        season: e.g. 2025. Use 2026 once season starts May 9.

    Returns:
        DataFrame with one row per player per game.
        Columns: player_id, player_name, position, team_id, team_abbr,
                 game_id, min, pts, reb, ast, stl, blk, tov, pf, fg_pct
    """
    print(f"  Fetching {season} WNBA game stats from balldontlie (free tier)...")
    try:
        data = _get_paginated(
            "stats",
            params={"seasons[]": season, "per_page": 100}
        )
    except Exception as e:
        warnings.warn(f"Stats fetch failed: {e}")
        return pd.DataFrame()

    if not data:
        print(f"  No stats data for {season} — season may not have started yet.")
        return pd.DataFrame()

    rows = []
    for item in data:
        player  = item.get("player", {})
        team    = item.get("team", {})
        pos_raw = player.get("position_abbreviation") or player.get("position") or "F"

        # Parse minutes — can be "32" or "32:15" format
        min_raw = item.get("min", "0") or "0"
        try:
            if ":" in str(min_raw):
                parts = str(min_raw).split(":")
                minutes = float(parts[0]) + float(parts[1]) / 60
            else:
                minutes = float(min_raw)
        except (ValueError, IndexError):
            minutes = 0.0

        fgm = float(item.get("fgm", 0) or 0)
        fga = float(item.get("fga", 0) or 0)

        rows.append({
            "player_id":   player.get("id"),
            "player_name": f"{player.get('first_name','')} {player.get('last_name','')}".strip(),
            "position_raw": pos_raw,
            "position":    POSITION_MAP.get(pos_raw, "F"),
            "team_id":     team.get("id"),
            "team_abbr":   team.get("abbreviation", ""),
            "game_id":     item.get("game", {}).get("id"),
            "min":         round(minutes, 2),
            "pts":         float(item.get("pts", 0) or 0),
            "reb":         float(item.get("reb", 0) or 0),
            "ast":         float(item.get("ast", 0) or 0),
            "stl":         float(item.get("stl", 0) or 0),
            "blk":         float(item.get("blk", 0) or 0),
            "tov":         float(item.get("turnover", 0) or 0),
            "pf":          float(item.get("pf", 0) or 0),
            "fg_pct":      round(fgm / fga, 3) if fga > 0 else 0.0,
            "plus_minus":  float(item.get("plus_minus", 0) or 0),
        })

    df = pd.DataFrame(rows)
    print(f"  Retrieved {len(df)} game-level stat rows ({season})")
    return df


def get_league_season_averages(season: int = 2025) -> pd.DataFrame:
    """
    Calculate per-game season averages from individual game stats.
    Aggregates /stats (free endpoint) to get the same result as
    /player_season_stats (paid endpoint).

    Filters to players with 10+ games (qualifying threshold).
    """
    game_stats = get_all_game_stats(season=season)
    if game_stats.empty:
        return pd.DataFrame()

    metrics = ["min", "pts", "reb", "ast", "stl", "blk", "tov", "pf", "plus_minus"]

    # Aggregate per player
    agg_dict = {m: "mean" for m in metrics}
    agg_dict["fg_pct"] = "mean"
    agg_dict["game_id"] = "count"

    season_avgs = (
        game_stats.groupby(["player_id", "player_name", "position", "team_id", "team_abbr"])
        .agg({**{m: "mean" for m in metrics}, "fg_pct": "mean", "game_id": "count"})
        .reset_index()
        .rename(columns={"game_id": "games_played"})
    )

    # Round averages
    for col in metrics + ["fg_pct"]:
        season_avgs[col] = season_avgs[col].round(3)

    # Filter qualifying players
    season_avgs = season_avgs[season_avgs["games_played"] >= 10].reset_index(drop=True)
    season_avgs["season"] = season

    print(f"  Season averages: {len(season_avgs)} qualifying players (10+ games)")
    return season_avgs


def get_positional_benchmarks(season: int = 2025) -> pd.DataFrame:
    """
    Build positional benchmarks (mean + SD by G/F/C) from live season data.
    Falls back to hardcoded 2025 data if API is unavailable.

    Returns:
        DataFrame with columns:
        season, position_group, metric, mean, std, n_players, source, fetched_at
    """
    season_avgs = get_league_season_averages(season=season)

    if season_avgs.empty:
        print("  API returned no data — using static 2025 fallback benchmarks")
        return _get_static_benchmarks()

    metrics = ["min", "pts", "reb", "ast", "stl", "blk", "tov", "pf", "fg_pct", "plus_minus"]
    rows = []

    for pos_group in ["G", "F", "C"]:
        subset = season_avgs[season_avgs["position"] == pos_group]
        if len(subset) < 3:
            continue
        for metric in metrics:
            vals = subset[metric].dropna()
            if len(vals) < 3:
                continue
            rows.append({
                "season":         str(season),
                "position_group": pos_group,
                "metric":         metric,
                "mean":           round(float(vals.mean()), 3),
                "std":            round(float(vals.std()),  3),
                "n_players":      int(len(vals)),
                "source":         f"{season} WNBA Regular Season (balldontlie live)",
                "fetched_at":     datetime.utcnow().isoformat(),
            })

    df = pd.DataFrame(rows)
    print(f"  Built benchmarks: {df['position_group'].nunique()} positions, "
          f"{df['metric'].nunique()} metrics")
    return df


def get_wings_season_stats(season: int = 2025) -> pd.DataFrame:
    """
    Dallas Wings player season averages specifically.
    Uses the same aggregated game stats as benchmarks.
    """
    season_avgs = get_league_season_averages(season=season)
    if season_avgs.empty:
        return pd.DataFrame()
    wings = season_avgs[season_avgs["team_id"] == WINGS_TEAM_ID].copy()
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
        player_value:   The player's value (e.g. 32.0 for minutes)
        metric:         e.g. "min", "pts", "reb"
        position_group: "G", "F", or "C"
        benchmarks_df:  From get_positional_benchmarks() — uses static if None

    Returns:
        dict with zscore, mean, std, interpretation
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
    zscore = round((player_value - mean) / std, 2) if std > 0 else 0.0

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
# DATABASE
# ==============================================================================

def write_benchmarks_to_db(
    benchmarks: pd.DataFrame,
    db_path: str = "waims_demo.db",
) -> bool:
    """Write positional benchmarks to WAIMS SQLite wnba_benchmarks table."""
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

    For 2026 season (starts May 9):
        benchmarks = fetch_wings_benchmarks(season=2026)
    """
    print(f"Fetching WNBA {season} benchmarks from balldontlie (free tier)...")
    try:
        benchmarks = get_positional_benchmarks(season=season)
    except EnvironmentError as e:
        print(f"⚠ {e}")
        print("  Using static 2025 fallback.")
        benchmarks = _get_static_benchmarks()
    except Exception as e:
        print(f"⚠ API error: {e}")
        print("  Using static 2025 fallback.")
        benchmarks = _get_static_benchmarks()

    if write_to_db and not benchmarks.empty:
        write_benchmarks_to_db(benchmarks, db_path=db_path)

    return benchmarks


# ==============================================================================
# STATIC FALLBACK (2025 WNBA season)
# ==============================================================================

def _get_static_benchmarks() -> pd.DataFrame:
    """
    Hardcoded 2025 WNBA regular season averages by position group.
    Used as fallback when API is unavailable or off-season.
    Update values here when 2026 season completes.
    """
    STATIC = {
        "min":        {"G": (26.8,7.2,52),  "F": (24.1,7.8,48),  "C": (20.4,7.1,22)},
        "pts":        {"G": (12.4,5.9,52),  "F": (10.8,5.3,48),  "C": ( 9.6,4.8,22)},
        "reb":        {"G": ( 3.2,1.8,52),  "F": ( 5.4,2.4,48),  "C": ( 7.8,2.9,22)},
        "ast":        {"G": ( 3.8,2.3,52),  "F": ( 1.9,1.2,48),  "C": ( 1.2,0.9,22)},
        "stl":        {"G": ( 1.1,0.6,52),  "F": ( 0.8,0.5,48),  "C": ( 0.6,0.4,22)},
        "blk":        {"G": ( 0.2,0.3,52),  "F": ( 0.6,0.5,48),  "C": ( 1.4,0.9,22)},
        "tov":        {"G": ( 2.1,1.0,52),  "F": ( 1.5,0.8,48),  "C": ( 1.3,0.7,22)},
        "pf":         {"G": ( 1.8,0.7,52),  "F": ( 2.1,0.8,48),  "C": ( 2.6,0.9,22)},
        "fg_pct":     {"G": (0.421,0.058,52),"F": (0.448,0.062,48),"C": (0.502,0.071,22)},
        "plus_minus": {"G": ( 0.4,4.8,52),  "F": ( 0.2,4.5,48),  "C": ( 0.1,4.2,22)},
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


# ==============================================================================
# SELF-TEST
# ==============================================================================

if __name__ == "__main__":
    print("WAIMS WNBA API Module — balldontlie.io (free tier)")
    print("=" * 55)

    # 1. Check API key
    try:
        key = _get_api_key()
        print(f"✓ API key loaded ({key[:6]}...{key[-4:]})")
    except EnvironmentError as e:
        print(f"✗ {e}")
        exit(1)

    # 2. Connection test — /teams is free tier
    print("\nTesting connection...")
    try:
        result = _get("teams")
        teams  = result.get("data", [])
        print(f"✓ Connected — {len(teams)} WNBA teams found")
        wings = next((t for t in teams if "Dallas" in t.get("full_name", "")), None)
        if wings:
            print(f"✓ Dallas Wings — team_id: {wings['id']} | abbr: {wings['abbreviation']}")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        exit(1)

    # 3. Fetch a small sample of game stats to verify free tier works
    print("\nTesting /stats endpoint (free tier)...")
    try:
        sample = _get("stats", {"seasons[]": 2025, "per_page": 5})
        rows   = sample.get("data", [])
        print(f"✓ /stats endpoint working — sample size: {len(rows)} rows")
        if rows:
            p = rows[0].get("player", {})
            print(f"  Sample player: {p.get('first_name')} {p.get('last_name')} "
                  f"({p.get('position_abbreviation')}) — "
                  f"{rows[0].get('pts')} pts, {rows[0].get('reb')} reb")
    except PermissionError as e:
        print(f"✗ {e}")
    except Exception as e:
        print(f"✗ Stats test failed: {e}")

    # 4. Show what full fetch would do
    print("\nTo fetch full 2025 benchmarks and write to DB:")
    print("  from wnba_api import fetch_wings_benchmarks")
    print("  fetch_wings_benchmarks(season=2025, db_path='waims_demo.db')")
    print()
    print("For 2026 season (starts May 9):")
    print("  fetch_wings_benchmarks(season=2026, db_path='waims_demo.db')")
    print()
    print("Static fallback is always available (no API needed):")
    print("  from wnba_api import _get_static_benchmarks")
    print("  benchmarks = _get_static_benchmarks()")
