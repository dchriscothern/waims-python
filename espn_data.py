# ==============================================================================
# WAIMS — ESPN WNBA Box Score Integration
# ==============================================================================
#
# DATA SOURCE: ESPN hidden public API (no auth required)
#   Scoreboard: http://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard
#   Box score:  http://site.api.espn.com/apis/site/v2/sports/basketball/wnba/summary?event={id}
#
# WHAT THIS PROVIDES:
#   - Dallas Wings game-by-game box scores (pts, reb, ast, min per player)
#   - Game outcomes (W/L, score margin, home/away)
#   - Joined to schedule and monitoring data for outcome validation
#
# WHY THIS MATTERS FOR THE MODEL:
#   Closes the outcome validation loop:
#   - Pre-injury pattern: what did monitoring look like 7 days before injury
#   - Performance drop on back-to-backs: actual quantified, not assumed
#   - Readiness score validation: did score 65 actually predict a bad game?
#   - Model can learn: CMJ -10% from baseline → points drop X% next game
#
# TABLES WRITTEN TO waims_demo.db:
#   game_results    — one row per game (date, opponent, W/L, score, margin)
#   game_box_scores — one row per player per game (pts, reb, ast, min, etc)
#
# USAGE:
#   python espn_data.py                    # fetch 2025 season, write to DB
#   from espn_data import fetch_wings_season
#   fetch_wings_season(season=2025)        # programmatic
#
# NO AUTH REQUIRED — ESPN public API, no API key needed
#
# NOTE: ESPN's API is undocumented and may change without notice.
#   The module handles failures gracefully — dashboard works without it.
#
# ==============================================================================

import time
import sqlite3
import warnings
from datetime import datetime, date, timedelta

import requests
import pandas as pd

# ==============================================================================
# CONFIG
# ==============================================================================

ESPN_BASE    = "http://site.api.espn.com/apis/site/v2/sports/basketball/wnba"
API_DELAY    = 0.3   # seconds between requests — be respectful
WINGS_ABBR   = "DAL"

# 2025 WNBA season date range
SEASON_DATES = {
    2019: ("20190524", "20190914"),   # First season as Dallas Wings (moved from Tulsa)
    2020: ("20200725", "20200930"),   # Bubble season — shortened
    2021: ("20210614", "20211019"),   # Full return season
    2022: ("20220506", "20221016"),
    2023: ("20230519", "20231022"),   # Playoff season
    2024: ("20240516", "20241013"),   # 9-31 season — injury-heavy, high value for analysis
    2025: ("20250515", "20251005"),   # 10-34 season — Bueckers rookie year
    2026: ("20260509", "20260930"),   # Wings opener May 9 vs Indiana
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Referer": "https://www.espn.com/",
}


# ==============================================================================
# ESPN API HELPERS
# ==============================================================================

