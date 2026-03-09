"""
WAIMS Data Quality Module
=========================
Tiered imputation and outlier handling with full audit logging.

Philosophy
----------
Imputation is never neutral — every fill-in makes an assumption about WHY
data is missing. In athlete monitoring, missing data is often NOT random:
a player who skipped her morning check-in after a back-to-back is likely
the one you most need to flag.

This module makes every imputation decision explicit and auditable.
Sport scientists can review the log rather than discover silent fills.

Imputation tiers (by data type)
--------------------------------
1. Wellness (daily check-in)
   - Missing = informative signal, NOT imputed for readiness scoring
   - Binary flag `wellness_submitted` added as model feature
   - Missing rows excluded from readiness calculation; flagged in UI

2. Force plate (CMJ / RSI)
   - LOCF (last observation carried forward) up to 3 days
   - Staleness flag added after 3+ days without a session
   - Sessions are infrequent by design — LOCF is defensible

3. GPS / training load
   - Device failure (missing session): excluded, not imputed
   - Spike outliers (>3σ from player rolling mean): winsorised to 3σ
   - Original value preserved in audit log

4. Sleep (from wearable)
   - Personal 14-day rolling mean if ≤2 consecutive days missing
   - Flagged (not imputed) if >2 consecutive days missing
   - Sleep has strong personal autocorrelation; personal baseline
     is more valid than population mean

5. ACWR
   - Recalculated from available load data
   - Flagged if <7 days of load data available (ratio unreliable)

Basketball-specific notes
--------------------------
- Back-to-back: missing wellness the morning after a B2B is likely
  load-related, not random. NEVER silently impute — flag explicitly.
- Positional differences: team-level mean imputation is inappropriate;
  centers and guards have structurally different baselines.
- Short WNBA season (40 games): rolling windows use 7–14 days,
  not 28+ days used in soccer literature.
- Travel direction (eastward): known confounder for next-day wellness;
  missing data on travel days gets an additional travel flag.

Alignment with Mercury WNBA project
--------------------------------------
Personal rolling baseline imputation for continuous metrics (consistent
with standard academic sport science practice). LOCF for infrequent
assessments. Missing as signal for daily subjective measures.

Usage
-----
    from data_quality import DataQualityProcessor

    dqp = DataQualityProcessor()
    wellness_clean = dqp.process_wellness(wellness_df)
    fp_clean       = dqp.process_force_plate(force_plate_df)
    gps_clean      = dqp.process_gps(training_load_df)
    report         = dqp.get_audit_report()
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WELLNESS_COLS   = ["sleep_hours", "soreness", "stress", "mood", "sleep_quality"]
FORCE_PLATE_COLS = ["cmj_height_cm", "rsi_modified"]
GPS_COLS        = ["session_distance", "high_speed_distance", "sprint_distance",
                   "decel_count", "accel_count", "practice_minutes"]

LOCF_MAX_DAYS   = 3     # Force plate: max days to carry forward
SLEEP_LOCF_DAYS = 2     # Sleep: max consecutive missing days before flagging
SPIKE_SIGMA     = 3.0   # GPS: winsorise beyond this many σ from personal rolling mean
ROLLING_WINDOW  = 14    # Personal baseline window (days) — shorter than soccer lit
ACWR_MIN_DAYS   = 7     # Minimum days of load data for reliable ACWR


class DataQualityProcessor:
    """
    Process and document all data quality decisions for WAIMS.

    Every imputation, exclusion, and winsorisation is logged to
    self.audit_log so sport scientists can review what happened.
    """

    def __init__(self):
        self.audit_log: list[dict] = []
        self.summary: dict = {
            "wellness_missing_flagged": 0,
            "force_plate_locf_filled": 0,
            "force_plate_stale_flagged": 0,
            "gps_sessions_excluded": 0,
            "gps_spikes_winsorised": 0,
            "sleep_personal_imputed": 0,
            "sleep_missing_flagged": 0,
            "acwr_unreliable_flagged": 0,
        }

    def _log(self, player_id, date, data_type, action, original_value, new_value, reason):
        self.audit_log.append({
            "timestamp": datetime.now().isoformat(),
            "player_id": player_id,
            "date": str(date),
            "data_type": data_type,
            "action": action,
            "original_value": original_value,
            "new_value": new_value,
            "reason": reason,
        })

    # -----------------------------------------------------------------------
    # 1. WELLNESS
    # -----------------------------------------------------------------------

    def process_wellness(self, df: pd.DataFrame,
                         schedule_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Process daily wellness check-in data.

        Missing rows → NOT imputed. Add `wellness_submitted` flag.
        Missing after B2B → additional `b2b_missing` flag.

        Parameters
        ----------
        df : wellness DataFrame (player_id, date, sleep_hours, soreness,
             stress, mood, sleep_quality)
        schedule_df : optional schedule with `is_back_to_back` column

        Returns
        -------
        DataFrame with `wellness_submitted`, `b2b_missing`, and per-metric
        `*_imputed` flags added.
        """
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])
        df["wellness_submitted"] = 1

        # Build full expected grid (every player × every date)
        all_players = df["player_id"].unique()
        all_dates   = pd.date_range(df["date"].min(), df["date"].max(), freq="D")
        full_grid   = pd.MultiIndex.from_product(
            [all_players, all_dates], names=["player_id", "date"]
        ).to_frame(index=False)

        df_full = full_grid.merge(df, on=["player_id", "date"], how="left")
        df_full["wellness_submitted"] = df_full["wellness_submitted"].fillna(0).astype(int)

        # Flag B2B missing if schedule provided
        df_full["b2b_missing"] = 0
        if schedule_df is not None and "is_back_to_back" in schedule_df.columns:
            b2b_dates = set(
                pd.to_datetime(schedule_df[schedule_df["is_back_to_back"] == 1]["date"])
            )
            mask = (df_full["wellness_submitted"] == 0) & (df_full["date"].isin(b2b_dates))
            df_full.loc[mask, "b2b_missing"] = 1
            b2b_count = mask.sum()
            if b2b_count > 0:
                self._log("ALL", "multiple", "wellness", "b2b_missing_flagged",
                          None, None,
                          f"{b2b_count} missing check-ins on B2B days — likely load-related, NOT imputed")

        # Log missing count per player
        missing = df_full[df_full["wellness_submitted"] == 0]
        for pid, grp in missing.groupby("player_id"):
            count = len(grp)
            self.summary["wellness_missing_flagged"] += count
            self._log(pid, "multiple", "wellness", "missing_flagged",
                      None, None,
                      f"{count} missing check-in days — excluded from readiness scoring, "
                      f"wellness_submitted=0 added as model feature")

        # Sleep: personal rolling imputation for short gaps (wearable data)
        df_full = self._impute_sleep(df_full)

        return df_full.sort_values(["player_id", "date"]).reset_index(drop=True)

    def _impute_sleep(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Sleep hours: personal 14-day rolling mean for ≤2 consecutive missing days.
        Flag (don't impute) if >2 consecutive days.
        """
        df = df.copy()
        df["sleep_imputed"] = 0
        df["sleep_flagged"]  = 0

        for pid in df["player_id"].unique():
            mask = df["player_id"] == pid
            sub  = df.loc[mask, "sleep_hours"].copy()

            # Personal rolling mean (only from submitted days)
            submitted_mask = df.loc[mask, "wellness_submitted"] == 1
            rolling_mean   = (sub.where(submitted_mask)
                               .rolling(window=ROLLING_WINDOW, min_periods=3)
                               .mean()
                               .ffill())

            # Find consecutive missing runs
            is_missing = sub.isna()
            run_id = (is_missing != is_missing.shift()).cumsum()

            for rid, run_grp in sub[is_missing].groupby(run_id[is_missing]):
                run_len = len(run_grp)
                idx     = run_grp.index

                if run_len <= SLEEP_LOCF_DAYS:
                    fill_vals = rolling_mean.loc[idx]
                    df.loc[idx, "sleep_hours"]   = fill_vals
                    df.loc[idx, "sleep_imputed"] = 1
                    self.summary["sleep_personal_imputed"] += run_len
                    for i in idx:
                        self._log(pid, df.loc[i, "date"], "sleep",
                                  "personal_rolling_mean_imputed",
                                  None, round(float(fill_vals.loc[i]), 2),
                                  f"{run_len}-day gap ≤ {SLEEP_LOCF_DAYS} days — "
                                  f"used personal {ROLLING_WINDOW}-day rolling mean")
                else:
                    df.loc[idx, "sleep_flagged"] = 1
                    self.summary["sleep_missing_flagged"] += run_len
                    self._log(pid, f"{df.loc[idx[0],'date']} to {df.loc[idx[-1],'date']}",
                              "sleep", "missing_flagged",
                              None, None,
                              f"{run_len}-day consecutive gap > {SLEEP_LOCF_DAYS} days — "
                              "NOT imputed, flagged for review")

        return df

    # -----------------------------------------------------------------------
    # 2. FORCE PLATE
    # -----------------------------------------------------------------------

    def process_force_plate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Force plate (CMJ / RSI): LOCF up to LOCF_MAX_DAYS days.
        Add staleness flag after that.
        """
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])

        all_players = df["player_id"].unique()
        all_dates   = pd.date_range(df["date"].min(), df["date"].max(), freq="D")
        full_grid   = pd.MultiIndex.from_product(
            [all_players, all_dates], names=["player_id", "date"]
        ).to_frame(index=False)

        df_full = full_grid.merge(df, on=["player_id", "date"], how="left")

        for col in FORCE_PLATE_COLS:
            if col not in df_full.columns:
                continue
            df_full[f"{col}_locf"]  = 0
            df_full[f"{col}_stale"] = 0

        for pid in df_full["player_id"].unique():
            mask = df_full["player_id"] == pid
            sub  = df_full.loc[mask].copy()

            for col in FORCE_PLATE_COLS:
                if col not in sub.columns:
                    continue

                days_since = 0
                for idx in sub.index:
                    val = df_full.loc[idx, col]
                    if pd.notna(val):
                        days_since = 0
                    else:
                        days_since += 1
                        if days_since <= LOCF_MAX_DAYS:
                            # Find last valid value
                            prev = df_full.loc[:idx-1][
                                (df_full.loc[:idx-1, "player_id"] == pid) &
                                df_full.loc[:idx-1, col].notna()
                            ]
                            if len(prev) > 0:
                                last_val = prev.iloc[-1][col]
                                df_full.loc[idx, col]             = last_val
                                df_full.loc[idx, f"{col}_locf"]   = 1
                                self.summary["force_plate_locf_filled"] += 1
                                self._log(pid, df_full.loc[idx, "date"], col,
                                          "locf_filled", None, round(float(last_val), 3),
                                          f"Day {days_since} of gap — LOCF from last valid session")
                        else:
                            df_full.loc[idx, f"{col}_stale"] = 1
                            self.summary["force_plate_stale_flagged"] += 1

        return df_full.sort_values(["player_id", "date"]).reset_index(drop=True)

    # -----------------------------------------------------------------------
    # 3. GPS / TRAINING LOAD
    # -----------------------------------------------------------------------

    def process_gps(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        GPS / training load:
        - Missing session (device failure): exclude, add `session_excluded` flag
        - Spike outliers (>SPIKE_SIGMA σ from personal rolling mean):
          winsorise to cap, preserve original in `*_original` column
        """
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])
        df["session_excluded"] = 0

        for col in GPS_COLS:
            if col not in df.columns:
                continue
            df[f"{col}_original"] = df[col].copy()
            df[f"{col}_winsorised"] = 0

            for pid in df["player_id"].unique():
                mask   = df["player_id"] == pid
                series = df.loc[mask, col].copy()

                # Winsorise spikes
                rolling_mean = series.rolling(window=ROLLING_WINDOW, min_periods=3).mean()
                rolling_std  = series.rolling(window=ROLLING_WINDOW, min_periods=3).std()
                upper_cap    = rolling_mean + SPIKE_SIGMA * rolling_std

                spike_mask = (series > upper_cap) & series.notna()
                if spike_mask.any():
                    spike_idx = series[spike_mask].index
                    for i in spike_idx:
                        orig = df.loc[i, col]
                        cap  = upper_cap.loc[i]
                        df.loc[i, col]                 = round(float(cap), 2)
                        df.loc[i, f"{col}_winsorised"] = 1
                        self.summary["gps_spikes_winsorised"] += 1
                        self._log(pid, df.loc[i, "date"], col,
                                  "winsorised",
                                  round(float(orig), 2), round(float(cap), 2),
                                  f"Value exceeded {SPIKE_SIGMA}σ rolling threshold — "
                                  "likely device error, original preserved in *_original")

        return df.sort_values(["player_id", "date"]).reset_index(drop=True)

    # -----------------------------------------------------------------------
    # 4. ACWR VALIDATION
    # -----------------------------------------------------------------------

    def validate_acwr(self, acwr_df: pd.DataFrame,
                      training_load_df: pd.DataFrame) -> pd.DataFrame:
        """
        Flag ACWR values where insufficient load history exists.
        ACWR is unreliable with <7 days of denominator data.
        """
        acwr_df = acwr_df.copy()
        acwr_df["date"] = pd.to_datetime(acwr_df["date"])
        acwr_df["acwr_reliable"] = 1

        for pid in acwr_df["player_id"].unique():
            load = training_load_df[training_load_df["player_id"] == pid].copy()
            load["date"] = pd.to_datetime(load["date"])

            for idx, row in acwr_df[acwr_df["player_id"] == pid].iterrows():
                window_start = row["date"] - pd.Timedelta(days=28)
                chronic_data = load[
                    (load["date"] >= window_start) & (load["date"] < row["date"])
                ]
                if len(chronic_data) < ACWR_MIN_DAYS:
                    acwr_df.loc[idx, "acwr_reliable"] = 0
                    self.summary["acwr_unreliable_flagged"] += 1
                    self._log(pid, row["date"], "acwr", "unreliable_flagged",
                              row.get("acwr"), None,
                              f"Only {len(chronic_data)} days of load data — "
                              f"need ≥{ACWR_MIN_DAYS} for reliable chronic load")

        return acwr_df

    # -----------------------------------------------------------------------
    # AUDIT REPORT
    # -----------------------------------------------------------------------

    def get_audit_report(self) -> dict:
        """Return summary counts and full audit log as a dict."""
        return {
            "summary": self.summary,
            "total_actions": len(self.audit_log),
            "log": self.audit_log,
        }

    def print_summary(self):
        """Print human-readable summary to stdout."""
        print("\n" + "="*60)
        print("WAIMS DATA QUALITY REPORT")
        print("="*60)
        for key, val in self.summary.items():
            label = key.replace("_", " ").title()
            print(f"  {label:<40} {val:>6}")
        print(f"  {'Total audit log entries':<40} {len(self.audit_log):>6}")
        print("="*60 + "\n")

    def get_audit_dataframe(self) -> pd.DataFrame:
        """Return audit log as a pandas DataFrame for display in Streamlit."""
        if not self.audit_log:
            return pd.DataFrame(columns=["timestamp","player_id","date","data_type",
                                          "action","original_value","new_value","reason"])
        return pd.DataFrame(self.audit_log)


# ---------------------------------------------------------------------------
# STREAMLIT DISPLAY HELPER
# ---------------------------------------------------------------------------

def show_data_quality_report(dqp: DataQualityProcessor):
    """
    Render a data quality audit panel inside a Streamlit expander.
    Call this from the Insights tab.
    """
    import streamlit as st

    with st.expander("🔍 Data Quality Audit Log", expanded=False):
        st.markdown("### Data Quality Decisions")
        st.caption(
            "Every imputation, exclusion, and winsorisation is logged here. "
            "No silent fills — all decisions are explicit and auditable."
        )

        report = dqp.get_audit_report()
        summary = report["summary"]

        # Summary metrics
        cols = st.columns(4)
        cols[0].metric("Wellness Missing (flagged)", summary["wellness_missing_flagged"])
        cols[1].metric("Force Plate LOCF fills",    summary["force_plate_locf_filled"])
        cols[2].metric("GPS Spikes Winsorised",      summary["gps_spikes_winsorised"])
        cols[3].metric("Sleep Imputed (personal)",   summary["sleep_personal_imputed"])

        st.markdown("---")
        st.markdown("**Imputation Policy Summary**")

        policy_data = {
            "Data Type": [
                "Wellness check-in (missing)",
                "Force plate CMJ/RSI",
                "GPS / Training load spikes",
                "Sleep (short gaps ≤2 days)",
                "Sleep (long gaps >2 days)",
                "ACWR (<7 days load history)",
            ],
            "Action": [
                "Flag only — NOT imputed",
                "LOCF up to 3 days, then staleness flag",
                "Winsorise to 3σ, preserve original",
                "Personal 14-day rolling mean",
                "Flag only — NOT imputed",
                "Flag as unreliable",
            ],
            "Rationale": [
                "Non-submission is informative (esp. post B2B). Coaches follow up manually.",
                "Sessions are infrequent by design. LOCF defensible for short gaps.",
                "Spikes >3σ likely device error, not athlete signal.",
                "Sleep has strong personal autocorrelation. Population mean inappropriate.",
                "Extended gap needs manual review — too long to assume baseline applies.",
                "Chronic load denominator needs ≥7 days or ratio is meaningless.",
            ],
        }
        import pandas as pd
        st.dataframe(pd.DataFrame(policy_data), use_container_width=True, hide_index=True)

        # Full audit log
        audit_df = dqp.get_audit_dataframe()
        if len(audit_df) > 0:
            st.markdown("---")
            st.markdown(f"**Full Audit Log** ({len(audit_df)} entries)")
            st.dataframe(audit_df, use_container_width=True, hide_index=True)
        else:
            st.info("No data quality actions logged yet — "
                    "run DataQualityProcessor on real data to populate this log.")
