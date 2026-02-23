# WAIMS Python - API Reference

Complete reference for all modules, functions, and classes.

---

## 📦 Module Overview

```
waims-python/
├── Data Generation
│   ├── generate_database.py
│   ├── generate_database_research.py
│   └── fetch_wehoop_data.py
├── Machine Learning
│   ├── train_models.py
│   └── Models (output)
├── Dashboard
│   └── dashboard.py
└── Utilities
    └── anonymize_players.py
```

---

## 🗄️ Database Schema

### **players**
```sql
CREATE TABLE players (
    player_id TEXT PRIMARY KEY,      -- P001, P002, etc.
    name TEXT,                        -- ATH_001, ATH_002, etc.
    position TEXT,                    -- G, F, C
    age INTEGER,                      -- 21-35
    injury_history_count INTEGER,    -- Number of previous injuries
    minutes_per_game REAL            -- Average minutes
)
```

### **wellness**
```sql
CREATE TABLE wellness (
    wellness_id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id TEXT,
    date DATE,
    sleep_hours REAL,                -- 5.5-9.5
    sleep_quality INTEGER,           -- 0-10
    soreness INTEGER,                -- 0-10
    stress INTEGER,                  -- 0-10
    mood INTEGER,                    -- 0-10
    FOREIGN KEY (player_id) REFERENCES players(player_id)
)
```

### **training_load**
```sql
CREATE TABLE training_load (
    load_id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id TEXT,
    date DATE,
    practice_minutes REAL,
    practice_rpe INTEGER,            -- 0-10 (Rating of Perceived Exertion)
    game_minutes REAL,
    total_daily_load REAL,           -- minutes × RPE
    FOREIGN KEY (player_id) REFERENCES players(player_id)
)
```

### **acwr**
```sql
CREATE TABLE acwr (
    acwr_id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id TEXT,
    date DATE,
    acwr REAL,                       -- Acute:Chronic Workload Ratio
    acute_load REAL,                 -- Last 7 days
    chronic_load REAL,               -- Last 21 days / 3
    FOREIGN KEY (player_id) REFERENCES players(player_id)
)
```

### **force_plate**
```sql
CREATE TABLE force_plate (
    test_id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id TEXT,
    date DATE,
    cmj_height_cm REAL,              -- Counter Movement Jump
    peak_power_w REAL,               -- Peak power output
    rsi_modified REAL,               -- Reactive Strength Index
    FOREIGN KEY (player_id) REFERENCES players(player_id)
)
```

### **injuries**
```sql
CREATE TABLE injuries (
    injury_id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id TEXT,
    injury_date DATE,
    injury_type TEXT,                -- Knee, ankle, etc.
    days_missed INTEGER,
    FOREIGN KEY (player_id) REFERENCES players(player_id)
)
```

---

## 🔧 Functions Reference

### **generate_database_research.py**

#### `create_database()`
Creates database with research-validated injury patterns.

**Parameters:** None

**Returns:** None (creates `waims_demo.db` file)

**Example:**
```python
python generate_database_research.py
```

**What it does:**
1. Creates SQLite database
2. Generates 12 players
3. Creates 50 days of wellness data
4. Calculates ACWR
5. Generates injuries when risk factors align

**Research thresholds:**
- ACWR > 1.5 = high risk (Gabbett 2016)
- Sleep < 6.5 hrs = high risk (Milewski 2014)
- Soreness > 7 = high risk (Hulin 2016)

---

### **train_models.py**

#### `load_data()`
```python
df = pd.read_sql_query('''SELECT ... FROM players ...''', conn)
```

**Returns:** pandas DataFrame with joined data

**Columns:** player_id, date, sleep_hours, soreness, acwr, cmj_height_cm, etc.

---

#### `engineer_features(df)`
```python
# Creates rolling averages
df['sleep_hours_7day_avg'] = df.groupby('player_id')['sleep_hours'].transform(
    lambda x: x.rolling(7, min_periods=1).mean()
)
```

**Parameters:**
- `df` (DataFrame): Raw data

**Returns:** DataFrame with engineered features

**Features created:**
- Rolling 7-day averages (sleep, soreness, load)
- Rolling 7-day std dev
- Wellness composite score
- Injury labels (injured within 7 days)

---

#### `train_injury_model(X, y)`
```python
model = RandomForestClassifier(
    n_estimators=100,
    max_depth=10,
    random_state=42
)
model.fit(X, y)
```

**Parameters:**
- `X` (DataFrame): Features
- `y` (Series): Target (injured_within_7days)

**Returns:** Trained RandomForest model

**Hyperparameters:**
- n_estimators: 100 trees
- max_depth: 10 levels
- random_state: 42 (reproducible)

**Saves to:** `models/injury_risk_model.pkl`

---

#### `calculate_readiness_score(row)`
```python
score = (
    (row['sleep_hours'] / 8 * 30) +
    ((10 - row['soreness']) / 10 * 25) +
    ((10 - row['stress']) / 10 * 25) +
    (row['mood'] / 10 * 20)
)
```

**Parameters:**
- `row` (Series): Player's daily data

