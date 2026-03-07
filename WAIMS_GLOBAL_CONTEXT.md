# WAIMS Global Context
> A living reference document for Claude sessions. Paste this at the start of any new conversation to restore full project context instantly.

---

## Project Overview

- **Name:** WAIMS — Workload Analysis & Injury Management System
- **Objective:** An elite Coach Command Center for NBA/WNBA coaches to manage player readiness, injury risk, and practice intensity using "decision-ready" language.
- **Guiding Philosophy:** 30-second morning brief, 3-click rule for drills, and prioritising player minutes (Orlando Magic framework).
- **Portfolio purpose:** Demonstrates sport science + software development capability. Two audiences: coaches (simple, actionable) and sport scientists (analytical depth).

---

## Technical Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit (Custom CSS/HTML for cards/alerts) |
| Analytics | Pandas, NumPy, Plotly (sparklines) |
| Storage | SQLite (schedule and historical loads) |
| Intelligence | Scikit-learn / Pickle for readiness scoring; custom Drill Optimizer logic |
| Automation | GitHub Actions (weekly research monitoring via `research_monitor.py`) |

---

## Architecture

### Tab Structure (8 tabs)
1. **📊 Today's Readiness** — Battery indicators, summary cards, quick actions
2. **👤 Athlete Profiles** — Speedometer, radar chart, z-score baselines, pill meters
3. **📈 Trends & Load** — Sleep/soreness trends + training load (GPS & Load merged)
4. **💪 Jump Testing** — CMJ height, RSI-Modified trends
5. **🚨 Availability & Injuries** — Injury log, pre-injury wellness context
6. **🔮 Forecast** — Risk score watchouts, model details
7. **🔍 Ask the Watchlist** — Natural language queries (poor sleep, high risk, readiness, position comparison)
8. **🤖 Insights** — Evidence review integrated beneath Ask section (not sidebar)

### Key Module Files
| File | Purpose |
|---|---|
| `dashboard.py` | Main app entry point |
| `athlete_profile_tab.py` | Full athlete profile UI |
| `improved_gauges.py` | Professional card/battery components |
| `z_score_module.py` | Personal baseline z-score logic |
| `research_citations.py` | Research foundation display |
| `research_context.py` | Basketball-specific risk context boxes |
| `research_monitor.py` | Automated PubMed + RSS monitoring |
| `research_log.json` | Evidence decision log (Integrate/Watchlist/Reject) |

---

## Core Data Structures

### `summary_rows`
List of dicts — one per player — used in Coach Command Center:
```python
{
    "name": str,
    "score": float,       # 0-100 readiness
    "emoji": str,         # 🟢 / 🟡 / 🔴
    "reason": str,        # plain-English flag
    "mins_4d": int,       # cumulative minutes last 4 days
    "inj_risk": str       # LOW / MOD / HIGH
}
```

### `DRILL_LIBRARY`
Dict mapping drill names to metadata:
```python
{
    "5-on-5 scrimmage": {
        "load_per_min": 8.5,
        "intensity": "HIGH",
        "focus": "competition simulation"
    },
    ...
}
```

### Readiness Formula
| Component | Weight |
|---|---|
| Wellness (sleep, soreness, stress, mood) | 35 pts |
| Force Plate (CMJ, RSI-Modified) | 25 pts |
| Schedule / Context | 10 pts |
| GPS / Z-Score deviation | 30 pts |

---

## Current Feature Set

### 1. Morning Brief (Coach Command Center)
Auto-generated bullets:
- Who to check in with
- Overnight readiness changes
- Cumulative load flags (coach-friendly language: "heavy legs this week")

**Wording principle:** Avoid clinical terms. Use: *"heavy legs"*, *"worth a check-in"*, *"lighter today regardless of score"*.

### 2. Roster Status Cards
- Red / Yellow / Green status with cumulative minutes
- Plain-English reason strings
- Minutes Cap labels per card
- Hidden Fatigue Flag: surfaces READY players trending down under high load
- Positional Group Readiness Strip: Guards / Wings / Bigs averages above cards

