# How to Add Athlete Profile Tab to Your Dashboard

## Step 1: Copy the module file

Save `athlete_profile_tab.py` in your `waims-python` directory:
```
waims-python/
├── dashboard.py
├── athlete_profile_tab.py  ← NEW FILE
└── ...
```

## Step 2: Update your dashboard.py

### A. Add import at the top (around line 14):

```python
from athlete_profile_tab import athlete_profile_tab, create_radar_chart
```

### B. Update the tabs line (around line 290):

**FIND THIS:**
```python
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Today's Readiness", 
    "📈 Trends", 
    "💪 Force Plate", 
    "🚨 Injuries", 
    "🤖 ML Predictions",
    "🔍 Smart Query"
])
```

**REPLACE WITH:**
```python
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📊 Today's Readiness", 
    "📈 Trends", 
    "💪 Force Plate", 
    "🚨 Injuries", 
    "🤖 ML Predictions",
    "🔍 Smart Query",
    "👤 Athlete Profiles"  # NEW TAB
])
```

### C. Add Tab 7 at the end (after tab6 closes, before the footer):

```python
# ==============================================================================
# TAB 7: ATHLETE PROFILES
# ==============================================================================

with tab7:
    athlete_profile_tab(wellness, training_load, acwr, force_plate, players)
```

## Step 3: Test it locally

```bash
cd waims-python
streamlit run dashboard.py
```

Should see 7 tabs now, with "👤 Athlete Profiles" as the last tab.

## Step 4: Deploy to Streamlit Cloud

```bash
# Commit both files
git add dashboard.py athlete_profile_tab.py
git commit -m "Add athlete profile tab with radar charts"
git push

# Streamlit Cloud will auto-deploy
```

---

## What You Get

### Profile Features:
✅ Athlete photo placeholder (can add real photos later)
✅ Radar chart showing 5 performance dimensions
✅ Today's status with color-coded readiness
✅ Key metrics cards (sleep, soreness, mood, stress)
✅ Workload management (ACWR, training load)
✅ Neuromuscular data (CMJ, RSI if available)
✅ 7-day trend charts (sleep, soreness, mood, stress, ACWR)
✅ Automated alerts based on research thresholds
✅ Personalized recommendations
✅ Research references

### Radar Chart Dimensions:
1. **Sleep Quality** - Hours relative to 8hr target
2. **Physical Readiness** - Inverse of soreness
3. **Mental Wellness** - Mood score
4. **Load Balance** - ACWR optimization
5. **Neuromuscular** - CMJ/RSI performance

---

## Adding Real Photos Later

### Option 1: URL-based (easiest)

Update line in `athlete_profile_tab.py`:

```python
# Replace this:
st.image(
    "https://via.placeholder.com/200x250/2E86AB/FFFFFF?text=" + selected_athlete.replace("_", "+"),
    ...
)

# With this:
photo_urls = {
    "ATH_001": "https://yoursite.com/photos/ath001.jpg",
    "ATH_002": "https://yoursite.com/photos/ath002.jpg",
    # ... etc
}

photo_url = photo_urls.get(selected_athlete, "https://via.placeholder.com/200x250")
st.image(photo_url, ...)
```

### Option 2: Local files

```python
import os
from PIL import Image

photo_path = f"photos/{selected_athlete}.jpg"
if os.path.exists(photo_path):
    st.image(photo_path, ...)
else:
    st.image("photos/default.jpg", ...)
```

---

## Customization Ideas

### 1. Add more metrics to radar chart:

Edit `create_radar_chart()` function to include:
- Recovery score
- Training volume
- Competition readiness
- Nutrition compliance
- Hydration status

### 2. Add injury history timeline:

```python
injury_history = injuries[injuries['player_id'] == athlete_id]
if len(injury_history) > 0:
    st.markdown("### 🏥 Injury History")
    for _, inj in injury_history.iterrows():
        st.markdown(f"- **{inj['injury_type']}** on {inj['injury_date']} ({inj['days_missed']} days)")
```

### 3. Add comparison to team average:

```python
team_avg_sleep = wellness[wellness['date'] == latest_date]['sleep_hours'].mean()
athlete_vs_team = latest_wellness['sleep_hours'] - team_avg_sleep

st.metric("Sleep", 
         f"{latest_wellness['sleep_hours']:.1f} hrs",
         delta=f"{athlete_vs_team:+.1f} vs team avg")
```

---

## Interview Talking Points

*"I added individual athlete profile pages with radar charts to visualize multi-dimensional performance. Each athlete gets a personalized dashboard showing their status, trends, and automated alerts based on research thresholds. The radar chart makes it easy to see at a glance which areas need attention - if sleep quality is low but everything else is good, you know exactly what to focus on. This is similar to what NBA teams use for player monitoring."*

**Shows:**
✅ User-centered design (different views for different needs)
✅ Data visualization skills (radar charts)
✅ Personalization
✅ Professional UI/UX
✅ Real-world application
