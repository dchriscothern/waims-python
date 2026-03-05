# ==============================================================================
# WAIMS — WNBA Benchmarks Module
# ==============================================================================
#
# CURRENT STATUS: Static 2025 benchmarks (no API required)
#
# UPGRADE PATH — uncomment one block when ready:
#
#   TIER 1 — balldontlie All-Star ($9.99/mo):
#     Unlocks /stats and /player_season_stats endpoints
#     Set BALLDONTLIE_API_KEY in .env and set USE_LIVE_API = True below
#     Live data auto-updates when 2026 season starts May 9
#
#   TIER 2 — Synergy Sports (team license):
#     Play-type data, shot quality, defensive metrics
#     Contact Wings front office — standard WNBA team tool
#     Would replace this module entirely with richer data
#
#   TIER 3 — Second Spectrum (team license):
#     True optical tracking — distance, sprints, acceleration
#     WNBA league-wide system, request through Wings FO
#     Replaces GPS proxy data in generate_database.py as well
#
# CURRENT BEHAVIOR:
#   Returns hardcoded 2025 WNBA regular season averages by position (G/F/C).
#   Already written to waims_demo.db wnba_benchmarks table.
#   Dashboard reads this for population context alongside individual monitoring.
#
# USAGE:
#   from wnba_api import fetch_wings_benchmarks, get_player_zscore_vs_position
#   benchmarks = fetch_wings_benchmarks()                          # static
#   benchmarks = fetch_wings_benchmarks(use_live_api=True)        # paid tier
#
# INSTALL (only needed when upgrading to live API):
#   pip install python-dotenv requests
#
# ==============================================================================

import os
import sqlite3
import warnings
from datetime import datetime

import pandas as pd

# ==============================================================================
# UPGRADE SWITCH
# ==============================================================================
# Set to True when you have a paid balldontlie key and want live data.
# Everything else stays the same — just flips the data source.
USE_LIVE_API = False


# ==============================================================================
# 2025 WNBA REGULAR SEASON BENCHMARKS (static)
# ==============================================================================
# Per-game averages for qualifying players (min 10 games, 40-game season)
# Position groups: G = Guards, F = Forwards, C = Centers
#
# TO UPDATE FOR 2026:
#   Either set USE_LIVE_API = True (paid tier fetches automatically),
#   or update the values in STATIC_2025 below once season completes.
#
# Wings context: Ogunbowale (G) ~20ppg, Sabally (F) ~18ppg, McCowan (C) ~8ppg

STATIC_2025 = {
    #metric       G                  F                  C
    "min":      {"G":(26.8,7.2,52), "F":(24.1,7.8,48), "C":(20.4,7.1,22)},
    "pts":      {"G":(12.4,5.9,52), "F":(10.8,5.3,48), "C":( 9.6,4.8,22)},
    "reb":      {"G":( 3.2,1.8,52), "F":( 5.4,2.4,48), "C":( 7.8,2.9,22)},
    "ast":      {"G":( 3.8,2.3,52), "F":( 1.9,1.2,48), "C":( 1.2,0.9,22)},
    "stl":      {"G":( 1.1,0.6,52), "F":( 0.8,0.5,48), "C":( 0.6,0.4,22)},
    "blk":      {"G":( 0.2,0.3,52), "F":( 0.6,0.5,48), "C":( 1.4,0.9,22)},
    "tov":      {"G":( 2.1,1.0,52), "F":( 1.5,0.8,48), "C":( 1.3,0.7,22)},
    "pf":       {"G":( 1.8,0.7,52), "F":( 2.1,0.8,48), "C":( 2.6,0.9,22)},
    "fg_pct":   {"G":(0.421,0.058,52),"F":(0.448,0.062,48),"C":(0.502,0.071,22)},
    "plus_minus":{"G":(0.4,4.8,52), "F":( 0.2,4.5,48), "C":( 0.1,4.2,22)},
}


# ==============================================================================
# CORE FUNCTIONS
# ==============================================================================

def get_positional_benchmarks(season: int = 2025, use_live_api: bool = False) -> pd.DataFrame:
    """
    Return WNBA positional benchmarks as a DataFrame.

    Args:
        season:       Season year. Static only supports 2025 currently.
        use_live_api: Set True with paid balldontlie key to fetch live data.

    Returns:
        DataFrame: season, position_group, metric, mean, std, n_players, source
    """
    if use_live_api or USE_LIVE_API:
        return _fetch_live_benchmarks(season=season)
    return _get_static_benchmarks()


