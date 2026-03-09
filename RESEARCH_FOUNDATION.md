# WAIMS — Research Foundation

Evidence basis for all monitoring thresholds and model weights.

Evidence grades:
- ★★★ Systematic review, meta-analysis, or RCT
- ★★  Observational cohort study
- ★   Clinical estimate or expert consensus (no direct research)

---



## Research Philosophy & Contextual Adjustment

### Evidence-Driven, Context-Informed

WAIMS thresholds are grounded in peer-reviewed systematic reviews and meta-analyses.
However, published thresholds are derived from heterogeneous sport populations — often soccer,
rugby, or mixed sport samples — and no evidence gate replaces the judgment of experienced
practitioners working with a specific team.

**The WAIMS evidence policy is:**
> Thresholds are set by research. Thresholds are adjusted by context.

### Why Basketball Context Matters

Basketball has specific characteristics that differentiate it from the sports most represented
in the monitoring literature:

- **Multi-directional, high-deceleration demands** — distinct from linear team sports (soccer, rugby)
- **WNBA pace of play** — shorter shot clock, different movement density vs NBA or European leagues
- **Positional differentiation** — guards carry different acute and chronic load profiles than forwards/centers
- **Schedule density** — 40-game WNBA regular season with back-to-backs differs structurally from soccer weekly cycles
- **Female physiology** — recovery rates, hormonal variability, and neuromuscular response differ from male-derived norms

### RSI-Modified — Context Note

RSI-Modified (25pts in WAIMS) is validated primarily by Gathercole et al. (2015) in elite female
rugby sevens athletes — the closest available female team sport population. The 2023 Janetzki
meta-analysis did not include RSI as a meta-analysed marker (insufficient standardised studies).

NBA and WNBA teams use RSI-Mod and drop jump alongside CMJ height because they measure
different qualities:
- **CMJ height** — explosive output, acceleration readiness (Janetzki 2023 validated)
- **RSI-Modified** — reactive strength, stretch-shortening cycle efficiency, more sensitive to
  accumulated fatigue and overreach (Gathercole 2015)

Both belong in a basketball monitoring system. The Janetzki finding validates CMJ height specifically;
the absence of RSI from that meta-analysis reflects insufficient standardised studies, not evidence
against its use.

### Threshold Adjustment Process

In a real high-performance department, WAIMS thresholds should be reviewed:

1. **With coaching staff** — do flagged athletes match coach intuition? (V1 validation method)
2. **With medical/athletic training** — do thresholds align with clinical observations?
3. **Against team historical data** — do z-score flags precede actual performance decrements or injury?
4. **In context of schedule** — preseason, regular season, and playoff thresholds may legitimately differ
5. **Without silos** — sport science, coaching, and medical staff should inform threshold decisions together

No threshold change without meta-analysis support is the evidence gate for new published research.
Contextual adjustment based on practitioner judgment, team data, and interdepartmental collaboration
is a separate and essential layer that published research cannot replace.

*This is how the Orlando Magic framework operates in practice: evidence sets the starting point,
practitioners calibrate to their specific context.*


## Data Quality & Imputation Policy

### Philosophy
Imputation is never neutral. Every fill-in makes an assumption about WHY data is missing.
In athlete monitoring, missing data is often NOT random — a player who skipped her morning
check-in after a back-to-back is likely the one you most need to flag.

Every imputation decision in WAIMS is explicit, logged, and auditable via `data_quality.py`.
No silent fills. Sport scientists can review every action taken on the data.

### Tiered Imputation by Data Type

| Data Type | Missing Handling | Rationale |
|---|---|---|
| Wellness check-in (missing submission) | Flag only — NOT imputed. Add `wellness_submitted=0` as model feature | Non-submission is informative, especially post B2B |
| Force plate CMJ / RSI | LOCF up to 3 days, staleness flag after | Sessions infrequent by design; LOCF defensible for short gaps |
| GPS / training load spikes (>3σ) | Winsorise to 3σ cap, preserve original in `*_original` column | Spikes >3σ likely device error, not athlete signal |
| Sleep hours (≤2 consecutive missing days) | Personal 14-day rolling mean | Sleep has strong personal autocorrelation; population mean inappropriate |
| Sleep hours (>2 consecutive missing days) | Flag only — NOT imputed | Extended gap needs manual review |
| ACWR (<7 days load history) | Flag as unreliable | Ratio meaningless with insufficient denominator |

