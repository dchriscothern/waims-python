# ==============================================================================
# WAIMS — WNBA Stats API Integration
# Fetches official WNBA data via nba_api (stats.wnba.com, league_id='10')
# ==============================================================================
#
# WHY nba_api OVER wehoop:
#   - nba_api hits stats.wnba.com directly (official source)
#   - wehoop wraps ESPN endpoint which is less stable and volunteer-maintained
#   - nba_api released through Feb 2026, actively maintained on PyPI
#   - WNBA support via league_id='10' across all endpoints
#
# WHAT THIS PROVIDES (game output data — NOT internal monitoring):
#   ✅ Player game logs (minutes, pts, reb, ast, stl, blk, +/-)
#   ✅ Season averages by position → positional benchmarks
#   ✅ Team game schedule with home/away and outcomes
#   ✅ Player roster with positions, heights, ages
#   ❌ GPS/distance (requires Second Spectrum or Kinexon hardware)
#   ❌ Optical tracking (Second Spectrum — team access only)
#   ❌ Force plate / internal load (proprietary hardware)
#
# ARCHITECTURE ROLE:
#   Python WAIMS (this file) → writes wnba_benchmarks table to SQLite DB
#   R-WAIMS (wehoop) → deeper statistical research layer, same underlying data
#   Dashboard reads benchmarks for context (e.g. "CMJ 2SD below WNBA positional avg")
#
# INSTALL:
#   pip install nba_api
#
# USAGE:
#   from wnba_api import WNBAStatsClient
#   client = WNBAStatsClient()
#   benchmarks = client.get_positional_benchmarks(season="2025")
#   client.write_benchmarks_to_db(benchmarks, db_path="waims_demo.db")
#
# AUTHOR: WAIMS Python System
# REFERENCES:
#   - nba_api: github.com/swar/nba_api (league_id='10' for WNBA)
#   - stats.wnba.com: official WNBA statistics
#   - Dallas Wings team_id: 1611661321
# ==============================================================================

import time
import sqlite3
import warnings
from datetime import datetime, date
from pathlib import Path

import pandas as pd

# nba_api — pip install nba_api
try:
    from nba_api.stats.endpoints import (
        PlayerGameLog,
        LeagueDashPlayerStats,
        CommonTeamRoster,
        TeamGameLog,
    )
    from nba_api.stats.static import teams as nba_teams
    NBA_API_AVAILABLE = True
except ImportError:
    NBA_API_AVAILABLE = False
    warnings.warn(
        "nba_api not installed. Run: pip install nba_api\n"
        "WNBA benchmark features will be unavailable until installed.",
        ImportWarning,
        stacklevel=2,
    )

# ==============================================================================
# CONSTANTS
# ==============================================================================

WNBA_LEAGUE_ID   = "10"          # WNBA league_id for all nba_api endpoints
DALLAS_WINGS_ID  = 1611661321    # Official WNBA team_id for Dallas Wings
API_DELAY        = 0.6           # Seconds between API calls (rate limiting)

# Required headers for stats.wnba.com — same domain as stats.nba.com
# The API blocks requests without a proper browser-like User-Agent
HEADERS = {
    "Accept":          "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection":      "keep-alive",
    "Host":            "stats.nba.com",
    "Origin":          "https://www.wnba.com",
    "Referer":         "https://www.wnba.com/",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    ),
    "x-nba-stats-origin": "stats",
    "x-nba-stats-token":  "true",
}

# Positional groups for WNBA benchmarking
# Guards handle more acceleration load; forwards/centers more contact/deceleration
POSITION_GROUPS = {
    "G":  ["G", "PG", "SG", "G-F"],
    "F":  ["F", "SF", "PF", "F-G", "F-C"],
    "C":  ["C", "C-F"],
}


# ==============================================================================
# CLIENT CLASS
# ==============================================================================

