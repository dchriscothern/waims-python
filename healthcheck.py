"""
WAIMS Health Check & Debugging
================================
Run before demoing or deploying to catch issues early.

Usage
-----
    python healthcheck.py              # full check, print report
    python healthcheck.py --quick      # syntax + DB only
    python healthcheck.py --fix        # attempt auto-fixes where possible
    streamlit run healthcheck.py       # interactive Streamlit report

Checks performed
----------------
1.  Python & package versions
2.  Required file existence
3.  Database integrity (tables, row counts, date ranges)
4.  Module imports (all WAIMS modules)
5.  Deprecation scan (use_container_width, pandas GroupBy)
6.  research_log.json validity
7.  Model file existence and loadability
8.  GitHub Actions workflow files
9.  Auth credentials integrity
10. Data quality spot-check (GPS spikes, missing wellness)
"""

import sys
import os
import json
import sqlite3
import importlib
import subprocess
from pathlib import Path
from datetime import datetime

try:
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

# ── Colour helpers (terminal) ─────────────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
BLUE   = "\033[94m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def ok(msg):   print(f"  {GREEN}[OK]{RESET}    {msg}")
def warn(msg): print(f"  {YELLOW}[WARN]{RESET}  {msg}")
def fail(msg): print(f"  {RED}[FAIL]{RESET}  {msg}")
def info(msg): print(f"  {BLUE}[INFO]{RESET}  {msg}")
def head(msg): print(f"\n{BOLD}{msg}{RESET}")

ISSUES   = []
WARNINGS = []

def record_fail(msg):
    ISSUES.append(msg)
    fail(msg)

def record_warn(msg):
    WARNINGS.append(msg)
    warn(msg)


# ==============================================================================
# CHECK 1: Python & packages
# ==============================================================================

def check_environment():
    head("1. Environment")

    # Python version
    v = sys.version_info
    if v.major == 3 and v.minor >= 10:
        ok(f"Python {v.major}.{v.minor}.{v.micro}")
    else:
        record_warn(f"Python {v.major}.{v.minor}.{v.micro} — recommend 3.10+")

    # Required packages
    required = {
        "streamlit":  "1.30",
        "pandas":     "2.0",
        "plotly":     "5.0",
        "sklearn":    None,
        "numpy":      None,
        "scipy":      None,
    }
    for pkg, min_ver in required.items():
        try:
            mod = importlib.import_module(pkg if pkg != "sklearn" else "sklearn")
            ver = getattr(mod, "__version__", "?")
            ok(f"{pkg} {ver}")
        except ImportError:
            record_fail(f"{pkg} not installed — run: pip install {pkg}")


# ==============================================================================
# CHECK 2: Required files
# ==============================================================================

REQUIRED_FILES = [
    "dashboard.py",
    "auth.py",
    "coach_command_center.py",
    "athlete_profile_tab.py",
    "improved_gauges.py",
    "z_score_module.py",
    "research_citations.py",
    "correlation_explorer.py",
    "data_quality.py",
    "model_validation.py",
    "sport_config.py",
    "research_monitor.py",
    "generate_database.py",
    "train_models.py",
    "waims_demo.db",
    "assets/branding/waims_run_man_logo.png",
]

OPTIONAL_FILES = [
    "research_log.json",
    "models/injury_risk_model.pkl",
    ".github/workflows/ci.yml",
    ".github/workflows/research_monitor.yml",
    ".github/workflows/retrain_models.yml",
    "research_context.py",
    "data/processed_data.csv",
]

def check_files():
    head("2. Required Files")
    for f in REQUIRED_FILES:
        p = Path(f)
        if p.exists():
            size = p.stat().st_size
            ok(f"{f} ({size:,} bytes)")
        else:
            record_fail(f"MISSING: {f}")

    head("2b. Optional Files")
    for f in OPTIONAL_FILES:
        p = Path(f)
        if p.exists():
            ok(f"{f}")
        else:
            record_warn(f"Not found (optional): {f}")


# ==============================================================================
# CHECK 3: Database integrity
# ==============================================================================

