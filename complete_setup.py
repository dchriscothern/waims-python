"""
WAIMS Python - Complete Setup Script
Runs all steps to get the system fully operational with ML and real data

Usage:
    python complete_setup.py
"""

import subprocess
import sys
import os

print("=" * 70)
print("WAIMS PYTHON - COMPLETE SETUP")
print("=" * 70)

# ==============================================================================
# Step 1: Install Required Packages
# ==============================================================================

print("\n📦 Step 1/4: Installing required packages...")

packages = [
    "pandas",
    "numpy",
    "scikit-learn",
    "streamlit",
    "plotly",
    "wehoop"
]

for package in packages:
    print(f"  Installing {package}...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", package, "-q"])

print("  ✓ All packages installed")

# ==============================================================================
# Step 2: Generate Database
# ==============================================================================

print("\n🗄️  Step 2/4: Generating database...")

if os.path.exists('waims_demo.db'):
    print("  Database already exists, skipping generation")
else:
    subprocess.call([sys.executable, "generate_database.py"])
    print("  ✓ Database created")

# ==============================================================================
# Step 3: Fetch Real WNBA Data (Optional)
# ==============================================================================

print("\n🏀 Step 3/4: Fetching real WNBA data (optional)...")

try:
    subprocess.call([sys.executable, "fetch_wehoop_data.py"])
    print("  ✓ Real game data added")
except Exception as e:
    print(f"  ⚠️  Could not fetch wehoop data: {e}")
    print("  Continuing with simulated data only...")

# ==============================================================================
# Step 4: Train ML Models
# ==============================================================================

print("\n🤖 Step 4/4: Training ML models...")

try:
    subprocess.call([sys.executable, "train_models.py"])
    print("  ✓ ML models trained")
except Exception as e:
    print(f"  ⚠️  Could not train models: {e}")
    print("  You can train manually with: python train_models.py")

# ==============================================================================
# Complete!
# ==============================================================================

print("\n" + "=" * 70)
print("✅ SETUP COMPLETE!")
print("=" * 70)

print("\n🚀 Next Steps:")
print("\n  1. Run the dashboard:")
print("     streamlit run dashboard.py")
print("\n  2. Open browser to: http://localhost:8501")
print("\n  3. Explore all 5 tabs:")
print("     - Today's Readiness")
print("     - Trends")
print("     - Force Plate")
print("     - Injuries")
print("     - ML Predictions ✨ NEW!")

print("\n📚 To learn what you built:")
print("     Open: LEARNING_GUIDE.md")

print("\n" + "=" * 70)
