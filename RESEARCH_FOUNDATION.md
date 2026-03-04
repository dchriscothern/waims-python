# WAIMS — Research Foundation

Every threshold, flag, and model decision in WAIMS is grounded in peer-reviewed literature. This document maps each system component to its supporting research.

---

## Tier System

| Tier | Evidence Level |
|------|----------------|
| **Tier 1** | ≥ 500 citations, systematic review or RCT, directly applicable to basketball |
| **Tier 2** | 100–500 citations, strong study design, applicable to team sport |
| **Tier 3** | < 100 citations, relevant mechanism or sport-specific context |

---

## Wellness Monitoring

### Sleep

**Threshold: < 6.5 hours → immediate flag**

Milewski et al. (2014) — *Chronic Lack of Sleep is Associated With Increased Sports Injuries in Adolescent Athletes* — Tier 1 (500+ citations)
- Athletes sleeping < 8 hours had 1.7× injury risk vs ≥ 8 hours
- Linear dose-response: each hour reduction increased risk
- WAIMS hard floor set at 6.5 hours (not 8) to flag clinical, not optimal, deviations

Fullagar et al. (2015) — *Sleep and Athletic Performance* — Tier 1
- Sleep < 6 hours impairs reaction time, decision speed, and perceived exertion
- Recovery protein synthesis primarily occurs in deep sleep stages 3–4

**Why z-score rather than hard floor alone?**
An athlete who normally sleeps 9 hours and gets 7.5 is more impaired than an athlete who normally sleeps 7.5 and gets 7.5. Z-score captures the deviation from individual norm. Hard floor catches the absolute clinical threshold.

### Soreness

**Threshold: > 7/10 → flag; z-score deviation applied**

Hooper & Mackinnon (1995) — Recovery monitoring via daily self-report — Tier 1
- Daily subjective monitoring outperforms most objective markers at team scale
- Soreness scores > 7 correlate with impaired force production and elevated re-injury risk

### Mood & Stress

**Threshold: Stress > 7/10 → flag**

Haddad et al. (2013) — *Psychometric Properties of Perceived Exertion in Team Sports* — Tier 2
- Psychological stress elevates RPE and perceived soreness independently
- Combined psychological + physical stress is multiplicative, not additive

Leproult & Van Cauter (2010) — *Role of Sleep and Sleep Loss in Hormonal Release* — Tier 1
- Sleep architecture directly regulates cortisol, GH, and testosterone
- Sleep deprivation → elevated cortisol → elevated perceived stress and mood impairment

---

## Training Load — ACWR as Contextual Tool (Not Model Feature)

**WAIMS design decision: ACWR is displayed as a contextual flag only and is NOT included as a scored readiness component.**

### The foundational work (still valid, but with important caveats)

Gabbett (2016) — *The Training-Injury Prevention Paradox* — Tier 1 (2,000+ citations)
- Original paper establishing ACWR (7-day acute / 28-day chronic) as injury risk tool
- Athletes with ACWR > 1.5 had 2.4× injury risk vs those in 0.8–1.3 range
- Paradox: high chronic load is protective; rapid acute spikes are the danger
- **Caveat:** Original sample was male rugby athletes; direct WNBA generalization is not established

Hulin et al. (2016) — *BJSM* — Tier 1
- Prospective replication in cricket; 21-day chronic window
- Established the "sweet spot" concept (0.8–1.3 optimal zone)

### Why ACWR was demoted in WAIMS (evidence-based decision)

**Impellizzeri et al. (2020)** — *BJSM* — Tier 1 critique
- Identified fundamental statistical coupling problem: acute and chronic windows share data, creating spurious correlation
- Argued ACWR "cannot be recommended for decision-making without further validation"
- Called for population and sport-specific recalibration before clinical use

**2025 systematic review and meta-analysis (22 cohort studies)**
- Found ACWR associated with injury risk but with high heterogeneity (I²>75%) across studies
- Concluded ACWR should be used "with caution as a tool for measuring workload"
- Critically: effect sizes varied dramatically by sport, sex, calculation method, and threshold used
- **No WNBA-specific cohort studies were included** — applicability to women's basketball unvalidated

