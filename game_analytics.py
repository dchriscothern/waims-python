"""Advanced game analytics built on top of the parsed box score and
play-by-play tables (player_game_stats, play_by_play_events, period_starters).

Everything here is computed directly from data already OCR'd and validated
in scripts/parse_arkansas_box_scores.py and parse_arkansas_play_by_play.py --
no new data collection. Two things this deliberately does NOT attempt,
because the source data can't support them without game film:
  - defensive impact beyond steals/blocks/rebounds (closeouts, help
    rotations, ball-screen navigation)
  - offensive action-type taxonomy (pick-and-roll, iso, post-up, spot-up)
Those require a human charting video, not a box score / play-by-play feed.
"""

from __future__ import annotations

import pandas as pd

SHOT_EVENT_TYPES = ("fg_made", "fg_missed")


# ── Team possessions & points-per-possession ────────────────────────────────

def team_possessions_and_ppp(box: pd.DataFrame) -> pd.DataFrame:
    """Standard possession estimate (FGA - OREB + TOV + 0.44*FTA), the same
    formula used by KenPom/basketball-reference. Requires only the box score.
    """
    team_totals = box.groupby(["game_id", "team", "team_name"], as_index=False).agg(
        fga=("fga", "sum"), oreb=("oreb", "sum"), tov=("tov", "sum"),
        fta=("fta", "sum"), pts=("pts", "sum"),
    )
    team_totals["possessions"] = (
        team_totals["fga"] - team_totals["oreb"] + team_totals["tov"] + 0.44 * team_totals["fta"]
    ).round(1)
    team_totals["ppp"] = (team_totals["pts"] / team_totals["possessions"]).round(3)
    return team_totals


# ── Shot efficiency by origin / zone ────────────────────────────────────────

def _shot_origin(raw_text: str) -> str:
    lower = (raw_text or "").lower().replace(" ", "")
    if "fastbreak" in lower:
        return "Transition"
    if "secondchance" in lower:
        return "Second Chance"
    if "fromturnover" in lower:
        return "Off Turnover"
    return "Half-Court"


def _shot_zone(raw_text: str) -> str:
    lower = (raw_text or "").lower().replace(" ", "")
    if "inthepaint" in lower:
        return "Paint"
    if "outsidethepaint" in lower or "3pt" in lower:
        return "Perimeter"
    return "Unspecified"


def shot_efficiency_by_type(pbp: pd.DataFrame, group_cols: list[str] | None = None) -> dict[str, pd.DataFrame]:
    """Points-per-shot-attempt split by origin (transition/half-court/off a
    turnover/second chance) and by zone (paint/perimeter). Each shot attempt
    (make or miss) carries these tags directly in its OCR'd description, so
    this is exact, not estimated -- but it's per-shot-attempt efficiency, not
    full possession accounting (a possession ending in a turnover has no
    shot attempt to tag).
    """
    shots = pbp[pbp["event_type"].isin(SHOT_EVENT_TYPES)].copy()
    if shots.empty:
        return {"origin": pd.DataFrame(), "zone": pd.DataFrame()}

    shots["origin"] = shots["raw_text"].apply(_shot_origin)
    shots["zone"] = shots["raw_text"].apply(_shot_zone)
    shots["made"] = (shots["event_type"] == "fg_made").astype(int)

    # None means "default to per-player"; an explicit [] means "team-wide,
    # no grouping" -- these need to stay distinct, so this can't just be
    # `group_cols or [...]` (an empty list is falsy too).
    group_cols = ["player_name_matched"] if group_cols is None else group_cols

    def _summarize(dim: str) -> pd.DataFrame:
        g = shots.groupby(group_cols + [dim], as_index=False).agg(
            attempts=("made", "count"), makes=("made", "sum"), points=("points", "sum"),
        )
        g["pts_per_attempt"] = (g["points"] / g["attempts"]).round(2)
        g["fg_pct"] = (g["makes"] / g["attempts"] * 100).round(1)
        return g.sort_values(group_cols + [dim])

    return {"origin": _summarize("origin"), "zone": _summarize("zone")}


