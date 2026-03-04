"""
WAIMS — Correlation Explorer
Surfaces hidden cross-metric relationships.

Sections:
  1. Correlation Heatmap        — Pearson r across all metrics
  2. Top Hidden Correlations    — ranked, annotated, research-linked
  3. Lag Analysis               — does yesterday's metric predict today's outcome?
  4. Conditional Risk Table     — P(injury | metric flagged)
  5. Per-Player Breakdown       — individual correlation fingerprints
  6. Model Feature Audit        — what the RF model actually learned
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from scipy import stats


# ─────────────────────────────────────────────────────────────────────────────
# DATA PREPARATION
# ─────────────────────────────────────────────────────────────────────────────

def _build_master(wellness, training_load, force_plate, acwr, injuries, players):
    """
    Merge all tables into a single flat daily frame.
    Adds injury_within_7days label, GPS columns if present.
    """
    df = wellness.copy()
    df = df.merge(
        training_load[["player_id", "date", "practice_minutes", "practice_rpe",
                        "total_daily_load", "game_minutes"] +
                       ([c for c in ["player_load", "accel_count", "decel_count",
                                     "total_distance_km", "hsr_distance_m"]
                         if c in training_load.columns])],
        on=["player_id", "date"], how="left",
    )
    df = df.merge(
        acwr[["player_id", "date", "acwr"]],
        on=["player_id", "date"], how="left",
    )

    # Forward-fill force plate (weekly tests) — robust to missing columns
    fp_cols = ["player_id", "date", "cmj_height_cm", "rsi_modified"]
    if "asymmetry_percent" in force_plate.columns:
        fp_cols.append("asymmetry_percent")

    fp_daily = (
        df[["player_id", "date"]]
        .merge(force_plate[fp_cols], on=["player_id", "date"], how="left")
        .sort_values(["player_id", "date"])
    )

    # Ensure column exists even if force_plate doesn't have it
    if "asymmetry_percent" not in fp_daily.columns:
        fp_daily["asymmetry_percent"] = np.nan

    fill_cols = ["cmj_height_cm", "rsi_modified", "asymmetry_percent"]
    fp_daily[fill_cols] = fp_daily.groupby("player_id")[fill_cols].ffill()

    # Merge back by keys (avoids index alignment issues)
    df = df.merge(fp_daily[["player_id", "date"] + fill_cols], on=["player_id", "date"], how="left")
    # Injury label
    df["injured_within_7days"] = 0
    if len(injuries) > 0:
        for _, inj in injuries.iterrows():
            inj_date = pd.Timestamp(inj["injury_date"])
            mask = (
                (df["player_id"] == inj["player_id"]) &
                (df["date"] >= inj_date - pd.Timedelta(days=7)) &
                (df["date"] <= inj_date)
            )
            df.loc[mask, "injured_within_7days"] = 1

    # Per-player z-scores
    for col, min_std in [
        ("sleep_hours", 0.3), ("soreness", 0.5), ("cmj_height_cm", 0.5),
        ("rsi_modified", 0.01), ("acwr", 0.05),
    ]:
        if col not in df.columns:
            continue
        df[f"{col}_z"] = df.groupby("player_id")[col].transform(
            lambda x: (x - x.expanding(5).mean().shift(1)) /
                      x.expanding(5).std().shift(1).clip(lower=min_std)
        ).fillna(0)

    # GPS z-scores
    for col, min_std in [("player_load", 10), ("accel_count", 2), ("decel_count", 2)]:
        if col not in df.columns:
            continue
        df[f"{col}_z"] = df.groupby("player_id")[col].transform(
            lambda x: (x - x.expanding(5).mean().shift(1)) /
                      x.expanding(5).std().shift(1).clip(lower=min_std)
        ).fillna(0)

    df = df.merge(players[["player_id", "name", "position"]], on="player_id", how="left")
    df = df.sort_values(["player_id", "date"])

    return df


METRIC_LABELS = {
    "sleep_hours":       "Sleep (hrs)",
    "sleep_quality":     "Sleep Quality",
    "soreness":          "Soreness",
    "stress":            "Stress",
    "mood":              "Mood",
    "practice_minutes":  "Practice Min",
    "practice_rpe":      "Session RPE",
    "total_daily_load":  "Daily Load",
    "game_minutes":      "Game Min",
    "acwr":              "ACWR",
    "cmj_height_cm":     "CMJ Height",
    "rsi_modified":      "RSI-Mod",
    "asymmetry_percent": "Asymmetry %",
    "player_load":       "Player Load",
    "accel_count":       "Accel Count",
    "decel_count":       "Decel Count",
    "total_distance_km": "Distance (km)",
    "hsr_distance_m":    "HSR (m)",
    "injured_within_7days": "Injury (7d)",
}

RESEARCH_NOTES = {
    ("sleep_hours", "soreness"):           "Sleep deprivation delays muscle recovery — Fullagar et al. 2015",
    ("sleep_hours", "cmj_height_cm"):      "Sleep <6h reduces explosive power output — Blumert et al. 2007",
    ("acwr", "injured_within_7days"):      "ACWR >1.5 = 2.4× injury risk — Gabbett 2016",
    ("cmj_height_cm", "injured_within_7days"): "CMJ drop = neuromuscular fatigue before injury — Gathercole 2015",
    ("soreness", "rsi_modified"):          "High soreness degrades reactive strength — Twist & Eston 2005",
    ("player_load", "accel_count"):        "Correlated in healthy state; divergence = fatigue signal — Reardon 2017",
    ("accel_count", "injured_within_7days"): "Accel drop precedes soft-tissue injury — Jaspers et al. 2018",
    ("sleep_hours", "mood"):               "Sleep architecture directly regulates mood — Leproult & Van Cauter 2010",
    ("stress", "soreness"):                "Psychological stress elevates perceived soreness — Haddad 2013",
    ("rsi_modified", "injured_within_7days"): "RSI-Mod sensitivity for overreach — Gathercole et al. 2015",
}


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1: HEATMAP
# ─────────────────────────────────────────────────────────────────────────────

def _heatmap_section(df):
    st.markdown("### 🔥 Correlation Heatmap")
    st.caption(
        "Pearson r across all metrics. Values close to ±1 are strong. "
        "Dark red = strong positive · Dark blue = strong negative · "
        "**Injury column** shows what actually predicts injury within 7 days in this dataset."
    )

    avail = [c for c in METRIC_LABELS if c in df.columns]
    corr  = df[avail].corr()

    # Rename for display
    labels = [METRIC_LABELS.get(c, c) for c in avail]
    z      = corr.values

    fig = go.Figure(go.Heatmap(
        z=z, x=labels, y=labels,
        colorscale="RdBu_r", zmid=0, zmin=-1, zmax=1,
        text=[[f"{v:.2f}" for v in row] for row in z],
        texttemplate="%{text}",
        textfont={"size": 8},
        hovertemplate="<b>%{y}</b> vs <b>%{x}</b><br>r = %{z:.3f}<extra></extra>",
    ))
    fig.update_layout(
        height=520,
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis=dict(tickfont=dict(size=9), tickangle=-45),
        yaxis=dict(tickfont=dict(size=9)),
    )
    st.plotly_chart(fig, use_container_width=True)

    return corr, avail


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2: TOP HIDDEN CORRELATIONS
# ─────────────────────────────────────────────────────────────────────────────

def _top_correlations_section(df, corr, avail, top_n=10):
    st.markdown("### 🔍 Top Hidden Correlations")
    st.caption("Ranked by absolute correlation strength. Excludes self-correlations and obvious pairs.")

    pairs = []
    cols_arr = list(corr.columns)
    for i, c1 in enumerate(cols_arr):
        for c2 in cols_arr[i+1:]:
            r = corr.loc[c1, c2]
            if abs(r) < 0.05:
                continue
            # p-value
            try:
                vals = df[[c1, c2]].dropna()
                _, p = stats.pearsonr(vals[c1], vals[c2])
            except Exception:
                p = 1.0
            pairs.append({
                "metric_a":  c1,
                "metric_b":  c2,
                "label_a":   METRIC_LABELS.get(c1, c1),
                "label_b":   METRIC_LABELS.get(c2, c2),
                "r":         r,
                "abs_r":     abs(r),
                "p":         p,
                "direction": "↑ positive" if r > 0 else "↓ negative",
            })

    pairs.sort(key=lambda x: x["abs_r"], reverse=True)
    top = pairs[:top_n]

    for rank, p in enumerate(top, 1):
        key1 = (p["metric_a"], p["metric_b"])
        key2 = (p["metric_b"], p["metric_a"])
        note = RESEARCH_NOTES.get(key1) or RESEARCH_NOTES.get(key2, "")

        strength = "Strong" if p["abs_r"] > 0.6 else ("Moderate" if p["abs_r"] > 0.3 else "Weak")
        s_color  = "#dc2626" if p["abs_r"] > 0.6 else ("#d97706" if p["abs_r"] > 0.3 else "#16a34a")
        sig_tag  = "✓ Significant" if p["p"] < 0.05 else "~ Marginal"
        dir_col  = "#dc2626" if p["r"] < 0 else "#16a34a"

        st.markdown(
            f"""
            <div style="background:#fff; border:1px solid #e2e8f0; border-radius:10px;
                padding:14px 18px; margin-bottom:8px; display:flex;
                align-items:center; gap:16px;">
                <div style="font-size:22px; font-weight:900; color:#94a3b8;
                    font-family:monospace; min-width:32px;">#{rank}</div>
                <div style="flex:1;">
                    <div style="font-weight:700; font-size:14px; color:#1e293b;">
                        {p['label_a']}
                        <span style="color:#94a3b8; font-weight:400;"> vs </span>
                        {p['label_b']}
                    </div>
                    {f'<div style="font-size:11px; color:#6366f1; margin-top:2px;">📚 {note}</div>' if note else ''}
                </div>
                <div style="text-align:right; min-width:120px;">
                    <div style="font-size:22px; font-weight:800; color:{s_color};
                        font-family:monospace;">r = {p['r']:+.3f}</div>
                    <div style="font-size:11px; color:#64748b;">
                        {strength} · <span style="color:{dir_col};">{p['direction']}</span>
                        · {sig_tag}
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3: LAG ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

