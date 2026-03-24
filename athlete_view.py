from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components

from auth import current_athlete_player_id
from readiness_logic import calculate_readiness_score, readiness_bucket

HERE = Path(__file__).parent
DB_PATH = HERE / "waims_demo.db"

_REAL_NAME_MAP = {
    "P001": "Arike Ogunbowale",
    "P002": "Paige Bueckers",
    "P003": "NaLyssa Smith",
    "P004": "Teaira McCowan",
    "P005": "Myisha Hines-Allen",
    "P006": "Kaila Charles",
    "P007": "DiJonai Carrington",
    "P008": "Tyasha Harris",
    "P009": "Yueru Li",
    "P010": "Aziaha James",
    "P011": "Maddy Siegrist",
    "P012": "Luisa Geiselsoder",
}


def _athlete_answer(query: str, athlete: pd.Series, recent: pd.DataFrame, load7: float, today_load: float) -> tuple[str, str] | None:
    q = (query or "").strip().lower()
    if not q:
        return None

    readiness = calculate_readiness_score(athlete)
    status, _, _ = readiness_bucket(readiness)
    guidance = (
        "You look ready for normal training today."
        if readiness >= 80
        else "You may need a lighter day or some check-in support today."
        if readiness >= 60
        else "Check in with staff before full training today."
    )

    if any(text in q for text in ("how am i", "how am i doing", "today", "ready")):
        return "#1e3a5f", f"<b>Today:</b> {status} ({readiness:.0f}/100)<br>{guidance}"

    if "sleep" in q:
        avg_sleep = float(recent["sleep_hours"].mean()) if len(recent) else float(athlete.get("sleep_hours", 0.0))
        return "#1e3a5f", (
            f"<b>Sleep:</b> {float(athlete.get('sleep_hours', 0.0)):.1f} hours last night."
            f"<br>7-day average: {avg_sleep:.1f} hours."
        )

    if "sore" in q or "soreness" in q or "stress" in q:
        avg_sore = float(recent["soreness"].mean()) if len(recent) else float(athlete.get("soreness", 0.0))
        avg_stress = float(recent["stress"].mean()) if len(recent) else float(athlete.get("stress", 0.0))
        return "#d97706", (
            f"<b>Soreness:</b> {float(athlete.get('soreness', 0.0)):.0f}/10 today."
            f"<br><b>Stress:</b> {float(athlete.get('stress', 0.0)):.0f}/10 today."
            f"<br>7-day averages: soreness {avg_sore:.1f}/10, stress {avg_stress:.1f}/10."
        )

    if "load" in q or "workload" in q:
        return "#0f766e", (
            f"<b>Load this week:</b> {load7:.0f} AU over the last 7 days."
            f"<br><b>Today's load:</b> {today_load:.0f} AU."
        )

    if any(text in q for text in ("points", "assists", "rebounds", "stats", "game")):
        return "#7c3aed", (
            "<b>Game snapshot:</b> check the game stats cards below for your latest points, rebounds, assists, minutes, and eFG%."
        )

    if "didn't play" in q or "didnt play" in q or "did not play" in q:
        return "#d97706", (
            "<b>If you did not play:</b> keep some structured work in your week so return-to-play minutes "
            "do not become a sudden spike. Short sprint work, change-of-direction reps, or a controlled "
            "conditioning block can help maintain your load base."
        )

    return "#94a3b8", (
        'Try: <b>"How am I doing today?"</b> - <b>"How was my sleep?"</b> - '
        '<b>"How is my soreness this week?"</b> - <b>"What should I do if I did not play?"</b>'
    )


