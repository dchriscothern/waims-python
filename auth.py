"""
WAIMS Role-Based Access Control
Demo login system showing data governance in practice.

Roles and access:
  head_coach      — Command Center, Trends, Availability (summary), Forecast
  asst_coach      — Same as Head Coach
  sport_scientist — All 8 tabs, full data
  medical         — All 8 tabs, full data
  gm              — Command Center (view only), Availability (summary only)

In production: replace DEMO_USERS with a database lookup + hashed passwords.
"""

import os
import streamlit as st

# ---------------------------------------------------------------------------
# DEMO USER CREDENTIALS
# Each app instance is bound to a specific sport and only exposes credentials for it.
# ---------------------------------------------------------------------------
DEMO_USERS = {
    "wnba": {
        "wnba_coach":     {"password": "wnba_coach",   "role": "head_coach",      "display": "WNBA Head Coach",
                           "name": "WNBA Coach Demo"},
        "wnba_acoach":    {"password": "wnba_acoach",  "role": "asst_coach",      "display": "WNBA Asst. Coach",
                           "name": "WNBA Asst. Coach Demo"},
        "wnba_scientist": {"password": "wnba_sci",     "role": "sport_scientist", "display": "WNBA Sport Scientist",
                           "name": "WNBA Scientist Demo"},
        "wnba_medical":   {"password": "wnba_med",     "role": "medical",         "display": "WNBA Medical / AT",
                           "name": "WNBA Medical Demo"},
        "wnba_gm":        {"password": "wnba_gm",      "role": "gm",              "display": "WNBA GM",
                           "name": "WNBA GM Demo"},
        "wnba_athlete":   {"password": "wnba_athlete", "role": "athlete",         "display": "WNBA Athlete",
                           "name": "WNBA Athlete Demo", "player_id": "P001"},
    },
    "mens": {
        "ark_coach":      {"password": "ark_coach",    "role": "head_coach",      "display": "Arkansas Head Coach",
                           "name": "Arkansas Coach Demo"},
        "ark_acoach":     {"password": "ark_acoach",   "role": "asst_coach",      "display": "Arkansas Asst. Coach",
                           "name": "Arkansas Asst. Coach Demo"},
        "ark_scientist":  {"password": "ark_sci",      "role": "sport_scientist", "display": "Arkansas Sport Scientist",
                           "name": "Arkansas Scientist Demo"},
        "ark_medical":    {"password": "ark_med",      "role": "medical",         "display": "Arkansas Medical / AT",
                           "name": "Arkansas Medical Demo"},
        "ark_gm":         {"password": "ark_gm",       "role": "gm",              "display": "Arkansas GM",
                           "name": "Arkansas GM Demo"},
        "ark_athlete":    {"password": "ark_athlete",  "role": "athlete",         "display": "Arkansas Athlete",
                           "name": "Arkansas Athlete Demo", "player_id": "P001"},
    },
}


def get_active_sport_key() -> str:
    sport = os.environ.get("WAIMS_SPORT", "").strip().lower()
    if sport in {"wnba", "mens"}:
        return sport
    if "sport" in st.query_params:
        sport = str(st.query_params["sport"]).strip().lower()
        if sport in {"wnba", "mens"}:
            return sport
    return "wnba"


def get_demo_users_for_active_sport() -> dict:
    return DEMO_USERS.get(get_active_sport_key(), DEMO_USERS["wnba"])

# ---------------------------------------------------------------------------
# TAB VISIBILITY PER ROLE
# True = show tab, False = hidden entirely
# ---------------------------------------------------------------------------
TAB_ACCESS = {
    #                            CC     Readiness  Profiles  Trends  Jumps  Injuries  Forecast  Insights  Intake  Game Perf
    "head_coach":      dict(cc=True,  rd=True,   ap=False, tr=False, jt=False, inj=True,  fc=True,  ins=False, di=False, gp=True),
    "asst_coach":      dict(cc=True,  rd=True,   ap=False, tr=False, jt=False, inj=True,  fc=True,  ins=False, di=False, gp=True),
    "sport_scientist": dict(cc=True,  rd=True,   ap=True,  tr=True, jt=True,  inj=True,  fc=True,  ins=True,  di=True,  gp=True),
    "medical":         dict(cc=True,  rd=True,   ap=True,  tr=True, jt=True,  inj=True,  fc=True,  ins=True,  di=False, gp=True),
    "gm":              dict(cc=True,  rd=False,  ap=False, tr=False,jt=False, inj=True,  fc=False, ins=False, di=False, gp=True),
    "athlete":         dict(cc=False, rd=True,   ap=False, tr=False,jt=False, inj=False, fc=False, ins=False, di=False, gp=False),
}

