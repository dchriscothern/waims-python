"""
Basketball-specific injury risk context with CMJ/RSI z-score integration.
All HTML built as single concatenated strings — no newlines that trigger
Streamlit's Markdown code-block renderer.
"""

import re


def _s(html: str) -> str:
    """Collapse whitespace so Streamlit never treats the HTML as a code block."""
    return re.sub(r"\s+", " ", html).strip()


def injury_mechanism_insight_box(metrics: dict, context: str = "practice"):
    """
    Render a basketball-specific risk insight box.

    metrics keys used:
        sleep_hours, soreness, acwr,
        cmj_zscore      (z-score vs personal 30-day baseline, optional)
        rsi_zscore       (z-score vs personal 30-day baseline, optional)
        cmj_height_cm    (raw, optional)
        rsi_modified     (raw, optional)
    """
    import streamlit as st

    sleep   = metrics.get("sleep_hours", 7.0)
    sore    = metrics.get("soreness", 5.0)
    acwr    = metrics.get("acwr", 1.0)
    cmj_z   = metrics.get("cmj_zscore", None)
    rsi_z   = metrics.get("rsi_zscore", None)
    cmj_raw = metrics.get("cmj_height_cm", None)
    rsi_raw = metrics.get("rsi_modified", None)

    # ── Risk scoring ──────────────────────────────────────────────────
    risk_points = 0

    # Wellness flags
    if sleep < 6.5:
        risk_points += 3
    elif sleep < 7.5:
        risk_points += 1

    if sore > 7:
        risk_points += 3
    elif sore > 5:
        risk_points += 1

    if acwr > 1.5:
        risk_points += 3
    elif acwr > 1.3:
        risk_points += 1

    # Neuromuscular flags — z-score based (objective fatigue)
    cmj_flag = rsi_flag = False
    if cmj_z is not None:
        if cmj_z <= -2.0:
            risk_points += 3
            cmj_flag = True
        elif cmj_z <= -1.0:
            risk_points += 2
            cmj_flag = True

    if rsi_z is not None:
        if rsi_z <= -2.0:
            risk_points += 3
            rsi_flag = True
        elif rsi_z <= -1.0:
            risk_points += 2
            rsi_flag = True

    # ── Risk level ────────────────────────────────────────────────────
    if risk_points >= 6:
        color, bg, emoji, level = "#ef4444", "#fee2e2", "🔴", "High"
    elif risk_points >= 3:
        color, bg, emoji, level = "#f59e0b", "#fef3c7", "🟡", "Moderate"
    else:
        color, bg, emoji, level = "#10b981", "#d1fae5", "🟢", "Low"

    ctx = context.capitalize()

    # ── Build insight bullets ─────────────────────────────────────────
    bullets = []

    if cmj_flag and cmj_z is not None:
        cmj_desc = f"{cmj_raw:.1f} cm" if cmj_raw else ""
        bullets.append(
            f"CMJ {cmj_desc} is <b>{abs(cmj_z):.1f}σ below her baseline</b> — "
            f"neuromuscular fatigue detected. High ACL/ankle risk with cutting and landing."
        )

    if rsi_flag and rsi_z is not None:
        rsi_desc = f"{rsi_raw:.2f}" if rsi_raw else ""
        bullets.append(
            f"RSI-modified {rsi_desc} is <b>{abs(rsi_z):.1f}σ below her baseline</b> — "
            f"reduced reactive strength. Avoid high-speed direction changes."
        )

    if not cmj_flag and not rsi_flag and cmj_z is not None:
        bullets.append("Neuromuscular readiness within normal range — force plate clear.")

    if sleep < 6.5:
        bullets.append("Sleep below 6.5 hrs — 1.7× injury risk (Milewski 2014). Limit high-intensity sprints.")
    elif sleep < 7.5:
        bullets.append("Sleep mildly reduced — monitor movement quality.")

    if acwr > 1.5:
        bullets.append("ACWR spike >1.5 — 2.4× injury risk (Gabbett 2016). Reduce training volume.")
    elif acwr > 1.3:
        bullets.append("ACWR elevated — approaching high-risk zone.")

    if context.lower() == "competition":
        bullets.append("Competition context: non-contact injuries peak in Q4. Monitor landing mechanics.")
    else:
        bullets.append("Practice context: non-contact injuries account for ~25% of all injuries. Focus on controlled mechanics.")

    # ── Render ────────────────────────────────────────────────────────
    bullet_html = "".join(
        f'<div style="display:flex;gap:8px;margin-bottom:6px;">'
        f'<span style="color:{color};margin-top:2px;">▸</span>'
        f'<span style="font-size:13px;color:#374151;line-height:1.5;">{b}</span>'
        f'</div>'
        for b in bullets
    )

    # Neuromuscular summary strip (only if force plate data present)
    neuro_strip = ""
    if cmj_z is not None or rsi_z is not None:
        cmj_label = (
            f'<span style="font-size:12px;font-weight:700;color:{"#ef4444" if cmj_flag else "#10b981"};">'
            f'CMJ {"▼" if cmj_flag else "●"} {f"{cmj_z:+.1f}σ" if cmj_z is not None else "—"}</span>'
        )
        rsi_label = (
            f'<span style="font-size:12px;font-weight:700;color:{"#ef4444" if rsi_flag else "#10b981"};">'
            f'RSI {"▼" if rsi_flag else "●"} {f"{rsi_z:+.1f}σ" if rsi_z is not None else "—"}</span>'
        )
        neuro_strip = _s(
            f'<div style="display:flex;gap:20px;background:rgba(0,0,0,0.04);'
            f'border-radius:6px;padding:8px 12px;margin-bottom:10px;">'
            f'<span style="font-size:11px;color:#6b7280;font-weight:600;">FORCE PLATE</span>'
            f'{cmj_label}{rsi_label}'
            f'</div>'
        )

    html = _s(
        f'<div style="background:{bg};border-left:5px solid {color};'
        f'border-radius:8px;padding:16px 18px;margin:10px 0;">'
        f'<div style="font-size:15px;font-weight:800;color:#1f2937;margin-bottom:10px;">'
        f'{emoji} {level} Risk — {ctx} Context</div>'
        f'{neuro_strip}'
        f'{bullet_html}'
        f'<div style="margin-top:10px;font-size:11px;color:#9ca3af;">'
        f'Neuromuscular data: Gathercole et al. (2015) · '
        f'Sleep: Milewski et al. (2014) · Load: Gabbett (2016)</div>'
        f'</div>'
    )

    st.markdown(html, unsafe_allow_html=True)