def _load_athlete_games(player_id: str, player_name: str) -> pd.DataFrame:
    if not DB_PATH.exists():
        return pd.DataFrame()
    try:
        conn = sqlite3.connect(str(DB_PATH))
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        if "game_box_scores" not in tables:
            conn.close()
            return pd.DataFrame()
        columns = {row[1] for row in conn.execute("PRAGMA table_info(game_box_scores)").fetchall()}
        select_cols = [col for col in ["date", "player_id", "player_name", "minutes", "pts", "reb", "ast", "stl", "blk", "plus_minus", "fgm", "fga", "fg3m"] if col in columns]
        if not select_cols:
            conn.close()
            return pd.DataFrame()
        sql = f"SELECT {', '.join(select_cols)} FROM game_box_scores"
        game_stats = pd.DataFrame()
        if "player_id" in columns and player_id:
            game_stats = pd.read_sql_query(sql + " WHERE player_id = ? ORDER BY date DESC", conn, params=[player_id])
        if len(game_stats) == 0 and "player_name" in columns and player_name:
            game_stats = pd.read_sql_query(sql + " WHERE player_name = ? ORDER BY date DESC", conn, params=[player_name])
        conn.close()
        if len(game_stats) == 0:
            return pd.DataFrame()
        game_stats["date"] = pd.to_datetime(game_stats["date"], errors="coerce")
        if all(col in game_stats.columns for col in ["fgm", "fg3m", "fga"]):
            fga = game_stats["fga"].replace(0, pd.NA)
            game_stats["efg_pct"] = ((game_stats["fgm"] + 0.5 * game_stats["fg3m"]) / fga * 100).round(1)
        return game_stats
    except Exception:
        return pd.DataFrame()


def _load_next_team_game(ref_date) -> pd.Series | None:
    if not DB_PATH.exists():
        return None
    try:
        conn = sqlite3.connect(str(DB_PATH))
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        if "schedule" not in tables:
            conn.close()
            return None
        schedule = pd.read_sql_query(
            "SELECT date, opponent, location, is_back_to_back, days_rest, travel_flag, venue FROM schedule ORDER BY date ASC",
            conn,
        )
        conn.close()
        if len(schedule) == 0:
            return None
        schedule["date"] = pd.to_datetime(schedule["date"], errors="coerce")
        next_games = schedule[schedule["date"] >= pd.Timestamp(ref_date)].sort_values("date")
        if len(next_games) == 0:
            return None
        return next_games.iloc[0]
    except Exception:
        return None


def _load_schedule_context(ref_date) -> dict:
    next_game = _load_next_team_game(ref_date)
    if next_game is None:
        return {"is_back_to_back": 0, "days_rest": 3}
    game_day = pd.to_datetime(next_game["date"])
    if game_day.date() == pd.Timestamp(ref_date).date():
        return {
            "is_back_to_back": int(next_game.get("is_back_to_back", 0) or 0),
            "days_rest": int(next_game.get("days_rest", 3) or 3),
        }
    return {"is_back_to_back": 0, "days_rest": max(int(next_game.get("days_rest", 3) or 3), 1)}


def _load_force_plate_context(player_id: str, ref_date) -> dict:
    if not DB_PATH.exists():
        return {"cmj_height_cm": None, "rsi_modified": None}
    try:
        conn = sqlite3.connect(str(DB_PATH))
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        if "force_plate" not in tables:
            conn.close()
            return {"cmj_height_cm": None, "rsi_modified": None}
        fp = pd.read_sql_query(
            "SELECT player_id, date, cmj_height_cm, rsi_modified FROM force_plate WHERE player_id = ? ORDER BY date DESC",
            conn,
            params=[player_id],
        )
        conn.close()
        if len(fp) == 0:
            return {"cmj_height_cm": None, "rsi_modified": None}
        fp["date"] = pd.to_datetime(fp["date"], errors="coerce")
        same_day = fp[fp["date"] == pd.Timestamp(ref_date)]
        row = same_day.iloc[0] if len(same_day) else fp.iloc[0]
        return {
            "cmj_height_cm": row.get("cmj_height_cm"),
            "rsi_modified": row.get("rsi_modified"),
        }
    except Exception:
        return {"cmj_height_cm": None, "rsi_modified": None}


def _format_stat_value(value, suffix: str = "", decimals: int = 0) -> str:
    if value is None or pd.isna(value):
        return "-"
    if decimals == 0:
        return f"{float(value):.0f}{suffix}"
    return f"{float(value):.{decimals}f}{suffix}"


