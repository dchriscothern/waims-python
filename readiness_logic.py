from __future__ import annotations

import pickle
from pathlib import Path

import pandas as pd

_READINESS_FN = None
try:
    _scorer_path = Path(__file__).resolve().parent / "models" / "readiness_scorer.pkl"
    if _scorer_path.exists():
        with open(_scorer_path, "rb") as _f:
            _scorer_data = pickle.load(_f)
            _READINESS_FN = _scorer_data.get("function")
except Exception:
    _READINESS_FN = None


LOAD_SCENARIO_EFFECTS = {
    "Rest / Practice only": {
        "sleep_adj": +0.1,
        "sore_adj": -0.3,
        "stress_adj": -0.5,
        "b2b": 0,
        "cmj_adj": 0.0,
    },
    "Typical game load (~28 min)": {
        "sleep_adj": -0.2,
        "sore_adj": +0.8,
        "stress_adj": +0.3,
        "b2b": 0,
        "cmj_adj": -0.5,
    },
    "Heavy game load (~36 min)": {
        "sleep_adj": -0.4,
        "sore_adj": +1.5,
        "stress_adj": +0.5,
        "b2b": 0,
        "cmj_adj": -1.5,
    },
    "Back-to-back game": {
        "sleep_adj": -0.7,
        "sore_adj": +2.5,
        "stress_adj": +1.5,
        "b2b": 1,
        "cmj_adj": -2.5,
    },
}


def calculate_readiness_score(row) -> float:
    """Shared WAIMS readiness formula used across staff and athlete views."""
    if _READINESS_FN is not None:
        try:
            return _READINESS_FN(row)
        except Exception:
            pass

    sleep_hrs = row.get("sleep_hours", 7.5)
    sleep_q = row.get("sleep_quality", 7)
    sleep_s = min(15, (sleep_hrs / 8.0) * 10 + (sleep_q / 10) * 5)
    sore_s = ((10 - row.get("soreness", 4)) / 10) * 10
    mood_s = (row.get("mood", 7) / 10) * 5
    stress_s = ((10 - row.get("stress", 4)) / 10) * 5
    cmj = row.get("cmj_height_cm")
    pos = str(row.get("position", row.get("pos", "F")))
    bench = 38 if "G" in pos else (30 if "C" in pos else 34)
    cmj_s = min(15, (cmj / bench) * 15) if cmj and cmj > 0 else 11
    rsi = row.get("rsi_modified")
    rsi_s = min(10, (rsi / 0.45) * 10) if rsi and rsi > 0 else 8
    sched_s = 10
    if row.get("is_back_to_back", 0):
        sched_s -= 4
    if row.get("days_rest", 3) <= 1:
        sched_s -= 2
    if row.get("travel_flag", 0):
        sched_s -= min(3, abs(row.get("time_zone_diff", 0)) * 1.5)
    if row.get("unrivaled_flag", 0):
        sched_s -= 2
    sched_s = max(0, sched_s)
    raw = sleep_s + sore_s + mood_s + stress_s + cmj_s + rsi_s + sched_s
    return round(min(100, raw * (100 / 70)), 1)


def readiness_bucket(score: float) -> tuple[str, str, str]:
    if score >= 80:
        return "READY", "#16a34a", "#ecfdf5"
    if score >= 60:
        return "MONITOR", "#d97706", "#fffbeb"
    return "PROTECT", "#dc2626", "#fef2f2"


def sum_recent_total_minutes(training_load_df, player_id, ref_date, days=4) -> float | None:
    if "practice_minutes" not in training_load_df.columns:
        return None

    training_load = training_load_df.copy()
    training_load["date"] = pd.to_datetime(training_load["date"])
    ref_date = pd.Timestamp(ref_date)
    window = training_load[
        (training_load["player_id"] == player_id)
        & (training_load["date"] > ref_date - pd.Timedelta(days=days))
        & (training_load["date"] <= ref_date)
    ].copy()
    if len(window) == 0:
        return None

    total = (
        window.get("game_minutes", pd.Series([0] * len(window))).fillna(0).sum()
        + window.get("practice_minutes", pd.Series([0] * len(window))).fillna(0).sum()
    )
    return float(total)


