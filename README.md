# WAIMS — Wellness & Athlete Injury Management System

**Professional Athlete Monitoring Dashboard**  
Built with Python · Streamlit · SQLite · Plotly · Random Forest · Generative AI

> Dallas Wings-inspired demo — 90 days · 12 players · anonymized roster  
> Live ESPN game data (2019–2025) · Evidence-based thresholds · Walsh 2021 · Gabbett 2016

---

## Quick Start

```bash
pip install -r requirements.txt
python generate_database.py   # creates DB with schedule, GPS, wellness
python train_models.py        # trains injury risk model + readiness scorer
streamlit run dashboard.py
```

Dashboard opens at `http://localhost:8501`

---

## What Type of AI/ML Does WAIMS Use?

WAIMS combines three distinct layers:

**1. Random Forest Classifier** (`train_models.py`)  
Supervised ML model trained on monitoring data to predict injury risk within 7 days.  
Features: sleep z-score, CMJ deviation, ACWR, player load, schedule context (back-to-back, travel, rest).  
Output: `injury_risk_score` (0–1 probability) per player per day.

**2. Evidence-Based Readiness Scorer** (`train_models.py → calculate_readiness_score`)  
Rule-based weighted formula — not ML. Deterministic and fully explainable.  
Weights: Sleep 15pts · Soreness 10pts · Mood 5pts · Stress 5pts · CMJ 15pts · RSI 10pts · Schedule 10pts.  
Preferred for daily operational decisions because every flag has a traceable reason.

**3. Generative AI Query Layer** (`smart_query.py`, Ask tab)  
Calls Claude API to answer natural-language questions about your monitoring data.  
Does not make clinical decisions — translates data into plain English for coaches and GMs.

---

## Features

### 8 Interactive Tabs

