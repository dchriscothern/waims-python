"""
WAIMS — Coach Command Center
30-second morning brief. Traffic lights, top alerts, GPS strip, forecast callout.
No clicks required. Links out to deep analyst tabs via st.session_state.
"""

import os
import pickle
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
from datetime import timedelta
from pathlib import Path

# Load readiness scorer trained model
# Falls back to formula if pkl not found (e.g. first run before train_models.py)
_SCORER_PATH = Path("models/readiness_scorer.pkl")
_READINESS_FN = None
if _SCORER_PATH.exists():
    try:
        with open(_SCORER_PATH, "rb") as _f:
            _scorer_data = pickle.load(_f)
            _READINESS_FN = _scorer_data.get("function")
    except Exception:
        _READINESS_FN = None


# ─────────────────────────────────────────────────────────────────────────────
# SHARED READINESS CALCULATOR
# Identical to athlete_profile_tab.py — single formula, both files self-contained.
# Uses pkl scorer when available, falls back to deterministic formula.
# ─────────────────────────────────────────────────────────────────────────────

def _calculate_readiness(row_dict):
    if _READINESS_FN is not None:
        try:
            return _READINESS_FN(row_dict)
        except Exception:
            pass
    sleep_hrs = row_dict.get("sleep_hours", 7.5)
    sleep_q   = row_dict.get("sleep_quality", 7)
    sleep_s   = min(15, (sleep_hrs / 8.0) * 10 + (sleep_q / 10) * 5)
    sore_s    = ((10 - row_dict.get("soreness", 4)) / 10) * 10
    mood_s    = (row_dict.get("mood", 7) / 10) * 5
    stress_s  = ((10 - row_dict.get("stress", 4)) / 10) * 5
    cmj       = row_dict.get("cmj_height_cm")
    pos       = str(row_dict.get("position", row_dict.get("pos", "F")))
    bench     = 38 if "G" in pos else (30 if "C" in pos else 34)
    cmj_s     = min(15, (cmj / bench) * 15) if cmj and cmj > 0 else 11
    rsi       = row_dict.get("rsi_modified")
    rsi_s     = min(10, (rsi / 0.45) * 10) if rsi and rsi > 0 else 8
    sched_s   = 10
    if row_dict.get("is_back_to_back", 0): sched_s -= 4
    if row_dict.get("days_rest", 3) <= 1:  sched_s -= 2
    sched_s   = max(0, sched_s)
    raw = sleep_s + sore_s + mood_s + stress_s + cmj_s + rsi_s + sched_s
    return round(min(100, raw * (100 / 70)), 1)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _zscore(val, series, min_std=0.1):
    s = series.dropna()
    if len(s) < 5:
        return 0.0
    return float((val - s.mean()) / max(s.std(), min_std))


def _readiness(row):
    """
    Uses trained readiness_scorer.pkl when available.
    Falls back to simplified formula if model not yet trained.
    The pkl version uses evidence-based weights from train_models.py:
    - Wellness 35pts, Force plate 25pts, Schedule 10pts, z-score modifier ±10pts
    - ACWR as contextual flag only (Impellizzeri 2020, 2025 meta-analysis)
    """
    if _READINESS_FN is not None:
        try:
            return _READINESS_FN(row)
        except Exception:
            pass
    # Fallback formula — mirrors train_models.py calculate_readiness_score weights
    # Sleep: 15pts | Soreness: 10pts | Mood: 5pts | Stress: 5pts = 35pts wellness
    # CMJ: 15pts | RSI: 10pts = 25pts force plate
    # Schedule: 10pts | z-modifier: ±5pts default neutral
    # Total possible: 100pts
    sleep_hrs = row.get("sleep_hours", 7.5)
    sleep_q   = row.get("sleep_quality", 7)
    sleep_s   = min(15, (sleep_hrs / 8.0) * 10 + (sleep_q / 10) * 5)
    sore_s    = ((10 - row.get("soreness", 4)) / 10) * 10
    mood_s    = (row.get("mood", 7)             / 10) * 5
    stress_s  = ((10 - row.get("stress", 4))    / 10) * 5

    cmj       = row.get("cmj_height_cm")
    pos       = str(row.get("position", row.get("pos", "F")))
    cmj_bench = 38 if "G" in pos else (30 if "C" in pos else 34)  # position-matched WNBA baseline
    cmj_s     = min(15, (cmj / cmj_bench) * 15) if cmj and cmj > 0 else 11
    rsi       = row.get("rsi_modified")
    rsi_s     = min(10, (rsi / 0.45) * 10) if rsi and rsi > 0 else 8  # neutral default ~0.36

    # Schedule context
    sched_s = 10
    if row.get("is_back_to_back", 0): sched_s -= 4
    if row.get("days_rest", 3) <= 1:  sched_s -= 2
    if row.get("travel_flag", 0):     sched_s -= min(3, abs(row.get("time_zone_diff", 0)) * 1.5)
    if row.get("unrivaled_flag", 0):  sched_s -= 2
    sched_s = max(0, sched_s)

    # Wellness(35) + Forceplate(25) + Schedule(10) = 70pts max in this fallback.
    # Full formula in train_models.py adds GPS(20pts) + z-modifier(10pts) = 100pts.
    # Rescale 70→100 so READY/MONITOR/PROTECT thresholds are correct.
    raw   = sleep_s + sore_s + mood_s + stress_s + cmj_s + rsi_s + sched_s
    total = raw * (100 / 70)
    return round(max(0, min(100, total)), 1)


