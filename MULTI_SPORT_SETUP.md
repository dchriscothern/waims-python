# WAIMS Multi-Sport Architecture

How WNBA and Arkansas Men's Basketball share one codebase, and what's
actually real vs. synthetic in each. For install/run commands, see
`SETUP_GUIDE.md` — this doc is about *why* it's built the way it is.

---

## The actual architecture (corrects an earlier draft of this doc)

There is **one shared `dashboard.py`** (and one shared `auth.py`,
`athlete_profile_tab.py`, etc.) at the repo root. There is no separate
`waims-wnba/dashboard.py` or `waims-mens/dashboard.py` — an earlier
version of this document described that split as if it existed; it never
did. Which sport you get is decided entirely by `get_active_sport()` in
`dashboard.py`, which checks, in order:

1. `WAIMS_SPORT` environment variable (reliable locally)
2. `st.secrets["WAIMS_SPORT"]` (Streamlit Cloud's Secrets panel — proven
   unreliable in practice, see `SETUP_GUIDE.md`)
3. `?sport=` query parameter on the page URL (the reliable Cloud option)
4. Falls back to `wnba` if none of the above are set

`waims-mens/` holds Arkansas-specific data files (`roster_arkansas.py`,
the database, models) but the dashboard code itself is not duplicated —
`get_paths_for_sport()` just points `DB_PATH`/`model_path` at the right
files for whichever sport is active.

---

## Quick Start

```bash
python launcher.py --sport wnba     # WNBA
python launcher.py --sport mens     # Arkansas
python launcher.py --list           # Show available sports
python launcher.py --setup          # Interactive first-time setup
```

Full install steps: `SETUP_GUIDE.md`.

---

## What's in each version — and what's real

### WNBA
- Anonymized roster, fully synthetic wellness/load/force-plate/game data
- `waims_demo.db`

### Arkansas Razorbacks
- Real roster names
- **Real game data**: box scores and play-by-play from 4 real Baha Mar
  summer games (parsed via OCR from the official PDFs), plus a real full
  2025-26 prior season for Billy Richmond III (37 games, from ESPN)
- **Synthetic** wellness, sleep, load, force plate, injuries, ACWR —
  same as WNBA, randomly generated, not real observations
- `waims-mens/data/waims_arkansas.db`

The app is explicit about this split in the UI itself: a sidebar "Data
source key" banner, a green "Real data" badge on the Game Performance
section of the Athlete Profile tab, and disclosure captions on the
Correlation Explorer tab. If you're extending this to a new team, keep
that real/synthetic labeling — don't let synthetic data pass as real or
vice versa; that's a trust problem, not just a cosmetic one.

An earlier version of this doc's FAQ said Arkansas was "real names, all
statistics synthetic" — that was accurate when written, before the real
game-data pipeline was built, and is no longer true. Corrected above.

---

## Customization

### Adjusting sport thresholds

Edit `common/sport_config_extended.py`:

```python
"mens_power5_basketball": {
    "thresholds": {
        "sleep_minimum_hrs": 6.5,
        "sleep_flag_hrs": 7.5,
        "cmj_zscore_flag": -0.9,
        "minutes_4day_flag": 130,
    }
}
```

### Adding a new team (synthetic data only)

```python
TEAM_CONFIGS = {
    "arkansas_razorbacks": {
        "display_name": "Arkansas Razorbacks",
        "sport": "mens_power5_basketball",
        "conference": "SEC",
        "threshold_overrides": {"minutes_4day_flag": 135},
    },
    "duke_blue_devils": {
        "display_name": "Duke Blue Devils",
        "sport": "mens_power5_basketball",
        "conference": "ACC",
        "threshold_overrides": {},
    },
}
```

This gets you a new team with synthetic wellness/load data out of the
box. It does **not** get you real game data — that requires either
manually running the OCR pipeline against that team's own box-score PDFs
(see `scripts/parse_arkansas_box_scores.py` — currently tuned to one
specific PDF layout, would need column-position adjustments for a
different source) or an ESPN gamelog fetch like
`scripts/load_prior_season_log.py` does for Billy Richmond. There's no
one-command "add real data for a new team" path yet.

### Adding a new sport

1. Add a sport config block to `common/sport_config_extended.py`
2. `get_paths_for_sport()` in `dashboard.py` needs a new branch pointing
   at that sport's database/model paths
3. Update `launcher.py`'s `SPORT_CONFIGS` dict

---

## Security considerations

**Current state (portfolio/demo):** logins are hardcoded username/password
pairs in `auth.py` (`DEMO_USERS`), no encryption at rest, no audit
logging, databases are just files distinguished by path. That's
appropriate for a demo — it is not appropriate for real athletes' real
data.

**If this were ever used with a real team's real data**, that gap needs
to close before anything else does. See `GOING_LIVE_CHECKLIST.md` for the
actual list — it's a substantially bigger lift than anything documented
here (real auth, compliant hosting, legal/compliance review), not a
config change.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| "Database not found" on first run | `python launcher.py --setup`, pick your sport |
| Arkansas dashboard shows placeholder names (`P2`, etc.) instead of real ones | Stale Cloud deploy or the zero-argument caching bug (fixed as of PR #24) — reboot the app |
| Import errors | Confirm you're in the repo root and ran `pip install -r requirements.txt` |

---

## Key Resources

- `SETUP_GUIDE.md` — install/run commands, deployment, troubleshooting
- `GOING_LIVE_CHECKLIST.md` — what "actually using this with a real team" requires
- `PRIVACY.md` — FERPA/HIPAA guidance (product guidance, not legal advice)
- `RESEARCH_FOUNDATION.md` — evidence base for thresholds

---

## FAQ

**Q: Can I run both versions simultaneously?**
A: Yes, on different ports:
```bash
WAIMS_SPORT=wnba streamlit run dashboard.py --server.port 8501
WAIMS_SPORT=mens streamlit run dashboard.py --server.port 8502
```
(PowerShell: `$env:WAIMS_SPORT="mens"; streamlit run dashboard.py --server.port 8502`)

**Q: Is real player data used?**
A: For Arkansas: real roster names, real 4-game box scores/play-by-play,
real prior-season stats for Billy Richmond III — all real. Wellness,
sleep, load, force plate, injuries are synthetic for both teams. See the
in-app "Real data" badges and disclosure captions for exactly which
section is which.

**Q: What about GDPR/HIPAA/FERPA compliance if this became real?**
A: See `GOING_LIVE_CHECKLIST.md`. Short version: real auth, compliant
hosting with a signable BAA, a real legal/compliance review, and (if
partnering with a university) IRB approval are all required — none of
that exists yet, by design, since this is currently a demo with synthetic
sensitive data.

---

Last updated: 2026-08-17
