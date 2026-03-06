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

### 9 Interactive Tabs

| Tab | Audience | Purpose |
|-----|----------|---------|
| Command Center | Coach | Morning brief — status badges, priority alerts, GPS strip, roster cards |
| Today's Readiness | Analyst | Z-score flags, wellness + force plate + GPS per player |
| Athlete Profiles | Analyst | Per-player deep-dive, radar chart, GPS trends, 7-day risk score, load projection, basketball-specific risk context (V1) |
| Trends | Analyst | 7-day rolling averages — sleep, soreness, mood, stress |
| Jump Testing | Analyst | CMJ & RSI vs personal baseline, 7-day team trend |
| Availability & Injuries | GM / Medical | Daily availability board, season %, injury log |
| GPS & Load | Analyst | Kinexon metrics, 14-day trends, player load ACWR |
| Forecast | GM / Coach | 7-day injury risk watchlist + load projection (what happens to readiness after tonight's game) |
| Insights | All | Natural-language queries + correlation heatmap + ESPN game outcome analysis |

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

Badges appear on: Command Center roster cards, Priority Alerts panel, Forecast tab, Athlete Profile.

### Classification Engine

Personal z-scores (30-day rolling baseline) + hard safety floors:

- Sleep < 7.0 hrs → yellow (Walsh et al. 2021 BJSM consensus)
- Sleep < 6.0 hrs → red
- Soreness or Stress > 7/10 → immediate flag
- CMJ/RSI position-matched benchmarks (G=38cm, F=34cm, C=30cm)
- ACWR: contextual flag only (Impellizzeri 2020)
- Scores rescaled 0–100 so READY/MONITOR/PROTECT thresholds are calibrated

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

Full citations in `RESEARCH_FOUNDATION.md`.

---

## Privacy

All player names anonymized (Player G1, Player F1, etc.).  
Safe for GitHub, portfolio, and professional presentations.


---

## V1 vs V2 — Feature Status

| Feature | V1 Status | V2 (Production) Plan |
|---|---|---|
| Basketball-Specific Risk Context | V1: Core flags (CMJ/RSI, decel, sleep, soreness) with clinical caveats. `injury_mechanism_insight_box` not built yet. | V2: Full mechanism language, position-specific context, practice vs competition differentiation. Requires validation on real team data first. |
| GPS decel monitoring | V1: z-score vs personal baseline, labelled as exposure indicator with cross-reference requirement (Clubb 2025). | V2: Individualised thresholds as % of each player's observed maximum (Pimenta et al. 2026). |
| Game load integration | V1: Practice minutes only (Kinexon). Game load not tracked. | V2: Second Spectrum optical tracking integration — true week-total load picture across practice + games. WNBA leaguewide data available since 2024. |
| ML model | V1: Random Forest trained on synthetic demo data. Predictions are illustrative. | V2: Retrained on 90+ days of real athlete data with real injury outcomes. Add menstrual cycle phase as feature. |
| Data input | V1: SQLite / CSV manual import. | V2: Live API connections — Kinexon, ForceDecks/Vald, wellness app (Smartabase or Teamworks Pulse), Second Spectrum. MCP server architecture. |
| Notifications | V1: Dashboard only — staff must open the app. | V2: Slack morning brief, SMS alerts for PROTECT-status players (medical staff only). |
| Athlete view | V1: Staff-facing only. | V2: Simplified athlete-facing readiness + trend view. No injury risk numbers shown to athletes. |
| Hormonal cycle | V1: Not modelled. | V2: Menstrual phase adjustment to CMJ/RSI thresholds and load recommendations (Bruinvels et al. 2017). Requires athlete consent protocol. |
