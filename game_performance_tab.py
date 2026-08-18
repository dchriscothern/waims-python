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

from game_analytics import (
    assist_creation,
    lineup_stints,
    lineup_summary,
    points_by_situation,
    shot_efficiency_by_type,
    team_pace,
    team_possessions_and_ppp,
    traditional_plus_stats,
    turnover_breakdown,
)

MIN_GAMES_FOR_CORRELATION = 20

ROADMAP_METRICS = [
    ("Offensive Gravity", "Needs optical player/ball tracking (defender X/Y/Z position at every moment) -- not extractable from a box score or play-by-play log."),
    ("Expected Shot Quality (qSQ) / EPV", "Needs precise shot-location coordinates and defender distance at release, not just paint/perimeter tags."),
    ("Potential / Secondary Assists", "Needs every pass tracked, not just the ones that led to a made shot -- our play-by-play only logs actual assists on makes."),
    ("Play-type efficiency (PnR, isolation, post-up, spot-up)", "This is Synergy Sports-style video-charted data. Hand-chartable from film (see the manual-tracking guide) -- not derivable from this data source."),
    ("Composite value metrics (BPM/RAPTOR/EPM-style single-number rating)", "A different kind of blocker than the rest of this list: these are regression models calibrated against thousands of player-seasons league-wide, not something more Arkansas games alone can produce -- needs a much larger reference dataset, not just more depth on this one team."),
]

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
        data["starters"] = (
            pd.read_sql_query("SELECT * FROM period_starters", conn)
            if "period_starters" in tables else pd.DataFrame()
        )
        data["prior_seasons"] = (
            pd.read_sql_query("SELECT * FROM player_prior_season_games", conn)
            if "player_prior_season_games" in tables else pd.DataFrame()
        )
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

    games, box, pbp, starters = data["games"], data["box"], data["pbp"], data["starters"]
    prior_seasons = data["prior_seasons"]

    wins = int((games["result"] == "W").sum())
    losses = int((games["result"] == "L").sum())
    ark_box = box[box["team"] == "ARK"]
    team_ppg = ark_box.groupby("game_id")["pts"].sum().mean()

    m1, m2, m3 = st.columns(3)
    m1.metric("Games Played", len(games))
    m2.metric("Record", f"{wins}-{losses}")
    m3.metric("Team PPG", f"{team_ppg:.1f}" if pd.notna(team_ppg) else "-")

    box_tab, log_tab, shot_tab, adv_tab = st.tabs(
        ["Box Scores", "Player Game Log", "Shot Detail", "Advanced Metrics"]
    )

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

            player_id = ark_box.loc[ark_box["player_name_matched"] == player_choice, "player_id"].iloc[0]
            player_prior = prior_seasons[prior_seasons["player_id"] == player_id]
            if not player_prior.empty:
                for season, season_rows in player_prior.groupby("season"):
                    season_rows = season_rows.sort_values("date")
                    source = season_rows["source"].iloc[0]
                    st.markdown(f"**{season} Season (Full Year) -- source: {source}**")
                    p_gp = len(season_rows)
                    p_cols = st.columns(6)
                    p_cols[0].metric("GP", p_gp)
                    p_cols[1].metric("PPG", f"{season_rows['pts'].mean():.1f}")
                    p_cols[2].metric("RPG", f"{season_rows['reb'].mean():.1f}")
                    p_cols[3].metric("APG", f"{season_rows['ast'].mean():.1f}")
                    p_fga, p_fgm = season_rows["fga"].sum(), season_rows["fgm"].sum()
                    p_cols[4].metric("FG%", f"{(p_fgm / p_fga * 100):.1f}" if p_fga else "-")
                    p_fta, p_ftm = season_rows["fta"].sum(), season_rows["ftm"].sum()
                    p_cols[5].metric("FT%", f"{(p_ftm / p_fta * 100):.1f}" if p_fta else "-")

                    prior_log_cols = {
                        "date": "Date", "opponent": "Opp", "home_or_away": "H/A", "result": "Result",
                        "min": "MIN", "fgm": "FGM", "fga": "FGA", "fg3m": "3PM", "fg3a": "3PA",
                        "ftm": "FTM", "fta": "FTA", "reb": "REB", "ast": "AST",
                        "tov": "TOV", "stl": "STL", "blk": "BLK", "pts": "PTS",
                    }
                    st.dataframe(
                        season_rows[list(prior_log_cols)].rename(columns=prior_log_cols),
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

    # ── Advanced Metrics ────────────────────────────────────────────────────
    with adv_tab:
        if pbp.empty:
            st.info("No play-by-play data loaded. Run scripts/parse_arkansas_play_by_play.py to populate advanced metrics.")
        else:
            st.caption(
                "Built from the possession-level play-by-play, not just box score totals. "
                "Everything below is exact from the parsed events -- shot type/zone splits, assist "
                "points created, and lineup net rating are all directly computable, with one caveat: "
                "defensive impact beyond steals/blocks/rebounds and offensive action-type taxonomy "
                "(pick-and-roll, iso, post-up) require charting game film and aren't in this data."
            )

            st.markdown("**Team efficiency (points per possession)**")
            ppp = team_possessions_and_ppp(box)
            ppp_display = ppp.merge(games[["game_id", "date", "opponent"]], on="game_id")
            ppp_display["Team"] = ppp_display.apply(
                lambda r: "Arkansas" if r["team"] == "ARK" else r["opponent"], axis=1
            )
            ppp_cols = {"date": "Date", "opponent": "Opp", "Team": "Team", "possessions": "Poss", "pts": "PTS", "ppp": "PPP"}
            st.dataframe(
                ppp_display.sort_values(["date", "team"])[list(ppp_cols)].rename(columns=ppp_cols),
                hide_index=True, width="stretch",
            )

            st.markdown("**Traditional-plus rate stats (per player, averaged across all games)**")
            st.caption(
                "eFG%, TS%, Usage%, and AST/TO -- standard formulas from box score totals. These are "
                "descriptive (what actually happened), not inferential, so they're valid at any game "
                "count -- unlike the correlation view further down, which needs many more games."
            )
            tps = traditional_plus_stats(box[box["team"] == "ARK"])
            if not tps.empty:
                tps_summary = tps.groupby("player_name_matched", as_index=False).agg(
                    gp=("game_id", "count"), min=("min", "mean"),
                    efg_pct=("efg_pct", "mean"), ts_pct=("ts_pct", "mean"),
                    usg_pct=("usg_pct", "mean"), ast_to_ratio=("ast_to_ratio", "mean"),
                )
                for c in ("min", "efg_pct", "ts_pct", "usg_pct", "ast_to_ratio"):
                    tps_summary[c] = tps_summary[c].round(1)
                st.dataframe(
                    tps_summary.rename(columns={
                        "player_name_matched": "Player", "gp": "GP", "min": "MIN",
                        "efg_pct": "eFG%", "ts_pct": "TS%", "usg_pct": "USG%", "ast_to_ratio": "AST/TO",
                    }).sort_values("USG%", ascending=False),
                    hide_index=True, width="stretch",
                )

            pace_col, situ_col = st.columns(2)
            with pace_col:
                st.markdown("**Team pace (possessions / 40 min)**")
                pace_df = team_pace(box).merge(games[["game_id", "date", "opponent"]], on="game_id")
                st.dataframe(
                    pace_df[["date", "opponent", "pace"]].rename(
                        columns={"date": "Date", "opponent": "Opp", "pace": "Pace"}
                    ),
                    hide_index=True, width="stretch",
                )
            with situ_col:
                st.markdown("**Points by situation (Arkansas, all games)**")
                situ_df = points_by_situation(pbp)
                if not situ_df.empty:
                    situ_pivot = situ_df.pivot_table(
                        index="game_id", columns="origin", values="points", fill_value=0
                    ).reset_index().merge(games[["game_id", "date", "opponent"]], on="game_id")
                    situ_pivot = situ_pivot.drop(columns="game_id").rename(columns={"date": "Date", "opponent": "Opp"})
                    st.dataframe(situ_pivot, hide_index=True, width="stretch")

            st.markdown("**Shot efficiency by play type (Arkansas, all games)**")
            eff_scope = st.radio("Split by", ["Team-wide", "Per player"], horizontal=True, key="gp_adv_eff_scope")
            group_cols = ["player_name_matched"] if eff_scope == "Per player" else []
            eff = shot_efficiency_by_type(pbp[pbp["team"] == "ARK"], group_cols=group_cols)
            eff_cols = (["player_name_matched"] if group_cols else []) + [
                "origin", "attempts", "makes", "points", "pts_per_attempt", "fg_pct"
            ]
            rename_cols = {"player_name_matched": "Player", "origin": "Type", "attempts": "Att",
                           "makes": "Makes", "points": "Pts", "pts_per_attempt": "Pts/Att", "fg_pct": "FG%"}
            origin_df = eff["origin"]
            st.dataframe(
                origin_df[[c for c in eff_cols if c in origin_df.columns]].rename(columns=rename_cols),
                hide_index=True, width="stretch",
            )

            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**Assist creation (points created, all games)**")
                ac = assist_creation(pbp)
                st.dataframe(
                    ac.rename(columns={
                        "player_name_matched": "Player", "assists": "AST",
                        "points_created": "Pts Created", "points_per_assist": "Pts/AST",
                    }),
                    hide_index=True, width="stretch",
                )
            with col_b:
                st.markdown("**Turnover breakdown (all games)**")
                tb = turnover_breakdown(pbp)
                st.dataframe(
                    tb.rename(columns={"player_name_matched": "Player", "subtype": "Type", "count": "Count"}),
                    hide_index=True, width="stretch",
                )

            st.markdown("**Lineup net rating (5-man units, all games)**")
            st.caption(
                "Point margin while each 5-man Arkansas unit was on the floor, reconstructed from "
                "substitutions and the running score. Small sample per unit -- read as early signal."
            )
            if starters.empty:
                st.info("No period-starters data loaded; lineup net rating needs it to seed each half's unit.")
            else:
                stints = lineup_stints(pbp, starters)
                if stints.empty:
                    st.info("No lineup stints could be reconstructed for these games.")
                else:
                    summary = lineup_summary(stints)
                    st.dataframe(
                        summary[["lineup_label", "stints", "net_rating"]].rename(
                            columns={"lineup_label": "Lineup", "stints": "Stints", "net_rating": "Net Rating"}
                        ),
                        hide_index=True, width="stretch",
                    )

            st.markdown("---")
            st.markdown("#### Roadmap")

            st.markdown("**Unlocks automatically with more games**")
            n_games = len(games)
            games_pct = min(100, round(n_games / MIN_GAMES_FOR_CORRELATION * 100))
            st.markdown(
                '<div style="border-left:4px solid #94a3b8;padding:8px 14px;background:#f8fafc;">'
                f'<b>Expanded correlation / trend analysis:</b> needs roughly {MIN_GAMES_FOR_CORRELATION}+ real games '
                f'before it says anything reliable. Currently at <b>{n_games} of ~{MIN_GAMES_FOR_CORRELATION}</b>.'
                '</div>',
                unsafe_allow_html=True,
            )
            st.progress(games_pct / 100, text=f"{n_games} / ~{MIN_GAMES_FOR_CORRELATION} games")

            st.markdown("**Planned, pending a different data source**")
            st.caption(
                "These don't unlock with more Arkansas games -- each needs data this app doesn't "
                "ingest today (optical player tracking, hand-charted video, or a league-wide reference "
                "dataset). Listed here so it's a stated plan, not an unexplained gap."
            )
            for name, why in ROADMAP_METRICS:
                st.markdown(f"- **{name}** -- {why}")
