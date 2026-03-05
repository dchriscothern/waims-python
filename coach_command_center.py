"""
WAIMS — Coach Command Center
30-second morning brief. Traffic lights, top alerts, GPS strip, forecast callout.
No clicks required. Links out to deep analyst tabs via st.session_state.
"""

import os
import pickle
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
from datetime import timedelta
from pathlib import Path

# Load readiness scorer trained model
# Falls back to formula if pkl not found (e.g. first run before train_models.py)
_SCORER_PATH = Path("models/readiness_scorer.pkl")
_READINESS_FN = None
if _SCORER_PATH.exists():
    try:
        with open(_SCORER_PATH, "rb") as _f:
            _scorer_data = pickle.load(_f)
            _READINESS_FN = _scorer_data.get("function")
    except Exception:
        _READINESS_FN = None


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _zscore(val, series, min_std=0.1):
    s = series.dropna()
    if len(s) < 5:
        return 0.0
    return float((val - s.mean()) / max(s.std(), min_std))


def _readiness(row):
    """
    Uses trained readiness_scorer.pkl when available.
    Falls back to simplified formula if model not yet trained.
    The pkl version uses evidence-based weights from train_models.py:
    - Wellness 35pts, Force plate 25pts, Schedule 10pts, z-score modifier ±10pts
    - ACWR as contextual flag only (Impellizzeri 2020, 2025 meta-analysis)
    """
    if _READINESS_FN is not None:
        try:
            return _READINESS_FN(row)
        except Exception:
            pass
    # Fallback formula (evidence-based weights, no pkl needed)
    sleep  = min(15, (row.get("sleep_hours", 7) / 8.0) * 10)
    sore   = ((10 - row.get("soreness", 5)) / 10) * 10
    mood   = (row.get("mood", 6)            / 10) * 5
    stress = ((10 - row.get("stress", 5))   / 10) * 5
    cmj    = row.get("cmj_height_cm", 30)
    cmj_s  = min(15, (cmj / 32) * 15) if cmj else 10
    rsi    = row.get("rsi_modified", 0.35)
    rsi_s  = min(10, (rsi / 0.45) * 10) if rsi else 7
    return round(max(0, min(100, sleep + sore + mood + stress + cmj_s + rsi_s)), 1)


def _traffic(score):
    if score >= 80: return "🟢", "#16a34a", "#dcfce7"
    if score >= 60: return "🟡", "#d97706", "#fef9c3"
    return "🔴", "#dc2626", "#fee2e2"


def _gps_flag(player_id, col, today_val, tl_df, ref_date):
    hist = tl_df[
        (tl_df["player_id"] == player_id) &
        (tl_df["date"] < ref_date) &
        (tl_df[col] > 0)
    ].tail(30)[col]
    if len(hist) < 5:
        return "🟡", None
    z = _zscore(today_val, hist)
    return ("🔴", z) if z <= -2 else (("🟡", z) if z <= -1 else ("🟢", z))


# ─────────────────────────────────────────────────────────────────────────────
# BUILD PLAYER SUMMARY TABLE
# ─────────────────────────────────────────────────────────────────────────────

