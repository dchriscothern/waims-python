# WAIMS — Setup Guide

Step-by-step installation and configuration.

---

## Requirements

- Python 3.12+
- pip
- ~50 MB disk space (database + models)

---

## Installation

```bash
# 1. Clone or download the repo
git clone https://github.com/yourname/waims.git
cd waims

# 2. Install dependencies
pip install -r requirements.txt

# 3. Generate database (creates waims_demo.db with GPS columns)
python generate_database.py

# 4. Train ML models
python train_models.py

# 5. Launch dashboard
streamlit run dashboard.py
```

Dashboard runs at `http://localhost:8501`

---

## requirements.txt

```
streamlit>=1.32.0
pandas>=2.0.0
numpy>=1.24.0
plotly>=5.18.0
scikit-learn>=1.4.0
scipy>=1.11.0
```

Optional (real WNBA data):
```
wehoop>=1.8.0
```

---

## File Structure

```
waims/
├── dashboard.py               # Main app — 10 tabs
├── coach_command_center.py    # Tab 1: Coach morning brief
├── correlation_explorer.py    # Tab 10: Hidden signal discovery
├── athlete_profile_tab.py     # Tab 3: Per-athlete deep-dive
├── generate_database.py       # DB creation + GPS synthetic data
├── train_models.py            # RF injury model + readiness scorer
├── smart_query.py             # Standalone NL query interface
├── improved_gauges.py         # Chart components (optional)
├── z_score_module.py          # Shared z-score helpers (optional)
├── research_citations.py      # Research modal (optional)
├── research_context.py        # Risk context box (optional)
├── requirements.txt
├── models/                    # Created by train_models.py
│   ├── injury_risk_model.pkl
│   └── readiness_scorer.pkl
├── data/                      # Created by train_models.py
│   └── processed_data.csv
├── assets/
│   ├── branding/
│   │   └── waims_run_man_logo.png
│   └── photos/                # Optional athlete photos
└── waims_demo.db              # Created by generate_database.py
```

---

## Tab Overview

| # | Tab | File | Audience |
|---|-----|------|----------|
| 1 | 🏀 Command Center | `coach_command_center.py` | Coach |
| 2 | 📊 Today's Readiness | `dashboard.py` | Analyst |
| 3 | 👤 Athlete Profiles | `athlete_profile_tab.py` | Analyst |
| 4 | 📈 Trends | `dashboard.py` | Analyst |
| 5 | 💪 Jump Testing | `dashboard.py` | Analyst |
| 6 | 🚨 Availability & Injuries | `dashboard.py` | GM / Medical |
| 7 | 📡 GPS & Load | `dashboard.py` | Analyst |
| 8 | 🤖 Forecast | `dashboard.py` | GM |
| 9 | 🔍 Ask the Watchlist | `dashboard.py` | All |
| 10 | 🔬 Correlations | `correlation_explorer.py` | Analyst |

---

## Database Tables

| Table | Key Columns |
|-------|-------------|
| `players` | player_id, name, position, age, injury_history_count |
| `wellness` | player_id, date, sleep_hours, sleep_quality, soreness, stress, mood |
| `training_load` | player_id, date, practice_minutes, practice_rpe, total_daily_load, **player_load, accel_count, decel_count**, total_distance_km, hsr_distance_m, sprint_distance_m |
| `force_plate` | player_id, date, cmj_height_cm, asymmetry_percent, rsi_modified |
| `acwr` | player_id, date, acwr, acute_load, chronic_load |
| `injuries` | player_id, injury_date, injury_type, severity, days_missed |
| `availability` | player_id, date, status, practice_status |

---

## Optional Enhancements

### Athlete Photos
Place image files in `assets/photos/` named by player key:
```
assets/photos/ath_001.jpg   # for player_id P001
assets/photos/ath_002.jpg
```

### Real WNBA Data (wehoop)
```bash
pip install wehoop
python fetch_real_data.py   # if you've built this module
```

### Standalone Query Interface
```bash
streamlit run smart_query.py --server.port 8502
```

---

## Run Order (Always)

```
1. python generate_database.py    # must run first — creates DB with GPS
2. python train_models.py         # must run after DB exists
3. streamlit run dashboard.py     # run last
```

If you modify `generate_database.py` (e.g. add columns), always retrain:
```bash
python generate_database.py && python train_models.py
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `waims_demo.db not found` | Run `python generate_database.py` first |
| `models/injury_risk_model.pkl not found` | Run `python train_models.py` |
| GPS sections blank / hidden | GPS columns missing — regenerate DB |
| `ModuleNotFoundError: scipy` | `pip install scipy` |
| Correlation tab empty | Need ≥ 10 records — ensure DB generated correctly |
| `ImportError: coach_command_center` | Ensure `coach_command_center.py` is in same directory as `dashboard.py` |
| `ImportError: correlation_explorer` | Ensure `correlation_explorer.py` is in same directory |
| Accel/decel flags never fire | Check `player_load` column exists: `sqlite3 waims_demo.db ".schema training_load"` |
| Port already in use | `streamlit run dashboard.py --server.port 8502` |

---

## Privacy / Sharing

Before any public demo or GitHub push:
```bash
python anonymize_players.py   # replaces names with ATH_001 etc.
```

The demo DB uses public WNBA player names for realism in portfolio presentations — confirm consent before sharing in professional contexts.
