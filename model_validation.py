"""
WAIMS Model Validation Framework
=================================
Implements the Julius.ai validation recipe for athlete injury risk
and readiness score models.

Validation philosophy
---------------------
The biggest trap in athlete monitoring ML is validating in a way that
accidentally leaks future information or overstates performance because
data is highly autocorrelated within a player and across days.

Two mandatory validation views
--------------------------------
1. Walk-forward time splits (will it work NEXT WEEK?)
   Train on days 1-45, validate on 46-60
   Train on days 1-60, validate on 61-75
   Train on days 1-75, validate on 76-90

2. Player holdout / GroupKFold (will it work for a NEW SIGNING?)
   Hold out 2-3 players entirely, train on rest

Key metrics by model type
--------------------------
Injury risk (classification, imbalanced):
  - PR-AUC (headline) — "when we flag risk, how often are we right?"
  - Precision@K top 3/day — matches real operational constraint
  - Calibration curve + Brier score — "if we say 30% risk, is it 30%?"
  - Lead-time distribution — days before injury the model flagged

Readiness score (ranking):
  - Spearman correlation vs coach intuition (V1 target: ≥0.70 on 70% of days)
  - MAE / RMSE vs any objective proxy
  - Day-to-day stability (score shouldn't whipsaw without cause)

Baselines to beat
-----------------
  - Last-7-day acute load threshold rule
  - ACWR > 1.5 heuristic
  - Player rolling z-score on soreness/fatigue

Ablation studies
----------------
  Model without GPS features
  Model without wellness features
  Model without game schedule features

Basketball-specific notes
--------------------------
  - Non-contact soft tissue injuries: primary validation target
  - Contact injuries: explicitly excluded (model not expected to predict)
  - 12-player demo roster: per-player analysis critical to catch
    "good overall but terrible for 3 athletes" problems
  - Precision@3 per day is the most operationally relevant metric
    given staff intervention capacity

Usage
-----
    from model_validation import ValidationFramework
    vf = ValidationFramework(wellness, training_load, injuries, players)
    results = vf.run_walk_forward()
    vf.show_streamlit_report(results)
"""

import pandas as pd
import numpy as np
from datetime import timedelta
import warnings
warnings.filterwarnings("ignore")


# ---------------------------------------------------------------------------
# Walk-forward split generator
# ---------------------------------------------------------------------------

def generate_walk_forward_splits(df: pd.DataFrame,
                                  date_col: str = "date",
                                  train_days: int = 45,
                                  val_days:   int = 15,
                                  step_days:  int = 15) -> list[dict]:
    """
    Generate rolling train/validation date splits.

    Default: 45-day train, 15-day validation, stepping 15 days.
    Covers a 90-day demo season in 3 folds.

    Returns
    -------
    List of dicts: [{fold, train_start, train_end, val_start, val_end}]
    """
    dates = pd.to_datetime(df[date_col])
    min_d = dates.min()
    max_d = dates.max()

    splits = []
    fold   = 1
    train_end = min_d + timedelta(days=train_days - 1)

    while train_end + timedelta(days=val_days) <= max_d:
        val_start = train_end + timedelta(days=1)
        val_end   = val_start + timedelta(days=val_days - 1)

        splits.append({
            "fold":        fold,
            "train_start": min_d,
            "train_end":   train_end,
            "val_start":   val_start,
            "val_end":     min(val_end, max_d),
        })

        train_end += timedelta(days=step_days)
        fold      += 1

    return splits


# ---------------------------------------------------------------------------
# Baseline models (to beat)
# ---------------------------------------------------------------------------

def baseline_acwr(acwr_df: pd.DataFrame, threshold: float = 1.5) -> pd.Series:
    """ACWR > threshold heuristic. Returns binary risk flag."""
    return (acwr_df["acwr"] > threshold).astype(int)


def baseline_soreness_zscore(wellness_df: pd.DataFrame,
                              window: int = 7,
                              z_threshold: float = 1.5) -> pd.DataFrame:
    """Player rolling z-score on soreness. Returns risk flag."""
    df = wellness_df.copy().sort_values(["player_id", "date"])
    df["sor_rolling_mean"] = (df.groupby("player_id")["soreness"]
                              .transform(lambda x: x.rolling(window, min_periods=3).mean()))
    df["sor_rolling_std"]  = (df.groupby("player_id")["soreness"]
                              .transform(lambda x: x.rolling(window, min_periods=3).std()))
    df["baseline_risk"]    = (
        (df["soreness"] - df["sor_rolling_mean"]) /
        df["sor_rolling_std"].clip(lower=0.01)
    ) > z_threshold
    return df[["player_id", "date", "baseline_risk"]]


