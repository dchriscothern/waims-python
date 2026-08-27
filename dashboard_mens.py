"""Cloud entry point for the Arkansas/mens WAIMS deployment.

Streamlit Community Cloud's Secrets panel doesn't reliably persist
WAIMS_SPORT (see SETUP_GUIDE.md, streamlit/streamlit#4123), and a
?sport= query string on the shared app hits an unrelated Cloud routing
bug. Point this deployment's "Main file path" at this file instead of
dashboard.py -- setting the env var here, before dashboard.py's sport
detection runs, is the one mechanism Cloud actually runs reliably.
"""
import os
import runpy
from pathlib import Path

os.environ["WAIMS_SPORT"] = "mens"

runpy.run_path(str(Path(__file__).resolve().parent / "dashboard.py"), run_name="__main__")