def _lag_analysis_section(df):
    st.markdown("### ⏱ Lag Analysis")
    st.caption(
        "Does a metric from N days ago predict today's outcome better than today's value? "
        "This reveals **temporal structure** — e.g. sleep 2 nights ago may predict CMJ drop "
        "more strongly than last night's sleep."
    )

    PREDICTORS = ["sleep_hours", "soreness", "stress", "player_load", "accel_count"]
    OUTCOMES   = ["cmj_height_cm", "rsi_modified", "soreness", "injured_within_7days"]
    LAGS       = [0, 1, 2, 3, 5, 7]

    predictor_opts = [c for c in PREDICTORS if c in df.columns]
    outcome_opts   = [c for c in OUTCOMES   if c in df.columns]

    c1, c2 = st.columns(2)
    pred_sel = c1.selectbox(
        "Predictor (X)", predictor_opts,
        format_func=lambda x: METRIC_LABELS.get(x, x),
    )
    out_sel = c2.selectbox(
        "Outcome (Y)", outcome_opts,
        format_func=lambda x: METRIC_LABELS.get(x, x),
        index=min(2, len(outcome_opts)-1),
    )

    lag_results = []
    for lag in LAGS:
        tmp = df[["player_id", "date", pred_sel, out_sel]].copy().dropna()
        tmp = tmp.sort_values(["player_id", "date"])
        tmp["pred_lagged"] = tmp.groupby("player_id")[pred_sel].shift(lag)
        tmp2 = tmp[["pred_lagged", out_sel]].dropna()
        if len(tmp2) < 10:
            continue
        try:
            r, p = stats.pearsonr(tmp2["pred_lagged"], tmp2[out_sel])
        except Exception:
            r, p = 0, 1
        lag_results.append({"lag": lag, "r": r, "abs_r": abs(r), "p": p})

    if lag_results:
        lag_df = pd.DataFrame(lag_results)
        colors = [
            "#16a34a" if abs(r) == lag_df["abs_r"].max() else "#94a3b8"
            for r in lag_df["abs_r"]
        ]
        fig = go.Figure(go.Bar(
            x=[f"{l}d" for l in lag_df["lag"]],
            y=lag_df["r"],
            marker_color=colors,
            text=[f"r={v:+.3f}" for v in lag_df["r"]],
            textposition="outside",
            hovertemplate="Lag %{x}: r = %{y:.3f}<extra></extra>",
        ))
        fig.update_layout(
            title=f"{METRIC_LABELS.get(pred_sel, pred_sel)} (lagged) → {METRIC_LABELS.get(out_sel, out_sel)}",
            height=300,
            yaxis=dict(title="Pearson r", zeroline=True, zerolinecolor="#e2e8f0"),
            xaxis=dict(title="Days Prior"),
            margin=dict(l=10, r=10, t=50, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)

        best = lag_df.loc[lag_df["abs_r"].idxmax()]
        lag_desc = "same day" if best["lag"] == 0 else f"{int(best['lag'])} day(s) prior"
        direction = "positively" if best["r"] > 0 else "negatively"
        st.info(
            f"**Strongest signal:** {METRIC_LABELS.get(pred_sel, pred_sel)} from **{lag_desc}** "
            f"correlates most {direction} with {METRIC_LABELS.get(out_sel, out_sel)} "
            f"(r = {best['r']:+.3f}{'  · statistically significant' if best['p'] < 0.05 else ''})"
        )
    else:
        st.warning("Insufficient data for lag analysis.")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4: CONDITIONAL RISK TABLE
# ─────────────────────────────────────────────────────────────────────────────

def _conditional_risk_section(df):
    st.markdown("### 🎯 Conditional Injury Risk")
    st.caption(
        "In this dataset: when a metric is flagged, what % of those athlete-days "
        "had an injury within the next 7 days? Compare to the **baseline rate** to see "
        "how much each flag actually elevates risk."
    )

    if "injured_within_7days" not in df.columns:
        st.info("No injury data available.")
        return

    total       = len(df)
    base_rate   = df["injured_within_7days"].mean() * 100

    FLAG_DEFS = [
        ("sleep_hours",       "lt", 6.5,  "Sleep < 6.5 hrs"),
        ("soreness",          "gt", 7.0,  "Soreness > 7/10"),
        ("stress",            "gt", 7.0,  "Stress > 7/10"),
        ("acwr",              "gt", 1.5,  "ACWR > 1.5"),
        ("acwr",              "lt", 0.8,  "ACWR < 0.8 (detraining)"),
        ("cmj_height_cm_z",   "lt", -1.5, "CMJ > 1.5σ below baseline"),
        ("rsi_modified_z",    "lt", -1.5, "RSI > 1.5σ below baseline"),
        ("player_load_z",     "lt", -1.5, "Player Load > 1.5σ below baseline"),
        ("accel_count_z",     "lt", -1.5, "Accel Count > 1.5σ below baseline"),
        ("mood",              "lt", 4.0,  "Mood < 4/10"),
    ]

    risk_rows = []
    for col, op, threshold, label in FLAG_DEFS:
        if col not in df.columns:
            continue
        flagged = df[df[col] < threshold] if op == "lt" else df[df[col] > threshold]
        n_flagged = len(flagged)
        if n_flagged < 5:
            continue
        risk_rate = flagged["injured_within_7days"].mean() * 100
        rel_risk  = risk_rate / base_rate if base_rate > 0 else 1.0
        risk_rows.append({
            "Flag":           label,
            "n_flagged":      n_flagged,
            "risk_pct":       risk_rate,
            "base_pct":       base_rate,
            "rel_risk":       rel_risk,
        })

    if not risk_rows:
        st.info("Not enough injury events to compute conditional risk (need more data).")
        return

    risk_df = pd.DataFrame(risk_rows).sort_values("rel_risk", ascending=False)

    # Chart
    bar_colors = [
        "#dc2626" if rr >= 2.0 else ("#f59e0b" if rr >= 1.3 else "#94a3b8")
        for rr in risk_df["rel_risk"]
    ]
    fig = go.Figure(go.Bar(
        x=risk_df["Flag"],
        y=risk_df["rel_risk"],
        marker_color=bar_colors,
        text=[f"{v:.1f}×" for v in risk_df["rel_risk"]],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>Relative risk: %{y:.2f}×<extra></extra>",
    ))
    fig.add_hline(y=1.0, line_dash="dash", line_color="#64748b",
                  annotation_text="Baseline (1.0×)", annotation_position="right")
    fig.update_layout(
        title=f"Relative Injury Risk When Flagged (baseline rate = {base_rate:.1f}%)",
        height=340,
        yaxis=dict(title="Relative Risk (×)", range=[0, risk_df["rel_risk"].max() * 1.25]),
        xaxis=dict(tickangle=-30),
        margin=dict(l=10, r=10, t=50, b=80),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Table
    display = risk_df.rename(columns={
        "n_flagged": "Days Flagged",
        "risk_pct":  "Risk % When Flagged",
        "base_pct":  "Baseline Risk %",
        "rel_risk":  "Relative Risk",
    })
    display["Risk % When Flagged"] = display["Risk % When Flagged"].apply(lambda x: f"{x:.1f}%")
    display["Baseline Risk %"]     = display["Baseline Risk %"].apply(lambda x: f"{x:.1f}%")
    display["Relative Risk"]       = display["Relative Risk"].apply(lambda x: f"{x:.2f}×")
    st.dataframe(display[["Flag", "Days Flagged", "Risk % When Flagged",
                           "Baseline Risk %", "Relative Risk"]],
                 use_container_width=True, hide_index=True)

    st.caption(
        "⚠️ Based on synthetic data — real-world rates will differ. "
        "Purpose is to demonstrate methodology for a sports science presentation."
    )


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5: PER-PLAYER BREAKDOWN
# ─────────────────────────────────────────────────────────────────────────────

def _per_player_section(df, players):
    st.markdown("### 👤 Per-Player Correlation Fingerprints")
    st.caption(
        "Every athlete responds differently. "
        "This shows each player's personal correlation between sleep and next-day soreness — "
        "a simple but powerful individual metric."
    )

    results = []
    for pid in players["player_id"].unique():
        p_df  = df[df["player_id"] == pid].sort_values("date").copy()
        name  = players.loc[players["player_id"] == pid, "name"].values[0]
        pos   = players.loc[players["player_id"] == pid, "position"].values[0]

        p_df["soreness_next"] = p_df["soreness"].shift(-1)
        tmp = p_df[["sleep_hours", "soreness_next"]].dropna()
        if len(tmp) < 10:
            continue
        try:
            r, p_val = stats.pearsonr(tmp["sleep_hours"], tmp["soreness_next"])
        except Exception:
            r, p_val = 0, 1

        # Also: CMJ vs soreness same day
        cmj_sor = p_df[["cmj_height_cm", "soreness"]].dropna()
        r_cmj = 0
        if len(cmj_sor) >= 5:
            try:
                r_cmj, _ = stats.pearsonr(cmj_sor["cmj_height_cm"], cmj_sor["soreness"])
            except Exception:
                pass

        results.append({
            "name":       name,
            "pos":        pos,
            "r_sleep_sor": round(r, 3),
            "r_cmj_sor":   round(r_cmj, 3),
            "n_days":      len(tmp),
            "sig":         p_val < 0.05,
        })

    if not results:
        st.info("Not enough per-player data.")
        return

    r_df = pd.DataFrame(results).sort_values("r_sleep_sor")

    fig = go.Figure(go.Bar(
        x=r_df["name"],
        y=r_df["r_sleep_sor"],
        marker_color=[
            "#16a34a" if r < -0.3 else ("#f59e0b" if r < 0 else "#94a3b8")
            for r in r_df["r_sleep_sor"]
        ],
        text=[f"{v:+.2f}" for v in r_df["r_sleep_sor"]],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>r = %{y:.3f}<extra></extra>",
    ))
    fig.add_hline(y=0, line_color="#e2e8f0")
    fig.update_layout(
        title="Sleep → Next-Day Soreness (per player, r value)",
        height=300,
        yaxis=dict(title="Pearson r", range=[
            min(-0.1, r_df["r_sleep_sor"].min() * 1.3),
            max(0.1,  r_df["r_sleep_sor"].max() * 1.3),
        ]),
        xaxis=dict(tickangle=-30),
        margin=dict(l=10, r=10, t=50, b=80),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.caption(
        "**Negative r = expected (healthier pattern):** more sleep → less next-day soreness.  "
        "Players with near-zero or positive r may have other confounders (high game load, injury history)."
    )

    # CMJ vs soreness scatter per player
    st.markdown("#### Scatter: CMJ vs Soreness (all players)")
    scatter_data = df[["cmj_height_cm", "soreness", "name", "position"]].dropna()
    if len(scatter_data) > 20:
        fig2 = px.scatter(
            scatter_data, x="cmj_height_cm", y="soreness",
            color="position", hover_data=["name"],
            trendline="ols",
            labels={
                "cmj_height_cm": "CMJ Height (cm)",
                "soreness":      "Soreness (0–10)",
            },
            title="CMJ vs Soreness — Position Breakdown",
        )
        fig2.update_layout(height=320, margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig2, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 6: MODEL FEATURE AUDIT
# ─────────────────────────────────────────────────────────────────────────────

def _model_audit_section():
    st.markdown("### 🤖 ML Model Feature Audit")
    st.caption(
        "What did the Random Forest actually learn? Feature importances show which "
        "signals the model weighted most when predicting injury within 7 days. "
        "GPS z-scores appear here because of the lag structure in the training data."
    )

    try:
        import pickle
        with open("models/injury_risk_model.pkl", "rb") as f:
            bundle = pickle.load(f)
        model = bundle["model"]
        feats = bundle["feature_cols"]

        imp_df = (
            pd.DataFrame({"feature": feats, "importance": model.feature_importances_})
            .sort_values("importance", ascending=True)
            .tail(15)
        )

        # Map to readable labels
        imp_df["label"] = imp_df["feature"].apply(
            lambda x: METRIC_LABELS.get(x.replace("_zscore","").replace("_7day_avg","").replace("flag_","").replace("_drop","").replace("_floor","").replace("_ceil","").replace("_spike",""), x)
            + (" (z-score)" if "_zscore" in x else "")
            + (" (7d avg)"  if "_7day_avg" in x else "")
            + (" (flag)"    if x.startswith("flag_") else "")
        )

        bar_colors = [
            "#dc2626" if v > 0.06 else ("#f59e0b" if v > 0.03 else "#94a3b8")
            for v in imp_df["importance"]
        ]

        fig = go.Figure(go.Bar(
            x=imp_df["importance"],
            y=imp_df["label"],
            orientation="h",
            marker_color=bar_colors,
            text=[f"{v:.4f}" for v in imp_df["importance"]],
            textposition="outside",
        ))
        fig.update_layout(
            title="Top 15 Features by Importance",
            height=450,
            xaxis=dict(title="Importance Score"),
            margin=dict(l=10, r=60, t=50, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)

        # GPS vs wellness comparison
        gps_imp   = sum(v for f, v in zip(feats, model.feature_importances_) if "load" in f or "accel" in f or "decel" in f)
        well_imp  = sum(v for f, v in zip(feats, model.feature_importances_) if f in ("sleep_hours","soreness","stress","mood") or f.endswith("_zscore") and not any(g in f for g in ["load","accel","decel","cmj","rsi"]))
        fp_imp    = sum(v for f, v in zip(feats, model.feature_importances_) if "cmj" in f or "rsi" in f)

        c1, c2, c3 = st.columns(3)
        c1.metric("Wellness signals", f"{well_imp*100:.1f}%", "of total importance")
        c2.metric("GPS signals",      f"{gps_imp*100:.1f}%",  "player load + accels/decels")
        c3.metric("Force plate",      f"{fp_imp*100:.1f}%",   "CMJ + RSI")

    except FileNotFoundError:
        st.warning("No trained model found. Run `python train_models.py` first.")
    except Exception as e:
        st.error(f"Could not load model: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def correlation_explorer_tab(wellness, training_load, force_plate, acwr, injuries, players):
    st.header("🔬 Correlation Explorer")
    st.markdown(
        "Surfaces hidden relationships between monitoring signals. "
        "Use this to identify which metrics predict injury, fatigue, and readiness "
        "in **your specific dataset** — not just the published literature."
    )

    with st.spinner("Building master dataset..."):
        df = _build_master(wellness, training_load, force_plate, acwr, injuries, players)

    total_records = len(df)
    n_players     = df["player_id"].nunique()
    date_range    = f"{df['date'].min().strftime('%b %d')} – {df['date'].max().strftime('%b %d, %Y')}"
    injury_pct    = df["injured_within_7days"].mean() * 100
    has_gps       = "player_load" in df.columns

    # Dataset summary bar
    st.markdown(
        f"""
        <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px;
            padding:14px 20px; display:flex; gap:32px; margin-bottom:20px; flex-wrap:wrap;">
            <div><span style="font-size:11px;color:#64748b;font-weight:600;">RECORDS</span>
                <div style="font-size:20px;font-weight:800;color:#1e293b;font-family:monospace;">{total_records:,}</div></div>
            <div><span style="font-size:11px;color:#64748b;font-weight:600;">ATHLETES</span>
                <div style="font-size:20px;font-weight:800;color:#1e293b;font-family:monospace;">{n_players}</div></div>
            <div><span style="font-size:11px;color:#64748b;font-weight:600;">DATE RANGE</span>
                <div style="font-size:20px;font-weight:800;color:#1e293b;font-family:monospace;">{date_range}</div></div>
            <div><span style="font-size:11px;color:#64748b;font-weight:600;">INJURY RATE</span>
                <div style="font-size:20px;font-weight:800;color:#dc2626;font-family:monospace;">{injury_pct:.1f}%</div></div>
            <div><span style="font-size:11px;color:#64748b;font-weight:600;">GPS DATA</span>
                <div style="font-size:20px;font-weight:800;color:{'#16a34a' if has_gps else '#dc2626'};font-family:monospace;">
                {'✓ Included' if has_gps else '✗ Missing'}</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Section tabs
    sec = st.radio(
        "Section",
        ["Heatmap", "Top Correlations", "Lag Analysis", "Conditional Risk", "Per-Player", "Model Audit"],
        horizontal=True,
    )

    st.markdown("---")

    if sec == "Heatmap":
        corr, avail = _heatmap_section(df)

    elif sec == "Top Correlations":
        avail = [c for c in METRIC_LABELS if c in df.columns]
        corr  = df[avail].corr()
        _top_correlations_section(df, corr, avail)

    elif sec == "Lag Analysis":
        _lag_analysis_section(df)

    elif sec == "Conditional Risk":
        _conditional_risk_section(df)

    elif sec == "Per-Player":
        _per_player_section(df, players)

    elif sec == "Model Audit":
        _model_audit_section()