def project_load_scenario(current_wellness_row, *, position: str, latest_cmj, latest_rsi, scenario: str) -> dict:
    fx = LOAD_SCENARIO_EFFECTS[scenario]
    today_input = dict(current_wellness_row)
    today_input.update(
        {
            "position": position,
            "cmj_height_cm": latest_cmj,
            "rsi_modified": latest_rsi,
            "is_back_to_back": int(today_input.get("is_back_to_back", 0)),
            "days_rest": int(today_input.get("days_rest", 1)),
        }
    )

    proj_sleep = max(4.5, min(9.5, float(today_input.get("sleep_hours", 7.5)) + fx["sleep_adj"]))
    proj_soreness = max(0, min(10, float(today_input.get("soreness", 4)) + fx["sore_adj"]))
    proj_stress = max(1, min(10, float(today_input.get("stress", 4)) + fx["stress_adj"]))
    proj_mood = max(1, min(10, float(today_input.get("mood", 7)) - fx["stress_adj"] * 0.3))
    proj_cmj = max(18, latest_cmj + fx["cmj_adj"]) if latest_cmj is not None else None

    forecast_input = {
        "sleep_hours": proj_sleep,
        "sleep_quality": today_input.get("sleep_quality", 7),
        "soreness": proj_soreness,
        "stress": proj_stress,
        "mood": proj_mood,
        "cmj_height_cm": proj_cmj,
        "rsi_modified": latest_rsi,
        "position": position,
        "is_back_to_back": fx["b2b"],
        "days_rest": 0 if fx["b2b"] else 1,
    }

    today_score = calculate_readiness_score(today_input)
    tomorrow_score = calculate_readiness_score(forecast_input)
    delta = tomorrow_score - today_score
    status, color, bg = readiness_bucket(tomorrow_score)

    return {
        "today_input": today_input,
        "forecast_input": forecast_input,
        "today_score": today_score,
        "tomorrow_score": tomorrow_score,
        "delta": delta,
        "status": status,
        "color": color,
        "bg": bg,
    }


def build_load_projection_recommendation(player_name: str, status: str, tomorrow_score: float, mins_4d: float | None) -> dict:
    if status == "PROTECT":
        if mins_4d and mins_4d > 90:
            min_cap = "20-24 minutes maximum"
            drill_note = "Remove from full-court sprints and late-game crunch situations"
        else:
            min_cap = "22-26 minutes"
            drill_note = "Limit explosive acceleration drills in warmup"
        return {
            "head": "Restrict Tonight",
            "label": "Protect Staff Recommendation",
            "color": "#dc2626",
            "bg": "#fef2f2",
            "body": (
                f"Cap {player_name} at {min_cap} tonight. {drill_note}. "
                f"Check in individually before practice - ask about sleep and leg fatigue. "
                f"Projected readiness tomorrow: {tomorrow_score:.0f}% (PROTECT)."
            ),
        }

    if status == "MONITOR":
        if mins_4d and mins_4d > 100:
            min_cap = "26-30 minutes"
            drill_note = "Reduce high-intensity interval reps in practice; prioritise skill work"
        else:
            min_cap = "standard minutes with close monitoring"
            drill_note = "Watch warmup quality - if movement looks laboured, reduce early"
        return {
            "head": "Monitor Closely",
            "label": "Monitor Staff Recommendation",
            "color": "#d97706",
            "bg": "#fffbeb",
            "body": (
                f"{player_name}: {drill_note}. Target {min_cap} tonight. "
                f"Re-check soreness in warmup - if it reaches 7/10 or higher, pull back further. "
                f"Projected readiness tomorrow: {tomorrow_score:.0f}% (MONITOR)."
            ),
        }

    return {
        "head": "Clear for Full Load",
        "label": "Clear Staff Recommendation",
        "color": "#16a34a",
        "bg": "#f0fdf4",
        "body": (
            f"{player_name} is projected to recover well. "
            f"No restrictions needed tonight - full minutes available. "
            f"Projected readiness tomorrow: {tomorrow_score:.0f}% (READY)."
        ),
    }
