"""Game Performance tab -- box scores, game logs, and shot detail.

Sourced from player_game_stats and play_by_play_events, both built by
scripts/parse_arkansas_box_scores.py and scripts/parse_arkansas_play_by_play.py
from the Baha Mar Hoops box score / play-by-play PDFs. Only populated for the
Arkansas (mens) database -- dashboard.py only mounts this tab when the active
sport is "mens".
"""

from __future__ import annotations

import re
import sqlite3

import pandas as pd
import streamlit as st

BOX_SCORE_DISPLAY_COLUMNS = {
    "player_number": "#",
    "player_name_matched": "Name",
    "min": "MIN",
    "fgm": "FGM", "fga": "FGA",
    "fg3m": "3PM", "fg3a": "3PA",
    "ftm": "FTM", "fta": "FTA",
    "oreb": "OREB", "dreb": "DREB", "reb": "REB",
    "ast": "AST", "tov": "TOV", "stl": "STL", "blk": "BLK",
    "pf": "PF", "pts": "PTS", "plus_minus": "+/-",
}

EVENT_TYPE_LABELS = {
    "fg_made": "FG Made", "fg_missed": "FG Missed",
    "ft_made": "FT Made", "ft_missed": "FT Missed",
    "rebound_offensive": "Off. Rebound", "rebound_defensive": "Def. Rebound",
    "turnover": "Turnover", "steal": "Steal", "assist": "Assist",
    "foul_personal": "Foul", "foul_drawn": "Foul Drawn", "block": "Block",
    "substitution_in": "Sub In", "substitution_out": "Sub Out",
    "timeout": "Timeout", "jumpball_won": "Jump Ball Won", "jumpball_lost": "Jump Ball Lost",
}

# Keyword tags pulled out of the raw OCR play-by-play text to describe a shot
# (zone, origin, subtype) without trying to fully re-space garbled OCR prose.
SHOT_TAGS = [
    ("3pt", "3PT"), ("2pt", "2PT"),
    ("inthepaint", "in the paint"), ("in the paint", "in the paint"),
    ("outsidethepaint", "outside the paint"), ("outside the paint", "outside the paint"),
    ("fastbreak", "fast break"), ("fast break", "fast break"),
    ("secondchance", "second chance"), ("second chance", "second chance"),
    ("fromturnover", "from turnover"), ("from turnover", "from turnover"),
    ("layup", "layup"), ("jumpshot", "jump shot"), ("jump shot", "jump shot"),
    ("dunk", "dunk"), ("hookshot", "hook shot"), ("hook shot", "hook shot"),
    ("tip-in", "tip-in"), ("floating", "floater"), ("blocked", "blocked"),
]


def _shot_description(raw_text: str) -> str:
    lower = (raw_text or "").lower()
    tags = []
    seen = set()
    for needle, label in SHOT_TAGS:
        if needle.replace(" ", "") in lower.replace(" ", "") and label not in seen:
            tags.append(label)
            seen.add(label)
    return ", ".join(tags) if tags else "-"


@st.cache_data(ttl=300)
def _load_tables(db_path: str) -> dict[str, pd.DataFrame]:
    conn = sqlite3.connect(db_path)
    try:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        if "player_game_stats" not in tables or "game_results" not in tables:
            return {}
        data = {
            "games": pd.read_sql_query("SELECT * FROM game_results ORDER BY date", conn),
            "box": pd.read_sql_query("SELECT * FROM player_game_stats", conn),
        }
        if "play_by_play_events" in tables:
            data["pbp"] = pd.read_sql_query("SELECT * FROM play_by_play_events", conn)
        else:
            data["pbp"] = pd.DataFrame()
        return data
    finally:
        conn.close()


def _game_label(row: pd.Series) -> str:
    return f"{row['date']} vs {row['opponent']} - Arkansas {row['final_score']} ({row['result']})"


