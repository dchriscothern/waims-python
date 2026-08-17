"""Parse Arkansas Baha Mar play-by-play PDFs into structured event rows.

Each game PDF has a fixed page structure (confirmed by OCR-ing page headers):
  page 0        : Box Score - Final
  pages 1-6     : Play by Play - First Half
  page 7        : Box Score - First Half
  pages 8..N-2  : Play by Play - Second Half
  page N-1      : Box Score - Second Half

The play-by-play table has 5 columns: Game Time | ARK | Score | Diff | OPP.
A single event's ARK/OPP cell can wrap across two OCR-detected lines, so rows
are anchored on the Game Time column (one clock value per event) rather than
plain y-gap clustering: everything between one Game Time box and the next
belongs to that event.

Usage:
    python scripts/parse_arkansas_play_by_play.py
"""

from __future__ import annotations

import re
import sqlite3
import sys
from pathlib import Path

import fitz
from rapidocr_onnxruntime import RapidOCR

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_arkansas_manual_coding_workbook import normalize_opponent
from parse_arkansas_box_scores import (
    EXCLUDED_GAME_IDS,
    OCR_MATRIX_SCALE,
    _extract_opponent_from_pdf_name,
    _match_roster_player,
)

ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"
DB_PATH = ROOT / "waims-mens" / "data" / "waims_arkansas.db"

# Column x-ranges (pixels) at OCR_MATRIX_SCALE, derived from the play-by-play
# table header (Game Time | ARK | Score | Diff | <opponent>).
COL_GAME_TIME = (60, 210)
COL_ARK = (205, 858)
COL_SCORE = (858, 1003)
COL_DIFF = (1003, 1093)
COL_OPP = (1093, 1780)

GAME_TIME_RE = re.compile(r"^\d{1,2}:\d{2}$")

_ocr = RapidOCR()


def _ocr_page(pdf_path: Path, page_index: int) -> list[dict]:
    doc = fitz.open(str(pdf_path))
    page = doc[page_index]
    pix = page.get_pixmap(matrix=fitz.Matrix(OCR_MATRIX_SCALE, OCR_MATRIX_SCALE), alpha=False)
    temp_image = ROOT / "__pbp_ocr_tmp.png"
    pix.save(str(temp_image))
    doc.close()

    try:
        result, _ = _ocr(str(temp_image))
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
            "text": text, "x_min": min(xs), "x_max": max(xs),
            "y_min": min(ys), "y_max": max(ys), "conf": conf,
        })
    return items


def _rows_from_page(items: list[dict]) -> list[dict]:
    """Group OCR items into event rows anchored on the Game Time column."""
    anchors = sorted(
        (i for i in items if GAME_TIME_RE.match(i["text"]) and COL_GAME_TIME[0] <= i["x_min"] < COL_GAME_TIME[1]),
        key=lambda i: i["y_min"],
    )
    if not anchors:
        return []

    # The Game Time label is vertically CENTERED on its row's cell content,
    # not aligned with the first line. For a normal one-line row that's ~2px
    # off and harmless, but for a row that wraps to two lines because two
    # events share the same clock value (e.g. an offensive rebound immediately
    # followed by the putback), the anchor sits between the two lines. A
    # one-sided window (anchor_y .. next_anchor_y) then slices the wrapped
    # row's first line into the previous row and orphans the "made (N)" line
    # with no player name attached, silently dropping the make. Using the
    # midpoint between consecutive anchors as the row boundary keeps each
    # row's content centered on its own anchor instead.
    rows = []
    for idx, anchor in enumerate(anchors):
        window_start = (
            (anchors[idx - 1]["y_min"] + anchor["y_min"]) / 2 if idx > 0 else float("-inf")
        )
        window_end = (
            (anchor["y_min"] + anchors[idx + 1]["y_min"]) / 2 if idx + 1 < len(anchors) else float("inf")
        )
        row_items = [i for i in items if window_start <= i["y_min"] < window_end and i is not anchor]
        rows.append({"game_time": anchor["text"], "items": row_items})
    return rows