**Returns:** Float (0-100)

**Components:**
- Sleep: 30 points (target: 8 hrs)
- Soreness: 25 points (lower is better)
- Stress: 25 points (lower is better)
- Mood: 20 points (higher is better)

**Interpretation:**
- 80-100: Ready to train (GREEN)
- 60-79: Monitor closely (YELLOW)
- 0-59: Needs attention (RED)

---

### **dashboard.py**

#### `load_data()`
```python
@st.cache_data
def load_data():
    conn = sqlite3.connect('waims_demo.db')
    players = pd.read_sql_query("SELECT * FROM players", conn)
    wellness = pd.read_sql_query("SELECT * FROM wellness", conn)
    # ... load all tables
    return players, wellness, training_load, force_plate, injuries
```

**Decorator:** `@st.cache_data` (caches results for performance)

**Returns:** Tuple of DataFrames

**Why cached:** Database queries are expensive, cache speeds up dashboard

---

#### `calculate_readiness_score(row)`
Same as train_models.py version

---

#### `get_status_color(score)`
```python
def get_status_color(score):
    if score >= 80:
        return "🟢", "green"
    elif score >= 60:
        return "🟡", "orange"
    else:
        return "🔴", "red"
```

**Parameters:**
- `score` (float): Readiness score 0-100

**Returns:** Tuple of (emoji, color_name)

---

### **anonymize_players.py**

#### `anonymize_database()`
```python
players['name'] = [f'ATH_{str(i+1).zfill(3)}' for i in range(len(players))]
players.to_sql('players', conn, if_exists='replace', index=False)
```

**What it does:**
- Reads players table
- Replaces names with ATH_001, ATH_002, etc.
- Updates database

**Usage:**
```bash
python anonymize_players.py
```

---

### **fetch_wehoop_data.py**

#### `fetch_wnba_games(seasons)`
```python
from wehoop.wnba import load_wnba_player_box

games = load_wnba_player_box(seasons=2025)
```

**Parameters:**
- `seasons` (list or int): Year(s) to fetch

**Returns:** DataFrame with game statistics

**Columns:**
- athlete_display_name
- team_short_display_name
- game_date
- minutes, points, rebounds, assists
- plus_minus

**Rate limits:** ESPN API has rate limits, don't spam

---

## 🤖 Machine Learning Model Specifications

### **RandomForest Configuration**

```python
RandomForestClassifier(
    n_estimators=100,          # Number of trees
    max_depth=10,              # Maximum tree depth
    min_samples_split=5,       # Min samples to split node
    min_samples_leaf=2,        # Min samples in leaf
    max_features='sqrt',       # Features per split
    random_state=42,           # Reproducibility
    n_jobs=-1,                 # Use all CPU cores
    class_weight='balanced'    # Handle imbalanced classes
)
```

### **Feature Importance**

After training, access via:
```python
import pickle
model = pickle.load(open('models/injury_risk_model.pkl', 'rb'))
feature_importance = model.feature_importances_

# Example output:
# acwr: 0.276
# practice_minutes_7day_avg: 0.226
# cmj_height_cm: 0.119
# injury_history_count: 0.094
```

### **Making Predictions**

```python
# Load model
model = pickle.load(open('models/injury_risk_model.pkl', 'rb'))

# Prepare features
features = pd.DataFrame({
    'age': [25],
    'sleep_hours': [6.2],
    'soreness': [7],
    'acwr': [1.6],
    # ... other features
})

# Predict probability
risk_prob = model.predict_proba(features)[0][1]  # Probability of injury
risk_percent = risk_prob * 100  # Convert to percentage

print(f"Injury risk: {risk_percent:.1f}%")
```

---

## 📊 Streamlit Components Used

### **Layout Elements**

```python
st.title("Dashboard Title")          # Main heading
st.header("Section Header")           # Section heading
st.subheader("Subsection")           # Smaller heading
st.markdown("**Bold text**")         # Formatted text
```

### **Data Display**

```python
st.dataframe(df)                     # Interactive table
st.metric("Label", "Value", "Delta") # Big number display
st.table(df)                         # Static table
```

### **Charts**

```python
import plotly.express as px

fig = px.line(df, x='date', y='value')
st.plotly_chart(fig, use_container_width=True)
```

### **Inputs**

```python
selected = st.selectbox("Choose", options)
date_range = st.date_input("Date Range", value=(start, end))
players = st.multiselect("Players", options)
```

### **Tabs**

```python
tab1, tab2, tab3 = st.tabs(["Tab 1", "Tab 2", "Tab 3"])

with tab1:
    st.write("Content for tab 1")

with tab2:
    st.write("Content for tab 2")
```

### **Containers**

```python
with st.expander("Click to expand"):
    st.write("Hidden content")

col1, col2 = st.columns(2)
with col1:
    st.metric("Metric 1", "Value")
with col2:
    st.metric("Metric 2", "Value")
```

---

## 🗃️ Data Types

### **player_id Format**
- Type: `TEXT`
- Pattern: `P###` (P001, P002, ..., P999)
- Purpose: Internal database key