# ── Assist creation & turnover quality ──────────────────────────────────────

def assist_creation(pbp: pd.DataFrame) -> pd.DataFrame:
    """Points created per assist: match each assist event to the made shot
    immediately preceding it (same team, same game clock -- how this report
    logs assists) and credit the assister with that shot's points. Only
    primary assists exist in this data; there's no secondary/"hockey assist"
    signal to extract.
    """
    rows = []
    for game_id, game_df in pbp.groupby("game_id"):
        game_df = game_df.sort_values("event_seq")
        by_seq = game_df.set_index("event_seq")
        for seq, row in by_seq.iterrows():
            if row["event_type"] != "assist" or row["team"] != "ARK":
                continue
            # Walk backward to the nearest preceding made shot by the same team
            # at the same game clock (assists are logged as the row right
            # after the make, same team, same "game_time").
            candidates = game_df[
                (game_df["event_seq"] < seq)
                & (game_df["team"] == "ARK")
                & (game_df["game_time"] == row["game_time"])
                & (game_df["event_type"] == "fg_made")
            ]
            shot_points = candidates.iloc[-1]["points"] if not candidates.empty else 0
            rows.append({
                "game_id": game_id,
                "player_id": row["player_id"],
                "player_name_matched": row["player_name_matched"],
                "points_created": shot_points,
            })

    if not rows:
        return pd.DataFrame(columns=["player_name_matched", "assists", "points_created"])
    df = pd.DataFrame(rows)
    summary = df.groupby("player_name_matched", as_index=False).agg(
        assists=("points_created", "count"), points_created=("points_created", "sum"),
    )
    summary["points_per_assist"] = (summary["points_created"] / summary["assists"]).round(2)
    return summary.sort_values("points_created", ascending=False)


TURNOVER_SUBTYPES = [
    ("badpass", "Bad Pass"), ("lostball", "Lost Ball"),
    ("offensive", "Offensive Foul"), ("outofbounds", "Out of Bounds"),
    ("travel", "Traveling"), ("doubledribble", "Double Dribble"),
    ("shotclock", "Shot Clock"), ("backcourt", "Backcourt"),
]


def turnover_breakdown(pbp: pd.DataFrame) -> pd.DataFrame:
    """Turnover subtype (bad pass / lost ball / offensive foul / etc.) per
    player, from the descriptor text already attached to each turnover event.
    """
    tos = pbp[(pbp["event_type"] == "turnover") & (pbp["team"] == "ARK")].copy()
    if tos.empty:
        return pd.DataFrame(columns=["player_name_matched", "subtype", "count"])

    def _subtype(raw_text: str) -> str:
        # OCR merges/spaces the descriptor inconsistently ("Lostball" vs
        # "Lost Ball"), so match on a normalized (lowercase, no-space) form
        # against known subtypes instead of trusting the regex capture verbatim.
        lower = (raw_text or "").lower().replace(" ", "")
        for needle, label in TURNOVER_SUBTYPES:
            if needle in lower:
                return label
        return "Other"

    tos["subtype"] = tos["raw_text"].apply(_subtype)
    return (
        tos.groupby(["player_name_matched", "subtype"], as_index=False)
        .size()
        .rename(columns={"size": "count"})
        .sort_values(["player_name_matched", "count"], ascending=[True, False])
    )


# ── Lineup stints & net rating ──────────────────────────────────────────────

def _forward_filled_diff(game_df: pd.DataFrame) -> pd.Series:
    """ARK-perspective score margin as of any event_seq, forward-filled from
    the last event that actually carried a score (most rows don't -- only
    scoring plays populate the Score/Diff columns).
    """
    diffs = game_df.set_index("event_seq")["diff"].apply(
        lambda d: None if pd.isna(d) or d == "" else int(d)
    )
    return diffs.reindex(range(int(diffs.index.min()), int(diffs.index.max()) + 1)).ffill().fillna(0)