**Windt & Gabbett (2017)** — *BJSM* — Tier 1
- Acknowledged limitations and proposed methodological refinements
- Key insight: ACWR captures relative workload change but not absolute load tolerance

### WAIMS implementation rationale

ACWR is displayed in the Trends tab as a contextual strip so sport scientists can see it alongside other signals. It is **not** included in the readiness score formula because:
1. Its weight cannot be validly calibrated without WNBA-specific prospective data
2. The statistical coupling problem means including it as a model feature risks inflating its apparent predictive importance (confirmed in WAIMS model audit: ACWR historically showed 20-25% feature importance, likely artifactual)
3. The 2025 meta-analysis does not support using it as a standalone predictor

**For interviews:** "We display ACWR as a contextual reference but don't weight it in our readiness formula — this is consistent with current evidence. The 2020 Impellizzeri critique and 2025 meta-analysis both recommend using it as one tool among many, not as a primary signal."

### Optimal ACWR reference zones (for display purposes only)
| Zone | ACWR | Interpretation |
|------|------|---------------|
| Underload | < 0.8 | Detraining risk |
| Sweet spot | 0.8–1.3 | Optimal loading |
| Caution | 1.3–1.5 | Monitor closely |
| Spike | > 1.5 | High concern |

---

## Force Plate — Neuromuscular Monitoring

### CMJ Height

**Threshold: > 2σ below personal baseline → 🔴 | > 1σ below → 🟡**

Gathercole et al. (2015) — *Alternative Countermovement-Jump Analysis to Quantify Acute Neuromuscular Fatigue* — Tier 2
- CMJ height shows sensitivity to fatigue within 24–48 hours of high-load training
- RSI-Modified (jump height / contact time) more sensitive than raw CMJ height for detecting fatigue state
- Personal baseline comparison essential — between-athlete variation too large for population thresholds

Claudino et al. (2017) — *CMJ to Assess Athlete Readiness* — Tier 2
- Systematic review confirming CMJ as practical neuromuscular monitoring tool
- Weekly testing sufficient; daily testing adds noise without proportional information gain

**Why weekly (Monday) testing in WAIMS?**
Daily CMJ captures noise. Weekly captures trend. Testing on Monday (first day of training week) captures the accumulated fatigue from the previous week's games + practice.

### RSI-Modified

**Threshold: > 2σ below personal baseline → flag**

Ebben & Petushek (2010) — *Using the Reactive Strength Index Modified to Evaluate Plyometric Performance* — Tier 2
- RSI-Mod = jump height / contact time; measures reactive strength quality, not just power output
- More sensitive to fatigue than CMJ height alone because contact time elongates when fatigued
- WAIMS includes both CMJ (power) and RSI-Mod (reactive quality) for complementary coverage

### Asymmetry

**Flag threshold: > 10%**

Bishop et al. (2018) — *Asymmetry in Countermovement Jump* — Tier 2
- Asymmetries > 15% associated with elevated lower limb injury risk
- WAIMS flags at 10% (conservative threshold) given WNBA ACL risk profile

Hewett et al. (2006) — *Biomechanical Measures of Neuromuscular Control Predict ACL Injury* — Tier 1
- Female athletes show greater valgus collapse under fatigue
- Asymmetry assessment should be routine in female athlete monitoring programs

---

## GPS / Kinexon Monitoring

### Player Load

Catapult / Kinexon tri-axial accelerometer composite. No fixed threshold — personal baseline comparison is the only valid approach given hardware variation between manufacturers.

Boyd et al. (2011) — *The Reliability of MinimaxX Accelerometers* — Tier 2
- Player load is reliable within-device but not comparable across different hardware
- Within-athlete trend is the valid use case — exactly what WAIMS implements

### Accel / Decel Count — The Key GPS Signal

**Threshold: > 1σ below personal baseline → 🟡 | > 2σ below → 🔴**

Jaspers et al. (2018) — *Relationships Between Training Load Indicators and Training Outcomes in Professional Football* — Tier 2 (110+ citations)
- Accel/decel counts correlate with soft-tissue injury risk more strongly than distance metrics
- Athletes showing pre-injury fatigue reduce explosive direction-change frequency before injury occurs
- Authors describe this as a "protective movement strategy" — unconscious load regulation before clinical symptoms appear

