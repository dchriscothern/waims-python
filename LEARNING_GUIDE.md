# WAIMS — Learning Guide

For interviews, presentations, and self-study. Explains the *why* behind every design decision.

---

## What Is WAIMS?

WAIMS (Wellness & Athlete Injury Management System) is a professional-grade athlete monitoring dashboard built for a WNBA team context. It combines:

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

## Tabs Explained

Tabs are role-gated (`TAB_ACCESS` in `auth.py`) — which of these a signed-in user sees depends on their role. A coach never sees Jump Testing or Insights; a GM sees Command Center (summary only) and Availability; Sport Scientist and Medical see everything. There's also a separate **Athlete View** (not a tab — a whole simplified page shown instead of the tab bar when logged in as the `athlete` role): one readiness answer, sleep/soreness/stress on one line, and a recovery checklist.

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

### 📈 Tab 4 — Trends & Load
7-day rolling average overlaid on raw daily values for wellness, force plate, **and** GPS/Kinexon load — one merged tab rather than separate Trends and GPS tabs. Used to identify gradual drift vs acute spikes. A coach saying "she's been off all week" is visible here before it becomes a flag. Player Load ACWR and accel/decel drops vs team median live here too: on a hard training day everyone's distance goes up, so when only one player's accels/decels drop, that's the signal.

### 💪 Tab 5 — Jump Testing
CMJ and RSI-Modified. Tested weekly (Mondays in the synthetic data). Z-scored vs personal 30-day baseline. Research shows CMJ drops of ≥ 2σ predict impaired performance and elevated injury risk (Gathercole 2015). Asymmetry > 10% flags lateral imbalance.

### 🚨 Tab 6 — Availability & Injuries
The medical/GM view. Status board (AVAILABLE / QUESTIONABLE / OUT), season availability %, and full injury log. Real deployments would integrate with team EMR.

### 🤖 Tab 7 — Forecast
The GM/staff view. 7-day risk watchlist plus the load-projection tool ("what happens to readiness if she plays tonight vs sits"). "Why she's here" narrative pulls every contributing flag. GPS flags appear at the bottom of each risk card and add weight to the composite risk score (at lower weight than CMJ/RSI, because objective mechanical signals are prioritised over load metrics).

### 🔍 Tab 8 — Insights
Merges what used to be two separate tabs (Ask the Watchlist + Correlation Explorer) plus model validation philosophy and the data-quality audit log:
- **Ask** — natural-language shortcuts, now with an in-browser **Voice Query** mic button (Chrome/Edge, Web Speech API — no extra packages). Type or speak "who didn't sleep well" and get an instant answer, no tab switching.
- **Correlations** — the research tool covered in depth below (lag analysis, conditional risk table, real WNBA/Arkansas rate stats).

### 📥 Tab 9 — Data Intake
New since the original build. The operator-facing surface for getting real files into WAIMS: upload a CSV/Excel into a drop-zone lane (wellness, GPS, force plate, etc.), see a live validation preview (rows detected, required columns, warnings) before anything is written, plus connector status cards and ingest audit history. Built for the transition from synthetic demo data to a real team's actual file exports.

### 🎯 Tab 10 — Game Performance
**Arkansas/mens deployment only** — hidden entirely on the WNBA app since it reads Arkansas-only tables (`player_game_stats`, `play_by_play_events`) that don't exist in the WNBA database. Real box scores, player game log, shot detail, and advanced possession/lineup metrics parsed from actual game data.

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

## Automated Evidence Review System

### Why build this instead of just re-reading the literature occasionally?

Thresholds decay. A sleep cutoff or a CMJ flag that was well-supported
in 2021 needs to stay well-supported — sports science keeps publishing,
and a monitoring tool that never checks back against new research is
just running on someone's old opinion. Most teams handle this
informally, if at all. WAIMS handles it as a standing system: a
scheduled GitHub Action, not a person remembering to check PubMed.

### How it works

`research_monitor.py` runs automatically every Monday morning (`cron`
in `.github/workflows/research_monitor.yml`, also triggerable on demand
via `workflow_dispatch`). Each run:

1. **Queries PubMed** across 10 topics mapped directly to WAIMS signals
   — Sleep & Athlete Injury Risk, CMJ/RSI as a Fatigue Marker, Basketball
   Load Monitoring, Female Athlete Monitoring & Recovery, Deceleration
   Monitoring, GPS Load Monitoring, ACWR Methodology, Menstrual Cycle &
   Athletic Performance, Basketball Injury Epidemiology, and Travel &
   Circadian Load. Each query is narrowly scoped (title/abstract term
   matching plus exclusion terms) specifically to keep out unrelated
   clinical noise — a sleep query, for instance, excludes insomnia drug
   trials.
2. **Pulls practitioner RSS feeds** from high-trust sports-science
   voices (Martin Buchheit, SPSR, the BJSM blog, Sportsmith, and
   others) — the applied-practice side, not just peer-reviewed papers.
3. **De-duplicates and scores** everything against a decision ladder
   modeled on how a real performance department would triage new
   evidence, not just dump it in a spreadsheet:

```
WATCHLIST   -> interesting, single study, monitor for replication
CANDIDATE   -> appears in a meta-analysis/systematic review; schedule formal staff review
APPROVED    -> reviewed by performance staff, approved for a WAIMS update
INTEGRATED  -> the change actually landed in code, RESEARCH_FOUNDATION.md, README, roadmap
REJECTED    -> reviewed, not applicable (wrong population, sport, etc.)
```

4. **Opens a pull request** with the updated `research_log.json` and an
   HTML decision report — it doesn't push directly or auto-apply
   anything. A human still reviews and merges.

The **formal policy** behind the ladder (Orlando Magic-style, per the
module's own docstring): *no threshold or weighting change ships
without a supporting meta-analysis or systematic review.* A single new
study goes to WATCHLIST, not production. This is the same evidence
discipline real performance departments use to avoid chasing every new
paper — WAIMS just automates the watching part.

New findings surface in the **Insights tab's Evidence Review inbox**,
where they wait to be triaged — foundational papers already backing
WAIMS's current thresholds (Walsh 2021, Gabbett 2016, Gathercole 2015,
etc.) live in `RESEARCH_FOUNDATION.md` and aren't re-surfaced here; this
system is a forward-looking inbox for *new* research only.

**Status:** confirmed running end-to-end as of 2026-09-23 — the weekly
run genuinely finds new papers, commits the update, and opens its own
PR with no manual step. This closes the "season loop" mentioned earlier
in this guide: evidence review → threshold updates → model retraining
→ improved flag accuracy, on a real, running schedule rather than as an
aspiration.

**Interview framing:** *"Most monitoring tools ship thresholds once and
never revisit them. WAIMS has a standing weekly check against new sports
science literature, with a formal decision ladder so a single new study
can't silently change production behavior — that's the same discipline
NBA performance departments use, just automated instead of ad hoc."*

---

## Research Tool Recommendations

The automated system above only watches for new research against
WAIMS's *existing* signals — it doesn't do open-ended literature review.
For digging into a new question, an interview talking point, or backing
a fresh Correlation Explorer finding, use the tools below instead.

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
Start at Tab 1 (Command Center). "A coach opens this at 7am and knows in 10 seconds who can go hard today. This card is red — here's why. Now let me show you the science behind that flag..." → Tab 8, Insights → Correlations section.

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
