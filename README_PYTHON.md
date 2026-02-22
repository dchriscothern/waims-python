# WAIMS Python - Interactive Athlete Monitoring Dashboard

Interactive web dashboard for athlete monitoring data visualization. Built with Python, Streamlit, and SQLite.

## 🎯 Quick Start

### **Install Dependencies**
```bash
pip install -r requirements.txt
```

### **Run Dashboard**
```bash
streamlit run dashboard.py
```

Dashboard opens at: `http://localhost:8501`

---

## 📊 Features

### **4 Interactive Tabs:**

**1. Today's Readiness** 📊
- Real-time readiness scores (0-100)
- Traffic light status (🟢🟡🔴)
- Sleep, soreness, stress, mood metrics
- Automatic flag warnings

**2. Trends** 📈
- Sleep patterns over time
- Soreness trends
- Training load visualization
- Multi-player comparison

**3. Force Plate** 💪
- CMJ jump height tracking
- RSI (Reactive Strength Index) trends
- Latest test results table
- Performance monitoring

**4. Injuries** 🚨
- Injury log with details
- Pre-injury wellness patterns
- Days missed tracking
- Warning sign identification

---

## 🗄️ Database

**SQLite database:** `waims_demo.db`

**6 tables, 1,637 data points:**
- `players` - 12 athletes
- `wellness` - 600 daily records
- `training_load` - 600 sessions
- `acwr` - 348 calculations
- `force_plate` - 84 tests
- `injuries` - 5 events

---

## 🎓 What This Demonstrates

**Technical Skills:**
- Python programming
- Data visualization (Plotly)
- Web development (Streamlit)
- SQL/database management
- Interactive dashboards

**Domain Knowledge:**
- Sports science metrics
- Readiness assessment
- Injury risk monitoring
- Performance tracking

---

## 🔧 Technologies

- **Python 3.12+**
- **Streamlit** - Web framework
- **Plotly** - Interactive charts
- **pandas** - Data manipulation
- **SQLite** - Database
- **scikit-learn** - ML (optional)

---

## 📁 Files

```
waims-python/
├── dashboard.py           # Main Streamlit app
├── waims_demo.db          # SQLite database
├── generate_database.py   # Data generator
├── train_models.py        # ML training (optional)
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

---

## 🚀 Usage Examples

### **View Today's Status**
```bash
streamlit run dashboard.py
# Click "Today's Readiness" tab
```

### **Analyze Trends**
```bash
# Select players from sidebar
# Choose date range
# View sleep/soreness/load trends
```

### **Check Force Plate**
```bash
# Click "Force Plate" tab
# View jump height trends
# Monitor RSI changes
```

---

## 🎯 For Interviews

### **5-Minute Demo:**

1. **Run dashboard** (30 sec)
   ```bash
   streamlit run dashboard.py
   ```

2. **Show Today's Readiness** (1 min)
   - "Here's today's status - 7 green, 3 yellow, 2 red"
   - "Click player to see details"
   - "Red flags show automatically"

3. **Show Trends** (2 min)
   - "Select multiple players"
   - "Sleep patterns over 2 weeks"
   - "Soreness correlation with load"

4. **Show Injuries** (1 min)
   - "5 recorded injuries"
   - "Warning signs visible 5-7 days prior"
   - "Sleep drops, soreness spikes"

5. **Explain** (30 sec)
   - "1,637 integrated data points"
   - "Built with Python, Streamlit, SQLite"
   - "Production-ready web app"

---

## 📊 Sample Data

**Generated from:** `generate_database.py`

**Includes:**
- 50 days of monitoring
- 12 players (simulated roster)
- Realistic patterns
- 5 injury scenarios
- Off-season training context

**Regenerate fresh data:**
```bash
python generate_database.py
```

---

## 🔍 SQL Queries (For Reference)

```sql
-- Today's wellness
SELECT * FROM wellness 
WHERE date = (SELECT MAX(date) FROM wellness);

-- Players with poor sleep
SELECT p.name, w.sleep_hours 
FROM wellness w 
JOIN players p ON w.player_id = p.player_id
WHERE w.sleep_hours < 7;

-- Recent injuries
SELECT p.name, i.injury_type, i.days_missed
FROM injuries i
JOIN players p ON i.player_id = p.player_id
ORDER BY i.injury_date DESC;
```

---

## ✅ Troubleshooting

**Dashboard won't start:**
```bash
# Install dependencies
pip install -r requirements.txt

# Check database exists
ls waims_demo.db

# Regenerate if needed
python generate_database.py
```

**No data showing:**
- Check database file is present
- Verify tables exist: open waims_demo.db in DB Browser
- Regenerate database with generate_database.py

---

## 📄 License

MIT

---

## 👤 Author

Chris Cothern - Sport Scientist

*Portfolio demonstration project*

---

**Built for professional basketball athlete monitoring - February 2026**
