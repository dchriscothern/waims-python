"""Bare-bones sanity-check viewer for parsed Arkansas game stats.

Not a dashboard tab -- just a console dump to confirm the box score parser
(scripts/parse_arkansas_box_scores.py) produced sane data before it gets
wired into a real player-profile view.

Usage:
    python scripts/view_arkansas_game_stats.py                 # all games
    python scripts/view_arkansas_game_stats.py --player ARK012 # one player's game log
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "waims-mens" / "data" / "waims_arkansas.db"

BOX_SCORE_COLUMNS = [
    ("player_number", "#"), ("player_name_matched", "Name"), ("min", "MIN"),
    ("fgm", "FGM"), ("fga", "FGA"), ("fg3m", "3PM"), ("fg3a", "3PA"),
    ("ftm", "FTM"), ("fta", "FTA"), ("reb", "REB"), ("ast", "AST"),
    ("tov", "TOV"), ("stl", "STL"), ("blk", "BLK"), ("pts", "PTS"),
]


def _print_table(rows: list[sqlite3.Row], columns: list[tuple[str, str]]) -> None:
    widths = [max(len(label), *(len(str(r[key]) if r[key] is not None else "-") for r in rows)) for key, label in columns]
    header = "  ".join(label.ljust(w) for (_, label), w in zip(columns, widths))
    print(header)
    print("-" * len(header))
    for r in rows:
        line = "  ".join(str(r[key] if r[key] is not None else "-").ljust(w) for (key, _), w in zip(columns, widths))
        print(line)


def show_all_games(conn: sqlite3.Connection) -> None:
    games = conn.execute(
        "SELECT game_id, date, opponent, final_score, result FROM game_results ORDER BY date"
    ).fetchall()
    for game in games:
        print(f"\n=== {game['date']} vs {game['opponent']} - Arkansas {game['final_score']} ({game['result']}) ===")
        rows = conn.execute(
            """
            SELECT * FROM player_game_stats
            WHERE game_id = ? AND team = 'ARK'
            ORDER BY pts DESC
            """,
            (game["game_id"],),
        ).fetchall()
        _print_table(rows, BOX_SCORE_COLUMNS)


def show_player(conn: sqlite3.Connection, player_id: str) -> None:
    rows = conn.execute(
        """
        SELECT g.date, g.opponent, s.*
        FROM player_game_stats s
        JOIN game_results g ON g.game_id = s.game_id
        WHERE s.player_id = ?
        ORDER BY g.date
        """,
        (player_id,),
    ).fetchall()
    if not rows:
        print(f"No game stats found for player_id={player_id}")
        return
    print(f"\n=== Game log: {rows[0]['player_name_matched']} ({player_id}) ===")
    columns = [("date", "Date"), ("opponent", "Opp")] + BOX_SCORE_COLUMNS[2:]
    _print_table(rows, columns)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--player", help="player_id, e.g. ARK012, to show a single player's game log")
    args = parser.parse_args()

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    if args.player:
        show_player(conn, args.player)
    else:
        show_all_games(conn)

    conn.close()


if __name__ == "__main__":
    main()
