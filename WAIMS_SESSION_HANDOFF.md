# WAIMS — Session Handoff Context
Paste this into a fresh Claude Sonnet window to resume development.

---

## What WAIMS Is

WAIMS (Wellness & Athlete Injury Management System) — Python + Streamlit athlete monitoring dashboard.
Dallas Wings-inspired WNBA demo roster. 12 players, 90 days, ~10,000+ synthetic data points.
Portfolio tool demonstrating sport science + software development capability.
Two audiences: **coaches** (traffic lights, plain English) and **sport scientists** (analytics, evidence).

**Stack:** Python, Streamlit, pandas, SQLite (demo), Random Forest (scikit-learn), GitHub Actions automation.

---

## Current File Inventory (all in repo root unless noted)

| File | Purpose |
|---|---|
| `dashboard.py` | Main app — 8 tabs |
| `coach_command_center.py` | Tab 1: Coach Command Center |
| `athlete_profile_tab.py` | Tab 3: Athlete Profiles |
| `improved_gauges.py` | Player card HTML components |
| `z_score_module.py` | Personal baseline z-score calculations |
| `research_citations.py` | Research Foundation display |
| `research_context.py` | Basketball-specific risk context |
| `research_monitor.py` | Automated PubMed + RSS search |
| `research_merge.py` | Safe merge for extended lookback |
| `research_topics_config.py` | PubMed query reference config |
| `research_log.json` | Evidence review inbox (auto-populated) |
| `train_models.py` | RF model training |
| `generate_database.py` | Synthetic demo data generator |
| `waims_demo.db` | SQLite database |
| `models/injury_risk_model.pkl` | Trained RF model |
| `.github/workflows/research_monitor.yml` | Weekly PubMed/RSS automation |
| `.github/workflows/retrain_models.yml` | Weekly model retrain |
| `README.md` | Full project documentation |
| `README_PYTHON.md` | Python-specific setup |
| `RESEARCH_FOUNDATION.md` | Evidence citations + policy |
| `WAIMS_GLOBAL_CONTEXT.md` | This file / AI session context |
| `SETUP_GUIDE.md` | Installation guide |
| `LEARNING_GUIDE.md` | Educational walkthrough |
| `WAIMS_Roadmap_2026.docx` | Product roadmap Word doc |
| `WAIMS_Coach_Overview.pdf` | One-page coach/GM PDF |
| `WAIMS_SportScientist_Overview.pdf` | Two-page sport scientist PDF |
| `assets/branding/waims_run_man_logo.png` | Logo |
| `assets/photos/` | Athlete placeholder photos |

---

## 8-Tab Architecture

1. **Command Center** (coach) — morning brief, traffic lights, positional group strip, minutes cap labels, hidden fatigue flag
2. **Today's Readiness** (analyst) — battery view, z-score personal baseline comparison
3. **Athlete Profiles** (sport scientist) — speedometer gauges, pill meters, 7-day trends, basketball risk context
4. **Trends & Load** (both) — GPS + wellness merged, rolling averages
5. **Jump Testing** (sport scientist) — CMJ/RSI vs personal baseline, force plate trends
6. **Availability & Injuries** (GM/medical) — injury log, pre-injury wellness
7. **Forecast** (both) — 7-day risk watchlist, load projection, RF model details
8. **Insights** (sport scientist) — Ask the Watchlist, model validation, evidence review, correlations

---

## Readiness Formula

| Signal | Weight | Threshold | Evidence |
|---|---|---|---|
| CMJ z-score (30-day baseline) | 35 pts | z<-1.0 flag | Gathercole 2015; Janetzki 2023 SR/meta |
| RSI-Modified z-score | 25 pts | z<-1.0 flag | Gathercole 2015 (elite female rugby 7s) |
| Sleep hours | 20 pts | <7h flag; <6h hard floor | Walsh 2021 BJSM |
| Soreness (0-10) | 10 pts | >7 requires action | Hulin et al. 2016 |
| Mood + Stress | 10 pts | combined | Saw et al. 2016 SR |
| ACWR | 0 pts | contextual flag only | Impellizzeri 2020 |

**CMJ height** predicts sprint/acceleration (Janetzki 2023). **RSI-Mod** measures reactive strength / fatigue sensitivity (Gathercole 2015). Different signals — both used by NBA/WNBA. **HRV excluded from V1** — standardisation challenges, non-significant in Janetzki 2023.

---

## Key Principles

