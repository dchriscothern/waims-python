# WAIMS — Python Technical Reference

Complete tab-by-tab and module reference for the WAIMS dashboard.

---

## Architecture Overview

```
generate_database.py  →  waims_demo.db  →  train_models.py  →  models/
                                    ↓
                             dashboard.py
                          ┌──────────────────────────────────┐
                          │  Tab 1: coach_command_center.py  │
                          │  Tab 3: athlete_profile_tab.py   │
                          │  Tab 10: correlation_explorer.py │
                          └──────────────────────────────────┘
```

---

## Tab Reference

### Tab 1 — 🏀 Command Center (`coach_command_center.py`)
**Audience:** Head coach, assistant coaches  
**Goal:** Full roster situational awareness in under 30 seconds

**Components:**
- Dark header with live 🟢/🟡/🔴 count (Ready / Monitor / Protect)
- **Priority Alerts panel** — auto-surfaces top 3 athletes needing action. Each alert includes a one-line coaching directive ("Cap practice at 60%", "No explosive loading today")
- **GPS / Kinexon Strip** — team avg load AU, team avg accel count, names of high-load and low-accel athletes
- **4-column Roster Grid** — every player card shows: readiness %, sleep, soreness, and three signal icons (🦵 CMJ · 📡 GPS Load · ⚡ Accels). Sorted red-first
- **7-day Team Sparklines** — sleep, soreness, mood, stress with delta arrow vs yesterday
- **Deep Dive nav tiles** — links to each analyst tab

**Key function:** `coach_command_center(wellness, players, force_plate, training_load, acwr, end_date)`

---

### Tab 2 — 📊 Today's Readiness (`dashboard.py → enhanced_todays_readiness_tab`)
**Audience:** Sport scientist, athletic trainer

**Components:**
- Compact view: full roster table with Load/Accels/Decels columns, z-score emoji badges (🟢🟡🔴)
- Detailed view: per-player expanded card — wellness panel, force plate panel (CMJ + RSI with σ delta), GPS/Kinexon panel (Player Load, Accel Count, Decel Count with σ delta display)
- GPS flags appended to flag notes with 📡 prefix

**Z-score flagging logic:**
```python
hist = training_load_df[player_id & date < ref & col > 0].tail(30)[col]
z = (today_val - hist.mean()) / max(hist.std(), 0.1)
# 🔴 if z ≤ −2.0  |  🟡 if z ≤ −1.0  |  🟢 otherwise
```

---

### Tab 3 — 👤 Athlete Profiles (`athlete_profile_tab.py`)
**Audience:** Sport scientist, medical staff

**Components:**
- Photo + position/age header
- Readiness speedometer gauge (0–100)
- 6-axis radar chart: Sleep / Physical / Mental / Load / Neuro / GPS
- 8 metric cards: Sleep · Soreness · Mood · ACWR · CMJ · RSI-Mod · Player Load · Accel Count
- Pill meters for soreness, stress, mood with colour-banded bar
- **GPS / Kinexon section:** 6 metric tiles (load, accels, decels, distance, HSR, sprint) + 14-day dual-axis trend chart (Player Load on left axis, Accel/Decel on right) + GPS flag notes with 📡 prefix
- Personal baseline z-score comparison panel (requires `z_score_module.py`)
- 7-day wellness + force plate overlay trend chart
- Basketball-specific risk context (requires `research_context.py`)

---

### Tab 4 — 📈 Trends (`dashboard.py`)
**Audience:** Sport scientist

Multi-athlete selector. Raw daily values (faint) overlaid with 7-day rolling average (bold). Metrics: sleep, soreness, mood, stress. Useful for spotting gradual drift across a training block.

---

### Tab 5 — 💪 Jump Testing (`dashboard.py`)
**Audience:** Athletic trainer, sport scientist

CMJ height and RSI-Modified vs personal 30-day baseline. Weekly test frequency. 7-day team trend chart. Asymmetry % flagged when > 10%.