### Basketball-Specific Notes
- **Back-to-back scheduling**: missing wellness the morning after a B2B is likely load-related, not random.
  NEVER silently impute — flag explicitly with `b2b_missing=1`
- **Positional differences**: team-level mean imputation inappropriate; centers and guards have
  structurally different baselines. Always use personal rolling mean
- **Short WNBA season** (40 games): rolling windows use 7–14 days, not 28+ days from soccer literature
- **Travel direction**: eastward travel is a known confounder for next-day wellness. Missing data
  on eastward travel days gets an additional travel flag in V2
- **Injury day exclusion**: the injury day itself is excluded from model training features
  to prevent leakage

### Alignment with Mercury WNBA Project
Personal rolling baseline imputation for continuous metrics aligns with the standard academic
sport science approach. LOCF for infrequent assessments. Missing as a signal (not imputed)
for daily subjective measures. This is consistent with the imputation approach used in the
Mercury project and with NBA/WNBA practitioner standards.

### Implementation
`data_quality.py` — `DataQualityProcessor` class handles all tiers with full audit logging.
`show_data_quality_report()` renders the audit panel in the Insights tab.

---

## Model Validation Framework

### Philosophy (Julius.ai Recipe)
The biggest trap in athlete monitoring ML is validating in a way that leaks future information
or overstates performance because data is highly autocorrelated within a player and across days.

Two mandatory validation views are required:

**View 1 — Walk-Forward Time Splits** ("Will it work next week?")
```
Train days 1-45  → Validate days 46-60
Train days 1-60  → Validate days 61-75
Train days 1-75  → Validate days 76-90
```
Prevents peeking at later-season distributions. Captures concept drift.

**View 2 — Player Holdout / GroupKFold** ("Will it work for a new signing?")
Hold out 2-3 players entirely, train on rest. Tests generalisation to new athletes.

### Metrics by Model Type

**Injury risk (classification, imbalanced):**
- **PR-AUC** (headline) — handles class imbalance; "when we flag risk, how often right?"
- **Precision@K top 3/day** — matches real operational constraint (staff can intervene on ~3/day)
- **Lead-time distribution** — flags 3-7 days before injury are useful; same-day flags are not
- **Calibration + Brier score** — if model says 30% risk, does injury happen ~30% of the time?
- ROC-AUC (secondary reference only — can look great when operationally mediocre)

**Readiness score (ranking):**
- **Spearman correlation** vs coach intuition. V1 target: ≥0.70 on 70%+ of days
- **Day-to-day stability** — score shouldn't change >20pts without a real wellness change
- MAE/RMSE if trained against an objective performance proxy

### Baselines to Beat
| Baseline | What it tests |
|---|---|
| ACWR > 1.5 heuristic | Does model add value over load ratio alone? |
| 7-day acute load spike rule | Does model add value over volume monitoring? |
| Player z-score on soreness | Does model add value over single-metric flag? |

### Ablation Studies
Remove GPS features / wellness features / schedule features / force plate features individually.
If performance barely changes, the ablated features are not contributing signal.

### Error Analysis
- **False positives**: were they near-misses (tightness, modified practice)? If yes, operationally correct
- **False negatives**: contact injuries and acute trauma are expected misses; unexplained non-contact misses need investigation
- **Per-player performance**: flag rate >30%/day is suspicious — systematic over-flagging for one player erodes coach trust

### V1 vs V2 Targets
| Stage | Method | Target |
|---|---|---|
| V1 Demo | Spearman vs coach intuition | ≥0.70 on 70%+ of days |
| V2 Production | Walk-forward + GroupKFold | PR-AUC > ACWR baseline; Precision@3 > 0.40 |
| V2 Production | Lead-time analysis | Median flag 3+ days before non-contact injury |
| V2 Production | Per-player performance | No player with flag rate >30%/day without injury history |