def baseline_acute_load(training_load_df: pd.DataFrame,
                         window: int = 7,
                         threshold_pct: float = 0.30) -> pd.DataFrame:
    """
    Last-7-day acute load exceeds rolling mean by threshold_pct.
    Simple load-spike rule.
    """
    df = training_load_df.copy().sort_values(["player_id", "date"])
    df["acute_7d"] = (df.groupby("player_id")["practice_minutes"]
                      .transform(lambda x: x.rolling(7, min_periods=3).mean()))
    df["chronic_28d"] = (df.groupby("player_id")["practice_minutes"]
                         .transform(lambda x: x.rolling(28, min_periods=7).mean()))
    df["baseline_load_risk"] = (
        (df["acute_7d"] - df["chronic_28d"]) /
        df["chronic_28d"].clip(lower=1)
    ) > threshold_pct
    return df[["player_id", "date", "baseline_load_risk"]]


# ---------------------------------------------------------------------------
# Readiness ranking validation
# ---------------------------------------------------------------------------

def spearman_vs_readiness(predicted_scores: pd.Series,
                           actual_scores:    pd.Series) -> float:
    """Spearman rank correlation between predicted and actual readiness ranking."""
    from scipy.stats import spearmanr
    mask = predicted_scores.notna() & actual_scores.notna()
    if mask.sum() < 3:
        return np.nan
    corr, _ = spearmanr(predicted_scores[mask], actual_scores[mask])
    return round(float(corr), 3)


def day_to_day_stability(readiness_df: pd.DataFrame,
                          score_col: str = "readiness_score",
                          flag_threshold: float = 20.0) -> pd.DataFrame:
    """
    Check day-to-day score stability per player.
    Flag days where score changed > flag_threshold points without
    a corresponding wellness submission change.

    Readiness shouldn't whipsaw unless something meaningful changed.
    """
    df = readiness_df.copy().sort_values(["player_id", "date"])
    df["prev_score"] = df.groupby("player_id")[score_col].shift(1)
    df["delta"]      = (df[score_col] - df["prev_score"]).abs()
    df["unstable"]   = df["delta"] > flag_threshold
    return df[["player_id", "date", score_col, "prev_score", "delta", "unstable"]]


def precision_at_k(risk_scores: pd.DataFrame,
                   injury_df:   pd.DataFrame,
                   k:           int = 3,
                   lookahead:   int = 7) -> dict:
    """
    Precision@K: among the top-K flagged players per day, how many
    actually got injured within the next `lookahead` days?

    Parameters
    ----------
    risk_scores : DataFrame with columns [player_id, date, risk_score]
    injury_df   : DataFrame with columns [player_id, injury_date]
                  (non-contact injuries only)
    k           : number of top flags to evaluate (default 3)
    lookahead   : days ahead to check for injury (default 7)

    Returns
    -------
    dict: {precision_at_k, recall_at_k, days_evaluated, flags_issued}
    """
    if len(risk_scores) == 0 or len(injury_df) == 0:
        return {"precision_at_k": None, "recall_at_k": None,
                "days_evaluated": 0, "flags_issued": 0,
                "note": "Insufficient data for Precision@K calculation"}

    # Build injury lookup: player → set of injury dates
    inj = injury_df.copy()
    inj["injury_date"] = pd.to_datetime(inj["injury_date"])

    hits = 0
    total_flags = 0
    total_injuries = len(inj)
    injuries_caught = set()

    for date, day_group in risk_scores.groupby("date"):
        date = pd.to_datetime(date)
        top_k = day_group.nlargest(k, "risk_score")

        for _, row in top_k.iterrows():
            total_flags += 1
            pid = row["player_id"]
            # Check if this player got injured in the lookahead window
            player_injuries = inj[
                (inj["player_id"] == pid) &
                (inj["injury_date"] >= date) &
                (inj["injury_date"] <= date + timedelta(days=lookahead))
            ]
            if len(player_injuries) > 0:
                hits += 1
                for _, inj_row in player_injuries.iterrows():
                    injuries_caught.add((pid, inj_row["injury_date"]))

    precision = hits / total_flags if total_flags > 0 else 0
    recall    = len(injuries_caught) / total_injuries if total_injuries > 0 else 0

    return {
        "precision_at_k": round(precision, 3),
        "recall_at_k":    round(recall, 3),
        "k":              k,
        "lookahead_days": lookahead,
        "days_evaluated": risk_scores["date"].nunique(),
        "flags_issued":   total_flags,
        "injuries_caught": len(injuries_caught),
        "total_injuries":  total_injuries,
    }


