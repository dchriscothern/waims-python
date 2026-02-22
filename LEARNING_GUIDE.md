# WAIMS Complete Learning Guide

Everything you built and how it works - study this to understand your portfolio projects.

---

## 🎯 Overview: What You Built

You created **TWO complete athlete monitoring systems**:

1. **Python System** - Interactive web dashboard
2. **R System** - Production automation pipeline

**Both are professional, working, and interview-ready.**

---

# 📊 PART 1: Python System Deep Dive

## File-by-File Breakdown

### **1. generate_database.py** (What it does)

**Purpose:** Creates a realistic SQLite database with 50 days of monitoring data

**How it works:**
```python
# Step 1: Create 12 players
players = ["Player A", "Player B", ...]  # 12 athletes

# Step 2: Create 50 days of dates
dates = [Day 1, Day 2, ... Day 50]

# Step 3: For each player, each day:
for player in players:
    for date in dates:
        # Generate wellness (sleep, soreness, stress, mood)
        sleep = random between 5.5 and 9.5 hours
        soreness = random between 0 and 10
        
        # Generate training load
        minutes = random practice time
        load = calculated from minutes + intensity
        
        # Every Monday: force plate test
        jump_height = baseline ± random variation
```

**Output:** `waims_demo.db` with 6 tables, 1,637 records

**Key Insight:** Uses numpy.random to create realistic patterns - not just random noise, but correlated data (e.g., high load → next day soreness)

---

### **2. dashboard.py** (What it does)

**Purpose:** Interactive web app to visualize the database

**Technology:** Streamlit (Python web framework)

**How it works:**

```python
# Load data from database
conn = sqlite3.connect('waims_demo.db')
data = pd.read_sql_query("SELECT * FROM wellness", conn)

# Create tabs
tab1, tab2, tab3, tab4 = st.tabs([...])

# Show visualizations
st.plotly_chart(figure)  # Interactive charts
st.metric("Sleep", "7.2 hrs")  # Big number displays
st.dataframe(data)  # Tables
```

**4 Tabs:**
1. **Today's Readiness** - Current status, red/yellow/green
2. **Trends** - Line charts over time
3. **Force Plate** - Jump height tracking
4. **Injuries** - Injury log with pre-injury patterns

**Key Insight:** Streamlit makes complex dashboards easy - no HTML/CSS/JS needed

---

### **3. train_models.py** (What it does)

**Purpose:** Train machine learning model to predict injury risk

**Algorithm:** RandomForest Classifier

**How it works:**

```python
# Step 1: Load and prepare data
features = [sleep, soreness, load, ACWR, jump_height, ...]
target = injured_within_7days (yes/no)

# Step 2: Train model
model = RandomForestClassifier()
model.fit(features, target)

# Step 3: Test accuracy
predictions = model.predict(test_data)
accuracy = how many correct / total

# Step 4: Save model
pickle.dump(model, 'injury_risk_model.pkl')
```

**Output:** Trained model that can predict: "This athlete has 73% risk of injury in next 7 days"

**Key Insight:** Uses past patterns (5 injury scenarios) to learn what warning signs look like

---

### **4. fetch_wehoop_data.py** (What it does)

**Purpose:** Download real 2025 WNBA game statistics

**Data Source:** ESPN API via wehoop package

**How it works:**

```python
# Fetch from ESPN
games = load_wnba_player_box(seasons=2025)

# Filter to recent (last 50 days)
recent = games[last_50_days]

# Save to database
games.to_sql('wehoop_games', database)
```

**Output:** Real game stats (minutes, points, rebounds) added to your database

**Key Insight:** Combines real game data with simulated wellness data - more credible than 100% fake

---

## 🗄️ Database Schema (SQLite)

### **players** table
```
player_id | name      | position | age | injury_history
P001      | Player A  | G        | 23  | 3
P002      | Player B  | G        | 28  | 1
```
*12 rows - one per athlete*

