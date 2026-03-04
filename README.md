# WAIMS — Readiness Watchlist

**Professional Athlete Monitoring Dashboard**  
Built with Python · Streamlit · SQLite · Plotly

> Dallas Wings-inspired demo — 90 days · 12 players · 10,000+ data points

---

## Quick Start

```bash
pip install -r requirements.txt
python generate_database.py   # creates DB with GPS columns
python train_models.py        # trains injury risk + readiness models
streamlit run dashboard.py
```

Dashboard opens at `http://localhost:8501`

---

## Features

### 10 Interactive Tabs

| Tab | Audience | Purpose |
|-----|----------|---------|
| 🏀 Command Center | **Coach** | 30-second morning brief — traffic light roster grid, priority alerts, GPS strip, team sparklines |
| 📊 Today's Readiness | Analyst | Z-score status, wellness + force plate + GPS flags per player |
| 👤 Athlete Profiles | Analyst | Full per-player deep-dive with radar chart, GPS trends, baseline comparisons |
| 📈 Trends | Analyst | 7-day rolling averages for sleep, soreness, mood, stress |
| 💪 Jump Testing | Analyst | CMJ & RSI vs personal baseline; 7-day team trend |
| 🚨 Availability & Injuries | GM / Medical | Daily availability board, season %, injury log |
| 📡 GPS & Load | Analyst | Kinexon metrics, 14-day trends, player load ACWR |
| 🤖 Forecast | GM | Multi-signal 7-day injury risk watchlist |
| 🔍 Ask the Watchlist | All | Natural-language query shortcuts incl. GPS queries |
| 🔬 Correlations | Analyst | Hidden signal discovery — heatmap, lag analysis, conditional risk |

### Monitoring Signals

- **Wellness** — Sleep, soreness, stress, mood (subjective daily)
- **Force Plate** — CMJ height, RSI-Modified (neuromuscular)
- **GPS / Kinexon** — Player load, accel count, decel count, distance, HSR, sprint
- **ACWR** — Acute:Chronic Workload Ratio (training load)

### Classification Engine

All player flags use **personal z-scores** (deviation from individual 30-day baseline), not population averages. Hard safety floors apply regardless of baseline:

- Sleep < 6.5 hrs → immediate flag
- Soreness or Stress > 7/10 → immediate flag
- CMJ/RSI drops weighted 1.5× vs subjective metrics
- GPS load/accel/decel drops flagged when > 1σ below personal norm

### Correlation Explorer

Surfaces hidden relationships the standard dashboard doesn't show:

- **Heatmap** — Pearson r across all metrics including injury label
- **Lag Analysis** — which lag (0–7 days prior) gives the strongest predictive signal
- **Conditional Risk** — P(injury within 7 days | metric flagged) vs baseline rate
- **Per-Player Fingerprints** — individual sleep→soreness correlations
- **Model Audit** — RF feature importance split across wellness / GPS / force plate

---

## Database

**File:** `waims_demo.db` (SQLite)

| Table | Rows | Description |
|-------|------|-------------|
| `players` | 12 | Roster — name, position, age, injury history |
| `wellness` | ~1,080 | Daily sleep, soreness, stress, mood |
| `training_load` | ~1,080 | Practice/game minutes, RPE, **GPS metrics** |
| `force_plate` | ~84 | CMJ height, RSI-Modified (weekly tests) |
| `acwr` | ~600 | Acute:Chronic Workload Ratio |
| `injuries` | ~5 | Injury events with dates and severity |
| `availability` | ~1,080 | Daily AVAILABLE / QUESTIONABLE / OUT status |

### training_load GPS Columns

| Column | Unit | Description |
|--------|------|-------------|
| `player_load` | AU | Kinexon tri-axial composite |
| `accel_count` | events | Accelerations above threshold |
| `decel_count` | events | Decelerations above threshold |
| `total_distance_km` | km | Total session distance |
| `hsr_distance_m` | m | High-speed running distance |
| `sprint_distance_m` | m | Sprint distance |

---

## Machine Learning

**Injury Risk Predictor** — RandomForest Classifier  
**Readiness Scorer** — Composite 0–100 with personal deviation modifier

Features include: sleep z-score, soreness z-score, stress z-score, CMJ z-score, RSI z-score, GPS player load, accel/decel deviations, ACWR, injury history, age, 7-day rolling averages, and GPS drop flags.

```bash
python train_models.py
# Outputs: models/injury_risk_model.pkl
#          models/readiness_scorer.pkl
```

---

## File Structure

```
waims/
├── dashboard.py               # Main Streamlit app (10 tabs)
├── coach_command_center.py    # Tab 1 — Coach morning brief
├── correlation_explorer.py    # Tab 10 — Hidden signal discovery
├── athlete_profile_tab.py     # Tab 3 — Per-athlete deep-dive
├── generate_database.py       # Synthetic data + GPS generation
├── train_models.py            # RF injury model + readiness scorer
├── smart_query.py             # NL query interface (standalone)
├── improved_gauges.py         # Gauge / battery chart components
├── z_score_module.py          # Shared z-score calculation helpers
├── research_citations.py      # Research foundation modal
├── models/
│   ├── injury_risk_model.pkl
│   └── readiness_scorer.pkl
├── data/
│   └── processed_data.csv
└── waims_demo.db
```

---

## Research Foundation

| Metric | Source |
|--------|--------|
| ACWR thresholds (0.8–1.3 optimal) | Gabbett (2016) — 2,000+ citations |
| Sleep < 6.5 hrs injury risk 1.7× | Milewski (2014) — 500+ citations |
| Asymmetry thresholds (women) | Bishop (2018), Hewett (2006) |
| WNBA knee injury risk factors | Menon et al. (2026) |
| Subjective > objective monitoring | Saw et al. (2016) |
| Accel/decel drop → injury | Jaspers et al. (2018) |
| CMJ as fatigue marker | Gathercole et al. (2015) |

---

## Tech Stack

- **Python 3.12+**
- **Streamlit** — web framework
- **Plotly** — interactive charts
- **pandas / numpy** — data manipulation
- **SQLite** — database
- **scikit-learn** — ML models
- **scipy** — Pearson correlation + p-values (Correlation Explorer)
- **wehoop** *(optional)* — real WNBA game data via ESPN API

---

## Privacy

- All demo data uses anonymized athlete IDs (`ATH_001`, `ATH_002`, …)
- No real protected health information in this repository
- Run `python anonymize_players.py` before any public sharing

---

## License

MIT — Portfolio demonstration project  
*Built by Chris Cothern, Sport Scientist*
