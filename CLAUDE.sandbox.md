# CLAUDE.md

## Environment: SANDBOX / STAGING

* This is a development and experimentation environment
* Safe to test new features, refactors, and architecture changes
* Breaking changes are acceptable if they improve structure
* Temporary debug code and logging are allowed
* Prioritize speed of iteration over polish
* UI can be rough if functionality is being tested
* Validate ideas here before promoting to production

## Sandbox Workflow
For local run commands, sandbox → main process, and Streamlit Cloud setup:
See `C:\GitHub\_docs\STREAMLIT-WORKFLOW.md`

---

## HOW TO APPROACH EVERY TASK

**Before writing any code:**
1. Identify the entry point (usually dashboard.py) and trace data flow to the affected area
2. State your interpretation of the task explicitly
3. If ambiguous, list interpretations and ask — do not pick one silently
4. Propose the minimal fix first, even in sandbox — refactors are fine but should be intentional, not incidental

**Minimum code rule:**
Write the minimum code that solves the problem. No speculative features, no added flexibility that wasn't requested. In sandbox, refactors are encouraged — but only when they improve clarity or scalability, not as a side effect of something else.

**Surgical changes only:**
Touch only what the task requires. Do not improve adjacent code, reformat unrelated sections, or clean up things that aren't broken. Match existing style. If you notice unrelated issues, mention them — do not fix them without being asked. Remove imports/variables/functions only if YOUR changes made them unused.

**Verify before finishing:**
For any multi-step task, state what success looks like before starting:
- What will be different when this is done?
- What will you check to confirm it worked?
Do not mark a task complete until those checks pass.

**When confused:**
Stop. Name what's unclear. Ask. The z-score methodology and evidence-based thresholds in this repo are intentional — do not change them based on assumptions.

---

## Project

WAIMS (Wellness and Injury Management System) is a Python + Streamlit athlete monitoring dashboard for performance staff. It tracks readiness, flags injury risk, and manages load for a 12-player anonymized women's basketball roster. Currently a portfolio/demo tool modeled on a WNBA context. V1 uses synthetic demo data.

Live URL: https://waims-python-zzikytfewmqiwwfhrdajwo.streamlit.app/
Repo: dchriscothern/waims-python

---

## Stack

* Frontend: Streamlit
* Database: SQLite (local), Supabase (future)
* Visualization: Plotly
* ML: Random Forest (train_models.py)
* Hosting: Streamlit Cloud via GitHub

---

## File Roles

* dashboard.py → app entry point, controls tab routing
* *_tab.py → UI layer only (no heavy data logic)
* *_module.py → calculations, transformations, metrics
* train_models.py → model training only (offline, not runtime)
* model_validation.py → validation logic only
* data_quality.py → input checks and validation rules
* improved_gauges.py → reusable UI components
* research_context.py → research citations and supporting evidence

Rule: UI files should not contain heavy data processing.

---

## Tab Structure (8 tabs)

1. Roster Overview
2. Athlete Profile
3. GPS & Load
4. Availability & Injuries
5. Force Plate (CMJ/RSI)
6. Z-Score Baselines
7. Research Context
8. [Update name when finalized]

---

## Data Flow

Data
→ preprocessing (z_score_module, data_quality)
→ modeling (optional, train_models)
→ tab-level logic
→ UI rendering (Streamlit)

Principles:
* Data transformation happens before UI
* UI only displays processed outputs
* Models are not run inside UI render loop

---

## Stable Rules

* Keep coach-facing outputs simple and practical
* Keep sport scientist outputs more technical
* Do not casually change evidence-based thresholds
* Prefer editing real source files instead of generated outputs
* WAIMS_Coach_Overview.pdf should remain a true one-pager
* WAIMS_SportScientist_Overview.pdf can be multi-page
* Emoji-free UI
* Text-only status labels
* Left-border color coding + horizontal fill bars
* Z-score personal baselines alongside absolute thresholds (not either/or)
* Force plate (CMJ/RSI) is primary fatigue signal, not GPS alone
* Research citations prioritize female/basketball-specific sources
  (Roberts 2019, Fort-Vanmeerhaeghe 2020, Hewett 2006)

---

## Common Failure Points

* Tab not rendering due to incorrect import or function call
* Streamlit tabs misaligned with function definitions
* Mixing UI code and data logic
* Incorrect data shape passed into visual components
* Z-score calculations using wrong baseline reference

Always check these first when debugging.

---

## Context Files

* WAIMS_GLOBAL_CONTEXT.md → long-term system thinking
* WAIMS_SESSION_HANDOFF.md → short-term continuity

CLAUDE.md = execution rules (primary file)

---

## Session State

(Update at the end of every session)

Last completed:
* [ ]

Known issues:
* [ ]

Next priority:
* [ ]

---

## Compacting

When compacting, preserve:
* current task
* files inspected or changed
* important commands
* decisions already made
* blockers or open questions

Do not preserve in detail:
* long logs
* repeated repo descriptions
* unrelated exploration
* rejected approaches unless still relevant
