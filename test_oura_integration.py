import oura_connector
import oura_mapper


def test_oura_demo_summary_contains_expected_fields():
    summary = oura_connector.get_latest_oura_summary(demo_mode=True, day="2026-03-21")

    assert summary["demo_mode"] is True
    assert summary["day"] == "2026-03-21"
    assert summary["readiness_score"] is not None
    assert summary["total_sleep_duration"] is not None
    assert summary["average_hrv"] is not None
    assert summary["resting_heart_rate"] is not None


def test_oura_mapper_converts_core_fields_to_waims_schema():
    mapped = oura_mapper.map_oura_to_wellness_schema(
        {
            "day": "2026-03-21",
            "readiness_score": 81,
            "total_sleep_duration": 27000,
            "average_hrv": 54,
            "resting_heart_rate": 48,
            "demo_mode": True,
        }
    )

    assert mapped["date"] == "2026-03-21"
    assert mapped["readiness"] == 81.0
    assert mapped["sleep_hours"] == 7.5
    assert mapped["hrv"] == 54.0
    assert mapped["rhr"] == 48.0
    assert mapped["demo_mode"] is True


def test_oura_status_defaults_to_demo_without_token(monkeypatch):
    monkeypatch.delenv("OURA_PERSONAL_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("OURA_API_TOKEN", raising=False)
    monkeypatch.delenv("OURA_TOKEN", raising=False)
    monkeypatch.delenv("OURA_DEMO_MODE", raising=False)
    monkeypatch.delenv("WAIMS_OURA_DEMO_MODE", raising=False)
    monkeypatch.delenv("WAIMS_DEMO_MODE", raising=False)

    status = oura_connector.get_oura_status()

    assert status["status"] == "Demo mode"
    assert status["kind"] == "demo"
    assert status["demo_mode"] is True
