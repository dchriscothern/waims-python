"""
Oura API proof-of-concept connector for WAIMS Python.

This module intentionally favors a demo-friendly flow:
- Personal access token auth only for the POC
- Automatic demo fallback when no token is configured
- Small surface area focused on daily readiness + sleep/recovery signals
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

import requests


OURA_API_BASE_URL = "https://api.ouraring.com/v2/usercollection"
DEFAULT_TIMEOUT_SECONDS = 15


class OuraConnectorError(RuntimeError):
    """Raised when the Oura API request fails in live mode."""


def _truthy_flag(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _today_iso() -> str:
    return date.today().isoformat()


def _yesterday_iso() -> str:
    return (date.today() - timedelta(days=1)).isoformat()


def _sample_daily_sleep(day: Optional[str] = None) -> Dict[str, Any]:
    sample_day = day or _today_iso()
    return {
        "day": sample_day,
        "score": 84,
        "sleep_score": 84,
        "total_sleep_duration": 7 * 3600 + 28 * 60,
        "average_hrv": 58,
        "resting_heart_rate": 49,
        "lowest_heart_rate": 46,
        "efficiency": 92,
        "latency": 12 * 60,
        "time_in_bed": 8 * 3600 + 1 * 60,
    }


def _sample_daily_readiness(day: Optional[str] = None) -> Dict[str, Any]:
    sample_day = day or _today_iso()
    return {
        "day": sample_day,
        "score": 82,
        "readiness_score": 82,
        "temperature_deviation": -0.1,
        "contributors": {
            "activity_balance": 80,
            "body_temperature": 96,
            "hrv_balance": 78,
            "previous_day_activity": 81,
            "previous_night": 85,
            "recovery_index": 79,
            "resting_heart_rate": 88,
            "sleep_balance": 84,
        },
    }


@dataclass
class OuraAPIClient:
    personal_access_token: Optional[str] = None
    demo_mode: Optional[bool] = None
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS

    def __post_init__(self) -> None:
        env_token = (
            os.getenv("OURA_PERSONAL_ACCESS_TOKEN")
            or os.getenv("OURA_API_TOKEN")
            or os.getenv("OURA_TOKEN")
            or ""
        ).strip()
        self.personal_access_token = (self.personal_access_token or env_token or "").strip() or None

        env_demo_value = (
            os.getenv("OURA_DEMO_MODE")
            or os.getenv("WAIMS_OURA_DEMO_MODE")
            or os.getenv("WAIMS_DEMO_MODE")
        )
        if self.demo_mode is None:
            if env_demo_value not in (None, ""):
                self.demo_mode = _truthy_flag(env_demo_value)
            else:
                self.demo_mode = not bool(self.personal_access_token)

    def _headers(self) -> Dict[str, str]:
        if not self.personal_access_token:
            raise OuraConnectorError(
                "Missing Oura personal access token. Set OURA_PERSONAL_ACCESS_TOKEN or enable demo mode."
            )
        return {"Authorization": f"Bearer {self.personal_access_token}"}

    def _get(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        response = requests.get(
            f"{OURA_API_BASE_URL}/{path.lstrip('/')}",
            headers=self._headers(),
            params=params,
            timeout=self.timeout_seconds,
        )
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise OuraConnectorError(f"Oura API request failed: {response.status_code} {response.text}") from exc
        return response.json()

    def get_daily_sleep(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        if self.demo_mode:
            return [_sample_daily_sleep(end_date or start_date or _today_iso())]

        params = {"start_date": start_date or _yesterday_iso(), "end_date": end_date or _today_iso()}
        payload = self._get("daily_sleep", params)
        return payload.get("data", [])

    def get_daily_readiness(
        self, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        if self.demo_mode:
            return [_sample_daily_readiness(end_date or start_date or _today_iso())]

        params = {"start_date": start_date or _yesterday_iso(), "end_date": end_date or _today_iso()}
        payload = self._get("daily_readiness", params)
        return payload.get("data", [])

    def get_daily_summary(self, day: Optional[str] = None) -> Dict[str, Any]:
        target_day = day or _today_iso()
        sleep_rows = self.get_daily_sleep(start_date=target_day, end_date=target_day)
        readiness_rows = self.get_daily_readiness(start_date=target_day, end_date=target_day)

        sleep_row = next((row for row in sleep_rows if row.get("day") == target_day), sleep_rows[0] if sleep_rows else {})
        readiness_row = next(
            (row for row in readiness_rows if row.get("day") == target_day),
            readiness_rows[0] if readiness_rows else {},
        )

        return {
            "day": target_day,
            "demo_mode": bool(self.demo_mode),
            "sleep": sleep_row,
            "readiness": readiness_row,
            "sleep_score": sleep_row.get("sleep_score", sleep_row.get("score")),
            "total_sleep_duration": sleep_row.get("total_sleep_duration"),
            "average_hrv": sleep_row.get("average_hrv"),
            "resting_heart_rate": sleep_row.get("resting_heart_rate"),
            "readiness_score": readiness_row.get("readiness_score", readiness_row.get("score")),
        }


def get_oura_status(
    personal_access_token: Optional[str] = None,
    demo_mode: Optional[bool] = None,
) -> Dict[str, Any]:
    client = OuraAPIClient(personal_access_token=personal_access_token, demo_mode=demo_mode)

    if client.demo_mode:
        sample_day = _today_iso()
        return {
            "connected": False,
            "demo_mode": True,
            "status": "Demo mode",
            "kind": "demo",
            "last_sync": sample_day,
            "source": "sample",
        }

    if not client.personal_access_token:
        return {
            "connected": False,
            "demo_mode": False,
            "status": "Not connected",
            "kind": "not_connected",
            "last_sync": None,
            "source": "none",
        }

    try:
        summary = client.get_daily_summary()
        last_sync = summary.get("day") or _today_iso()
        return {
            "connected": True,
            "demo_mode": False,
            "status": "Connected",
            "kind": "active",
            "last_sync": last_sync,
            "source": "oura_api",
        }
    except Exception as exc:
        return {
            "connected": False,
            "demo_mode": False,
            "status": "Error",
            "kind": "error",
            "last_sync": None,
            "error": str(exc),
            "source": "oura_api",
        }


def get_latest_oura_summary(
    personal_access_token: Optional[str] = None,
    demo_mode: Optional[bool] = None,
    day: Optional[str] = None,
) -> Dict[str, Any]:
    client = OuraAPIClient(personal_access_token=personal_access_token, demo_mode=demo_mode)
    return client.get_daily_summary(day=day)
