# WAIMS — Learning Guide

For interviews, presentations, and self-study. Explains the *why* behind every design decision.

---

## What Is WAIMS?

WAIMS (Watchlist Athlete Injury Monitoring System) is a professional-grade athlete monitoring dashboard built for a WNBA team context. It combines:

- **Subjective data** — daily wellness questionnaires (sleep, soreness, stress, mood)
- **Objective neuromuscular data** — force plate testing (CMJ, RSI-Modified)
- **Objective external load data** — GPS/Kinexon (player load, accel/decel counts, distance)
- **Machine learning** — Random Forest injury risk predictor trained on all signals simultaneously
- **Statistical correlation analysis** — surfaces hidden relationships between metrics

The system is designed around two personas: a **coach** who needs situational awareness in 30 seconds, and a **sport scientist** who needs deep analytical tools.

---

## The Two-Persona Architecture

### Why not just build one dashboard?

Pro tools (Catapult, Kinexon, Teamworks) all structure their interfaces around roles:
- Coaches see traffic lights. They make real-time decisions. They don't have time for σ notation.
- Sport scientists need z-scores, lags, conditional probabilities, and model audit trails.

**Tab 1 — Command Center** serves the coach. Everything else serves the analyst. This is the correct architecture for a real deployment.

---

## 10 Tabs Explained

### 🏀 Tab 1 — Command Center
The most important tab. Answers in one glance:
- Who can go hard today? (green)
- Who do I protect? (red)
- What is the team GPS load situation?
- What are my top 3 action items?

The alert engine surfaces only the highest-severity finding per player. A coach sees "No explosive loading for Bueckers today" — not a wall of z-scores.

### 📊 Tab 2 — Today's Readiness
The analyst version of Tab 1. Every player, every signal, every z-score visible. Compact and detailed views. GPS panel shows the Kinexon numbers with σ delta so you can explain the number in a sentence.

### 👤 Tab 3 — Athlete Profiles
The full story per athlete. Radar chart covers six dimensions: Sleep / Physical / Mental / Load / Neuro / GPS. The GPS section has a 14-day trend chart with Player Load on the left axis and Accel/Decel Count on the right — divergence between these two axes is a key fatigue signal.

### 📈 Tab 4 — Trends
7-day rolling average overlaid on raw daily values. Used to identify gradual drift vs acute spikes. A coach saying "she's been off all week" is visible here before it becomes a flag.

### 💪 Tab 5 — Jump Testing
CMJ and RSI-Modified. Tested weekly (Mondays in the synthetic data). Z-scored vs personal 30-day baseline. Research shows CMJ drops of ≥ 2σ predict impaired performance and elevated injury risk (Gathercole 2015). Asymmetry > 10% flags lateral imbalance.

### 🚨 Tab 6 — Availability & Injuries
The medical/GM view. Status board (AVAILABLE / QUESTIONABLE / OUT), season availability %, and full injury log. Real deployments would integrate with team EMR.

### 📡 Tab 7 — GPS & Load
Kinexon full session breakdown. Player Load ACWR (acute:chronic for GPS load — same concept as training load ACWR). Accel/decel drops vs team median and personal baseline. Key insight: on a hard training day, everyone's distance goes up; when only one player's accels/decels drop, that's the signal.

### 🤖 Tab 8 — Forecast
The GM view. 7-day risk watchlist. "Why she's here" narrative pulls every contributing flag. GPS flags appear at the bottom of each risk card and add weight to the composite risk score (at lower weight than CMJ/RSI, because objective mechanical signals are prioritised over load metrics).

### 🔍 Tab 9 — Ask the Watchlist
Natural language shortcuts. No SQL. No dashboard literacy required. Type "accel drop" — get the list of athletes whose accel count is ≥ 1σ below their personal 30-day norm, with 🔴/🟡/🟢 status. Staff who aren't sport scientists can use this independently.

### 🔬 Tab 10 — Correlation Explorer
The research tool. What makes WAIMS more than a monitoring dashboard — it's an analytical discovery environment. Five sub-sections covered in detail below.

---

## The Z-Score Engine

### Why personal baselines, not population averages?

A soreness score of 6/10 means very different things for different athletes. For an athlete whose baseline is 2, it's a significant deviation. For an athlete whose baseline is 5, it's normal. Population-average thresholds (the common approach) miss this entirely.

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

For GPS metrics (load, accels, decels), **negative** z-scores are the concerning direction — they indicate the athlete is doing less than normal, which is the fatigue/protective movement signal.

---

## Three-Source Flag System

```
Wellness (subjective)    →  sleep z, soreness z, stress z, mood z
Force Plate (objective)  →  CMJ z, RSI-Mod z, asymmetry
GPS / Kinexon (objective) →  player load z, accel z, decel z
```

Why three sources? Because each has different failure modes:

