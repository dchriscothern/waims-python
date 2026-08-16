"""Parse Arkansas Baha Mar box score PDFs into structured per-player game stats.

The source PDFs are scanned images (no text layer), so the official box score
page (page 1 of each PDF) is OCR'd with RapidOCR. RapidOCR returns one
bounding box per detected phrase, and this report's box score table has a
fixed column layout, so cells are reassembled by bucketing each OCR box into
the column whose x-range contains its center, then grouping boxes into rows
by y-proximity.

Usage:
    python scripts/parse_arkansas_box_scores.py
"""

from __future__ import annotations

import difflib
import re
import sqlite3
from pathlib import Path

import fitz
from rapidocr_onnxruntime import RapidOCR

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_arkansas_manual_coding_workbook import OPPONENT_ALIASES, normalize_opponent

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "waims-mens"))
from roster_arkansas import ARKANSAS_ROSTER_2026

# The source PDF misspells Columbia as "Colombia" on the box score itself.
OPPONENT_ALIASES.setdefault("colombia", "Columbia")

ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"
DB_PATH = ROOT / "waims-mens" / "data" / "waims_arkansas.db"

# Baha-Mar-Summer-Stats-3-vs-Toros-del-Valle.pdf is a byte-for-byte duplicate
# of the Columbia game PDF (confirmed via pixel hash), not a real 5th game.
EXCLUDED_GAME_IDS = {"Baha-Mar-Summer-Stats-3-vs-Toros-del-Valle"}

BOX_SCORE_PAGE_INDEX = 0
OCR_MATRIX_SCALE = 3

# Column x-ranges (pixels) at OCR_MATRIX_SCALE, derived from the header row
# of the Baha Mar Hoops box score template. Consistent across games since
# it's a fixed-width computer-generated report.
COLUMNS = [
    ("number", 70, 135),
    ("name", 135, 415),
    ("min", 450, 545),
    ("fg", 545, 620),
    ("fg3", 620, 685),
    ("ft", 685, 750),
    ("oreb", 750, 802),
    ("dreb", 802, 848),
    ("treb", 848, 902),
    ("pf", 902, 950),
    ("fd", 950, 995),
    ("tp", 995, 1046),
    ("ast", 1046, 1092),
    ("tov", 1092, 1146),
    ("stl", 1146, 1196),
    ("bs", 1196, 1242),
    ("ba", 1242, 1300),
    ("plusminus", 1300, 1360),
]
SIDE_PANEL_X_MIN = 1360  # Shooting-by-period / summary panels start here; ignore.
ROW_Y_GAP = 12  # Max y-gap (px) between OCR boxes in the same table row.
HEADER_BAND_HEIGHT = 100  # Skip this much below a team header before player rows start.

TEAM_SCORE_RE = re.compile(r"^([A-Za-z][A-Za-z ]*[A-Za-z])-(\d+)$")
DATE_RE = re.compile(r"(\d{2}/\d{2}/\d{2})")


def _ocr_page(pdf_path: Path, page_index: int) -> list[dict]:
    doc = fitz.open(str(pdf_path))
    page = doc[page_index]
    pix = page.get_pixmap(matrix=fitz.Matrix(OCR_MATRIX_SCALE, OCR_MATRIX_SCALE), alpha=False)
    temp_image = ROOT / f"__box_score_ocr_tmp.png"
    pix.save(str(temp_image))
    doc.close()

    try:
        result, _ = RapidOCR()(str(temp_image))
    finally:
        temp_image.unlink(missing_ok=True)

    items = []
    for box, text, conf in result or []:
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        text = str(text).strip()
        if not text:
            continue
        items.append({
            "text": text,
            "x_min": min(xs), "x_max": max(xs),
            "y_min": min(ys), "y_max": max(ys),
            "conf": conf,
        })
    return items


def _column_for_x(x_center: float) -> str | None:
    for name, x_min, x_max in COLUMNS:
        if x_min <= x_center < x_max:
            return name
    return None


def _split_made_attempted(text: str) -> tuple[int | None, int | None]:
    m = re.match(r"^(\d+)-(\d+)$", text)
    if not m:
        return None, None
    return int(m.group(1)), int(m.group(2))


def _cluster_rows(items: list[dict]) -> list[list[dict]]:
    rows: list[list[dict]] = []
    current: list[dict] = []
    last_y: float | None = None
    for item in sorted(items, key=lambda i: i["y_min"]):
        if last_y is not None and item["y_min"] - last_y > ROW_Y_GAP:
            rows.append(current)
            current = []
        current.append(item)
        last_y = item["y_min"]
    if current:
        rows.append(current)
    return rows


