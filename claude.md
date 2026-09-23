# CLAUDE.md

## Project
WAIMS (Wellness & Athlete Injury Management System) is a Python + Streamlit athlete monitoring dashboard for performance staff. It tracks readiness, flags injury risk, and manages load for a 12-player anonymized women's basketball roster. Currently a portfolio/demo tool modeled on a WNBA context. V1 uses synthetic demo data. A second deployment (`WAIMS_SPORT=mens`, launched via `dashboard_mens.py`) reuses the same app for a real Arkansas Razorbacks men's dataset.

**Live URL (WNBA):** https://waims-python-zzikytfewmqiwwfhrdajwo.streamlit.app/
**Live URL (Arkansas/mens):** separate Cloud app — URL not yet recorded here, see the user for the current link
**Repo:** `dchriscothern/waims-python`

---

## Main Files
- `dashboard.py` — main entry point, tab routing, multi-sport bootstrap
- `dashboard_mens.py` — Cloud entry point that locks the deployment to Arkansas (`WAIMS_SPORT=mens`) before running `dashboard.py`. Restored into `sandbox`'s working tree 2026-09-23 (was previously stranded on unmerged branch `fix-arkansas-cloud-deploy-v2`) — commit it once you're ready.
- `auth.py` — role-based login, tab visibility (`TAB_ACCESS`), and data-field visibility per role
- `coach_command_center.py` — coach-facing outputs (Command Center tab)
- `athlete_profile_tab.py` — individual athlete deep-dive
- `athlete_view.py` — simplified athlete-facing view
- `correlation_explorer.py` — lag analysis, conditional risk table, real game-stat correlations (Insights tab)
- `game_performance_tab.py` — Arkansas-only Game Performance tab
- `improved_gauges.py` — visual gauge components
- `z_score_module.py` — personal baseline z-score comparisons
- `research_citations.py` — PRISMA-flagged research citations (`research_context.py` is an older, currently-unused module — don't confuse the two)
- `train_models.py` — Random Forest model training
- `model_validation.py` — model validation
- `data_quality.py` — data quality checks
- `common/sport_config_extended.py` — per-sport thresholds/team config used at runtime
- `README.md`
- `LEARNING_GUIDE.md`
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

## Tab Structure (role-gated, up to 10 tabs — see `TAB_ACCESS` in `auth.py`)
1. Command Center
2. Today's Readiness
3. Athlete Profiles
4. Trends & Load (wellness + force plate + GPS/Kinexon merged)
5. Jump Testing
6. Availability & Injuries
7. Forecast
8. Insights (Ask/voice query + Correlation Explorer + model validation + data quality audit log)
9. Data Intake
10. Game Performance — Arkansas/mens deployment only, hidden on WNBA

Plus a separate Athlete View (not a tab bar — a whole simplified page) for the `athlete` role.

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
- [ ] Describe what was finished

**Known issues:**
- [ ] List any current bugs or rough edges

**Next priority:**
- [ ] Single next thing to do

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