### Non-Contact Scope
Non-contact soft tissue injuries are the primary validation target.
Contact injuries are explicitly excluded — the model is not expected to predict these.

### Implementation
`model_validation.py` — contains all validation functions, baseline models, and Streamlit display.

## Recommended Evidence Sources for WAIMS

### Primary Literature (automated via research_monitor.py)
| Source | Access | Use |
|---|---|---|
| **PubMed** | Free, no key | Primary literature. WAIMS monitor searches 10 targeted queries weekly. |
| **SPORT Discus** | Library/institutional | Best sports science database — broader than PubMed for applied sport. Search manually. |
| **Google Scholar** | Free | Citation tracking — find what cited Gathercole 2015, Walsh 2021, etc. to surface newer work. |
| **Semantic Scholar** | Free | AI-generated TLDRs + citation graphs. Good for rapid screening. |

### Practitioner Layer (manual weekly review)
| Source | Access | Use |
|---|---|---|
| **Sportsmith** | $13/month | Applied practice translation (Jo Clubb deceleration series, Tim Gabbett). Best practice layer. |
| **Martin Buchheit / SPSR** | Free RSS | GPS 3.0, load monitoring methodology. Auto-monitored via research_monitor.py. |
| **BJSM Blog** | Free RSS | Walsh 2021 sleep consensus, Impellizzeri ACWR critique. Auto-monitored. |
| **Science for Sport** | Free + paid tier | Practitioner-facing research summaries. Good for staying current without reading full papers. |

### What ScienceConnect.io Is (not a search tool)
ScienceConnect.io is a Wiley single-sign-on platform — lets you access multiple academic publishers
with one account. Not a research discovery tool. Not relevant for WAIMS monitoring.

### Sports Science AI (Recommended for Real-Team Deployment)
**sportscienceai.com** — purpose-built AI research assistant for sport science.
- Database updated weekly with latest research (not general web training data)
- Citations for every referenced paper — no hallucinations
- Tailored for sport science, not general knowledge
- Handles the deep "what does the literature say about X" questions that PubMed queries miss
- Covers journals outside PubMed (e.g. Scientific Journal of Sport and Performance)
- For a real team: replaces manual gap searches entirely alongside the automated PubMed monitor
- Flagged as V2 tooling — paid subscription, appropriate when working with a real organisation

*Together, automated PubMed monitoring (already built) + Sports Science AI gives full coverage
without any manual periodic searches.*

## Sleep

### Primary Threshold: < 7.0 hrs → yellow flag | < 6.0 hrs → red flag

**Walsh et al. 2021** ★★★  
BJSM expert consensus statement on sleep and athletic performance.  
Recommends 7–9 hrs for elite athletes. Sub-7 associated with elevated injury risk,  
impaired neuromuscular function, and reduced cognitive performance.  
*Citation: Walsh NP et al. (2021). Sleep and the athlete: narrative review and 2021 expert consensus recommendations. BJSM.*

**2025 Meta-analysis** ★★★  
Shorter sleep duration significantly associated with injury risk (OR = 1.34, 95% CI 1.08–1.66).  
Each additional hour of sleep associated with OR = 0.52 for injury.  
Athletes sleeping < 8 hrs: relative risk 1.70 in one included study.  
Female athletes: inadequate sleep compounds hormonal variability, impairs neuromuscular control.

**Charest & Grandner 2020** ★★  
Female-specific sleep considerations — hormonal variability (menstrual cycle, hormonal contraception)  
affects sleep architecture and recovery quality independent of duration.

**Previous threshold (retired):** Milewski et al. 2014 — < 6.5 hrs → 1.7× injury risk.  
Retained for historical reference but superseded by Walsh 2021 consensus and 2025 meta-analysis.  
New threshold: < 7.0 hrs reflects current evidence base.

---

## Force Plate — CMJ & RSI

**Gathercole et al. 2015** ★★★  
CMJ and RSI-Modified as neuromuscular fatigue monitoring tools.  
> 2 SD drop from individual baseline = meaningful neuromuscular fatigue signal.  
RSI-Mod more sensitive than peak power for detecting overreach.  
*WAIMS weight: CMJ 15pts, RSI 10pts in readiness score.*

