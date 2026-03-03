"""
Improved Gauge Designs - Clean, Professional, No Emojis
Optimized for executive/professional presentation
"""

import streamlit as st
import plotly.graph_objects as go

def create_clean_speedometer(value, title, thresholds=[60, 80]):
    """Clean speedometer - professional design, no emojis"""
    value = max(0, min(100, float(value)))
    y_start, g_start = thresholds
    
    if value >= g_start:
        status_color = "#10b981"
        status_text = "READY"
    elif value >= y_start:
        status_color = "#f59e0b"
        status_text = "MONITOR"
    else:
        status_color = "#ef4444"
        status_text = "AT RISK"
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={'font': {'size': 48, 'color': status_color, 'family': 'Arial Black'}, 'suffix': ""},
        title={'text': f"<b>{title}</b><br><span style='font-size:14px; color:{status_color}'>{status_text}</span>", 'font': {'size': 16}},
        gauge={
            'shape': "angular",
            'axis': {'range': [0, 100], 'tickwidth': 2, 'tickcolor': "rgba(0,0,0,0.1)", 'tickvals': [0, 50, 100], 'tickfont': {'size': 12, 'color': '#6b7280'}},
            'bar': {'color': status_color, 'thickness': 0.35},
            'bgcolor': "white",
            'borderwidth': 0,
            'steps': [
                {'range': [0, y_start], 'color': 'rgba(239, 68, 68, 0.15)'},
                {'range': [y_start, g_start], 'color': 'rgba(245, 158, 11, 0.15)'},
                {'range': [g_start, 100], 'color': 'rgba(16, 185, 129, 0.15)'}
            ],
            'threshold': {'line': {'color': status_color, 'width': 8}, 'thickness': 0.85, 'value': value}
        }
    ))
    
    fig.update_layout(height=220, margin=dict(l=20, r=20, t=60, b=10), paper_bgcolor="white", font={'family': 'Arial'})
    return fig

def create_simple_battery(value, label, show_emoji=False):
    """Simplified horizontal bar - NO emojis"""
    if value >= 80:
        color, status = "#10b981", "GOOD"
    elif value >= 60:
        color, status = "#f59e0b", "OK"
    else:
        color, status = "#ef4444", "LOW"
    
    return f"""
    <div style="background:white;border-left:4px solid {color};padding:12px;margin:6px 0;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
            <span style="font-size:13px;font-weight:700;color:#1f2937;">{label}</span>
            <span style="font-size:14px;font-weight:800;color:{color};">{value:.0f}%</span>
        </div>
        <div style="background:#f3f4f6;height:24px;border-radius:4px;overflow:hidden;position:relative;">
            <div style="background:{color};height:100%;width:{value:.1f}%;transition:width 0.3s;"></div>
            <div style="position:absolute;top:50%;left:12px;transform:translateY(-50%);font-size:11px;font-weight:700;color:{'#065f46' if value>30 else '#6b7280'};">{status}</div>
        </div>
    </div>
    """

def create_player_card_compact(player_name, position, readiness_score, metrics, photo_url=None):
    """Clean player card - professional, no emojis"""
    if readiness_score >= 80:
        status_color, status_bg, status_text = "#10b981", "#d1fae5", "READY"
    elif readiness_score >= 60:
        status_color, status_bg, status_text = "#f59e0b", "#fef3c7", "MONITOR"
    else:
        status_color, status_bg, status_text = "#ef4444", "#fee2e2", "AT RISK"
    
    photo_html = f'<img src="{photo_url}" style="width:70px;height:70px;border-radius:50%;object-fit:cover;">' if photo_url else f'<div style="width:70px;height:70px;border-radius:50%;background:{status_color};display:flex;align-items:center;justify-content:center;color:white;font-size:18px;font-weight:700;">{player_name[:2].upper()}</div>'
    
    return f"""
    <div style="background:white;border-left:5px solid {status_color};padding:16px;margin:10px 0;box-shadow:0 1px 3px rgba(0,0,0,0.1);">
        <div style="display:flex;gap:16px;align-items:center;margin-bottom:14px;">
            {photo_html}
            <div style="flex:1;">
                <div style="font-size:17px;font-weight:800;color:#1f2937;margin-bottom:3px;">{player_name}</div>
                <div style="font-size:12px;color:#6b7280;margin-bottom:6px;">{position}</div>
                <div style="display:inline-block;background:{status_bg};color:{status_color};padding:3px 10px;border-radius:4px;font-size:12px;font-weight:700;">{status_text}</div>
            </div>
            <div style="text-align:center;">
                <div style="font-size:42px;font-weight:800;color:{status_color};line-height:1;">{readiness_score:.0f}</div>
                <div style="font-size:10px;color:#6b7280;font-weight:600;margin-top:3px;">READINESS</div>
            </div>
        </div>
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;">
            {_create_mini_metric_clean("Sleep", metrics['sleep'])}
            {_create_mini_metric_clean("Physical", metrics['physical'])}
            {_create_mini_metric_clean("Mental", metrics['mental'])}
            {_create_mini_metric_clean("Stress", metrics['stress'])}
        </div>
    </div>
    """

def _create_mini_metric_clean(label, value):
    """Helper for mini metric bars - NO EMOJIS"""
    color = "#10b981" if value >= 80 else "#f59e0b" if value >= 60 else "#ef4444"
    return f"""
    <div style="text-align:center;">
        <div style="font-size:10px;color:#6b7280;margin-bottom:4px;font-weight:600;">{label}</div>
        <div style="background:#f3f4f6;height:20px;border-radius:4px;overflow:hidden;border:1px solid {color}40;">
            <div style="background:{color};height:100%;width:{value:.0f}%;transition:width 0.3s;"></div>
        </div>
        <div style="font-size:11px;font-weight:700;color:{color};margin-top:3px;">{value:.0f}</div>
    </div>
    """

def create_recommendation_box(readiness_score, context="practice"):
    """Clean recommendation box - no emojis"""
    if readiness_score >= 80:
        border_color, bg_color = "#10b981", "#d1fae5"
        title, text = "Full Training Cleared", f"Athlete shows optimal readiness for {context}. No modifications needed."
    elif readiness_score >= 60:
        border_color, bg_color = "#f59e0b", "#fef3c7"
        title, text = "Monitor Closely", f"Some readiness concerns. Consider lighter intensity for {context}."
    else:
        border_color, bg_color = "#ef4444", "#fee2e2"
        title, text = "Volume Reduction Recommended", f"Significant readiness concerns. Recommend 50% volume reduction for {context}."
    
    return f"""
    <div style="background:{bg_color};border-left:6px solid {border_color};padding:14px 18px;margin:14px 0;">
        <div style="font-size:15px;font-weight:800;color:#1f2937;margin-bottom:6px;">{title}</div>
        <div style="font-size:13px;color:#374151;line-height:1.5;">{text}</div>
    </div>
    """
