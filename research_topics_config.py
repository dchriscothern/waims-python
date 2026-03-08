"""
research_topics_config.py
==========================
Tightened PubMed search topics for WAIMS evidence monitor.
Replace the SEARCH_TOPICS list in research_monitor.py with this.

Philosophy:
  - Sport science and performance monitoring only
  - Female athlete / basketball specificity where possible
  - No broad clinical medicine terms that flood results with irrelevant papers
  - Each query is narrow enough that most results will be relevant

Usage in research_monitor.py:
    from research_topics_config import SEARCH_TOPICS, POST_FILTER_TERMS
"""

# ==============================================================================
# PUBMED SEARCH QUERIES
# These replace the original broad topic list in research_monitor.py
# Each is a targeted PubMed query — use field tags for precision
# ==============================================================================

SEARCH_TOPICS = [

    # ── SLEEP & RECOVERY ──────────────────────────────────────────────────────
    # Narrow to athletes — avoids clinical sleep disorder papers
    {
        "topic": "sleep_athlete_performance",
        "query": '(sleep[Title/Abstract]) AND (athlete[Title/Abstract] OR "sport performance"[Title/Abstract]) AND (injury[Title/Abstract] OR recovery[Title/Abstract] OR readiness[Title/Abstract])',
        "waims_relevance": "Sleep threshold evidence (Walsh 2021 baseline)",
        "min_quality_gate": "WATCHLIST",  # single studies → watchlist; SR/meta → CANDIDATE
    },

    # ── TRAINING LOAD & INJURY RISK ───────────────────────────────────────────
    # Avoids ACWR papers unless they have new methodology
    {
        "topic": "training_load_injury",
        "query": '("training load"[Title/Abstract] OR "workload"[Title/Abstract]) AND (injury[Title/Abstract] OR "injury risk"[Title/Abstract]) AND (basketball[Title/Abstract] OR athlete[Title/Abstract])',
        "waims_relevance": "Load-injury relationship; ACWR validation",
        "min_quality_gate": "WATCHLIST",
    },

    # ── FORCE PLATE / NEUROMUSCULAR MONITORING ────────────────────────────────
    {
        "topic": "cmj_neuromuscular_monitoring",
        "query": '("countermovement jump"[Title/Abstract] OR "CMJ"[Title/Abstract] OR "reactive strength index"[Title/Abstract]) AND (fatigue[Title/Abstract] OR monitoring[Title/Abstract] OR readiness[Title/Abstract])',
        "waims_relevance": "CMJ/RSI threshold evidence (Gathercole 2015 baseline)",
        "min_quality_gate": "WATCHLIST",
    },

    # ── GPS / PHYSICAL MONITORING ─────────────────────────────────────────────
    # Explicitly basketball-focused to avoid soccer-only papers
    {
        "topic": "gps_basketball_load",
        "query": '(GPS[Title/Abstract] OR "player load"[Title/Abstract] OR "accelerometer"[Title/Abstract]) AND (basketball[Title/Abstract] OR "team sport"[Title/Abstract]) AND (monitoring[Title/Abstract] OR load[Title/Abstract])',
        "waims_relevance": "GPS metrics, decel monitoring, player load thresholds",
        "min_quality_gate": "WATCHLIST",
    },

    # ── DECELERATION SPECIFICALLY ─────────────────────────────────────────────
    # Key signal in WAIMS — deserves its own query
    {
        "topic": "deceleration_injury_risk",
        "query": '(deceleration[Title/Abstract] OR "high-speed deceleration"[Title/Abstract]) AND (injury[Title/Abstract] OR "ACL"[Title/Abstract] OR "hamstring"[Title/Abstract]) AND (sport[Title/Abstract] OR athlete[Title/Abstract])',
        "waims_relevance": "Decel as primary GPS injury signal",
        "min_quality_gate": "WATCHLIST",
    },

    # ── FEMALE ATHLETE SPECIFIC ───────────────────────────────────────────────
    {
        "topic": "female_athlete_monitoring",
        "query": '("female athlete"[Title/Abstract] OR "women\'s basketball"[Title/Abstract] OR "female basketball"[Title/Abstract]) AND (load[Title/Abstract] OR monitoring[Title/Abstract] OR recovery[Title/Abstract] OR readiness[Title/Abstract] OR injury[Title/Abstract])',
        "waims_relevance": "Female-specific thresholds — core WAIMS design principle",
        "min_quality_gate": "WATCHLIST",
    },

    # ── MENSTRUAL CYCLE / HORMONAL ────────────────────────────────────────────
    # Narrow to performance relevance — avoids pure clinical endocrinology
    {
        "topic": "menstrual_cycle_performance",
        "query": '("menstrual cycle"[Title/Abstract] OR "hormonal"[Title/Abstract]) AND ("athletic performance"[Title/Abstract] OR "injury risk"[Title/Abstract] OR "neuromuscular"[Title/Abstract] OR "ACL"[Title/Abstract])',
        "waims_relevance": "Menstrual cycle phase adjustment — V2 feature",
        "min_quality_gate": "WATCHLIST",
    },

    # ── WELLNESS QUESTIONNAIRE VALIDITY ──────────────────────────────────────
    {
        "topic": "wellness_monitoring_validity",
        "query": '("wellness questionnaire"[Title/Abstract] OR "subjective wellness"[Title/Abstract] OR "athlete monitoring"[Title/Abstract]) AND (valid[Title/Abstract] OR reliab[Title/Abstract] OR sensitiv[Title/Abstract])',
        "waims_relevance": "Validity of subjective monitoring tools (Saw 2016 baseline)",
        "min_quality_gate": "WATCHLIST",
    },

    # ── BASKETBALL-SPECIFIC LOAD ──────────────────────────────────────────────
    {
        "topic": "basketball_load_performance",
        "query": '(basketball[Title]) AND ("training load"[Title/Abstract] OR "game load"[Title/Abstract] OR "back-to-back"[Title/Abstract] OR "schedule"[Title/Abstract] OR "fatigue"[Title/Abstract])',
        "waims_relevance": "Basketball-specific load norms and schedule effects",
        "min_quality_gate": "WATCHLIST",
    },

    # ── READINESS / RETURN TO PLAY ────────────────────────────────────────────
    {
        "topic": "readiness_return_to_play",
        "query": '("return to play"[Title/Abstract] OR "return to sport"[Title/Abstract] OR "readiness"[Title/Abstract]) AND (criteria[Title/Abstract] OR assessment[Title/Abstract] OR monitoring[Title/Abstract]) AND (basketball[Title/Abstract] OR athlete[Title/Abstract])',
        "waims_relevance": "Return to play criteria and readiness assessment",
        "min_quality_gate": "WATCHLIST",
    },

]