EXPECTED_TABLES = {
    "players":       10,
    "wellness":      400,
    "training_load": 400,
    "force_plate":   200,
    "injuries":      1,
    "acwr":          400,
}

def check_database():
    head("3. Database Integrity")
    db_path = Path("waims_demo.db")
    if not db_path.exists():
        record_fail("waims_demo.db not found — run: python generate_database.py")
        return

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Check tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}

        for table, min_rows in EXPECTED_TABLES.items():
            if table not in tables:
                record_fail(f"Table missing: {table}")
                continue
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            if count >= min_rows:
                ok(f"{table}: {count:,} rows")
            else:
                record_warn(f"{table}: only {count} rows (expected ≥{min_rows})")

        # Check date range
        cursor.execute("SELECT MIN(date), MAX(date) FROM wellness")
        min_d, max_d = cursor.fetchone()
        if min_d and max_d:
            ok(f"Wellness date range: {min_d} → {max_d}")
        else:
            record_warn("Wellness table has no dates")

        # Check for NULLs in critical columns
        for col in ["sleep_hours", "soreness", "stress", "mood"]:
            cursor.execute(f"SELECT COUNT(*) FROM wellness WHERE {col} IS NULL")
            nulls = cursor.fetchone()[0]
            if nulls == 0:
                ok(f"wellness.{col}: no NULLs")
            else:
                record_warn(f"wellness.{col}: {nulls} NULL values")

        conn.close()

    except Exception as e:
        record_fail(f"Database error: {e}")


# ==============================================================================
# CHECK 4: Module imports
# ==============================================================================

WAIMS_MODULES = [
    "auth",
    "coach_command_center",
    "data_quality",
    "model_validation",
    "sport_config",
]

def check_imports():
    head("4. Module Imports")
    for mod in WAIMS_MODULES:
        try:
            importlib.import_module(mod)
            ok(f"import {mod}")
        except ImportError as e:
            record_fail(f"import {mod} failed: {e}")
        except Exception as e:
            record_warn(f"import {mod} raised: {e}")


# ==============================================================================
# CHECK 5: Deprecation scan
# ==============================================================================

SCAN_FILES = [
    "dashboard.py",
    "coach_command_center.py",
    "athlete_profile_tab.py",
    "data_quality.py",
    "model_validation.py",
]

DEPRECATIONS = [
    ("use_container_width",
     "Replace with width='stretch' (except on st.button calls)",
     ["st.button", "form_submit_button", "sidebar.button"]),
    ("include_groups=True",
     "GroupBy.apply — add include_groups=False",
     []),
]

def check_deprecations():
    head("5. Deprecation Scan")
    for fname in SCAN_FILES:
        fpath = Path(fname)
        if not fpath.exists():
            continue
        lines = fpath.read_text(encoding="utf-8", errors="replace").splitlines()
        for dep, fix, exceptions in DEPRECATIONS:
            hits = []
            for i, line in enumerate(lines, 1):
                if dep in line:
                    # Skip if it's an exception pattern
                    if any(exc in line for exc in exceptions):
                        continue
                    hits.append(i)
            if hits:
                record_warn(f"{fname} L{hits}: '{dep}' — {fix}")
            else:
                ok(f"{fname}: no '{dep}'")


# ==============================================================================
# CHECK 6: research_log.json
# ==============================================================================

def check_research_log():
    head("6. Research Log")
    p = Path("research_log.json")
    if not p.exists():
        info("research_log.json not found — Evidence Review tab will show setup message (OK for demo)")
        return

    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            record_fail("research_log.json: expected a list at root")
            return

        n_total    = len(data)
        n_pending  = sum(1 for x in data if x.get("decision", "PENDING") == "PENDING")
        n_candidate = sum(1 for x in data if x.get("gate_status") == "CANDIDATE")

        ok(f"research_log.json: {n_total} papers, {n_pending} pending, {n_candidate} candidates")

        # Check structure of first entry
        if data:
            required_keys = ["title", "decision"]
            missing = [k for k in required_keys if k not in data[0]]
            if missing:
                record_warn(f"research_log.json entries missing keys: {missing}")

    except json.JSONDecodeError as e:
        record_fail(f"research_log.json is not valid JSON: {e}")


