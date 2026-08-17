# WAIMS — Setup Guide

Step-by-step installation and configuration. Covers both the WNBA (fully
synthetic demo) and Arkansas (real game data + synthetic wellness) tracks —
they share one codebase, split only by which sport you tell it to run as.

---

## Requirements

- Python 3.11+
- pip
- ~150 MB disk space (databases + models)

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
```

There is **one shared `dashboard.py`**, not separate copies per sport —
which sport you get depends entirely on an environment variable / URL
parameter at launch time (see below). `MULTI_SPORT_SETUP.md` covers why
it's built this way.

---

## Running WNBA (fully synthetic)

```bash
python generate_database.py   # creates waims_demo.db
python train_models.py        # trains models/*.pkl
streamlit run dashboard.py
# or: python launcher.py --sport wnba
```

Dashboard runs at `http://localhost:8501`. Everything — wellness, load,
force plate, game stats — is synthetic demo data.

---

## Running Arkansas ("mens") — real game data + synthetic wellness

```bash
python launcher.py --sport mens
# or manually:
#   set WAIMS_SPORT=mens          (Windows cmd)
#   $env:WAIMS_SPORT="mens"       (PowerShell)
#   WAIMS_SPORT=mens               (bash)
# then: streamlit run dashboard.py
```

`waims-mens/data/waims_arkansas.db` is **already committed to the repo**
with real data pre-loaded:
- Real box scores and play-by-play from 4 Baha Mar summer games
- Real prior-season log for Billy Richmond III (37 games, 2025-26, via ESPN)
- Synthetic wellness/load/force-plate/injury data layered on top (dates:
  2026-05-17 to 2026-08-14)

**Do not delete `waims-mens/data/waims_arkansas.db` and let it
auto-regenerate.** If it's missing, `launcher.py` will silently rebuild it
by running `generate_database_arkansas.py`, which only creates *synthetic*
data — it has no knowledge of the real box scores/play-by-play/prior-season
data, and running it will overwrite that real data with nothing. If the
real data is ever lost, restore it by re-running, in order:

```bash
python scripts/parse_arkansas_box_scores.py
python scripts/parse_arkansas_play_by_play.py
python scripts/load_prior_season_log.py --player-id ARK013 --season 2025-26 --source espn --csv waims-mens/data/prior_seasons/richmond_billy_iii_2025_26.csv
```

The source PDFs those first two scripts OCR are kept locally only
(`docs/Baha-Mar-Summer-Stats-*.pdf`, gitignored — too large to commit) —
make sure you still have local copies before you ever need to do this.

