# WAIMS Global Context
# Used by Claude (Sonnet) to resume development sessions.
# Paste this at the start of a new session.

## What WAIMS Is
WAIMS (Wellness & Athlete Injury Management System) — Python + Streamlit athlete monitoring dashboard.
Dallas Wings-inspired WNBA demo roster. 12 players, 90 days, ~10,000+ synthetic data points.
Portfolio tool demonstrating sport science + software development capability.
Two audiences: **coaches** (traffic lights, plain English) and **sport scientists** (analytics, evidence).

Stack: Python, Streamlit, pandas, SQLite (demo), Random Forest (scikit-learn), GitHub Actions.

## Complete File Inventory

### Core Application
| File | Purpose |
|---|---|
| `dashboard.py` | Main app — 8 role-aware tabs |
| `auth.py` | Role-based login — 5 roles, tab + data access control |
| `coach_command_center.py` | Tab 1: Coach Command Center |
| `athlete_profile_tab.py` | Tab 3: Athlete Profiles |
| `improved_gauges.py` | Player card HTML components |
| `z_score_module.py` | Personal baseline z-score calculations |
| `research_citations.py` | Research Foundation Streamlit display |
| `research_context.py` | Basketball-specific risk context |
| `correlation_explorer.py` | Signal correlations tab |

### Data & ML
| File | Purpose |
|---|---|
| `data_quality.py` | Tiered imputation + audit log — DataQualityProcessor class |
| `model_validation.py` | Walk-forward validation, Precision@K, lead-time, baselines |
| `sport_config.py` | Multi-team config: WNBA thresholds, positions, GPS, compliance |
| `train_models.py` | RF model training |
| `generate_database.py` | Synthetic demo data generator |
| `waims_demo.db` | SQLite database |
| `models/injury_risk_model.pkl` | Trained RF model |

### Research & Evidence
| File | Purpose |
|---|---|
| `research_monitor.py` | Automated PubMed + RSS search |
| `research_merge.py` | Safe merge for extended lookback |
| `research_topics_config.py` | PubMed query reference config |
| `research_log.json` | Evidence review inbox (auto-populated) |

### Testing & Quality
| File | Purpose |
|---|---|
| `healthcheck.py` | Pre-demo diagnostic — 10 checks, terminal + Streamlit mode |
| `test_waims.py` | Unit tests — 34 passing (readiness, queries, z-score, auth, data quality) |
| `pytest.ini` | Pytest config — registers db mark |
| `requirements.txt` | Python dependencies |

### Automation (GitHub Actions)
| File | Purpose |
|---|---|
| `.github/workflows/ci.yml` | CI — runs unit tests on every push |
| `.github/workflows/research_monitor.yml` | Monday 8am — PubMed/RSS search |
| `.github/workflows/retrain_models.yml` | Sunday 6am — RF model retrain |

### Documentation
| File | Purpose |
|---|---|
| `README.md` | Full project documentation |
| `README_PYTHON.md` | Python-specific setup |
| `RESEARCH_FOUNDATION.md` | Evidence citations + policy + data quality + validation |
| `WAIMS_GLOBAL_CONTEXT.md` | This file |
| `SETUP_GUIDE.md` | Installation guide |
| `LEARNING_GUIDE.md` | Educational walkthrough |
| `WAIMS_Roadmap_2026.docx` | Product roadmap |
| `WAIMS_Coach_Overview.pdf` | One-page coach/GM PDF |
| `WAIMS_SportScientist_Overview.pdf` | Two-page sport scientist PDF |
| `WAIMS_Demo_CheatSheet.docx` | 10-minute demo script |
| `assets/branding/waims_run_man_logo.png` | Logo |

## 8-Tab Architecture (role-aware)

| Tab | Key | Audience | Key Features |
|---|---|---|---|
| Command Center | cc | Coach/GM | Morning brief, traffic lights, positional strip, minutes labels, hidden fatigue flag, export buttons |
| Today's Readiness | rd | Analyst | Battery view, z-score baseline comparison |
| Athlete Profiles | ap | Sport Scientist | Speedometer gauges, pill meters, 7-day trends, basketball risk context |
| Trends & Load | tr | Both | GPS + wellness merged, rolling averages |
| Jump Testing | jt | Sport Scientist | CMJ/RSI vs personal baseline, force plate trends |
| Availability & Injuries | inj | GM/Medical | Injury log, pre-injury wellness |
| Forecast | fc | Both | 7-day risk watchlist, load projection, RF model |
| Insights | ins | Sport Scientist | Ask the Watchlist, data quality audit, model validation, evidence review, correlations |

