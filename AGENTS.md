# AGENTS.md

## Project
WAIMS (Wellness and Injury Management System) is a Python + Streamlit athlete monitoring dashboard for performance staff. It tracks readiness, flags injury risk, and manages load for a 12-player anonymized women's basketball roster. Currently a portfolio/demo tool modeled on a WNBA context. V1 uses synthetic demo data.

**Live URL:** [Streamlit Cloud link here]
**Repo:** `dchriscothern/waims-python`

---

## Main Files
- `dashboard.py` — main entry point, tab routing
- `coach_command_center.py` — coach-facing outputs
- `athlete_profile_tab.py` — individual athlete deep-dive
- `improved_gauges.py` — visual gauge components
- `z_score_module.py` — personal baseline z-score comparisons
- `research_context.py` — PRISMA-flagged research citations
- `train_models.py` — Random Forest model training
- `model_validation.py` — model validation
- `data_quality.py` — data quality checks
- `README.md`
- `WAIMS_SESSION_HANDOFF.md`
- `WAIMS_GLOBAL_CONTEXT.md`

---

## Stack
- **Frontend:** Streamlit
- **Database:** SQLite (local), Supabase (future)
- **Visualization:** Plotly
- **ML:** Random Forest (`train_models.py`)
- **Hosting:** Streamlit Cloud via GitHub

---

## Tab Structure (8 tabs)
1. Roster Overview
2. Athlete Profile
3. GPS & Load
4. Availability & Injuries
5. Force Plate (CMJ/RSI)
6. Z-Score Baselines
7. Research Context
8. [Tab 8 name — update here]

---

## Stable Rules
- Keep coach-facing outputs simple and practical.
- Keep sport scientist outputs more technical.
- Do not casually change evidence-based thresholds.
- Prefer editing real source files instead of generated outputs.
- `WAIMS_Coach_Overview.pdf` should remain a true one-pager.
- `WAIMS_SportScientist_Overview.pdf` can be multi-page.
- Emoji-free UI. Text-only status labels. Left-border color coding. Horizontal fill bars.
- Z-score personal baselines alongside absolute safety thresholds — not either/or.
- Force plate (CMJ/RSI) is primary fatigue signal, not GPS alone.
- Research citations prioritize female/basketball-specific sources (Roberts 2019, Fort-Vanmeerhaeghe 2020, Hewett 2006).

---

## Session State
_Update at the end of every session._

**Last completed:**
- [x] Updated WAIMS with 2026 WNBA mid-season stats via enhanced fetch_wehoop_data.py
- [x] Created multi-sport architecture with parallel waims-wnba/ and waims-mens/ directories
- [x] Implemented Arkansas Men's Basketball version with real roster (14 players)
- [x] Extended sport_config.py to common/sport_config_extended.py supporting WNBA + Men's Power 5
- [x] Generated 1,260 synthetic records for Arkansas with men-specific GPS baselines
- [x] Trained Random Forest injury risk model for Arkansas (100 trees, 28 features)
- [x] Created multi-sport launcher (launcher.py) with setup wizard and sport selection
- [x] Comprehensive documentation: MULTI_SPORT_SETUP.md + IMPLEMENTATION_SUMMARY.md
- [x] Fixed Windows Unicode encoding issues (PowerShell cp1252)

**Known issues:**
- [ ] Dashboard needs sport/team selector parameter integration (dashboard.py customization pending)
- [ ] Wehoop API testing needed (requires live 2026 data fetch)
- [ ] Role-based access validation across sports not yet tested in UI

**Next priority:**
- [ ] Integrate sport parameter into dashboard.py (allow --sport wnba/mens)
- [ ] Test full dashboard launch: `python launcher.py --sport mens`
- [ ] Validate WNBA dashboard with 2026 wehoop stats
- [ ] Add more Power 5 teams (Duke, Kansas, UCLA) following Arkansas template

---

## Compacting
When compacting, preserve:
- current task
- files inspected or changed
- important commands
- decisions already made
- blockers or open questions

Do not preserve in detail:
- long logs
- repeated repo descriptions
- unrelated exploration
- rejected approaches unless still relevant
