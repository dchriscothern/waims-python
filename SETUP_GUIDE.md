# WAIMS Python - Complete Setup Guide

**Professional Athlete Monitoring System with Machine Learning**

Built with Python, Streamlit, SQLite, and wehoop integration for real WNBA data.

---

## 📋 Table of Contents

1. [Quick Start](#quick-start)
2. [System Requirements](#system-requirements)
3. [Installation](#installation)
4. [File Structure](#file-structure)
5. [Usage Guide](#usage-guide)
6. [Features](#features)
7. [Data Sources](#data-sources)
8. [ML Model](#ml-model)
9. [Customization](#customization)
10. [Troubleshooting](#troubleshooting)
11. [Privacy & Ethics](#privacy--ethics)
12. [FAQ](#faq)

---

## 🚀 Quick Start

**Get running in 5 minutes:**

```bash
# 1. Clone or download repository
cd waims-python

# 2. Install dependencies
pip install -r requirements.txt

# 3. Generate sample database
python generate_database_research.py

# 4. Train ML models
python train_models.py

# 5. Launch dashboard
streamlit run dashboard.py
```

Dashboard opens at: `http://localhost:8501`

---

## 💻 System Requirements

### **Minimum:**
- Python 3.10+
- 4GB RAM
- 500MB disk space
- Windows, Mac, or Linux

### **Recommended:**
- Python 3.12+
- 8GB RAM
- 1GB disk space
- Modern web browser (Chrome, Firefox, Safari)

### **Optional:**
- wehoop package (for real WNBA data)
- Internet connection (for wehoop API)

---

## 📦 Installation

### **Step 1: Install Python**

**Windows:**
- Download from: https://www.python.org/downloads/
- Run installer, check "Add Python to PATH"

**Mac:**
```bash
brew install python@3.12
```

**Linux:**
```bash
sudo apt-get install python3.12
```

---

### **Step 2: Install Dependencies**

```bash
# Navigate to project folder
cd waims-python

# Install required packages
pip install -r requirements.txt
```

**Packages installed:**
- pandas (data manipulation)
- numpy (numerical operations)
- scikit-learn (machine learning)
- streamlit (web dashboard)
- plotly (interactive charts)
- wehoop (WNBA data - optional)

---

### **Step 3: Verify Installation**

```bash
# Check Python version
python --version
# Should show: Python 3.10.x or higher

# Check packages
pip list | grep streamlit
# Should show: streamlit x.x.x
```

---

## 📁 File Structure

```
waims-python/
├── README.md                        # Project overview
├── SETUP_GUIDE.md                   # This file
├── LEARNING_GUIDE.md                # Educational guide
├── requirements.txt                 # Python dependencies
│
├── Data Generation:
│   ├── generate_database.py         # Basic synthetic data
│   ├── generate_database_research.py # Research-validated data
│   ├── fetch_wehoop_data.py         # Real WNBA game data
│   └── fetch_all_wnba_data.py       # Multi-team pipeline (new!)
│
├── Machine Learning:
│   ├── train_models.py              # Train injury predictor
│   └── add_schedule_features_example.py # Feature expansion guide
│
├── Dashboard:
│   ├── dashboard.py                 # Main Streamlit app (5 tabs)
│   └── .streamlit/                  # Streamlit config (auto-created)
│
├── Utilities:
│   ├── anonymize_players.py         # Privacy tool (ATH_001 format)
│   └── complete_setup.py            # Automated setup script
│
├── Data (auto-created):
│   ├── waims_demo.db                # SQLite database
│   ├── models/                      # Trained ML models
│   │   ├── injury_risk_model.pkl
│   │   └── readiness_scorer.pkl
│   ├── data/                        # Processed datasets
│   └── logs/                        # System logs
│
└── Documentation:
    ├── docs/
    │   └── DATA_ARCHITECTURE.md     # Design decisions
    └── examples/                    # Code examples
```

---

## 🎯 Usage Guide

### **1. Generate Database**

**Option A: Research-Validated Data (Recommended)**
```bash
python generate_database_research.py
```
- Creates injuries when risk factors align
- Uses thresholds from Gabbett, Milewski, Hulin
- 83 days of data for 12 players
- Output: `waims_demo.db`

**Option B: Basic Synthetic Data**
```bash
python generate_database.py
```
- Simpler version
- Random injury placement
- Good for quick testing

**Option C: Add Real WNBA Data**
```bash
python fetch_wehoop_data.py
```
- Requires wehoop: `pip install wehoop`
- Downloads 2025 WNBA season games
- Adds to database as separate table

---

### **2. Train ML Models**

```bash
python train_models.py
```

**What it does:**
1. Loads data from database
2. Engineers 26 features
3. Trains RandomForest classifier
4. Calculates readiness scores
5. Saves models to `models/`

**Expected output:**
```
============================================================
WAIMS - Training ML Models
============================================================

1. Loading data from database...
✓ Loaded 600 records

2. Engineering features...
✓ Created 26 features

3. Training Injury Risk Predictor...
   Training samples: 564
   Injury cases: 8
   Model Performance:
     Accuracy: 0.98
     AUC-ROC: 0.991

✓ Model saved: models/injury_risk_model.pkl

4. Creating Readiness Scorer...
✓ Readiness scores calculated

============================================================
TRAINING COMPLETE
============================================================
```

**Typical training time:** 10-30 seconds

---

### **3. Launch Dashboard**

```bash
streamlit run dashboard.py
```

**Opens in browser at:** `http://localhost:8501`

**5 Interactive Tabs:**

**📊 Today's Readiness**
- Current status for all players
- Color-coded: 🟢 Green / 🟡 Yellow / 🔴 Red
- Expandable player cards with details
- Automatic warning flags

**📈 Trends**
- Sleep patterns over time
- Soreness tracking
- Training load visualization
- Multi-player comparison

**💪 Force Plate**
- CMJ jump height trends
- RSI (Reactive Strength Index)
- Latest test results table
- Performance monitoring

**🚨 Injuries**
- Injury log with details
- Pre-injury wellness patterns
- Warning sign visualization
- Days missed tracking

**🤖 ML Predictions**
- Injury risk scores (0-100)
- Risk factor identification
- Model status and info
- Top-risk athletes highlighted

---

### **4. Anonymize for Public Sharing**

```bash
python anonymize_players.py
```

**Converts:**
- "Paige Bueckers" → "ATH_001"
- "Arike Ogunbowale" → "ATH_002"

**Safe for:**
- GitHub commits
- Portfolio demos
- LinkedIn posts
- Job applications

---

## ✨ Features

### **Database (SQLite)**
- 6 normalized tables
- 1,637 data points (sample)
- Relational schema with foreign keys
- Queryable with SQL or pandas

**Tables:**
- `players` - Athlete roster
- `wellness` - Daily subjective metrics
- `training_load` - Practice/game minutes
- `acwr` - Acute:Chronic Workload Ratio
- `force_plate` - Neuromuscular testing
- `injuries` - Injury events

---

### **Machine Learning**
- **Algorithm:** RandomForest Classifier
- **Purpose:** Predict injury risk in next 7 days
- **Features:** 15-30+ (extensible)
- **Performance:** 98% accuracy (on demo data)

**Key Features Used:**
- Sleep hours & quality
- Soreness, stress, mood
- Training load (ACWR)
- Force plate metrics (CMJ, RSI)
- Injury history
- Rolling averages (7-day)

---

### **Dashboard (Streamlit)**
- **Technology:** Python Streamlit framework
- **Charts:** Interactive Plotly visualizations
- **Filters:** Date range, player selection
- **Responsive:** Works on desktop/tablet
- **Real-time:** Updates with data changes

---

### **Research Foundation**
All thresholds validated from peer-reviewed research:

- **ACWR:** Gabbett (2016) - 2,000+ citations
- **Sleep:** Milewski (2014) - 500+ citations
- **Load Spikes:** Hulin (2016) - 400+ citations
- **Asymmetry:** Bishop (2018) - 300+ citations

---

## 📊 Data Sources

### **1. Simulated Data (Default)**
- Generated by Python scripts
- Research-validated patterns
- Safe for public demos
- No privacy concerns

**Use when:**
- Learning the system
- Portfolio demonstrations
- No real data available

---

### **2. Real WNBA Game Data (wehoop)**
- ESPN API integration
- 2002-present seasons
- All 12 teams available
- Player box scores, team stats

**Available data:**
- Minutes played
- Points, rebounds, assists
- Plus/minus
- Game dates, opponents
- Home/away

**What's NOT included:**
- GPS/accelerometer data (requires hardware)
- Wellness surveys (requires direct collection)
- Force plate data (requires equipment)
- Medical injury details (protected)

**Example:**
```python
from wehoop.wnba import load_wnba_player_box

# Get Dallas Wings 2025 season
games = load_wnba_player_box(seasons=2025)
dallas = games[games['team'] == 'DAL']
```

---

### **3. Public Injury Data**
- WNBA official injury reports
- ProSportsTransactions.com
- Publicly reported only
- No protected health information

**What you can use:**
- Player out/questionable status
- Injury type (ankle, knee, etc.)
- Dates missed
- Return dates

**What you CANNOT use:**
- Detailed medical records
- Surgery reports
- Internal team data
- Anything under HIPAA

---

## 🤖 ML Model Details

### **Training Process**

**1. Data Preparation**
```python
# Load from database
df = pd.read_sql_query("SELECT * FROM ...", conn)

# Create features
df['acwr_7day_avg'] = rolling_average(df['acwr'], 7)
df['sleep_hours_7day_avg'] = rolling_average(df['sleep'], 7)

# Create target (injury in next 7 days)
df['injured_within_7days'] = label_injuries(df)
```

**2. Feature Engineering**
- Rolling averages (7-day windows)
- Wellness composites
- Load trends
- Interaction terms

**3. Model Training**
```python
model = RandomForestClassifier(
    n_estimators=100,
    max_depth=10,
    random_state=42
)
model.fit(X_train, y_train)
```

**4. Validation**
- Train/test split (80/20)
- AUC-ROC score
- Feature importance analysis

---

### **How to Improve Model**

**1. More Data**
- Use all 12 WNBA teams (not just one)
- Multiple seasons (2023-2025)
- 180+ injuries vs 8

**2. More Features**
- Back-to-back games
- Travel distance
- Position-specific workload
- HRV, resting heart rate

**3. Better Labels**
- Real injury data (public reports)
- Validated injury dates
- Injury severity levels

**See:** `add_schedule_features_example.py` for code

---

## 🎨 Customization

### **Change Player Names**

Edit `generate_database_research.py` line ~175:
```python
'name': [f'ATH_{str(i+1).zfill(3)}' for i in range(12)],
```

---

### **Change Team Size**

Edit number of players:
```python
range(12)  # Change to 15 for 15 players
```

---

### **Change Date Range**

Edit start/end dates:
```python
start_date = datetime(2026, 1, 2)  # Change dates
end_date = datetime(2026, 2, 20)
```

---

### **Add New Features**

In `train_models.py`, line ~122:
```python
feature_cols = [
    'age', 'sleep_hours', 'acwr',
    'YOUR_NEW_FEATURE',  # Add here
]
```

---

### **Change Thresholds**

Edit research thresholds in `generate_database_research.py`:
```python
ACWR_HIGH_RISK = 1.5      # Gabbett 2016
SLEEP_LOW_RISK = 6.5      # Milewski 2014
SORENESS_HIGH = 7         # Hulin 2016
```

---

## 🔧 Troubleshooting

### **Common Issues**

**"Cannot open database"**
```bash
# Solution: Generate database first
python generate_database_research.py
```

**"Module not found: streamlit"**
```bash
# Solution: Install packages
pip install -r requirements.txt
```

**"Port 8501 already in use"**
```bash
# Solution: Kill existing Streamlit
# Windows: Ctrl+C in terminal
# Mac/Linux: Ctrl+C or kill process
```

**"No such column: asymmetry_percent"**
```bash
# Solution: Download latest train_models.py
# Or regenerate database
python generate_database_research.py
```

**Dashboard shows "Player A" instead of "ATH_001"**
```bash
# Solution: Run anonymizer
python anonymize_players.py
```

---

## 🔒 Privacy & Ethics

### **What's Safe to Share Publicly**

✅ **Anonymized data** (ATH_001, ATH_002)
✅ **Simulated injury scenarios**
✅ **Public game statistics** (points, minutes)
✅ **Model code and architecture**
✅ **Aggregate statistics**

### **What to Keep Private**

❌ **Real athlete names with health data**
❌ **Medical records or diagnoses**
❌ **Internal team protocols**
❌ **Anything under NDA**
❌ **Protected health information (HIPAA)**

### **Best Practices**

1. **Default to anonymization** for demos
2. **Store real data locally** (not in Git)
3. **Use generic identifiers** for public repos
4. **Cite data sources** appropriately
5. **Respect athlete privacy** always

### **For Production Use**

- Keep sensitive data on internal servers
- Implement access controls (SSO/VPN)
- Use role-based permissions
- Log all data access
- Follow team's data governance policies

**See:** `docs/DATA_ARCHITECTURE.md` for detailed privacy design

---

## ❓ FAQ

**Q: Is this real WNBA data?**
A: The database can use real game statistics from wehoop (ESPN API), but injuries are simulated for demo purposes. Real injury data is protected health information.

**Q: Can I use this for my team?**
A: Yes! The system is designed to integrate real data sources. Contact your team's data management staff for data access.

**Q: How accurate is the ML model?**
A: On demo data: 98%. On real data: depends on data quality and quantity. Professional models typically achieve 70-85% accuracy with sufficient training data.

**Q: What data do I need to collect?**
A: Minimum: daily wellness surveys (sleep, soreness). Ideal: + GPS/load data + force plate testing + game statistics.

**Q: Can I add more features?**
A: Yes! The model is extensible. See `add_schedule_features_example.py` for how to add back-to-back games, travel, etc.

**Q: Why RandomForest instead of deep learning?**
A: RandomForest works better with small datasets (<10,000 samples), is more interpretable, and is industry standard for sports injury prediction.

**Q: How often should I retrain?**
A: Weekly during season, monthly in off-season, or whenever you add significant new data.

**Q: Can I deploy this to production?**
A: The code is production-ready but needs proper security, access controls, and integration with your team's data systems. Recommend consulting with your IT team.

---

## 📚 Additional Resources

**Learning:**
- `LEARNING_GUIDE.md` - Comprehensive educational guide
- `docs/DATA_ARCHITECTURE.md` - System design decisions

**Research Papers:**
- Gabbett TJ (2016). Training-injury prevention paradox
- Milewski MD et al (2014). Sleep and sports injuries
- Hulin BT et al (2016). Spikes in acute workload
- Bishop C et al (2018). Bilateral asymmetry

**Tools:**
- wehoop: https://github.com/sportsdataverse/wehoop
- Streamlit: https://docs.streamlit.io
- scikit-learn: https://scikit-learn.org

**Community:**
- Issues: GitHub Issues (if applicable)
- Questions: Contact project author

---

## 🎓 Credits

**Built by:** Chris Cothern  
**Purpose:** Portfolio demonstration & professional athlete monitoring  
**License:** MIT  
**Research Foundation:** Gabbett, Milewski, Hulin, Bishop et al.

---

## ✅ Next Steps

1. ✅ **Complete setup** (this guide)
2. 📖 **Read LEARNING_GUIDE.md** (understand what you built)
3. 🚀 **Customize for your use case**
4. 💼 **Share in portfolio/interviews**
5. 🔬 **Integrate real data** (if applicable)

---

**Questions? Issues? Check the FAQ or review LEARNING_GUIDE.md**

**Ready to deploy? Consult with your team's IT/data security team.**

---

*Last updated: February 2026*
