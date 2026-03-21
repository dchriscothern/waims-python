"""
Mapping helpers for translating Oura POC payloads into WAIMS wellness fields.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def _coerce_float(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _seconds_to_hours(value: Any) -> Optional[float]:
    seconds = _coerce_float(value)
    if seconds is None:
        return None

    if seconds > 1000:
        return round(seconds / 3600.0, 2)

    return round(seconds, 2)


def map_oura_to_wellness_schema(oura_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Flatten the Oura daily payload into a WAIMS-friendly wellness shape.

    Required mappings:
    - readiness_score -> readiness
    - total_sleep_duration -> sleep_hours
    - average_hrv -> hrv
    - resting_heart_rate -> rhr
    """

    readiness_block = oura_payload.get("readiness") or {}
    sleep_block = oura_payload.get("sleep") or {}

    readiness_score = oura_payload.get("readiness_score", readiness_block.get("readiness_score", readiness_block.get("score")))
    total_sleep_duration = oura_payload.get("total_sleep_duration", sleep_block.get("total_sleep_duration"))
    average_hrv = oura_payload.get("average_hrv", sleep_block.get("average_hrv"))
    resting_heart_rate = oura_payload.get("resting_heart_rate", sleep_block.get("resting_heart_rate"))
    sleep_score = oura_payload.get("sleep_score", sleep_block.get("sleep_score", sleep_block.get("score")))

    return {
        "date": oura_payload.get("day") or sleep_block.get("day") or readiness_block.get("day"),
        "readiness": _coerce_float(readiness_score),
        "sleep_hours": _seconds_to_hours(total_sleep_duration),
        "hrv": _coerce_float(average_hrv),
        "rhr": _coerce_float(resting_heart_rate),
        "sleep_score": _coerce_float(sleep_score),
        "source": "oura_ring",
        "source_provider": "oura",
        "demo_mode": bool(oura_payload.get("demo_mode", False)),
    }


def map_oura_record(
    readiness_record: Optional[Dict[str, Any]] = None,
    sleep_record: Optional[Dict[str, Any]] = None,
    demo_mode: bool = False,
) -> Dict[str, Any]:
    combined = {
        "day": (sleep_record or {}).get("day") or (readiness_record or {}).get("day"),
        "readiness": readiness_record or {},
        "sleep": sleep_record or {},
        "readiness_score": (readiness_record or {}).get("readiness_score", (readiness_record or {}).get("score")),
        "total_sleep_duration": (sleep_record or {}).get("total_sleep_duration"),
        "average_hrv": (sleep_record or {}).get("average_hrv"),
        "resting_heart_rate": (sleep_record or {}).get("resting_heart_rate"),
        "sleep_score": (sleep_record or {}).get("sleep_score", (sleep_record or {}).get("score")),
        "demo_mode": demo_mode,
    }
    return map_oura_to_wellness_schema(combined)