**Labban et al. 2024** ★★  
Female basketball — CMJ force-time variables predict next-day readiness.  
Asymmetry > 10–15% associated with elevated injury risk in female athletes.  
*WAIMS threshold: asymmetry_pct > 15% = flag.*

**Bishop et al. 2023** ★★  
RSI-Modified sensitivity in women's basketball — validated cutoffs for flag thresholds.


**Janetzki et al. 2023** ★★★
*"Assessing athlete readiness using physical, physiological, and perceptual markers: A systematic review and meta-analysis"*
Scientific Journal of Sport and Performance, 2(3), 339–380. DOI: 10.55860/AGRH6754

165 studies in systematic review. 27 studies in meta-analysis. 20 readiness markers evaluated across 46 sports.
Searched MEDLINE, Embase, Emcare, Scopus, SPORT Discus through March 2023.

**Key meta-analysis findings (only statistically significant result):**
- CMJ **jump height** (without arm swing), acute cross-sectional: large, significant correlation with 10m sprint speed/time (r = 0.69, 95% CI 0.47–0.83, p = .00, I² = 71.4%)
- CMJ **peak power**: non-significant with 10m sprint time (r = 0.13, p = .87) — power metrics not validated
- Squat jump height: non-significant (r = 0.70, p = .17 — large effect but underpowered, n=3 studies)
- CMJ height vs total distance (longitudinal): non-significant (r = 0.38, p = .41)
- HRV (RMSSD + SD1) vs Yo-Yo IR1: non-significant (r = 0.66, p = .31)
- Sub-maximal HR vs Yo-Yo IR1: non-significant (r = -0.65, p = .47)
- Salivary cortisol and blood CRP biomarkers: non-significant across all performance measures

**Critical nuance for WAIMS:**
CMJ jump height predicts **sprint and acceleration** qualities — not endurance or total distance.
This means CMJ is a readiness-to-perform (explosive output) signal, not purely a fatigue-from-load signal.
The paper explicitly states practitioners should "use caution" applying CMJ to predict total distance or maximal speed.

**WAIMS application:**
- Validates CMJ jump height as the primary neuromuscular readiness marker (35pts in formula)
- Does NOT validate CMJ peak power — confirms WAIMS correctly uses height, not power
- RSI-Modified (25pts in WAIMS) not meta-analysed in this paper — evidence base remains Gathercole 2015 specifically
- HRV non-significant here — supports current WAIMS decision not to include HRV in V1; revisit for V2 with better standardisation
- Biomarkers (CK, cortisol, CRP) non-significant — confirms WAIMS correctly excludes invasive biomarkers from scoring

*Citation: Janetzki SJ, Bourdon PC, Burgess DJ, Barratt GK, Bellenger CR. (2023). Assessing athlete readiness using physical, physiological, and perceptual markers: A systematic review and meta-analysis. Scientific Journal of Sport and Performance, 2(3), 339–380. https://doi.org/10.55860/AGRH6754*

**Cormack et al. 2008** ★★  
CMJ monitoring protocol — individual baseline approach superior to population norms  
for detecting meaningful fatigue in small-squad settings.

---

## ACWR (Acute:Chronic Workload Ratio)

**Status in WAIMS: Contextual flag only — NOT weighted in readiness score or model**

**Gabbett 2016** ★★  
Original ACWR paper — sweet spot 0.8–1.3, > 1.5 = elevated injury risk (2.4×).  
Foundational but now critiqued for methodological limitations.

**Impellizzeri et al. 2020** ★★★  
Statistical coupling critique — ACWR numerator and denominator share data,  
creating mathematical artifact in the correlation with injury.  
Recommends "use with caution" as standalone metric.

**2025 ACWR Meta-analysis** ★★★  
Confirms Impellizzeri concerns. ACWR remains useful as a directional flag  
but should not be the primary weighted feature in injury risk models.