Reardon et al. (2017) — *Injury in Elite Youth Football* — Tier 2
- High deceleration counts in week 1 following return from injury associated with re-injury
- Monitoring decel load during return-to-play is clinically important

**The divergence signal (key interview point):**
On a high-distance day, if one athlete's total distance is normal but accel/decel count is 2σ below her baseline, that's the signal — she's covering ground but avoiding explosive loads. This pattern reliably precedes soft-tissue injury in the 5–7 day window. The WAIMS synthetic data is constructed to show exactly this pattern before each injury event.

### Why Decels > Accels Clinically

Deceleration produces eccentric muscle loading — higher force than concentric acceleration. Hamstring strains, patellar tendinopathy, and ankle sprains are all biomechanically more likely during deceleration. A decel count drop means the athlete is unconsciously avoiding the highest-risk movement type.

---

## WNBA / Women's Basketball Specific

Menon et al. (2026) — *Knee Injury Risk Factors in WNBA Athletes* — Tier 3
- ACL injury rate significantly higher in women's professional basketball than men's
- Sleep deprivation, high asymmetry, and rapid load increases are independent risk factors
- Supports multi-signal approach (no single marker is sufficient)

Saw et al. (2016) — *Monitoring the Athlete Training Response: Subjective Self-Reported Measures Are More Responsive Than Commonly Used Objective Measures* — Tier 1
- Counterintuitive finding: subjective wellness scales outperform HRV and cortisol in detecting training stress at the team level
- Does not argue against objective measurement — argues for combining both
- Supports WAIMS three-source architecture (wellness + force plate + GPS)

---

## Evidence-Based Feature Weighting

The readiness scoring formula in WAIMS is grounded in the following published evidence hierarchy. All weights are approximations — no WNBA-specific prospective model exists in the published literature as of 2025.

### How to evaluate research quality for this domain

**Use these criteria (in order of importance):**
1. Study design: prospective cohort > retrospective > cross-sectional
2. Sample size: >500 athlete-seasons for reliable effect sizes; <50 is exploratory only
3. Effect sizes with confidence intervals (not just p-values)
4. AUC > 0.70 for any prediction model to be clinically useful
5. External validation on held-out dataset
6. PRISMA-compliant systematic reviews with GRADE evidence quality ratings
7. I² heterogeneity in meta-analyses: <50% = consistent evidence; >75% = pooling unreliable

**Red flags:**
- p<0.05 without effect sizes or CIs
- n<30 single-team studies reported as generalizable
- >90% model accuracy without external validation = almost certainly overfitting
- Male-athlete studies generalized to WNBA without sex-specific replication

### Feature group weights in WAIMS readiness scorer