Those two OCR scripts additionally need `rapidocr-onnxruntime` and
`pymupdf`, which are **not** in `requirements.txt` (they're only needed
for this one-time/rare regeneration path, not for running the dashboard):
```bash
pip install rapidocr-onnxruntime pymupdf
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

`WAIMS_SPORT` (`wnba` or `mens`) is the one that actually matters for
day-to-day use — see "Sport selection on Streamlit Cloud" below for why
it behaves differently there than locally.

---

## File Structure (accurate as of this doc's last update)

```
waims-python/
├── dashboard.py                    # Single shared entry point — routes by WAIMS_SPORT
├── auth.py                         # Role-based login, both sports' demo credentials
├── launcher.py                     # Local convenience wrapper (sets env var + runs streamlit)
├── coach_command_center.py         # Coach-facing morning brief
├── athlete_profile_tab.py          # Per-athlete deep-dive (incl. real game stats section)
├── game_performance_tab.py         # Arkansas-only: box scores/log/shots/advanced metrics
├── game_analytics.py               # PPP, shot efficiency, assist creation, lineup net rating
├── correlation_explorer.py         # Signal discovery (sport-aware since Aug 2026)
├── improved_gauges.py              # Gauge/pill chart components
├── z_score_module.py               # Shared z-score helpers
├── research_context.py             # PRISMA-flagged research citations
├── generate_database.py            # WNBA synthetic data generator
├── train_models.py                 # WNBA model training
├── common/
│   └── sport_config_extended.py    # Per-sport threshold/config definitions
├── waims-mens/
│   ├── roster_arkansas.py          # Arkansas roster (ARK001-ARK0xx player_ids)
│   ├── generate_database_arkansas.py  # Synthetic wellness/load ONLY (see warning above)
│   ├── train_models_arkansas.py
│   ├── data/
│   │   ├── waims_arkansas.db       # Real game data + synthetic wellness (committed)
│   │   └── prior_seasons/*.csv     # Real prior-season logs
│   └── models/
├── scripts/
│   ├── parse_arkansas_box_scores.py     # OCR pipeline: PDF -> player_game_stats
│   ├── parse_arkansas_play_by_play.py   # OCR pipeline: PDF -> play_by_play_events
│   ├── load_prior_season_log.py         # Generic CSV loader -> player_prior_season_games
│   ├── view_arkansas_game_stats.py      # Console sanity-check viewer
│   └── build_arkansas_manual_coding_workbook.py  # Legacy/unused — superseded by the OCR parsers
├── requirements.txt
├── models/                         # WNBA models
├── assets/
└── waims_demo.db                   # WNBA database (gitignored, regenerate locally)
```

---

## Database Tables

| Table | Sport(s) | Created by | Real or synthetic |
|-------|----------|-----------|--------------------|
| `players` | both | generate_database*.py | names real for Arkansas roster; WNBA anonymized |
| `wellness` | both | generate_database*.py | synthetic |
| `training_load` | both | generate_database*.py | synthetic |
| `force_plate` | both | generate_database*.py | synthetic |
| `acwr` | both | generate_database*.py | synthetic |
| `injuries` | both | generate_database*.py | synthetic |
| `availability` | both | generate_database*.py | synthetic |
| `game_results` | both | espn_data.py (WNBA) / parse_arkansas_box_scores.py (ARK) | WNBA real ESPN results; Arkansas real |
| `game_box_scores` | WNBA | espn_data.py | real |
| `player_game_stats` | Arkansas | parse_arkansas_box_scores.py | **real** |
| `play_by_play_events` | Arkansas | parse_arkansas_play_by_play.py | **real** |
| `period_starters` | Arkansas | parse_arkansas_play_by_play.py | **real** |
| `player_prior_season_games` | Arkansas | load_prior_season_log.py | **real** (ESPN) |

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `no such table: schedule` (WNBA) | Run `python generate_database.py` first |
| `models/*.pkl not found` | Run `python train_models.py` (or `train_models_arkansas.py`) |
| Arkansas roster/stats show generic `P2`-style IDs instead of real names, or Game Performance tab is empty | See "sport-aware caching" below — usually a stale deploy, reboot the app |
| Port already in use running two sports locally | `streamlit run dashboard.py --server.port 8502` (or any free port) for the second one |
| `ModuleNotFoundError: scipy` | `pip install scipy` |
| `ModuleNotFoundError` for rapidocr/fitz | Only needed for the OCR regeneration scripts, see above — `pip install rapidocr-onnxruntime pymupdf` |
| Correlation tab shows large-looking r-values that seem too good | Expected with few real games — see the in-app disclosure caption, not a bug |
| `git push` fails with an SSL certificate error on Windows | `git config --global http.sslBackend schannel` (uses Windows' cert store instead of a bundled CA file) |
| PR from a long-lived branch shows a false "merge conflicts" error after a squash merge | Cherry-pick the new commit(s) onto a fresh branch off current `main` and PR that instead |

---

## Streamlit Cloud Deployment

1. Push repo to GitHub (ensure `.env` is in `.gitignore` — it already is)
2. Connect the repo at share.streamlit.io, main file path: `dashboard.py`

### Sport selection on Streamlit Cloud

Locally, `WAIMS_SPORT` as an environment variable works reliably. On
Streamlit Community Cloud, the Secrets panel that's supposed to set it has
proven unreliable in practice (documented upstream:
streamlit/streamlit#4123 — Secrets don't always propagate to `os.environ`).
The code has a fallback chain: `os.environ` → `st.secrets` → the page's own
`?sport=` query parameter. **The query-param route is the one that's
actually been reliable:**

- WNBA: `https://your-app.streamlit.app/`
- Arkansas: `https://your-app.streamlit.app/?sport=mens`

One app, one URL, bookmark both variants. If you'd rather have two fully
separate Cloud apps with their own URLs instead, that also works — deploy
twice from the same repo and set `WAIMS_SPORT = "mens"` in the second
app's Secrets — just budget time for the Secrets panel to be flaky.

3. (Optional) API key secrets, same as `.env` above:
   ```
   ANTHROPIC_API_KEY = "your_key"
   BALLDONTLIE_API_KEY = "your_key"
   ```
4. `waims_demo.db` must be committed to the repo for WNBA on Cloud (or add
   generation to app startup). `waims-mens/data/waims_arkansas.db` is
   already committed with real data — see the warning above about not
   letting it get silently regenerated.
5. Direct pushes to `main` are blocked by a repository rule (PR required).
   Merge via a pull request — `gh pr create` / `gh pr merge` from the
   command line works well if the GitHub website is slow or unresponsive.