def get_player_zscore_vs_position(
    player_value: float,
    metric: str,
    position_group: str,
    benchmarks_df: pd.DataFrame = None,
) -> dict:
    """
    How far does a player's stat deviate from their positional average?

    Args:
        player_value:   e.g. 32.0 (minutes)
        metric:         "min", "pts", "reb", "ast", "stl", "blk",
                        "tov", "pf", "fg_pct", "plus_minus"
        position_group: "G", "F", or "C"
        benchmarks_df:  From get_positional_benchmarks() — loads static if None

    Returns:
        dict: zscore, mean, std, n_players, interpretation

    Example:
        get_player_zscore_vs_position(32.0, "min", "G")
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


def write_benchmarks_to_db(
    benchmarks: pd.DataFrame,
    db_path: str = "waims_demo.db",
) -> bool:
    """Write benchmarks to WAIMS SQLite wnba_benchmarks table."""
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


def fetch_wings_benchmarks(
    season: int = 2025,
    db_path: str = "waims_demo.db",
    write_to_db: bool = True,
    use_live_api: bool = False,
) -> pd.DataFrame:
    """
    Main entry point. Get benchmarks and optionally write to DB.

    Current behavior:  returns static 2025 data (no API needed)
    Upgrade to live:   set use_live_api=True or USE_LIVE_API=True at top of file

    Args:
        season:       Season year
        db_path:      Path to waims_demo.db
        write_to_db:  Whether to write to SQLite
        use_live_api: Override USE_LIVE_API flag for this call only
    """
    benchmarks = get_positional_benchmarks(season=season, use_live_api=use_live_api)
    if write_to_db and not benchmarks.empty:
        write_benchmarks_to_db(benchmarks, db_path=db_path)
    return benchmarks


# ==============================================================================
# STATIC DATA
# ==============================================================================

def _get_static_benchmarks() -> pd.DataFrame:
    """Return hardcoded 2025 WNBA benchmarks. No API, no network, always works."""
    rows = []
    for metric, positions in STATIC_2025.items():
        for pos_group, (mean, std, n) in positions.items():
            rows.append({
                "season":         "2025",
                "position_group": pos_group,
                "metric":         metric,
                "mean":           mean,
                "std":            std,
                "n_players":      n,
                "source":         "2025 WNBA Regular Season (static)",
                "fetched_at":     datetime.utcnow().isoformat(),
            })
    df = pd.DataFrame(rows)
    print(f"✓ Loaded {len(df)} benchmark rows — 2025 WNBA season (static)")
    return df


# ==============================================================================
# LIVE API (balldontlie paid tier — uncomment when ready)
# ==============================================================================

def _fetch_live_benchmarks(season: int = 2025) -> pd.DataFrame:
    """
    Fetch live benchmarks from balldontlie paid tier.
    Called automatically when USE_LIVE_API = True.

    UPGRADE STEPS:
      1. Subscribe to balldontlie All-Star ($9.99/mo) at app.balldontlie.io
      2. Add key to .env:  BALLDONTLIE_API_KEY=your_key_here
      3. pip install python-dotenv requests
      4. Set USE_LIVE_API = True at top of this file
      5. Run: python wnba_api.py

    Falls back to static data if API call fails.
    """
    # Load .env
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    import requests
    import time

    api_key = os.getenv("BALLDONTLIE_API_KEY", "").strip()
    if not api_key:
        warnings.warn("BALLDONTLIE_API_KEY not set — falling back to static data.")
        return _get_static_benchmarks()

    BASE_URL     = "https://api.balldontlie.io/wnba/v1"
    POSITION_MAP = {
        "G":"G","Guard":"G","PG":"G","SG":"G","G-F":"G",
        "F":"F","Forward":"F","SF":"F","PF":"F","F-G":"F","F-C":"F",
        "C":"C","Center":"C","C-F":"C",
    }
    headers = {"Authorization": api_key}

    def paginate(endpoint, params):
        params = dict(params)
        params["per_page"] = 100
        all_data = []
        for _ in range(30):
            resp = requests.get(f"{BASE_URL}/{endpoint}", headers=headers,
                                params=params, timeout=15)
            if resp.status_code in (401, 403):
                raise PermissionError(f"API key insufficient for /{endpoint} — check plan tier")
            resp.raise_for_status()
            result = resp.json()
            all_data.extend(result.get("data", []))
            cursor = result.get("meta", {}).get("next_cursor")
            if not cursor:
                break
            params["cursor"] = cursor
            time.sleep(0.5)
        return all_data

    try:
        print(f"  Fetching {season} WNBA stats from balldontlie (paid tier)...")

        # Try player_season_stats first (All-Star tier)
        try:
            data = paginate("player_season_stats", {"season": season, "season_type": 2})
            source = "player_season_stats"
        except PermissionError:
            # Fall back to aggregating /stats (also paid but lower tier)
            print("  player_season_stats unavailable — aggregating from /stats...")
            data = paginate("stats", {"seasons[]": season})
            source = "stats_aggregated"

        if not data:
            print(f"  No data for {season} — season may not have started.")
            return _get_static_benchmarks()

        # Parse into DataFrame
        rows = []
        for item in data:
            player  = item.get("player", {})
            team    = item.get("team", {})
            pos_raw = player.get("position_abbreviation") or "F"
            rows.append({
                "player_id":   player.get("id"),
                "player_name": f"{player.get('first_name','')} {player.get('last_name','')}".strip(),
                "position":    POSITION_MAP.get(pos_raw, "F"),
                "team_abbr":   team.get("abbreviation", ""),
                "games_played": item.get("games_played", 1),
                "min":   float(item.get("min", 0) or 0),
                "pts":   float(item.get("pts", 0) or 0),
                "reb":   float(item.get("reb", 0) or 0),
                "ast":   float(item.get("ast", 0) or 0),
                "stl":   float(item.get("stl", 0) or 0),
                "blk":   float(item.get("blk", 0) or 0),
                "tov":   float(item.get("turnover", item.get("tov", 0)) or 0),
                "pf":    float(item.get("pf", 0) or 0),
                "fg_pct": float(item.get("fg_pct", 0) or 0),
                "plus_minus": float(item.get("plus_minus", 0) or 0),
            })

        df = pd.DataFrame(rows)
        df = df[df["games_played"] >= 10]

        # Build positional benchmarks
        metrics = ["min","pts","reb","ast","stl","blk","tov","pf","fg_pct","plus_minus"]
        bench_rows = []
        for pos in ["G","F","C"]:
            sub = df[df["position"] == pos]
            for metric in metrics:
                vals = sub[metric].dropna()
                if len(vals) < 3:
                    continue
                bench_rows.append({
                    "season": str(season), "position_group": pos, "metric": metric,
                    "mean": round(float(vals.mean()), 3),
                    "std":  round(float(vals.std()),  3),
                    "n_players": int(len(vals)),
                    "source": f"{season} WNBA Regular Season ({source}, balldontlie)",
                    "fetched_at": datetime.utcnow().isoformat(),
                })

        result = pd.DataFrame(bench_rows)
        print(f"  ✓ Live benchmarks: {len(result)} rows from {len(df)} qualifying players")
        return result

    except PermissionError as e:
        warnings.warn(f"Paid tier required: {e} — falling back to static data.")
        return _get_static_benchmarks()
    except Exception as e:
        warnings.warn(f"Live API failed: {e} — falling back to static data.")
        return _get_static_benchmarks()


# ==============================================================================
# SELF-TEST
# ==============================================================================

if __name__ == "__main__":
    print("WAIMS WNBA Benchmarks Module")
    print("=" * 55)
    print(f"Mode: {'LIVE API' if USE_LIVE_API else 'Static 2025 data'}")
    print()

    benchmarks = get_positional_benchmarks()

    print()
    print(f"{'Metric':<14} {'G mean':>8} {'F mean':>8} {'C mean':>8}")
    print("-" * 44)
    for metric in STATIC_2025.keys():
        sub = benchmarks[benchmarks["metric"] == metric]
        g = sub[sub["position_group"]=="G"]["mean"].values
        f = sub[sub["position_group"]=="F"]["mean"].values
        c = sub[sub["position_group"]=="C"]["mean"].values
        print(f"{metric:<14}"
              f"{g[0]:>8.3f}" if len(g) else f"{'–':>8}",
              end="")
        print(f"{f[0]:>8.3f}" if len(f) else f"{'–':>8}", end="")
        print(f"{c[0]:>8.3f}" if len(c) else f"{'–':>8}")

    print()
    print("Z-score example — 32 min/game for a guard:")
    result = get_player_zscore_vs_position(32.0, "min", "G", benchmarks)
    print(f"  {result['interpretation']}")

    print()
    print("Upgrade paths:")
    print("  balldontlie All-Star ($9.99/mo): set USE_LIVE_API = True above")
    print("  Synergy Sports: team license via Wings FO, replace this module")
    print("  Second Spectrum: optical tracking, team license via Wings FO")
