"""
WAIMS Multi-Sport Launcher
===========================
Unified entry point for running WNBA or Men's Power 5 basketball versions.
Allows easy switching between organizations without maintaining duplicate code.

Usage:
    python launcher.py --sport wnba          # Run WNBA version
    python launcher.py --sport mens          # Run Arkansas Men's version
    python launcher.py --list                # Show available teams/sports
    python launcher.py --setup               # First-time setup wizard
"""

import os
import sys
import subprocess
import argparse
import codecs
from pathlib import Path

# Windows PowerShell/cmd often defaults to a non-UTF-8 code page, which crashes when
# printing Unicode characters like ✓, ❌, or 📊. Force UTF-8 output with a safe fallback.
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    else:
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="replace")
        sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, errors="replace")
except Exception:
    pass

# Add common module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "common"))

from sport_config_extended import list_supported_sports, get_teams_by_sport, list_supported_teams

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
WAIMS_WNBA = os.path.join(REPO_ROOT, "waims-wnba")
WAIMS_MENS = os.path.join(REPO_ROOT, "waims-mens")

# ==============================================================================
# SETUP OPTIONS
# ==============================================================================

SPORT_CONFIGS = {
    "wnba": {
        "display_name": "WNBA Basketball",
        "dir": REPO_ROOT,
        "dashboard": os.path.join(REPO_ROOT, "dashboard.py"),
        "data_gen": os.path.join(REPO_ROOT, "generate_database.py"),
        "model_train": os.path.join(REPO_ROOT, "train_models.py"),
        "database": os.path.join(REPO_ROOT, "waims_demo.db"),
        "description": "Women's professional basketball (Dallas Wings demo)",
    },
    "mens": {
        "display_name": "Men's Power 5 Basketball (Arkansas Razorbacks)",
        "dir": REPO_ROOT,
        "dashboard": os.path.join(REPO_ROOT, "dashboard.py"),
        "data_gen": os.path.join(WAIMS_MENS, "generate_database_arkansas.py"),
        "model_train": os.path.join(WAIMS_MENS, "train_models_arkansas.py"),
        "database": os.path.join(WAIMS_MENS, "data", "waims_arkansas.db"),
        "description": "Men's college basketball (Arkansas Razorbacks - SEC)",
    },
}

# ==============================================================================
# FUNCTIONS
# ==============================================================================

def print_banner():
    """Print welcome banner."""
    print("\n" + "=" * 70)
    print(" " * 20 + "WAIMS Multi-Sport Dashboard")
    print(" " * 15 + "Wellness & Athlete Injury Management System")
    print("=" * 70 + "\n")


def list_options():
    """Show available sports and teams."""
    print_banner()
    print("📊 AVAILABLE SPORTS & TEAMS:\n")
    
    for sport in list_supported_sports():
        teams = get_teams_by_sport(sport)
        if sport == "wnba_basketball":
            sport_key = "wnba"
        elif sport == "mens_power5_basketball":
            sport_key = "mens"
        else:
            continue
            
        config = SPORT_CONFIGS.get(sport_key)
        if not config:
            continue
            
        print(f"  🏀 {config['display_name']}")
        print(f"     {config['description']}")
        print(f"     Run with: python launcher.py --sport {sport_key}")
        print(f"     Teams: {', '.join(teams)}\n")


def setup_wizard():
    """Interactive setup wizard."""
    print_banner()
    print("🛠️  FIRST-TIME SETUP WIZARD\n")
    
    print("This script will help you set up WAIMS for your sport.\n")
    print("Select a sport to set up:\n")
    
    for idx, (key, config) in enumerate(SPORT_CONFIGS.items(), 1):
        print(f"  {idx}. {config['display_name']}")
    
    choice = input("\nEnter number (1-2): ").strip()
    
    if choice == "1":
        return setup_wnba()
    elif choice == "2":
        return setup_mens()
    else:
        print("\n❌ Invalid choice")
        return False


def setup_wnba():
    """Set up WNBA version."""
    print("\n🏀 Setting up WNBA Version...\n")
    
    config = SPORT_CONFIGS["wnba"]
    print(f"📁 Working directory: {config['dir']}")
    
    # Generate database
    print(f"\n1️⃣  Generating synthetic data...")
    print(f"   Running: python {config['data_gen']}")
    result = subprocess.run(
        [sys.executable, config["data_gen"]],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"❌ Data generation failed:")
        print(result.stderr)
        return False
    
    print("   ✓ Database created")
    
    # Train model
    print(f"\n2️⃣  Training injury risk model...")
    print(f"   Running: python {config['model_train']}")
    result = subprocess.run(
        [sys.executable, config["model_train"]],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"❌ Model training failed:")
        print(result.stderr)
        return False
    
    print("   ✓ Model trained")
    
    print("\n✅ WNBA setup complete!")
    print(f"\nTo run the dashboard:")
    print(f"   streamlit run dashboard.py\n")
    return True


