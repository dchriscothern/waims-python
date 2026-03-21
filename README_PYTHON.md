# WAIMS — Python Technical Reference

Complete module and tab reference for developers and portfolio review.

---

## Architecture

```
generate_database.py  ──►  waims_demo.db  ──►  train_models.py  ──►  models/
                                │                      │
                         espn_data.py          processed_data.csv
                                │
                         wnba_api.py
                                │
                         oura_connector.py
                                │
                          oura_mapper.py
                                │
                          dashboard.py
                    ┌───────────┴────────────────────┐
                    │  coach_command_center.py (Tab 1) │
                    │  athlete_profile_tab.py  (Tab 3) │
                    │  athlete_view.py         (Athlete) │
                    │  correlation_explorer.py (Tab 10)│
                    │  smart_query.py          (Tab 9) │
                    └──────────────────────────────────┘
```

---

## Module Reference

### `generate_database.py`
Generates `waims_demo.db` with all tables needed for training and dashboard.

Key outputs:
- 12 anonymized players (G1–G5, F1–F5, C1–C2) with position-appropriate stats
- 90 days wellness, training load (GPS), force plate, ACWR
- 2026 Wings schedule (44 games, back-to-backs, travel flags, FIBA break)
- 5 injury events with pre-injury signal patterns
- Unrivaled transition flags for G1, G2 (played Jan–Mar 2026)

---

### `train_models.py`
Trains two models and runs outcome validation (Section 8).

**Section 1–7:** Core training
- Loads monitoring data + schedule via LEFT JOIN (graceful fallback if no schedule)
- Engineers z-score features (30-day personal baseline)
- Trains Random Forest injury risk classifier
- Calculates evidence-based readiness scores
- Saves `models/injury_risk_model.pkl` and `models/readiness_scorer.pkl`
- Exports `data/processed_data.csv` with ESPN game context joined

**Section 8:** Model improvement loop (runs only if game data exists)
- **A. Back-to-back validation** — actual pts drop on B2B vs rest → validates -4pt penalty
- **B. Pre-injury patterns** — 7-day monitoring window before each injury event
- **C. Readiness validation** — Pearson r between readiness score and game performance

**Readiness score formula (0–100):**
```
Sleep (hrs)     15 pts    Walsh 2021 BJSM  (quality 5pts + quantity 10pts)
Soreness        10 pts    floor: >7/10 = flag
Mood             5 pts
Stress           5 pts    floor: >7/10 = flag
CMJ             15 pts    Gathercole 2015, Labban 2024 — position-matched (G=38, F=34, C=30cm)
RSI             10 pts    Bishop 2023
Schedule        10 pts    back-to-back -4, travel -3 (scaled), rest<2d -2, Unrivaled -2*
─────────────────────────────────────
Base total      70 pts    (schedule deducts from 10pt allowance)
GPS modifier   ±20 pts    Jaspers 2017, Petway 2020 — player_load, accel, decel z-scores
Z-score mod    ±10 pts    Cormack 2008 — intra-individual deviation from 30-day baseline
─────────────────────────────────────
Rescaled ×100/70 so final output spans 0–100 correctly
* Unrivaled -2: clinical estimate, no published research — flagged for validation
```

---

### `espn_data.py`
Fetches Dallas Wings game results + box scores from ESPN public API.
No API key required.

Key functions:
- `fetch_wings_season(season, db_path)` — single season
- `fetch_wings_all_time(seasons, db_path)` — multi-season (2019–2025)
- `get_player_career_summary(db_path)` — career averages per player
- `get_back_to_back_performance_summary(box_scores, schedule)` — validates B2B penalty
- `get_performance_vs_monitoring(box_scores, wellness, training_load, force_plate)` — outcome join

Season coverage: 2019–2025 (246 games, 2325 player-game rows as of March 2026)

---

### `wnba_api.py`
WNBA positional benchmarks (G/F/C) for population context.

- Default: static 2025 season averages (no API needed)
- Upgrade path: set `USE_LIVE_API = True` + balldontlie All-Star ($9.99/mo)
- Writes `wnba_benchmarks` table to DB
- `get_player_zscore_vs_position(value, metric, position_group)` — population z-score

Note: GPS player_load (Kinexon units) cannot be directly compared to WNBA minutes.
Population benchmarks are display-only context, not model features.

---

### `coach_command_center.py` — Tab 1
**Audience:** Head coach, assistant coaches  
**Goal:** Full roster situational awareness in under 30 seconds

Components:
- Dark header — live READY/MONITOR/PROTECT counts
- Priority Alerts — top 3 flagged players, reason + directive
- GPS/Kinexon strip — team avg load, high-load players, low-accel players
- Roster cards (Plotly figures) — name, position, status badge, readiness %, reason line
- 7-day team sparklines — sleep, soreness, mood, stress

Status badges:
- READY (green) ≥ 80
- MONITOR (amber) 60–79
- PROTECT (red) < 60

---

### `athlete_profile_tab.py` — Tab 3
**Audience:** Sports scientist, athletic trainer  
**Goal:** Full per-player monitoring picture