---

### Tab 6 — 🚨 Availability & Injuries (`dashboard.py → availability_injuries_tab`)
**Audience:** GM, medical staff, coach

- Daily availability board (AVAILABLE / QUESTIONABLE / OUT)
- Season availability % per player
- Injury log with type, severity, days missed

---

### Tab 7 — 📡 GPS & Load (`dashboard.py → gps_load_tab`)
**Audience:** Sport scientist, S&C coach

Full Kinexon session breakdown. Player load ACWR. 14-day trend per player. Accel/decel drop detection vs team median and personal baseline. HSR and sprint distance tracking.

---

### Tab 8 — 🤖 Forecast (`dashboard.py`)
**Audience:** GM, medical director

7-day injury risk watchlist. Each player risk card shows: risk score bar, wellness flags, GPS row (Load/Accels/Decels with σ delta badges), "Why she's here" flag narrative. GPS flags add +1 to risk score (lower weight than CMJ/RSI which add +2/+3).

---

### Tab 9 — 🔍 Ask the Watchlist (`dashboard.py` inline / `smart_query.py` standalone)
**Audience:** Any user

Pattern-matched NL queries. No API key required.

**Supported GPS queries** (only appear if GPS columns detected):
- `gps today` — full team GPS with personal z-score flags
- `high load` — players above team median
- `low load` — players ≥ 1σ below personal baseline
- `accel drop` — protective movement pattern flag
- `decel drop` — direction-change braking reduction flag

---

### Tab 10 — 🔬 Correlations (`correlation_explorer.py`)
**Audience:** Sport scientist, researcher, interview demo

**Six sub-sections (radio selector):**

**Heatmap** — Pearson r matrix across all metrics. Injury column shows what actually predicts injury within 7 days in this dataset.

**Top Correlations** — Ranked by |r| with research citations auto-matched. Includes p-value significance tag. Example output:
```
#1  Sleep (hrs) vs Soreness  r = −0.42  Moderate · ↓ negative
    📚 Fullagar et al. 2015 — Sleep deprivation delays muscle recovery
```

**Lag Analysis** — Interactive: choose any predictor + outcome, visualise r across lags 0–7 days. Surfaces temporal structure not visible in same-day correlations. Key finding: sleep N-2 days often predicts CMJ drop more strongly than last night's sleep.

**Conditional Risk** — For each flag definition (Sleep < 6.5, ACWR > 1.5, CMJ z < −1.5, Accel z < −1.5, etc.) computes: n days flagged, % with injury within 7 days, relative risk vs baseline. Displayed as bar chart + downloadable table.

**Per-Player Fingerprints** — Individual sleep→next-day soreness Pearson r per athlete. Negative = healthy pattern. Scatter: CMJ vs Soreness by position.

**Model Audit** — RF feature importances for top 15 features. Wellness vs GPS vs force plate % split shown as three summary metrics.

---

## Module Reference

### `generate_database.py`
Generates `waims_demo.db` with 90 days of synthetic data.

GPS generation logic:
```python
GPS_BASELINES = {
    "G": (320, 42, 38, 6.8, 620, 180),  # load, accels, decels, km, hsr, sprint
    "F": (295, 36, 33, 6.2, 510, 140),
    "C": (265, 28, 26, 5.4, 380, 90),
}
# Correlated with game vs practice day (1.3× multiplier on game days)
# Fatigue drift: -8% across 90 days
# Pre-injury warning: -18% accels/decels in 5–7 days before each injury event
```

### `train_models.py`
Trains RandomForest injury risk predictor and readiness scorer.

Feature list (40+ features):
- Raw wellness, 7-day rolling averages, personal z-scores
- Force plate: CMJ, RSI z-scores
- GPS: player_load, accel_count, decel_count, rolling averages, z-scores, drop flags
- Hard-floor binary flags: `flag_sleep_floor`, `flag_acwr_spike`, `flag_load_drop`, `flag_accel_drop`, `flag_decel_drop`

