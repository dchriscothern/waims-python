"""
WAIMS Python - Complete Setup Script

Bootstraps the current demo environment:
1. install Python dependencies from requirements.txt
2. generate the demo database if needed
3. train the demo models
4. print next-step commands

Usage:
    python complete_setup.py
"""

import os
import subprocess
import sys


def run_step(label, command):
    print(f"\n{label}")
    print(f"  $ {' '.join(command)}")
    subprocess.check_call(command)


print("=" * 70)
print("WAIMS PYTHON - COMPLETE SETUP")
print("=" * 70)

run_step("Step 1/3: Installing requirements", [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

if os.path.exists("waims_demo.db"):
    print("\nStep 2/3: Demo database already exists - skipping generate_database.py")
else:
    run_step("Step 2/3: Generating demo database", [sys.executable, "generate_database.py"])

run_step("Step 3/3: Training demo models", [sys.executable, "train_models.py"])

print("\n" + "=" * 70)
print("SETUP COMPLETE")
print("=" * 70)
print("\nNext steps:")
print("  1. streamlit run dashboard.py")
print("  2. python healthcheck.py --quick")
print("  3. Open http://localhost:8501")
print("  4. Spot-check Athlete View and Athlete Profiles")
print("\nDocs:")
print("  - README.md")
print("  - README_PYTHON.md")
print("  - LEARNING_GUIDE.md")
print("\n" + "=" * 70)