# Tab labels (must match order used in dashboard.py)
TAB_LABELS = {
    "cc":  "Command Center",
    "rd":  "Today's Readiness",
    "ap":  "Athlete Profiles",
    "tr":  "Trends & Load",
    "jt":  "Jump Testing",
    "inj": "Availability & Injuries",
    "fc":  "Forecast",
    "ins": "Insights",
    "di":  "Data Intake",
    "gp":  "Game Performance",
}

# Data field visibility per role (used to mask columns in dataframes)
DATA_ACCESS = {
    "head_coach": {
        "show_readiness_score": True,
        "show_raw_wellness": False,   # sleep/soreness/stress/mood raw values
        "show_force_plate_detail": False,
        "show_injury_detail": False,  # summary only
        "show_gps": True,
    },
    "asst_coach": {
        "show_readiness_score": True,
        "show_raw_wellness": False,
        "show_force_plate_detail": False,
        "show_injury_detail": False,
        "show_gps": True,
    },
    "sport_scientist": {
        "show_readiness_score": True,
        "show_raw_wellness": True,
        "show_force_plate_detail": True,
        "show_injury_detail": True,
        "show_gps": True,
    },
    "medical": {
        "show_readiness_score": True,
        "show_raw_wellness": True,
        "show_force_plate_detail": True,
        "show_injury_detail": True,
        "show_gps": True,
    },
    "gm": {
        "show_readiness_score": False,
        "show_raw_wellness": False,
        "show_force_plate_detail": False,
        "show_injury_detail": False,  # availability only
        "show_gps": False,
    },
}


def get_role_color(role: str) -> str:
    return {
        "head_coach":      "#1e3a5f",
        "asst_coach":      "#2563eb",
        "sport_scientist": "#059669",
        "medical":         "#7c3aed",
        "gm":              "#b45309",
        "athlete":         "#0f766e",
    }.get(role, "#6b7280")