### **wellness** table
```
player_id | date       | sleep_hours | soreness | stress | mood
P001      | 2026-01-02 | 7.2         | 4        | 5      | 7
P001      | 2026-01-03 | 6.8         | 5        | 6      | 6
```
*600 rows - 12 players × 50 days*

### **training_load** table
```
player_id | date       | practice_minutes | practice_rpe | game_minutes
P001      | 2026-01-02 | 65.2            | 7            | 0
```
*600 rows*

### **force_plate** table
```
player_id | date       | cmj_height_cm | rsi_modified
P001      | 2026-01-06 | 32.5          | 0.38
```
*84 rows - 12 players × 7 weeks (Monday tests)*

### **acwr** table
```
player_id | date       | acwr | acute_load | chronic_load
P001      | 2026-01-22 | 1.2  | 350       | 292
```
*348 rows - calculated from training load*

### **injuries** table
```
player_id | injury_date | injury_type       | days_missed
P001      | 2026-01-14  | Knee inflammation | 7
```
*5 rows - simulated injury scenarios*

**Joins:**
```sql
-- Get player name with wellness data
SELECT p.name, w.sleep_hours
FROM wellness w
JOIN players p ON w.player_id = p.player_id
WHERE w.date = '2026-02-20'
```

---

## 🤖 Machine Learning Explained

### **What is RandomForest?**

Think of it like asking 100 experts to vote:

```
Tree 1: "High soreness + low sleep = 80% risk"
Tree 2: "High load + previous injury = 75% risk"
Tree 3: "Normal - 20% risk"
...
Tree 100: "High risk - 85%"

Final prediction: Average of all votes = 65% risk
```

### **How training works:**

```python
# Historical data (we have 5 injuries with warning signs)
Training examples:
- Player A, 7 days before injury: sleep=6.0, soreness=8, load=high → Outcome: INJURED
- Player A, 14 days before injury: sleep=7.5, soreness=4, load=normal → Outcome: NOT INJURED
- Player C, 5 days before injury: sleep=5.8, soreness=9, load=high → Outcome: INJURED
...

Model learns: "When I see sleep<6.5 AND soreness>7 → probably injury coming"
```

### **Feature Importance:**

After training, model tells us which factors matter most:
```
1. Sleep (30%) - Most important predictor
2. Soreness (25%)
3. ACWR (20%)
4. Force plate jump height (15%)
5. Stress (10%)
```

---

## 📈 How Streamlit Works

### **Basic Structure:**

```python
import streamlit as st

# This creates a web page automatically!
st.title("My Dashboard")  # Big heading
st.metric("Sleep", "7.2 hrs")  # Number display
st.line_chart(data)  # Chart

# Interactivity
selected = st.selectbox("Choose player", ["Player A", "Player B"])
if selected == "Player A":
    st.write("You chose Player A!")
```

**Run with:** `streamlit run dashboard.py`

**Magic:** Streamlit turns Python code into interactive web pages automatically!

---

# 📊 PART 2: R System Deep Dive

## File-by-File Breakdown

### **1. config.R**

**Purpose:** Central configuration with all thresholds

**Key Contents:**
```r
# Research-validated thresholds
acwr_optimal <- c(0.8, 1.3)  # Gabbett 2016
sleep_critical <- 6.0  # Milewski 2014
asymmetry_red <- 15.0  # Bishop 2018

# Folder structure
dirs <- list(
  raw_gps = "raw/gps",
  raw_wellness = "raw/wellness",
  ...
)
```

**Why important:** One place to change all thresholds, with research citations

---

### **2. generate_sample_data.R**

**Purpose:** Create 83 days of monitoring data (off-season context)

**How it differs from Python:**
- Uses R's tidyverse (dplyr, tidyr)
- Creates CSV files instead of database
- More realistic off-season patterns (lower load, better sleep)
- Includes progressive fatigue over time

**Output:** CSV files in raw/ folders

---

### **3. fetch_game_data.R**

**Purpose:** Download real 2025 WNBA game data via wehoop