def _traffic(score):
    if score >= 80: return "🟢", "#16a34a", "#dcfce7"
    if score >= 60: return "🟡", "#d97706", "#fef9c3"
    return "🔴", "#dc2626", "#fee2e2"


def _gps_flag(player_id, col, today_val, tl_df, ref_date):
    hist = tl_df[
        (tl_df["player_id"] == player_id) &
        (tl_df["date"] < ref_date) &
        (tl_df[col] > 0)
    ].tail(30)[col]
    if len(hist) < 5:
        return "🟡", None
    z = _zscore(today_val, hist)
    return ("🔴", z) if z <= -2 else (("🟡", z) if z <= -1 else ("🟢", z))


# ─────────────────────────────────────────────────────────────────────────────
# BUILD PLAYER SUMMARY TABLE
# ─────────────────────────────────────────────────────────────────────────────

def _build_summary(wellness, players, force_plate, training_load, end_date, ml_predictions=None):
    ref = pd.Timestamp(end_date)
    rows = []

    for _, p in players.iterrows():
        pid = p["player_id"]

        # ── Wellness ──────────────────────────────────────────────────────────
        w_today = wellness[(wellness["player_id"] == pid) & (pd.to_datetime(wellness["date"]) == pd.Timestamp(ref))]
        if len(w_today) == 0:
            continue
        w = w_today.iloc[0]
        score = _readiness(w)
        emoji, color, bg = _traffic(score)

        # ── CMJ z-score ───────────────────────────────────────────────────────
        fp_today = force_plate[(force_plate["player_id"] == pid) & (pd.to_datetime(force_plate["date"]) == pd.Timestamp(ref))]
        cmj_flag = "—"
        if len(fp_today) > 0:
            cmj_val = fp_today.iloc[0]["cmj_height_cm"]
            hist_cmj = force_plate[
                (force_plate["player_id"] == pid) & (pd.to_datetime(force_plate["date"]) < pd.Timestamp(ref))
            ].tail(30)["cmj_height_cm"]
            z = _zscore(cmj_val, hist_cmj, min_std=0.5)
            cmj_flag = "🔴" if z <= -2 else ("🟡" if z <= -1 else "🟢")

        # ── GPS flags ─────────────────────────────────────────────────────────
        has_gps = "player_load" in training_load.columns
        pl_flag = ac_flag = "—"
        if has_gps:
            gps_today = training_load[
                (training_load["player_id"] == pid) & (training_load["date"] == ref)
            ]
            if len(gps_today) > 0:
                g = gps_today.iloc[0]
                pl_flag, _ = _gps_flag(pid, "player_load", g["player_load"], training_load, ref)
                ac_flag, _ = _gps_flag(pid, "accel_count", g["accel_count"], training_load, ref)

        # Coach-language reason lines — decision-ready, no raw numbers
        # Priority: safety signals first, then performance signals
        flags = []
        if w["sleep_hours"] < 6.0:    flags.append("Poor sleep — recovery compromised")
        elif w["sleep_hours"] < 7.0:  flags.append("Short sleep last night")
        if w["soreness"] >= 9:        flags.append("Body very sore — protect today")
        elif w["soreness"] >= 7:      flags.append("High soreness reported")
        if w["stress"] >= 9:          flags.append("High stress — limit demands")
        elif w["stress"] >= 7:        flags.append("Elevated stress reported")
        if cmj_flag == "🔴":          flags.append("Power output down — legs not ready")
        if ac_flag  == "🔴":          flags.append("Movement quality reduced")
        if pl_flag  == "🔴":          flags.append("Below normal physical output")
        if w["mood"] <= 3:            flags.append("Low mood — check in before session")
        elif w["mood"] <= 4:          flags.append("Low mood today")
        reason = " · ".join(flags[:2]) if flags else "Cleared for full training"

        # Injury risk from ML model — loaded from processed_data.csv
        inj_risk = None
        if ml_predictions is not None and len(ml_predictions) > 0:
            _risk_row = ml_predictions[
                (ml_predictions["player_id"] == pid) &
                (pd.to_datetime(ml_predictions["date"]) == pd.Timestamp(ref))
            ]
            if len(_risk_row) > 0:
                inj_risk = round(float(_risk_row.iloc[0]["injury_risk_score"]) * 100, 0)

        # ── Cumulative minutes — 4-day and 8-day rolling ────────────────────
        # Per Orlando Magic sport science: coaches think in minutes, not scores.
        # "Minutes played in last 4 or 8 days — that's how coaches live."
        # (NBA practitioner interview, 2024)
        mins_4d = mins_8d = None
        if "practice_minutes" in training_load.columns:
            tl_hist = training_load[
                (training_load["player_id"] == pid) &
                (pd.to_datetime(training_load["date"]) > pd.Timestamp(ref) - pd.Timedelta(days=8)) &
                (pd.to_datetime(training_load["date"]) <= pd.Timestamp(ref))
            ].copy()
            if len(tl_hist) > 0:
                tl_hist["total_min"] = (
                    tl_hist.get("game_minutes", pd.Series([0]*len(tl_hist))).fillna(0) +
                    tl_hist.get("practice_minutes", pd.Series([0]*len(tl_hist))).fillna(0)
                )
                last4 = tl_hist[pd.to_datetime(tl_hist["date"]) > pd.Timestamp(ref) - pd.Timedelta(days=4)]
                mins_4d = round(last4["total_min"].sum(), 0) if len(last4) > 0 else 0
                mins_8d = round(tl_hist["total_min"].sum(), 0)

        rows.append({
            "pid":      pid,
            "name":     p["name"],
            "pos":      p.get("position", ""),
            "score":    score,
            "emoji":    emoji,
            "color":    color,
            "bg":       bg,
            "sleep":    w["sleep_hours"],
            "soreness": w["soreness"],
            "mood":     w["mood"],
            "stress":   w.get("stress", 0),
            "cmj":      cmj_flag,
            "load":     pl_flag,
            "accel":    ac_flag,
            "reason":   reason,
            "inj_risk": inj_risk,
            "mins_4d":  mins_4d,
            "mins_8d":  mins_8d,
        })


    return sorted(rows, key=lambda r: r["score"])