class WNBAStatsClient:
    """
    Client for WNBA Stats API via nba_api.
    Provides player benchmarks, game logs, and roster data
    for integration with the WAIMS monitoring dashboard.

    Raises ImportError at instantiation if nba_api is not installed.
    """

    def __init__(self):
        if not NBA_API_AVAILABLE:
            raise ImportError(
                "nba_api is required. Install with: pip install nba_api"
            )
        self._cache = {}

    # ──────────────────────────────────────────────────────────────────────────
    # ROSTER
    # ──────────────────────────────────────────────────────────────────────────

    def get_team_roster(self, season: str = "2025") -> pd.DataFrame:
        """
        Fetch Dallas Wings roster for a given season.

        Args:
            season: Season year string e.g. "2025", "2026"

        Returns:
            DataFrame with player names, positions, numbers, ages
        """
        cache_key = f"roster_{season}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            roster = CommonTeamRoster(
                team_id=str(DALLAS_WINGS_ID),
                season=season,
                league_id_nullable=WNBA_LEAGUE_ID,
                headers=HEADERS,
                timeout=30,
            )
            time.sleep(API_DELAY)
            df = roster.get_data_frames()[0]
            df.columns = df.columns.str.lower()
            self._cache[cache_key] = df
            return df
        except Exception as e:
            warnings.warn(f"Roster fetch failed ({season}): {e}")
            return pd.DataFrame()

    # ──────────────────────────────────────────────────────────────────────────
    # GAME LOGS
    # ──────────────────────────────────────────────────────────────────────────

    def get_player_game_logs(
        self,
        player_id: int,
        season: str = "2025",
        season_type: str = "Regular Season",
    ) -> pd.DataFrame:
        """
        Fetch game-by-game stats for a single player.

        Args:
            player_id:   WNBA player_id (from roster)
            season:      e.g. "2025"
            season_type: "Regular Season", "Playoffs", "Pre Season"

        Returns:
            DataFrame with per-game stats sorted newest first
        """
        try:
            logs = PlayerGameLog(
                player_id=str(player_id),
                season=season,
                season_type_all_star=season_type,
                league_id_nullable=WNBA_LEAGUE_ID,
                headers=HEADERS,
                timeout=30,
            )
            time.sleep(API_DELAY)
            df = logs.get_data_frames()[0]
            df.columns = df.columns.str.lower()
            df["game_date"] = pd.to_datetime(df["game_date"])
            return df.sort_values("game_date", ascending=False).reset_index(drop=True)
        except Exception as e:
            warnings.warn(f"Game log fetch failed (player {player_id}): {e}")
            return pd.DataFrame()

    def get_team_game_log(
        self,
        season: str = "2025",
        season_type: str = "Regular Season",
    ) -> pd.DataFrame:
        """
        Fetch game-by-game results for Dallas Wings.
        Useful for annotating schedule with outcomes and game-day load context.

        Returns:
            DataFrame with game dates, opponents, W/L, points
        """
        try:
            log = TeamGameLog(
                team_id=str(DALLAS_WINGS_ID),
                season=season,
                season_type_all_star=season_type,
                league_id_nullable=WNBA_LEAGUE_ID,
                headers=HEADERS,
                timeout=30,
            )
            time.sleep(API_DELAY)
            df = log.get_data_frames()[0]
            df.columns = df.columns.str.lower()
            df["game_date"] = pd.to_datetime(df["game_date"])
            return df.sort_values("game_date", ascending=False).reset_index(drop=True)
        except Exception as e:
            warnings.warn(f"Team game log fetch failed: {e}")
            return pd.DataFrame()

    # ──────────────────────────────────────────────────────────────────────────
    # LEAGUE-WIDE BENCHMARKS
    # ──────────────────────────────────────────────────────────────────────────

    def get_league_player_stats(
        self,
        season: str = "2025",
        per_mode: str = "PerGame",
    ) -> pd.DataFrame:
        """
        Fetch league-wide player stats for a season.
        Used to build positional benchmarks (e.g. avg minutes for guards).

        Args:
            season:   e.g. "2025"
            per_mode: "PerGame", "Totals", "Per36", "Per100Possessions"

        Returns:
            DataFrame with all WNBA players, stats, positions
        """
        cache_key = f"league_stats_{season}_{per_mode}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            # nba_api parameter name changed between versions:
            # older versions: per_mode_simple
            # newer versions: per_mode_simple still used but some builds differ
            # Try both names gracefully
            stats = LeagueDashPlayerStats(
                    season=season,
                    per_mode_detailed=per_mode,
                    league_id_nullable=WNBA_LEAGUE_ID,
                    season_type_all_star="Regular Season",
                    headers=HEADERS,
                    timeout=60,
                )
            time.sleep(API_DELAY)
            df = stats.get_data_frames()[0]
            df.columns = df.columns.str.lower()
            self._cache[cache_key] = df
            return df
        except Exception as e:
            warnings.warn(f"League stats fetch failed ({season}): {e}")
            return pd.DataFrame()

    def get_positional_benchmarks(self, season: str = "2025") -> pd.DataFrame:
        """
        Build positional benchmarks from league-wide per-game stats.
        Returns mean and SD for key metrics by position group (G / F / C).

        These benchmarks feed the dashboard context:
        e.g. "Player's minutes are 1.5 SD above WNBA guard average"

        Args:
            season: Season year string

        Returns:
            DataFrame with columns:
            position_group, metric, mean, std, n_players
        """
        df = self.get_league_player_stats(season=season)
        if df.empty:
            return pd.DataFrame()

        # Map raw positions to G / F / C groups
        def map_position(pos):
            if not isinstance(pos, str):
                return "F"
            pos = pos.upper().strip()
            for group, variants in POSITION_GROUPS.items():
                if pos in variants:
                    return group
            return "F"  # Default

        df["position_group"] = df.get("player_position", df.get("position", "F")).apply(map_position)

        # Metrics relevant to monitoring context
        benchmark_metrics = [
            "min",           # Minutes per game
            "pts",           # Points
            "reb",           # Rebounds (contact/jumping proxy)
            "ast",           # Assists
            "stl",           # Steals (defensive effort)
            "blk",           # Blocks
            "tov",           # Turnovers (fatigue proxy)
            "pf",            # Personal fouls
            "plus_minus",    # Net impact
        ]

        available = [m for m in benchmark_metrics if m in df.columns]
        rows = []

        for metric in available:
            for pos_group in ["G", "F", "C"]:
                subset = df[df["position_group"] == pos_group][metric].dropna()
                if len(subset) < 3:
                    continue
                rows.append({
                    "season":         season,
                    "position_group": pos_group,
                    "metric":         metric,
                    "mean":           round(subset.mean(), 3),
                    "std":            round(subset.std(),  3),
                    "n_players":      len(subset),
                    "fetched_at":     datetime.utcnow().isoformat(),
                })

        return pd.DataFrame(rows)

    # ──────────────────────────────────────────────────────────────────────────
    # GAME LOAD PROXY
    # ──────────────────────────────────────────────────────────────────────────

    def calculate_game_load_proxy(self, game_log: pd.DataFrame) -> pd.DataFrame:
        """
        Estimate physical demand from box score statistics.
        This is a PROXY only — true game load requires Second Spectrum
        optical tracking or in-arena GPS (Kinexon).

        Formula: load_proxy = min * (1 + reb/10 + (stl+blk)/5)
        Based on: Weiss et al. 2017 (basketball load estimation from stats)

        NOTE: For real production, request Second Spectrum access from the Wings.
        This provides actual distance, sprint counts, and acceleration load.

        Args:
            game_log: DataFrame from get_player_game_logs()

        Returns:
            DataFrame with game_load_proxy and high_load_flag columns added
        """
        if game_log.empty:
            return game_log

        # Ensure numeric
        for col in ["min", "reb", "stl", "blk"]:
            if col in game_log.columns:
                game_log[col] = pd.to_numeric(game_log[col], errors="coerce").fillna(0)

        game_log["game_load_proxy"] = (
            game_log.get("min", 0)
            * (1
               + game_log.get("reb", 0) / 10
               + (game_log.get("stl", 0) + game_log.get("blk", 0)) / 5)
        ).round(1)

        # Flag high-demand games (starters >30min or high defensive actions)
        game_log["high_load_flag"] = (
            (game_log.get("min", 0) >= 30)
            | ((game_log.get("stl", 0) + game_log.get("blk", 0)) >= 5)
        ).astype(int)

        return game_log

    # ──────────────────────────────────────────────────────────────────────────
    # DATABASE INTEGRATION
    # ──────────────────────────────────────────────────────────────────────────

    def write_benchmarks_to_db(
        self,
        benchmarks: pd.DataFrame,
        db_path: str = "waims_demo.db",
    ) -> bool:
        """
        Write positional benchmarks to WAIMS SQLite database.
        The dashboard reads this table for population-context displays.

        Creates table: wnba_benchmarks
        Columns: season, position_group, metric, mean, std, n_players, fetched_at

        This is the integration point between Python WAIMS and R-WAIMS:
        R-WAIMS (wehoop) can also write to this table for richer benchmarks.

        Args:
            benchmarks: DataFrame from get_positional_benchmarks()
            db_path:    Path to waims_demo.db

        Returns:
            True if successful, False otherwise
        """
        if benchmarks.empty:
            warnings.warn("No benchmark data to write.")
            return False

        try:
            conn = sqlite3.connect(db_path)
            # Replace existing benchmarks for this season
            benchmarks.to_sql(
                "wnba_benchmarks",
                conn,
                if_exists="replace",
                index=False,
            )
            conn.close()
            print(f"✓ Wrote {len(benchmarks)} benchmark rows to {db_path}")
            return True
        except Exception as e:
            warnings.warn(f"DB write failed: {e}")
            return False

    def write_game_log_to_db(
        self,
        game_log: pd.DataFrame,
        player_name: str,
        db_path: str = "waims_demo.db",
    ) -> bool:
        """
        Write player game log to WAIMS SQLite database.
        Enables dashboard to show game-day context alongside monitoring data.

        Creates/appends table: wnba_game_logs

        Args:
            game_log:    DataFrame from get_player_game_logs()
            player_name: Player display name (for joining with internal data)
            db_path:     Path to waims_demo.db
        """
        if game_log.empty:
            return False

        game_log = game_log.copy()
        game_log["player_name"] = player_name
        game_log["fetched_at"]  = datetime.utcnow().isoformat()

        try:
            conn = sqlite3.connect(db_path)
            game_log.to_sql("wnba_game_logs", conn, if_exists="replace", index=False)
            conn.close()
            print(f"✓ Wrote {len(game_log)} game log rows for {player_name}")
            return True
        except Exception as e:
            warnings.warn(f"Game log DB write failed: {e}")
            return False