**How it works:**
```r
library(wehoop)

# Fetch Dallas Wings 2025 games
games <- load_wnba_player_box(seasons = 2025) %>%
  filter(team_short_display_name == "DAL")

# Calculate game load
games <- games %>%
  mutate(
    game_load = minutes * (1 + total_rebounds/10)
  )

# Save as CSV
write_csv(games, "raw/game_tracking/wehoop_games.csv")
```

**Key Insight:** This is REAL data from ESPN, not simulated!

---

### **4. demo_script.R**

**Purpose:** 5-minute interview demonstration

**What it shows:**
1. Load system and configuration
2. Generate sample data
3. Quick analyses (sleep trends, load patterns, force plate)
4. Summary statistics

**Run with:** `source("scripts/demo_script.R")`

---

### **5. simple_report.R**

**Purpose:** Generate HTML daily readiness report

**Output:** Beautiful HTML file with:
- Purple gradient header
- Summary cards (green/yellow/red counts)
- Player table with status
- Opens automatically in browser

**Technology:** Pure R - builds HTML as a string with glue()

---

## 🔄 R vs Python Comparison

| Aspect | Python System | R System |
|--------|--------------|----------|
| **Data Storage** | SQLite database | CSV files |
| **Visualization** | Streamlit web app | HTML reports |
| **Real Data** | wehoop (optional) | wehoop (core feature) |
| **ML** | RandomForest | Not implemented |
| **Best For** | Quick demos, portfolios | Production deployment |
| **Automation** | Manual run | Task Scheduler ready |
| **Documentation** | Moderate | Extensive (500+ lines) |

---

## 🎓 Key Concepts to Understand

### **1. ACWR (Acute:Chronic Workload Ratio)**

**Formula:** `ACWR = Last 7 days load / Last 21 days load (÷3)`

**Example:**
```
Last 7 days: 350 minutes
Last 21 days: 875 minutes ÷ 3 = 292 minutes

ACWR = 350 / 292 = 1.20
```

**Interpretation:**
- ACWR 0.8-1.3: **Optimal** (sweet spot)
- ACWR > 1.5: **High risk** (spike in load)
- ACWR < 0.8: **Detraining** (not training enough)

**Research:** Gabbett (2016) - 2000+ citations

---

### **2. Readiness Score**

**Formula:** Composite of multiple factors

```
Readiness = Sleep (30%) + 
            Low Soreness (25%) + 
            Low Stress (25%) + 
            Mood (20%)

Example:
- Sleep: 7.2 / 8.0 * 30 = 27 points
- Soreness: (10-4) / 10 * 25 = 15 points
- Stress: (10-5) / 10 * 25 = 12.5 points
- Mood: 7 / 10 * 20 = 14 points
Total = 68.5 / 100 (Yellow status)
```

---

### **3. Force Plate Testing**

**CMJ (Counter Movement Jump):**
- Stand on force plates
- Jump as high as possible
- Measures: height, power, asymmetry

**RSI (Reactive Strength Index):**
- Jump height / contact time
- Measures: explosiveness, efficiency
- Target: > 0.35

**Why it matters:** Drop in jump height = neuromuscular fatigue

---

### **4. wehoop Package**

**What it is:** R/Python package to access ESPN's WNBA API

**What it provides:**
- Play-by-play data
- Player box scores
- Team statistics
- Historical games (2002-present)

**What it does NOT provide:**
- GPS distance data (requires hardware)
- Accelerations/decelerations
- Player load (mechanical)

---

## 🗂️ Data Architecture Decision

### **Why athlete_id everywhere?**

**Roster has multiple IDs:**
```
athlete_id: ATH_001 (primary - the person)
gps_id: GPS_001 (device that may change)
force_plate_id: FP_001 (device)
wearable_id: WR_001 (device)
```

**Exported data uses athlete_id:**
```csv
athlete_id,date,sleep_hours
ATH_001,2026-02-20,7.2
```

**Why?**
1. Devices can break/change → athlete_id stays same
2. Simpler joins (one key for everything)
3. AMS systems expect athlete IDs, not device IDs
4. Industry standard practice