# ─────────────────────────────────────────────────────────────────────────────
# ALERT GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

def _top_alerts(summary_rows, acwr_df, end_date, n=3):
    alerts = []
    ref = pd.Timestamp(end_date)
    latest_acwr = acwr_df[acwr_df["date"] == ref] if len(acwr_df) > 0 else pd.DataFrame()

    for r in summary_rows:
        pid = r["pid"]

        if r["score"] < 60:
            # Build a coach-readable why from the same reason logic
            why_parts = []
            if r["sleep"] < 6.0:   why_parts.append("didn't sleep well")
            elif r["sleep"] < 7.0: why_parts.append("short sleep")
            if r["soreness"] >= 9: why_parts.append("body very sore")
            elif r["soreness"] >= 7: why_parts.append("high soreness")
            if r["stress"] >= 7:   why_parts.append("high stress")
            why = " and ".join(why_parts[:2]) if why_parts else "multiple signals flagged"
            alerts.append({
                "level":  "🔴 CRITICAL",
                "name":   r["name"],
                "msg":    f"Not ready — {why}",
                "action": "Modified session only — no contact, no max effort",
            })
        elif r["score"] < 75 and r["soreness"] >= 7:
            alerts.append({
                "level":  "🟡 MONITOR",
                "name":   r["name"],
                "msg":    "Body load is high — watch movement quality in warmup",
                "action": "Reduce contact and high-speed running today",
            })

        if not latest_acwr.empty:
            a = latest_acwr[latest_acwr["player_id"] == pid]
            if len(a) > 0 and a.iloc[0]["acwr"] > 1.5:
                alerts.append({
                    "level":  "🟡 WORKLOAD",
                    "name":   r["name"],
                    "msg":    "Training load has spiked this week relative to recent baseline",
                    "action": "Cap volume today — full intensity, shorter duration",
                })

        if r["cmj"] == "🔴":
            alerts.append({
                "level":  "🔴 NEURO",
                "name":   r["name"],
                "msg":    "Legs not responding — jump power significantly below her normal",
                "action": "No sprinting or jumping today — active recovery only",
            })

        if r["accel"] == "🔴":
            alerts.append({
                "level":  "🟡 GPS",
                "name":   r["name"],
                "msg":    "Moving protectively — avoiding explosive cuts and changes of direction",
                "action": "Watch warmup closely — may need to pull from drills",
            })

    # Deduplicate by name, keep highest severity
    seen = {}
    for a in alerts:
        key = a["name"]
        if key not in seen:
            seen[key] = a
        elif a["level"].startswith("🔴") and seen[key]["level"].startswith("🟡"):
            seen[key] = a

    return list(seen.values())[:n]


# ─────────────────────────────────────────────────────────────────────────────
# GPS SUMMARY STRIP
# ─────────────────────────────────────────────────────────────────────────────

def _schedule_context(end_date, db_path="waims_demo.db"):
    """Return today's game/practice context string for header."""
    import sqlite3
    try:
        conn = sqlite3.connect(db_path)
        import pandas as _pd
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        if "schedule" not in tables:
            conn.close()
            return "Practice Day"
        sched = _pd.read_sql_query(
            "SELECT * FROM schedule WHERE date = ?",
            conn, params=[str(end_date)]
        )
        conn.close()
        if sched.empty:
            return "Practice Day"
        row = sched.iloc[0]
        opp  = row.get("opponent", "")
        loc  = row.get("location", "home")
        b2b  = row.get("is_back_to_back", 0)
        rest = row.get("days_rest", 3)
        fiba = row.get("fiba_break", 0)
        if fiba:
            return "FIBA Break"
        if opp and str(opp).strip():
            home_away = "vs" if str(loc).lower() == "home" else "@"
            context = f"Game Day — {home_away} {opp}"
            if b2b:
                context += "  ·  Back-to-Back"
            elif int(rest) <= 1:
                context += f"  ·  {rest}d rest"
            return context
        return "Practice Day"
    except Exception:
        return "Practice Day"