Components:
- Readiness gauge (Plotly speedometer) — uses same pkl scorer as Command Center
- Radar chart — Sleep, Physical, Mental, Load, Neuro, GPS (position-matched CMJ benchmark)
- 8 metric cards — sleep, soreness, mood, ACWR⚠, CMJ, RSI, Load, Accels
- GPS / Kinexon section — 14-day trend chart, z-score flags
- Personal baseline z-score comparison (30-day rolling)
- 7-day wellness + force plate overlay trend chart
- Basketball-specific risk context (practice vs competition)
- Research references with evidence grades

Formula alignment: readiness score uses shared _calculate_readiness() function,
identical to coach_command_center.py — single source of truth via pkl scorer.
Sleep threshold: <7.0 yellow, <6.0 red (Walsh 2021) — consistent across all tabs.
CMJ benchmark: position-matched G=38cm, F=34cm, C=30cm — consistent across all tabs.

ACWR treatment: displayed as "ACWR ⚠" — contextual flag only, not weighted.
Reason: Impellizzeri 2020 statistical coupling critique, 2025 meta-analysis.

---

### `athlete_view.py`
**Audience:** Athlete  
**Goal:** Clean, top-to-bottom personal briefing without exposing team or injury-risk data

Current top layout:
- readiness/status card + today's sleep / soreness / stress on one line
- compact context row: This Week, Load, Next Game
- Today Plan
- Last Game vs Season Average
- Recovery Checklist
- Wearable Recovery
- Ask a Question

Design intent:
- lower cognitive load than staff tabs
- compact, scannable, athlete-facing language
- wearable section stays supplementary rather than primary guidance

---

### `oura_connector.py`
**Audience:** Developer / demo reviewer  
**Goal:** Proof-of-concept wearable ingestion path for WAIMS

Behavior:
- uses Oura v2 REST API with personal access token auth
- supports `daily_sleep` and `daily_readiness` collection
- defaults to demo mode when no token is configured
- exposes `get_oura_status()` for UI-safe connection state
- intentionally not production OAuth

---

### `oura_mapper.py`
**Audience:** Developer / demo reviewer  
**Goal:** Translate Oura payloads into WAIMS wellness schema fields

Core mappings:
- `readiness_score` -> `readiness`
- `total_sleep_duration` -> `sleep_hours`
- `average_hrv` -> `hrv`
- `resting_heart_rate` -> `rhr`

This keeps the wearable POC additive and compatible with the existing readiness vocabulary.

---

### `correlation_explorer.py` — Tab 10
**Audience:** Sports scientist, analyst  
**Goal:** Surface hidden signal relationships

Sections:
1. Correlation heatmap (Pearson r, all metrics)
2. Top hidden correlations — ranked, annotated with research citations
3. Lag analysis — does yesterday's metric predict today's outcome?
4. Conditional risk table — P(injury | metric flagged)
5. Per-player breakdown
6. Model feature audit — RF feature importances

ESPN integration: `_build_master()` joins `game_results` and `game_box_scores`
on game dates, adding `game_team_pts`, `game_margin`, `game_result_binary`.
These appear in heatmap when ESPN data is present in DB.

---

### `smart_query.py` — Tab 9
**Audience:** All staff  
**Goal:** Natural-language data questions

Calls Claude API (claude-sonnet). Context includes:
- Current roster readiness snapshot
- Recent wellness and GPS metrics
- Injury history
- Schedule context

Example queries:
- "Who had poor sleep last night?"
- "Which players are on a back-to-back this week?"
- "Show me everyone with CMJ drop and high soreness"
- "Does team readiness correlate with game margin?"

---

## Key Design Decisions

**Single readiness formula across all tabs**  
All three calculation surfaces (Command Center, Athlete Profile, train_models.py) now use
the same pkl scorer or identical fallback formula. Prior to audit, athlete_profile_tab.py
used a different formula (wellness only, no CMJ/RSI/schedule) which caused meaningful
score divergence — a player with good sleep but fatigued legs could show 90% in profiles
but correctly 65% in Command Center. Resolved March 2026.

**Personal z-scores over population thresholds**  
Small rosters (12 players) make population norms unreliable. A guard who normally scores 7/10 on soreness and reports 7/10 today is not flagged — because that's her norm. Personal 30-day rolling baseline is more sensitive and specific.

**Hard safety floors**  
Some signals override z-scores: sleep < 7 hrs, soreness/stress > 7. These are absolute thresholds regardless of personal baseline. Prevents "this player is always tired so we normalize it."

**ACWR demotion**  
ACWR is displayed but not weighted in readiness score or model features. Reason: Impellizzeri et al. 2020 identified mathematical coupling artifacts; 2025 meta-analysis recommends "use with caution." Back-to-back and days_rest features replace it as schedule load signals.

**Evidence grades**  
All thresholds tagged ★★★ (RCT/systematic review), ★★ (observational cohort), or ★ (clinical estimate). Unrivaled transition penalty explicitly marked as clinical estimate — no research exists.

---

## Upgrade Paths

| Current | Upgrade | What changes |
|---------|---------|--------------|
| Static WNBA benchmarks | balldontlie All-Star $9.99/mo | Live season averages |
| Synthetic wellness data | Real athlete monitoring input | Model predictions become valid |
| ESPN box scores (free) | Second Spectrum (team license) | True GPS game load replaces proxy |
| Anonymized players | Real roster (with consent) | Photos, actual career stats |