- **Docs updated every session**: README, RESEARCH_FOUNDATION, WAIMS_GLOBAL_CONTEXT, roadmap, PDFs
- **Evidence gate**: No threshold change without meta-analysis or systematic review (Orlando Magic framework)
- **Context layer**: Thresholds set by research, adjusted by context. Basketball-specific: multi-directional decel load, WNBA pace/schedule, positional differentiation, female physiology. Calibrated via coach/medical/sport science collaboration — no silos
- **Audience separation**: Coaches see traffic lights only. Raw wellness scores not shown to coaches. Sidebar panels inappropriate for Evidence Review (coaches see Command Center)
- **Data governance** (#1 real-team priority): Coaches → traffic lights + scores. Medical/AT → full health data. GM/FO → availability only. V2 needs RBAC, encryption, audit logs, consent, BAA, WNBA CBA legal review. V1 = synthetic data, N/A
- **Sportsmith**: Manual weekly review ($13/month). No scraping
- **Sports Science AI** (sportscienceai.com): Recommended for V2/real-team — purpose-built, citations only, weekly DB updates, replaces manual gap searches alongside automated PubMed monitor
- **Claude model**: Sonnet for iterative dev work

---

## Coach Command Center Features (V1.1)

- **Positional Group Readiness Strip**: Guards / Wings / Bigs averages above roster cards
- **Minutes Cap labels**: Cumulative 4-day minutes on each player card. Flag at >120 min/4d
- **Hidden Fatigue Flag**: READY player whose score is trending down under high load
- **Coach language**: "Heavy legs this week" not "high cumulative load". "Consider" not "Protect". "Your call on minutes" always preserved
- **Morning brief**: 3-bullet plain English summary

---

## Evidence Review System

- **Purpose**: Forward-looking inbox only. Foundational papers in RESEARCH_FOUNDATION.md
- **Sources**: PubMed (10 targeted queries, automated weekly), Martin Buchheit RSS, SPSR, BJSM
- **Decision ladder**: PENDING → Watchlist → Integrated | Rejected
- **Gate levels**: CANDIDATE (meta/SR) → REVIEW (basketball-specific) → WATCHLIST (cohort) → BACKGROUND
- **Extended lookback workflow**: `python research_monitor.py --days 730 --output research_log_extended.json` then `python research_merge.py`
- **Policy**: No threshold change without meta-analysis support

---

## Key Research Integrated

| Paper | Key Finding | WAIMS Use |
|---|---|---|
| Janetzki et al. 2023 (165-study SR/meta) | CMJ height → sprint (r=0.69, p=.00, only sig. finding). HRV, biomarkers, sub-max HR all non-sig | Validates CMJ height weight; supports HRV exclusion from V1 |
| Gathercole et al. 2015 | RSI-Mod more sensitive than CMJ height for overreach detection in elite female athletes | RSI-Mod 25pts in formula |
| Walsh et al. 2021 BJSM | Sleep consensus: 7h min, 9h target | Sleep 20pts, thresholds |
| Saw et al. 2016 (56-study SR) | Subjective wellness trumps objective measures | Mood/stress/soreness in formula |
| Boskovic et al. 2024 (GPS 3.0) | GPS = locomotor only; decel count most relevant basketball metric | GPS framing in Trends tab |
| Pimenta et al. 2026 (SR/meta, WNBA) | Sleep extension +1.5h → 12-18% performance gain | Sleep as #1 intervention |
| Mah 2011 | Sleep extension RCT in basketball players | Sleep research context |
| Impellizzeri 2020 BJSM | ACWR limitations | ACWR = flag only, no score weight |
| Charest & Grandner 2021 | Travel + circadian disruption, eastward penalty | Travel direction note (V2) |

---

## Automation (GitHub Actions)

| Workflow | Schedule | Purpose |
|---|---|---|
| `research_monitor.yml` | Monday 8am UTC | PubMed + RSS search, commits to research_log.json |
| `retrain_models.yml` | Sunday 6am UTC | Retrains RF model, commits .pkl files |

Setup: push `.github/workflows/` files to repo. `GITHUB_TOKEN` automatic — no config needed.

---

## Ask the Watchlist — Supported Queries

`poor sleep` | `high risk` | `readiness` | `compare positions` | `back to back` / `b2b` / `schedule` / `rest`

Back-to-back query added this session — was returning "unknown" before fix.

---

## V2 / V3 Roadmap Items

**V2 (production-ready):**
- Live APIs: Kinexon, ForceDecks, wellness app
- Second Spectrum optical tracking (WNBA 2024)
- Eastward/westward circadian travel penalty
- Menstrual phase CMJ/RSI adjustment (WHSP / Bruinvels 2017)
- OUT vs GTD availability distinction + Projected Impact squad toggle
- Data governance: RBAC, encryption, audit logs, consent protocol, BAA, WNBA CBA review
- ML validation: walk-forward splits, PR-AUC, Precision@K, lead-time analysis
- Sports Science AI integration (sportscienceai.com)

**V3 (future):**
- MCP server architecture for Kinexon, ForceDecks, Slack, Second Spectrum
- Drill-level GPS tagging via PlayerMaker/Kinexon timestamp-gating
- Athlete-facing app

---

## Bugs Fixed (This and Previous Sessions)

- `NameError` for `_sleep_v` — variable scope issue in coach_command_center.py
- `UnicodeEncodeError` in HTML generation on Windows — UTF-8 fix
- Deprecated `use_container_width` → `width='stretch'`
- pandas GroupBy deprecation → `include_groups=False`
- `SyntaxError` from apostrophe in "She's" → replaced with "She has"
- Paper title truncation `[:100]` → `[:200]` with `word-wrap:break-word`
- RSS duplicate dedup fix in research_monitor.py (hash-based ID)
- Back-to-back query returning "unknown" → parse_query now handles b2b/schedule/rest

---

## Pending / Not Yet Done

- [ ] Verify Saw et al. 2016 citation is the correct 56-study SR version
- [ ] Add Stojanovic 2025 basketball meta formally to RESEARCH_FOUNDATION.md
- [ ] Hormonal cycle / menstrual phase research (Bruinvels 2017, WHSP) before V2 feature
- [ ] Test back-to-back query against actual demo database schedule table
- [ ] Upload updated coach_command_center.py to verify Windows syntax fix still clean

---
*Last updated: March 2026. All V1 demo data is synthetic.*