### 3. GPS Strip
Team-level averages: Player Load and Acceleration counts (session-level, not drill-level yet — see Roadmap).

### 4. Drill Optimizer (In Progress)
Logic to swap HIGH intensity drills for LOW intensity alternatives based on team fatigue state. UI being refined inside the main Command Center tab.

### 5. Athlete Profiles
- Clean speedometer (readiness)
- Radar chart (Sleep / Physical / Mental / Load / Neuro)
- Z-score personal baseline comparison (30-day lookback)
- Whistle-style pill meters (soreness, stress, mood)
- Basketball-specific risk context box (practice vs competition)

### 6. Evidence Review (Insights Tab)
- Integrated beneath Ask section — not sidebar (coaches use sidebar, separation required)
- Decision buttons: Integrate / Watchlist / Reject / Reset
- Writes decisions to `research_log.json`
- GitHub Actions workflow (`research_monitor.yml`) runs weekly on Mondays
- Evidence policy: no threshold change without meta-analysis or systematic review (Orlando Magic framework)

---

## Roadmap

### V2 (Next)
- Drill Optimizer UI — finalized inside Command Center
- Positional Readiness averages (Guards / Wings / Bigs) — partially implemented
- Translation Layer: raw GPS stats → coach-friendly advice

### V3 (Future)
- Drill-level GPS tagging (PlayerMaker / Kinexon integration)
  - PlayerMaker: timestamp-gated drill segmentation via IMU shin sensors
  - Approach: session start/stop per drill → load metrics mapped per segment
- OUT vs GTD availability distinction
- Projected Impact squad toggle
- MCP server integrations: Kinexon, ForceDecks, Slack, Second Spectrum

---

## Key Research & Evidence Gates

| Threshold | Source | Status |
|---|---|---|
| Sleep < 6.5 hrs → 1.7x injury risk | Milewski et al. 2014 | Integrated |
| ACWR > 1.5 → 2.4x injury risk | Gabbett 2016 | Integrated |
| Soreness > 7 → monitoring required | Hulin et al. 2016 | Integrated |
| GPS 3.0 deceleration monitoring limitations | Boskovic et al. 2024; Jo Clubb / Sportsmith | Watchlist |
| Sleep optimisation in elite athletes | Cheri Mah research | Integrated |

**Evidence policy:** No threshold change without a supporting meta-analysis or systematic review.

---

## Design Principles

| Principle | Detail |
|---|---|
| Audience separation | Coaches see Command Center. Sport scientists see Insights / deeper tabs. Sidebar ≠ Evidence Review. |
| 30-second brief | Morning Brief must be scannable in under 30 seconds |
| 3-click rule | Any drill change should require no more than 3 clicks |
| Coach language | No clinical jargon in coach-facing UI. "Heavy legs" not "high cumulative load." |
| Evidence gate | Orlando Magic framework — evidence must meet systematic review standard before changing thresholds |
| Docs updated every session | README, roadmap, and RESEARCH_FOUNDATION updated whenever code changes |

---

## Bugs Fixed (Reference Log)

| Bug | Fix |
|---|---|
| `NameError` for `_sleep_v` | Variable scope issue — resolved |
| `UnicodeEncodeError` on Windows | UTF-8 fix for HTML generation |
| Deprecated `use_container_width` | Replaced with `width='stretch'` |
| pandas GroupBy deprecation | Fixed with `include_groups=False` |

---

## Documentation Files

| File | Purpose |
|---|---|
| `README.md` | Project overview and setup |
| `RESEARCH_FOUNDATION.md` | Evidence base for all thresholds |
| `WAIMS_Roadmap_2026.docx` | Full product roadmap |
| `WAIMS_Coach_Overview.pdf` | One-page coach-facing summary |
| `WAIMS_SportScientist_Overview.pdf` | Two-page technical overview |
| `WAIMS_GLOBAL_CONTEXT.md` | This file — session context for Claude |

---

*Last updated: March 2026*