*WAIMS implementation: ACWR displayed with ⚠ indicator. Back-to-back (days_rest),  
travel_flag, and time_zone_diff replace ACWR as schedule load features in the model.*

---

## Schedule Context

**Back-to-back penalty: -4 pts** ★★  
Based on condensed schedule literature (Morikawa 2022 NBA, translated to WNBA context).  
ESPN game data validation (Section 8, train_models.py) will replace this estimate  
with data-driven evidence once sufficient real monitoring data accumulates.

**Travel/timezone penalty: up to -3 pts** ★  
Scaled by timezone difference. Clinical estimate — no WNBA-specific published research.  
General travel fatigue literature supports directional effect.

**Days rest < 2: -2 pts** ★★  
Short recovery window associated with performance decrements in team sports literature.

**Unrivaled transition: -2 pts** ★ (clinical estimate only)  
No published research on Unrivaled-to-WNBA transition load.  
Rationale: 72ft court vs 94ft WNBA (23% shorter), 18s shot clock, 3-quarter format.  
Different movement demands, acceleration patterns, game density.  
*Flagged for prospective validation with actual transition data.*

---

## Injury Risk — General

**Saw et al. 2016** ★★★  
Systematic review of subjective wellness monitoring in elite athletes.  
Validates multi-item wellness questionnaires (sleep, fatigue, stress, mood) as  
sensitive to training load changes and injury risk.

**Watson 2017** ★★  
Sleep and athletic performance review — validates sleep hours as primary recovery metric  
over sleep quality ratings in team sport settings.

---

## Female Athlete Specific

**Espasa-Labrador et al. 2023** ★★  
ACL injury risk in female basketball — biomechanical and hormonal factors.  
Asymmetry thresholds may need adjustment for female athletes vs male norms.

**Stojanovic et al. 2025** ★★★  
Female basketball workload monitoring — positional differences in load tolerance.  
Guards tolerate higher relative loads than forwards/centers before performance decrements.