**See:** `docs/DATA_ARCHITECTURE.md` for full explanation

---

## 🎯 What to Say in Interviews

### **"Walk me through your Python project"**

*"I built an interactive dashboard using Streamlit that visualizes athlete monitoring data from a SQLite database. The database has 1,600+ integrated data points across wellness, training load, force plate testing, and injuries. The dashboard has 4 tabs - today's readiness shows color-coded status for each player, trends shows sleep and soreness patterns over time, force plate tracks neuromuscular fatigue, and injuries shows warning signs that appeared 5-7 days before each injury event. I also trained a RandomForest model to predict injury risk, though it's not integrated into the dashboard yet. The system demonstrates SQL skills, data visualization with Plotly, and understanding of sports science metrics."*

### **"Walk me through your R project"**

*"I built a production-ready monitoring pipeline in R that automates daily workflows. It generates realistic monitoring data, integrates real 2025 WNBA game statistics via the wehoop API, and produces HTML reports. All thresholds are research-validated from 40+ peer-reviewed studies - ACWR from Gabbett 2016, sleep from Milewski 2014, asymmetry from Bishop 2018. The system uses athlete_id as the primary key across all data sources to simplify AMS integration and handle device changes. It's designed to run via Task Scheduler each morning and output daily readiness reports. The code has 500+ lines of inline documentation and follows modern R style with snake_case throughout."*

### **"Why did you build two systems?"**

*"They demonstrate different skillsets. Python shows dashboard development, data visualization, and ML capabilities - great for quick prototyping and stakeholder communication. R shows production deployment thinking, research translation, and real data integration - what you'd actually deploy in an organization. Together they show I can both prototype solutions quickly and think through operational deployment challenges."*

---

## 📚 Study Plan

### **Day 1: Understand the Data**
- [ ] Open waims_demo.db in DB Browser for SQLite
- [ ] Run sample SQL queries
- [ ] Look at all 6 tables
- [ ] Understand the relationships

### **Day 2: Understand the Dashboard**
- [ ] Run `streamlit run dashboard.py`
- [ ] Click through all 4 tabs
- [ ] Look at dashboard.py code
- [ ] Understand how Streamlit works

### **Day 3: Understand ML**
- [ ] Read train_models.py
- [ ] Understand feature engineering
- [ ] Look up RandomForest algorithm
- [ ] Understand injury prediction

### **Day 4: Understand R System**
- [ ] Run demo_script.R
- [ ] Generate sample data
- [ ] Look at HTML report
- [ ] Understand wehoop integration

### **Day 5: Understand Research**
- [ ] Read DATA_ARCHITECTURE.md
- [ ] Look up ACWR paper (Gabbett 2016)
- [ ] Understand readiness scoring
- [ ] Review force plate metrics

---

## 🎓 Resources to Learn More

**ACWR:**
- Gabbett TJ (2016). The training-injury prevention paradox
- Google Scholar: Search "ACWR injury prevention"

**Streamlit:**
- docs.streamlit.io
- 30-day Streamlit challenge

**RandomForest:**
- scikit-learn.org/stable/modules/ensemble.html
- YouTube: "Random Forest Explained"

**wehoop:**
- github.com/sportsdataverse/wehoop
- Documentation: wehoop.sportsdataverse.org

**R tidyverse:**
- r4ds.hadley.nz (free online book)
- tidyverse.org

---

## ✅ Final Checklist

**You should be able to explain:**
- [ ] How the database is structured (6 tables, relationships)
- [ ] What athlete_id is and why we use it
- [ ] What ACWR means and optimal ranges
- [ ] How readiness score is calculated
- [ ] What force plate testing measures
- [ ] How the ML model predicts injuries
- [ ] Why you built both Python and R systems
- [ ] How wehoop provides real game data
- [ ] What the dashboard shows in each tab
- [ ] How the R system automates daily workflows

---

**Take your time studying this. You built something impressive - make sure you can explain it!** 🎓
