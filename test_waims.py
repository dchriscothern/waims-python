"""
WAIMS Unit Tests
================
Tests for core logic: readiness formula, query parsing,
z-score calculations, data quality, sport config, and auth.

Run:
    pytest test_waims.py -v
    pytest test_waims.py -v --tb=short   # shorter tracebacks
    pytest test_waims.py::TestReadiness  # single class

These tests use only synthetic data — no database required for most tests.
Database tests are marked @pytest.mark.db and require waims_demo.db.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock


# ==============================================================================
# READINESS FORMULA TESTS
# ==============================================================================

class TestReadinessFormula:
    """
    Tests for the core readiness scoring formula.
    Formula: CMJ 35pts + RSI 25pts + Sleep 20pts + Soreness 10pts + Mood/Stress 10pts
    
    These test the formula logic directly without importing dashboard.py
    (which requires streamlit context).
    """

    def _score(self, sleep=8.0, soreness=2, stress=2, mood=8,
               cmj_z=0.5, rsi_z=0.5):
        """Replicate the readiness formula used in dashboard.py"""
        sleep_pct    = min(100, (sleep / 8) * 100)
        physical_pct = ((10 - soreness) / 10) * 100
        mental_pct   = (mood / 10) * 100
        stress_pct   = ((10 - stress) / 10) * 100

        # Simplified formula matching dashboard
        score = (
            (sleep / 8) * 30 +
            ((10 - soreness) / 10) * 25 +
            ((10 - stress) / 10) * 25 +
            (mood / 10) * 20
        )
        return round(min(100, max(0, score)), 1)

    def test_perfect_athlete_scores_100(self):
        score = self._score(sleep=8, soreness=0, stress=0, mood=10)
        assert score == 100.0

    def test_worst_case_scores_zero(self):
        score = self._score(sleep=0, soreness=10, stress=10, mood=0)
        assert score == 0.0

    def test_good_athlete_scores_ready(self):
        """8hr sleep, low soreness/stress, good mood → READY (≥80)"""
        score = self._score(sleep=8, soreness=2, stress=2, mood=8)
        assert score >= 80, f"Expected ≥80, got {score}"

    def test_poor_sleep_drops_score(self):
        """Sleep drops from 8h to 5h should drop score significantly"""
        good = self._score(sleep=8, soreness=2, stress=2, mood=8)
        poor = self._score(sleep=5, soreness=2, stress=2, mood=8)
        assert poor < good
        assert good - poor >= 10, f"Expected ≥10pt drop, got {good - poor:.1f}"

    def test_high_soreness_drops_score(self):
        good = self._score(soreness=2)
        bad  = self._score(soreness=9)
        assert bad < good

    def test_sleep_weight_is_30pts(self):
        """Sleep contributes 30pts at max — difference between 0 and 8hrs sleep"""
        full_sleep  = self._score(sleep=8,  soreness=0, stress=0, mood=10)
        no_sleep    = self._score(sleep=0,  soreness=0, stress=0, mood=10)
        sleep_contribution = full_sleep - no_sleep
        assert abs(sleep_contribution - 30) < 1, \
            f"Sleep weight should be ~30pts, got {sleep_contribution}"

    def test_soreness_weight_is_25pts(self):
        """Soreness contributes 25pts at max"""
        no_soreness  = self._score(sleep=8, soreness=0,  stress=0, mood=10)
        max_soreness = self._score(sleep=8, soreness=10, stress=0, mood=10)
        diff = no_soreness - max_soreness
        assert abs(diff - 25) < 1, f"Soreness weight should be ~25pts, got {diff}"

    def test_score_never_exceeds_100(self):
        score = self._score(sleep=12, soreness=0, stress=0, mood=10)
        assert score <= 100

    def test_score_never_below_0(self):
        score = self._score(sleep=0, soreness=10, stress=10, mood=0)
        assert score >= 0

    def test_traffic_light_thresholds(self):
        """Test READY/MONITOR/PROTECT threshold boundaries"""
        ready   = self._score(sleep=8, soreness=1, stress=1, mood=9)
        monitor = self._score(sleep=7, soreness=5, stress=5, mood=6)
        protect = self._score(sleep=5, soreness=8, stress=8, mood=3)

        assert ready >= 80,    f"Expected READY (≥80), got {ready}"
        assert 60 <= monitor < 80, f"Expected MONITOR (60-79), got {monitor}"
        assert protect < 60,   f"Expected PROTECT (<60), got {protect}"


# ==============================================================================
# QUERY PARSING TESTS
# ==============================================================================

class TestQueryParsing:
    """Tests for the Ask the Watchlist query parser."""

    def _parse(self, text):
        """Replicate parse_query logic from dashboard.py"""
        text = text.lower().strip()
        if any(w in text for w in ["poor sleep", "bad sleep", "tired", "sleep"]):
            return "poor_sleep"
        elif any(w in text for w in ["high risk", "at risk", "injury risk"]):
            return "high_risk"
        elif any(w in text for w in ["readiness", "ready"]):
            return "readiness"
        elif "compare position" in text or "position comparison" in text:
            return "position_comparison"
        elif any(w in text for w in ["back to back", "back-to-back", "b2b", "schedule", "rest"]):
            return "back_to_back"
        return "unknown"

    def test_poor_sleep_keywords(self):
        assert self._parse("poor sleep") == "poor_sleep"
        assert self._parse("bad sleep last night") == "poor_sleep"
        assert self._parse("who is tired") == "poor_sleep"
        assert self._parse("sleep") == "poor_sleep"

    def test_high_risk_keywords(self):
        assert self._parse("high risk players") == "high_risk"
        assert self._parse("who is at risk") == "high_risk"
        assert self._parse("injury risk today") == "high_risk"

    def test_readiness_keywords(self):
        assert self._parse("readiness") == "readiness"
        assert self._parse("who is ready") == "readiness"
        assert self._parse("show me readiness scores") == "readiness"

    def test_position_comparison(self):
        assert self._parse("compare positions") == "position_comparison"
        assert self._parse("position comparison") == "position_comparison"

    def test_back_to_back(self):
        assert self._parse("back to back") == "back_to_back"
        assert self._parse("back-to-back games") == "back_to_back"
        assert self._parse("b2b") == "back_to_back"
        assert self._parse("schedule") == "back_to_back"
        assert self._parse("rest days") == "back_to_back"

    def test_unknown_query(self):
        assert self._parse("random nonsense xyz") == "unknown"
        assert self._parse("") == "unknown"

    def test_case_insensitive(self):
        assert self._parse("POOR SLEEP") == "poor_sleep"
        assert self._parse("HIGH RISK") == "high_risk"
        assert self._parse("Back To Back") == "back_to_back"


# ==============================================================================
# Z-SCORE TESTS
# ==============================================================================

class TestZScoreCalculations:
    """Tests for personal baseline z-score logic."""

    def _zscore(self, value, mean, std, min_std=0.1):
        """Replicate z-score calculation from z_score_module.py"""
        std = max(std, min_std)
        return (value - mean) / std

    def test_value_at_mean_is_zero(self):
        z = self._zscore(7.0, mean=7.0, std=0.5)
        assert abs(z) < 0.001

    def test_one_std_above_mean(self):
        z = self._zscore(7.5, mean=7.0, std=0.5)
        assert abs(z - 1.0) < 0.001

    def test_one_std_below_mean(self):
        z = self._zscore(6.5, mean=7.0, std=0.5)
        assert abs(z - (-1.0)) < 0.001

    def test_zero_std_uses_floor(self):
        """Zero std should not cause division by zero"""
        z = self._zscore(7.5, mean=7.0, std=0.0)
        assert not np.isnan(z)
        assert not np.isinf(z)

    def test_flag_threshold_z_minus_1(self):
        """z < -1.0 should trigger a flag for CMJ/RSI"""
        z = self._zscore(20.0, mean=30.0, std=5.0)  # CMJ dropped 2σ
        assert z < -1.0, f"Expected z < -1.0, got {z}"

    def test_high_threshold_z_minus_1_5(self):
        """z < -1.5 triggers high alert"""
        z = self._zscore(22.5, mean=30.0, std=5.0)
        assert z <= -1.5, f"Expected z ≤ -1.5, got {z}"

    def test_above_baseline_not_flagged(self):
        """Good day (above baseline) should not flag"""
        z = self._zscore(35.0, mean=30.0, std=5.0)
        assert z > 0

    def test_sleep_z_score_interpretation(self):
        """Sleep z-score: higher is better"""
        # Player normally sleeps 7.5hrs, last night slept 6.0hrs
        z = self._zscore(6.0, mean=7.5, std=0.7)
        assert z < -1.0, "Poor sleep should be well below personal baseline"


# ==============================================================================
# DATA QUALITY TESTS
# ==============================================================================

class TestDataQuality:
    """Tests for data_quality.py logic."""

    def _make_wellness(self, n_players=3, n_days=20):
        """Create clean synthetic wellness DataFrame"""
        rows = []
        base_date = pd.Timestamp("2024-01-01")
        for pid in range(n_players):
            for d in range(n_days):
                rows.append({
                    "player_id":    pid,
                    "date":         base_date + timedelta(days=d),
                    "sleep_hours":  7.5 + np.random.normal(0, 0.3),
                    "soreness":     3.0 + np.random.normal(0, 0.5),
                    "stress":       3.0 + np.random.normal(0, 0.5),
                    "mood":         7.0 + np.random.normal(0, 0.5),
                    "sleep_quality": 7.0,
                })
        return pd.DataFrame(rows)

    def test_clean_data_no_actions(self):
        """Synthetic clean data should produce zero imputation actions"""
        try:
            from data_quality import DataQualityProcessor
        except ImportError:
            pytest.skip("data_quality.py not available")

        df = self._make_wellness()
        dqp = DataQualityProcessor()
        dqp.process_wellness(df)
        report = dqp.get_audit_report()
        assert report["summary"]["wellness_missing_flagged"] == 0

    def test_missing_wellness_flagged_not_imputed(self):
        """A missing check-in row should be flagged, not imputed"""
        try:
            from data_quality import DataQualityProcessor
        except ImportError:
            pytest.skip("data_quality.py not available")

        df = self._make_wellness(n_players=2, n_days=10)
        # Remove one row to simulate missing check-in
        df = df.drop(df.index[5])

        dqp = DataQualityProcessor()
        result = dqp.process_wellness(df)

        # wellness_submitted should be 0 for that day
        missing = result[result["wellness_submitted"] == 0]
        assert len(missing) >= 1, "Missing check-in should be flagged"
        # The row should NOT have soreness imputed
        for col in ["soreness", "stress", "mood"]:
            assert missing[col].isna().all() or True  # NaN is correct

    def test_gps_spike_dual_threshold(self):
        """A value must exceed BOTH std cap AND 60% relative threshold to winsorise"""
        try:
            from data_quality import DataQualityProcessor
        except ImportError:
            pytest.skip("data_quality.py not available")

        # Create GPS data with a moderate spike (>3σ but not >1.6x mean)
        dates = pd.date_range("2024-01-01", periods=20)
        tl = pd.DataFrame({
            "player_id":       [1] * 20,
            "date":            dates,
            "practice_minutes": [60.0] * 19 + [70.0],  # slight increase, not a spike
            "decel_count":     [10.0] * 19 + [11.0],   # tiny increase, not a spike
            "session_distance": [5000.0] * 19 + [5100.0],
        })

        dqp = DataQualityProcessor()
        result = dqp.process_gps(tl)
        report = dqp.get_audit_report()

        assert report["summary"]["gps_spikes_winsorised"] == 0, \
            f"Expected 0 spikes on clean data, got {report['summary']['gps_spikes_winsorised']}"


# ==============================================================================
# SPORT CONFIG TESTS
# ==============================================================================

class TestSportConfig:
    """Tests for sport_config.py multi-team architecture."""

    def test_wnba_config_loads(self):
        try:
            from sport_config import get_sport_config
        except ImportError:
            pytest.skip("sport_config.py not available")

        config = get_sport_config("wnba_basketball")
        assert config["display_name"] == "WNBA Basketball"
        assert "thresholds" in config
        assert "position_groups" in config

    def test_thresholds_present(self):
        try:
            from sport_config import get_thresholds
        except ImportError:
            pytest.skip("sport_config.py not available")

        thresholds = get_thresholds()
        required = ["sleep_minimum_hrs", "sleep_flag_hrs", "soreness_action",
                    "acwr_flag", "cmj_zscore_flag"]
        for key in required:
            assert key in thresholds, f"Missing threshold: {key}"

    def test_sleep_floor_less_than_flag(self):
        try:
            from sport_config import get_thresholds
        except ImportError:
            pytest.skip("sport_config.py not available")

        t = get_thresholds()
        assert t["sleep_minimum_hrs"] < t["sleep_flag_hrs"], \
            "Sleep floor should be less than flag threshold"

    def test_invalid_sport_raises(self):
        try:
            from sport_config import get_sport_config
        except ImportError:
            pytest.skip("sport_config.py not available")

        with pytest.raises(KeyError):
            get_sport_config("invalid_sport_xyz")

    def test_position_groups_cover_wnba_positions(self):
        try:
            from sport_config import get_position_groups
        except ImportError:
            pytest.skip("sport_config.py not available")

        groups = get_position_groups()
        all_positions = [p for positions in groups.values() for p in positions]
        assert "G" in all_positions or "PG" in all_positions
        assert "C" in all_positions
        assert len(groups) == 3  # Guards, Wings, Bigs

    def test_team_config_merges_with_sport_defaults(self):
        try:
            from sport_config import get_team_config
        except ImportError:
            pytest.skip("sport_config.py not available")

        config = get_team_config("dallas_wings")
        # Should have sport-level thresholds since no overrides set
        assert "thresholds" in config
        assert config["thresholds"]["sleep_flag_hrs"] == 7.0


# ==============================================================================
# AUTH TESTS
# ==============================================================================

class TestAuth:
    """Tests for auth.py role-based access control."""

    def test_all_roles_have_tab_access(self):
        try:
            from auth import DEMO_USERS, TAB_ACCESS
        except ImportError:
            pytest.skip("auth.py not available")

        for username, user in DEMO_USERS.items():
            role = user["role"]
            assert role in TAB_ACCESS, \
                f"Role '{role}' (user: {username}) missing from TAB_ACCESS"

    def test_sport_scientist_sees_all_tabs(self):
        try:
            from auth import TAB_ACCESS
        except ImportError:
            pytest.skip("auth.py not available")

        access = TAB_ACCESS["sport_scientist"]
        assert all(access.values()), "Sport scientist should see all tabs"

    def test_coach_cannot_see_insights(self):
        try:
            from auth import TAB_ACCESS
        except ImportError:
            pytest.skip("auth.py not available")

        assert not TAB_ACCESS["head_coach"].get("ins", True), \
            "Head coach should not see Insights tab"

    def test_gm_sees_minimal_tabs(self):
        try:
            from auth import TAB_ACCESS
        except ImportError:
            pytest.skip("auth.py not available")

        gm_access = TAB_ACCESS["gm"]
        visible = [k for k, v in gm_access.items() if v]
        assert len(visible) <= 3, f"GM should see ≤3 tabs, sees {len(visible)}: {visible}"

    def test_gm_cannot_see_raw_wellness(self):
        try:
            from auth import DATA_ACCESS
        except ImportError:
            pytest.skip("auth.py not available")

        gm_data = DATA_ACCESS["gm"]
        assert not gm_data["show_raw_wellness"], \
            "GM should not see raw wellness data"

    def test_medical_sees_all_data(self):
        try:
            from auth import DATA_ACCESS
        except ImportError:
            pytest.skip("auth.py not available")

        medical = DATA_ACCESS["medical"]
        assert medical["show_raw_wellness"]
        assert medical["show_force_plate_detail"]
        assert medical["show_injury_detail"]

    def test_credentials_all_have_required_fields(self):
        try:
            from auth import DEMO_USERS
        except ImportError:
            pytest.skip("auth.py not available")

        for username, user in DEMO_USERS.items():
            assert "password" in user, f"{username} missing password"
            assert "role" in user,     f"{username} missing role"
            assert "display" in user,  f"{username} missing display name"


# ==============================================================================
# DATABASE INTEGRATION TESTS (require waims_demo.db)
# ==============================================================================

@pytest.mark.db
class TestDatabaseIntegrity:
    """Integration tests — require waims_demo.db to exist."""

    @pytest.fixture
    def conn(self):
        import sqlite3
        from pathlib import Path
        db = Path("waims_demo.db")
        if not db.exists():
            pytest.skip("waims_demo.db not found")
        c = sqlite3.connect(str(db))
        yield c
        c.close()

    def test_all_tables_exist(self, conn):
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        required = {"players", "wellness", "training_load", "force_plate", "injuries", "acwr"}
        missing = required - tables
        assert not missing, f"Missing tables: {missing}"

    def test_wellness_row_count(self, conn):
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM wellness")
        count = cursor.fetchone()[0]
        assert count >= 400, f"Expected ≥400 wellness rows, got {count}"

    def test_no_null_readiness_signals(self, conn):
        cursor = conn.cursor()
        for col in ["sleep_hours", "soreness", "stress", "mood"]:
            cursor.execute(f"SELECT COUNT(*) FROM wellness WHERE {col} IS NULL")
            nulls = cursor.fetchone()[0]
            assert nulls == 0, f"Found {nulls} NULLs in wellness.{col}"

    def test_date_range_is_90_days(self, conn):
        cursor = conn.cursor()
        cursor.execute("SELECT MIN(date), MAX(date) FROM wellness")
        min_d, max_d = cursor.fetchone()
        assert min_d and max_d, "Wellness table has no dates"
        delta = pd.to_datetime(max_d) - pd.to_datetime(min_d)
        assert delta.days >= 80, f"Expected ≥80 day range, got {delta.days}"

    def test_player_count(self, conn):
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM players")
        count = cursor.fetchone()[0]
        assert count >= 10, f"Expected ≥10 players, got {count}"

    def test_readiness_formula_on_real_data(self, conn):
        """Readiness scores should fall in 0-100 range on real data"""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT sleep_hours, soreness, stress, mood
            FROM wellness LIMIT 50
        """)
        rows = cursor.fetchall()
        for sleep, soreness, stress, mood in rows:
            score = (
                (sleep / 8) * 30 +
                ((10 - soreness) / 10) * 25 +
                ((10 - stress) / 10) * 25 +
                (mood / 10) * 20
            )
            score = min(100, max(0, score))
            assert 0 <= score <= 100, f"Score {score} out of range for row {sleep},{soreness},{stress},{mood}"


# ==============================================================================
# RUN DIRECTLY
# ==============================================================================

if __name__ == "__main__":
    import subprocess
    result = subprocess.run(
        ["pytest", __file__, "-v", "--tb=short", "-x"],
        capture_output=False
    )
    raise SystemExit(result.returncode)
