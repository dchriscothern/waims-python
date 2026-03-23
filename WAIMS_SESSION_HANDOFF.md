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
| `research_context.py` | Planned richer basketball risk-context module (not present in current V1 repo) |
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
| `.github/workflows/retrain_models.yml` | Sunday 6am UTC | Retrains RF model, commits .pkl files |

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
- [x] sport_config.py built — WNBA + Springbok rugby configured. Set ACTIVE_SPORT to switch context
- [ ] Test back-to-back query against actual demo database schedule table
- [ ] Upload updated coach_command_center.py to verify Windows syntax fix still clean

---
*Last updated: March 2026. All V1 demo data is synthetic.*


## New Modules Added (This Session)

### auth.py — Role-Based Login System
- Login screen renders before anything else — unauthenticated users see only the login page
- 5 roles: Head Coach, Asst. Coach, Sport Scientist, Medical/AT, General Manager
- `TAB_ACCESS` dict controls tab visibility per role
- `DATA_ACCESS` dict controls field-level data visibility
- Sidebar shows user badge (role + name) and Sign Out button
- GM gets availability-only Command Center view
- Demo credentials shown on login screen

| Username | Password | Role |
|---|---|---|
| coach | coach123 | Head Coach |
| acoach | acoach123 | Asst. Coach |
| scientist | sci123 | Sport Scientist |
| medical | med123 | Medical / AT |
| gm | gm123 | General Manager |

### data_quality.py — Tiered Imputation with Audit Log
Tiered strategy — every decision explicit and logged:
- Wellness missing → flag only (wellness_submitted=0 feature). NOT imputed
- B2B missing → additional b2b_missing flag
- Force plate → LOCF up to 3 days, staleness flag after
- GPS spikes >3σ → winsorise, preserve original in *_original column
- Sleep ≤2 days gap → personal 14-day rolling mean
- Sleep >2 days gap → flag only
- ACWR <7 days load data → flag as unreliable
- Full audit log viewable in Insights tab → Data Quality expander
- `DataQualityProcessor` class + `show_data_quality_report()` for Streamlit

### model_validation.py — Full Julius.ai Validation Recipe
- `generate_walk_forward_splits()` — 45-day train / 15-day validate rolling
- `baseline_acwr()`, `baseline_soreness_zscore()`, `baseline_acute_load()` — baselines to beat
- `precision_at_k()` — top-K flags per day vs actual injuries with lookahead window
- `lead_time_analysis()` — days before injury model first flagged the player
- `per_player_performance()` — catches "good overall, terrible for 3 players" problems
- `day_to_day_stability()` — flags score whipsaw >20pts without wellness change
- `show_validation_framework_streamlit()` — full framework docs in Insights tab expander

---

## Updated File Inventory (additions)

| File | Purpose |
|---|---|
| `auth.py` | Role-based login — 5 roles, tab + data access control |
| `sport_config.py` | Multi-sport config: WNBA basketball + Springbok rugby. Thresholds, GPS metrics, positions, compliance per sport |
| `data_quality.py` | Tiered imputation with full audit log |
| `model_validation.py` | Walk-forward validation, Precision@K, lead-time, baselines |


---
*Last updated: March 2026. All V1 demo data is synthetic.*

## Corrections & Updates (Latest Session)

### sport_config.py — Rebuilt (WNBA basketball only)
- **Springbok Analytics** is a Second Spectrum MRI (Match & Rotation Intelligence) platform
  used by WNBA/NBA teams including Dallas Wings — it is a V2/V3 DATA SOURCE, not a sport config
- Rugby config removed entirely — was incorrect
- Now contains: WNBA basketball sport defaults + TEAM_CONFIGS for Dallas Wings
- To add another WNBA team: add entry to TEAM_CONFIGS with threshold overrides
- Positional GPS norms documented as V2 gap (Guards/Wings/Bigs decel profiles differ)

### coach_command_center.py — Morning brief squad language fixed
- "Full squad available today. 6 players fully ready" → now uses percentage
- "Full squad" only when 100% ready. "Squad in good shape" at 75%+. Actual X/Y count otherwise

### data_quality.py — GPS false positive fixed
- Dual threshold: value must exceed BOTH std-based cap AND be 60%+ above rolling mean
- Prevents false positives on low-variance integer columns (decel_count etc.)
- Synthetic demo database should now show 0 GPS winsorisations

### WAIMS_Coach_Overview.pdf — Rebuilt (single page)
- Removed "Why the Thresholds Are Set This Way" section (sport scientist content)
- Now single page: traffic lights, Command Center features, role access, B2B, What WAIMS Is Not

### RESEARCH_FOUNDATION.md updates
- Multi-sport section corrected: Springbok Analytics = MRI platform (data source), not a sport
- Sleep research broadened beyond basketball — Walsh 2021 covers all athletes
- Male vs female sleep differences documented
- Recent sleep SR/reviews added (Fullagar 2015, Charest & Grandner 2021, Doherty 2019)
- V3 note: personalised sleep recs from genetic/biomarker data — user has research to upload
- Positional GPS norms gap documented (V2 feature)

### Key principles added
- **Individualized positional thresholds**: Guards vs Bigs have structurally different
  decel/load profiles. V2 uses position-group z-scores, not whole-team baseline.
  sport_config.py position_groups already provide the grouping structure.
- **Sleep research scope**: core thresholds are population-independent (Walsh 2021).
  Basketball/WNBA-specific research (Mah 2011, Pimenta 2026) informs the 9h target.
  V3: personalised recommendations from biomarker/genetic data (research to be uploaded).

### Do NOT add to existing repo
- Stock ticker / live score display concept
- Athlete-facing gamification / biz plan → new separate repo
- Athlete personal recommendations module → V3, new module when research is ready