# ==============================================================================
# CHECK 7: ML model
# ==============================================================================

def check_model():
    head("7. ML Model")
    model_path = Path("models/injury_risk_model.pkl")
    if not model_path.exists():
        record_warn("models/injury_risk_model.pkl not found — Forecast tab will show training instructions")
        info("To fix: run python train_models.py")
        return

    try:
        import pickle
        with open(model_path, "rb") as f:
            model = pickle.load(f)
        ok(f"Model loaded: {type(model).__name__}")

        # Check it has predict method
        if hasattr(model, "predict"):
            ok("Model has predict() method")
        else:
            record_warn("Model missing predict() — may not be a valid sklearn model")

    except Exception as e:
        record_fail(f"Model load failed: {e}")


# ==============================================================================
# CHECK 8: GitHub Actions
# ==============================================================================

def check_github_actions():
    head("8. GitHub Actions")
    workflows = [
        ".github/workflows/ci.yml",
        ".github/workflows/research_monitor.yml",
        ".github/workflows/retrain_models.yml",
    ]
    for wf in workflows:
        p = Path(wf)
        if p.exists():
            ok(f"{wf}")
        else:
            record_warn(f"Workflow not found: {wf} — automation won't run on GitHub")


# ==============================================================================
# CHECK 9: Auth credentials
# ==============================================================================

def check_auth():
    head("9. Auth System")
    try:
        from auth import DEMO_USERS, TAB_ACCESS, DATA_ACCESS
        ok(f"{len(DEMO_USERS)} demo users configured")

        # Check all roles have TAB_ACCESS
        for username, user in DEMO_USERS.items():
            role = user["role"]
            if role in TAB_ACCESS:
                ok(f"  {username} ({role}): tab access configured")
            else:
                record_fail(f"  {username} role '{role}' missing from TAB_ACCESS")

    except ImportError:
        record_fail("auth.py not found or has import error")
    except Exception as e:
        record_warn(f"Auth check raised: {e}")


# ==============================================================================
# CHECK 10: Data quality spot-check
# ==============================================================================

def check_data_quality():
    head("10. Data Quality Spot-Check")
    try:
        import pandas as pd
        import sqlite3

        conn = sqlite3.connect("waims_demo.db")
        wellness = pd.read_sql_query("SELECT * FROM wellness", conn)
        fp       = pd.read_sql_query("SELECT * FROM force_plate", conn)
        tl       = pd.read_sql_query("SELECT * FROM training_load", conn)
        conn.close()

        # Check for GPS spikes using the same dual-threshold logic as data_quality.py
        spike_count = 0
        for col in ["player_load", "session_distance", "decel_count"]:
            if col not in tl.columns:
                continue
            for pid in tl["player_id"].unique():
                series = tl[tl["player_id"] == pid][col].dropna()
                if len(series) < 5:
                    continue
                roll_mean = series.rolling(14, min_periods=3).mean()
                roll_std  = series.rolling(14, min_periods=3).std()
                std_floor = (roll_mean * 0.15).clip(lower=2.0)
                roll_std  = roll_std.fillna(std_floor).clip(lower=std_floor)
                upper_cap = roll_mean + 3.0 * roll_std
                rel_cap   = roll_mean * 1.60
                spikes    = ((series > upper_cap) & (series > rel_cap)).sum()
                spike_count += spikes

        if spike_count == 0:
            ok("GPS data: no spikes detected (clean synthetic data — expected)")
        else:
            record_warn(f"GPS data: {spike_count} spike(s) detected — check data_quality.py logic")

        # Check wellness completeness
        total_expected = wellness["player_id"].nunique() * wellness["date"].nunique()
        actual = len(wellness)
        pct = actual / total_expected * 100 if total_expected > 0 else 0
        ok(f"Wellness completeness: {actual}/{total_expected} ({pct:.0f}%)")

    except Exception as e:
        record_warn(f"Data quality check raised: {e}")