def _find_team_blocks(items: list[dict]) -> list[dict]:
    """Locate the two team header rows and their following Totals rows."""
    headers = []
    for item in items:
        m = TEAM_SCORE_RE.match(item["text"].replace(" ", ""))
        if m and item["x_min"] < 415:
            headers.append({"team_raw": m.group(1), "score": int(m.group(2)), "y": item["y_min"]})
    headers.sort(key=lambda h: h["y"])

    totals_ys = sorted(
        item["y_min"] for item in items
        if item["text"].strip().lower() == "totals" and item["x_min"] < 415
    )

    blocks = []
    for i, header in enumerate(headers):
        totals_y = next((y for y in totals_ys if y > header["y"]), None)
        next_header_y = headers[i + 1]["y"] if i + 1 < len(headers) else None
        row_end = totals_y if totals_y is not None else next_header_y
        blocks.append({
            "team_raw": header["team_raw"],
            "score": header["score"],
            "row_start_y": header["y"] + HEADER_BAND_HEIGHT,
            "row_end_y": row_end,
        })
    return blocks


def _normalize_name_key(name: str) -> str:
    return re.sub(r"[^a-z]", "", name.lower())


ROSTER_KEYS = {_normalize_name_key(p["name"]): p for p in ARKANSAS_ROSTER_2026}


def _match_roster_player(raw_name: str) -> dict | None:
    key = _normalize_name_key(raw_name)
    if not key:
        return None
    best_match = difflib.get_close_matches(key, ROSTER_KEYS.keys(), n=1, cutoff=0.55)
    if not best_match:
        return None
    return ROSTER_KEYS[best_match[0]]


def parse_box_score(pdf_path: Path) -> dict:
    game_id = pdf_path.stem
    items = _ocr_page(pdf_path, BOX_SCORE_PAGE_INDEX)

    text_blob = " ".join(i["text"] for i in items)
    date_match = DATE_RE.search(text_blob)
    date_value = date_match.group(1) if date_match else ""

    table_items = [i for i in items if i["x_min"] < SIDE_PANEL_X_MIN]
    blocks = _find_team_blocks(table_items)

    opponent = normalize_opponent(_extract_opponent_from_pdf_name(pdf_path))

    player_rows = []
    team_totals = []
    for block in blocks:
        team_label = "ARK" if block["team_raw"].strip().lower() == "arkansas" else "OPP"
        team_name = opponent if team_label == "OPP" else "Arkansas"

        block_items = [
            i for i in table_items
            if block["row_start_y"] <= i["y_min"] < (block["row_end_y"] or float("inf"))
        ]
        for row in _cluster_rows(block_items):
            cells: dict[str, str] = {}
            for item in row:
                col = _column_for_x((item["x_min"] + item["x_max"]) / 2)
                if col is None:
                    continue
                cells.setdefault(col, []).append(item)

            name_items = cells.get("name")
            number_items = cells.get("number")
            if not name_items:
                continue
            raw_name = " ".join(t["text"] for t in sorted(name_items, key=lambda t: t["x_min"]))

            if raw_name.strip().lower() == "team":
                # Team-level rebound row, not a player.
                continue

            def _cell_text(col: str) -> str | None:
                vals = cells.get(col)
                return vals[0]["text"] if vals else None

            def _cell_int(col: str) -> int | None:
                text = _cell_text(col)
                if text is None:
                    return None
                text = text.replace("O", "0")  # common OCR digit confusion
                try:
                    return int(text)
                except ValueError:
                    return None

            fgm, fga = _split_made_attempted(_cell_text("fg") or "")
            fg3m, fg3a = _split_made_attempted(_cell_text("fg3") or "")
            ftm, fta = _split_made_attempted(_cell_text("ft") or "")

            player_number = None
            if number_items:
                try:
                    player_number = int(number_items[0]["text"])
                except ValueError:
                    player_number = None

            roster_match = _match_roster_player(raw_name) if team_label == "ARK" else None

            player_rows.append({
                "game_id": game_id,
                "team": team_label,
                "team_name": team_name,
                "player_number": player_number,
                "player_name_raw": raw_name,
                "player_id": roster_match["player_id"] if roster_match else None,
                "player_name_matched": roster_match["name"] if roster_match else None,
                "min": _cell_text("min"),
                "fgm": fgm, "fga": fga,
                "fg3m": fg3m, "fg3a": fg3a,
                "ftm": ftm, "fta": fta,
                "oreb": _cell_int("oreb"), "dreb": _cell_int("dreb"), "reb": _cell_int("treb"),
                "pf": _cell_int("pf"), "fd": _cell_int("fd"),
                "pts": _cell_int("tp"),
                "ast": _cell_int("ast"), "tov": _cell_int("tov"), "stl": _cell_int("stl"),
                "blk": _cell_int("bs"), "blk_against": _cell_int("ba"),
                "plus_minus": _cell_int("plusminus"),
            })

        team_totals.append({"team": team_label, "team_name": team_name, "score": block["score"]})

    return {
        "game_id": game_id,
        "date": date_value,
        "opponent": opponent,
        "source_pdf": pdf_path.name,
        "player_rows": player_rows,
        "team_totals": team_totals,
    }


