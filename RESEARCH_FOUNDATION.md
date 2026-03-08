# WAIMS — Research Foundation

Evidence basis for all monitoring thresholds and model weights.

Evidence grades:
- ★★★ Systematic review, meta-analysis, or RCT
- ★★  Observational cohort study
- ★   Clinical estimate or expert consensus (no direct research)

---

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

165 studies in systematic review. 27 studies in meta-analysis. 20 readiness markers evaluated.
**Key findings directly applied in WAIMS:**
- CMJ jump height: large correlation with sprint performance (r = 0.69, p = .00) — strongest validated readiness-to-performance link
- CMJ peak power and squat jump: non-significant correlations — validates WAIMS choice of CMJ height/RSI over power metrics
- 5 markers meta-analysed: CMJ, HRV (RMSSD/SD1), sub-maximal HR, sRPE
- HRV (RMSSD): significant correlation with performance — supports HRV as V2 addition
- Sub-maximal HR: significant correlation — validates aerobic readiness monitoring
- sRPE: significant correlation — validates subjective wellness as legitimate signal alongside objective measures

*WAIMS application: Primary evidence base for CMJ z-score as the highest-weighted readiness signal (35pts).
Validates the three-source architecture (subjective + neuromuscular + GPS) as each marker class
showed independent predictive validity. Also supports HRV as the most valuable V2 addition.*
*Citation: Janetzki SJ, Bourdon PC, Burgess DJ, Barratt GK, Bellenger CR. (2023). Scientific Journal of Sport and Performance, 2(3), 339–380.*

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