| Tab | Audience | Purpose |
|-----|----------|---------|
| Command Center | Coach | Morning brief — status badges, unit readiness strip (G/F/C), roster cards with minutes cap + hidden fatigue flag, overnight delta |
| Today's Readiness | Analyst | Z-score flags, wellness + force plate + GPS per player |
| Athlete Profiles | Analyst | Per-player deep-dive, radar chart, GPS trends, 7-day risk score, load projection, basketball-specific risk context |
| Trends & Load | Analyst | 7-day rolling averages — sleep, soreness, mood, stress + GPS/Kinexon load merged into single tab |
| Jump Testing | Analyst | CMJ & RSI vs personal baseline, 7-day team trend |
| Availability & Injuries | GM / Medical | Daily availability board, season %, injury log |
| Forecast | GM / Coach | 7-day injury risk watchlist + load projection (what happens to readiness after tonight's game) |
| Insights | Sport Scientist | Natural-language queries + model validation philosophy + evidence review inbox + correlation heatmap |

### Monitoring Signals

- **Wellness** — Sleep (hrs + quality), soreness, stress, mood, HRV
- **Force Plate** — CMJ height, RSI-Modified, asymmetry %
- **GPS / Kinexon** — Player load AU, accel/decel count, distance, HSR, sprint
- **Schedule** — Back-to-back, days rest, travel, timezone, Unrivaled transition flag
- **Game Data** — ESPN box scores 2019–2025 (pts, min, +/-, W/L, margin)

### Status Badges

Every player card shows two signals side by side:

| Badge | Score | Meaning |
|-------|-------|---------|
| READY (green) | ≥ 80 | Full training — no restrictions |
| MONITOR (amber) | 60–79 | Modified load — watch closely |
| PROTECT (red) | < 60 | Restricted session — flag for medical |

| Risk Label | Threshold | Meaning |
|------------|-----------|---------|
| Injury watch (red) | ≥ 60/100 | High-density warning cluster — active management needed this week |
| Watch closely (amber) | 30–60/100 | Elevated signals — monitor and be ready to modify |
| Low risk (green) | < 30/100 | No elevated concern based on current signals |

**Readiness** = how ready today. **Risk label** = probability of injury within 7 days.
These can diverge: a player can feel fine (MONITOR) but show a warning-signal cluster (Injury watch).
That divergence is the clinical value — subjective wellness and objective neuromuscular state don't always agree.

Cards also show **▲/▼ overnight** — readiness change vs yesterday, so coaches see what moved since last session.

### Classification Engine

Personal z-scores (30-day rolling baseline) + hard safety floors:

- Sleep < 7.0 hrs → yellow (Walsh et al. 2021 BJSM consensus)
- Sleep < 6.0 hrs → red
- Soreness or Stress > 7/10 → immediate flag
- CMJ/RSI position-matched benchmarks (G=38cm, F=34cm, C=30cm)
- ACWR: contextual flag only (Impellizzeri 2020)
- Scores rescaled 0–100 so READY/MONITOR/PROTECT thresholds are calibrated

---

## Model Validation

**V1 validation question:** Does the readiness score ranking match what the coach already knows?

WAIMS V1 does not operate as a validated injury classifier — the Forecast tab produces a heuristic risk score. The meaningful V1 validation is Spearman rank correlation between WAIMS daily ranking and coach informal assessment. Target: coach agrees with top/bottom 3 flagged athletes on ≥ 70% of days.

**V2 validation upgrades** (when 1 full season of real data is available): walk-forward time splits, player-holdout GroupKFold, PR-AUC + calibration, Precision@K top 3 per day, lead-time analysis, and ablation studies. See Insights tab → Model Validation Philosophy for full framework.

---

## Data Sources

| Source | How accessed | Tables created |
|--------|-------------|----------------|
| Synthetic demo data | `generate_database.py` | players, wellness, training_load, force_plate, acwr, injuries, availability, schedule |
| ESPN WNBA (free) | `espn_data.py` | game_results, game_box_scores |
| WNBA benchmarks | `wnba_api.py` (static 2025) | wnba_benchmarks |
| Model outputs | `train_models.py` | ml_predictions, back_to_back_analysis, pre_injury_patterns, readiness_validation |

---

## Pipeline

```
1. python generate_database.py     # always first
2. python espn_data.py             # optional, one-time ESPN fetch
3. python train_models.py          # always after generate
4. streamlit run dashboard.py
```

---

## Research Foundation

| Signal | Citation | Threshold / Finding |
|--------|----------|---------------------|
| Sleep | Walsh et al. 2021 BJSM consensus | < 7 hrs yellow, < 6 hrs red |
| Sleep (meta) | 2025 systematic review + meta-analysis | OR = 1.34 per hr lost |
| Sleep (basketball) | Pernigoni et al. 2024 J Sports Sci (44-study basketball SR) | Single game no duration impact; B2B + travel = circadian disruption |
| CMJ readiness | Gathercole et al. 2015; Labban 2024 | > 2 SD drop = neuromuscular fatigue |
| CMJ recovery | Pernigoni 2024; Goulart 2022 female meta-analysis | Female athletes: NO CMJ drop at 24h post-match (vs male 24-48h) |
| Post-match soreness | Pernigoni 2024 basketball SR; Clark et al. 2025 PLOS One | Peaks 24-48h; substantially lower in female players |
| Back-to-back | Charest et al. 2021 J Clin Sleep Med (NBA B2B travel) | Sleep/circadian disruption confirmed; injury risk increase on B2B contested |
| ACWR | Impellizzeri et al. 2020 | Flag only — not weighted |
| Unrivaled | Clinical estimate | -2pt (no published research — explicitly flagged) |

**Research philosophy:** Thresholds are set by research, adjusted by context. Published thresholds come from heterogeneous populations (often soccer/rugby). WAIMS accounts for basketball-specific demands — pace of play, multi-directional deceleration load, positional differentiation, WNBA schedule density, and female physiology. In a real high-performance department, thresholds are calibrated through collaboration between sport science, coaching, and medical staff — evidence sets the starting point, practitioners adjust to their specific context.

Full citations in `RESEARCH_FOUNDATION.md`.

---

## Data Governance (Real-Team Deployment)

> This section does not apply to the demo. It is documented here because data governance
> is the #1 priority before any real athlete data enters WAIMS.

### The Core Problem

If athletes believe their wellness data affects playing time or contract negotiations,
they will misreport. The data becomes worthless. Trust is the foundation of any
monitoring system — governance is how you protect it.

### Who Sees What

| Data Type | Athlete | Coach | Assistant Coach | GM / Front Office | Medical / AT | Sport Scientist |
|---|---|---|---|---|---|---|
| Traffic light (READY/MONITOR/PROTECT) | Own only | ✓ All | ✓ All | ✓ Summary | ✓ All | ✓ All |
| Readiness score (number) | Own only | ✓ All | ✓ All | ✗ | ✓ All | ✓ All |
| Sleep hours | Own only | ✗ | ✗ | ✗ | ✓ All | ✓ All |
| Soreness / stress / mood (raw) | Own only | ✗ | ✗ | ✗ | ✓ All | ✓ All |
| Force plate (CMJ, RSI) | Own only | Summary flag only | ✗ | ✗ | ✓ All | ✓ All |
| GPS / Kinexon load | Own only | ✓ All | ✓ All | ✗ | ✓ All | ✓ All |
| Injury log | Own only | ✗ | ✗ | Availability status only | ✓ All | ✓ All |
| Injury risk score | Own only | ✗ | ✗ | ✗ | ✓ All | ✓ All |
| Menstrual cycle (V2) | Own only | ✗ | ✗ | ✗ | ✓ With consent | ✓ With consent |

**Key principle:** Coaches see actionable outputs (traffic lights, minutes guidance).
Medical and sport science staff see the signals behind them.
Front office sees availability status only — not health data.

### Athlete Trust Principles

These should be communicated to athletes before any monitoring begins:

1. **Wellness data is for health, not selection.** It informs load management,
   not contract decisions or playing time.
2. **Coaches see traffic lights, not your answers.** Raw soreness and mood scores
   are not visible to coaching staff.
3. **You own your data.** Athletes can request to see all data collected on them
   at any time.
4. **Data is never sold or shared** outside the organisation without explicit consent.
5. **Opting out is possible.** Reduced data collection reduces the system's ability
   to protect you — but participation must be voluntary.

### Legal Considerations (US / WNBA Context)

| Regulation | Applies When | Implication for WAIMS |
|---|---|---|
| **HIPAA** | Medical staff handle or store health data | Injury log, force plate, and any clinically-collected data requires HIPAA-compliant storage (encrypted at rest, access logs, BAA with any cloud vendor) |
| **GDPR** | Any EU-national athletes on roster | Right to erasure, data portability, explicit consent for biometric collection |
| **WNBA CBA** | All WNBA athletes | Collective bargaining agreement has specific provisions on biometric data — review before deployment |
| **State privacy laws** | Varies | California CCPA, Texas, others — check state of team headquarters |

### V2 Implementation Requirements

Before real athlete data enters WAIMS:

- [x] **Role-based login system built** (`auth.py`) — 5 roles: Head Coach, Asst. Coach, Sport Scientist, Medical/AT, GM. Each role sees a different tab set and data access level. Demo credentials on login screen.
- [ ] Data encrypted at rest and in transit (AES-256 minimum)
- [ ] Audit log — who accessed what data and when
- [ ] Data retention policy — how long is data kept, when is it deleted
- [ ] Athlete consent protocol — written, specific to each data type collected
- [ ] Business Associate Agreement (BAA) with any cloud hosting vendor (HIPAA)
- [ ] Legal review of WNBA CBA biometric provisions before deployment
- [ ] Athlete-facing view — simplified readiness trend, no injury risk score shown to athletes

*In V1 demo: all data is synthetic and anonymized. No real athlete data. No governance requirements apply.*


---


## New Modules (v1.1)

| File | Purpose |
|---|---|
| `auth.py` | Role-based login — 5 roles (Head Coach, Asst. Coach, Sport Scientist, Medical/AT, GM) |
| `data_quality.py` | Tiered imputation with full audit log — no silent fills |
| `model_validation.py` | Walk-forward validation, Precision@K, lead-time analysis, baselines |
| `sport_config.py` | Multi-team config — WNBA basketball thresholds, position groups, compliance |
| `healthcheck.py` | Pre-demo startup diagnostic — 10 checks, terminal + Streamlit mode |
| `test_waims.py` | Unit tests (34 passing) — readiness formula, queries, z-scores, auth, data quality |
| `pytest.ini` | Pytest configuration — registers db mark for database tests |
| `.github/workflows/ci.yml` | GitHub Actions CI — runs unit tests on every push automatically |


## Automation Overview

| Workflow | Trigger | Purpose |
|---|---|---|
| `ci.yml` | Every push to main/develop | Runs unit tests — green checkmark on GitHub repo |
| `research_monitor.yml` | Monday 8am UTC | PubMed + RSS search, commits to research_log.json |
| `retrain_models.yml` | Sunday 6am UTC | Retrains RF model, commits .pkl files |

**Setup:** Push `.github/workflows/` files to repo. `GITHUB_TOKEN` is automatic — no config needed.

**Running tests locally:**
```bash
pytest test_waims.py -v -k "not db"   # no database required
pytest test_waims.py -v                # full suite with waims_demo.db
python healthcheck.py                  # pre-demo diagnostic (terminal)
streamlit run healthcheck.py           # pre-demo diagnostic (browser)
```

## Data Quality & Imputation

WAIMS uses a tiered, auditable imputation strategy via `data_quality.py`.
Every decision is logged — no silent fills.

| Data Type | Handling | Rationale |
|---|---|---|
| Wellness missing (no check-in) | Flag only — `wellness_submitted=0` feature | Non-submission is informative, esp. post B2B |
| Force plate CMJ/RSI | LOCF up to 3 days, staleness flag after | Infrequent sessions; LOCF defensible |
| GPS spikes (>3σ) | Winsorise to 3σ, preserve original | Spikes likely device error |
| Sleep (≤2 days missing) | Personal 14-day rolling mean | Strong personal autocorrelation |
| Sleep (>2 days missing) | Flag only | Extended gap needs manual review |
| ACWR (<7 days load history) | Flag as unreliable | Ratio meaningless without denominator |

**Key basketball rules:**
- Missing wellness after a B2B game → explicit `b2b_missing` flag, never imputed
- Personal rolling mean always preferred over team/population mean (positions differ structurally)
- WNBA rolling windows: 7–14 days (not 28+ days from soccer literature)
- Injury day excluded from model training features (prevents leakage)

The audit log is visible in the **Insights tab → Data Quality Audit Log expander**.

---

## Model Validation Framework

WAIMS implements the full Julius.ai validation recipe in `model_validation.py`.

**Two mandatory views:**
1. Walk-forward time splits (Days 1-45 train → 46-60 validate, etc.) — "will it work next week?"
2. Player holdout / GroupKFold — "will it work for a new signing?"

**Headline metrics:**
- Injury risk: PR-AUC + Precision@3/day + Lead-time distribution (target: 3-7 days early)
- Readiness: Spearman rank correlation vs coach intuition (V1 target: ≥0.70 on 70%+ of days)

**Baselines the model must beat:** ACWR heuristic, 7-day load spike rule, player z-score soreness

**Non-contact soft tissue injuries only** — contact injuries explicitly excluded from validation scope.

See RESEARCH_FOUNDATION.md for full framework documentation.

---

## Privacy

All player names anonymized (Player G1, Player F1, etc.).  
Safe for GitHub, portfolio, and professional presentations.

---

## V1 vs V2 vs V3 — Feature Status

| Feature | V1 Status | V2 (Production) Plan | V3 (Future) |
|---|---|---|---|
| Basketball-Specific Risk Context | Core flags (CMJ/RSI, decel, sleep, soreness) with clinical caveats | Full mechanism language, position-specific context, practice vs competition differentiation | — |
| Positional Group Readiness Strip | Guards / Wings / Bigs avg readiness above roster cards | — | Integrate with drill-level load by unit |
| Minutes Cap on Cards | Recommended cap based on readiness + 4-day load | Incorporate Second Spectrum game minutes for true cumulative load | — |
| Hidden Fatigue Detection | Flags READY players trending down under high load (>100 min/4d) | Incorporate decel trend data for earlier detection | — |
| GPS decel monitoring | z-score vs personal baseline, labelled as exposure indicator (Clubb 2025) | Individualised thresholds as % of each player's observed maximum (Pimenta 2026) | — |
| Drill-level GPS tagging | Not built | Not in scope | PlayerMaker/Kinexon timestamp-gated drill segmentation — analyst labels drill type in app, load metrics mapped per segment |
| Game load integration | Practice minutes only (Kinexon) | Second Spectrum optical tracking — true week-total load across practice + games | — |
| ML model | Random Forest on synthetic demo data — illustrative only | Retrain on 90+ days real data with real injury outcomes. Add menstrual cycle phase as feature | Walk-forward validation, PR-AUC, Precision@K |
| Data input | SQLite / CSV manual import | Live APIs: Kinexon, ForceDecks, wellness app. MCP server architecture | — |
| Notifications | Dashboard only | Slack morning brief, SMS alerts for PROTECT-status (medical staff only) | — |
| Hormonal cycle | Not modelled | Menstrual phase adjustment to CMJ/RSI thresholds (Bruinvels 2017). Requires consent protocol | WHSP Institute publications auto-monitored |
| Travel direction | B2B flag only | Eastward/westward circadian penalty (Charest 2021) — ~1 day/time zone eastward | — |

---

## Automated Workflows (GitHub Actions)

Once workflow files are pushed to your repo, GitHub runs them automatically — no further action needed.

### How to activate:
1. Push `.github/workflows/retrain_models.yml` and `.github/workflows/research_monitor.yml` to your repo
2. Go to your repo → **Actions** tab → confirm workflows are listed
3. They run on schedule automatically. To trigger manually: Actions → select workflow → **Run workflow**

### Weekly Model Retrain (`retrain_models.yml`)
Runs every **Sunday 6am UTC** — models are ready before Monday morning brief.
Also triggers automatically when `train_models.py` or `generate_database.py` changes.

```bash
# Generate the workflow file
python research_monitor.py --github-action > .github/workflows/research_monitor.yml

# Retrain workflow — copy from repo root
cp retrain_models.yml .github/workflows/retrain_models.yml
```

What it does:
- Runs `train_models.py` on latest data in the database
- Commits updated `models/injury_risk_model.pkl`, `models/readiness_scorer.pkl`, `data/processed_data.csv`
- Dashboard reads updated models on next page load — no restart needed

**When to retrain:** Weekly is right for a demo. In production with real daily data, retrain after every 7+ new player-days of data. More data = better predictions.

### Weekly Evidence Review (`research_monitor.yml`)
Runs every **Monday 8am UTC** — new papers ready for triage when staff arrive.

```bash
python research_monitor.py --github-action > .github/workflows/research_monitor.yml
```

What it does:
- Searches PubMed across 10 sport-science topics
- Pulls Martin Buchheit, SPSR, BJSM RSS feeds
- Filters clinical noise automatically
- Saves new papers to `research_log.json` as PENDING
- Commits results — appear in Insights tab Evidence Review on next dashboard load

### Important: `GITHUB_TOKEN`
Both workflows use `${{ secrets.GITHUB_TOKEN }}` to push commits back to the repo.
This token is **automatically provided by GitHub** — you do not need to create it.
It only needs read/write permissions on the repo, which is the default for Actions.

---

## Research Monitoring

WAIMS includes `research_monitor.py` — an automated PubMed + RSS tool that flags new papers relevant to the evidence base.

**Purpose:** Forward-looking inbox only. Foundational papers (Walsh 2021, Gabbett 2016, Gathercole 2015, etc.) are already integrated in `RESEARCH_FOUNDATION.md`. This monitor surfaces NEW research for weekly triage in the Evidence Review section of the Insights tab.

**Run manually:**
```bash
python research_monitor.py                        # last 7 days, console output
python research_monitor.py --days 30              # last 30 days
python research_monitor.py --save                 # save to research_log.json
python research_monitor.py --html                 # generate HTML report
python research_monitor.py --output custom.json   # save to separate file (for merge workflow)
```

**Extended lookback + merge (preserves existing decisions):**
```bash
python research_monitor.py --days 730 --output research_log_extended.json
python research_merge.py --new research_log_extended.json --existing research_log.json
```

**Run automatically (GitHub Actions — Monday 8am weekly):**
```bash
python research_monitor.py --github-action > .github/workflows/research_monitor.yml
```

**Search topics:** Sleep & athlete injury risk, CMJ/RSI monitoring, basketball load, female athlete monitoring, deceleration, GPS load, ACWR methodology, menstrual cycle & performance, basketball injury epidemiology, travel & circadian load.

**Relevance filter:** Clinical noise (surgery, pharmacology, oncology, animal studies, etc.) is automatically filtered out before papers reach your log. Only sport science relevant papers surface for triage.

**Decision workflow:**
1. CANDIDATE (meta-analysis/SR) — read abstract, schedule staff review if relevant
2. REVIEW (basketball-specific) — read abstract, Watchlist only
3. Does it change a threshold or interpretation in WAIMS?
4. YES → update `RESEARCH_FOUNDATION.md` + relevant module + README
5. NO → Watchlist or Reject

**Policy:** No threshold change without meta-analysis or systematic review support. Single studies go to Watchlist.

**Sportsmith.co:** Manual monitoring recommended — trusted applied sport science (Jo Clubb, Tim Gabbett). $13/month premium. Log as `Source: Sportsmith (manual YYYY-MM-DD)`.

**Sports Science AI (sportscienceai.com):** Purpose-built AI research assistant for sport science. Database updated weekly. Citations for every paper. Covers journals outside PubMed. Recommended for real-team deployment as a complement to the automated PubMed monitor — together they provide full coverage without manual periodic gap searches.

---

## Drill-Level Load Library (V3 Roadmap)

Concept surfaced by Gemini analysis (2026-03-06). Coaches often have "black box" drills — they know the tactical intent but not the physiological cost.

**What's already in WAIMS (V1):**
- Load Projection: plain-language guidance per scenario ("Heavy game — expect soreness tomorrow")
- Unit Readiness Strip: Guards/Wings/Bigs readiness — coaches adjust drill intensity by unit
- 3-click rule: Command Center → flag → Athlete Profile detail

**V3 roadmap:**
- Drill-level GPS tagging via PlayerMaker or Kinexon — timestamp-gated drill segmentation
- Analyst labels drill type in app, load metrics mapped per segment automatically
- Drill Menu with biometric price tags, Modify Practice button, Practice Script output

**Note on ACWR:** Do not reintroduce ACWR weighting from external suggestions. WAIMS has correctly demoted ACWR to a contextual flag only (Impellizzeri 2020 BJSM critique).
