import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "waims-mens"))

from roster_arkansas import ARKANSAS_ROSTER_2026


def test_arkansas_roster_uses_real_2026_27_players():
    names = {player["name"] for player in ARKANSAS_ROSTER_2026}

    assert len(ARKANSAS_ROSTER_2026) == 15
    assert "Caleb Ourigou" in names
    assert "Abdou Toure" in names
    assert "Amere Brown" in names
    assert "Billy Richmond III" in names
    assert "Cooper Bowser" in names
    assert "Paulo Semedo" in names
    assert "Isaiah Joe" not in names
    assert "Jaylin Williams" not in names


def test_arkansas_game_pdfs_create_importable_summary_rows():
    from scripts.build_arkansas_manual_coding_workbook import parse_game_summary_rows

    rows = parse_game_summary_rows(Path(__file__).resolve().parent / "docs")

    assert len(rows) >= 5
    assert {row["opponent"] for row in rows} >= {"Bahamas", "Carleton", "Columbia", "Toros Del Valle", "Calgary"}
    assert all(row["final_score"] for row in rows)
    assert all(row["date"] for row in rows)