def render_login_page():
    """Render the login screen. Returns True if login succeeded."""

    st.markdown("""
    <style>
    /* Center the login form vertically */
    section[data-testid="stMain"] > div { padding-top: 2rem; }
    </style>
    """, unsafe_allow_html=True)

    # Spacer to push login box down
    st.markdown("<div style='margin-top:40px;'></div>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        sport_name = "WNBA" if get_active_sport_key() == "wnba" else "Arkansas"

    # Header
        st.markdown(
            '<div style="text-align:center;margin-bottom:24px;">'
            '<div style="font-size:28px;font-weight:800;color:#1e3a5f;">WAIMS</div>'
            '<div style="font-size:14px;color:#64748b;margin-top:4px;">'
            f'Wellness & Athlete Injury Management System<br>{sport_name} Environment | v1.1</div>'
            '</div>',
            unsafe_allow_html=True
        )

        # Login form inside a native Streamlit container
        with st.container(border=True):
            with st.form("login_form"):
                username  = st.text_input("Username", placeholder=f"e.g. {sport_name.lower()}_coach")
                password  = st.text_input("Password", type="password", placeholder="Password")
                submitted = st.form_submit_button("Sign In", width="stretch")

            if submitted:
                users = get_demo_users_for_active_sport()
                user = users.get(username.strip().lower())
                if user and user["password"] == password.strip():
                    st.session_state["authenticated"] = True
                    st.session_state["username"]      = username.strip().lower()
                    st.session_state["role"]          = user["role"]
                    st.session_state["display_role"]  = user["display"]
                    st.session_state["user_name"]     = user["name"]
                    st.session_state["player_id"]     = user.get("player_id")
                    st.session_state["active_sport"]  = get_active_sport_key()
                    st.rerun()
                else:
                    st.error("Incorrect username or password for this environment.")

        # Demo credentials panel
        st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown(
                "<div style='font-size:12px;font-weight:700;color:#1e3a5f;"
                f"margin-bottom:10px;'>{sport_name} Demo Credentials</div>",
                unsafe_allow_html=True
            )
            users = get_demo_users_for_active_sport()
            creds = []
            for username_key, user in users.items():
                role_label = {
                    "head_coach": "Head Coach",
                    "asst_coach": "Asst. Coach",
                    "sport_scientist": "Sport Scientist",
                    "medical": "Medical / AT",
                    "gm": "General Manager",
                    "athlete": "Athlete",
                }.get(user["role"], user["role"])
                creds.append((f"{username_key} / {user['password']}", role_label, {
                    "head_coach": "#1e3a5f",
                    "asst_coach": "#2563eb",
                    "sport_scientist": "#059669",
                    "medical": "#7c3aed",
                    "gm": "#b45309",
                    "athlete": "#0f766e",
                }.get(user["role"], "#374151")))
            for user_str, role_str, color in creds:
                st.markdown(
                    f'<div style="display:flex;justify-content:space-between;'
                    f'padding:4px 0;border-bottom:1px solid #f1f5f9;font-size:12px;">'
                    f'<span style="color:#374151;">{user_str}</span>'
                    f'<span style="color:{color};font-weight:700;">{role_str}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )

    return False


def render_user_badge():
    """Sidebar badge showing current user role and logout button."""
    role  = st.session_state.get("role", "")
    name  = st.session_state.get("display_role", "")
    color = get_role_color(role)

    st.sidebar.markdown(f"""
    <div style="background:{color}18; border-left:4px solid {color};
                padding:10px 14px; border-radius:8px; margin-bottom:12px;">
      <div style="font-size:11px; color:{color}; font-weight:700; text-transform:uppercase;
                  letter-spacing:0.5px;">Signed in as</div>
      <div style="font-size:15px; font-weight:800; color:#1f2937; margin-top:2px;">{name}</div>
      <div style="font-size:11px; color:#64748b; margin-top:2px;">
        {'Full access' if role in ('sport_scientist','medical')
         else 'Coach view - wellness data restricted' if role in ('head_coach','asst_coach')
         else 'Executive view - availability only'}
      </div>
    </div>
    """, unsafe_allow_html=True)

    if st.sidebar.button(
        "Sign Out",
        width="stretch",
        key="sidebar_sign_out",
    ):
        for key in [
            "authenticated",
            "username",
            "role",
            "display_role",
            "user_name",
            "player_id",
            "_coach_active_query",
            "_coach_voice_applied",
            "_athlete_voice_applied",
            "query_to_run",
        ]:
            st.session_state.pop(key, None)
        st.rerun()

    # ── Logo at bottom of sidebar ─────────────────────────────────────────────
    st.sidebar.markdown("<div style='flex:1;'></div>", unsafe_allow_html=True)
    st.sidebar.markdown("---")
    from pathlib import Path as _Path
    _logo = _Path("assets/branding/waims_run_man_logo.png")
    if _logo.exists():
        st.sidebar.image(str(_logo), width=40)
    st.sidebar.markdown(
        "<div style='font-size:10px;color:#94a3b8;'>WAIMS v1.1 · Chris Cothern</div>",
        unsafe_allow_html=True
    )


def is_authenticated() -> bool:
    return st.session_state.get("authenticated", False)


def current_role() -> str:
    return st.session_state.get("role", "")


def current_athlete_player_id():
    return st.session_state.get("player_id")


def can_see(tab_key: str) -> bool:
    """Return True if current role can see this tab."""
    role = current_role()
    return TAB_ACCESS.get(role, {}).get(tab_key, False)


def data_access() -> dict:
    """Return data access permissions for current role."""
    return DATA_ACCESS.get(current_role(), DATA_ACCESS["gm"])


def get_visible_tabs() -> list[tuple[str, str]]:
    """Return list of (key, label) tuples for tabs the current role can see."""
    role = current_role()
    access = TAB_ACCESS.get(role, {})
    tabs = [(k, TAB_LABELS[k]) for k, visible in access.items() if visible]
    if get_active_sport_key() != "mens":
        # Game Performance is sourced from Arkansas-only tables (player_game_stats,
        # play_by_play_events) that don't exist in the WNBA database.
        tabs = [t for t in tabs if t[0] != "gp"]
    return tabs
