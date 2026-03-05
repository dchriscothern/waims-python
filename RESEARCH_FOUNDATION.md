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