### **name Format**
- Type: `TEXT`
- Pattern: `ATH_###` (ATH_001, ATH_002, ...)
- Purpose: Public display identifier

### **date Format**
- Type: `DATE`
- Pattern: `YYYY-MM-DD`
- Example: `2026-02-20`
- Storage: SQLite stores as TEXT, pandas converts to datetime

### **ACWR Calculation**
```python
acute_load = last_7_days.sum()
chronic_load = last_21_days.sum() / 3
acwr = acute_load / chronic_load if chronic_load > 0 else 1.0
```

**Typical values:**
- 0.8-1.3: Optimal (Gabbett 2016)
- >1.5: High injury risk
- <0.8: Detraining risk

---

## 💾 File I/O

### **Reading Database**
```python
import sqlite3
import pandas as pd

conn = sqlite3.connect('waims_demo.db')
df = pd.read_sql_query("SELECT * FROM wellness", conn)
conn.close()
```

### **Writing to Database**
```python
import sqlite3
import pandas as pd

conn = sqlite3.connect('waims_demo.db')
df.to_sql('table_name', conn, if_exists='replace', index=False)
conn.commit()
conn.close()
```

### **Saving Models**
```python
import pickle

# Save
with open('models/model.pkl', 'wb') as f:
    pickle.dump(model, f)

# Load
with open('models/model.pkl', 'rb') as f:
    model = pickle.load(f)
```

---

## 🔍 SQL Query Examples

### **Get Today's Wellness**
```sql
SELECT p.name, w.sleep_hours, w.soreness
FROM wellness w
JOIN players p ON w.player_id = p.player_id
WHERE w.date = (SELECT MAX(date) FROM wellness);
```

### **Players with Poor Sleep**
```sql
SELECT p.name, w.sleep_hours, w.date
FROM wellness w
JOIN players p ON w.player_id = p.player_id
WHERE w.sleep_hours < 6.5
ORDER BY w.date DESC;
```

### **High ACWR Alerts**
```sql
SELECT p.name, a.acwr, a.date
FROM acwr a
JOIN players p ON a.player_id = p.player_id
WHERE a.acwr > 1.5
ORDER BY a.acwr DESC;
```

### **Injury History**
```sql
SELECT p.name, COUNT(*) as injury_count
FROM injuries i
JOIN players p ON i.player_id = p.player_id
GROUP BY p.name
ORDER BY injury_count DESC;
```

---

## 🎯 Performance Optimization

### **Database Indexing**
```sql
CREATE INDEX idx_wellness_date ON wellness(date);
CREATE INDEX idx_wellness_player ON wellness(player_id);
CREATE INDEX idx_training_date ON training_load(date);
```

### **Streamlit Caching**
```python
@st.cache_data  # Cache data loading
def load_data():
    # Expensive operation
    return data

@st.cache_resource  # Cache ML models
def load_model():
    return pickle.load(open('model.pkl', 'rb'))
```

### **Pandas Optimization**
```python
# Use appropriate dtypes
df['player_id'] = df['player_id'].astype('category')
df['date'] = pd.to_datetime(df['date'])

# Vectorized operations (fast)
df['acwr_risk'] = (df['acwr'] > 1.5).astype(int)

# Avoid loops (slow)
# for i, row in df.iterrows():  # DON'T DO THIS
```

---

## 🐛 Common Errors

### **"no such table: players"**
**Cause:** Database not created

**Solution:**
```bash
python generate_database_research.py
```

### **"no such column: asymmetry_percent"**
**Cause:** Schema mismatch between database and code

**Solution:** Regenerate database or update train_models.py

### **"Port 8501 already in use"**
**Cause:** Streamlit already running

**Solution:** Kill process or use different port:
```bash
streamlit run dashboard.py --server.port 8502
```

### **"pickle protocol error"**
**Cause:** Python version mismatch

**Solution:** Retrain model with same Python version

---

## 📚 Dependencies

### **Core Requirements**
```
pandas>=2.0.0       # Data manipulation
numpy>=1.24.0       # Numerical operations
scikit-learn>=1.3.0 # Machine learning
streamlit>=1.28.0   # Dashboard framework
plotly>=5.17.0      # Interactive charts
```

### **Optional**
```
wehoop>=2.0.0       # WNBA data (ESPN API)
```

### **Development**
```
pytest              # Testing
black               # Code formatting
flake8              # Linting
```

---

## 🔐 Security Considerations

### **Database**
- SQLite has no built-in user authentication
- For production: use PostgreSQL with access controls
- Never commit databases with real data to Git

### **API Keys**
- wehoop doesn't require API key currently
- If using paid APIs, store keys in environment variables:
```python
import os
api_key = os.environ.get('API_KEY')
```

### **Streamlit Cloud**
- Don't deploy sensitive data to public Streamlit Cloud
- Use Streamlit secrets for credentials
- Force anonymization in cloud environment

---

## 📖 Related Documentation

- `SETUP_GUIDE.md` - Installation and usage
- `LEARNING_GUIDE.md` - Educational content
- `docs/DATA_ARCHITECTURE.md` - Design decisions
- `README.md` - Project overview

---

*Last updated: February 2026*
