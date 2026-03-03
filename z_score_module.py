"""
Z-Score Module for Personalized Athlete Monitoring
Compares current values to individual baseline (not population average)
"""

import re
import pandas as pd
import numpy as np
import streamlit as st


def _html_oneliner(s: str) -> str:
    """Collapse all whitespace so Streamlit never treats indented HTML as a code block."""
    return re.sub(r"\s+", " ", s).strip()


def calculate_athlete_baselines(wellness_df, player_id, lookback_days=30):
    athlete_data = wellness_df[wellness_df["player_id"] == player_id].copy()
    athlete_data = athlete_data.sort_values("date", ascending=False).head(lookback_days)

    if len(athlete_data) < 7:
        return None

    baselines = {}
    for col, default_std in [
        ("sleep_hours", 0.5),
        ("soreness", 1.0),
        ("stress", 1.0),
        ("mood", 1.0),
        ("sleep_quality", 1.0),
    ]:
        baselines[col] = {
            "mean": athlete_data[col].mean(),
            "std": max(athlete_data[col].std(), default_std * 0.1) or default_std,
        }

    return baselines


def calculate_z_score(current_value, baseline_mean, baseline_std):
    if not baseline_std:
        baseline_std = 0.5
    return (current_value - baseline_mean) / baseline_std


def interpret_z_score(z_score, metric_type="higher_better"):
    if metric_type == "higher_better":
        if z_score >= 1.0:
            return ("Above Baseline", "#10b981", "▲")
        elif z_score >= -0.5:
            return ("At Baseline", "#6b7280", "●")
        elif z_score >= -1.5:
            return ("Below Baseline", "#f59e0b", "▼")
        else:
            return ("Well Below Baseline", "#ef4444", "▼▼")
    else:
        if z_score <= -1.0:
            return ("Below Baseline", "#10b981", "▼")
        elif z_score <= 0.5:
            return ("At Baseline", "#6b7280", "●")
        elif z_score <= 1.5:
            return ("Above Baseline", "#f59e0b", "▲")
        else:
            return ("Well Above Baseline", "#ef4444", "▲▲")


def create_z_score_display(metric_name, current_value, z_score, metric_type="higher_better", unit=""):
    status, color, arrow = interpret_z_score(z_score, metric_type)

    # Clamp marker position to 5–95% so it stays inside the bar
    bar_pct = min(95, max(5, ((z_score + 3) / 6) * 100))

    # Direction label
    z_dir = f"{z_score:+.2f}σ"

    html = (
        f'<div style="background:#fff;border:1px solid #e5e7eb;border-left:4px solid {color};'
        f'border-radius:8px;padding:14px 16px;margin:8px 0;">'

        # Top row: name left, value right
        f'<div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:10px;">'
        f'<span style="font-size:13px;font-weight:700;color:#1f2937;">{metric_name}</span>'
        f'<span style="font-size:15px;font-weight:800;color:{color};">{current_value:.1f}{unit}</span>'
        f'</div>'

        # Track
        f'<div style="position:relative;height:10px;border-radius:5px;'
        f'background:linear-gradient(to right,#fee2e2 0%,#fef3c7 33%,#d1fae5 100%);'
        f'margin-bottom:6px;">'
        # Centre tick (baseline)
        f'<div style="position:absolute;top:-3px;left:50%;width:1px;height:16px;background:#9ca3af;"></div>'
        # Marker
        f'<div style="position:absolute;top:-4px;left:{bar_pct:.1f}%;transform:translateX(-50%);'
        f'width:12px;height:18px;border-radius:3px;background:{color};'
        f'box-shadow:0 1px 4px {color}80;"></div>'
        f'</div>'

        # Scale labels
        f'<div style="display:flex;justify-content:space-between;font-size:10px;color:#9ca3af;margin-bottom:10px;">'
        f'<span>−3σ</span><span>Baseline</span><span>+3σ</span>'
        f'</div>'

        # Status chip
        f'<div style="display:inline-flex;align-items:center;gap:6px;'
        f'background:{color}15;border-radius:4px;padding:4px 10px;">'
        f'<span style="font-size:11px;font-weight:700;color:{color};">{arrow} {status}</span>'
        f'<span style="font-size:11px;color:#6b7280;">{z_dir}</span>'
        f'</div>'

        f'</div>'
    )

    return html  # already a single line — no newlines to trigger Markdown code-block


def add_z_score_alerts(current_wellness, baselines, research_thresholds):
    alerts = []

    sleep_z = calculate_z_score(
        current_wellness["sleep_hours"],
        baselines["sleep_hours"]["mean"],
        baselines["sleep_hours"]["std"],
    )
    if current_wellness["sleep_hours"] < 6.5:
        alerts.append({
            "type": "critical",
            "metric": "Sleep",
            "message": f"Sleep <6.5 hrs — 1.7× injury risk (Milewski 2014)",
            "color": "#ef4444",
        })
    elif sleep_z < -2.0:
        alerts.append({
            "type": "warning",
            "metric": "Sleep",
            "message": f"Sleep {current_wellness['sleep_hours']:.1f} hrs is unusually low for this athlete (z={sleep_z:.1f}σ)",
            "color": "#f59e0b",
        })

    soreness_z = calculate_z_score(
        current_wellness["soreness"],
        baselines["soreness"]["mean"],
        baselines["soreness"]["std"],
    )
    if current_wellness["soreness"] > 7:
        alerts.append({
            "type": "warning",
            "metric": "Soreness",
            "message": f"Soreness >7 — requires monitoring (Hulin 2016)",
            "color": "#f59e0b",
        })
    elif soreness_z > 2.0:
        alerts.append({
            "type": "info",
            "metric": "Soreness",
            "message": f"Soreness {current_wellness['soreness']:.0f}/10 is unusually high for this athlete (z={soreness_z:.1f}σ)",
            "color": "#3b82f6",
        })

    return alerts
