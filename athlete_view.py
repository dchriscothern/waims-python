"""
Athlete-facing WAIMS view.
Privacy-safe summary for one athlete only, with a small supported voice/text Q&A.
"""

from __future__ import annotations

import json
from datetime import timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components


def _calc_readiness(row_dict: dict) -> float:
    sleep_hrs = row_dict.get("sleep_hours", 7.5)
    sleep_q = row_dict.get("sleep_quality", 7)
    sleep_s = min(15, (sleep_hrs / 8.0) * 10 + (sleep_q / 10) * 5)
    sore_s = ((10 - row_dict.get("soreness", 4)) / 10) * 10
    mood_s = (row_dict.get("mood", 7) / 10) * 5
    stress_s = ((10 - row_dict.get("stress", 4)) / 10) * 5
    cmj = row_dict.get("cmj_height_cm")
    pos = str(row_dict.get("position", "F"))
    bench = 38 if "G" in pos else (30 if "C" in pos else 34)
    cmj_s = min(15, (cmj / bench) * 15) if cmj and cmj > 0 else 11
    rsi = row_dict.get("rsi_modified")
    rsi_s = min(10, (rsi / 0.45) * 10) if rsi and rsi > 0 else 8
    sched_s = 10
    if row_dict.get("is_back_to_back", 0):
        sched_s -= 4
    if row_dict.get("days_rest", 3) <= 1:
        sched_s -= 2
    sched_s = max(0, sched_s)
    raw = sleep_s + sore_s + mood_s + stress_s + cmj_s + rsi_s + sched_s
    return round(min(100, raw * (100 / 70)), 1)


def _status_copy(score: float) -> tuple[str, str, str]:
    if score >= 80:
        return "READY", "#16a34a", "You look ready for normal training today."
    if score >= 60:
        return "MONITOR", "#d97706", "You can train today, but keep an eye on recovery signals."
    return "RECOVER", "#dc2626", "Today should lean recovery-first before full intensity."


def _build_answer_payload(player_row: dict, week_df: pd.DataFrame) -> dict:
    sleep_avg = round(float(week_df["sleep_hours"].mean()), 1) if len(week_df) else 0.0
    soreness_avg = round(float(week_df["soreness"].mean()), 1) if len(week_df) else 0.0
    stress_avg = round(float(week_df["stress"].mean()), 1) if len(week_df) else 0.0
    load_avg = round(float(week_df["total_daily_load"].mean()), 1) if "total_daily_load" in week_df.columns and len(week_df) else 0.0

    played_today = float(player_row.get("game_minutes", 0) or 0) > 0
    today_load = round(float(player_row.get("total_daily_load", 0) or 0), 1)
    score = float(player_row["readiness_score"])
    label, _, guidance = _status_copy(score)

    dnp_guidance = (
        "You did not play, so add 15–20 minutes of structured work after the game or next morning: "
        "controlled sprints, change-of-direction reps, or a short conditioning circuit. "
        "The goal is to maintain your load base so a sudden return to game minutes does not spike soft-tissue risk."
        if not played_today
        else "You played today. Prioritize cooldown, fluids, nutrition, and sleep so you bounce back for the next session."
    )

    return {
        "readiness_score": score,
        "readiness_label": label,
        "guidance": guidance,
        "sleep_hours": round(float(player_row.get("sleep_hours", 0) or 0), 1),
        "soreness": int(player_row.get("soreness", 0) or 0),
        "stress": int(player_row.get("stress", 0) or 0),
        "mood": int(player_row.get("mood", 0) or 0),
        "sleep_avg": sleep_avg,
        "soreness_avg": soreness_avg,
        "stress_avg": stress_avg,
        "load_avg": load_avg,
        "played_today": played_today,
        "today_load": today_load,
        "dnp_guidance": dnp_guidance,
    }


