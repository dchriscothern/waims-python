# WAIMS — Learning Guide

For interviews, presentations, and self-study. Explains the *why* behind every design decision.

---

## What Is WAIMS?

WAIMS (Wellness & Athlete Injury Management System) is a professional-grade athlete monitoring
dashboard built for a WNBA team context. It combines:

- **Subjective data** — daily wellness questionnaires (sleep, soreness, stress, mood)
- **Objective neuromuscular data** — force plate testing (CMJ, RSI-Modified)
- **Objective external load data** — GPS/Kinexon (player load, accel/decel counts, distance)
- **Machine learning** — Random Forest injury risk predictor trained on all signals simultaneously
- **Statistical correlation analysis** — surfaces hidden relationships between metrics
- **Automated evidence monitoring** — weekly PubMed + RSS triage with formal decision gate

The system is designed around two personas: a **coach** who needs situational awareness in
30 seconds, and a **sport scientist** who needs deep analytical tools.

---

## The Two-Persona Architecture

### Why not just build one dashboard?

Pro tools (Catapult, Kinexon, Teamworks) all structure their interfaces around roles:
- Coaches see traffic lights. They make real-time decisions. They don't have time for σ notation.
- Sport scientists need z-scores, lags, conditional probabilities, and model audit trails.

**Tab 1 — Command Center** serves the coach. Everything else serves the analyst.
This is the correct architecture for a real deployment.

---

## 8 Tabs Explained

### 🏀 Tab 1 — Command Center
The most important tab. Answers in one glance:
- Who can go hard today? (green)
- Who do I protect? (red)
- What is the team GPS load situation?
- What are my top 3 action items?

The Positional Group Readiness Strip shows Guards / Wings / Bigs averages above the roster
cards — coaches can adjust drill intensity by unit before the session.

The alert engine surfaces only the highest-severity finding per player. A coach sees
"No explosive loading for Bueckers today" — not a wall of z-scores.

Hidden Fatigue Flag: players who show READY (≥80%) but are trending down under high load
(>100 min/4d) get an amber flag. This is the load accumulation signal that precedes
the score actually dropping into MONITOR territory.

### 📊 Tab 2 — Today's Readiness
The analyst version of Tab 1. Every player, every signal, every z-score visible.
Compact and detailed views. GPS panel shows Kinexon numbers with σ delta so you can
explain the number in a sentence.

### 👤 Tab 3 — Athlete Profiles
The full story per athlete. Radar chart covers six dimensions: Sleep / Physical / Mental /
Load / Neuro / GPS. The GPS section has a 14-day trend chart with Player Load on the left
axis and Accel/Decel Count on the right — divergence between these two axes is a key
fatigue signal.

### 📈 Tab 4 — Trends & Load
7-day rolling average overlaid on raw daily values. Used to identify gradual drift vs
acute spikes. GPS/Kinexon load trends are merged into this same tab — sleep, soreness,
player load, and accel/decel all in one place with 7-day rolling context. A coach saying
"she's been off all week" is visible here before it becomes a flag.

### 💪 Tab 5 — Jump Testing
CMJ and RSI-Modified. Tested weekly (Mondays in the synthetic data). Z-scored vs personal
30-day baseline. Research shows CMJ drops of ≥ 2σ predict impaired performance and elevated
injury risk (Gathercole 2015). Asymmetry > 10% flags lateral imbalance.

### 🚨 Tab 6 — Availability & Injuries
The medical/GM view. Status board (AVAILABLE / QUESTIONABLE / OUT), season availability %,
and full injury log. Real deployments would integrate with team EMR.

### 🤖 Tab 7 — Forecast
The GM view. 7-day risk watchlist. "Why she's here" narrative pulls every contributing
flag. GPS flags appear at the bottom of each risk card and add weight to the composite
risk score (at lower weight than CMJ/RSI, because objective mechanical signals are
prioritised over load metrics).

Load Projection: select a player and a game scenario (rest, typical game, heavy game,
back-to-back) and see projected readiness tomorrow with a specific staff recommendation.
Evidence-based adjustments use female-specific basketball recovery literature
(Pernigoni 2024 44-study SR, Goulart 2022 female meta-analysis).