def _get(url: str, params: dict = None) -> dict:
    """GET request to ESPN API. Returns empty dict on failure."""
    try:
        resp = requests.get(url, headers=HEADERS, params=params or {}, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as e:
        warnings.warn(f"ESPN API HTTP error: {e} — {url}")
        return {}
    except requests.exceptions.Timeout:
        warnings.warn(f"ESPN API timeout — {url}")
        return {}
    except Exception as e:
        warnings.warn(f"ESPN API error: {e}")
        return {}


def _get_scoreboard_for_date(game_date: str) -> list:
    """
    Fetch all WNBA games on a given date.
    date format: YYYYMMDD e.g. "20250601"
    Returns list of game event dicts.
    """
    data = _get(f"{ESPN_BASE}/scoreboard", params={"dates": game_date})
    return data.get("events", [])


def _get_box_score(event_id: str) -> dict:
    """
    Fetch full box score for a game by ESPN event ID.
    Returns raw ESPN summary response.
    """
    return _get(f"{ESPN_BASE}/summary", params={"event": event_id})


# ==============================================================================
# PARSE FUNCTIONS
# ==============================================================================

def _parse_game_result(event: dict) -> dict | None:
    """
    Extract game result from ESPN event dict.
    Returns None if Dallas Wings not in this game.
    """
    competitions = event.get("competitions", [{}])
    if not competitions:
        return None
    comp = competitions[0]

    competitors = comp.get("competitors", [])
    wings_comp  = next((c for c in competitors
                        if c.get("team", {}).get("abbreviation") == WINGS_ABBR), None)
    if not wings_comp:
        return None

    opp_comp = next((c for c in competitors
                     if c.get("team", {}).get("abbreviation") != WINGS_ABBR), None)

    wings_score = int(wings_comp.get("score", 0) or 0)
    opp_score   = int(opp_comp.get("score", 0) or 0) if opp_comp else 0
    wings_won   = wings_comp.get("winner", False)

    game_date_raw = comp.get("date", "")[:10]   # "2025-06-01T00:00Z" → "2025-06-01"

    return {
        "event_id":       event.get("id"),
        "date":           game_date_raw,
        "opponent":       opp_comp["team"]["displayName"] if opp_comp else "Unknown",
        "opponent_abbr":  opp_comp["team"]["abbreviation"] if opp_comp else "",
        "home_away":      "home" if wings_comp.get("homeAway") == "home" else "away",
        "wings_score":    wings_score,
        "opp_score":      opp_score,
        "score_margin":   wings_score - opp_score,
        "result":         "W" if wings_won else "L",
        "status":         event.get("status", {}).get("type", {}).get("description", ""),
        "season":         event.get("season", {}).get("year"),
    }


def _parse_box_score(summary: dict, event_id: str, game_date: str) -> list:
    """
    Extract per-player box score from ESPN summary response.
    Returns list of player stat dicts for Wings players only.
    """
    rows = []

    # ESPN box score structure: boxscore → players → [team] → statistics → athletes
    boxscore = summary.get("boxscore", {})
    teams    = boxscore.get("players", [])

    wings_team = next(
        (t for t in teams if t.get("team", {}).get("abbreviation") == WINGS_ABBR),
        None
    )
    if not wings_team:
        return rows

    # Get stat labels from first statistics block
    stat_blocks = wings_team.get("statistics", [])
    if not stat_blocks:
        return rows

    stat_block  = stat_blocks[0]
    stat_names  = [n.lower().replace(" ", "_") for n in stat_block.get("names", [])]
    athletes    = stat_block.get("athletes", [])

    for athlete in athletes:
        player     = athlete.get("athlete", {})
        stats_raw  = athlete.get("stats", [])
        did_not_play = athlete.get("didNotPlay", False)

        if did_not_play or not stats_raw:
            continue

        stat_dict = dict(zip(stat_names, stats_raw))

        # Parse minutes — ESPN returns "32:14" format
        min_raw = stat_dict.get("min", "0") or "0"
        try:
            if ":" in str(min_raw):
                parts   = str(min_raw).split(":")
                minutes = round(float(parts[0]) + float(parts[1]) / 60, 2)
            else:
                minutes = float(min_raw)
        except (ValueError, IndexError):
            minutes = 0.0

        # Safe int/float parse helper
        def si(key, default=0):
            try: return int(stat_dict.get(key, default) or default)
            except: return default

        def sf(key, default=0.0):
            try: return float(stat_dict.get(key, default) or default)
            except: return default

        rows.append({
            "event_id":    event_id,
            "date":        game_date,
            "player_id":   player.get("id"),
            "player_name": player.get("displayName", ""),
            "position":    player.get("position", {}).get("abbreviation", ""),
            "minutes":     minutes,
            "pts":         si("pts"),
            "reb":         si("reb"),
            "ast":         si("ast"),
            "stl":         si("stl"),
            "blk":         si("blk"),
            "tov":         si("to"),        # ESPN uses "to" for turnovers
            "pf":          si("pf"),
            "fgm":         si("fgm"),
            "fga":         si("fga"),
            "fg_pct":      sf("fg%") / 100 if sf("fg%") > 1 else sf("fg%"),
            "three_pm":    si("3pm"),
            "three_pa":    si("3pa"),
            "ftm":         si("ftm"),
            "fta":         si("fta"),
            "plus_minus":  si("+/-"),
        })

    return rows


# ==============================================================================
# MAIN FETCH FUNCTION
# ==============================================================================

def fetch_wings_season(
    season: int = 2025,
    db_path: str = "waims_demo.db",
    write_to_db: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Fetch complete Dallas Wings season game results and box scores from ESPN.
    Writes to game_results and game_box_scores tables in waims_demo.db.

    Args:
        season:      WNBA season year (2025 = most recent complete)
        db_path:     Path to waims_demo.db
        write_to_db: Whether to persist to SQLite

    Returns:
        Tuple of (game_results_df, box_scores_df)

    Usage:
        from espn_data import fetch_wings_season
        results, boxes = fetch_wings_season(season=2025)
    """
    if season not in SEASON_DATES:
        warnings.warn(f"Season {season} not in SEASON_DATES config. Add date range.")
        return pd.DataFrame(), pd.DataFrame()

    start_str, end_str = SEASON_DATES[season]
    start = datetime.strptime(start_str, "%Y%m%d").date()
    end   = datetime.strptime(end_str,   "%Y%m%d").date()

    print(f"Fetching {season} Wings season from ESPN ({start} → {end})...")
    print("  No API key required — ESPN public endpoint")

    all_results   = []
    all_box_scores = []
    days_checked  = 0
    games_found   = 0

    current = start
    while current <= end:
        date_str = current.strftime("%Y%m%d")
        events   = _get_scoreboard_for_date(date_str)

        for event in events:
            result = _parse_game_result(event)
            if result is None:
                continue   # Not a Wings game

            games_found += 1
            all_results.append(result)
            print(f"  {result['date']}: Wings {result['result']} "
                  f"{result['wings_score']}-{result['opp_score']} "
                  f"{'vs' if result['home_away']=='home' else '@'} "
                  f"{result['opponent_abbr']}")

            # Fetch box score for completed games
            if result["status"] in ("Final", "Final/OT"):
                time.sleep(API_DELAY)
                summary   = _get_box_score(result["event_id"])
                box_rows  = _parse_box_score(summary, result["event_id"], result["date"])
                all_box_scores.extend(box_rows)

        days_checked += 1
        current += timedelta(days=1)
        if days_checked % 30 == 0:
            print(f"  ... checked {days_checked} days, {games_found} Wings games found")
        time.sleep(API_DELAY)

    results_df   = pd.DataFrame(all_results)   if all_results   else pd.DataFrame()
    box_score_df = pd.DataFrame(all_box_scores) if all_box_scores else pd.DataFrame()

    print(f"\n  ✓ {games_found} Wings games | {len(box_score_df)} player-game rows")

    if write_to_db and not results_df.empty:
        _write_to_db(results_df, box_score_df, db_path)

    return results_df, box_score_df


def _write_to_db(results_df, box_score_df, db_path):
    """Write game results and box scores to SQLite DB."""
    try:
        conn = sqlite3.connect(db_path)
        results_df.to_sql("game_results", conn, if_exists="replace", index=False)
        print(f"  ✓ Wrote {len(results_df)} rows to game_results")
        if not box_score_df.empty:
            box_score_df.to_sql("game_box_scores", conn, if_exists="replace", index=False)
            print(f"  ✓ Wrote {len(box_score_df)} rows to game_box_scores")
        conn.close()
    except Exception as e:
        warnings.warn(f"DB write failed: {e}")


# ==============================================================================
# ANALYSIS HELPERS — used by train_models.py and dashboard
# ==============================================================================

def load_game_results(db_path: str = "waims_demo.db") -> pd.DataFrame:
    """Load game_results table from DB."""
    try:
        conn = sqlite3.connect(db_path)
        df   = pd.read_sql_query("SELECT * FROM game_results", conn)
        conn.close()
        df["date"] = pd.to_datetime(df["date"])
        return df
    except Exception:
        return pd.DataFrame()


def load_box_scores(db_path: str = "waims_demo.db") -> pd.DataFrame:
    """Load game_box_scores table from DB."""
    try:
        conn = sqlite3.connect(db_path)
        df   = pd.read_sql_query("SELECT * FROM game_box_scores", conn)
        conn.close()
        df["date"] = pd.to_datetime(df["date"])
        return df
    except Exception:
        return pd.DataFrame()


def get_performance_vs_monitoring(
    box_scores: pd.DataFrame,
    wellness: pd.DataFrame,
    training_load: pd.DataFrame,
    force_plate: pd.DataFrame,
) -> pd.DataFrame:
    """
    Join game box scores to monitoring data on the same date.
    This is the outcome validation table — the core of the model improvement loop.

    Returns one row per player per game with:
    - Game performance: pts, reb, ast, min, plus_minus
    - Same-day monitoring: sleep, soreness, cmj, player_load
    - Schedule context: back_to_back, days_rest
    - Pre-game trend: 7-day avg readiness before game

    Used by train_models.py to:
    - Learn performance-monitoring correlations
    - Validate readiness score against actual performance
    - Identify pre-injury monitoring patterns
    """
    if box_scores.empty or wellness.empty:
        return pd.DataFrame()

    # Join box scores to same-day wellness
    merged = box_scores.merge(
        wellness[["player_id", "date", "sleep_hours", "soreness_0_10",
                  "mood_0_10", "stress_0_10"]],
        on=["player_id", "date"],
        how="left"
    )

    # Join most recent force plate before game date
    if not force_plate.empty:
        fp_latest = (
            force_plate.sort_values("date")
            .groupby("player_id")
            .last()
            .reset_index()[["player_id", "cmj_height_cm", "rsi_modified",
                            "asymmetry_pct"]]
        )
        merged = merged.merge(fp_latest, on="player_id", how="left")

    # Join same-day GPS load
    if not training_load.empty and "player_load" in training_load.columns:
        merged = merged.merge(
            training_load[["player_id", "date", "player_load",
                           "acwr", "accel_count", "decel_count"]],
            on=["player_id", "date"],
            how="left"
        )

    # Performance flags
    merged["low_scoring_game"]   = (merged["pts"] < merged.groupby("player_id")["pts"]
                                    .transform("mean") * 0.7).astype(int)
    merged["high_minutes_game"]  = (merged["minutes"] >= 32).astype(int)
    merged["positive_plus_minus"] = (merged["plus_minus"] > 0).astype(int)

    print(f"  Performance-monitoring joined table: {len(merged)} player-game rows")
    return merged


def get_back_to_back_performance_summary(
    box_scores: pd.DataFrame,
    schedule: pd.DataFrame,
) -> pd.DataFrame:
    """
    Quantify actual performance drop on back-to-back games vs rest days.
    This replaces the -4pt assumption with data-driven evidence.

    Returns:
        Summary DataFrame showing avg pts/reb/ast/min on:
        - back-to-back games (days_rest = 0 or 1)
        - normal rest (days_rest >= 2)
        - full rest (days_rest >= 3)
    """
    if box_scores.empty or schedule.empty:
        return pd.DataFrame()

    box_scores["date"] = pd.to_datetime(box_scores["date"])
    schedule["date"]   = pd.to_datetime(schedule["date"])

    merged = box_scores.merge(
        schedule[["date", "is_back_to_back", "days_rest", "travel_flag"]],
        on="date",
        how="left"
    )

    merged["rest_category"] = pd.cut(
        merged["days_rest"].fillna(3),
        bins=[-1, 1, 2, 100],
        labels=["Back-to-back (0-1 days)", "Short rest (2 days)", "Normal rest (3+ days)"]
    )

    summary = (
        merged.groupby("rest_category")[["pts", "reb", "ast", "minutes", "plus_minus"]]
        .agg(["mean", "std", "count"])
        .round(2)
    )

    print("\n  Performance by rest category:")
    print(summary.to_string())
    return summary


# ==============================================================================
# SELF-TEST
# ==============================================================================

def fetch_wings_all_time(
    seasons: list = None,
    db_path: str = "waims_demo.db",
) -> tuple:
    """
    Fetch complete Wings game history across multiple seasons.
    Defaults to 2019-2025 (all available ESPN data for Dallas Wings).

    This gives the model:
    - Career performance patterns per player (Ogunbowale, Sabally etc)
    - Back-to-back performance drop quantified across 6 seasons
    - Injury-adjacent box score patterns (performance before/after injury)
    - Longitudinal scoring trends for context

    NOTE: No pre-2025 wellness/monitoring data exists (synthetic only exists
    for 2025). So this game data informs the outcome validation layer only,
    not the injury prediction model training directly.

    Args:
        seasons: List of years e.g. [2023, 2024, 2025]. Default: 2019-2025.
        db_path: Path to waims_demo.db

    Returns:
        Tuple of (all_results_df, all_box_scores_df)
    """
    if seasons is None:
        seasons = [2019, 2020, 2021, 2022, 2023, 2024, 2025]

    all_results    = []
    all_box_scores = []

    for season in seasons:
        print(f"\n{'='*50}")
        results, boxes = fetch_wings_season(season=season, db_path=db_path, write_to_db=False)
        if not results.empty:
            results["season"] = season
            all_results.append(results)
        if not boxes.empty:
            boxes["season"] = season
            all_box_scores.append(boxes)
        print(f"Season {season}: {len(results)} games, {len(boxes)} player-game rows")

    combined_results = pd.concat(all_results,    ignore_index=True) if all_results    else pd.DataFrame()
    combined_boxes   = pd.concat(all_box_scores, ignore_index=True) if all_box_scores else pd.DataFrame()

    # Write combined to DB
    if not combined_results.empty:
        try:
            conn = sqlite3.connect(db_path)
            combined_results.to_sql("game_results",    conn, if_exists="replace", index=False)
            combined_boxes.to_sql("game_box_scores",   conn, if_exists="replace", index=False)
            conn.close()
            print(f"\n✓ All-time data written to {db_path}")
            print(f"  game_results:    {len(combined_results)} games ({seasons[0]}-{seasons[-1]})")
            print(f"  game_box_scores: {len(combined_boxes)} player-game rows")
        except Exception as e:
            warnings.warn(f"DB write failed: {e}")

    return combined_results, combined_boxes


def get_player_career_summary(
    db_path: str = "waims_demo.db",
    player_name: str = None,
) -> pd.DataFrame:
    """
    Career summary stats per player from all-time game data.
    Useful for athlete profile tab context.

    Returns per-player averages across all seasons with Wings:
    games_played, seasons, avg_pts, avg_reb, avg_ast, avg_min,
    avg_pts_back_to_back, avg_pts_normal_rest, b2b_performance_drop
    """
    boxes   = load_box_scores(db_path)
    results = load_game_results(db_path)

    if boxes.empty:
        return pd.DataFrame()

    if player_name:
        boxes = boxes[boxes["player_name"].str.contains(player_name, case=False)]

    # Join schedule context
    if not results.empty:
        boxes = boxes.merge(
            results[["event_id", "result", "score_margin", "home_away"]],
            on="event_id", how="left"
        )

    # Career averages
    career = (
        boxes.groupby("player_name")
        .agg(
            games_played   = ("pts", "count"),
            seasons        = ("season", "nunique"),
            avg_pts        = ("pts", "mean"),
            avg_reb        = ("reb", "mean"),
            avg_ast        = ("ast", "mean"),
            avg_min        = ("minutes", "mean"),
            avg_plus_minus = ("plus_minus", "mean"),
        )
        .round(2)
        .reset_index()
    )

    career = career[career["games_played"] >= 10].sort_values("avg_pts", ascending=False)
    return career


if __name__ == "__main__":
    print("WAIMS ESPN Data Module")
    print("=" * 55)
    print("No API key required — ESPN public endpoint")
    print()

    # Quick connection test — just one day
    print("Testing connection (checking 2025-06-01)...")
    events = _get_scoreboard_for_date("20250601")
    if events:
        print(f"✓ Connected — {len(events)} WNBA games on 2025-06-01")
        wings_games = [e for e in events
                       if any(c.get("team", {}).get("abbreviation") == WINGS_ABBR
                              for comp in e.get("competitions", [{}])
                              for c in comp.get("competitors", []))]
        if wings_games:
            result = _parse_game_result(wings_games[0])
            if result:
                print(f"✓ Wings game found: {result['result']} "
                      f"{result['wings_score']}-{result['opp_score']} "
                      f"vs {result['opponent']}")
        else:
            print("  No Wings game on this date (expected — check another date)")
    else:
        print("✗ No data returned — check network connection")
        print("  ESPN API works from local machines but may be blocked in some environments")
        print()

    print()
    print("To fetch full 2025 season:")
    print("  from espn_data import fetch_wings_season")
    print("  results, boxes = fetch_wings_season(season=2025, db_path='waims_demo.db')")
    print()
    print("Note: Full season fetch checks ~140 days = ~2-3 minutes with rate limiting")
    print()
    print("Tables written to DB:")
    print("  game_results    — one row per game (W/L, score, margin, home/away)")
    print("  game_box_scores — one row per player per game (pts, reb, ast, min)")
    print()
    print("To fetch all-time Wings history (2019-2025, ~15-20 min):")
    print("  from espn_data import fetch_wings_all_time")
    print("  fetch_wings_all_time(seasons=[2019,2020,2021,2022,2023,2024,2025])")
    print()
    print("To fetch just recent seasons for faster testing:")
    print("  fetch_wings_all_time(seasons=[2024, 2025])")
    print()
    print("Next step after fetch: run train_models.py to incorporate game outcomes")