def _build_summary(wellness, players, force_plate, training_load, end_date):
    ref = pd.Timestamp(end_date)
    rows = []

    for _, p in players.iterrows():
        pid = p["player_id"]

        # ── Wellness ──────────────────────────────────────────────────────────
        w_today = wellness[(wellness["player_id"] == pid) & (wellness["date"] == ref)]
        if len(w_today) == 0:
            continue
        w = w_today.iloc[0]
        score = _readiness(w)
        emoji, color, bg = _traffic(score)

        # ── CMJ z-score ───────────────────────────────────────────────────────
        fp_today = force_plate[(force_plate["player_id"] == pid) & (force_plate["date"] == ref)]
        cmj_flag = "—"
        if len(fp_today) > 0:
            cmj_val = fp_today.iloc[0]["cmj_height_cm"]
            hist_cmj = force_plate[
                (force_plate["player_id"] == pid) & (force_plate["date"] < ref)
            ].tail(30)["cmj_height_cm"]
            z = _zscore(cmj_val, hist_cmj, min_std=0.5)
            cmj_flag = "🔴" if z <= -2 else ("🟡" if z <= -1 else "🟢")

        # ── GPS flags ─────────────────────────────────────────────────────────
        has_gps = "player_load" in training_load.columns
        pl_flag = ac_flag = "—"
        if has_gps:
            gps_today = training_load[
                (training_load["player_id"] == pid) & (training_load["date"] == ref)
            ]
            if len(gps_today) > 0:
                g = gps_today.iloc[0]
                pl_flag, _ = _gps_flag(pid, "player_load", g["player_load"], training_load, ref)
                ac_flag, _ = _gps_flag(pid, "accel_count", g["accel_count"], training_load, ref)

        # Plain-English top reason for coach card
        flags = []
        if w["sleep_hours"] < 7.0:    flags.append(f"Low sleep ({w['sleep_hours']:.1f}h)")
        if w["soreness"] >= 7:        flags.append(f"High soreness ({w['soreness']:.0f}/10)")
        if w["stress"] >= 7:          flags.append(f"High stress ({w['stress']:.0f}/10)")
        if cmj_flag == "🔴":          flags.append("CMJ drop")
        if ac_flag  == "🔴":          flags.append("Accel drop")
        if pl_flag  == "🔴":          flags.append("Low GPS load")
        if w["mood"] <= 4:            flags.append(f"Low mood ({w['mood']:.0f}/10)")
        reason = " · ".join(flags[:2]) if flags else "All clear"

        rows.append({
            "pid":      pid,
            "name":     p["name"],
            "pos":      p.get("position", ""),
            "score":    score,
            "emoji":    emoji,
            "color":    color,
            "bg":       bg,
            "sleep":    w["sleep_hours"],
            "soreness": w["soreness"],
            "mood":     w["mood"],
            "cmj":      cmj_flag,
            "load":     pl_flag,
            "accel":    ac_flag,
            "reason":   reason,
        })


    return sorted(rows, key=lambda r: r["score"])


# ─────────────────────────────────────────────────────────────────────────────
# ALERT GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

def _top_alerts(summary_rows, acwr_df, end_date, n=3):
    alerts = []
    ref = pd.Timestamp(end_date)
    latest_acwr = acwr_df[acwr_df["date"] == ref] if len(acwr_df) > 0 else pd.DataFrame()

    for r in summary_rows:
        pid = r["pid"]

        if r["score"] < 60:
            alerts.append({
                "level": "🔴 CRITICAL",
                "name":  r["name"],
                "msg":   f"Readiness {r['score']:.0f}% — Sleep {r['sleep']:.1f}h · Soreness {r['soreness']:.0f}/10",
                "action": "Protect — modified session only",
            })
        elif r["score"] < 75 and r["soreness"] >= 7:
            alerts.append({
                "level": "🟡 MONITOR",
                "name":  r["name"],
                "msg":   f"Soreness {r['soreness']:.0f}/10 with readiness {r['score']:.0f}%",
                "action": "Reduce contact load today",
            })

        if not latest_acwr.empty:
            a = latest_acwr[latest_acwr["player_id"] == pid]
            if len(a) > 0 and a.iloc[0]["acwr"] > 1.5:
                alerts.append({
                    "level": "🟡 WORKLOAD",
                    "name":  r["name"],
                    "msg":   f"ACWR {a.iloc[0]['acwr']:.2f} — acute load spike detected",
                    "action": "Cap practice at 60%",
                })

        if r["cmj"] == "🔴":
            alerts.append({
                "level": "🔴 NEURO",
                "name":  r["name"],
                "msg":   "CMJ >2σ below personal baseline — neuromuscular fatigue",
                "action": "No explosive loading today",
            })

        if r["accel"] == "🔴":
            alerts.append({
                "level": "🟡 GPS",
                "name":  r["name"],
                "msg":   "Accel count >2σ below baseline — protective movement pattern",
                "action": "Monitor direction-change load",
            })

    # Deduplicate by name, keep highest severity
    seen = {}
    for a in alerts:
        key = a["name"]
        if key not in seen:
            seen[key] = a
        elif a["level"].startswith("🔴") and seen[key]["level"].startswith("🟡"):
            seen[key] = a

    return list(seen.values())[:n]