def setup_mens():
    """Set up Men's Power 5 version."""
    print("\n🏀 Setting up Men's Power 5 Basketball (Arkansas)...\n")
    
    config = SPORT_CONFIGS["mens"]
    print(f"📁 Working directory: {config['dir']}")
    
    # Generate database
    print(f"\n1️⃣  Generating synthetic data...")
    print(f"   Running: python {config['data_gen']}")
    result = subprocess.run(
        [sys.executable, config["data_gen"]],
        cwd=config["dir"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"❌ Data generation failed:")
        print(result.stderr)
        return False
    
    print("   ✓ Database created")
    
    # Train model
    print(f"\n2️⃣  Training injury risk model...")
    print(f"   Running: python {config['model_train']}")
    result = subprocess.run(
        [sys.executable, config["model_train"]],
        cwd=config["dir"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"❌ Model training failed:")
        print(result.stderr)
        return False
    
    print("   ✓ Model trained")
    
    print("\n✅ Arkansas Men's Basketball setup complete!")
    print(f"\nTo run the dashboard:")
    print(f"   cd {config['dir']}")
    print(f"   streamlit run dashboard.py\n")
    return True


def run_dashboard(sport: str):
    """Launch dashboard for specified sport."""
    if sport not in SPORT_CONFIGS:
        print(f"\n❌ Invalid sport: {sport}")
        print(f"Available: {', '.join(SPORT_CONFIGS.keys())}")
        return False
    
    config = SPORT_CONFIGS[sport]
    
    print_banner()
    print(f"🚀 Launching {config['display_name']} dashboard...\n")
    print(f"📊 Sport: {config['display_name']}")
    print(f"📁 Directory: {config['dir']}")
    print(f"🗄️  Database: {config['database']}\n")
    
    # Verify dashboard exists
    if not os.path.exists(config["dashboard"]):
        print(f"❌ Dashboard not found: {config['dashboard']}")
        print("\nSetup required. Run: python launcher.py --setup")
        return False
    
    # Verify database exists
    if not os.path.exists(config["database"]):
        print(f"⚠️  Database not found: {config['database']}")
        print("Running data generation first...\n")
        
        result = subprocess.run(
            [sys.executable, config["data_gen"]],
            cwd=config["dir"] if sport == "mens" else REPO_ROOT,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"❌ Data generation failed:")
            print(result.stderr)
            return False
        
        print("✓ Database created\n")
    
    # Launch Streamlit
    try:
        print("=" * 70)
        print("Streamlit dashboard starting... (Ctrl+C to stop)\n")
        print("=" * 70 + "\n")

        env = os.environ.copy()
        env["WAIMS_SPORT"] = sport

        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", config["dashboard"]],
            cwd=config["dir"],
            env=env,
        )
    except KeyboardInterrupt:
        print("\n\n" + "=" * 70)
        print("Dashboard stopped")
        print("=" * 70)
    
    return True


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="WAIMS Multi-Sport Dashboard Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python launcher.py --sport wnba           Launch WNBA dashboard
  python launcher.py --sport mens           Launch Arkansas Men's dashboard
  python launcher.py --list                 Show available sports
  python launcher.py --setup                First-time setup wizard
        """
    )
    
    parser.add_argument(
        "--sport",
        choices=list(SPORT_CONFIGS.keys()),
        help="Sport to launch (wnba or mens)"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available sports and teams"
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Run first-time setup wizard"
    )
    
    args = parser.parse_args()
    
    # No arguments = show help
    if not (args.sport or args.list or args.setup):
        parser.print_help()
        print("\n" + "=" * 70)
        print("Quick start:")
        print("  python launcher.py --sport wnba    # WNBA dashboard")
        print("  python launcher.py --sport mens    # Arkansas Men's")
        print("  python launcher.py --list          # Show options")
        print("=" * 70 + "\n")
        return
    
    # List available options
    if args.list:
        list_options()
        return
    
    # Setup wizard
    if args.setup:
        setup_wizard()
        return
    
    # Launch dashboard
    if args.sport:
        run_dashboard(args.sport)
        return


if __name__ == "__main__":
    main()