# ==============================================================================
# CONVENIENCE FUNCTIONS (for direct use without class instantiation)
# ==============================================================================

def fetch_wings_benchmarks(
    season: str = "2025",
    db_path: str = "waims_demo.db",
    write_to_db: bool = True,
) -> pd.DataFrame:
    """
    One-call function: fetch WNBA positional benchmarks and optionally
    write to the WAIMS database.

    Usage:
        from wnba_api import fetch_wings_benchmarks
        benchmarks = fetch_wings_benchmarks(season="2025")

    Args:
        season:     WNBA season year
        db_path:    Path to waims_demo.db
        write_to_db: Whether to persist to SQLite

    Returns:
        DataFrame with positional benchmarks
    """
    if not NBA_API_AVAILABLE:
        print("nba_api not installed. Run: pip install nba_api")
        return pd.DataFrame()

    client = WNBAStatsClient()
    print(f"Fetching WNBA {season} positional benchmarks from stats.wnba.com...")
    benchmarks = client.get_positional_benchmarks(season=season)

    if benchmarks.empty:
        print("No benchmarks retrieved — check network and nba_api version.")
        return benchmarks

    print(f"  Retrieved benchmarks for {benchmarks['position_group'].nunique()} "
          f"position groups, {benchmarks['metric'].nunique()} metrics")

    if write_to_db:
        client.write_benchmarks_to_db(benchmarks, db_path=db_path)

    return benchmarks