# ─────────────────────────────────────────────────────────────────────────────
# GPS SUMMARY STRIP
# ─────────────────────────────────────────────────────────────────────────────

def _schedule_context(end_date, db_path="waims_demo.db"):
    """Return today's game/practice context string for header."""
    import sqlite3
    try:
        conn = sqlite3.connect(db_path)
        import pandas as _pd
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        if "schedule" not in tables:
            conn.close()
            return "Practice Day"
        sched = _pd.read_sql_query(
            "SELECT * FROM schedule WHERE date = ?",
            conn, params=[str(end_date)]
        )
        conn.close()
        if sched.empty:
            return "Practice Day"
        row = sched.iloc[0]
        opp  = row.get("opponent", "")
        loc  = row.get("location", "home")
        b2b  = row.get("is_back_to_back", 0)
        rest = row.get("days_rest", 3)
        fiba = row.get("fiba_break", 0)
        if fiba:
            return "FIBA Break"
        if opp and str(opp).strip():
            home_away = "vs" if str(loc).lower() == "home" else "@"
            context = f"Game Day — {home_away} {opp}"
            if b2b:
                context += "  ·  Back-to-Back"
            elif int(rest) <= 1:
                context += f"  ·  {rest}d rest"
            return context
        return "Practice Day"
    except Exception:
        return "Practice Day"


def _gps_strip(training_load, players, end_date):
    ref = pd.Timestamp(end_date)
    if "player_load" not in training_load.columns:
        return None

    today_gps = training_load[training_load["date"] == ref].merge(
        players[["player_id", "name"]], on="player_id", how="left"
    )
    if len(today_gps) == 0:
        return None

    team_avg_load = today_gps["player_load"].mean()
    team_avg_acc  = today_gps["accel_count"].mean()
    high_load     = today_gps[today_gps["player_load"] > today_gps["player_load"].quantile(0.75)]
    low_acc       = today_gps[today_gps["accel_count"] < today_gps["accel_count"].quantile(0.25)]

    return {
        "team_avg_load": round(team_avg_load, 1),
        "team_avg_acc":  round(team_avg_acc, 1),
        "high_load_names": ", ".join(high_load["name"].tolist()),
        "low_acc_names":   ", ".join(low_acc["name"].tolist()),
        "n_players":       len(today_gps),
    }


# ─────────────────────────────────────────────────────────────────────────────
# MINI SPARKLINE
# ─────────────────────────────────────────────────────────────────────────────