- **Wellness only** — athletes misreport or suppress scores; confirmed by Saw et al. (2016) that subjective methods work but need calibration
- **Force plate only** — tested weekly, misses daily variation; and some fatigue doesn't affect CMJ until quite severe
- **GPS only** — load metrics don't capture neuromuscular state

When all three converge (e.g. low sleep + CMJ drop + accel count drop), the system fires a CRITICAL alert. When only one fires, it's a monitor situation.

---

## GPS / Kinexon Concepts

### Player Load
Tri-axial accelerometer composite (AU = arbitrary units). Sum of accelerations in X, Y, Z directions weighted by direction. Higher = more mechanical work done. Drops below personal baseline on a high-distance day = effort-effort dissociation = fatigue signal.

### Accel Count and Decel Count
Number of acceleration/deceleration events above a speed threshold per session. In basketball, these map to cuts, sprints, closeouts, and defensive slides — the explosive movements that determine performance and carry injury risk.

**Key research insight (Jaspers et al. 2018):** Athletes approaching soft-tissue injury show protective movement strategies — they unconsciously reduce explosive direction changes even when total distance stays normal. Accel/decel drop at normal distance is the early warning signal. This is what the dashboard is built to detect.

### Why Decels Matter More Than Accels (clinically)
Deceleration produces higher eccentric forces than acceleration. Hamstring strains, patellar tendinopathy, and ankle sprains are all more likely during deceleration than during pure acceleration. A drop in decel count means the athlete is avoiding the highest-load movement pattern.

---

## Correlation Explorer — In Depth

### Why build this instead of just using published thresholds?

Published thresholds are derived from general populations — often soccer, rugby, or mixed sport samples. WNBA athletes are different. Your specific team is different again. The Correlation Explorer surfaces what's actually true in your data.

### Pearson Correlation (r)

Measures linear relationship between two variables. Range: −1 to +1.

- r = −0.42 (sleep vs soreness): as sleep goes up, soreness tends to go down. Moderate relationship.
- r = +0.71 (player load vs distance): expected, very strong
- r = −0.28 (accel count vs injury within 7 days): small but meaningful — accel drops precede injury

### Lag Analysis — The Key Innovation

Most monitoring dashboards compare today's metrics to today's outcomes. But biology has delay:
- Sleep deprivation affects recovery over 24–48 hours
- Overtraining shows in CMJ 48–72 hours after the session
- Psychological stress accumulates over days

The lag analysis lets you ask: "Does sleep 2 nights ago predict today's CMJ drop better than last night's sleep?"

```python
tmp["pred_lagged"] = tmp.groupby("player_id")[pred_col].shift(lag)
r, p = pearsonr(tmp["pred_lagged"], tmp[outcome_col])
```

This is a finding you can say in an interview: *"Our lag analysis shows the strongest predictive signal for CMJ drops is sleep from 2 nights prior, not last night — consistent with the delayed recovery timeline in the literature."*

### Conditional Risk Table

Answers: "When this flag fires, what percentage of those athlete-days had an injury within 7 days?"

```
ACWR > 1.5    →  8.3% injury rate  (baseline: 3.1%)  →  2.7× relative risk
CMJ z < −1.5  →  7.1% injury rate  (baseline: 3.1%)  →  2.3× relative risk
Accel z < −1.5 → 6.8% injury rate  (baseline: 3.1%)  →  2.2× relative risk
```

This converts statistical signals into decision-relevant probabilities. A GM can understand "2.7× the injury risk" even if they don't understand z-scores.

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

GPS z-score drop flags (`flag_accel_drop`, `flag_decel_drop`, `flag_load_drop`) are binary features that fire when the z-score crosses −1.0. These give the model a simple, interpretable signal to weight.

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

**Recommended workflow for WAIMS:**
1. Search Semantic Scholar for "GPS monitoring basketball injury" or "CMJ fatigue prediction"
2. Export PDFs of the 3–5 most relevant papers
3. Paste PDFs into Claude with "How does this support my correlation findings in WAIMS?"
4. Use the citations in your Correlation Explorer annotations

---

## Interview Talking Points

### "Walk me through the system"
Start at Tab 1 (Command Center). "A coach opens this at 7am and knows in 10 seconds who can go hard today. This card is red — here's why. Now let me show you the science behind that flag..." → Tab 10 (Correlations).

### "Why GPS accel/decel and not just distance?"
"Total distance is a quantity metric. Accel and decel count are quality metrics — they capture the explosive, high-force movements that actually drive injury risk. An athlete who runs 6km but with half her normal acceleration events is showing a protective movement pattern. That's often the pre-clinical signal before a soft-tissue injury."

### "How is this different from what teams already use?"
"Catapult and Kinexon provide the raw GPS numbers. Teamworks handles the wellness surveys. What those tools don't do is correlate them against each other, weight them by personal baseline, and surface a single risk score with an explainable narrative. The Correlation Explorer is what I built — that's not in off-the-shelf tools."