def _text_in_column(row_items: list[dict], col: tuple[float, float]) -> str:
    matched = [i for i in row_items if col[0] <= (i["x_min"] + i["x_max"]) / 2 < col[1]]
    matched.sort(key=lambda i: (i["y_min"], i["x_min"]))
    return " ".join(i["text"] for i in matched).strip()


PLAYER_LEAD_RE = re.compile(r"^(\d{1,2})\s*([A-Z][A-Za-z,.\s]*?)(?=[a-z]|\d)")
# Period Starters cells are just "NUM Name" with nothing trailing, unlike the
# main event log's ALL-CAPS-name-then-lowercase-action format PLAYER_LEAD_RE
# is tuned for -- its non-greedy lookahead stops at the first internal
# lowercase letter, which for a Title Case name ("Wilkinson") is character 2.
STARTER_NAME_RE = re.compile(r"^(\d{1,2})\s*(.+)$")
TRAILING_COUNT_RE = re.compile(r"\((\d+)\)\s*$")
FOUL_COUNT_RE = re.compile(r"\((\d+)\s*-\s*(\d+)\)\s*$")
SHOT_VALUE_RE = re.compile(r"(\d)\s*pt\s*FG", re.IGNORECASE)


def _classify_event(text: str) -> dict:
    """Best-effort classification of one team-column cell's event text."""
    lower = text.lower().replace(" ", "")

    event = {"raw_text": text, "event_type": None, "points": 0, "stat_count": None,
              "player_number": None, "player_name_raw": None}

    lead = PLAYER_LEAD_RE.match(text)
    if lead:
        event["player_number"] = int(lead.group(1))
        event["player_name_raw"] = lead.group(2).strip(" ,.")

    if "substitution" in lower:
        event["event_type"] = "substitution_in" if "in" in lower[-4:] else "substitution_out"
    elif "timeout" in lower:
        event["event_type"] = "timeout"
    elif "jumpball" in lower:
        event["event_type"] = "jumpball_won" if "won" in lower else "jumpball_lost"
    elif SHOT_VALUE_RE.search(text):
        # Must be checked before turnover/rebound: shot descriptions often carry
        # qualifiers like "from turnover" or "second chance" that would otherwise
        # be mistaken for those event types, silently dropping the points.
        shot_value = int(SHOT_VALUE_RE.search(text).group(1))
        made = "made" in lower
        event["event_type"] = "fg_made" if made else "fg_missed"
        event["points"] = shot_value if made else 0
        m = TRAILING_COUNT_RE.search(text)
        if m:
            event["stat_count"] = int(m.group(1))
    elif "freethrow" in lower:
        made = "made" in lower
        event["event_type"] = "ft_made" if made else "ft_missed"
        event["points"] = 1 if made else 0
        m = TRAILING_COUNT_RE.search(text)
        if m:
            event["stat_count"] = int(m.group(1))
    elif "assist" in lower:
        event["event_type"] = "assist"
        m = TRAILING_COUNT_RE.search(text)
        if m:
            event["stat_count"] = int(m.group(1))
    elif "rebound" in lower:
        event["event_type"] = "rebound_offensive" if "offensive" in lower else "rebound_defensive"
        m = TRAILING_COUNT_RE.search(text)
        if m:
            event["stat_count"] = int(m.group(1))
    elif "turnover" in lower:
        event["event_type"] = "turnover"
        m = TRAILING_COUNT_RE.search(text)
        if m:
            event["stat_count"] = int(m.group(1))
    elif "steal" in lower:
        event["event_type"] = "steal"
        m = TRAILING_COUNT_RE.search(text)
        if m:
            event["stat_count"] = int(m.group(1))
    elif "foul" in lower:
        event["event_type"] = "foul_drawn" if "drawn" in lower else "foul_personal"
        m = FOUL_COUNT_RE.search(text)
        if m:
            event["stat_count"] = int(m.group(1))
    elif "block" in lower:
        event["event_type"] = "block"
        m = TRAILING_COUNT_RE.search(text)
        if m:
            event["stat_count"] = int(m.group(1))

    return event