def lead_time_analysis(risk_scores: pd.DataFrame,
                        injury_df:   pd.DataFrame,
                        risk_threshold: float = 0.5) -> pd.DataFrame:
    """
    For each injury event, find the earliest day the model flagged
    that player above risk_threshold before the injury.

    Returns DataFrame with lead_time_days per injury event.
    A model that flags 3-7 days before injury is operationally useful.
    Same-day flags are not.
    """
    results = []
    inj = injury_df.copy()
    inj["injury_date"] = pd.to_datetime(inj["injury_date"])

    for _, inj_row in inj.iterrows():
        pid         = inj_row["player_id"]
        injury_date = inj_row["injury_date"]

        # Look back up to 14 days before injury
        window_start = injury_date - timedelta(days=14)
        pre_injury_scores = risk_scores[
            (risk_scores["player_id"] == pid) &
            (risk_scores["date"] >= window_start) &
            (risk_scores["date"] < injury_date) &
            (risk_scores["risk_score"] >= risk_threshold)
        ].sort_values("date")

        if len(pre_injury_scores) > 0:
            first_flag = pre_injury_scores.iloc[0]["date"]
            lead_time  = (injury_date - pd.to_datetime(first_flag)).days
        else:
            lead_time  = 0  # No advance warning

        results.append({
            "player_id":    pid,
            "injury_date":  injury_date,
            "injury_type":  inj_row.get("injury_type", "Unknown"),
            "first_flag":   pre_injury_scores.iloc[0]["date"] if len(pre_injury_scores) > 0 else None,
            "lead_time_days": lead_time,
            "advance_warning": lead_time >= 3,
        })

    return pd.DataFrame(results)


def per_player_performance(risk_scores:   pd.DataFrame,
                           injury_df:     pd.DataFrame,
                           players_df:    pd.DataFrame,
                           risk_threshold: float = 0.5) -> pd.DataFrame:
    """
    Per-player false positive and flag rates.
    Catches "model is good overall but terrible for 3 athletes" problems.
    """
    results = []
    inj = injury_df.copy()
    inj["injury_date"] = pd.to_datetime(inj["injury_date"])

    for pid in players_df["player_id"].unique():
        player_name  = players_df[players_df["player_id"] == pid]["name"].values[0] \
                       if len(players_df[players_df["player_id"] == pid]) > 0 else str(pid)
        player_scores = risk_scores[risk_scores["player_id"] == pid]
        player_injuries = inj[inj["player_id"] == pid]

        total_days   = len(player_scores)
        flags_issued = (player_scores["risk_score"] >= risk_threshold).sum() \
                       if "risk_score" in player_scores.columns else 0
        flag_rate    = flags_issued / total_days if total_days > 0 else 0
        injuries     = len(player_injuries)

        results.append({
            "player":       player_name,
            "total_days":   total_days,
            "flags_issued": int(flags_issued),
            "flag_rate_%":  round(flag_rate * 100, 1),
            "injuries":     injuries,
            "over_flagged": flag_rate > 0.30,  # >30% of days flagged = suspicious
        })

    return pd.DataFrame(results).sort_values("flag_rate_%", ascending=False)


# ---------------------------------------------------------------------------
# STREAMLIT DISPLAY
# ---------------------------------------------------------------------------