### 🔬 Tab 8 — Insights
The sport scientist's analytical home. Four sections:

**Ask a Question** — Natural language shortcuts. No SQL. No dashboard literacy required.
Type "accel drop" — get the list of athletes whose accel count is ≥ 1σ below their personal
30-day norm, with 🔴/🟡/🟢 status. Staff who aren't sport scientists can use this independently.

**Model Validation Philosophy** — Documents the V1 validation approach (Spearman rank
correlation vs coach intuition) and the V2 upgrade path (walk-forward splits, PR-AUC,
Precision@K). Collapsible expander — sport scientist audience only, not visible to coaches.

**Evidence Review** — Weekly automated PubMed + RSS triage. Forward-looking inbox.
Foundational papers are already in RESEARCH_FOUNDATION.md. This surfaces NEW research.
Decision buttons: Integrate / Watchlist / Reject / Reset. Decisions saved to
research_log.json. Policy: no threshold change without meta-analysis support.

**Signal Correlations** — The research tool. Correlation heatmap, lag analysis, conditional
risk table, per-player breakdown, and model feature audit. Five sub-sections covered below.

---

## The Z-Score Engine

### Why personal baselines, not population averages?

A soreness score of 6/10 means very different things for different athletes. For an athlete
whose baseline is 2, it's a significant deviation. For an athlete whose baseline is 5, it's
normal. Population-average thresholds (the common approach) miss this entirely.

WAIMS uses an **expanding personal baseline** for each athlete:

```python
roll_mean = df.groupby("player_id")[col].transform(
    lambda x: x.shift(1).expanding(min_periods=5).mean()
)
roll_std = df.groupby("player_id")[col].transform(
    lambda x: x.shift(1).expanding(min_periods=5).std().clip(lower=min_std)
)
z_score = (today_value - roll_mean) / roll_std
```

The `shift(1)` prevents data leakage — today's value isn't included in its own baseline.

### Flag thresholds

| z-score | Status | Meaning |
|---------|--------|---------|
| ≤ −2.0 | 🔴 | Severe deviation — >2 standard deviations below normal |
| ≤ −1.0 | 🟡 | Moderate deviation — worth monitoring |
| > −1.0 | 🟢 | Within normal personal range |

For GPS metrics (load, accels, decels), **negative** z-scores are the concerning direction —
they indicate the athlete is doing less than normal, which is the fatigue/protective movement
signal.

---

## Three-Source Flag System

```
Wellness (subjective)     →  sleep z, soreness z, stress z, mood z
Force Plate (objective)   →  CMJ z, RSI-Mod z, asymmetry
GPS / Kinexon (objective) →  player load z, accel z, decel z
```

Why three sources? Because each has different failure modes:

- **Wellness only** — athletes misreport or suppress scores; confirmed by Saw et al. (2016)
  that subjective methods work but need calibration
- **Force plate only** — tested weekly, misses daily variation; and some fatigue doesn't
  affect CMJ until quite severe
- **GPS only** — load metrics don't capture neuromuscular state

When all three converge (e.g. low sleep + CMJ drop + accel count drop), the system fires a
CRITICAL alert. When only one fires, it's a monitor situation.

---

## GPS / Kinexon Concepts

### Player Load
Tri-axial accelerometer composite (AU = arbitrary units). Sum of accelerations in X, Y, Z
directions weighted by direction. Higher = more mechanical work done. Drops below personal
baseline on a high-distance day = effort-effort dissociation = fatigue signal.

### Accel Count and Decel Count
Number of acceleration/deceleration events above a speed threshold per session. In
basketball, these map to cuts, sprints, closeouts, and defensive slides — the explosive
movements that determine performance and carry injury risk.

**Key research insight (Jaspers et al. 2018):** Athletes approaching soft-tissue injury
show protective movement strategies — they unconsciously reduce explosive direction changes
even when total distance stays normal. Accel/decel drop at normal distance is the early
warning signal. This is what the dashboard is built to detect.