def _render_voice_box(payload: dict):
    payload_json = json.dumps(payload)
    components.html(
        f"""
        <style>
          body {{ font-family: Arial, sans-serif; margin: 0; padding: 0; }}
          #voiceShell {{
            padding-bottom: 6px;
          }}
          #askBtn {{
            background:#0f766e;color:white;border:none;border-radius:8px;
            padding:8px 16px;font-size:13px;font-weight:700;cursor:pointer;
          }}
          #queryBox {{
            display:none;width:100%;box-sizing:border-box;padding:8px 12px;border-radius:8px;
            border:1px solid #cbd5e1;font-size:13px;margin:8px 0 0;font-family:Arial,sans-serif;
          }}
          #answerBox {{
            display:none;background:#f8fafc;border-left:4px solid #0f766e;border-radius:0 8px 8px 0;
            padding:12px 16px;font-size:13px;color:#0f172a;margin-top:8px;line-height:1.6;
          }}
          #helperText {{
            font-size:11px;color:#94a3b8;font-style:italic;
          }}
        </style>
        <div id="voiceShell">
        <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
          <button id="askBtn" onclick="toggleVoice()">🎙 Ask</button>
          <span id="voiceStatus" style="font-size:11px;color:#64748b;"></span>
          <span id="helperText">
            Voice Preview · Chrome only · Tap Ask, speak, then tap again to stop
          </span>
        </div>
        <input id="queryBox" type="text" placeholder="Type your question and press Enter"
               onkeydown="if(event.key==='Enter') answerQuery(this.value)" />
        <div id="answerBox"></div>
        </div>
        <script>
          const DATA = {payload_json};
          let recognizing = false;
          let recognition;

          function resizeFrame(h) {{
            try {{ window.frameElement.style.height = h + 'px'; }} catch(e) {{}}
          }}

          function showTypedFallback(message) {{
            const status = document.getElementById('voiceStatus');
            status.innerHTML = message;
            status.style.color = '#d97706';
            const query = document.getElementById('queryBox');
            query.style.display = 'block';
            query.focus();
            resizeFrame(220);
          }}

          function answerQuery(q) {{
            q = q.toLowerCase().trim();
            const box = document.getElementById('answerBox');
            document.getElementById('queryBox').style.display = 'block';
            box.style.display = 'block';
            box.style.borderColor = '#0f766e';

            let html = '';
            if (q.includes('how am i') || q.includes('how do i') || q.includes('today')) {{
              html = '<b>Today:</b> ' + DATA.readiness_label + ' (' + DATA.readiness_score.toFixed(0) + '/100)<br>' + DATA.guidance;
            }} else if (q.includes('ready') || q.includes('train')) {{
              html = '<b>Training view:</b> ' + DATA.guidance;
            }} else if (q.includes('sleep')) {{
              html = '<b>Sleep:</b> ' + DATA.sleep_hours.toFixed(1) + ' hours last night.<br>'
                   + '7-day average: ' + DATA.sleep_avg.toFixed(1) + ' hours.';
            }} else if (q.includes('sore') || q.includes('body')) {{
              html = '<b>Soreness this week:</b> ' + DATA.soreness_avg.toFixed(1) + '/10 average.<br>'
                   + 'Today: ' + DATA.soreness + '/10.';
            }} else if (q.includes('stress')) {{
              html = '<b>Stress:</b> ' + DATA.stress + '/10 today.<br>'
                   + '7-day average: ' + DATA.stress_avg.toFixed(1) + '/10.';
            }} else if (q.includes("didn't play") || q.includes('did not play') || q.includes('dnp')) {{
              html = '<b>Load guidance:</b> ' + DATA.dnp_guidance;
            }} else {{
              html = 'Try: <b>"How am I doing today?"</b> · <b>"Am I ready to train?"</b> · '
                   + '<b>"How was my sleep?"</b> · <b>"How is my soreness this week?"</b> · '
                   + '<b>"What should I do if I didn\\'t play?"</b>';
            }}

            box.innerHTML = html;
            setTimeout(function() {{
              resizeFrame(Math.max(220, Math.min(document.body.scrollHeight + 26, 360)));
            }}, 50);
          }}

          function toggleVoice() {{
            if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {{
              showTypedFallback('Mic unavailable here — type your question below and press Enter.');
              return;
            }}
            if (recognizing) {{ recognition.stop(); return; }}

            const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
            recognition = new SR();
            recognition.lang = 'en-US';
            recognition.interimResults = false;
            recognition.maxAlternatives = 1;

            recognition.onstart = function() {{
              recognizing = true;
              document.getElementById('askBtn').style.background = '#dc2626';
              document.getElementById('askBtn').innerHTML = '🔴 Tap To Stop';
              document.getElementById('voiceStatus').innerHTML = 'Listening now — say your question, then tap again to stop.';
              document.getElementById('voiceStatus').style.color = '#64748b';
              resizeFrame(220);
            }};
            recognition.onresult = function(event) {{
              const t = event.results[0][0].transcript;
              const query = document.getElementById('queryBox');
              query.value = t;
              answerQuery(t);
            }};
            recognition.onerror = function() {{
              showTypedFallback('Mic blocked — type your question below and press Enter.');
            }};
            recognition.onend = function() {{
              recognizing = false;
              document.getElementById('askBtn').style.background = '#0f766e';
              document.getElementById('askBtn').innerHTML = '🎙 Ask';
              if (!document.getElementById('answerBox').innerHTML) {{
                document.getElementById('voiceStatus').innerHTML = '';
                resizeFrame(220);
              }}
            }};
            recognition.start();
          }}
        </script>
        """,
        height=220,
    )