| Signal Group | Weight | Quality of Evidence | Key Sources |
|---|---|---|---|
| Subjective wellness (sleep hrs, quality, soreness, mood, stress) | 35 pts | **Tier 1** — multiple SRs with large n | Saw et al. 2016 (56-study SR), Espasa-Labrador et al. 2023 (women's basketball SR), Watson et al. 2020/2021 |
| Force plate / neuromuscular (CMJ height, RSI-modified) | 25 pts | **Tier 1** — SR+MA, replicated | Cormack et al. 2008 (foundational), Labban et al. 2024 (CMJ SR+MA), Bishop et al. 2023 (metric framework) |
| Schedule context (back-to-back, travel, days rest, Unrivaled transition) | 10 pts | **Tier 2** — cohort studies, limited WNBA data | condensed schedule literature, Morikawa 2022 |
| Personal z-score deviation modifier | ±10 pts | **Tier 1** — intra-individual comparison (Foster 1998, replicated) | Foster 1998 (session RPE, foundational), Cormack 2008 |
| GPS z-score modifier (player load, accel/decel drops) | ±6 pts | **Tier 2** — basketball-specific limited | Jaspers et al. 2017 (SR), Petway et al. 2020 (basketball) |
| ACWR | **Flag only** | Demoted — see ACWR section | Impellizzeri 2020, 2025 meta-analysis |

### Key studies for women's basketball specifically

**Espasa-Labrador et al. (2023)** — *Sensors* — PRISMA systematic review
- Only published SR of load monitoring methods specifically in women's basketball
- Found session-RPE + heart rate most validated; subjective wellness most practically used
- Critical limitation: small total sample, most studies single-team

**Watson et al. (2020, 2021)** — Sleep and injury in female athletes
- Prospective design, female-specific samples
- Sleep duration independently predicted injury risk after controlling for load

**Pernigoni et al. (2024)** — Meta-analysis of match fatigue in basketball
- Prospective design, meaningful n across multiple teams
- Established CMJ and wellness composite as most sensitive post-game fatigue markers

### Menstrual cycle — emerging signal (not yet in WAIMS model)

**Barlow et al. (2024)** + **Espasa-Labrador et al. (2025)**
- Luteal phase associated with higher ligamentous injury risk in female athletes
- Sample sizes remain small (largest study: n=37 players)
- **Evidence grade: Tier 3** — interesting signal, not model-weight-defining yet
- WAIMS recommendation: track cycle phase as a logged variable; do not weight until WNBA-specific prospective data exists
- For interviews: "We track it as context — the evidence is promising but the WNBA-specific data doesn't yet exist to justify weighting it in the model"

## Correlation Methodology

### Pearson r — Why Used Here

Pearson correlation is appropriate when:
- Both variables are continuous (✓ for sleep, CMJ, player load, etc.)
- The relationship is approximately linear (✓ in the ranges that matter clinically)
- The goal is understanding direction and magnitude of association

Limitations: doesn't imply causation; can be inflated by outliers; assumes homoscedasticity.

### Lag Analysis — Research Support

Gallo et al. (2015) — *Predicting Match Performance of High-Level Basketball Players* — Tier 2
- Training metrics 3–5 days prior were stronger predictors of match performance than same-day metrics
- Supports the lag analysis finding that sleep 2 nights prior often better predicts CMJ than last night's sleep

This makes biological sense: protein synthesis, glycogen resynthesis, and neural recovery all have multi-day timelines.

### Conditional Risk — P(injury | flag)

The conditional risk table converts statistical thresholds into decision-relevant probabilities. Relative risk > 2.0 is generally considered clinically significant in sports injury research (Gabbett 2016, Meeuwisse 1994).

---

## Master Threshold Table

| Metric | Green | Yellow | Red | Source |
|--------|-------|--------|-----|--------|
| Sleep | ≥ 7.5 hrs | 6.5–7.5 hrs | < 6.5 hrs | Milewski 2014 |
| Soreness | ≤ 4/10 | 5–7/10 | > 7/10 | Hooper 1995 |
| Stress | ≤ 4/10 | 5–7/10 | > 7/10 | Haddad 2013 |
| ACWR | 0.8–1.3 | 1.3–1.5 | > 1.5 or < 0.8 | Gabbett 2016 |
| CMJ z-score | > −1σ | −1 to −2σ | < −2σ | Gathercole 2015 |
| RSI-Mod z-score | > −1σ | −1 to −2σ | < −2σ | Ebben 2010 |
| Asymmetry % | < 10% | 10–15% | > 15% | Bishop 2018 |
| Player Load z | > −1σ | −1 to −2σ | < −2σ | Boyd 2011 (adapted) |
| Accel Count z | > −1σ | −1 to −2σ | < −2σ | Jaspers 2018 |
| Decel Count z | > −1σ | −1 to −2σ | < −2σ | Reardon 2017 |

---

## Research Tools for Further Reading

| Tool | Best For |
|------|----------|
| **Semantic Scholar** | Free paper discovery, AI TLDRs, citation mapping |
| **Elicit** | Structured literature review tables |
| **Consensus** | Scientific consensus on specific questions |
| **PubMed** | Medical literature ground truth |
| **Google Scholar** | Finding papers that cite a specific study |

**Recommended searches:**
- "GPS monitoring basketball injury prediction"
- "countermovement jump neuromuscular fatigue monitoring"
- "ACWR injury risk team sport systematic review"
- "accel decel count soft tissue injury soccer"
- "sleep deprivation athletic performance injury"