STARTER_LABEL_RE = re.compile(r"^(ARK|[A-Z]{2,4})$")


def _cluster_by_x(items: list[dict], gap: float = 40) -> list[list[dict]]:
    """Group items into column clusters by x-gap -- robust to OCR splitting
    a single logical cell ("5 Wilkinson J") into multiple boxes, which it
    does inconsistently even across otherwise-identical page renders.
    """
    ordered = sorted(items, key=lambda i: i["x_min"])
    clusters: list[list[dict]] = []
    current: list[dict] = []
    last_x_max = None
    for item in ordered:
        if last_x_max is not None and item["x_min"] - last_x_max > gap:
            clusters.append(current)
            current = []
        current.append(item)
        last_x_max = item["x_max"]
    if current:
        clusters.append(current)
    return clusters


def _cluster_by_y(items: list[dict], gap: float = 20) -> list[list[dict]]:
    """Group items into row clusters by y-gap. Used instead of trusting a
    fixed offset from the row's own team-marker label, whose y-position
    relative to its row's content shifts a few px run to run (OCR bounding
    boxes aren't perfectly reproducible even on an identical page render).
    Clustering the actual content's y-positions is robust to that drift.
    """
    ordered = sorted(items, key=lambda i: i["y_min"])
    clusters: list[list[dict]] = []
    current: list[dict] = []
    last_y = None
    for item in ordered:
        if last_y is not None and item["y_min"] - last_y > gap:
            clusters.append(current)
            current = []
        current.append(item)
        last_y = item["y_min"]
    if current:
        clusters.append(current)
    return clusters


def _extract_period_starters(items: list[dict]) -> list[dict]:
    """Pull the "Period Starters" box (5 ARK + 5 opponent names) off the
    first page of a half, before _strip_page_chrome removes it. Returns
    [] on continuation pages that don't have this block.

    OCR chunks the "Period Starters:" label and each "NUM Name I" cell
    inconsistently run to run -- sometimes one box, sometimes split into
    several, sometimes with duplicate overlapping detections for the same
    cell -- even on visually identical page renders. This clusters the
    actual content by position (y then x) rather than trusting any single
    marker's exact coordinates, and dedupes same-jersey-number entries by
    keeping the longest (most complete) name reconstruction.
    """
    label = next(
        (i for i in items if "starters" in i["text"].lower().replace(" ", "")), None
    )
    header = next(
        (i for i in items if i["text"].replace(" ", "").lower() == "gametime"), None
    )
    if label is None:
        return []
    region_end = header["y_min"] if header is not None else label["y_min"] + 200

    candidates = [
        i for i in items
        if label["y_min"] < i["y_min"] < region_end and i["x_min"] >= 135
    ]
    markers = [
        i for i in items
        if label["y_min"] < i["y_min"] < region_end and i["x_min"] < 135
        and STARTER_LABEL_RE.match(i["text"].strip())
    ]

    raw_starters = []
    for row in _cluster_by_y(candidates):
        row_y = sum(i["y_min"] for i in row) / len(row)
        marker = min(markers, key=lambda m: abs(m["y_min"] - row_y), default=None)
        if marker is None or abs(marker["y_min"] - row_y) > 40:
            continue  # no confident team label for this row; skip rather than guess
        team = "ARK" if marker["text"].strip() == "ARK" else "OPP"

        for cluster in _cluster_by_x(row):
            cell_text = " ".join(i["text"] for i in sorted(cluster, key=lambda i: i["x_min"]))
            lead = STARTER_NAME_RE.match(cell_text)
            if not lead:
                continue
            raw_starters.append({
                "team": team,
                "player_number": int(lead.group(1)),
                "player_name_raw": lead.group(2).strip(" ,."),
            })

    # Dedupe: OCR occasionally emits overlapping partial + full detections
    # for the same cell (e.g. "H" and "HUNTER S" for the same jersey number).
    best_by_key: dict[tuple[str, int], dict] = {}
    for s in raw_starters:
        key = (s["team"], s["player_number"])
        if key not in best_by_key or len(s["player_name_raw"]) > len(best_by_key[key]["player_name_raw"]):
            best_by_key[key] = s

    starters = []
    for s in best_by_key.values():
        roster_match = _match_roster_player(s["player_name_raw"]) if s["team"] == "ARK" else None
        starters.append({
            **s,
            "player_id": roster_match["player_id"] if roster_match else None,
            "player_name_matched": roster_match["name"] if roster_match else None,
        })
    return starters