def athlete_home_view(
    player_id: str,
    wellness_df: pd.DataFrame,
    players_df: pd.DataFrame,
    force_plate_df: pd.DataFrame,
    training_load_df: pd.DataFrame,
    end_date,
):
    athlete = players_df[players_df["player_id"] == player_id]
    if len(athlete) == 0:
        st.error("Athlete profile not found for this login.")
        return

    athlete_row = athlete.iloc[0]
    ref_date = pd.to_datetime(end_date)

    today_w = wellness_df[
        (wellness_df["player_id"] == player_id) &
        (pd.to_datetime(wellness_df["date"]) == ref_date)
    ]
    if len(today_w) == 0:
        st.info("No athlete data available for today.")
        return

    today = today_w.iloc[0].to_dict()
    today["position"] = athlete_row.get("position", "")

    today_fp = force_plate_df[
        (force_plate_df["player_id"] == player_id) &
        (pd.to_datetime(force_plate_df["date"]) == ref_date)
    ]
    if len(today_fp) > 0:
        today.update(today_fp.iloc[0].to_dict())

    today_load = training_load_df[
        (training_load_df["player_id"] == player_id) &
        (pd.to_datetime(training_load_df["date"]) == ref_date)
    ]
    if len(today_load) > 0:
        today.update(today_load.iloc[0].to_dict())

    today["readiness_score"] = _calc_readiness(today)
    label, color, guidance = _status_copy(today["readiness_score"])

    week_cutoff = ref_date - timedelta(days=6)
    week_wellness = wellness_df[
        (wellness_df["player_id"] == player_id) &
        (pd.to_datetime(wellness_df["date"]) >= week_cutoff)
    ].copy()
    week_load = training_load_df[
        (training_load_df["player_id"] == player_id) &
        (pd.to_datetime(training_load_df["date"]) >= week_cutoff)
    ][["player_id", "date", "total_daily_load", "game_minutes", "practice_minutes"]].copy()
    week_df = week_wellness.merge(week_load, on=["player_id", "date"], how="left")

    st.header("My Readiness")
    st.caption("Your athlete view shows only your own data. No teammate information appears here.")

    hero_left, hero_right = st.columns([1.5, 1])
    with hero_left:
        st.markdown(
            f'<div style="background:{color}12;border-left:4px solid {color};padding:16px 18px;'
            f'border-radius:0 10px 10px 0;margin-bottom:12px;">'
            f'<div style="font-size:11px;font-weight:700;letter-spacing:0.14em;text-transform:uppercase;color:{color};">Today</div>'
            f'<div style="font-size:30px;font-weight:800;color:#0f172a;margin:4px 0;">{label} · {today["readiness_score"]:.0f}/100</div>'
            f'<div style="font-size:14px;color:#334155;">{guidance}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with hero_right:
        st.metric("Sleep", f'{float(today.get("sleep_hours", 0)):.1f} hrs')
        st.metric("Soreness", f'{int(today.get("soreness", 0))}/10')
        st.metric("Stress", f'{int(today.get("stress", 0))}/10')

    st.markdown(
        '<div style="font-size:11px;font-weight:700;letter-spacing:0.18em;text-transform:uppercase;'
        'color:#94a3b8;margin:4px 0 6px 0;">Ask a Question</div>',
        unsafe_allow_html=True,
    )
    _render_voice_box(_build_answer_payload(today, week_df))

    st.markdown("<div style='margin-top:-8px;'></div>", unsafe_allow_html=True)
    card1, card2, card3 = st.columns(3)
    with card1:
        st.markdown("**This Week**")
        st.caption(f"Average sleep: {week_df['sleep_hours'].mean():.1f} hrs")
        st.caption(f"Average soreness: {week_df['soreness'].mean():.1f}/10")
    with card2:
        st.markdown("**Load View**")
        load_total = float(week_df["total_daily_load"].fillna(0).sum()) if "total_daily_load" in week_df.columns else 0.0
        st.caption(f"7-day load: {load_total:.0f} AU")
        st.caption(f"Today's load: {float(today.get('total_daily_load', 0) or 0):.0f} AU")
    with card3:
        st.markdown("**If You Didn't Play**")
        played = float(today.get("game_minutes", 0) or 0) > 0
        st.caption("Played today" if played else "Did not play today")
        st.caption("Keep some structured work in your week so return-to-play minutes do not become a sudden spike.")

    trend_col1, trend_col2 = st.columns(2)
    with trend_col1:
        sleep_fig = go.Figure()
        sleep_fig.add_trace(go.Scatter(
            x=pd.to_datetime(week_df["date"]),
            y=week_df["sleep_hours"],
            mode="lines+markers",
            line=dict(color="#2563eb", width=3),
            name="Sleep",
        ))
        sleep_fig.update_layout(height=260, margin=dict(l=10, r=10, t=30, b=10), title="Sleep Trend")
        st.plotly_chart(sleep_fig, width="stretch")
    with trend_col2:
        recovery_fig = go.Figure()
        recovery_fig.add_trace(go.Scatter(
            x=pd.to_datetime(week_df["date"]),
            y=week_df["soreness"],
            mode="lines+markers",
            line=dict(color="#d97706", width=3),
            name="Soreness",
        ))
        recovery_fig.add_trace(go.Scatter(
            x=pd.to_datetime(week_df["date"]),
            y=week_df["stress"],
            mode="lines+markers",
            line=dict(color="#dc2626", width=2),
            name="Stress",
        ))
        recovery_fig.update_layout(height=260, margin=dict(l=10, r=10, t=30, b=10), title="Soreness & Stress")
        st.plotly_chart(recovery_fig, width="stretch")
