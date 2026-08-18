"""
WAIMS Rendering / Integration Tests
====================================
These drive the real running app via Streamlit's headless AppTest
harness -- catching the class of bug unit tests can't, because the app
was never actually rendered. Concretely: the Jump Testing comparison
card HTML-escaping bug (missing unsafe_allow_html=True) shipped
silently for a while because nothing here existed before; the test in
TestJumpTestingComparisonCards below is a direct regression test for it.

Both waims_demo.db (WNBA) and waims-mens/data/waims_arkansas.db
(Arkansas), plus both sports' models/*.pkl, are committed to the repo,
so these run against real data with no setup/generation step needed.

Run:
    pytest test_app_rendering.py -v
    pytest test_app_rendering.py -v --tb=short
"""

import os

import pytest
from streamlit.testing.v1 import AppTest

WNBA_USER = ("wnba_scientist", "wnba_sci")
MENS_USER = ("ark_scientist", "ark_sci")


def _boot(sport: str) -> AppTest:
    os.environ["WAIMS_SPORT"] = sport
    at = AppTest.from_file("dashboard.py")
    at.run(timeout=60)
    return at


def _login(at: AppTest, username: str, password: str) -> AppTest:
    at.text_input[0].input(username).run(timeout=60)
    at.text_input[1].input(password).run(timeout=60)
    at.button[0].click().run(timeout=60)
    return at


def _tab(at: AppTest, label: str):
    labels = [t.label for t in at.tabs]
    assert label in labels, f"Tab '{label}' not found -- available: {labels}"
    tab = at.tabs[labels.index(label)]
    tab.run(timeout=60)
    return tab


class TestLogin:
    def test_wnba_login_succeeds(self):
        at = _boot("wnba")
        _login(at, *WNBA_USER)
        assert not at.exception

    def test_mens_login_succeeds(self):
        at = _boot("mens")
        _login(at, *MENS_USER)
        assert not at.exception


class TestAthleteProfileRendering:
    """Also covers the per-sport threshold wiring from earlier today --
    if that regressed, the KeyErrors on a missing threshold key would
    surface here as an exception, not just a wrong-looking number."""

    def test_wnba_athlete_profile_renders(self):
        at = _boot("wnba")
        _login(at, *WNBA_USER)
        prof = _tab(at, "Athlete Profiles")
        prof.selectbox[0].select(prof.selectbox[0].options[0]).run(timeout=60)
        assert not at.exception

    def test_mens_athlete_profile_renders(self):
        at = _boot("mens")
        _login(at, *MENS_USER)
        prof = _tab(at, "Athlete Profiles")
        prof.selectbox[0].select(prof.selectbox[0].options[0]).run(timeout=60)
        assert not at.exception


class TestGamePerformanceRendering:
    def test_mens_advanced_metrics_renders(self):
        at = _boot("mens")
        _login(at, *MENS_USER)
        adv = _tab(at, "Advanced Metrics")
        assert not at.exception
        assert any("Roadmap" in e.label for e in adv.expander)

    def test_gp_tab_absent_for_wnba(self):
        """Game Performance only has data for Arkansas -- it should be
        hidden entirely on the WNBA side, not shown empty/broken."""
        at = _boot("wnba")
        _login(at, *WNBA_USER)
        labels = [t.label for t in at.tabs]
        assert "Game Performance" not in labels


class TestJumpTestingComparisonCards:
    """Regression test for the HTML-escaping bug the user found: raw
    HTML must render, never show up as literal visible text."""

    def test_comparison_card_has_no_leaked_html_text(self):
        at = _boot("mens")
        _login(at, *MENS_USER)
        jt = _tab(at, "Jump Testing")
        assert not at.exception
        # A markdown block containing real HTML tags MUST have allow_html=True,
        # or the tags render as visible literal text instead of being
        # interpreted -- exactly the bug this regression-tests for. Checking
        # the text alone (e.g. "starts with <div") is too blunt: plenty of
        # markdown blocks correctly use HTML with allow_html=True already.
        for m in jt.markdown:
            looks_like_html = "<div" in m.value or "<b>" in m.value or "<span" in m.value
            if looks_like_html:
                assert m.allow_html, (
                    f"HTML content without allow_html=True -- will render as literal text: {m.value[:120]!r}"
                )


class TestDataIntakeVendorLabels:
    """Regression test for the vendor-label fix -- VALD/VBS/Kinexon
    should be directly visible in the zone picker, not just implied by
    a generic auto-title-cased key."""

    def test_vendor_names_visible_in_zone_picker(self):
        at = _boot("mens")
        _login(at, *MENS_USER)
        di = _tab(at, "Data Intake")
        zone_picker = next(sb for sb in di.selectbox if "zone" in (sb.label or "").lower())
        options_text = " ".join(zone_picker.options)
        assert "VALD" in options_text
        assert "VBS" in options_text
        assert "Kinexon" in options_text


class TestAskTheWatchlist:
    """parse_query() lives inline in dashboard.py, which can't be
    import-tested directly (it's a full Streamlit script -- importing
    it executes the whole app). Driving the real Insights tab exercises
    the actual active code path end to end instead."""

    @pytest.mark.parametrize("query,expected_phrase", [
        ("poor sleep", "Poor Sleep"),
        ("high risk players", "High Risk"),
        ("who is ready", "Readiness"),
        ("back to back games", "Back To Back"),
    ])
    def test_query_classified_correctly(self, query, expected_phrase):
        at = _boot("wnba")
        _login(at, *WNBA_USER)
        _tab(at, "Insights")
        at.session_state["query_to_run"] = query
        at.run(timeout=60)
        assert not at.exception
        # Re-fetch the tab reference after the rerun -- the one from _tab()
        # above is a snapshot from before session_state was set, and won't
        # reflect the query result.
        ins = at.tabs[[t.label for t in at.tabs].index("Insights")]
        info_texts = [i.value for i in ins.info]
        assert any(expected_phrase in v for v in info_texts), (
            f"Expected an 'Understood as: {expected_phrase}' message, got: {info_texts}"
        )