# ==============================================================================
# STREAMLIT MODE
# ==============================================================================

def run_streamlit_report():
    """Interactive Streamlit health check dashboard."""
    import streamlit as st
    import pandas as pd

    st.set_page_config(page_title="WAIMS Health Check", page_icon="🏥", layout="wide")
    st.title("🏥 WAIMS Health Check")
    st.caption(f"Run at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Run all checks and collect results
    results = []

    checks = [
        ("Environment",      check_environment),
        ("Files",            check_files),
        ("Database",         check_database),
        ("Imports",          check_imports),
        ("Deprecations",     check_deprecations),
        ("Research Log",     check_research_log),
        ("ML Model",         check_model),
        ("GitHub Actions",   check_github_actions),
        ("Auth System",      check_auth),
        ("Data Quality",     check_data_quality),
    ]

    col1, col2, col3 = st.columns(3)

    # Run silently first to collect counts
    import io, contextlib
    for name, fn in checks:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            global ISSUES, WARNINGS
            before_issues = len(ISSUES)
            before_warns  = len(WARNINGS)
            try:
                fn()
            except Exception as e:
                ISSUES.append(f"{name}: unexpected error — {e}")

        new_issues = len(ISSUES) - before_issues
        new_warns  = len(WARNINGS) - before_warns
        status = "🔴 Issues" if new_issues else ("🟡 Warnings" if new_warns else "🟢 OK")
        results.append({"Check": name, "Status": status,
                        "Issues": new_issues, "Warnings": new_warns})

    # Summary metrics
    total_issues = len(ISSUES)
    total_warns  = len(WARNINGS)

    col1.metric("Critical Issues", total_issues,
                delta="Fix before demo" if total_issues else None,
                delta_color="inverse")
    col2.metric("Warnings", total_warns,
                delta="Review recommended" if total_warns else None,
                delta_color="inverse")
    col3.metric("Status",
                "🔴 NOT DEMO READY" if total_issues else
                ("🟡 DEMO READY (with warnings)" if total_warns else "🟢 DEMO READY"))

    st.markdown("---")

    # Results table
    df = pd.DataFrame(results)
    st.dataframe(df, width="stretch", hide_index=True)

    if ISSUES:
        st.markdown("### 🔴 Critical Issues (must fix)")
        for i in ISSUES:
            st.error(i)

    if WARNINGS:
        st.markdown("### 🟡 Warnings (review recommended)")
        for w in WARNINGS:
            st.warning(w)

    if not ISSUES and not WARNINGS:
        st.success("✅ All checks passed — WAIMS is demo ready.")


# ==============================================================================
# MAIN
# ==============================================================================

def run_terminal():
    print(f"\n{'='*55}")
    print(f" WAIMS HEALTH CHECK — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*55}")

    check_environment()
    check_files()
    check_database()
    check_imports()
    check_deprecations()
    check_research_log()
    check_model()
    check_github_actions()
    check_auth()
    check_data_quality()

    print(f"\n{'='*55}")
    if ISSUES:
        print(f"{RED}{BOLD} {len(ISSUES)} CRITICAL ISSUE(S) — fix before demo:{RESET}")
        for i, issue in enumerate(ISSUES, 1):
            print(f"  {RED}{i}. {issue}{RESET}")
    if WARNINGS:
        print(f"{YELLOW}{BOLD} {len(WARNINGS)} WARNING(S):{RESET}")
        for i, w in enumerate(WARNINGS, 1):
            print(f"  {YELLOW}{i}. {w}{RESET}")
    if not ISSUES and not WARNINGS:
        print(f"{GREEN}{BOLD} ALL CHECKS PASSED - WAIMS is demo ready{RESET}")
    print(f"{'='*55}\n")

    return len(ISSUES)  # exit code


if __name__ == "__main__":
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
    except ImportError:
        get_script_run_ctx = None

    if get_script_run_ctx is not None and get_script_run_ctx() is not None:
        run_streamlit_report()
    else:
        exit_code = run_terminal()
        sys.exit(exit_code)