def _player_label(matched, raw, number) -> str:
    if pd.notna(matched) and matched:
        return str(matched)
    if pd.notna(raw) and raw:
        return str(raw)
    return f"#{int(number)}" if pd.notna(number) else "Unknown"


def lineup_stints(pbp: pd.DataFrame, starters: pd.DataFrame) -> pd.DataFrame:
    """Reconstruct 5-man ARK lineups and the score margin while each was on
    the floor. A stint boundary is any substitution event; the net rating
    for a stint is the change in ARK's margin between the moment it starts
    and the moment it ends -- directly readable off the play-by-play's own
    running Score/Diff columns, no possession estimation needed.
    """
    stints = []

    for game_id, game_df in pbp.groupby("game_id"):
        game_df = game_df.sort_values("event_seq")
        diff_by_seq = _forward_filled_diff(game_df)

        for half in ("H1", "H2"):
            half_df = game_df[game_df["half"] == half]
            if half_df.empty:
                continue
            half_starters = starters[
                (starters["game_id"] == game_id) & (starters["half"] == half) & (starters["team"] == "ARK")
            ]
            lineup = {
                _player_label(row["player_name_matched"], row["player_name_raw"], row["player_number"])
                for _, row in half_starters.iterrows()
            }
            if not lineup:
                continue

            stint_start_seq = half_df["event_seq"].min()
            subs = half_df[
                (half_df["team"] == "ARK")
                & half_df["event_type"].isin(["substitution_in", "substitution_out"])
            ]

            for game_time, batch in subs.groupby("game_time", sort=False):
                batch = batch.sort_values("event_seq")
                change_seq = batch["event_seq"].iloc[0]
                if change_seq > stint_start_seq:
                    start_diff = diff_by_seq.get(stint_start_seq, 0)
                    end_diff = diff_by_seq.get(change_seq - 1, start_diff)
                    stints.append({
                        "game_id": game_id, "half": half,
                        "lineup": tuple(sorted(lineup)),
                        "start_seq": stint_start_seq, "end_seq": change_seq - 1,
                        "net_rating": end_diff - start_diff,
                    })
                for _, sub in batch.iterrows():
                    name = _player_label(sub["player_name_matched"], sub["player_name_raw"], sub["player_number"])
                    if sub["event_type"] == "substitution_out":
                        lineup.discard(name)
                    else:
                        lineup.add(name)
                stint_start_seq = change_seq

            end_seq = half_df["event_seq"].max()
            if end_seq >= stint_start_seq:
                start_diff = diff_by_seq.get(stint_start_seq, 0)
                end_diff = diff_by_seq.get(end_seq, start_diff)
                stints.append({
                    "game_id": game_id, "half": half,
                    "lineup": tuple(sorted(lineup)),
                    "start_seq": stint_start_seq, "end_seq": end_seq,
                    "net_rating": end_diff - start_diff,
                })

    return pd.DataFrame(stints)


def lineup_summary(stints: pd.DataFrame, min_stints: int = 1) -> pd.DataFrame:
    """Aggregate repeated 5-man combinations across games/halves."""
    if stints.empty:
        return pd.DataFrame(columns=["lineup", "stints", "net_rating"])
    summary = stints.groupby("lineup", as_index=False).agg(
        stints=("net_rating", "count"), net_rating=("net_rating", "sum"),
    )
    summary = summary[summary["stints"] >= min_stints]
    summary["lineup_label"] = summary["lineup"].apply(lambda l: ", ".join(l))
    return summary.sort_values("net_rating", ascending=False)


# ── Traditional-plus rate stats (descriptive, not inferential) ──────────────
#
# Everything below reports what actually happened -- shooting efficiency and
# usage rates computed from real box score totals -- as opposed to the
# correlation/trend-style stats elsewhere in this app that need many games
# before they mean anything. A rate stat over even 1 game is just an accurate
# fact about that game; it doesn't carry the same small-sample-size caveat.