**Menstrual cycle tracking** ★  
Graded Tier 3 in WAIMS (track but don't weight in model).  
Insufficient evidence for individualized threshold adjustment.  
Recommend prospective tracking to identify individual patterns.

---

## Research Quality Framework

Applied to all thresholds in WAIMS:

| Grade | Evidence type | Action |
|-------|--------------|--------|
| ★★★ | Systematic review / meta-analysis / RCT | Use as primary threshold |
| ★★ | Observational cohort, prospective | Use with noted limitations |
| ★ | Expert consensus / clinical estimate | Use with explicit ★ label, flag for validation |
| No research | Novel situation (e.g. Unrivaled) | Document assumption, plan prospective data collection |

All ★ thresholds in WAIMS are explicitly labeled in source code comments  
and in dashboard research references.

## External Analysis Attribution

**Gemini AI analysis (2026-03-06):** Reviewed coach_command_center.py and identified three 
highest-utility additions for NBA/WNBA environments:
1. Positional Group Readiness Strip — guards/wings/bigs unit averages (implemented V1.1)
2. Minutes Cap on roster cards — prescriptive per-player limit (implemented V1.1)  
3. Hidden Fatigue Flag — READY but trending down under load (implemented V1.1)

Items 4 (OUT/GTD Availability distinction) and 5 (Projected Impact squad toggle) deferred to V2.
Item 4 partially covered by Availability tab. Item 5 is squad-level load projection — V2 roadmap.

## Key Institutions to Monitor

### WHSP Institute (Women's Health, Sports & Performance)
- **URL:** whspinstitute.org
- **Launched:** January 29, 2026
- **Investment:** $50M+ from Clara Wu Tsai (co-owner, New York Liberty) and co-founders
- **Led by:** Dr. Kate Ackerman (triple board-certified, global leader in female athlete health)
- **Research team:** Dr. Trent Stellingwerff (150+ peer-reviewed publications, IOC consensus statements)
- **Relevance to WAIMS:** Directly addresses every female-specific gap in WAIMS — hormonal cycle, ACL risk, recovery rates, biomechanics. Their publications appear on PubMed and are automatically caught by the evidence monitor.
- **Monitoring approach:** PubMed (automated weekly via GitHub Actions) + quarterly manual check of whspinstitute.org/our-research. Do NOT scrape — new institute, small team, manual is appropriate.
- **WAIMS connection:** Less than 10% of sports science research has historically focused on women (Ackerman 2026). WAIMS is explicitly designed to use female-specific baselines (Goulart 2022, Pernigoni 2024) rather than male-derived norms. WHSP research will directly improve V2 features: menstrual cycle phase adjustment, female-specific CMJ recovery rates, ACL risk context.

### Travel Direction & Circadian Science
- **Key finding:** Eastward travel is harder than westward. The human circadian rhythm runs ~24.25 hours, making it naturally easier to delay (westward) than advance (eastward).
- **NBA evidence:** Teams traveling eastward won 44.51% vs 40.83% when traveling westward (Charest et al. 2021 JCSM). Circadian misalignment and travel distance both negatively influence performance, interacting significantly (Chronobiology International, 9,840 NBA games, 2014-2018).
- **Current WAIMS treatment:** B2B flag only — no directional awareness. Dallas Wings flying east (e.g., to New York, Washington) warrants a higher penalty than flying west (e.g., to Seattle, LA).
- **V2 roadmap:** Add `travel_direction` field (east/west) and `time_zones_crossed` to the schedule context. Apply asymmetric circadian penalty: eastward = ~1 day/time zone to resync; westward = ~0.5 day/time zone.

---

## Model Validation Framework

### Current Approach (V1): Readiness Score — Coach Intuition Alignment

WAIMS does not currently operate as a trained injury classifier. The forecast tab produces a **risk score watchout** — a heuristic composite — not a validated predictive model. This is the correct posture for a system without sufficient real-team injury event data.

**Primary validation question (V1):**
> Does the readiness score ranking match what the coach already knows?

This is the most meaningful validation available at this stage. A readiness score that consistently surprises the coaching staff is a red flag. A score that surfaces the same 2–3 athletes the coach was already watching — with a clear explanation — builds trust.

**V1 validation method:**
- **Spearman rank correlation** between WAIMS readiness ranking and coach's informal daily assessment
- Target: coach agrees with top and bottom 3 athletes flagged on ≥ 70% of days
- Collected informally — coach feedback after morning brief, noted in session log
- No formal injury event validation required at V1 (insufficient events in demo data)

**Operational framing:**
WAIMS flags the right 2–3 athletes for a coach each morning. Precision@K (top 3) is more meaningful than row-level accuracy. The goal is not to be right about every player — it is to surface the most important conversations before practice.

---

### V2 Validation Upgrades

When real team data accumulates (minimum 1 full season recommended):

**Time-aware validation (walk-forward splits)**
Train on days 1–45, validate on 46–60. Repeat across the season. Prevents future data leakage and captures load pattern drift across the schedule. This is the most important methodological upgrade.

**Player-holdout test**
GroupKFold by `player_id` — answers whether the model generalises to a new signing with limited history. Stress test for roster turnover scenarios.

**Injury classification metrics (if sufficient events)**
- PR-AUC (primary — handles class imbalance)
- Calibration curve + Brier score (is the model's 30% risk actually 30%?)
- Lead-time analysis: flags arriving 3–7 days before injury are operationally useful; same-day flags are not

**Simple baselines to beat**
Model must outperform:
- Acute load threshold rule (last 7 days)
- ACWR heuristic
- Player rolling z-score on soreness/fatigue alone

**Ablation studies**
Test model without GPS features, without wellness features, without schedule features. Identifies which data streams are actually driving signal vs noise.

**Injury type stratification**
Non-contact soft tissue injuries (load-related) should be predictable. Contact injuries should not be expected to validate well — document this explicitly so coaches understand model scope.

---

### Dashboard Transparency Note

The WAIMS dashboard surfaces the validation philosophy directly to sport scientists via the Insights tab. Coaches see decision-ready outputs. Sport scientists see the evidence grade, threshold source, and validation status behind every metric.

*Validation framework informed by Julius.ai model validation analysis (2026). Applied and adapted for WAIMS operational context.*