def _render_stat_grid(title: str, cards: list[tuple[str, str, str]], accent: str) -> None:
    card_html = []
    for label, value, detail in cards:
        detail_html = f'<div style="font-size:11px;color:#64748b;margin-top:4px;">{detail}</div>' if detail else ""
        card_html.append(
            (
                f'<div style="background:#ffffff;border:1px solid #e2e8f0;border-top:3px solid {accent};'
                'border-radius:12px;padding:12px 14px;min-height:86px;">'
                f'<div style="font-size:10px;font-weight:700;letter-spacing:0.14em;text-transform:uppercase;color:#94a3b8;">{label}</div>'
                f'<div style="font-size:24px;font-weight:800;color:#0f172a;line-height:1.15;margin-top:6px;">{value}</div>'
                f'{detail_html}'
                '</div>'
            )
        )
    st.markdown(f"### {title}")
    st.markdown(
        (
            '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));'
            f'gap:12px;margin-bottom:12px;">{"".join(card_html)}</div>'
        ),
        unsafe_allow_html=True,
    )


def _rollup_stat(series: pd.Series) -> float | None:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    return float(clean.mean()) if len(clean) else None


def _truthy_flag(value) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _get_runtime_setting(*keys):
    for key in keys:
        env_value = os.getenv(key)
        if env_value not in (None, ""):
            return env_value
        try:
            if key in st.secrets:
                secret_value = st.secrets[key]
                if secret_value not in (None, ""):
                    return str(secret_value)
        except Exception:
            pass
    return ""


def _resolve_oura_status_label() -> tuple[str, str, str]:
    demo_flag = _truthy_flag(_get_runtime_setting("OURA_DEMO_MODE", "WAIMS_OURA_DEMO_MODE", "WAIMS_DEMO_MODE"))
    try:
        import oura_connector  # type: ignore
    except ImportError:
        return ("Demo mode", "Sample data", "#2563eb") if demo_flag else ("Not connected", "?", "#94a3b8")

    get_status = getattr(oura_connector, "get_oura_status", None)
    if callable(get_status):
        try:
            raw = get_status()
            if isinstance(raw, dict):
                if raw.get("error"):
                    return "Error", "?", "#d97706"
                if raw.get("demo_mode") is True:
                    return "Demo mode", "Sample data", "#2563eb"
                if raw.get("connected") is True:
                    sync = raw.get("last_sync") or raw.get("last_sync_at") or raw.get("synced_at") or raw.get("updated_at") or "Recent"
                    return "Active", str(sync), "#16a34a"
            elif isinstance(raw, str):
                lowered = raw.lower()
                if "demo" in lowered:
                    return "Demo mode", "Sample data", "#2563eb"
                if "active" in lowered or "connected" in lowered:
                    return "Active", "Recent", "#16a34a"
        except Exception:
            return "Error", "?", "#d97706"

    return ("Demo mode", "Sample data", "#2563eb") if demo_flag else ("Not connected", "?", "#94a3b8")


