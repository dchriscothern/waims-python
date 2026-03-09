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

import streamlit as st

# ---------------------------------------------------------------------------
# DEMO USER CREDENTIALS
# In production: query a users table with hashed passwords (bcrypt / argon2)
# ---------------------------------------------------------------------------
DEMO_USERS = {
    "coach":     {"password": "coach123",   "role": "head_coach",      "display": "Head Coach",
                  "name": "Coach Demo"},
    "acoach":    {"password": "acoach123",  "role": "asst_coach",      "display": "Asst. Coach",
                  "name": "Asst. Coach Demo"},
    "scientist": {"password": "sci123",     "role": "sport_scientist", "display": "Sport Scientist / Medical",
                  "name": "Sport Scientist Demo"},
    "medical":   {"password": "med123",     "role": "medical",         "display": "Medical / AT",
                  "name": "Medical Staff Demo"},
    "gm":        {"password": "gm123",      "role": "gm",              "display": "General Manager",
                  "name": "GM Demo"},
}

# ---------------------------------------------------------------------------
# TAB VISIBILITY PER ROLE
# True = show tab, False = hidden entirely
# ---------------------------------------------------------------------------
TAB_ACCESS = {
    #                            CC     Readiness  Profiles  Trends  Jumps  Injuries  Forecast  Insights
    "head_coach":      dict(cc=True,  rd=True,   ap=False, tr=True, jt=False, inj=True,  fc=True,  ins=False),
    "asst_coach":      dict(cc=True,  rd=True,   ap=False, tr=True, jt=False, inj=True,  fc=True,  ins=False),
    "sport_scientist": dict(cc=True,  rd=True,   ap=True,  tr=True, jt=True,  inj=True,  fc=True,  ins=True),
    "medical":         dict(cc=True,  rd=True,   ap=True,  tr=True, jt=True,  inj=True,  fc=True,  ins=True),
    "gm":              dict(cc=True,  rd=False,  ap=False, tr=False,jt=False, inj=True,  fc=False, ins=False),
}

# Tab labels (must match order used in dashboard.py)
TAB_LABELS = {
    "cc":  "🏀 Command Center",
    "rd":  "📊 Today's Readiness",
    "ap":  "👤 Athlete Profiles",
    "tr":  "📈 Trends & Load",
    "jt":  "💪 Jump Testing",
    "inj": "🚨 Availability & Injuries",
    "fc":  "🔮 Forecast",
    "ins": "🔍 Insights",
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
    }.get(role, "#6b7280")


def render_login_page():
    """Render the login screen. Returns True if login succeeded."""

    st.markdown("""
    <style>
    .login-box {
        max-width: 420px;
        margin: 60px auto;
        padding: 40px;
        background: white;
        border-radius: 16px;
        box-shadow: 0 4px 24px rgba(0,0,0,0.10);
        border-top: 6px solid #1e3a5f;
    }
    .login-title {
        font-size: 26px;
        font-weight: 800;
        color: #1e3a5f;
        margin-bottom: 4px;
    }
    .login-sub {
        font-size: 14px;
        color: #64748b;
        margin-bottom: 28px;
    }
    .demo-creds {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 14px 18px;
        margin-top: 24px;
        font-size: 13px;
    }
    .demo-creds h4 { color: #1e3a5f; margin: 0 0 10px 0; font-size: 13px; }
    .cred-row { display: flex; justify-content: space-between; padding: 3px 0;
                border-bottom: 1px solid #f1f5f9; color: #374151; }
    .role-badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 700;
        color: white;
        margin-left: 6px;
    }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.markdown('<div class="login-title">🏀 WAIMS</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-sub">Wellness & Athlete Injury Management System<br>Dallas Wings Demo · v1.1</div>',
                    unsafe_allow_html=True)

        with st.form("login_form"):
            username = st.text_input("Username", placeholder="e.g. coach")
            password = st.text_input("Password", type="password", placeholder="Password")
            submitted = st.form_submit_button("Sign In", use_container_width=True)

        if submitted:
            user = DEMO_USERS.get(username.strip().lower())
            if user and user["password"] == password.strip():
                st.session_state["authenticated"] = True
                st.session_state["username"]      = username.strip().lower()
                st.session_state["role"]          = user["role"]
                st.session_state["display_role"]  = user["display"]
                st.session_state["user_name"]     = user["name"]
                st.rerun()
            else:
                st.error("Incorrect username or password.")

        # Demo credentials panel
        st.markdown("""
        <div class="demo-creds">
          <h4>Demo Credentials</h4>
          <div class="cred-row"><span>coach / coach123</span><span style="color:#1e3a5f;font-weight:700">Head Coach</span></div>
          <div class="cred-row"><span>acoach / acoach123</span><span style="color:#2563eb;font-weight:700">Asst. Coach</span></div>
          <div class="cred-row"><span>scientist / sci123</span><span style="color:#059669;font-weight:700">Sport Scientist</span></div>
          <div class="cred-row"><span>medical / med123</span><span style="color:#7c3aed;font-weight:700">Medical / AT</span></div>
          <div class="cred-row" style="border:none"><span>gm / gm123</span><span style="color:#b45309;font-weight:700">General Manager</span></div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

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
         else 'Coach view — wellness data restricted' if role in ('head_coach','asst_coach')
         else 'Executive view — availability only'}
      </div>
    </div>
    """, unsafe_allow_html=True)

    if st.sidebar.button("🚪 Sign Out", use_container_width=True):
        for key in ["authenticated", "username", "role", "display_role", "user_name"]:
            st.session_state.pop(key, None)
        st.rerun()


def is_authenticated() -> bool:
    return st.session_state.get("authenticated", False)


def current_role() -> str:
    return st.session_state.get("role", "")


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
    return [(k, TAB_LABELS[k]) for k, visible in access.items() if visible]