### "What would you add with real data?"
"Heart rate variability (HRV) is the strongest single-day readiness signal missing here. I'd also add periodization logic — a load taper curve that adjusts recommendations based on proximity to the NCAA Tournament or playoffs. And I'd want to run the lag analysis on a full season of real data — 90 days of synthetic data gives you the methodology, but the findings would sharpen considerably with 2–3 seasons."

---

## Systems Thinking in WAIMS

### Why Single-Metric Monitoring Fails

Most athlete monitoring tools treat each signal in isolation — sleep is sleep, soreness is soreness, GPS load is GPS load. This is a linear model of a nonlinear system. The human body under training stress is a complex adaptive system: signals interact, feedback loops operate across different timescales, and the same input (a hard training session) produces different outputs depending on the current state of the whole system.

A player with 7 hours of sleep, soreness of 6/10, and a CMJ drop of 1.5σ is not three separate yellow flags. She is a system showing early-stage convergent fatigue — three independent sensors detecting the same underlying state from different angles. That convergence is the signal. WAIMS is designed to detect it.

### The Three-Layer Signal Architecture

WAIMS deliberately uses three independent measurement sources with different failure modes:

**Subjective wellness** (sleep, soreness, stress, mood) — sensitive to psychological state and perceived recovery, but athletes suppress or misreport under competitive pressure. High signal-to-noise ratio when honest, high noise when suppressed.

**Objective neuromuscular** (CMJ, RSI-Modified) — cannot be suppressed. Mechanical output reflects actual neuromuscular state. But tested weekly in most protocols, so misses daily variation. Gathercole (2015) validated CMJ as the most sensitive fatigue marker, but only when compared to personal baseline — not population norms.

**Objective external load** (GPS/Kinexon) — captures what the body was asked to do, not how it responded. Protective movement patterns (reduced accel/decel counts at normal distance) appear before subjective soreness peaks, making this a leading indicator. The key insight from Jaspers et al. (2018): athletes unconsciously reduce explosive direction changes before a soft-tissue injury becomes clinically apparent.

When all three converge — low wellness, reduced CMJ, and protective GPS pattern — the system is in a high-risk state regardless of what the athlete reports verbally. When only one fires, it is a monitoring situation. This convergence architecture reduces both false positives (unnecessary load reductions) and false negatives (missed injury precursors).

### Feedback Loops Across Timescales

WAIMS operates across multiple feedback loops simultaneously:

**Daily loop** — overnight wellness → morning brief → practice modification → next-day wellness. The Hidden Fatigue Flag closes this loop by detecting when accumulated load is degrading daily readiness before the score drops into PROTECT territory.

**Weekly loop** — 4-day and 8-day cumulative minutes → load warning → session volume decision → weekly load trajectory. The load projection tool models this explicitly: select a game scenario tonight, see where readiness lands tomorrow.

**Season loop** — evidence review (GitHub Actions weekly) → threshold updates → model retraining → improved flag accuracy. This is the meta-feedback loop — the system learns and updates its own decision rules as new research emerges and as real outcome data accumulates.

**Individual adaptation loop** — the 30-day expanding personal baseline means the system continuously recalibrates to each athlete's changing state across a season. A player recovering from a mild injury will have a suppressed baseline; the z-score engine adapts rather than flagging her as perpetually flagged.

### Emergent Patterns vs Threshold Crossing

Traditional monitoring flags a player when a metric crosses a fixed threshold. WAIMS flags a player when a pattern emerges across multiple signals. This is the difference between a thermometer and a diagnostic system.

The Conditional Risk Table in the Insights tab makes this explicit: ACWR alone carries a 2.7× relative injury risk when above 1.5. CMJ drop alone carries 2.3×. But the combination of ACWR spike + CMJ drop + accel count reduction is not additive — it is multiplicative. That is emergent risk, not summed risk. The Random Forest model captures this interaction structure; a linear model would not.

### Why This Matters for High Performance Environments

Elite sport is a complex system under external pressure (schedule, travel, media, competition). Athlete readiness is not a static number — it is a dynamic state that emerges from the interaction of physical load, psychological stress, sleep quality, and environmental context. A monitoring system that treats these as independent variables will consistently miss the players who are at the edge of their adaptive capacity — the players where early intervention has the highest leverage.

WAIMS is designed around this principle: surface the convergent signals, translate them into coach-ready language, and close the feedback loop between monitoring data and training decisions. The goal is not to replace coach judgment — it is to give coaches a system that extends their perceptual range into dimensions they cannot observe directly.

---

### Interview Framing — Systems Language

If the role involves a systems-oriented leader (performance director, head of sport science, medical director):

*"Most monitoring tools are single-metric dashboards. WAIMS is a convergence detection system — it's looking for the state of the whole athlete, not the value of any single variable. The three-source architecture, the personal baseline engine, and the multi-timescale feedback loops are all design choices driven by how complex biological systems actually work under load."*

*"The evidence review system adds a fourth loop — the system's own decision rules update as new research emerges. That's not just a monitoring tool; it's a learning system."*