def _extract_opponent_from_pdf_name(pdf_path: Path) -> str:
    stem = pdf_path.stem
    if "vs" in stem.lower():
        return stem.split("vs", 1)[-1] if "vs-" not in stem.lower() else stem.lower().split("vs-", 1)[-1]
    return stem


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS player_game_stats (
            game_id TEXT,
            team TEXT,
            team_name TEXT,
            player_number INTEGER,
            player_name_raw TEXT,
            player_id TEXT,
            player_name_matched TEXT,
            min TEXT,
            fgm INTEGER, fga INTEGER,
            fg3m INTEGER, fg3a INTEGER,
            ftm INTEGER, fta INTEGER,
            oreb INTEGER, dreb INTEGER, reb INTEGER,
            pf INTEGER, fd INTEGER,
            pts INTEGER,
            ast INTEGER, tov INTEGER, stl INTEGER,
            blk INTEGER, blk_against INTEGER,
            plus_minus INTEGER,
            PRIMARY KEY (game_id, team, player_number)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS game_results (
            game_id TEXT PRIMARY KEY,
            date TEXT,
            opponent TEXT,
            team TEXT,
            arkansas_score INTEGER,
            opponent_score INTEGER,
            final_score TEXT,
            result TEXT,
            source_pdf TEXT,
            status TEXT,
            notes TEXT
        )
        """
    )


def save_game(conn: sqlite3.Connection, parsed: dict) -> int:
    _ensure_schema(conn)
    cur = conn.cursor()

    cur.execute("DELETE FROM player_game_stats WHERE game_id = ?", (parsed["game_id"],))
    for row in parsed["player_rows"]:
        cur.execute(
            """
            INSERT INTO player_game_stats (
                game_id, team, team_name, player_number, player_name_raw, player_id,
                player_name_matched, min, fgm, fga, fg3m, fg3a, ftm, fta,
                oreb, dreb, reb, pf, fd, pts, ast, tov, stl, blk, blk_against, plus_minus
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                row["game_id"], row["team"], row["team_name"], row["player_number"],
                row["player_name_raw"], row["player_id"], row["player_name_matched"], row["min"],
                row["fgm"], row["fga"], row["fg3m"], row["fg3a"], row["ftm"], row["fta"],
                row["oreb"], row["dreb"], row["reb"], row["pf"], row["fd"], row["pts"],
                row["ast"], row["tov"], row["stl"], row["blk"], row["blk_against"], row["plus_minus"],
            ),
        )

    ark_score = next((t["score"] for t in parsed["team_totals"] if t["team"] == "ARK"), None)
    opp_score = next((t["score"] for t in parsed["team_totals"] if t["team"] == "OPP"), None)
    final_score = f"{ark_score}-{opp_score}" if ark_score is not None and opp_score is not None else ""
    result = None
    if ark_score is not None and opp_score is not None:
        result = "W" if ark_score > opp_score else "L" if ark_score < opp_score else "T"

    cur.execute(
        """
        INSERT OR REPLACE INTO game_results (
            game_id, date, opponent, team, arkansas_score, opponent_score,
            final_score, result, source_pdf, status, notes
        ) VALUES (?, ?, ?, 'Arkansas', ?, ?, ?, ?, ?, 'OCR box score parsed', ?)
        """,
        (
            parsed["game_id"], parsed["date"], parsed["opponent"],
            ark_score, opp_score, final_score, result, parsed["source_pdf"],
            "Parsed from official box score table (page 1).",
        ),
    )
    conn.commit()
    return len(parsed["player_rows"])


def main() -> None:
    pdf_files = sorted(DOCS_DIR.glob("Baha-Mar-Summer-Stats-*.pdf"))
    conn = sqlite3.connect(str(DB_PATH))
    _ensure_schema(conn)

    for pdf_path in pdf_files:
        if pdf_path.stem in EXCLUDED_GAME_IDS:
            print(f"Skipping {pdf_path.name} (duplicate of Columbia game, not a real box score)")
            continue
        print(f"Parsing {pdf_path.name} ...")
        parsed = parse_box_score(pdf_path)
        n = save_game(conn, parsed)
        ark = next((t for t in parsed["team_totals"] if t["team"] == "ARK"), None)
        opp = next((t for t in parsed["team_totals"] if t["team"] == "OPP"), None)
        score_str = f"{ark['score']}-{opp['score']}" if ark and opp else "unknown"
        unmatched = [
            r["player_name_raw"] for r in parsed["player_rows"]
            if r["team"] == "ARK" and r["player_id"] is None
        ]
        print(f"  {parsed['date']} vs {parsed['opponent']}: Arkansas {score_str}, {n} player rows")
        if unmatched:
            print(f"  Unmatched Arkansas names (need manual review): {unmatched}")

    conn.close()


if __name__ == "__main__":
    main()