GPS detection:
```python
gps_present = all(c in df.columns and df[c].notna().sum() > 0 for c in gps_cols)
# GPS features added automatically if present; skipped cleanly if not
```

Readiness score GPS modifier:
```python
for z_col in ["player_load_zscore", "accel_count_zscore", "decel_count_zscore"]:
    z = row.get(z_col, 0)
    if z <= -2.0: modifier -= 2   # severe GPS drop
    elif z <= -1.0: modifier -= 1  # moderate GPS drop
```

### `coach_command_center.py`
Exported function: `coach_command_center(wellness, players, force_plate, training_load, acwr, end_date)`

Alert logic priority: CRITICAL (score < 60) → NEURO (CMJ 🔴) → WORKLOAD (ACWR > 1.5) → GPS (accel 🔴) → MONITOR (soreness ≥ 7). Deduplicates by player name keeping highest severity.

### `correlation_explorer.py`
Exported function: `correlation_explorer_tab(wellness, training_load, force_plate, acwr, injuries, players)`

Builds a master merged daily frame with forward-filled force plate data and expanding-window personal z-scores (shifted by 1 day — no data leakage). scipy.stats.pearsonr used for all correlations + p-values.

### `athlete_profile_tab.py`
Exported function: `athlete_profile_tab(wellness, training_load, acwr, force_plate, players, injuries)`

GPS z-score via `_gps_zscore(player_id, col, today_val, training_load_df, ref_date)`. Radar chart includes GPS axis normalised to position baseline. Graceful fallback: GPS sections hidden if `player_load` column not in dataframe.

### `smart_query.py`
Standalone Streamlit app (`streamlit run smart_query.py`). Also embedded inline in Tab 9.

GPS query detection:
```python
if HAS_GPS:  # detected via PRAGMA table_info
    if "accel drop" in query: return "gps_accel_drop", {}
    if "low load" in query:   return "gps_low_load", {}
```

---

## Database Schema

```sql
CREATE TABLE training_load (
    load_id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id TEXT, date DATE,
    practice_minutes REAL, practice_rpe INTEGER,
    strength_volume REAL, game_minutes REAL, total_daily_load REAL,
    -- GPS / Kinexon
    player_load REAL,       -- tri-axial composite (AU)
    accel_count INTEGER,    -- events above threshold
    decel_count INTEGER,    -- events above threshold
    total_distance_km REAL, hsr_distance_m REAL, sprint_distance_m REAL,
    FOREIGN KEY (player_id) REFERENCES players(player_id)
);
```

---

## 5-Minute Interview Demo Script

**30 sec — Command Center:**
> "This is the coach's tab. No clicks — one glance tells them who's green, who's yellow, who to protect. The GPS strip shows team load and flags the low-accel athletes. Red card means modified session only."

**60 sec — Today's Readiness:**
> "Each flag uses personal z-scores, not population averages. Her soreness is 7 but that might be normal for her. We compare to her own 30-day baseline. The 📡 flag here means her accel count dropped two standard deviations — that's a protective movement pattern, often a pre-clinical injury signal."

**60 sec — Correlation Explorer:**
> "This is what separates us. Not just monitoring — discovery. The lag analysis here shows sleep from two nights ago predicts CMJ drop more strongly than last night's sleep. The conditional risk table shows that when accel count drops more than 1.5σ, this dataset shows 2.1× the baseline injury rate within 7 days."

**60 sec — Forecast:**
> "The model was trained on all signals simultaneously — wellness, force plate, and GPS. Feature audit shows GPS z-scores account for about 18% of the model's predictive weight. Each risk card tells you exactly why the athlete is flagged."

**30 sec — Ask the Watchlist:**
> "Any coach or staff can type 'accel drop' or 'poor sleep' and get an instant answer. No SQL, no dashboard literacy required."
