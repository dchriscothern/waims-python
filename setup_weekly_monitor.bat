@echo off
REM ============================================================
REM  WAIMS Evidence Review -- Automated Weekly Setup
REM  Run this ONCE to schedule Monday 8am automatic runs.
REM  Requires: Python installed, this repo at C:\GitHub\waims-python
REM ============================================================

REM Detect Python path
where python > nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found in PATH. Install Python and try again.
    pause
    exit /b 1
)

REM Get repo path (where this file lives)
set REPO=%~dp0
set SCRIPT=%REPO%research_monitor.py
set REPORT=%REPO%research_report_latest.html

echo Setting up WAIMS Evidence Review -- weekly Monday 8am...
echo Repo path: %REPO%

REM Create the scheduled task
schtasks /create /tn "WAIMS Evidence Review" ^
  /tr "python \"%SCRIPT%\" --days 7 --save --html" ^
  /sc weekly /d MON /st 08:00 ^
  /f ^
  /ru "%USERNAME%"

if %errorlevel% equ 0 (
    echo.
    echo SUCCESS: Task scheduled for every Monday at 8:00am
    echo.
    echo To verify: open Task Scheduler and look for "WAIMS Evidence Review"
    echo To run now: python research_monitor.py --days 7 --save --html
    echo To view report: open the latest research_report_YYYYMMDD.html in your browser
    echo To remove: schtasks /delete /tn "WAIMS Evidence Review" /f
) else (
    echo.
    echo Task Scheduler setup failed. Try running as Administrator.
    echo.
    echo Alternative: run manually each Monday:
    echo   python research_monitor.py --days 7 --save --html
)

echo.
pause

