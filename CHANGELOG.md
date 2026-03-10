# WAIMS — Changelog

All notable changes to this project are documented here.  
Format: [Conventional Commits](https://www.conventionalcommits.org/) · Maintained by Chris Cothern

---

## [1.1.0] — March 2026

### Features
- **feat(command-center):** Add positional group readiness strip — Guards / Wings / Bigs average readiness displayed above roster cards for instant tactical read by unit
- **feat(command-center):** Add hidden fatigue detection — flags READY players trending down under high cumulative load (>100 min/4d), shows "Watch Closely" badge
- **feat(command-center):** Add load warning labels on roster cards — warning language replaces hard minutes cap (coach judgment preserved)
- **feat(command-center):** Add overnight delta arrow — readiness change vs yesterday shown on each card
- **feat(dashboard):** Add Availability & Injuries tab — daily availability board (AVAILABLE / QUESTIONABLE / OUT), season availability %, full injury log
- **feat(dashboard):** Add GPS & Load section — Kinexon metrics, 14-day trends, player load ACWR merged into Trends & Load tab
- **feat(forecast):** Add Load Projection tool — select player + scenario, see projected readiness tomorrow with specific staff recommendation
- **feat(forecast):** Add ML injury risk watchlist — Random Forest flags players matching pre-injury patterns from training data
- **feat(insights):** Add Evidence Review inbox — automated PubMed + RSS triage with formal evidence gate (CANDIDATE / REVIEW / WATCHLIST / BACKGROUND)
- **feat(insights):** Add Model Validation Philosophy expander — V1 Spearman approach and V2 upgrade roadmap documented in Insights tab
- **feat(insights):** Add Signal Correlations section — heatmap, lag analysis, conditional risk table, ESPN game outcome integration
- **feat(evidence):** Add research_monitor.py — automated weekly PubMed + RSS monitoring via GitHub Actions (Monday 8am)
- **feat(evidence):** Add research_merge.py — safe extended-lookback merge preserving existing Integrate/Watchlist/Reject decisions
- **feat(evidence):** Add research_topics_config.py — tightened sport-science-only PubMed queries with clinical noise filter

### Fixes
- **fix(dashboard):** Resolve datetime comparison errors between datetime64 and date objects in readiness tab sort
- **fix(dashboard):** Replace deprecated `use_container_width` Streamlit parameter with `width='stretch'`
- **fix(models):** Fix pandas GroupBy deprecation warning — add `include_groups=False`
- **fix(dashboard):** Fix ReportLab word wrap overflow in PDF exports — use Paragraph objects in table cells
- **fix(athlete-profile):** Unify readiness formula across Command Center, Athlete Profile, and train_models.py — prior divergence caused score differences of up to 15pts for same player

### Research & Evidence
- **research:** Update sleep threshold from <6.5h (Milewski 2014) to <7.0h (Walsh 2021 BJSM consensus + 2025 meta-analysis OR=1.34)
- **research:** Demote ACWR from weighted signal to contextual flag only (Impellizzeri 2020 + 2025 meta-analysis)
- **research:** Apply GPS 3.0 framing throughout — GPS = external locomotor load only, CMJ/RSI = neuromuscular response signal (Boskovic et al. 2024)
- **research:** Apply female-specific CMJ recovery rates to Load Projection — no CMJ drop at 24h post-match in female players (Pernigoni 2024, Goulart 2022)
- **research:** Add WHSP Institute as monitored institution — Dr. Kate Ackerman, launched Jan 2026, $50M+, Clara Wu Tsai/NY Liberty
- **research:** Add travel direction science — eastward harder than westward, ~1 day/time zone to resync (Charest 2021)
- **research:** Add model validation framework to RESEARCH_FOUNDATION.md — V1 Spearman/coach intuition, V2 walk-forward splits, PR-AUC, Precision@K

### Documentation
- **docs:** Update README — 8 tabs (down from 10), model validation section, V1/V2/V3 roadmap table
- **docs:** Update SETUP_GUIDE.md — file structure reflects current module count, research tools documented
- **docs:** Update README_PYTHON.md — architecture diagram, 8-tab reference, research module entries
- **docs:** Update LEARNING_GUIDE.md — 8 tabs explained, model validation and evidence review sections added, interview talking points updated
- **docs:** Add WAIMS_GLOBAL_CONTEXT.md — session context file for Claude AI sessions
- **docs:** Rebuild WAIMS_Coach_Overview.pdf — one-pager with readable table headers, model validation row
- **docs:** Rebuild WAIMS_SportScientist_Overview.pdf — two-pager with V1/V2/V3 table, model validation and evidence review sections

### Style
- **style(command-center):** Replace clinical language with coach language throughout — "heavy legs this week" replaces "high cumulative load", "watch closely" replaces "hidden fatigue", raw numbers removed from morning brief
- **style(command-center):** Replace "HIGH LOAD / LOW ACCELS" GPS labels with "WORKED HARD / MOVING CAREFULLY"

---

## [1.0.0] — February 2026

### Initial Release
- **feat:** Dallas Wings-inspired WNBA monitoring dashboard — 90-day demo, 12 anonymized players
- **feat(dashboard):** 8-tab Streamlit app — Command Center, Today's Readiness, Athlete Profiles, Trends & Load, Jump Testing, Availability & Injuries, Forecast, Insights
- **feat(models):** Random Forest injury risk classifier trained on synthetic monitoring data
- **feat(models):** Evidence-based readiness scorer — hybrid hard safety floors + personal z-score baseline
- **feat(models):** Section 8 model improvement loop — back-to-back validation, pre-injury patterns, readiness-performance correlation
- **feat(data):** generate_database.py — 12 players, 90 days, GPS columns, schedule, injuries, availability
- **feat(data):** espn_data.py — Dallas Wings game results + box scores 2019–2025 (no API key)
- **feat(data):** wnba_api.py — WNBA positional benchmarks (G/F/C) static 2025
- **feat(athlete-profile):** Per-player deep-dive — radar chart, z-score baselines, pill meters, GPS trends, basketball-specific risk context
- **feat(correlation):** Correlation explorer — Pearson heatmap, lag analysis, conditional risk table, ESPN game outcome integration
- **feat(insights):** Natural-language query interface — Ask the Watchlist powered by Claude API
- **research:** Establish evidence base — Walsh 2021 (sleep), Gabbett 2016 (ACWR), Gathercole 2015 (CMJ/RSI), Hulin 2016 (soreness), Impellizzeri 2020 (ACWR critique), Saw 2016 (wellness monitoring)
- **research:** Establish evidence gate policy — Orlando Magic framework, no threshold change without meta-analysis support
- **docs:** Initial README, SETUP_GUIDE, LEARNING_GUIDE, README_PYTHON, RESEARCH_FOUNDATION

---

## Roadmap

### V2 — Production (next milestone)
- Live API connections: Kinexon, ForceDecks/Vald, Teamworks Pulse, Second Spectrum
- Eastward/westward circadian travel penalty (Charest 2021)
- Individualised GPS thresholds as % of each player's max capacity (Pimenta 2026)
- Menstrual cycle phase adjustment to thresholds (WHSP Institute / Bruinvels 2017)
- Force plate profiling — RSI × CMJ scatter plot, force-dominant vs velocity-dominant athlete classification (Adam Kearns IMG Academy framework)
- Slack morning brief + SMS for PROTECT-status players
- Walk-forward model validation, PR-AUC, Precision@K
- Voice input for Ask a Question (Web Speech API)

### V3 — Future
- Drill-level GPS tagging via PlayerMaker/Kinexon timestamp-gated segmentation
- MCP server architecture for live data integrations
- Full injury event validation with real season data
- Athlete-facing simplified readiness view (no injury risk numbers shown to athletes)