def _render_wearable_recovery_panel() -> None:
    status_text, sync_text, accent = _resolve_oura_status_label()
    if status_text == "Active":
        body = "Oura recovery data is connected. Sleep and recovery signals can support your daily readiness view."
    elif status_text == "Demo mode":
        body = "Wearable recovery is shown in demo mode. This space is reserved for sleep, HRV, resting HR, and readiness when a device is connected."
    elif status_text == "Error":
        body = "Wearable recovery data is currently unavailable because the connector needs attention."
    else:
        body = "No wearable connected yet. Oura or WHOOP can be added later to bring sleep and recovery signals into this view."

    st.markdown(
        f'<div style="background:#f8fafc;border-left:4px solid {accent};border-radius:0 8px 8px 0;padding:12px 16px;margin:14px 0 14px 0;">'
        f'<div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-start;">'
        f'<div>'
        f'<div style="font-size:12px;font-weight:700;color:#0f172a;margin-bottom:6px;">Wearable Recovery</div>'
        f'<div style="font-size:13px;color:#334155;line-height:1.6;">{body}</div>'
        f'</div>'
        f'<div style="text-align:right;white-space:nowrap;">'
        f'<div style="font-size:12px;font-weight:700;color:{accent};">{status_text}</div>'
        f'<div style="font-size:11px;color:#94a3b8;margin-top:4px;">{sync_text}</div>'
        f'</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _render_info_panel(title: str, body: str, accent: str) -> None:
    st.markdown(
        f'<div style="background:#f8fafc;border-left:4px solid {accent};border-radius:0 8px 8px 0;padding:12px 16px;margin-bottom:14px;">'
        f'<div style="font-size:12px;font-weight:700;color:#0f172a;margin-bottom:6px;">{title}</div>'
        f'<div style="font-size:13px;color:#334155;line-height:1.6;">{body}</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def _render_compact_context_card(title: str, line_one: str, line_two: str) -> None:
    st.markdown(
        '<div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:10px;'
        'padding:12px 14px;min-height:92px;">'
        f'<div style="font-size:11px;font-weight:700;letter-spacing:0.14em;'
        f'text-transform:uppercase;color:#94a3b8;margin-bottom:8px;">{title}</div>'
        f'<div style="font-size:13px;color:#0f172a;line-height:1.45;">{line_one}</div>'
        f'<div style="font-size:12px;color:#64748b;line-height:1.45;margin-top:4px;">{line_two}</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def athlete_home_view(wellness_df: pd.DataFrame, players_df: pd.DataFrame, training_load_df: pd.DataFrame, end_date) -> None:
    athlete_pid = current_athlete_player_id()
    if not athlete_pid:
        st.error("Athlete profile not connected to this login.")
        return

    today = wellness_df[wellness_df["date"] == pd.to_datetime(end_date)].copy()
    today = today.merge(players_df[["player_id", "name", "position"]], on="player_id", how="left")
    player_today = today[today["player_id"].astype(str) == str(athlete_pid)]
    if player_today.empty:
        st.error("Athlete profile not found for this login.")
        return

    athlete = player_today.iloc[0].copy()
    athlete.update(_load_force_plate_context(str(athlete_pid), end_date))
    athlete.update(_load_schedule_context(end_date))
    readiness = calculate_readiness_score(athlete)
    status, status_color, status_bg = readiness_bucket(readiness)
    guidance = (
        "You look ready for normal training today."
        if readiness >= 80
        else "You may need a lighter day or some check-in support today."
        if readiness >= 60
        else "You should check in with staff before full training today."
    )

    recent = wellness_df[wellness_df["player_id"].astype(str) == str(athlete_pid)].sort_values("date").tail(7)
    recent_load = training_load_df[
        (training_load_df["player_id"].astype(str) == str(athlete_pid)) &
        (pd.to_datetime(training_load_df["date"]) > pd.Timestamp(end_date) - pd.Timedelta(days=7))
    ].copy()
    load7 = float(recent_load["player_load"].sum()) if len(recent_load) and "player_load" in recent_load.columns else 0.0
    today_rows = recent_load[pd.to_datetime(recent_load["date"]) == pd.Timestamp(end_date)] if len(recent_load) else pd.DataFrame()
    today_load = float(today_rows["player_load"].sum()) if len(today_rows) and "player_load" in today_rows.columns else 0.0

    athlete_name = str(athlete.get("name", "")).strip()
    mapped_real_name = _REAL_NAME_MAP.get(str(athlete_pid), athlete_name)
    athlete_games = _load_athlete_games(str(athlete_pid), mapped_real_name)
    latest_game = athlete_games.iloc[0] if len(athlete_games) else None
    last_five_games = athlete_games.head(5) if len(athlete_games) else pd.DataFrame()
    next_game = _load_next_team_game(end_date)

    st.markdown(
        '<div style="background:#e0f2fe;border-radius:10px;padding:14px 18px;font-size:14px;color:#0f4c81;margin-bottom:18px;">'
        '<b>Athlete View</b> - This page shows only your own readiness, trends, and recovery guidance.</div>',
        unsafe_allow_html=True,
    )
    st.markdown("## My Readiness")
    st.caption("Your athlete view shows only your own data. No teammate information appears here.")

    top_left, top_right = st.columns([1.05, 1.35], gap="large")
    with top_left:
        st.markdown(
            f'<div style="background:{status_bg};border-left:4px solid {status_color};border-radius:0 10px 10px 0;padding:14px 16px;">'
            f'<div style="font-size:11px;font-weight:700;letter-spacing:0.18em;color:{status_color};text-transform:uppercase;margin-bottom:8px;">Today</div>'
            f'<div style="font-size:22px;font-weight:800;color:#0f172a;margin-bottom:8px;">{status} - {readiness:.0f}/100</div>'
            f'<div style="font-size:13px;color:#334155;line-height:1.5;">{guidance}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with top_right:
        metric_cols = st.columns(3)
        metric_cols[0].metric("Sleep", f"{float(athlete.get('sleep_hours', 0.0)):.1f} hrs")
        metric_cols[1].metric("Soreness", f"{float(athlete.get('soreness', 0.0)):.0f}/10")
        metric_cols[2].metric("Stress", f"{float(athlete.get('stress', 0.0)):.0f}/10")

    practice_minutes = float(recent_load["practice_minutes"].fillna(0).sum()) if len(recent_load) and "practice_minutes" in recent_load.columns else 0.0
    game_minutes = float(recent_load["game_minutes"].fillna(0).sum()) if len(recent_load) and "game_minutes" in recent_load.columns else 0.0
    sleep_last = float(athlete.get("sleep_hours", 0.0) or 0.0)
    soreness_today = float(athlete.get("soreness", 0.0) or 0.0)
    stress_today = float(athlete.get("stress", 0.0) or 0.0)
    did_not_play_recently = game_minutes < 5 and practice_minutes > 0
    avg_sleep = float(recent["sleep_hours"].mean()) if len(recent) else float(athlete.get("sleep_hours", 0.0))
    avg_sore = float(recent["soreness"].mean()) if len(recent) else float(athlete.get("soreness", 0.0))

    if next_game is not None:
        next_game_line_one = f"{pd.to_datetime(next_game['date']).strftime('%b %d')} vs {next_game.get('opponent', 'TBD')}"
        trip_note = "Travel" if int(next_game.get("travel_flag", 0) or 0) == 1 else "No travel"
        if str(next_game.get("location", "")).strip():
            trip_note = "Travel" if int(next_game.get("travel_flag", 0) or 0) == 1 else str(next_game.get("location", "")).strip()
        next_game_line_two = f"{int(next_game.get('days_rest', 0) or 0)} days rest · {trip_note}"
    else:
        next_game_line_one = "No game scheduled"
        next_game_line_two = "Schedule not available"

    context_cols = st.columns(3)
    with context_cols[0]:
        _render_compact_context_card(
            "This Week",
            f"Avg sleep {avg_sleep:.1f} hrs",
            f"Soreness {avg_sore:.1f}/10",
        )
    with context_cols[1]:
        _render_compact_context_card(
            "Load",
            f"7-day: {load7:.0f} AU",
            f"Today's load: {today_load:.0f} AU",
        )
    with context_cols[2]:
        _render_compact_context_card(
            "Next Game",
            next_game_line_one,
            next_game_line_two,
        )

    plan_text = (
        "Full practice and normal court work are appropriate today."
        if readiness >= 80
        else "Normal practice is possible, but pay attention to leg feel and ask for a lighter modification if needed."
        if readiness >= 60
        else "Use a modified day and check in with staff before full-speed work."
    )
    if sleep_last < 7:
        plan_text = "Keep practice focused and efficient today. Short sleep means the goal is quality work, not extra volume."
    elif soreness_today >= 7 or stress_today >= 7:
        plan_text = "Use a lighter day or modified volume today. Check in early if your legs or energy do not feel right."
    elif did_not_play_recently:
        plan_text = "If you did not get game minutes recently, keep some structured work in the plan so your load base stays ready."

    recovery_text = (
        "Priority today: sleep, hydration, and normal recovery routine."
        if readiness >= 80
        else "Priority today: hydration, recovery lift or regen, and soreness check-in."
        if readiness >= 60
        else "Priority today: treatment, recovery work, and a lower-load option."
    )
    if next_game is not None and int(next_game.get("is_back_to_back", 0) or 0) == 1:
        recovery_text = "Priority today: hydration, sleep, and recovery work because the next game is part of a back-to-back."
    elif int(next_game.get("travel_flag", 0) or 0) == 1 if next_game is not None else False:
        recovery_text = "Priority today: hydration, sleep timing, and recovery because travel is part of the next game block."
    _render_info_panel("Today Plan", f"{plan_text}<br>{recovery_text}", status_color)

    if latest_game is not None and len(athlete_games):
        latest_pts = float(latest_game.get("pts", 0) or 0)
        latest_reb = float(latest_game.get("reb", 0) or 0)
        latest_ast = float(latest_game.get("ast", 0) or 0)
        latest_min = float(latest_game.get("minutes", 0) or 0)
        _render_info_panel(
            "Last Game vs Season Average",
            f"PTS {latest_pts:.0f} vs {_format_stat_value(_rollup_stat(athlete_games['pts']), decimals=1)} average. "
            f"REB {latest_reb:.0f} vs {_format_stat_value(_rollup_stat(athlete_games['reb']), decimals=1)}. "
            f"AST {latest_ast:.0f} vs {_format_stat_value(_rollup_stat(athlete_games['ast']), decimals=1)}. "
            f"MIN {latest_min:.0f} vs {_format_stat_value(_rollup_stat(athlete_games['minutes']), decimals=1)}.",
            "#7c3aed",
        )

    checklist_items = []
    if sleep_last < 7:
        checklist_items.append("Protect your sleep tonight and keep caffeine later in the day under control")
    if soreness_today >= 7:
        checklist_items.append("Tell staff early if leg soreness stays high in warmup")
    if stress_today >= 7:
        checklist_items.append("Keep recovery simple today: breathe, hydrate, and use the lower-noise option after practice")
    if did_not_play_recently:
        checklist_items.append("Add a short conditioning or sprint block so your load does not drop too low")
    if next_game is not None and int(next_game.get("is_back_to_back", 0) or 0) == 1:
        checklist_items.append("Prioritize hydration and recovery tonight because the next game is a back-to-back")
    if next_game is not None and int(next_game.get("travel_flag", 0) or 0) == 1:
        checklist_items.append("Travel is coming up, so hydration and sleep timing matter more than usual")
    if not checklist_items:
        if readiness >= 80:
            checklist_items = [
                "Hydrate and fuel as normal",
                "Normal lift / court session",
                "Standard post-practice recovery",
            ]
        elif readiness >= 60:
            checklist_items = [
                "Hydrate and check in before practice",
                "Reduce unnecessary extra volume",
                "Recovery lift or regen after court work",
            ]
        else:
            checklist_items = [
                "Check in with staff before full-speed work",
                "Prioritize treatment and recovery",
                "Use the lower-load option today",
            ]
    checklist_html = "".join(f"<div>- {item}</div>" for item in checklist_items)
    _render_info_panel("Recovery Checklist", checklist_html, "#0f766e")

    _render_wearable_recovery_panel()

    st.markdown('<div style="font-size:11px;font-weight:700;letter-spacing:0.18em;text-transform:uppercase;color:#94a3b8;margin:18px 0 8px;">Ask a Question</div>', unsafe_allow_html=True)
    components.html(
        """
        <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
          <button id="athMicBtn" onclick="toggleAthleteVoice()" style="background:#0f766e;color:white;border:none;border-radius:8px;padding:8px 16px;font-size:13px;font-weight:700;cursor:pointer;">Ask</button>
          <span id="athMicStatus" style="font-size:11px;color:#64748b;"></span>
          <span style="font-size:11px;color:#94a3b8;font-style:italic;">Voice Preview - Chrome only - Tap Ask, speak, then tap again to stop</span>
        </div>
        <script>
        let recognizing = false;
        let recognition;
        function runAthleteQuickAction(text) {
          const clean = (text || '').trim();
          if (!clean) { return; }
          document.getElementById('athMicStatus').textContent = 'Running your question now...';
          document.getElementById('athMicStatus').style.color = '#0f766e';
          const normalized = clean.toLowerCase();
          let buttonLabel = 'How Am I Doing?';
          if (normalized.includes('sleep')) {
            buttonLabel = 'Sleep';
          } else if (normalized.includes('sore') || normalized.includes('soreness') || normalized.includes('stress')) {
            buttonLabel = 'Soreness & Stress';
          } else if (normalized.includes("didn't play") || normalized.includes('didnt play') || normalized.includes('did not play')) {
            buttonLabel = "Didn't Play";
          } else if (normalized.includes('points') || normalized.includes('assists') || normalized.includes('rebounds') || normalized.includes('stats') || normalized.includes('game')) {
            buttonLabel = 'Game Stats';
          }
          try {
            const parentDoc = window.parent.document;
            const buttons = Array.from(parentDoc.querySelectorAll('button'));
            const quickButton = buttons.find((btn) => (btn.textContent || '').trim() === buttonLabel);
            if (quickButton) {
              setTimeout(() => quickButton.click(), 150);
            } else {
              document.getElementById('athMicStatus').textContent = 'Voice heard you, but the athlete action button was not found.';
              document.getElementById('athMicStatus').style.color = '#d97706';
            }
          } catch (err) {
            document.getElementById('athMicStatus').textContent = 'Voice heard you, but the page could not run the athlete action.';
            document.getElementById('athMicStatus').style.color = '#d97706';
          }
        }
        function toggleAthleteVoice() {
          if (!(("webkitSpeechRecognition" in window) || ("SpeechRecognition" in window))) {
            document.getElementById('athMicStatus').textContent = 'Voice questions work in Chrome or Edge.';
            document.getElementById('athMicStatus').style.color = '#d97706';
            return;
          }
          if (recognizing) { recognition.stop(); return; }
          const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
          recognition = new SR();
          recognition.lang = 'en-US';
          recognition.interimResults = false;
          recognition.maxAlternatives = 1;
          recognition.onstart = function() {
            recognizing = true;
            document.getElementById('athMicBtn').style.background = '#dc2626';
            document.getElementById('athMicBtn').innerHTML = 'Tap To Stop';
            document.getElementById('athMicStatus').textContent = 'Listening now - say your question, then tap again to stop.';
          };
          recognition.onresult = function(event) { runAthleteQuickAction(event.results[0][0].transcript); };
          recognition.onerror = function() {
            document.getElementById('athMicStatus').textContent = 'Mic blocked in Chrome - allow microphone access, or use one of the quick options below.';
            document.getElementById('athMicStatus').style.color = '#d97706';
          };
          recognition.onend = function() {
            recognizing = false;
            document.getElementById('athMicBtn').style.background = '#0f766e';
            document.getElementById('athMicBtn').innerHTML = 'Ask';
          };
          recognition.start();
        }
        </script>
        """,
        height=56,
    )

    q1, q2, q3, q4, q5 = st.columns(5)
    with q1:
        if st.button("How Am I Doing?", width='stretch', key="ath_q_today"):
            st.session_state["athlete_query_to_run"] = "how am i doing today"
            st.rerun()
    with q2:
        if st.button("Sleep", width='stretch', key="ath_q_sleep"):
            st.session_state["athlete_query_to_run"] = "sleep"
            st.rerun()
    with q3:
        if st.button("Soreness & Stress", width='stretch', key="ath_q_sore"):
            st.session_state["athlete_query_to_run"] = "soreness and stress"
            st.rerun()
    with q4:
        if st.button("Didn't Play", width='stretch', key="ath_q_dnp"):
            st.session_state["athlete_query_to_run"] = "did not play"
            st.rerun()
    with q5:
        if st.button("Game Stats", width='stretch', key="ath_q_game"):
            st.session_state["athlete_query_to_run"] = "game stats"
            st.rerun()

    effective_query = (st.session_state.pop("athlete_query_to_run", "") or st.session_state.get("_athlete_active_query", "")).strip()
    if effective_query:
        st.session_state["_athlete_active_query"] = effective_query
    athlete_answer = _athlete_answer(effective_query, athlete, recent, load7, today_load)
    if athlete_answer:
        border_color, answer_html = athlete_answer
        st.markdown(f'<div style="background:#f8fafc;border-left:4px solid {border_color};border-radius:0 8px 8px 0;padding:12px 16px;font-size:13px;color:#0f172a;margin-top:8px;margin-bottom:16px;line-height:1.6;">{answer_html}</div>', unsafe_allow_html=True)

    if latest_game is not None:
        efg_val = latest_game.get('efg_pct')
        game_cards = [
            ("PTS", _format_stat_value(latest_game.get("pts", 0)), "Latest game"),
            ("REB", _format_stat_value(latest_game.get("reb", 0)), "Latest game"),
            ("AST", _format_stat_value(latest_game.get("ast", 0)), "Latest game"),
            ("MIN", _format_stat_value(latest_game.get("minutes", 0)), "Latest game"),
            ("eFG%", _format_stat_value(efg_val, "%", decimals=1), "Latest game"),
        ]
        if pd.notna(latest_game.get('date')):
            game_date_detail = pd.to_datetime(latest_game["date"]).strftime("%b %d, %Y")
            game_cards[-1] = ("eFG%", _format_stat_value(efg_val, "%", decimals=1), game_date_detail)
    else:
        game_cards = [
            ("PTS", "-", "Latest game"),
            ("REB", "-", "Latest game"),
            ("AST", "-", "Latest game"),
            ("MIN", "-", "Latest game"),
            ("eFG%", "-", "Latest game"),
        ]

    st.markdown(
        '<div style="font-size:11px;font-weight:700;letter-spacing:0.18em;text-transform:uppercase;color:#94a3b8;margin:18px 0 8px;">More Detail</div>',
        unsafe_allow_html=True,
    )
    detail_view = st.selectbox(
        "Detail view",
        ["Recovery Trends", "Game Snapshot", "Last 5 Games", "Load Snapshot"],
        index=0,
        key="athlete_detail_view",
        label_visibility="collapsed",
    )

    if detail_view == "Game Snapshot":
        _render_stat_grid("Game Snapshot", game_cards, "#7c3aed")
        if latest_game is None:
            st.caption("Game stats will appear here when box-score data is available for your player.")
    elif detail_view == "Last 5 Games":
        if latest_game is None or not len(last_five_games):
            st.caption("Recent game averages will appear here once box-score data is available.")
        else:
            _render_stat_grid(
                "Last 5 Games",
                [
                    ("PTS AVG", _format_stat_value(_rollup_stat(last_five_games["pts"]), decimals=1), "Rolling average"),
                    ("REB AVG", _format_stat_value(_rollup_stat(last_five_games["reb"]), decimals=1), "Rolling average"),
                    ("AST AVG", _format_stat_value(_rollup_stat(last_five_games["ast"]), decimals=1), "Rolling average"),
                    ("MIN AVG", _format_stat_value(_rollup_stat(last_five_games["minutes"]), decimals=1), "Rolling average"),
                ],
                "#2563eb",
            )
    elif detail_view == "Load Snapshot":
        _render_stat_grid(
            "Load Snapshot",
            [
                ("7-Day Load", _format_stat_value(load7, " AU"), "Last 7 days"),
                ("Today's Load", _format_stat_value(today_load, " AU"), "Today"),
                ("Practice Min", _format_stat_value(practice_minutes), "Last 7 days"),
                ("Game Min", _format_stat_value(game_minutes), "Last 7 days"),
            ],
            "#0f766e",
        )
    else:
        if len(recent):
            trend_cols = st.columns(2)
            trend_frame = recent.copy()
            trend_frame["date"] = pd.to_datetime(trend_frame["date"])
            with trend_cols[0]:
                st.markdown("### Sleep Trend")
                sleep_fig = px.line(trend_frame, x="date", y="sleep_hours", markers=True)
                sleep_fig.update_layout(height=260, margin=dict(l=10, r=10, t=10, b=10), xaxis_title="", yaxis_title="Hours")
                st.plotly_chart(sleep_fig, width='stretch')
            with trend_cols[1]:
                st.markdown("### Soreness & Stress")
                stress_fig = px.line(trend_frame, x="date", y=["soreness", "stress"], markers=True)
                stress_fig.update_layout(height=260, margin=dict(l=10, r=10, t=10, b=10), xaxis_title="", yaxis_title="Score")
                st.plotly_chart(stress_fig, width='stretch')
        else:
            st.caption("Recovery trends will appear here when the last 7 days of athlete data are available.")
