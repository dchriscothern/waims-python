from __future__ import annotations

import shutil
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd


# -----------------------------------------------------------------------------
# Paths
# -----------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[1]  # scripts/ -> repo root
DB_PATH = REPO_ROOT / "waims_demo.db"

DROP_ROOT = REPO_ROOT / "data_drop"
PROCESSED_ROOT = DROP_ROOT / "_processed"


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _snake(s: str) -> str:
    return (
        s.strip()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("/", "_")
        .lower()
    )


def _ensure_dirs() -> None:
    DROP_ROOT.mkdir(parents=True, exist_ok=True)
    PROCESSED_ROOT.mkdir(parents=True, exist_ok=True)


def _read_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [_snake(c) for c in df.columns]
    return df


def _parse_date_col(df: pd.DataFrame) -> pd.DataFrame:
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"]).dt.date.astype(str)  # store as ISO text
    if "injury_date" in df.columns:
        df["injury_date"] = pd.to_datetime(df["injury_date"]).dt.date.astype(str)
    if "return_date" in df.columns:
        df["return_date"] = pd.to_datetime(df["return_date"]).dt.date.astype(str)
    return df


def _delete_existing(conn: sqlite3.Connection, table: str, df: pd.DataFrame) -> None:
    """
    Demo-friendly "upsert": delete existing rows for the same keys, then append.
    Uses (player_id, date) if present; else just appends.
    """
    if "player_id" in df.columns and "date" in df.columns:
        keys = df[["player_id", "date"]].dropna().drop_duplicates()
        if len(keys) == 0:
            return

        # Build a simple WHERE with IN lists (fine for demo-size)
        # Note: player_id could be int or str; cast to str for safety.
        player_ids = tuple(str(x) for x in keys["player_id"].tolist())
        dates = tuple(str(x) for x in keys["date"].tolist())

        # Delete any rows matching those player_ids AND those dates
        # (slightly broader than exact pairs, but safe for demo; avoids duplicates)
        q = f"""
        DELETE FROM {table}
        WHERE CAST(player_id AS TEXT) IN ({",".join(["?"] * len(player_ids))})
          AND date IN ({",".join(["?"] * len(dates))})
        """
        conn.execute(q, (*player_ids, *dates))
        conn.commit()


@dataclass
class TableSpec:
    name: str
    folder: Path
    required_cols: tuple[str, ...]
    optional_cols: tuple[str, ...] = ()


def _missing_required(df: pd.DataFrame, required: Iterable[str]) -> list[str]:
    return [c for c in required if c not in df.columns]


# -----------------------------------------------------------------------------
# Table mapping (adjust required cols to match your exports)
# -----------------------------------------------------------------------------
SPECS = [
    TableSpec(
        name="wellness",
        folder=DROP_ROOT / "wellness",
        required_cols=("player_id", "date", "sleep_hours", "soreness", "stress", "mood"),
        optional_cols=("sleep_quality", "fatigue", "fatigue_0_10", "soreness_0_10", "stress_0_10", "mood_0_10"),
    ),
    TableSpec(
        name="training_load",
        folder=DROP_ROOT / "training_load",
        required_cols=("player_id", "date"),
        optional_cols=(
            "practice_minutes", "practice_rpe", "total_daily_load", "game_minutes",
            "player_load", "accel_count", "decel_count",
            "total_distance_km", "hsr_distance_m", "sprint_distance_m",
        ),
    ),
    TableSpec(
        name="force_plate",
        folder=DROP_ROOT / "force_plate",
        required_cols=("player_id", "date"),
        optional_cols=("cmj_height_cm", "rsi_modified", "asymmetry_percent"),
    ),
    TableSpec(
        name="injuries",
        folder=DROP_ROOT / "injuries",
        required_cols=("player_id", "injury_date", "injury_type"),
        optional_cols=("return_date", "days_missed", "notes"),
    ),
    TableSpec(
        name="schedule",
        folder=DROP_ROOT / "schedule",
        required_cols=("date",),
        optional_cols=("is_back_to_back", "days_rest", "travel_flag", "time_zone_diff", "game_type"),
    ),
]


# -----------------------------------------------------------------------------
# Main ingest
# -----------------------------------------------------------------------------
def ingest() -> None:
    _ensure_dirs()
    if not DB_PATH.exists():
        raise FileNotFoundError(f"DB not found: {DB_PATH} (run generate_demo_data.py first)")

    conn = sqlite3.connect(DB_PATH)

    total_files = 0
    ingested_files = 0

    for spec in SPECS:
        spec.folder.mkdir(parents=True, exist_ok=True)
        for csv_path in sorted(spec.folder.glob("*.csv")):
            total_files += 1
            try:
                df = _read_csv(csv_path)
                df = _parse_date_col(df)

                missing = _missing_required(df, spec.required_cols)
                if missing:
                    print(f"[SKIP] {spec.name}: {csv_path.name} missing required columns: {missing}")
                    continue

                # keep only known columns (required + optional + any extras you want to keep)
                keep = list(spec.required_cols) + [c for c in spec.optional_cols if c in df.columns]
                df = df[keep].copy()

                # demo-friendly upsert
                try:
                    _delete_existing(conn, spec.name, df)
                except sqlite3.OperationalError:
                    # table doesn't exist yet -> to_sql will create it
                    pass

                df.to_sql(spec.name, conn, if_exists="append", index=False)

                # move file to processed
                dest_dir = PROCESSED_ROOT / spec.name
                dest_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(csv_path), str(dest_dir / csv_path.name))

                ingested_files += 1
                print(f"[OK] {spec.name}: {csv_path.name} -> db")

            except Exception as e:
                print(f"[ERR] {spec.name}: {csv_path.name} -> {e}")

    conn.close()
    print(f"\nDone. Files seen: {total_files} | Ingested: {ingested_files} | DB: {DB_PATH}")


if __name__ == "__main__":
    ingest()