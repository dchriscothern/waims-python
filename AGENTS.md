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

**Last completed (2026-08-17):**
- [x] Multi-sport routing: one shared `dashboard.py`, sport selected via `WAIMS_SPORT` env var / `st.secrets` / `?sport=` query param — not separate `waims-wnba/`/`waims-mens/` dashboards (an earlier plan described that split; it was never built)
- [x] Real Arkansas game data: box scores + play-by-play parsed via OCR from 4 real Baha Mar summer games (`scripts/parse_arkansas_box_scores.py`, `scripts/parse_arkansas_play_by_play.py`), real prior-season log for Billy Richmond III (37 games, ESPN)
- [x] Game Performance tab (box scores, player log, shot detail, advanced possession/lineup metrics) and a real-game-stats section on the Athlete Profile tab
- [x] Real-vs-synthetic data labeling audited and fixed app-wide (sidebar banner, per-section captions, "Real data" badges)
- [x] Correlation Explorer extended to Arkansas's real game data, with sample-size caveats
- [x] Fixed a real production bug: `load_data()`/`startup_health_report()` in `dashboard.py` cached with zero arguments, so a shared Streamlit Cloud process stuck on whichever sport loaded first regardless of later requests — now parameterized by `db_path`
- [x] Docs corrected: `SETUP_GUIDE.md`, `MULTI_SPORT_SETUP.md` rewritten to match actual architecture; `IMPLEMENTATION_SUMMARY.md` marked as a historical snapshot; new `GOING_LIVE_CHECKLIST.md` for real-team production readiness

**Known issues:**
- [ ] `sandbox` and `main` have different-shaped git histories after a squash merge — future `sandbox` → `main` PRs may show a false "merge conflicts" error; resync `sandbox` onto `main` before the next round of work
- [ ] No real authentication, encryption at rest, or audit logging — fine for the current synthetic-data demo, see `GOING_LIVE_CHECKLIST.md` before this ever touches real athlete data

**Next priority:**
- [ ] User-driven — no single next task queued as of 2026-08-17

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