### Why Decels Matter More Than Accels (clinically)
Deceleration produces higher eccentric forces than acceleration. Hamstring strains,
patellar tendinopathy, and ankle sprains are all more likely during deceleration than
during pure acceleration. A drop in decel count means the athlete is avoiding the
highest-load movement pattern.

---

## Signal Correlations — In Depth

### Why build this instead of just using published thresholds?

Published thresholds are derived from general populations — often soccer, rugby, or mixed
sport samples. WNBA athletes are different. Your specific team is different again. The
Correlation Explorer surfaces what's actually true in your data.

### Pearson Correlation (r)

Measures linear relationship between two variables. Range: −1 to +1.

- r = −0.42 (sleep vs soreness): as sleep goes up, soreness tends to go down. Moderate.
- r = +0.71 (player load vs distance): expected, very strong
- r = −0.28 (accel count vs injury within 7 days): small but meaningful

### Lag Analysis — The Key Innovation

Most monitoring dashboards compare today's metrics to today's outcomes. But biology
has delay:
- Sleep deprivation affects recovery over 24–48 hours
- Overtraining shows in CMJ 48–72 hours after the session
- Psychological stress accumulates over days

The lag analysis lets you ask: "Does sleep 2 nights ago predict today's CMJ drop better
than last night's sleep?"

```python
tmp["pred_lagged"] = tmp.groupby("player_id")[pred_col].shift(lag)
r, p = pearsonr(tmp["pred_lagged"], tmp[outcome_col])
```

Interview line: *"Our lag analysis shows the strongest predictive signal for CMJ drops is
sleep from 2 nights prior, not last night — consistent with the delayed recovery timeline
in the literature."*

### Conditional Risk Table

Answers: "When this flag fires, what percentage of those athlete-days had an injury within
7 days?"

```
ACWR > 1.5     →  8.3% injury rate  (baseline: 3.1%)  →  2.7× relative risk
CMJ z < −1.5   →  7.1% injury rate  (baseline: 3.1%)  →  2.3× relative risk
Accel z < −1.5 →  6.8% injury rate  (baseline: 3.1%)  →  2.2× relative risk
```

This converts statistical signals into decision-relevant probabilities. A GM can understand
"2.7× the injury risk" even if they don't understand z-scores.

---

## Machine Learning

### Why Random Forest?

- Works with small datasets (90 days × 12 players = ~1,080 samples)
- Interpretable via feature importance (you can explain what it learned)
- Industry standard in peer-reviewed sports injury prediction literature
- Handles missing data gracefully with imputation
- Deep learning requires 10–100× more data to generalise

### Feature Engineering Philosophy

Raw values alone miss the signal. The model uses:
1. **Raw values** — today's sleep hours, soreness, GPS load
2. **7-day rolling averages** — the trend direction
3. **Personal z-scores** — deviation from individual baseline (the key signal)
4. **Hard-floor flags** — binary: sleep below 6.5, ACWR above 1.5, GPS drop below 1σ
5. **Composite** — wellness score combining all subjective metrics

GPS z-score drop flags (`flag_accel_drop`, `flag_decel_drop`, `flag_load_drop`) are binary
features that fire when the z-score crosses −1.0. These give the model a simple,
interpretable signal to weight.

### Model Validation (V1)

WAIMS V1 does not claim to be a validated injury classifier — it is a heuristic risk score.
The meaningful V1 validation question is: **does the readiness ranking match what the coach
already knows?**

- Method: Spearman rank correlation between WAIMS daily ranking and coach informal assessment
- Target: coach agrees with top/bottom 3 flagged athletes on ≥70% of days
- No formal injury event validation required at V1 (insufficient events in demo data)

V2 upgrades when real season data is available: walk-forward time splits, player-holdout
GroupKFold, PR-AUC + calibration, Precision@K top 3 per day, lead-time analysis.

---

## Evidence Review System

WAIMS includes automated weekly research monitoring via GitHub Actions.

