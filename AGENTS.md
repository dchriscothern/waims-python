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
- [x] Coach Command Center roster status now shows a compact summary with the full player card grid behind a collapsed detail dropdown.
- [x] Forecast / Insights jump-profile merge path hardened so missing `player_id` during force-plate profiling no longer crashes the app.
- [x] PR review blockers addressed: retrain workflow push target hardened, GM availability access restored, and duplicate/corrupted research-log evidence row removed.
- [x] Staging mobile-web polish started for athlete-facing views by stacking high-density cards/charts into fewer side-by-side columns.
- [x] Data Intake tab no longer throws `NameError` for `render_soft_card_grid`; connector status cards now render locally in `dashboard.py`.

**Known issues:**
- [ ] Need visual QA in Streamlit to confirm the new roster summary/dropdown spacing feels right on deployed layout.
- [ ] Need deployed app verification that Forecast / Insights loads cleanly with current Cloud data snapshot.
- [ ] Coach Command Center still needs a separate phone-focused layout pass if staff will use that tab regularly on small screens.

**Next priority:**
- [ ] Run a staging smoke test for sports scientist tabs after the Data Intake fix, then continue the coach-facing mobile polish pass.

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
