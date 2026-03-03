"""
Improved Gauge Designs — Clean, Professional
"""

import streamlit as st
import plotly.graph_objects as go


def create_clean_speedometer(value, title, thresholds=[60, 80]):
    """
    Solid filled-arc gauge. The bar fills from 0 up to the value
    with full thickness, coloured by status zone.
    """
    value = max(0.0, min(100.0, float(value)))
    y_start, g_start = thresholds

    if value >= g_start:
        status_color = "#10b981"
        status_text  = "READY"
    elif value >= y_start:
        status_color = "#f59e0b"
        status_text  = "MONITOR"
    else:
        status_color = "#ef4444"
        status_text  = "AT RISK"

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={
            "font": {"size": 44, "color": status_color, "family": "Arial Black"},
            "suffix": "",
        },
        title={
            "text": f"<b>{title}</b><br><span style='font-size:13px;color:{status_color};'>{status_text}</span>",
            "font": {"size": 15},
        },
        gauge={
            "shape": "angular",
            "axis": {
                "range": [0, 100],
                "tickvals": [0, 25, 50, 75, 100],
                "tickwidth": 1,
                "tickcolor": "rgba(0,0,0,0.15)",
                "tickfont": {"size": 11, "color": "#9ca3af"},
            },
            # Full-thickness solid bar coloured by status
            "bar": {"color": status_color, "thickness": 1.0},
            "bgcolor": "#f3f4f6",   # light grey track behind the bar
            "borderwidth": 0,
            # Faint zone bands visible behind the bar
            "steps": [
                {"range": [0,       y_start], "color": "rgba(239,68,68,0.12)"},
                {"range": [y_start, g_start], "color": "rgba(245,158,11,0.12)"},
                {"range": [g_start, 100],     "color": "rgba(16,185,129,0.12)"},
            ],
        },
    ))

    fig.update_layout(
        height=240,
        margin=dict(l=20, r=20, t=60, b=10),
        paper_bgcolor="white",
        font=dict(family="Arial"),
    )

    return fig


def create_simple_battery(value, label):
    """Horizontal progress bar — no emojis."""
    if value >= 80:
        color, status = "#10b981", "GOOD"
    elif value >= 60:
        color, status = "#f59e0b", "OK"
    else:
        color, status = "#ef4444", "LOW"

    return (
        f'<div style="background:white;border-left:4px solid {color};padding:12px;margin:6px 0;">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">'
        f'<span style="font-size:13px;font-weight:700;color:#1f2937;">{label}</span>'
        f'<span style="font-size:14px;font-weight:800;color:{color};">{value:.0f}%</span>'
        f'</div>'
        f'<div style="background:#f3f4f6;height:24px;border-radius:4px;overflow:hidden;position:relative;">'
        f'<div style="background:{color};height:100%;width:{value:.1f}%;"></div>'
        f'<div style="position:absolute;top:50%;left:12px;transform:translateY(-50%);'
        f'font-size:11px;font-weight:700;color:{"#065f46" if value > 30 else "#6b7280"};">{status}</div>'
        f'</div>'
        f'</div>'
    )


def create_player_card_compact(player_name, position, readiness_score, metrics, photo_url=None):
    """Clean player card — no emojis."""
    if readiness_score >= 80:
        sc, sb, st_ = "#10b981", "#d1fae5", "READY"
    elif readiness_score >= 60:
        sc, sb, st_ = "#f59e0b", "#fef3c7", "MONITOR"
    else:
        sc, sb, st_ = "#ef4444", "#fee2e2", "AT RISK"

    photo_html = (
        f'<img src="{photo_url}" style="width:70px;height:70px;border-radius:50%;object-fit:cover;">'
        if photo_url else
        f'<div style="width:70px;height:70px;border-radius:50%;background:{sc};'
        f'display:flex;align-items:center;justify-content:center;'
        f'color:white;font-size:18px;font-weight:700;">{player_name[:2].upper()}</div>'
    )

    mini = "".join(_mini_metric(k.capitalize(), v) for k, v in metrics.items())

    return (
        f'<div style="background:white;border-left:5px solid {sc};padding:16px;margin:10px 0;'
        f'box-shadow:0 1px 3px rgba(0,0,0,0.1);">'
        f'<div style="display:flex;gap:16px;align-items:center;margin-bottom:14px;">'
        f'{photo_html}'
        f'<div style="flex:1;">'
        f'<div style="font-size:17px;font-weight:800;color:#1f2937;margin-bottom:3px;">{player_name}</div>'
        f'<div style="font-size:12px;color:#6b7280;margin-bottom:6px;">{position}</div>'
        f'<div style="display:inline-block;background:{sb};color:{sc};padding:3px 10px;'
        f'border-radius:4px;font-size:12px;font-weight:700;">{st_}</div>'
        f'</div>'
        f'<div style="text-align:center;">'
        f'<div style="font-size:42px;font-weight:800;color:{sc};line-height:1;">{readiness_score:.0f}</div>'
        f'<div style="font-size:10px;color:#6b7280;font-weight:600;margin-top:3px;">READINESS</div>'
        f'</div>'
        f'</div>'
        f'<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;">{mini}</div>'
        f'</div>'
    )


def _mini_metric(label, value):
    color = "#10b981" if value >= 80 else "#f59e0b" if value >= 60 else "#ef4444"
    return (
        f'<div style="text-align:center;">'
        f'<div style="font-size:10px;color:#6b7280;margin-bottom:4px;font-weight:600;">{label}</div>'
        f'<div style="background:#f3f4f6;height:20px;border-radius:4px;overflow:hidden;border:1px solid {color}40;">'
        f'<div style="background:{color};height:100%;width:{value:.0f}%;"></div>'
        f'</div>'
        f'<div style="font-size:11px;font-weight:700;color:{color};margin-top:3px;">{value:.0f}</div>'
        f'</div>'
    )


def create_recommendation_box(readiness_score, context="practice"):
    """Clean recommendation box — no emojis."""
    if readiness_score >= 80:
        bc, bg = "#10b981", "#d1fae5"
        title  = "Full Training Cleared"
        text   = f"Athlete shows optimal readiness for {context}. No modifications needed."
    elif readiness_score >= 60:
        bc, bg = "#f59e0b", "#fef3c7"
        title  = "Monitor Closely"
        text   = f"Some readiness concerns. Consider lighter intensity for {context}."
    else:
        bc, bg = "#ef4444", "#fee2e2"
        title  = "Volume Reduction Recommended"
        text   = f"Significant readiness concerns. Recommend 50% volume reduction for {context}."

    return (
        f'<div style="background:{bg};border-left:6px solid {bc};padding:14px 18px;margin:14px 0;">'
        f'<div style="font-size:15px;font-weight:800;color:#1f2937;margin-bottom:6px;">{title}</div>'
        f'<div style="font-size:13px;color:#374151;line-height:1.5;">{text}</div>'
        f'</div>'
    )