def _strip_page_chrome(items: list[dict]) -> list[dict]:
    """Drop everything above the "Game Time" column header.

    Each page repeats the game/venue/officials header block, and the first
    page of a half also has a "Period Starters" box, above the actual table.
    The table header's own y-position varies page to page depending on
    whether that block is present, so anchor the cutoff on the literal
    "Game Time" header label rather than a fixed y value -- otherwise the
    first row's anchor window (which has no previous anchor to bound it)
    sweeps all of that chrome text into the first event.
    """
    header = next(
        (i for i in items if i["text"].replace(" ", "").lower() == "gametime"), None
    )
    if header is None:
        return items
    return [i for i in items if i["y_min"] > header["y_max"]]


def _half_page_indices(total_pages: int) -> tuple[range, range]:
    first_half = range(1, 7)
    second_half = range(8, total_pages - 1)
    return first_half, second_half


def parse_play_by_play(pdf_path: Path) -> tuple[list[dict], list[dict]]:
    game_id = pdf_path.stem
    doc = fitz.open(str(pdf_path))
    total_pages = doc.page_count
    doc.close()

    first_half_pages, second_half_pages = _half_page_indices(total_pages)
    events = []
    period_starters = []
    seq = 0

    for half, pages in (("H1", first_half_pages), ("H2", second_half_pages)):
        for page_index in pages:
            raw_items = _ocr_page(pdf_path, page_index)
            if page_index == pages[0]:
                for starter in _extract_period_starters(raw_items):
                    period_starters.append({"game_id": game_id, "half": half, **starter})
            items = _strip_page_chrome(raw_items)
            for row in _rows_from_page(items):
                score_text = _text_in_column(row["items"], COL_SCORE)
                diff_text = _text_in_column(row["items"], COL_DIFF)
                ark_text = _text_in_column(row["items"], COL_ARK)
                opp_text = _text_in_column(row["items"], COL_OPP)

                for team, cell_text in (("ARK", ark_text), ("OPP", opp_text)):
                    if not cell_text:
                        continue
                    parsed = _classify_event(cell_text)
                    if parsed["event_type"] is None and not parsed["player_name_raw"]:
                        continue  # unrecognized/noise fragment
                    roster_match = _match_roster_player(parsed["player_name_raw"]) if (
                        team == "ARK" and parsed["player_name_raw"]
                    ) else None
                    events.append({
                        "game_id": game_id,
                        "event_seq": seq,
                        "half": half,
                        "page_index": page_index,
                        "game_time": row["game_time"],
                        "team": team,
                        "score": score_text or None,
                        "diff": diff_text or None,
                        "event_type": parsed["event_type"],
                        "points": parsed["points"],
                        "stat_count": parsed["stat_count"],
                        "player_number": parsed["player_number"],
                        "player_name_raw": parsed["player_name_raw"],
                        "player_id": roster_match["player_id"] if roster_match else None,
                        "player_name_matched": roster_match["name"] if roster_match else None,
                        "raw_text": parsed["raw_text"],
                    })
                    seq += 1
    return events, period_starters