def _parse_minutes(min_str) -> float:
    """'MM:SS' -> float minutes. Returns 0.0 for missing/unparseable values."""
    if not min_str or not isinstance(min_str, str) or ":" not in min_str:
        return 0.0
    try:
        m, s = min_str.split(":")
        return int(m) + int(s) / 60
    except ValueError:
        return 0.0


def traditional_plus_stats(box: pd.DataFrame) -> pd.DataFrame:
    """Per-player-per-game eFG%, TS%, Usage%, and AST/TO ratio -- standard
    formulas, computed entirely from box score totals already in this table.
    Usage% needs team totals for the same game, so it's computed per game_id.
    """
    rows = []
    for game_id, game_df in box.groupby("game_id"):
        for team, team_df in game_df.groupby("team"):
            team_min = team_df["min"].apply(_parse_minutes).sum()
            team_fga, team_fta, team_tov = team_df["fga"].sum(), team_df["fta"].sum(), team_df["tov"].sum()
            for _, p in team_df.iterrows():
                p_min = _parse_minutes(p["min"])
                efg = ((p["fgm"] + 0.5 * p["fg3m"]) / p["fga"] * 100) if p["fga"] else None
                ts_denom = 2 * (p["fga"] + 0.44 * p["fta"])
                ts = (p["pts"] / ts_denom * 100) if ts_denom else None
                usg = None
                team_poss_proxy = team_fga + 0.44 * team_fta + team_tov
                if p_min and team_min and team_poss_proxy:
                    usg = (
                        (p["fga"] + 0.44 * p["fta"] + p["tov"]) * (team_min / 5)
                        / (p_min * team_poss_proxy) * 100
                    )
                ast_to = (p["ast"] / p["tov"]) if p["tov"] else None
                rows.append({
                    "game_id": game_id, "team": team,
                    "player_id": p.get("player_id"), "player_name_matched": p.get("player_name_matched"),
                    "player_name_raw": p.get("player_name_raw"),
                    "min": round(p_min, 1),
                    "efg_pct": round(efg, 1) if efg is not None else None,
                    "ts_pct": round(ts, 1) if ts is not None else None,
                    "usg_pct": round(usg, 1) if usg is not None else None,
                    "ast_to_ratio": round(ast_to, 2) if ast_to is not None else None,
                })
    return pd.DataFrame(rows)


def team_pace(box: pd.DataFrame) -> pd.DataFrame:
    """Pace factor (possessions per 40 minutes) per game -- both teams'
    possession estimates averaged, per the standard KenPom-style formula.
    """
    poss = team_possessions_and_ppp(box)
    rows = []
    for game_id, game_df in poss.groupby("game_id"):
        if len(game_df) < 2:
            continue
        avg_poss = game_df["possessions"].mean()
        box_game = box[box["game_id"] == game_id]
        team_min = box_game[box_game["team"] == "ARK"]["min"].apply(_parse_minutes).sum()
        pace = (40 * avg_poss / (team_min / 5)) if team_min else None
        rows.append({"game_id": game_id, "pace": round(pace, 1) if pace is not None else None})
    return pd.DataFrame(rows)


def points_by_situation(pbp: pd.DataFrame) -> pd.DataFrame:
    """Points scored per game by situation (transition / second-chance / off
    a turnover / half-court), for Arkansas, using the same origin tags shot
    efficiency already relies on -- surfaced here as named team totals rather
    than per-shot efficiency.
    """
    shots = pbp[(pbp["team"] == "ARK") & (pbp["event_type"] == "fg_made")].copy()
    if shots.empty:
        return pd.DataFrame(columns=["game_id", "origin", "points"])
    shots["origin"] = shots["raw_text"].apply(_shot_origin)
    return (
        shots.groupby(["game_id", "origin"], as_index=False)["points"].sum()
        .sort_values(["game_id", "origin"])
    )