def _gps_strip(training_load, players, end_date):
    ref = pd.Timestamp(end_date)
    if "player_load" not in training_load.columns:
        return None

    today_gps = training_load[training_load["date"] == ref].merge(
        players[["player_id", "name"]], on="player_id", how="left"
    )
    if len(today_gps) == 0:
        return None

    team_avg_load = today_gps["player_load"].mean()
    team_avg_acc  = today_gps["accel_count"].mean()
    high_load     = today_gps[today_gps["player_load"] > today_gps["player_load"].quantile(0.75)]
    low_acc       = today_gps[today_gps["accel_count"] < today_gps["accel_count"].quantile(0.25)]

    return {
        "team_avg_load": round(team_avg_load, 1),
        "team_avg_acc":  round(team_avg_acc, 1),
        "high_load_names": ", ".join(high_load["name"].tolist()),
        "low_acc_names":   ", ".join(low_acc["name"].tolist()),
        "n_players":       len(today_gps),
    }


# ─────────────────────────────────────────────────────────────────────────────
# MINI SPARKLINE
# ─────────────────────────────────────────────────────────────────────────────

def _sparkline(values, color="#2E86AB"):
    fig = go.Figure(go.Scatter(
        y=values, mode="lines",
        line=dict(color=color, width=2),
        fill="tozeroy", fillcolor=f"rgba(46,134,171,0.08)",
    ))
    fig.update_layout(
        height=50, margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# MAIN RENDER
# ─────────────────────────────────────────────────────────────────────────────

def coach_command_center(wellness, players, force_plate, training_load, acwr, end_date, ml_predictions=None):

    summary         = _build_summary(wellness, players, force_plate, training_load, end_date, ml_predictions=ml_predictions)
    alerts          = _top_alerts(summary, acwr, end_date)
    gps             = _gps_strip(training_load, players, end_date)
    game_context    = _schedule_context(end_date)
    ref             = pd.Timestamp(end_date)

    # ── HEADER: date + game/practice context + traffic light counts ───────────
    n_green  = sum(1 for r in summary if r["score"] >= 80)
    n_yellow = sum(1 for r in summary if 60 <= r["score"] < 80)
    n_red    = sum(1 for r in summary if r["score"] < 60)

    # Game context badge color
    ctx_is_game = "Game Day" in game_context
    ctx_color   = "#f59e0b" if ctx_is_game else "#64748b"
    ctx_bg      = "rgba(245,158,11,0.12)" if ctx_is_game else "rgba(100,116,139,0.10)"

    # Build header HTML as a plain string — avoids f-string + rgba() conflicts
    # that cause Streamlit to render raw HTML instead of rendering it
    date_str   = end_date.strftime("%A, %B %d")
    header_html = (
        '<div style="background:linear-gradient(135deg,#0f172a 0%,#1e293b 60%,#0f3460 100%);'
        'border-radius:14px;padding:22px 28px 18px;margin-bottom:18px;'
        'border:1px solid rgba(255,255,255,0.07);">'
        '<div style="display:flex;align-items:center;justify-content:space-between;'
        'flex-wrap:wrap;gap:12px;">'

        # Left — date, title, context badge
        '<div>'
        f'<div style="font-size:11px;font-weight:600;letter-spacing:0.22em;'
        f'text-transform:uppercase;color:#94a3b8;margin-bottom:4px;">{date_str}</div>'
        '<div style="font-size:22px;font-weight:700;color:#f8fafc;'
        'letter-spacing:-0.01em;margin-bottom:6px;">Command Center</div>'
        f'<div style="display:inline-block;font-size:12px;font-weight:600;'
        f'color:{ctx_color};background:{ctx_bg};'
        f'border-radius:6px;padding:3px 10px;letter-spacing:0.04em;">{game_context}</div>'
        '</div>'

        # Right — traffic light counts
        '<div style="display:flex;gap:24px;align-items:center;">'

        f'<div style="text-align:center;">'
        f'<div style="font-size:30px;font-weight:800;color:#4ade80;'
        f'font-family:monospace;line-height:1;">{n_green}</div>'
        '<div style="font-size:10px;color:#86efac;letter-spacing:0.1em;'
        'font-weight:700;margin-top:2px;">READY</div>'
        '</div>'

        f'<div style="text-align:center;">'
        f'<div style="font-size:30px;font-weight:800;color:#fbbf24;'
        f'font-family:monospace;line-height:1;">{n_yellow}</div>'
        '<div style="font-size:10px;color:#fde68a;letter-spacing:0.1em;'
        'font-weight:700;margin-top:2px;">MONITOR</div>'
        '</div>'

        f'<div style="text-align:center;">'
        f'<div style="font-size:30px;font-weight:800;color:#f87171;'
        f'font-family:monospace;line-height:1;">{n_red}</div>'
        '<div style="font-size:10px;color:#fca5a5;letter-spacing:0.1em;'
        'font-weight:700;margin-top:2px;">PROTECT</div>'
        '</div>'

        '</div>'  # end right
        '</div>'  # end flex row
        '</div>'  # end outer div
    )
    st.markdown(header_html, unsafe_allow_html=True)

    # ── SINCE LAST SESSION — always exactly 3 bullets ───────────────────────
    # Framework: 3 fixed questions a coach needs answered every morning:
    #   1. WHO needs a conversation before practice? (availability / protect)
    #   2. WHAT changed overnight? (biggest wellness movement)
    #   3. WHAT do I do differently today? (load watch / injury risk)
    # If no issue exists for a slot, show a positive confirmation — silence is
    # ambiguous; a green light is actionable. (Kitman Labs design principle)
    yesterday = ref - pd.Timedelta(days=1)
    w_today_all = wellness[pd.to_datetime(wellness["date"]) == pd.Timestamp(ref)]
    w_yest      = wellness[pd.to_datetime(wellness["date"]) == pd.Timestamp(yesterday)]

    # ── BULLET 1: WHO needs a conversation (protect + watch) ─────────────────
    protect_list  = [r["name"] for r in summary if r["score"] < 60]
    watch_list    = [r["name"] for r in summary if r.get("inj_risk") and r["inj_risk"] >= 60
                     and r["score"] >= 60]  # already in protect if score<60
    if protect_list and watch_list:
        b1 = (f"<b>Check in before practice:</b> {', '.join(protect_list[:2])} on protect — "
              f"modified session only. {', '.join(watch_list[:2])} on injury watch — limit "
              f"max-effort reps.")
        b1_color = "#dc2626"
    elif protect_list:
        names = ', '.join(protect_list[:3])
        b1 = (f"<b>{len(protect_list)} player{'s' if len(protect_list)>1 else ''} on protect "
              f"today:</b> {names} — modified session, flag for medical if pain >7/10.")
        b1_color = "#dc2626"
    elif watch_list:
        names = ', '.join(watch_list[:3])
        b1 = (f"<b>Injury watch this week:</b> {names} — clear for today but limit "
              f"max-effort reps and monitor warmup quality closely.")
        b1_color = "#d97706"
    else:
        ready_count = len([r for r in summary if r["score"] >= 80])
        b1 = (f"<b>Full squad available today.</b> {ready_count} players fully ready, "
              f"no protect or injury watch flags.")
        b1_color = "#16a34a"

    # ── BULLET 2: WHAT changed overnight (biggest single movement) ───────────
    b2 = None
    b2_color = "#475569"
    if len(w_yest) > 0:
        merged = pd.merge(
            w_today_all[["player_id","sleep_hours","soreness","stress","mood"]],
            w_yest[["player_id","sleep_hours","soreness","stress","mood"]],
            on="player_id", suffixes=("_t","_y")
        )
        # Score biggest overnight readiness drop
        biggest_drop = None
        biggest_drop_name = ""
        biggest_drop_reason = ""
        for _, mr in merged.iterrows():
            pname_r = players[players["player_id"] == mr["player_id"]]["name"].values
            pname_r = pname_r[0] if len(pname_r)>0 else "Unknown"
            # find corresponding summary score
            today_s = next((r["score"] for r in summary if r["pid"]==mr["player_id"]), None)
            yest_row = dict(mr)
            yest_row_calc = {
                "sleep_hours": mr["sleep_hours_y"], "soreness": mr["soreness_y"],
                "stress": mr["stress_y"], "mood": mr["mood_y"],
                "position": players[players["player_id"]==mr["player_id"]]["position"].values[0]
                             if len(players[players["player_id"]==mr["player_id"]])>0 else "F"
            }
            yest_score = _calculate_readiness(yest_row_calc)
            if today_s is not None:
                drop = yest_score - today_s
                if biggest_drop is None or drop > biggest_drop:
                    biggest_drop = drop
                    biggest_drop_name = pname_r
                    # identify the signal that drove it
                    sore_change = mr["soreness_t"] - mr["soreness_y"]
                    sleep_change = mr["sleep_hours_y"] - mr["sleep_hours_t"]
                    stress_change = mr["stress_t"] - mr["stress_y"]
                    if sleep_change > 0.8:
                        biggest_drop_reason = f"sleep dropped {sleep_change:.1f}h overnight"
                    elif sore_change >= 2:
                        biggest_drop_reason = f"soreness up {sore_change:.0f} points overnight"
                    elif stress_change >= 2:
                        biggest_drop_reason = f"stress up {stress_change:.0f} points overnight"
                    else:
                        biggest_drop_reason = "multiple wellness signals declined"

        if biggest_drop and biggest_drop > 5:
            b2 = (f"<b>Biggest overnight drop:</b> {biggest_drop_name} "
                  f"({biggest_drop:.0f}% readiness decline) — {biggest_drop_reason}. "
                  f"Check in individually before session starts.")
            b2_color = "#d97706"

        # If no significant drops, show biggest improver as positive signal
        if b2 is None:
            b2 = "<b>Stable overnight.</b> No significant readiness drops across the squad — wellness consistent with yesterday."
            b2_color = "#16a34a"
    else:
        b2 = "<b>No yesterday data</b> — first session of tracking period."
        b2_color = "#64748b"

    # ── BULLET 3: WHAT to do differently (load context) ──────────────────────
    high_load_players = []
    if "practice_minutes" in training_load.columns:
        for r in summary:
            mins4 = r.get("mins_4d")
            if mins4 and mins4 > 120:
                high_load_players.append((r["name"], int(mins4)))
    monitor_count = len([r for r in summary if 60 <= r["score"] < 80])

    if high_load_players:
        names_load = ", ".join(f"{n} ({m} min)" for n,m in high_load_players[:2])
        b3 = (f"<b>High cumulative load:</b> {names_load} in last 4 days — "
              f"consider shortened practice or lighter intensity today regardless of readiness score.")
        b3_color = "#d97706"
    elif monitor_count >= 4:
        b3 = (f"<b>{monitor_count} players on MONITOR today</b> — consider reducing "
              f"total session volume by 10–15%. Focus on skill quality over conditioning load.")
        b3_color = "#d97706"
    else:
        ready_pct = round(len([r for r in summary if r["score"]>=80]) / max(len(summary),1) * 100)
        b3 = (f"<b>Load looks manageable.</b> {ready_pct}% of squad fully ready — "
              f"normal training volume appropriate today.")
        b3_color = "#16a34a"

    # ── Render all 3 bullets ─────────────────────────────────────────────────
    def _bullet(text, color):
        icon = "⚠" if color == "#dc2626" else ("◑" if color == "#d97706" else "✓")
        icon_col = color
        return (
            f'<div style="display:flex;gap:12px;align-items:flex-start;'
            f'padding:8px 0;border-bottom:1px solid #f1f5f9;">'
            f'<span style="color:{icon_col};font-size:15px;min-width:18px;'
            f'margin-top:1px;font-weight:700;">{icon}</span>'
            f'<span style="font-size:13px;color:#1e293b;line-height:1.5;">{text}</span>'
            f'</div>'
        )

    brief_html = (
        '<div style="background:#f8fafc;border:1px solid #e2e8f0;'
        'border-left:4px solid #f59e0b;border-radius:0 8px 8px 0;'
        'padding:14px 18px;margin-bottom:16px;">'
        '<div style="font-size:10px;font-weight:700;letter-spacing:0.15em;'
        'color:#94a3b8;text-transform:uppercase;margin-bottom:8px;">'
        'Morning Brief</div>'
        + _bullet(b1, b1_color)
        + _bullet(b2, b2_color)
        + _bullet(b3, b3_color)
        + '</div>'
    )
    st.markdown(brief_html, unsafe_allow_html=True)

    # ── ROW 1: Alerts + GPS Strip ─────────────────────────────────────────────
    left, right = st.columns([3, 2])

    with left:
        st.markdown(
            '<div style="font-size:11px; font-weight:700; letter-spacing:0.18em; '
            'text-transform:uppercase; color:#94a3b8; margin-bottom:10px;">'
            'Priority Alerts</div>',
            unsafe_allow_html=True,
        )

        if not alerts:
            st.markdown(
                '<div style="background:#f0fdf4; border-left:4px solid #22c55e; '
                'border-radius:0 8px 8px 0; padding:14px 18px; '
                'color:#15803d; font-weight:600; font-size:14px;">'
                'All clear — no priority alerts today</div>',
                unsafe_allow_html=True,
            )
        else:
            for a in alerts[:3]:   # hard cap at 3
                is_red  = a["level"].startswith("🔴")
                border  = "#ef4444" if is_red else "#f59e0b"
                bg      = "#fff5f5" if is_red else "#fffbeb"
                # Plain label — strip emoji from level string
                lbl_raw = a["level"].split(" ", 1)[-1] if " " in a["level"] else a["level"]
                lbl     = lbl_raw.replace("🔴","").replace("🟡","").strip()
                lbl_color = "#dc2626" if is_red else "#d97706"
                html = (
                    f'<div style="background:{bg};border-left:4px solid {border};'
                    f'border-radius:0 8px 8px 0;padding:12px 16px;margin-bottom:8px;">'
                    # Name + label on one line
                    f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">'
                    f'<span style="font-weight:800;font-size:14px;color:#0f172a;">{a["name"]}</span>'
                    f'<span style="font-size:10px;font-weight:700;color:{lbl_color};'
                    f'letter-spacing:0.08em;">{lbl}</span>'
                    f'</div>'
                    # Why
                    f'<div style="font-size:12px;color:#475569;margin-bottom:6px;">{a["msg"]}</div>'
                    # What to do
                    f'<div style="font-size:12px;font-weight:700;color:#1e40af;">'
                    f'&#9658; {a["action"]}</div>'
                    f'</div>'
                )
                st.markdown(html, unsafe_allow_html=True)

    with right:
        st.markdown(
            '<div style="font-size:11px; font-weight:700; letter-spacing:0.18em; '
            'text-transform:uppercase; color:#94a3b8; margin-bottom:10px;">'
            'GPS / Kinexon Strip</div>',
            unsafe_allow_html=True,
        )

        if gps:
            avg_load = gps["team_avg_load"]
            avg_acc  = int(round(gps["team_avg_acc"]))
            hi_names = gps["high_load_names"] or "—"
            lo_names = gps["low_acc_names"]   or "—"
            gps_html = (
                '<div style="background:linear-gradient(135deg,#0ea5e9,#0284c7);'
                'border-radius:12px;padding:16px 20px;color:#fff;">'
                # Two stat cells
                '<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">'
                '<div>'
                '<div style="font-size:10px;font-weight:600;opacity:0.75;'
                'letter-spacing:0.1em;text-transform:uppercase;">Team Avg Load</div>'
                f'<div style="font-size:26px;font-weight:800;font-family:monospace;">{avg_load}</div>'
                '<div style="font-size:10px;opacity:0.6;">AU</div>'
                '</div>'
                '<div>'
                '<div style="font-size:10px;font-weight:600;opacity:0.75;'
                'letter-spacing:0.1em;text-transform:uppercase;">Team Avg Accels</div>'
                f'<div style="font-size:26px;font-weight:800;font-family:monospace;">{avg_acc}</div>'
                '<div style="font-size:10px;opacity:0.6;">events above threshold</div>'
                '</div>'
                '</div>'
                # High load / low accels names
                '<div style="margin-top:12px;border-top:1px solid rgba(255,255,255,0.2);'
                'padding-top:10px;">'
                '<div style="font-size:10px;font-weight:700;opacity:0.8;margin-bottom:3px;">'
                'HIGH LOAD</div>'
                f'<div style="font-size:12px;">{hi_names}</div>'
                '<div style="font-size:10px;font-weight:700;opacity:0.8;'
                'margin-top:8px;margin-bottom:3px;">LOW ACCELS</div>'
                f'<div style="font-size:12px;">{lo_names}</div>'
                '</div>'
                '</div>'
            )
            st.markdown(gps_html, unsafe_allow_html=True)
        else:
            st.markdown(
                '<div style="background:#f1f5f9;border-radius:8px;padding:16px;'
                'color:#94a3b8;font-size:13px;">GPS data unavailable</div>',
                unsafe_allow_html=True,
            )

    # ── ROW 2: Roster Status ─────────────────────────────────────────────────
    # Cards show: name | position | status badge | readiness % | 2 reasons max
    # Sorted red → yellow → green (most urgent top-left)
    # No availability %, no signal icons — badge IS the availability signal

    st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
    st.markdown(
        '<div style="font-size:11px; font-weight:700; letter-spacing:0.18em; '
        'text-transform:uppercase; color:#94a3b8; margin-bottom:10px;">Roster Status</div>',
        unsafe_allow_html=True,
    )

    grid_rows = (
        [r for r in summary if r["score"] < 60] +
        [r for r in summary if 60 <= r["score"] < 80] +
        [r for r in summary if r["score"] >= 80]
    )

    CARD = {
        "red":    {"bg": "#fde8e8", "border": "#ef4444", "score": "#dc2626",
                   "badge_bg": "#fecaca", "badge_fg": "#991b1b", "label": "PROTECT"},
        "yellow": {"bg": "#fef9c3", "border": "#f59e0b", "score": "#d97706",
                   "badge_bg": "#fef3c7", "badge_fg": "#92400e", "label": "MONITOR"},
        "green":  {"bg": "#dcfce7", "border": "#22c55e", "score": "#16a34a",
                   "badge_bg": "#bbf7d0", "badge_fg": "#166534", "label": "READY"},
    }

    def _key(score):
        return "red" if score < 60 else ("yellow" if score < 80 else "green")

    def _card_html(r):
        k = _key(r["score"])
        c = CARD[k]

        inj_risk = r.get("inj_risk")
        # Risk indicator — only show when elevated (≥30%). 
        # "Low risk" adds noise without adding decision value for a coach.
        # Coaches act on alerts, not confirmations. (Kitman Labs design principle 2024)
        if inj_risk is not None and inj_risk >= 60:
            risk_txt, risk_color, risk_bg = "Injury watch this week", "#dc2626", "#fee2e2"
            risk_badge = (
                f'<span style="background:{risk_bg};color:{risk_color};font-size:10px;'
                f'font-weight:700;padding:2px 7px;border-radius:4px;'
                f'border:1px solid {risk_color}44;white-space:nowrap;">{risk_txt}</span>'
            )
            risk_tooltip = "7-day injury risk ≥60% — limit max-effort reps, monitor warmup"
        elif inj_risk is not None and inj_risk >= 30:
            risk_txt, risk_color, risk_bg = "Watch closely", "#d97706", "#fef3c7"
            risk_badge = (
                f'<span style="background:{risk_bg};color:{risk_color};font-size:10px;'
                f'font-weight:700;padding:2px 7px;border-radius:4px;'
                f'border:1px solid {risk_color}44;white-space:nowrap;">{risk_txt}</span>'
            )
            risk_tooltip = "7-day injury risk 30–60% — monitor closely this week"
        else:
            # No badge when low risk — absence of alert IS the signal
            risk_badge   = ""
            risk_tooltip = ""

        # overnight change — compare yesterday's score if available
        overnight = r.get("overnight_delta")
        if overnight is not None and abs(overnight) >= 2:
            arrow     = "▲" if overnight > 0 else "▼"
            ov_color  = "#16a34a" if overnight > 0 else "#dc2626"
            ov_html   = (f'<span style="font-size:11px;color:{ov_color};'
                         f'margin-left:6px;font-weight:600;">'
                         f'{arrow}{abs(overnight):.0f}% overnight</span>')
        else:
            ov_html = ""

        return (
            f'<div style="background:{c["bg"]};border:2px solid {c["border"]};'
            f'border-radius:10px;padding:14px 16px;min-height:140px;'
            f'display:flex;flex-direction:column;gap:6px;">'

            # Row 1: name + status badge
            f'<div style="display:flex;justify-content:space-between;align-items:flex-start;">'
            f'  <div>'
            f'    <div style="font-weight:800;font-size:14px;color:#0f172a;">{r["name"]}</div>'
            f'    <div style="font-size:11px;color:#64748b;margin-top:1px;">{r["pos"]}</div>'
            f'  </div>'
            f'  <span style="background:{c["badge_bg"]};color:{c["badge_fg"]};font-size:10px;'
            f'  font-weight:800;padding:3px 8px;border-radius:5px;letter-spacing:0.06em;'
            f'  white-space:nowrap;">{c["label"]}</span>'
            f'</div>'

            # Row 2: big readiness % + overnight delta + risk badge
            f'<div style="display:flex;justify-content:space-between;align-items:center;'
            f'margin-top:4px;">'
            f'  <div style="display:flex;align-items:baseline;gap:4px;">'
            f'    <span style="font-size:32px;font-weight:800;color:{c["score"]};'
            f'    font-family:Georgia,serif;line-height:1;">{r["score"]:.0f}%</span>'
            f'    {ov_html}'
            f'  </div>'
            f'  <div title="{risk_tooltip}">{risk_badge}</div>'
            f'</div>'

            # Row 3: cumulative minutes — Orlando Magic framework: coaches think in minutes
            + (
                f'<div style="font-size:11px;color:#64748b;margin-top:3px;">'
                f'<b style="color:#334155;">{r["mins_4d"]:.0f} min</b> last 4 days'
                + (f' &nbsp;·&nbsp; <b style="color:#334155;">{r["mins_8d"]:.0f}</b> last 8'
                   if r.get("mins_8d") is not None else "")
                + '</div>'
                if r.get("mins_4d") is not None else ""
            )

            # Divider
            + f'<div style="border-top:1px solid {c["border"]}55;margin:4px 0;"></div>'

            # Row 4: reason — plain English, coach-decision language only (no raw numbers)
            + f'<div style="font-size:11px;color:#475569;line-height:1.4;">{r["reason"]}</div>'

            + f'</div>'
        )

    # Build overnight deltas for all players
    yesterday_scores = {}
    w_yest_all = wellness[pd.to_datetime(wellness["date"]) == pd.Timestamp(ref - pd.Timedelta(days=1))]
    for _, py in players.iterrows():
        wy = w_yest_all[w_yest_all["player_id"] == py["player_id"]]
        if len(wy) > 0:
            wy_row = dict(wy.iloc[0]) | {"position": py.get("position", "F")}
            fp_y = force_plate[force_plate["player_id"] == py["player_id"]].sort_values("date")
            fp_y = fp_y[pd.to_datetime(fp_y["date"]) <= pd.Timestamp(ref - pd.Timedelta(days=1))]
            if len(fp_y) > 0:
                wy_row["cmj_height_cm"] = fp_y.iloc[-1]["cmj_height_cm"]
                wy_row["rsi_modified"]  = fp_y.iloc[-1]["rsi_modified"]
            yesterday_scores[py["player_id"]] = _calculate_readiness(wy_row)

    for r in grid_rows:
        yest = yesterday_scores.get(r["pid"])
        r["overnight_delta"] = round(r["score"] - yest, 1) if yest is not None else None

    cols = st.columns(4)
    for i, r in enumerate(grid_rows):
        with cols[i % 4]:
            st.markdown(_card_html(r), unsafe_allow_html=True)

    # ── LEGEND — scrollable reference at bottom of roster ────────────────────
    st.markdown("<div style='margin-top:18px;'></div>", unsafe_allow_html=True)
    st.markdown(
        '<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;'
        'padding:12px 18px;font-size:11px;color:#64748b;">'
        '<span style="font-weight:700;color:#334155;margin-right:12px;">KEY</span>'
        '<span style="margin-right:16px;">'
        '<b style="color:#16a34a;">READY</b> ≥80% — full training, no restrictions</span>'
        '<span style="margin-right:16px;">'
        '<b style="color:#d97706;">MONITOR</b> 60–79% — modified load, watch closely</span>'
        '<span style="margin-right:16px;">'
        '<b style="color:#dc2626;">PROTECT</b> &lt;60% — restricted session, flag for medical</span>'
        '<span style="display:block;margin-top:6px;">'
        '<b>Injury watch</b> = 7-day risk ≥60% &nbsp;·&nbsp; '
        '<b>Watch closely</b> = 30–60% &nbsp;·&nbsp; '
        'No badge = low risk (&lt;30%) &nbsp;·&nbsp; '
        '<b>▲/▼ overnight</b> = readiness change vs yesterday &nbsp;·&nbsp; '
        '<b>min last 4/8 days</b> = practice + game minutes combined</span>'
        '</div>',
        unsafe_allow_html=True,
    )
