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

    summary = _build_summary(wellness, players, force_plate, training_load, end_date)
    alerts  = _top_alerts(summary, acwr, end_date)
    gps     = _gps_strip(training_load, players, end_date)
    ref     = pd.Timestamp(end_date)

    # ── HEADER ────────────────────────────────────────────────────────────────
    n_green  = sum(1 for r in summary if r["score"] >= 80)
    n_yellow = sum(1 for r in summary if 60 <= r["score"] < 80)
    n_red    = sum(1 for r in summary if r["score"] < 60)

    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 60%, #0f3460 100%);
            border-radius: 16px;
            padding: 28px 32px 20px;
            margin-bottom: 20px;
            border: 1px solid rgba(255,255,255,0.08);
        ">
            <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:12px;">
                <div>
                    <div style="font-family:'Georgia',serif; font-size:11px; font-weight:600;
                        letter-spacing:0.25em; text-transform:uppercase; color:#94a3b8; margin-bottom:6px;">
                        Morning Brief · {end_date.strftime('%A, %B %d')}
                    </div>
                    <div style="font-family:'Georgia',serif; font-size:28px; font-weight:700;
                        color:#f8fafc; letter-spacing:-0.02em;">
                        WAIMS Command Center
                    </div>
                </div>
                <div style="display:flex; gap:20px;">
                    <div style="text-align:center;">
                        <div style="font-size:32px; font-weight:800; color:#4ade80; font-family:monospace;">{n_green}</div>
                        <div style="font-size:11px; color:#86efac; letter-spacing:0.08em; font-weight:600;">READY</div>
                    </div>
                    <div style="text-align:center;">
                        <div style="font-size:32px; font-weight:800; color:#fbbf24; font-family:monospace;">{n_yellow}</div>
                        <div style="font-size:11px; color:#fde68a; letter-spacing:0.08em; font-weight:600;">MONITOR</div>
                    </div>
                    <div style="text-align:center;">
                        <div style="font-size:32px; font-weight:800; color:#f87171; font-family:monospace;">{n_red}</div>
                        <div style="font-size:11px; color:#fca5a5; letter-spacing:0.08em; font-weight:600;">PROTECT</div>
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── ROW 1: Alerts + GPS Strip ─────────────────────────────────────────────
    left, right = st.columns([3, 2])

    with left:
        st.markdown(
            '<div style="font-family:Georgia,serif; font-size:13px; font-weight:700; '
            'letter-spacing:0.12em; text-transform:uppercase; color:#64748b; margin-bottom:10px;">'
            'Priority Alerts</div>',
            unsafe_allow_html=True,
        )

        if not alerts:
            st.markdown(
                '<div style="background:#f0fdf4; border:1px solid #bbf7d0; border-radius:10px; '
                'padding:16px 20px; color:#15803d; font-weight:600; font-size:15px;">'
                '✅ All systems green — no priority alerts today</div>',
                unsafe_allow_html=True,
            )
        else:
            for a in alerts:
                is_red = a["level"].startswith("🔴")
                border = "#fca5a5" if is_red else "#fde68a"
                bg     = "#fff5f5" if is_red else "#fffbeb"
                icon   = "🔴" if is_red else "🟡"
                st.markdown(
                    f"""
                    <div style="background:{bg}; border-left:4px solid {border};
                        border-radius:0 10px 10px 0; padding:14px 18px; margin-bottom:10px;">
                        <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                            <div>
                                <span style="font-weight:800; font-size:14px; color:#1e293b;">
                                    {icon} {a['name']}
                                </span>
                                <span style="font-size:11px; font-weight:600; color:#64748b;
                                    background:rgba(0,0,0,0.06); border-radius:4px;
                                    padding:2px 8px; margin-left:8px;">
                                    {a['level'].split(' ',1)[1]}
                                </span>
                                <div style="font-size:13px; color:#475569; margin-top:4px;">{a['msg']}</div>
                            </div>
                        </div>
                        <div style="margin-top:8px; font-size:12px; font-weight:700;
                            color:#1e40af; letter-spacing:0.04em;">
                            ➤ {a['action']}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    with right:
        st.markdown(
            '<div style="font-family:Georgia,serif; font-size:13px; font-weight:700; '
            'letter-spacing:0.12em; text-transform:uppercase; color:#64748b; margin-bottom:10px;">'
            'GPS / Kinexon Strip</div>',
            unsafe_allow_html=True,
        )

        if gps:
            st.markdown(
                f"""
                <div style="background:linear-gradient(135deg,#0ea5e9,#0284c7);
                    border-radius:12px; padding:18px 22px; color:#fff;">
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:14px;">
                        <div>
                            <div style="font-size:11px; font-weight:600; opacity:0.75;
                                letter-spacing:0.1em; text-transform:uppercase;">Team Avg Load</div>
                            <div style="font-size:28px; font-weight:800; font-family:monospace;">
                                {gps['team_avg_load']}</div>
                            <div style="font-size:10px; opacity:0.65;">AU (arbitrary units)</div>
                        </div>
                        <div>
                            <div style="font-size:11px; font-weight:600; opacity:0.75;
                                letter-spacing:0.1em; text-transform:uppercase;">Team Avg Accels</div>
                            <div style="font-size:28px; font-weight:800; font-family:monospace;">
                                {gps['team_avg_acc']:.0f}</div>
                            <div style="font-size:10px; opacity:0.65;">events above threshold</div>
                        </div>
                    </div>
                    <div style="margin-top:14px; border-top:1px solid rgba(255,255,255,0.2); padding-top:12px;">
                        <div style="font-size:11px; font-weight:700; opacity:0.8; margin-bottom:4px;">
                            ⬆ HIGH LOAD</div>
                        <div style="font-size:12px;">{gps['high_load_names'] or '—'}</div>
                        <div style="font-size:11px; font-weight:700; opacity:0.8;
                            margin-top:8px; margin-bottom:4px;">⬇ LOW ACCELS</div>
                        <div style="font-size:12px;">{gps['low_acc_names'] or '—'}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.info("GPS data not available — run generate_database.py")

    # ── ROW 2: Roster Grid ────────────────────────────────────────────────────
    st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)
    st.markdown(
        '<div style="font-family:Georgia,serif; font-size:13px; font-weight:700; '
        'letter-spacing:0.12em; text-transform:uppercase; color:#64748b; margin-bottom:12px;">'
        'Roster Status</div>',
        unsafe_allow_html=True,
    )

    # Red first, then yellow, then green — most urgent top-left
    grid_rows = (
        [r for r in summary if r["score"] < 60] +
        [r for r in summary if 60 <= r["score"] < 80] +
        [r for r in summary if r["score"] >= 80]
    )

    # Color scheme per status
    STATUS_STYLES = {
        "red":    {"bg": "#fef2f2", "border": "#ef4444", "score_color": "#dc2626", "badge_bg": "#fecaca", "badge_text": "#991b1b", "label": "PROTECT"},
        "yellow": {"bg": "#fffbeb", "border": "#f59e0b", "score_color": "#d97706", "badge_bg": "#fef3c7", "badge_text": "#92400e", "label": "MONITOR"},
        "green":  {"bg": "#f0fdf4", "border": "#22c55e", "score_color": "#16a34a", "badge_bg": "#dcfce7", "badge_text": "#166534", "label": "READY"},
    }

    def _status_key(score):
        return "red" if score < 60 else ("yellow" if score < 80 else "green")

    # Render each card as a Plotly figure — bypasses Streamlit HTML sanitiser
    # so background colors are guaranteed to show
    def _player_card(r):
        key   = _status_key(r["score"])
        s     = STATUS_STYLES[key]
        score = r["score"]

        BG    = {"red": "#fde8e8", "yellow": "#fef9c3", "green": "#dcfce7"}[key]
        BDCLR = {"red": "#ef4444", "yellow": "#f59e0b", "green": "#22c55e"}[key]
        SCLR  = {"red": "#dc2626", "yellow": "#d97706", "green": "#16a34a"}[key]
        LBL   = {"red": "PROTECT", "yellow": "MONITOR", "green": "READY"}[key]
        LBLCLR= {"red": "#991b1b", "yellow": "#92400e", "green": "#166534"}[key]

        fig = go.Figure()

        # Background fill
        fig.add_shape(type="rect", x0=0, y0=0, x1=1, y1=1,
                      fillcolor=BG, line=dict(color=BDCLR, width=2),
                      xref="paper", yref="paper", layer="below")

        # Player name
        fig.add_annotation(x=0.06, y=0.88, text=f"<b>{r['name']}</b>",
                           xref="paper", yref="paper", showarrow=False,
                           font=dict(size=14, color="#0f172a"), xanchor="left")
        # Position
        fig.add_annotation(x=0.06, y=0.74, text=r["pos"],
                           xref="paper", yref="paper", showarrow=False,
                           font=dict(size=11, color="#64748b"), xanchor="left")
        # Status badge
        fig.add_annotation(x=0.94, y=0.88, text=f"<b>{LBL}</b>",
                           xref="paper", yref="paper", showarrow=False,
                           font=dict(size=10, color=LBLCLR), xanchor="right",
                           bgcolor=s["badge_bg"], borderpad=4)
        # Score
        fig.add_annotation(x=0.06, y=0.46,
                           text=f"<b>{score:.0f}<span style='font-size:16px'>%</span></b>",
                           xref="paper", yref="paper", showarrow=False,
                           font=dict(size=38, color=SCLR, family="Georgia, serif"),
                           xanchor="left")
        # Reason line
        fig.add_annotation(x=0.06, y=0.12, text=r["reason"],
                           xref="paper", yref="paper", showarrow=False,
                           font=dict(size=11, color="#475569"), xanchor="left")
        # Divider line
        fig.add_shape(type="line", x0=0.04, y0=0.22, x1=0.96, y1=0.22,
                      xref="paper", yref="paper",
                      line=dict(color=BDCLR, width=1, dash="solid"))

        fig.update_layout(
            height=150,
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor=BG,
            plot_bgcolor=BG,
            xaxis=dict(visible=False, range=[0,1]),
            yaxis=dict(visible=False, range=[0,1]),
            showlegend=False,
        )
        return fig

    cols = st.columns(4)
    for i, r in enumerate(grid_rows):
        with cols[i % 4]:
            st.plotly_chart(
                _player_card(r),
                use_container_width=True,
                config={"displayModeBar": False},
                key=f"card_{r['pid']}",
            )

    # ── ROW 3: Team Wellness Sparklines ───────────────────────────────────────
    st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)
    st.markdown(
        '<div style="font-family:Georgia,serif; font-size:13px; font-weight:700; '
        'letter-spacing:0.12em; text-transform:uppercase; color:#64748b; margin-bottom:10px;">'
        '7-Day Team Trends</div>',
        unsafe_allow_html=True,
    )

    cutoff = ref - pd.Timedelta(days=7)
    week_w = wellness[wellness["date"] >= cutoff].copy()

    sp1, sp2, sp3, sp4 = st.columns(4)
    spark_cfg = [
        (sp1, "sleep_hours",  "Avg Sleep (hrs)",    "#2E86AB"),
        (sp2, "soreness",     "Avg Soreness /10",   "#A23B72"),
        (sp3, "mood",         "Avg Mood /10",       "#44BBA4"),
        (sp4, "stress",       "Avg Stress /10",     "#F18F01"),
    ]
    for col_widget, field, label, color in spark_cfg:
        daily = week_w.groupby("date")[field].mean().sort_index()
        with col_widget:
            st.markdown(
                f'<div style="font-size:12px; font-weight:700; color:#475569; margin-bottom:2px;">'
                f'{label}</div>',
                unsafe_allow_html=True,
            )
            last_val = daily.iloc[-1] if len(daily) > 0 else 0
            delta    = daily.iloc[-1] - daily.iloc[-2] if len(daily) > 1 else 0
            arrow    = "↑" if delta > 0 else ("↓" if delta < 0 else "→")
            d_color  = "#16a34a" if (
                (field in ("sleep_hours","mood") and delta > 0) or
                (field in ("soreness","stress") and delta < 0)
            ) else "#dc2626"
            st.markdown(
                f'<div style="font-size:18px; font-weight:800; color:#1e293b;">'
                f'{last_val:.1f} <span style="font-size:13px; color:{d_color};">{arrow}{abs(delta):.1f}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if len(daily) > 1:
                st.plotly_chart(
                    _sparkline(daily.values, color),
                    use_container_width=True,
                    config={"displayModeBar": False},
                    key=f"spark_{field}",
                )