def fetch_player_season_log(
    player_name: str,
    season: str = "2025",
    db_path: str = "waims_demo.db",
    write_to_db: bool = True,
) -> pd.DataFrame:
    """
    Fetch and optionally store game log for a named WNBA player.

    Usage:
        from wnba_api import fetch_player_season_log
        log = fetch_player_season_log("Paige Bueckers", season="2025")

    NOTE: player_name must match ESPN/NBA.com display name exactly.
    Use client.get_team_roster() to confirm names.
    """
    if not NBA_API_AVAILABLE:
        print("nba_api not installed. Run: pip install nba_api")
        return pd.DataFrame()

    client = WNBAStatsClient()

    # Get roster to find player_id
    roster = client.get_team_roster(season=season)
    if roster.empty:
        print(f"Could not fetch roster for {season} season.")
        return pd.DataFrame()

    # Match player name (case-insensitive, partial match)
    name_col = "player" if "player" in roster.columns else roster.columns[0]
    match = roster[roster[name_col].str.lower().str.contains(
        player_name.lower().split()[-1]  # Match on last name
    )]

    if match.empty:
        print(f"Player '{player_name}' not found in {season} Wings roster.")
        print(f"Available: {roster[name_col].tolist()}")
        return pd.DataFrame()

    player_id = match.iloc[0].get("player_id") or match.iloc[0].get("playerid")
    print(f"Fetching game log for {match.iloc[0][name_col]} (ID: {player_id})...")

    log = client.get_player_game_logs(player_id=player_id, season=season)
    log = client.calculate_game_load_proxy(log)

    if write_to_db and not log.empty:
        client.write_game_log_to_db(log, player_name=player_name, db_path=db_path)

    return log