def _ensure_schema(conn: sqlite3.Connection) -> None:
    # Recreated from scratch each run (this data is always fully regenerated
    # from the PDFs, never incrementally updated), so schema changes -- like
    # adding event_seq -- don't need a migration path.
    conn.execute("DROP TABLE IF EXISTS play_by_play_events")
    conn.execute("DROP TABLE IF EXISTS period_starters")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS play_by_play_events (
            game_id TEXT,
            event_seq INTEGER,
            half TEXT,
            page_index INTEGER,
            game_time TEXT,
            team TEXT,
            score TEXT,
            diff TEXT,
            event_type TEXT,
            points INTEGER,
            stat_count INTEGER,
            player_number INTEGER,
            player_name_raw TEXT,
            player_id TEXT,
            player_name_matched TEXT,
            raw_text TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS period_starters (
            game_id TEXT,
            half TEXT,
            team TEXT,
            player_number INTEGER,
            player_name_raw TEXT,
            player_id TEXT,
            player_name_matched TEXT
        )
        """
    )


def save_game(conn: sqlite3.Connection, game_id: str, events: list[dict], period_starters: list[dict]) -> int:
    # Caller (main()) must have already called _ensure_schema() once. It's
    # not safe to call again here: it now DROPs and recreates both tables
    # (to allow schema changes without a migration path), and save_game is
    # called once per game in a loop -- calling it here would wipe out every
    # previously-saved game each time the next one is processed.
    cur = conn.cursor()
    cur.execute("DELETE FROM play_by_play_events WHERE game_id = ?", (game_id,))
    cur.execute("DELETE FROM period_starters WHERE game_id = ?", (game_id,))
    for e in events:
        cur.execute(
            """
            INSERT INTO play_by_play_events (
                game_id, event_seq, half, page_index, game_time, team, score, diff,
                event_type, points, stat_count, player_number, player_name_raw,
                player_id, player_name_matched, raw_text
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                e["game_id"], e["event_seq"], e["half"], e["page_index"], e["game_time"], e["team"],
                e["score"], e["diff"], e["event_type"], e["points"], e["stat_count"],
                e["player_number"], e["player_name_raw"], e["player_id"],
                e["player_name_matched"], e["raw_text"],
            ),
        )
    for s in period_starters:
        cur.execute(
            """
            INSERT INTO period_starters (
                game_id, half, team, player_number, player_name_raw, player_id, player_name_matched
            ) VALUES (?,?,?,?,?,?,?)
            """,
            (
                s["game_id"], s["half"], s["team"], s["player_number"],
                s["player_name_raw"], s["player_id"], s["player_name_matched"],
            ),
        )
    conn.commit()
    return len(events)


def validate_against_box_score(conn: sqlite3.Connection, game_id: str) -> None:
    box = dict(
        conn.execute(
            "SELECT player_id, pts FROM player_game_stats WHERE game_id=? AND team='ARK' AND player_id IS NOT NULL",
            (game_id,),
        ).fetchall()
    )
    pbp = conn.execute(
        """
        SELECT player_id, SUM(points) FROM play_by_play_events
        WHERE game_id=? AND team='ARK' AND player_id IS NOT NULL
        GROUP BY player_id
        """,
        (game_id,),
    ).fetchall()
    pbp_points = {pid: pts or 0 for pid, pts in pbp}

    mismatches = []
    for player_id, box_pts in box.items():
        pbp_pts = pbp_points.get(player_id, 0)
        if pbp_pts != box_pts:
            mismatches.append((player_id, box_pts, pbp_pts))

    if mismatches:
        print(f"  VALIDATION MISMATCH for {game_id}: (player_id, box_score_pts, play_by_play_pts)")
        for m in mismatches:
            print(f"    {m}")
    else:
        print(f"  Validation OK: play-by-play points match box score for all {len(box)} matched Arkansas players")


def main() -> None:
    pdf_files = sorted(DOCS_DIR.glob("Baha-Mar-Summer-Stats-*.pdf"))
    conn = sqlite3.connect(str(DB_PATH))
    _ensure_schema(conn)

    for pdf_path in pdf_files:
        if pdf_path.stem in EXCLUDED_GAME_IDS:
            continue
        print(f"Parsing play-by-play: {pdf_path.name} ...")
        events, period_starters = parse_play_by_play(pdf_path)
        n = save_game(conn, pdf_path.stem, events, period_starters)
        print(f"  {n} events parsed, {len(period_starters)} period-starter entries")
        validate_against_box_score(conn, pdf_path.stem)

    conn.close()


if __name__ == "__main__":
    main()
