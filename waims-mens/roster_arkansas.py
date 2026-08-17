"""
Arkansas Razorbacks Men's Basketball roster source-of-truth.
==========================================================
This roster is based on the official Arkansas Razorbacks 2026-27 roster PDF
from the team site and is the correct live roster for the dashboard.

The dashboard still uses synthetic monitoring data (wellness, load, CMJ, RSI,
injury simulation) for demo analytics. The roster itself is now real.
"""

# Official Arkansas Razorbacks 2026-27 roster extracted from the Razorbacks roster PDF.
# 15 players total.
ARKANSAS_ROSTER_2026 = [
    {"player_id": "ARK001", "name": "Caleb Ourigou", "position": "F/C", "age": 18, "injury_history_count": 0},
    {"player_id": "ARK002", "name": "Abdou Toure", "position": "W", "age": 18, "injury_history_count": 0},
    {"player_id": "ARK003", "name": "Amere Brown", "position": "G", "age": 20, "injury_history_count": 0},
    {"player_id": "ARK004", "name": "Miikka Muurinen", "position": "W/F", "age": 18, "injury_history_count": 0},
    {"player_id": "ARK005", "name": "Ayden Kelley", "position": "G", "age": 21, "injury_history_count": 0},
    {"player_id": "ARK006", "name": "Jeremiah Wilkinson", "position": "G", "age": 21, "injury_history_count": 0},
    {"player_id": "ARK007", "name": "JJ Andrews", "position": "W", "age": 18, "injury_history_count": 0},
    {"player_id": "ARK008", "name": "Maper Maker", "position": "F/C", "age": 18, "injury_history_count": 0},
    {"player_id": "ARK009", "name": "Davion Thompson", "position": "G", "age": 18, "injury_history_count": 0},
    {"player_id": "ARK010", "name": "Ilia Frolov", "position": "F/C", "age": 18, "injury_history_count": 0},
    {"player_id": "ARK011", "name": "Cooper Bowser", "position": "F/C", "age": 23, "injury_history_count": 0},
    {"player_id": "ARK012", "name": "Jordan Smith Jr.", "position": "G", "age": 18, "injury_history_count": 0},
    {"player_id": "ARK013", "name": "Billy Richmond III", "position": "G/W", "age": 21, "injury_history_count": 0},
    {"player_id": "ARK014", "name": "Isaiah Sealy", "position": "W", "age": 20, "injury_history_count": 0},
    {"player_id": "ARK015", "name": "Paulo Semedo", "position": "F/C", "age": 19, "injury_history_count": 0},
]


def normalize_position(position: str) -> str:
    """Map roster labels onto standard WAIMS men's baseline keys."""
    pos = (position or "").strip().upper().replace(" ", "")
    mapping = {
        "PG": "PG",
        "SG": "SG",
        "G": "G",
        "W": "SF",
        "GF": "G",
        "GW": "G",
        "G/W": "G",
        "WG": "G",
        "SF": "SF",
        "F": "F",
        "PF": "PF",
        "FC": "C",
        "CF": "C",
        "F/C": "C",
        "W/F": "F",
        "FW": "F",
        "C": "C",
    }
    return mapping.get(pos, "F")


# Position mapping for GPS baseline calculations (Men vs Women)
GPS_BASELINES_MENS = {
    # pos: (player_load, accels, decels, distance_km, hsr_m, sprint_m)
    # Higher values than WNBA due to male physiology and college intensity
    "PG": (380, 50, 46, 7.5, 720, 220),
    "SG": (370, 48, 44, 7.3, 690, 210),
    "G": (375, 49, 45, 7.4, 705, 215),
    "SF": (350, 42, 38, 6.8, 610, 180),
    "F": (340, 40, 36, 6.6, 590, 170),
    "PF": (330, 36, 33, 6.2, 520, 140),
    "C": (310, 30, 28, 5.8, 450, 110),
}

# Defensive readiness profiles (college-specific)
# Males typically less variable in force metrics, more stable RPE reporting
READINESS_PROFILES = {
    "ARK001": {"sleep_var": 0.4, "soreness_honest": True, "stress_reporter": True},
    "ARK002": {"sleep_var": 0.7, "soreness_honest": False, "stress_reporter": False},
    "ARK003": {"sleep_var": 0.5, "soreness_honest": True, "stress_reporter": True},
    "ARK004": {"sleep_var": 0.6, "soreness_honest": True, "stress_reporter": False},
    "ARK005": {"sleep_var": 0.8, "soreness_honest": False, "stress_reporter": True},
    "ARK006": {"sleep_var": 0.4, "soreness_honest": True, "stress_reporter": True},
    "ARK007": {"sleep_var": 0.9, "soreness_honest": True, "stress_reporter": True},
    "ARK008": {"sleep_var": 0.5, "soreness_honest": True, "stress_reporter": False},
    "ARK009": {"sleep_var": 0.6, "soreness_honest": False, "stress_reporter": False},
    "ARK010": {"sleep_var": 0.4, "soreness_honest": True, "stress_reporter": True},
    "ARK011": {"sleep_var": 0.7, "soreness_honest": True, "stress_reporter": False},
    "ARK012": {"sleep_var": 0.5, "soreness_honest": True, "stress_reporter": True},
    "ARK013": {"sleep_var": 0.8, "soreness_honest": False, "stress_reporter": False},
    "ARK014": {"sleep_var": 0.6, "soreness_honest": True, "stress_reporter": True},
    "ARK015": {"sleep_var": 0.5, "soreness_honest": True, "stress_reporter": True},
}