## Login System
5 roles: Head Coach (coach/coach123) · Asst. Coach (acoach/acoach123) ·
Sport Scientist (scientist/sci123) · Medical/AT (medical/med123) · GM (gm/gm123)
- Coaches: Command Center, Readiness, Trends, Injuries, Forecast. No raw wellness.
- Sport Scientist/Medical: All 8 tabs, full data
- GM: Command Center (summary only) + Availability

## Readiness Formula
| Signal | Weight | Threshold | Evidence |
|---|---|---|---|
| CMJ z-score (30-day) | 35 pts | z<-1.0 flag | Gathercole 2015; Janetzki 2023 |
| RSI-Modified z-score | 25 pts | z<-1.0 flag | Gathercole 2015 |
| Sleep hours | 20 pts | <7h flag; <6h floor | Walsh 2021 BJSM |
| Soreness | 10 pts | >7 action | Hulin 2016 |
| Mood + Stress | 10 pts | combined | Saw et al. 2016 SR |
| ACWR | 0 pts | flag only | Impellizzeri 2020 |

CMJ height → sprint/acceleration (Janetzki 2023). RSI-Mod → fatigue sensitivity (Gathercole 2015).
HRV excluded V1 — non-significant in Janetzki 2023 meta.

## Key Principles
- **Docs updated every session**: README, RESEARCH_FOUNDATION, this file, roadmap, PDFs
- **Evidence gate**: No threshold change without meta-analysis or SR (Orlando Magic framework)
- **Context layer**: Thresholds set by research, adjusted by context. Basketball-specific calibration.
- **Audience separation**: Coaches see traffic lights. Raw wellness restricted to medical/sport sci.
- **Data governance**: Role-based login built. V2: SSO (Okta/Azure AD), encryption, audit logs, WNBA CBA review.
- **Data quality**: Tiered imputation — missing wellness flagged NOT imputed. Full audit log.
- **Model validation**: Walk-forward + player holdout. PR-AUC headline. Precision@K top 3/day. Lead-time target 3-7 days.
- **Testing**: 34 unit tests passing. CI runs on every push. Run healthcheck.py before demos.
- **Springbok Analytics**: Second Spectrum MRI platform (data source V2/V3) — NOT a sport config.
- **No rugby config**: sport_config.py is WNBA basketball + Dallas Wings only.
- **Sports Science AI** (sportscienceai.com): Recommended for V2 real-team research monitoring.
- **Claude model**: Sonnet for iterative dev work.

## Automation
| Workflow | Trigger | Purpose |
|---|---|---|
| ci.yml | Push to main | pytest test_waims.py -k "not db" |
| research_monitor.yml | Monday 8am UTC | PubMed + RSS, commits research_log.json |
| retrain_models.yml | Sunday 6am UTC | RF retrain, commits .pkl |

## V2 / V3 Roadmap
**V2:** Live APIs (Kinexon, ForceDecks), Second Spectrum / Springbok Analytics, eastward travel penalty,
menstrual phase adjustment (WHSP), OUT vs GTD distinction, SSO auth, walk-forward ML validation,
positional GPS norms, Sports Science AI, personalised sleep recs (biomarker/genetic data — user has research).

**V3:** MCP servers for Kinexon/ForceDecks/Slack/Second Spectrum, drill-level GPS, athlete-facing app.

**Do NOT add to this repo:** Stock ticker concept, athlete gamification biz plan (separate repo),
personalised recommendations module (V3, new module when research uploaded).

## Bugs Fixed
- NameError _sleep_v — variable scope in coach_command_center.py
- UnicodeEncodeError Windows — UTF-8 fix
- use_container_width deprecated → width='stretch' (all non-button calls)
- pandas GroupBy deprecation → include_groups=False
- SyntaxError apostrophe in "She's" → "She has"
- Paper title truncation [:100] → [:200]
- RSS duplicate dedup — hash-based ID in research_monitor.py
- Back-to-back query returning "unknown" — parse_query fixed
- GPS false positive winsorise — dual threshold (>3σ AND >60% above mean)
- Morning brief "Full squad" with 6/12 players — now uses percentage
- Tab indentation bug — tr/jt/inj/fc/ins content at wrong indent level (fixed)
- Z-score boundary test — <= not < for exact boundary

## Pending
- [ ] Verify Saw et al. 2016 citation is the 56-study SR version
- [ ] Add Stojanovic 2025 basketball meta to RESEARCH_FOUNDATION.md
- [ ] Hormonal cycle research (Bruinvels 2017, WHSP) before V2 feature
- [ ] Test B2B query against actual demo schedule table
- [ ] Auth tests skip in CI (Streamlit not available) — expected, documented