# ==============================================================================
# POST-FETCH FILTER
# Applied AFTER PubMed returns results — catches any clinical noise that
# slipped through the query
# ==============================================================================

POST_FILTER_TERMS = {

    # Title must contain at least one of these (sport relevance check)
    "title_must_include_one_of": [
        "athlete", "sport", "basketball", "player", "training", "exercise",
        "physical", "performance", "fitness", "load", "fatigue", "recovery",
        "sleep", "jump", "gps", "monitoring", "readiness", "injury",
        "female", "women", "wnba", "nba",
    ],

    # Paper is rejected if title contains any of these
    "title_must_exclude": [
        "surgery", "surgical", "operative", "pharmacol", "drug trial",
        "placebo", "biopsy", "histolog", "patholog", "radiology",
        "cancer", "tumor", "oncol", "cardiac arrest", "sepsis",
        "pediatric patient", "hospital admission", "inpatient",
        "anesthesia", "post-operative", "preoperative",
        "clinical trial", "randomized controlled", "double blind",
        # clinical rehab (not sport rehab)
        "physical therapy patient", "occupational therapy",
    ],
}

# ==============================================================================
# QUALITY GATE RULES
# Maps evidence type → gate status in research_log.json
# ==============================================================================

QUALITY_GATE_RULES = {
    # These abstract keywords suggest high-quality evidence
    "CANDIDATE": [
        "systematic review", "meta-analysis", "meta analysis",
        "pooled analysis", "cochrane",
    ],
    # These suggest good but single study
    "REVIEW": [
        "narrative review", "scoping review", "expert consensus",
        "consensus statement",
    ],
    # Everything else defaults to ASSESS or WATCHLIST
    "WATCHLIST": [
        "cohort study", "prospective", "longitudinal",
        "observational", "cross-sectional",
    ],
    "BACKGROUND": [
        "case study", "case report", "pilot study",
        "letter to the editor", "commentary",
    ],
}

# ==============================================================================
# HOW TO USE IN research_monitor.py
# ==============================================================================
"""
1. Add this file to your project directory.

2. In research_monitor.py, replace:
      SEARCH_TOPICS = [
          "sleep injury risk athletes",
          "training load monitoring",
          ...
      ]
   
   With:
      from research_topics_config import SEARCH_TOPICS, POST_FILTER_TERMS, QUALITY_GATE_RULES

3. Update your PubMed fetch loop to use the "query" field from each topic dict
   instead of building queries from plain strings.

4. After fetching, apply POST_FILTER_TERMS to drop irrelevant results before
   they hit research_log.json.

5. Apply QUALITY_GATE_RULES to set gate_status on each paper automatically.

This will substantially reduce clinical noise and ensure the evidence review
tab shows only sport science relevant papers.
"""
