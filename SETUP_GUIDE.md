# WAIMS — Setup Guide

Step-by-step installation and configuration.

---

## Requirements

- Python 3.11+
- pip
- ~100 MB disk space (database + models + ESPN data)

---

## Installation

```bash
# 1. Clone repo
git clone https://github.com/dchriscothern/waims-python.git
cd waims-python

# 2. Create virtual environment (recommended)
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # Windows PowerShell
# source .venv/bin/activate     # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Generate demo database
python generate_database.py

# 5. (Optional but recommended) Fetch real ESPN game data
python espn_data.py
# Then in Python:
# from espn_data import fetch_wings_all_time
# fetch_wings_all_time(seasons=[2024, 2025])

# 6. Train models
python train_models.py

# 7. Launch dashboard
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
requests>=2.31.0
python-dotenv>=1.0.0
anthropic>=0.20.0
```

---

## Environment Variables (Optional)

Create a `.env` file in the project root for API integrations:

```
# Claude API — enables Ask the Watchlist generative AI tab
ANTHROPIC_API_KEY=your_key_here

# balldontlie — enables live WNBA benchmarks (paid tier required for stats)
BALLDONTLIE_API_KEY=your_key_here
```

Never commit `.env` to GitHub — add to `.gitignore`.

For Streamlit Cloud deployment: Settings → Secrets → add same key/value pairs.

---

## File Structure

```
waims-python/
├── dashboard.py                 # Main app — 10 tabs
├── coach_command_center.py      # Tab 1: Coach morning brief
├── athlete_profile_tab.py       # Tab 3: Per-athlete deep-dive
├── correlation_explorer.py      # Tab 10: Signal discovery + ESPN correlations
├── generate_database.py         # DB creation — 12 players, 90 days, schedule
├── train_models.py              # RF model + readiness scorer + Section 8 validation
├── espn_data.py                 # ESPN WNBA box scores 2019–2025 (no API key)
├── wnba_api.py                  # WNBA positional benchmarks (static 2025)
├── smart_query.py               # Generative AI natural-language query
├── improved_gauges.py           # Gauge/pill chart components (optional)
├── z_score_module.py            # Shared z-score helpers (optional)
├── research_citations.py        # Research modal (optional)
├── research_context.py          # Risk context box (optional)
├── .env                         # API keys — never commit (in .gitignore)
├── .env.example                 # Template — safe to commit
├── requirements.txt
├── models/                      # Created by train_models.py
│   ├── injury_risk_model.pkl
│   └── readiness_scorer.pkl
├── data/                        # Created by train_models.py
│   └── processed_data.csv       # All player-days with injury_risk_score
├── assets/
│   ├── branding/
│   │   └── waims_run_man_logo.png
│   └── photos/                  # Optional athlete photos
└── waims_demo.db                # Created by generate_database.py
```

---

## Run Order (Always)

```
1. python generate_database.py     # must run first
2. python espn_data.py             # optional — run once, re-run for new seasons
3. python train_models.py          # must run after generate_database.py
4. streamlit run dashboard.py
```

If you modify `generate_database.py`, always retrain:
```bash
python generate_database.py && python train_models.py
```

---

## Database Tables

| Table | Created by | Key columns |
|-------|-----------|-------------|
| `players` | generate_database.py | player_id, name, position, age |
| `wellness` | generate_database.py | player_id, date, sleep_hours, soreness, stress, mood, hrv |
| `training_load` | generate_database.py | player_id, date, player_load, accel_count, decel_count, total_distance_km |
| `force_plate` | generate_database.py | player_id, date, cmj_height_cm, rsi_modified, asymmetry_percent |
| `acwr` | generate_database.py | player_id, date, acwr, acute_load, chronic_load |
| `schedule` | generate_database.py | date, opponent, is_back_to_back, days_rest, travel_flag, game_type |
| `injuries` | generate_database.py | player_id, injury_date, injury_type, severity, days_missed |
| `availability` | generate_database.py | player_id, date, status, practice_status |
| `game_results` | espn_data.py | date, opponent, result, score_margin, home_away |
| `game_box_scores` | espn_data.py | player_name, date, pts, minutes, plus_minus, reb, ast |
| `wnba_benchmarks` | wnba_api.py | position_group, metric, mean, std, n_players |
| `ml_predictions` | train_models.py | player_id, date, injury_risk_score, readiness_score |
| `back_to_back_analysis` | train_models.py | rest_category, pts_mean, min_mean, games |
| `pre_injury_patterns` | train_models.py | player_id, injury_date, pre_inj_avg_sleep, pre_inj_avg_cmj |
| `readiness_validation` | train_models.py | date, readiness_score, pts, plus_minus — r values |

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `no such table: schedule` | Run `python generate_database.py` first |
| `models/*.pkl not found` | Run `python train_models.py` |
| GPS sections blank | Regenerate DB — GPS columns missing |
| `ModuleNotFoundError: scipy` | `pip install scipy` |
| Correlation tab empty | Need ≥ 10 records — ensure DB generated |
| NaN in game correlations | Demo dates don't overlap game dates — expected with synthetic data |
| ESPN fetch returns no games | Check network — ESPN API works from local machine |
| `[Model Improvement] Skipped` | See error message — usually missing import or table |
| Port already in use | `streamlit run dashboard.py --server.port 8502` |

---

## Streamlit Cloud Deployment

1. Push repo to GitHub (ensure `.env` is in `.gitignore`)
2. Connect repo at share.streamlit.io
3. Settings → Secrets → add:
   ```
   ANTHROPIC_API_KEY = "your_key"
   BALLDONTLIE_API_KEY = "your_key"
   ```
4. Note: `waims_demo.db` must be committed to repo for cloud deployment  
   (or add DB generation to app startup)

---

## Live And Staging Workflow

Use two branches and two Streamlit apps:

- `main` = stable live WAIMS demo
- `codex/staging` = safe test branch for new features
- live Streamlit app -> `main` + `dashboard.py`
- staging Streamlit app -> `codex/staging` + `dashboard.py`

This lets you test role changes, UI updates, and new features without touching the live demo until you merge.

### Athlete View In Staging

The staging branch currently includes a demo athlete role:

- login: `athlete / athlete123`
- scope: only the logged-in athlete's own data
- surface: readiness, trends, voice/text questions, and simple recovery guidance

Do not expose teammate names, roster tables, or cross-athlete injury-risk views in the athlete role.
