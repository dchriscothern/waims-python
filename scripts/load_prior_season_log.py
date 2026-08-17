"""Load a player's prior-season game log (from a clean CSV, e.g. pulled from
ESPN's gamelog page) into waims_arkansas.db.

Unlike the Baha Mar box scores, this data doesn't need OCR -- it's already
structured. This script just validates and loads it, tagged by player_id and
season so multiple players/seasons can accumulate here over time.

Usage:
    python scripts/load_prior_season_log.py --player-id ARK013 --season 2025-26 \
        --source espn --csv waims-mens/data/prior_seasons/richmond_billy_iii_2025_26.csv
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "waims-mens" / "data" / "waims_arkansas.db"

sys.path.insert(0, str(ROOT / "waims-mens"))
from roster_arkansas import ARKANSAS_ROSTER_2026

REQUIRED_COLUMNS = [
    "date", "opponent", "home_or_away", "result", "min",
    "fgm", "fga", "fg3m", "fg3a", "ftm", "fta",
    "reb", "ast", "stl", "blk", "tov", "pts",
]


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS player_prior_season_games (
            player_id TEXT,
            season TEXT,
            source TEXT,
            date TEXT,
            opponent TEXT,
            home_or_away TEXT,
            result TEXT,
            min INTEGER,
            fgm INTEGER, fga INTEGER,
            fg3m INTEGER, fg3a INTEGER,
            ftm INTEGER, fta INTEGER,
            reb INTEGER, ast INTEGER, stl INTEGER, blk INTEGER, tov INTEGER,
            pts INTEGER,
            PRIMARY KEY (player_id, season, date)
        )
        """
    )


def load_csv(player_id: str, season: str, source: str, csv_path: Path) -> int:
    if player_id not in {p["player_id"] for p in ARKANSAS_ROSTER_2026}:
        raise ValueError(f"{player_id} is not on the current roster (roster_arkansas.py)")

    df = pd.read_csv(csv_path)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"CSV missing required columns: {missing}")

    conn = sqlite3.connect(str(DB_PATH))
    _ensure_schema(conn)
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM player_prior_season_games WHERE player_id = ? AND season = ?",
        (player_id, season),
    )
    for _, row in df.iterrows():
        cur.execute(
            """
            INSERT INTO player_prior_season_games (
                player_id, season, source, date, opponent, home_or_away, result,
                min, fgm, fga, fg3m, fg3a, ftm, fta, reb, ast, stl, blk, tov, pts
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                player_id, season, source, row["date"], row["opponent"], row["home_or_away"],
                row["result"], row["min"], row["fgm"], row["fga"], row["fg3m"], row["fg3a"],
                row["ftm"], row["fta"], row["reb"], row["ast"], row["stl"], row["blk"],
                row["tov"], row["pts"],
            ),
        )
    conn.commit()
    n = len(df)
    conn.close()
    return n


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--player-id", required=True, help="e.g. ARK013")
    parser.add_argument("--season", required=True, help="e.g. 2025-26")
    parser.add_argument("--source", default="espn")
    parser.add_argument("--csv", required=True, type=Path)
    args = parser.parse_args()

    n = load_csv(args.player_id, args.season, args.source, args.csv)
    print(f"Loaded {n} games for {args.player_id}, season {args.season}, source {args.source}")


if __name__ == "__main__":
    main()
