from __future__ import annotations


def calculate_readiness_score(row) -> float:
    """Shared WAIMS readiness formula used across staff and athlete views."""
    sleep_hrs = row.get("sleep_hours", 7.5)
    sleep_q = row.get("sleep_quality", 7)
    sleep_s = min(15, (sleep_hrs / 8.0) * 10 + (sleep_q / 10) * 5)
    sore_s = ((10 - row.get("soreness", 4)) / 10) * 10
    mood_s = (row.get("mood", 7) / 10) * 5
    stress_s = ((10 - row.get("stress", 4)) / 10) * 5
    cmj = row.get("cmj_height_cm")
    pos = str(row.get("position", "F"))
    bench = 38 if "G" in pos else (30 if "C" in pos else 34)
    cmj_s = min(15, (cmj / bench) * 15) if cmj and cmj > 0 else 11
    rsi = row.get("rsi_modified")
    rsi_s = min(10, (rsi / 0.45) * 10) if rsi and rsi > 0 else 8
    sched_s = 10
    if row.get("is_back_to_back", 0):
        sched_s -= 4
    if row.get("days_rest", 3) <= 1:
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