**Philosophy:** The Evidence Review tab is a forward-looking inbox — not a historical
literature review. Foundational papers (Walsh 2021, Gabbett 2016, Gathercole 2015) are
already integrated into thresholds in RESEARCH_FOUNDATION.md. The monitor surfaces only
NEW research for weekly triage.

**Evidence gate policy (Orlando Magic framework):**
No WAIMS threshold change without a supporting meta-analysis or systematic review.
Single new studies go to Watchlist only.

**Decision ladder:**
- CANDIDATE (meta-analysis/SR) → schedule formal staff review
- REVIEW (basketball-specific) → read abstract, Watchlist only
- WATCHLIST → monitor for replication
- BACKGROUND → awareness only

**Clinical noise filtering:** Tightened PubMed queries and a post-fetch relevance filter
automatically discard papers about surgery, pharmacology, oncology, animal studies, and
unrelated clinical topics. Only sport science relevant papers surface for triage.

---

## Research Tool Recommendations

For finding sports science literature to support your work:

| Tool | Best Use | Cost |
|------|----------|------|
| **Semantic Scholar** | Free paper discovery, AI-generated TLDRs, citation graphs | Free |
| **Elicit** | Structured literature review with summary tables | Free tier |
| **Consensus** | "Is there scientific consensus on X?" | Limited free |
| **PubMed** | Ground-truth medical literature verification | Free |
| **Google Scholar** | Citation tracking, finding newer papers that cite a classic | Free |
| **Sportsmith** | Applied practice translation layer (Jo Clubb, Tim Gabbett) | $13/month |

**Recommended workflow for WAIMS:**
1. Search Semantic Scholar for "GPS monitoring basketball injury" or "CMJ fatigue prediction"
2. Export PDFs of the 3–5 most relevant papers
3. Paste PDFs into Claude with "How does this support my correlation findings in WAIMS?"
4. Use the citations in your Correlation Explorer annotations

---

## Interview Talking Points

### "Walk me through the system"
Start at Tab 1 (Command Center). "A coach opens this at 7am and knows in 10 seconds who
can go hard today. This card is red — here's why. Now let me show you the science behind
that flag..." → Tab 8 (Insights → Correlations).

### "Why GPS accel/decel and not just distance?"
"Total distance is a quantity metric. Accel and decel count are quality metrics — they
capture the explosive, high-force movements that actually drive injury risk. An athlete
who runs 6km but with half her normal acceleration events is showing a protective movement
pattern. That's often the pre-clinical signal before a soft-tissue injury."

### "How is this different from what teams already use?"
"Catapult and Kinexon provide the raw GPS numbers. Teamworks handles the wellness surveys.
What those tools don't do is correlate them against each other, weight them by personal
baseline, and surface a single risk score with an explainable narrative. The correlation
analysis and evidence review system are what I built — those aren't in off-the-shelf tools."

### "How do you know the model is working?"
"For V1 with synthetic data, the meaningful validation is: does the readiness ranking match
what a coach would already know? We measure that with Spearman rank correlation — does the
system flag the same 2-3 athletes the coach was already watching? With real team data, we'd
move to walk-forward time splits, PR-AUC, and Precision@K — how often does the top-3 daily
watchlist contain the players who actually get injured? That's documented in the Model
Validation Philosophy section of the Insights tab."

### "What would you add with real data?"
"Heart rate variability (HRV) is the strongest single-day readiness signal missing here.
I'd also add periodization logic — a load taper curve that adjusts recommendations based
on proximity to playoffs. The travel direction feature (eastward vs westward circadian
penalty) is already designed for V2. And I'd want to run the lag analysis on a full season
of real data — 90 days of synthetic data gives you the methodology, but the findings would
sharpen considerably with 2–3 seasons."

### "What's the evidence gate?"
"No threshold changes without a meta-analysis or systematic review. Single studies go to
Watchlist. The system is modelled on the Orlando Magic framework — evidence-based but
operationally conservative. I built an automated PubMed monitor that runs weekly via GitHub
Actions and surfaces new papers for triage in the dashboard. Decisions are logged with a
decision date and rationale."