# ==============================================================================
# DATA SOURCES REFERENCE
# ==============================================================================

DATA_SOURCES = {
    "stats.wnba.com (via nba_api)": {
        "available":    True,
        "what":         "Box scores, game logs, season averages, player/team info",
        "not_available": "GPS, distance, optical tracking, internal load",
        "reliability":  "High — official source, actively maintained",
        "cost":         "Free",
        "use_in_waims": "Positional benchmarks, game context, minute load proxy",
    },
    "wehoop (R package)": {
        "available":    True,
        "what":         "Same as stats.wnba.com + ESPN play-by-play",
        "not_available": "GPS, optical tracking",
        "reliability":  "Medium — ESPN endpoint can break without notice",
        "cost":         "Free",
        "use_in_waims": "R-WAIMS research layer, historical analysis",
    },
    "balldontlie.io": {
        "available":    True,
        "what":         "Clean REST API, box scores, player stats, real-time updates",
        "not_available": "Advanced tracking",
        "reliability":  "Medium — good free tier for quick lookups",
        "cost":         "Free tier / paid for historical depth",
        "use_in_waims": "Backup source, real-time game scores during season",
    },
    "Second Spectrum": {
        "available":    False,
        "what":         "TRUE game movement: distance, speed zones, acceleration, shot quality",
        "not_available": "N/A — provides everything",
        "reliability":  "Gold standard — WNBA league-wide optical tracking system",
        "cost":         "Team license — request from Wings front office",
        "use_in_waims": "PRIORITY upgrade — replaces all load proxies with real data",
    },
    "Sportradar": {
        "available":    False,
        "what":         "Official WNBA data provider, structured feeds, historical depth",
        "not_available": "Internal monitoring",
        "reliability":  "Commercial grade",
        "cost":         "Paid API",
        "use_in_waims": "Alternative to nba_api if team gets licensed access",
    },
    "Kinexon GPS (in-arena)": {
        "available":    False,
        "what":         "Real game GPS: player load, accel/decel, distance in games",
        "not_available": "N/A",
        "reliability":  "Industry standard for WNBA/NBA in-arena tracking",
        "cost":         "Hardware + license",
        "use_in_waims": "Ideal — would make game_load_proxy column real data",
    },
}


if __name__ == "__main__":
    print("WAIMS WNBA Stats API Module")
    print("=" * 50)
    print(f"nba_api available: {NBA_API_AVAILABLE}")
    print()
    print("Data Sources Available to WAIMS:")
    for source, info in DATA_SOURCES.items():
        status = "✅" if info["available"] else "🔒"
        print(f"  {status} {source}")
        print(f"     Provides: {info['what'][:70]}")
        print(f"     Cost: {info['cost']}")
        print()
    print("Quick start:")
    print("  from wnba_api import fetch_wings_benchmarks")
    print("  benchmarks = fetch_wings_benchmarks(season='2025')")