def _sparkline(values, color="#2E86AB"):
    fig = go.Figure(go.Scatter(
        y=values, mode="lines",
        line=dict(color=color, width=2),
        fill="tozeroy", fillcolor=f"rgba(46,134,171,0.08)",
    ))
    fig.update_layout(
        height=50, margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# MAIN RENDER
# ─────────────────────────────────────────────────────────────────────────────

def coach_command_center(wellness, players, force_plate, training_load, acwr, end_date):

    summary         = _build_summary(wellness, players, force_plate, training_load, end_date)
    alerts          = _top_alerts(summary, acwr, end_date)
    gps             = _gps_strip(training_load, players, end_date)
    game_context    = _schedule_context(end_date)
    ref             = pd.Timestamp(end_date)

    # ── HEADER: date + game/practice context + traffic light counts ───────────
    n_green  = sum(1 for r in summary if r["score"] >= 80)
    n_yellow = sum(1 for r in summary if 60 <= r["score"] < 80)
    n_red    = sum(1 for r in summary if r["score"] < 60)

    # Game context badge color
    ctx_is_game = "Game Day" in game_context
    ctx_color   = "#f59e0b" if ctx_is_game else "#64748b"
    ctx_bg      = "rgba(245,158,11,0.12)" if ctx_is_game else "rgba(100,116,139,0.10)"

    # Build header HTML as a plain string — avoids f-string + rgba() conflicts
    # that cause Streamlit to render raw HTML instead of rendering it
    date_str   = end_date.strftime("%A, %B %d")
    header_html = (
        '<div style="background:linear-gradient(135deg,#0f172a 0%,#1e293b 60%,#0f3460 100%);'
        'border-radius:14px;padding:22px 28px 18px;margin-bottom:18px;'
        'border:1px solid rgba(255,255,255,0.07);">'
        '<div style="display:flex;align-items:center;justify-content:space-between;'
        'flex-wrap:wrap;gap:12px;">'

        # Left — date, title, context badge
        '<div>'
        f'<div style="font-size:11px;font-weight:600;letter-spacing:0.22em;'
        f'text-transform:uppercase;color:#94a3b8;margin-bottom:4px;">{date_str}</div>'
        '<div style="font-size:22px;font-weight:700;color:#f8fafc;'
        'letter-spacing:-0.01em;margin-bottom:6px;">Command Center</div>'
        f'<div style="display:inline-block;font-size:12px;font-weight:600;'
        f'color:{ctx_color};background:{ctx_bg};'
        f'border-radius:6px;padding:3px 10px;letter-spacing:0.04em;">{game_context}</div>'
        '</div>'

        # Right — traffic light counts
        '<div style="display:flex;gap:24px;align-items:center;">'

        f'<div style="text-align:center;">'
        f'<div style="font-size:30px;font-weight:800;color:#4ade80;'
        f'font-family:monospace;line-height:1;">{n_green}</div>'
        '<div style="font-size:10px;color:#86efac;letter-spacing:0.1em;'
        'font-weight:700;margin-top:2px;">READY</div>'
        '</div>'

        f'<div style="text-align:center;">'
        f'<div style="font-size:30px;font-weight:800;color:#fbbf24;'
        f'font-family:monospace;line-height:1;">{n_yellow}</div>'
        '<div style="font-size:10px;color:#fde68a;letter-spacing:0.1em;'
        'font-weight:700;margin-top:2px;">MONITOR</div>'
        '</div>'

        f'<div style="text-align:center;">'
        f'<div style="font-size:30px;font-weight:800;color:#f87171;'
        f'font-family:monospace;line-height:1;">{n_red}</div>'
        '<div style="font-size:10px;color:#fca5a5;letter-spacing:0.1em;'
        'font-weight:700;margin-top:2px;">PROTECT</div>'
        '</div>'

        '</div>'  # end right
        '</div>'  # end flex row
        '</div>'  # end outer div
    )
    st.markdown(header_html, unsafe_allow_html=True)

    # ── ROW 1: Alerts + GPS Strip ─────────────────────────────────────────────
    left, right = st.columns([3, 2])

    with left:
        st.markdown(
            '<div style="font-size:11px; font-weight:700; letter-spacing:0.18em; '
            'text-transform:uppercase; color:#94a3b8; margin-bottom:10px;">'
            'Priority Alerts</div>',
            unsafe_allow_html=True,
        )

        if not alerts:
            st.markdown(
                '<div style="background:#f0fdf4; border-left:4px solid #22c55e; '
                'border-radius:0 8px 8px 0; padding:14px 18px; '
                'color:#15803d; font-weight:600; font-size:14px;">'
                'All clear — no priority alerts today</div>',
                unsafe_allow_html=True,
            )
        else:
            for a in alerts[:3]:   # hard cap at 3
                is_red  = a["level"].startswith("🔴")
                border  = "#ef4444" if is_red else "#f59e0b"
                bg      = "#fff5f5" if is_red else "#fffbeb"
                # Plain label — strip emoji from level string
                lbl_raw = a["level"].split(" ", 1)[-1] if " " in a["level"] else a["level"]
                lbl     = lbl_raw.replace("🔴","").replace("🟡","").strip()
                lbl_color = "#dc2626" if is_red else "#d97706"
                html = (
                    f'<div style="background:{bg};border-left:4px solid {border};'
                    f'border-radius:0 8px 8px 0;padding:12px 16px;margin-bottom:8px;">'
                    # Name + label on one line
                    f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">'
                    f'<span style="font-weight:800;font-size:14px;color:#0f172a;">{a["name"]}</span>'
                    f'<span style="font-size:10px;font-weight:700;color:{lbl_color};'
                    f'letter-spacing:0.08em;">{lbl}</span>'
                    f'</div>'
                    # Why
                    f'<div style="font-size:12px;color:#475569;margin-bottom:6px;">{a["msg"]}</div>'
                    # What to do
                    f'<div style="font-size:12px;font-weight:700;color:#1e40af;">'
                    f'&#9658; {a["action"]}</div>'
                    f'</div>'
                )
                st.markdown(html, unsafe_allow_html=True)

    with right:
        st.markdown(
            '<div style="font-size:11px; font-weight:700; letter-spacing:0.18em; '
            'text-transform:uppercase; color:#94a3b8; margin-bottom:10px;">'
            'GPS / Kinexon Strip</div>',
            unsafe_allow_html=True,
        )

        if gps:
            avg_load = gps["team_avg_load"]
            avg_acc  = int(round(gps["team_avg_acc"]))
            hi_names = gps["high_load_names"] or "—"
            lo_names = gps["low_acc_names"]   or "—"
            gps_html = (
                '<div style="background:linear-gradient(135deg,#0ea5e9,#0284c7);'
                'border-radius:12px;padding:16px 20px;color:#fff;">'
                # Two stat cells
                '<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">'
                '<div>'
                '<div style="font-size:10px;font-weight:600;opacity:0.75;'
                'letter-spacing:0.1em;text-transform:uppercase;">Team Avg Load</div>'
                f'<div style="font-size:26px;font-weight:800;font-family:monospace;">{avg_load}</div>'
                '<div style="font-size:10px;opacity:0.6;">AU</div>'
                '</div>'
                '<div>'
                '<div style="font-size:10px;font-weight:600;opacity:0.75;'
                'letter-spacing:0.1em;text-transform:uppercase;">Team Avg Accels</div>'
                f'<div style="font-size:26px;font-weight:800;font-family:monospace;">{avg_acc}</div>'
                '<div style="font-size:10px;opacity:0.6;">events above threshold</div>'
                '</div>'
                '</div>'
                # High load / low accels names
                '<div style="margin-top:12px;border-top:1px solid rgba(255,255,255,0.2);'
                'padding-top:10px;">'
                '<div style="font-size:10px;font-weight:700;opacity:0.8;margin-bottom:3px;">'
                'HIGH LOAD</div>'
                f'<div style="font-size:12px;">{hi_names}</div>'
                '<div style="font-size:10px;font-weight:700;opacity:0.8;'
                'margin-top:8px;margin-bottom:3px;">LOW ACCELS</div>'
                f'<div style="font-size:12px;">{lo_names}</div>'
                '</div>'
                '</div>'
            )
            st.markdown(gps_html, unsafe_allow_html=True)
        else:
            st.markdown(
                '<div style="background:#f1f5f9;border-radius:8px;padding:16px;'
                'color:#94a3b8;font-size:13px;">GPS data unavailable</div>',
                unsafe_allow_html=True,
            )

    # ── ROW 2: Roster Status ─────────────────────────────────────────────────
    # Cards show: name | position | status badge | readiness % | 2 reasons max
    # Sorted red → yellow → green (most urgent top-left)
    # No availability %, no signal icons — badge IS the availability signal

    st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
    st.markdown(
        '<div style="font-size:11px; font-weight:700; letter-spacing:0.18em; '
        'text-transform:uppercase; color:#94a3b8; margin-bottom:10px;">Roster Status</div>',
        unsafe_allow_html=True,
    )

    grid_rows = (
        [r for r in summary if r["score"] < 60] +
        [r for r in summary if 60 <= r["score"] < 80] +
        [r for r in summary if r["score"] >= 80]
    )

    CARD = {
        "red":    {"bg": "#fde8e8", "border": "#ef4444", "score": "#dc2626",
                   "badge_bg": "#fecaca", "badge_fg": "#991b1b", "label": "PROTECT"},
        "yellow": {"bg": "#fef9c3", "border": "#f59e0b", "score": "#d97706",
                   "badge_bg": "#fef3c7", "badge_fg": "#92400e", "label": "MONITOR"},
        "green":  {"bg": "#dcfce7", "border": "#22c55e", "score": "#16a34a",
                   "badge_bg": "#bbf7d0", "badge_fg": "#166534", "label": "READY"},
    }

    def _key(score):
        return "red" if score < 60 else ("yellow" if score < 80 else "green")

    def _card(r):
        k  = _key(r["score"])
        c  = CARD[k]
        fig = go.Figure()

        # Card background + border
        fig.add_shape(type="rect", x0=0, y0=0, x1=1, y1=1,
                      fillcolor=c["bg"], line=dict(color=c["border"], width=2),
                      xref="paper", yref="paper", layer="below")

        # Name (top-left)
        fig.add_annotation(
            x=0.07, y=0.87, xref="paper", yref="paper", showarrow=False,
            text=f"<b>{r['name']}</b>",
            font=dict(size=13, color="#0f172a"), xanchor="left")

        # Position (below name)
        fig.add_annotation(
            x=0.07, y=0.72, xref="paper", yref="paper", showarrow=False,
            text=r["pos"],
            font=dict(size=11, color="#64748b"), xanchor="left")

        # Status badge (top-right) — this IS the availability signal
        fig.add_annotation(
            x=0.93, y=0.87, xref="paper", yref="paper", showarrow=False,
            text=f"<b>{c['label']}</b>",
            font=dict(size=10, color=c["badge_fg"]),
            bgcolor=c["badge_bg"], borderpad=4, xanchor="right")

        # Readiness % (large, left) — kept per design decision
        fig.add_annotation(
            x=0.07, y=0.45, xref="paper", yref="paper", showarrow=False,
            text=f"<b>{r['score']:.0f}%</b>",
            font=dict(size=34, color=c["score"], family="Georgia, serif"),
            xanchor="left")

        # Divider
        fig.add_shape(type="line", x0=0.05, y0=0.22, x1=0.95, y1=0.22,
                      xref="paper", yref="paper",
                      line=dict(color=c["border"], width=1))

        # 2-reason line (bottom) — max 2 signals, plain English
        fig.add_annotation(
            x=0.07, y=0.10, xref="paper", yref="paper", showarrow=False,
            text=r["reason"],
            font=dict(size=10, color="#475569"), xanchor="left")

        fig.update_layout(
            height=140,
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor=c["bg"], plot_bgcolor=c["bg"],
            xaxis=dict(visible=False, range=[0, 1]),
            yaxis=dict(visible=False, range=[0, 1]),
            showlegend=False,
        )
        return fig

    cols = st.columns(4)
    for i, r in enumerate(grid_rows):
        with cols[i % 4]:
            st.plotly_chart(
                _card(r),
                use_container_width=True,
                config={"displayModeBar": False},
                key=f"card_{r['pid']}",
            )
    # Sparklines removed — belong in Trends tab, not command center