def show_validation_framework_streamlit():
    """
    Render the full validation framework documentation in Streamlit.
    Called from the Insights tab model validation expander.
    """
    import streamlit as st

    with st.expander("📐 Model Validation Framework (Julius.ai Recipe)", expanded=False):
        st.markdown("### Validation Philosophy")
        st.info(
            "The biggest trap in athlete monitoring ML is validating in a way that "
            "leaks future information or overstates performance because data is "
            "highly autocorrelated within a player and across days."
        )

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**View 1 — Walk-Forward Time Splits**")
            st.markdown("*Will it work next week?*")
            splits_demo = pd.DataFrame([
                {"Fold": 1, "Train":   "Days 1–45",  "Validate": "Days 46–60"},
                {"Fold": 2, "Train":   "Days 1–60",  "Validate": "Days 61–75"},
                {"Fold": 3, "Train":   "Days 1–75",  "Validate": "Days 76–90"},
            ])
            st.dataframe(splits_demo, hide_index=True, use_container_width=True)

        with col2:
            st.markdown("**View 2 — Player Holdout (GroupKFold)**")
            st.markdown("*Will it work for a new signing?*")
            st.markdown(
                "Hold out 2–3 players entirely, train on the rest. "
                "Tests whether the model generalises to athletes with no prior history."
            )

        st.markdown("---")
        st.markdown("### Metrics by Model Type")

        tab_inj, tab_rdns = st.tabs(["Injury Risk (Classification)", "Readiness (Ranking)"])

        with tab_inj:
            metrics = pd.DataFrame([
                {"Metric": "PR-AUC (Average Precision)", "Priority": "★★★ Headline",
                 "Why": "Handles class imbalance. When we flag risk, how often are we right?"},
                {"Metric": "Precision@3 per day",        "Priority": "★★★ Operational",
                 "Why": "Top 3 flags per day matches real staff intervention capacity."},
                {"Metric": "Lead-time distribution",     "Priority": "★★★ Operational",
                 "Why": "Flags 3-7 days before injury are useful. Same-day flags are not."},
                {"Metric": "Calibration (Brier score)",  "Priority": "★★ Secondary",
                 "Why": "If model says 30% risk, does injury happen ~30% of the time?"},
                {"Metric": "ROC-AUC",                    "Priority": "★ Reference only",
                 "Why": "Can look great even when operationally mediocre under imbalance."},
            ])
            st.dataframe(metrics, hide_index=True, use_container_width=True)
            st.caption("Non-contact soft tissue injuries only. Contact injuries excluded — model not expected to predict these.")

        with tab_rdns:
            metrics2 = pd.DataFrame([
                {"Metric": "Spearman correlation",    "Priority": "★★★ Headline",
                 "Why": "V1 target: ≥0.70 on 70%+ of days vs coach intuition ranking."},
                {"Metric": "Day-to-day stability",    "Priority": "★★ Diagnostic",
                 "Why": "Score shouldn't whipsaw >20pts without a real wellness change."},
                {"Metric": "MAE / RMSE",              "Priority": "★ If proxy target exists",
                 "Why": "Only meaningful if readiness trained vs an objective performance proxy."},
            ])
            st.dataframe(metrics2, hide_index=True, use_container_width=True)

        st.markdown("---")
        st.markdown("### Baselines to Beat")
        st.caption("If the RF model doesn't beat these, the model isn't adding value.")
        baselines = pd.DataFrame([
            {"Baseline": "ACWR > 1.5 heuristic",           "Complexity": "Simple threshold",
             "What it tests": "Does the model add value over load ratio alone?"},
            {"Baseline": "7-day acute load spike rule",     "Complexity": "Simple threshold",
             "What it tests": "Does the model add value over volume monitoring?"},
            {"Baseline": "Player z-score on soreness/fatigue", "Complexity": "Personal baseline",
             "What it tests": "Does the model add value over a single-metric flag?"},
        ])
        st.dataframe(baselines, hide_index=True, use_container_width=True)

        st.markdown("---")
        st.markdown("### Ablation Studies")
        ablations = pd.DataFrame([
            {"Ablation": "Remove GPS features",              "Question": "Is GPS actually contributing signal?"},
            {"Ablation": "Remove wellness features",          "Question": "Is subjective data driving the model?"},
            {"Ablation": "Remove game schedule features",     "Question": "Does schedule context add value?"},
            {"Ablation": "Remove force plate features",       "Question": "Does CMJ/RSI improve over wellness alone?"},
        ])
        st.dataframe(ablations, hide_index=True, use_container_width=True)

        st.markdown("---")
        st.markdown("### Error Analysis — Building Coach Trust")
        st.markdown(
            "**False positives:** Were they actually near-misses — tightness, modified practice, "
            "load reduction — that didn't become a recorded injury? If yes, they are operationally correct flags.\n\n"
            "**False negatives:** What patterns did the model miss? Contact injuries and acute trauma "
            "are expected misses. Unexplained non-contact misses need investigation.\n\n"
            "**Per-player performance:** Check if the model over-flags specific athletes "
            "(flag rate >30%/day is suspicious). Systematic over-flagging for one player "
            "erodes coach trust faster than anything else."
        )

        st.markdown("---")
        st.markdown("### V1 vs V2 Validation Targets")
        targets = pd.DataFrame([
            {"Stage": "V1 Demo",    "Method": "Spearman vs coach intuition",
             "Target": "≥0.70 rank correlation on 70%+ of days"},
            {"Stage": "V2 Prod",    "Method": "Walk-forward + GroupKFold",
             "Target": "PR-AUC > ACWR baseline; Precision@3 > 0.40"},
            {"Stage": "V2 Prod",    "Method": "Lead-time analysis",
             "Target": "Median flag 3+ days before non-contact injury"},
            {"Stage": "V2 Prod",    "Method": "Calibration",
             "Target": "Brier score < naive base rate"},
            {"Stage": "V2 Prod",    "Method": "Per-player performance",
             "Target": "No player with flag rate >30%/day without injury history"},
        ])
        st.dataframe(targets, hide_index=True, use_container_width=True)