def game_performance_tab(db_path, players: pd.DataFrame) -> None:
    data = _load_tables(str(db_path))
    if not data or data["games"].empty:
        st.info("No game performance data loaded yet. Run scripts/parse_arkansas_box_scores.py "
                "(and scripts/parse_arkansas_play_by_play.py for shot detail) to populate this tab.")
        return

    games, box, pbp = data["games"], data["box"], data["pbp"]

    wins = int((games["result"] == "W").sum())
    losses = int((games["result"] == "L").sum())
    ark_box = box[box["team"] == "ARK"]
    team_ppg = ark_box.groupby("game_id")["pts"].sum().mean()

    m1, m2, m3 = st.columns(3)
    m1.metric("Games Played", len(games))
    m2.metric("Record", f"{wins}-{losses}")
    m3.metric("Team PPG", f"{team_ppg:.1f}" if pd.notna(team_ppg) else "-")

    box_tab, log_tab, shot_tab = st.tabs(["Box Scores", "Player Game Log", "Shot Detail"])

    # ── Box Scores ──────────────────────────────────────────────────────────
    with box_tab:
        game_choice = st.selectbox(
            "Game", games.index, format_func=lambda i: _game_label(games.loc[i]), key="gp_box_game"
        )
        game_row = games.loc[game_choice]
        st.caption(f"Source: {game_row['source_pdf']}")

        for team_key, team_label in (("ARK", "Arkansas"), ("OPP", game_row["opponent"])):
            team_rows = box[(box["game_id"] == game_row["game_id"]) & (box["team"] == team_key)].copy()
            if team_rows.empty:
                continue
            team_rows = team_rows.sort_values("pts", ascending=False)
            display_col = "player_name_matched" if team_key == "ARK" else "player_name_raw"
            cols = {**BOX_SCORE_DISPLAY_COLUMNS, "player_name_raw": "Name"}
            show_cols = [c for c in cols if c in team_rows.columns and (c != "player_name_matched" or team_key == "ARK") and (c != "player_name_raw" or team_key == "OPP")]
            st.markdown(f"**{team_label}**")
            st.dataframe(
                team_rows[show_cols].rename(columns=cols),
                hide_index=True, width="stretch",
            )

    # ── Player Game Log ─────────────────────────────────────────────────────
    with log_tab:
        roster_names = sorted(ark_box["player_name_matched"].dropna().unique())
        if not roster_names:
            st.info("No Arkansas players matched to the roster yet.")
        else:
            player_choice = st.selectbox("Player", roster_names, key="gp_log_player")
            player_rows = ark_box[ark_box["player_name_matched"] == player_choice].merge(
                games[["game_id", "date", "opponent"]], on="game_id"
            ).sort_values("date")

            gp = len(player_rows)
            avg_cols = st.columns(6)
            avg_cols[0].metric("GP", gp)
            avg_cols[1].metric("PPG", f"{player_rows['pts'].mean():.1f}")
            avg_cols[2].metric("RPG", f"{player_rows['reb'].mean():.1f}")
            avg_cols[3].metric("APG", f"{player_rows['ast'].mean():.1f}")
            fga_sum, fgm_sum = player_rows["fga"].sum(), player_rows["fgm"].sum()
            avg_cols[4].metric("FG%", f"{(fgm_sum / fga_sum * 100):.1f}" if fga_sum else "-")
            fta_sum, ftm_sum = player_rows["fta"].sum(), player_rows["ftm"].sum()
            avg_cols[5].metric("FT%", f"{(ftm_sum / fta_sum * 100):.1f}" if fta_sum else "-")

            log_cols = {
                "date": "Date", "opponent": "Opp", "min": "MIN",
                "fgm": "FGM", "fga": "FGA", "fg3m": "3PM", "fg3a": "3PA",
                "ftm": "FTM", "fta": "FTA", "reb": "REB", "ast": "AST",
                "tov": "TOV", "stl": "STL", "blk": "BLK", "pts": "PTS",
            }
            st.dataframe(
                player_rows[list(log_cols)].rename(columns=log_cols),
                hide_index=True, width="stretch",
            )

    # ── Shot Detail ─────────────────────────────────────────────────────────
    with shot_tab:
        if pbp.empty:
            st.info("No play-by-play data loaded. Run scripts/parse_arkansas_play_by_play.py to populate shot detail.")
        else:
            game_choice2 = st.selectbox(
                "Game", games.index, format_func=lambda i: _game_label(games.loc[i]), key="gp_shot_game"
            )
            game_row2 = games.loc[game_choice2]
            game_events = pbp[(pbp["game_id"] == game_row2["game_id"]) & (pbp["team"] == "ARK")]

            shot_names = sorted(game_events["player_name_matched"].dropna().unique())
            player_filter = st.selectbox("Player (optional)", ["All"] + shot_names, key="gp_shot_player")

            shots = game_events[game_events["event_type"].isin(["fg_made", "fg_missed", "ft_made", "ft_missed"])].copy()
            if player_filter != "All":
                shots = shots[shots["player_name_matched"] == player_filter]
            shots = shots.sort_values(["half", "page_index"])

            if shots.empty:
                st.info("No shot events for this selection.")
            else:
                shots["Result"] = shots["event_type"].map(EVENT_TYPE_LABELS)
                shots["Description"] = shots["raw_text"].apply(_shot_description)
                shots["Player"] = shots["player_name_matched"].fillna(shots["player_number"].astype("Int64").astype(str))
                display = shots.rename(columns={"half": "Half", "game_time": "Clock", "points": "Pts", "score": "Score"})
                st.dataframe(
                    display[["Half", "Clock", "Player", "Result", "Description", "Pts", "Score"]],
                    hide_index=True, width="stretch",
                )

                made = shots[shots["event_type"].isin(["fg_made", "ft_made"])]
                attempted = shots[shots["event_type"].isin(["fg_made", "fg_missed", "ft_made", "ft_missed"])]
                st.caption(f"{len(made)} made / {len(attempted)} attempted in this view")
