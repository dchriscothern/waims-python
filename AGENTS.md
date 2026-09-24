# AGENTS.md

## Project
WAIMS (Wellness & Athlete Injury Management System) is a Python + Streamlit athlete monitoring dashboard for performance staff. It tracks readiness, flags injury risk, and manages load for a 12-player anonymized women's basketball roster. Currently a portfolio/demo tool modeled on a WNBA context. V1 uses synthetic demo data. A second deployment (`WAIMS_SPORT=mens`) reuses the same app for a real Arkansas Razorbacks men's dataset.

**Live URL (WNBA):** https://waims-python-zzikytfewmqiwwfhrdajwo.streamlit.app/
**Live URL (Arkansas/mens):** separate Cloud app — URL not yet recorded here, ask the user for the current link
**Repo:** `dchriscothern/waims-python`

---

## Main Files
- `dashboard.py` — main entry point, tab routing, multi-sport bootstrap
- `dashboard_mens.py` — Cloud entry point that locks the deployment to Arkansas (`WAIMS_SPORT=mens`) before running `dashboard.py`. Restored into `sandbox`'s working tree 2026-09-23 (was previously stranded on unmerged branch `fix-arkansas-cloud-deploy-v2`) — commit it once ready.
- `auth.py` — role-based login, tab visibility (`TAB_ACCESS`), and data-field visibility per role
- `coach_command_center.py` — coach-facing outputs (Command Center tab)
- `athlete_profile_tab.py` — individual athlete deep-dive
- `athlete_view.py` — simplified athlete-facing view
- `correlation_explorer.py` — lag analysis, conditional risk table, real game-stat correlations (Insights tab)
- `game_performance_tab.py` — Arkansas-only Game Performance tab
- `improved_gauges.py` — visual gauge components
- `z_score_module.py` — personal baseline z-score comparisons
- `research_citations.py` — PRISMA-flagged research citations (`research_context.py` is an older, currently-unused module)
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
- [ ] `dashboard_mens.py` was restored to `sandbox`'s working tree from the stranded `fix-arkansas-cloud-deploy-v2` branch (2026-09-23) but is **not yet committed** — commit and push once confirmed working, then this branch can be deleted (it also carries a lot of pre-squash-merge history not worth merging wholesale — only the file itself was pulled in, not the branch).
- [x] `SETUP_GUIDE.md`'s "Sport selection on Streamlit Cloud" section claimed the `?sport=mens` query-param route was "the one that's actually been reliable" — this was backwards (any query string triggers a false "app doesn't exist" from Cloud's routing layer); corrected 2026-09-23.

**Last completed (2026-09-23):**
- [x] Audited and corrected `README.md`, `LEARNING_GUIDE.md`, `CLAUDE.md`/`CLAUDE.sandbox.md`, `AGENTS.md` against actual current tab structure (`TAB_ACCESS`/`TAB_LABELS` in `auth.py`) and file layout — all previously described an 8-tab structure last accurate before the multi-sport/Insights-merge/Data-Intake/Game-Performance work
- [x] Restored `dashboard_mens.py` (Secrets-free Arkansas Cloud entry point) into `sandbox`'s working tree — verified with Streamlit's `AppTest` harness, no exceptions, Arkansas login screen renders correctly

**Next priority:**
- [ ] User-driven — no single next task queued as of 2026-09-23

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
