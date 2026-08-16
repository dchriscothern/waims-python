"""
WAIMS Multi-Sport Setup Guide
==============================

This guide explains how to set up and run both the WNBA and Men's Power 5
basketball versions of WAIMS (Wellness & Athlete Injury Management System).

---

## ✅ Quick Start

### Option 1: Guided Setup (Recommended for first run)
```bash
cd c:\GitHub\waims-python
python launcher.py --setup
```

### Option 2: Direct Launch

**WNBA Version (Dallas Wings Demo):**
```bash
python launcher.py --sport wnba
```

**Men's Version (Arkansas Razorbacks):**
```bash
python launcher.py --sport mens
```

### Option 3: View Available Options
```bash
python launcher.py --list
```

---

## 📁 Directory Structure

```
waims-python/
├── launcher.py                          # Multi-sport launcher (NEW)
├── common/                              # Shared utilities (NEW)
│   └── sport_config_extended.py        # Extended sport configuration
│
├── waims-wnba/                          # WNBA version (refactored)
│   ├── dashboard.py
│   ├── coach_command_center.py
│   ├── athlete_profile_tab.py
│   ├── improved_gauges.py
│   ├── z_score_module.py
│   ├── research_citations.py
│   ├── data/
│   │   └── (WNBA database)
│   └── models/
│       └── (WNBA models)
│
├── waims-mens/                          # Men's Power 5 version (NEW)
│   ├── dashboard.py                     # (shared from WNBA, configurable)
│   ├── coach_command_center.py          # (shared from WNBA, configurable)
│   ├── roster_arkansas.py              # Arkansas roster data
│   ├── generate_database_arkansas.py   # Men's data generator
│   ├── train_models_arkansas.py        # Men's model training
│   ├── data/
│   │   └── waims_arkansas.db           # Arkansas database
│   └── models/
│       ├── injury_risk_model.pkl       # Trained model
│       └── feature_scaler.pkl          # Feature scaler
│
├── generate_database.py                 # WNBA data generator (existing)
├── train_models.py                      # WNBA model training (existing)
├── fetch_wehoop_data.py                # 2026 WNBA stats fetcher (UPDATED)
└── [other existing files...]
```

---

## 🚀 Getting Started

### Step 1: Environment Setup

Ensure you have Python 3.9+ and the required dependencies:

```bash
cd c:\GitHub\waims-python
pip install -r requirements.txt
```

Key packages:
- streamlit (dashboard UI)
- pandas, numpy (data processing)
- scikit-learn (machine learning)
- sqlite3 (database)
- plotly (visualization)
- wehoop (WNBA data fetching)

### Step 2: Choose Your Version

**For WNBA (first time):**
```bash
python launcher.py --setup
# Select option 1: WNBA Basketball
# This generates synthetic data and trains the model
```

**For Arkansas Men's (first time):**
```bash
python launcher.py --setup
# Select option 2: Men's Power 5 Basketball
# This generates synthetic data and trains the model
```

### Step 3: Launch Dashboard

**WNBA:**
```bash
python launcher.py --sport wnba
```

**Arkansas Men's:**
```bash
python launcher.py --sport mens
```

The dashboard will open automatically in your browser at `http://localhost:8501`

---

## 📊 What's in Each Version?

### WNBA Version
- **Team:** Dallas Wings (fictional demo roster)
- **Population:** Female basketball players
- **Data:** 90 days synthetic, 2026 season mid-way
- **Database:** `waims_demo.db`
- **Thresholds:** Women-specific (sleep, CMJ, RSI, GPS)
- **Models:** Random Forest injury risk classifier, readiness calculator

**Key Differences from Men's:**
- Lower GPS baselines (decel counts, sprint distance)
- Different sleep targets (9h optimal vs 9.5h)
- Female-specific physiology in CMJ/RSI expectations
- WNBA-specific schedule (40-game season, ~3 games/week)

### Men's Power 5 Version (Arkansas Razorbacks)
- **Team:** Arkansas Razorbacks (SEC)
- **Population:** Male college basketball players (real 14-player roster)
- **Data:** 90 days synthetic, reflects college schedule
- **Database:** `waims-mens/data/waims_arkansas.db`
- **Thresholds:** Men-specific (higher CMJ, different sleep patterns)
- **Models:** Random Forest injury risk classifier, readiness calculator

**Key Differences from WNBA:**
- Higher GPS baselines (male athletes produce more force)
- Higher sleep targets (college recovery crucial)
- Different soreness thresholds (college athletes report differently)
- NCAA compliance considerations (FERPA, state consent laws)
- Tournament play common (frequent back-to-back games)

---

## 🔧 Customization

### Adjusting Sport Thresholds

Edit `common/sport_config_extended.py`:

```python
"mens_power5_basketball": {
    "thresholds": {
        "sleep_minimum_hrs": 6.5,
        "sleep_flag_hrs": 7.5,
        "cmj_zscore_flag": -0.9,  # Adjust as needed
        "minutes_4day_flag": 130,
        # ... other thresholds
    }
}
```

### Adding a New Team

```python
TEAM_CONFIGS = {
    "arkansas_razorbacks": {
        "display_name": "Arkansas Razorbacks",
        "sport": "mens_power5_basketball",
        "conference": "SEC",
        "threshold_overrides": {
            "minutes_4day_flag": 135,  # Team-specific
        },
    },
    # Add new team here:
    "duke_blue_devils": {
        "display_name": "Duke Blue Devils",
        "sport": "mens_power5_basketball",
        "conference": "ACC",
        "threshold_overrides": {},
    },
}
```

### Adding a New Sport

1. Add sport config to `common/sport_config_extended.py`:

```python
"my_sport_basketball": {
    "display_name": "My Sport Basketball",
    "population": "mixed",
    "readiness_weights": { ... },
    "thresholds": { ... },
    # ... etc
}
```

2. Create version-specific directory:
```bash
mkdir waims-mysport
# Create dashboard.py, data generator, model training scripts
```

3. Update `launcher.py` to include new sport in `SPORT_CONFIGS`

---

## 📈 Data Workflow

### WNBA Workflow
1. **fetch_wehoop_data.py** → Fetches real 2026 WNBA stats via wehoop API
2. **generate_database.py** → Creates synthetic demo data (merges with real stats if available)
3. **train_models.py** → Trains RF model on wellness + GPS + force plate data
4. **dashboard.py** → Displays readiness, injury risk, trends, etc.

### Arkansas Men's Workflow
1. **roster_arkansas.py** → Defines 14-player roster with realistic attributes
2. **generate_database_arkansas.py** → Creates synthetic college basketball data
3. **train_models_arkansas.py** → Trains RF model with men's-specific baselines
4. **dashboard.py** → Same UI, different thresholds and data

---

## 🧪 Testing

### Check Available Sports
```bash
python launcher.py --list
```

### Verify Database Creation
```bash
cd waims-wnba
python ../generate_database.py
# Check for: waims_demo.db

cd ../waims-mens
python generate_database_arkansas.py
# Check for: data/waims_arkansas.db
```

### Verify Model Training
```bash
python train_models.py          # WNBA
python train_models_arkansas.py # Arkansas
# Check for .pkl files in models/ directory
```

### Run Dashboard Locally
```bash
python launcher.py --sport wnba  # Test WNBA
python launcher.py --sport mens  # Test Arkansas
# Navigate to http://localhost:8501
```

---

## 🔐 Multi-Sport Security Considerations

### Data Isolation
- WNBA data: `waims_demo.db` (root)
- Arkansas data: `waims-mens/data/waims_arkansas.db` (separate)
- No cross-team data access in current V1

### Future (V2)
- RBAC (role-based access control)
- SSO (Okta/Azure AD)
- Encryption at rest
- Audit logs
- Separate database servers per sport/team

---

## 📝 Shared Components

### Used by Both Versions
- `sport_config_extended.py` — Sport/team configuration
- `improved_gauges.py` — Readiness visualization components
- `z_score_module.py` — Baseline z-score calculations
- `research_citations.py` — Evidence base display
- `auth.py` — Role-based login

### Sport-Specific Components
- **WNBA:** `generate_database.py`, `train_models.py`, dashboard with WNBA thresholds
- **Arkansas:** `generate_database_arkansas.py`, `train_models_arkansas.py`, dashboard with men's thresholds

---

## 🐛 Troubleshooting

### "Database not found" on first run
```bash
python launcher.py --setup
# Select your sport and let it generate data automatically
```

### "Model not found" error
```bash
cd waims-wnba           # or waims-mens
python train_models.py  # or train_models_arkansas.py
```

### Streamlit connection errors
```bash
# Restart streamlit
# Close browser, run launcher.py again
python launcher.py --sport wnba
```

### Import errors
```bash
# Ensure you're in the right directory
cd c:\GitHub\waims-python
python -m pip install -r requirements.txt
```

---

## 📚 Key Resources

- `README.md` — Full project documentation
- `RESEARCH_FOUNDATION.md` — Evidence base for thresholds
- `WAIMS_GLOBAL_CONTEXT.md` — Session context
- `AGENTS.md` — Development planning
- `claude.md` — Claude AI notes

---

## 🎯 Next Steps

### Short-term (V1.1)
- [ ] Deploy WNBA version with 2026 stats
- [ ] Test Arkansas Men's version locally
- [ ] Add more Power 5 teams as needed

### Medium-term (V2)
- [ ] Integrate live Kinexon/ForceDecks APIs
- [ ] Add positional GPS norms
- [ ] Implement RBAC + SSO
- [ ] NCAA compliance review (FERPA, state laws)
- [ ] Second Spectrum / Springbok Analytics integration

### Long-term (V3)
- [ ] MCP server integration
- [ ] Athlete-facing mobile app
- [ ] Predictive analytics expansion

---

## ❓ FAQ

**Q: Can I run both versions simultaneously?**
A: Yes, but on different ports:
```bash
# Terminal 1: WNBA
streamlit run waims-wnba/dashboard.py --server.port 8501

# Terminal 2: Arkansas
streamlit run waims-mens/dashboard.py --server.port 8502
```

**Q: How do I update WNBA stats?**
A: Run the updated fetch_wehoop_data.py script:
```bash
python fetch_wehoop_data.py
# This pulls 2026 season stats and updates waims_demo.db
```

**Q: Can I add my own team?**
A: Yes! Follow the "Adding a New Team" section in Customization above.

**Q: Is real player data used?**
A: Arkansas roster uses real 2024-25 player names (for portfolio). 
All statistics are synthetic/demo. WNBA version uses fully anonymized names.

**Q: What about GDPR/HIPAA compliance?**
A: This is portfolio demo code. Real deployment requires:
- Consent management
- Encryption at rest & in transit
- Audit logging
- Data residency compliance
- WNBA CBA review (for WNBA)
- FERPA review (for NCAA)

---

Last updated: August 14, 2026
"""

# Print this to console if run directly
if __name__ == "__main__":
    print(__doc__)
