"""
WAIMS Sport Configuration - Extended
====================================
Multi-sport support: WNBA Basketball (female) and Men's College Basketball (Power 5)

Key differences:
- WNBA: female population, shorter season (40 games), different thresholds
- Men's Power 5: male population, college schedule, higher loads

Springbok Analytics note
------------------------
Springbok Analytics is an independent MRI (Match and Rotation Intelligence) platform.
Second Spectrum is the official NBA/WNBA optical tracking provider.
Both are potential data sources for V2/V3, not sport configs.

Adding a new team
-----------------
Add a new entry to TEAM_CONFIGS with team-specific threshold calibrations.
Sport-level defaults apply unless explicitly overridden.

Usage
-----
    from common.sport_config_extended import get_sport_config, get_team_config
    
    config = get_sport_config("wnba_basketball")  # WNBA defaults
    config = get_sport_config("mens_power5_basketball")  # Men's Power 5 defaults
    team_config = get_team_config("arkansas_razorbacks")  # team-specific
"""

# ==============================================================================
# ACTIVE DEFAULTS
# ==============================================================================
ACTIVE_SPORT = "wnba_basketball"
ACTIVE_TEAM  = "arkansas_razorbacks"  # For men's version


# ==============================================================================
# WNBA BASKETBALL — SPORT-LEVEL CONFIG
# ==============================================================================

SPORT_CONFIGS = {

    "wnba_basketball": {
        "display_name": "WNBA Basketball",
        "population":   "female",
        "league":       "WNBA",
        "level":        "professional",

        # Readiness formula weights (must sum to 100)
        "readiness_weights": {
            "cmj_zscore":   35,
            "rsi_modified": 25,
            "sleep_hours":  20,
            "soreness":     10,
            "mood_stress":  10,
        },

        # Absolute thresholds — evidence-based defaults
        "thresholds": {
            "sleep_minimum_hrs":      6.0,
            "sleep_flag_hrs":         7.0,
            "sleep_target_hrs":       9.0,
            "soreness_action":        7,
            "acwr_flag":              1.5,
            "acwr_caution":           1.3,
            "cmj_zscore_flag":       -1.0,
            "cmj_zscore_high":       -1.5,
            "rsi_zscore_flag":       -1.0,
            "minutes_4day_flag":      120,
            "minutes_4day_b2b_flag":  80,
        },

        # Position groups
        "position_groups": {
            "Guards":   ["G", "PG", "SG", "G/F"],
            "Wings":    ["F", "SF", "SG/SF", "G/F"],
            "Bigs":     ["C", "PF", "C/PF", "F/C"],
        },

        # GPS configuration
        "gps_priority_metric":   "decel_count",
        "gps_secondary_metrics": ["hsr_distance", "sprint_distance", "accel_count",
                                   "practice_minutes"],

        # Schedule / recovery
        "typical_recovery_days":  1,
        "b2b_common":             True,
        "season_games":           40,
        "acwr_chronic_window":    28,
        "rolling_baseline_days":  14,

        # Validation scope
        "primary_injury_target":  "non_contact_soft_tissue",
        "contact_injury_excluded": True,

        # Compliance
        "compliance": {
            "primary_regulation": "HIPAA",
            "secondary": [
                "GDPR (EU-national athletes)",
                "WNBA CBA biometric data provisions",
            ],
            "consent_required": True,
            "data_residency":   "US",
        },

        # Evidence base
        "key_evidence": [
            "Janetzki et al. 2023 (CMJ height, r=0.69 sprint — 165-study SR/meta)",
            "Gathercole et al. 2015 (RSI-Mod, elite female rugby 7s)",
            "Walsh et al. 2021 BJSM (sleep consensus)",
            "Mah et al. 2011 (sleep extension RCT, female basketball)",
            "Pimenta et al. 2026 SR/meta (WNBA — sleep +12-18% performance)",
            "Saw et al. 2016 SR (subjective wellness, 56 studies)",
            "Boskovic et al. 2024 GPS 3.0 (decel count priority)",
            "Impellizzeri et al. 2020 BJSM (ACWR limitations)",
        ],
    },

    # ==============================================================================
    # MEN'S POWER 5 COLLEGE BASKETBALL — SPORT-LEVEL CONFIG
    # ==============================================================================
    
    "mens_power5_basketball": {
        "display_name": "Men's College Basketball (Power 5)",
        "population":   "male",
        "league":       "NCAA Division I - Power 5",
        "level":        "collegiate",

        # Readiness formula weights (adjusted for male physiology and college context)
        "readiness_weights": {
            "cmj_zscore":   30,      # Slightly lower — males more consistent
            "rsi_modified": 25,
            "sleep_hours":  25,      # Higher weight — college recovery crucial
            "soreness":     10,
            "mood_stress":  10,
        },

        # Absolute thresholds — adjusted for male population
        # Males typically have higher force production, different sleep needs
        "thresholds": {
            "sleep_minimum_hrs":      6.5,   # Slightly higher floor for males
            "sleep_flag_hrs":         7.5,   # Higher flag (college lifestyle)
            "sleep_target_hrs":       9.5,   # Higher target
            "soreness_action":        6,     # Slightly lower — collegiate athletes report differently
            "acwr_flag":              1.5,
            "acwr_caution":           1.3,
            "cmj_zscore_flag":       -0.9,   # Slightly higher threshold (males more consistent)
            "cmj_zscore_high":       -1.3,
            "rsi_zscore_flag":       -0.9,
            "minutes_4day_flag":      130,   # Slightly higher for collegiate (college games ~40 min)
            "minutes_4day_b2b_flag":  90,    # College B2B common (tournament play)
        },

        # Position groups (same as WNBA)
        "position_groups": {
            "Guards":   ["PG", "SG", "G"],
            "Wings":    ["SF", "PF", "F"],
            "Bigs":     ["C", "B"],
        },

        # GPS configuration (same priority)
        "gps_priority_metric":   "decel_count",
        "gps_secondary_metrics": ["hsr_distance", "sprint_distance", "accel_count",
                                   "practice_minutes"],

        # Schedule / recovery (college-specific)
        "typical_recovery_days":  1,
        "b2b_common":             True,      # Tournament play = frequent B2B
        "season_games":           35,        # NCAA reg season ~35 games
        "acwr_chronic_window":    28,
        "rolling_baseline_days":  14,

        # Validation scope
        "primary_injury_target":  "non_contact_soft_tissue",
        "contact_injury_excluded": True,

        # Compliance (college-specific)
        "compliance": {
            "primary_regulation": "HIPAA",
            "secondary": [
                "FERPA (student-athlete records)",
                "NCAA eligibility and health rules",
                "State consent laws (varies by institution)",
            ],
            "consent_required": True,
            "data_residency":   "US",
        },

        # Evidence base (adjusted for men/college)
        "key_evidence": [
            "Janetzki et al. 2023 (CMJ height, r=0.69 sprint — all populations)",
            "Gathercole et al. 2015 (RSI-Mod, elite athletes)",
            "Walsh et al. 2021 BJSM (sleep consensus — all populations)",
            "Mah et al. 2011 (sleep extension, basketball — includes male subjects)",
            "Saw et al. 2016 SR (subjective wellness, 56 studies)",
            "Boskovic et al. 2024 GPS 3.0 (decel count priority)",
            "Impellizzeri et al. 2020 BJSM (ACWR — sport-agnostic)",
            "Beckham et al. 2020 (college athlete fatigue patterns)",
        ],
    },
}


# ==============================================================================
# TEAM-LEVEL OVERRIDES
# ==============================================================================

TEAM_CONFIGS = {

    # ==============================================================================
    # WNBA TEAMS
    # ==============================================================================

    "dallas_wings": {
        "display_name": "Dallas Wings (WNBA Demo)",
        "sport":        "wnba_basketball",
        "demo":         True,
        "threshold_overrides": {},
        "notes": (
            "Demo team. All data synthetic. Thresholds use WNBA sport defaults. "
            "In production: calibrate with Wings coaching and medical staff."
        ),
    },

    # ==============================================================================
    # MEN'S COLLEGE BASKETBALL TEAMS
    # ==============================================================================

    "arkansas_razorbacks": {
        "display_name": "Arkansas Razorbacks",
        "sport":        "mens_power5_basketball",
        "demo":         False,
        "conference":   "SEC",
        "threshold_overrides": {
            # Arkansas-specific calibrations (can be adjusted post-season)
            "minutes_4day_flag":      135,   # Arkansas runs deep lineups, slightly higher
        },
        "notes": (
            "Arkansas Razorbacks Men's Basketball (SEC). "
            "Real roster data. Thresholds calibrated for SEC play. "
            "This is a portfolio demo — not for live team deployment."
        ),
    },

    # Template for adding more Power 5 teams
    # "duke_blue_devils": {
    #     "display_name": "Duke Blue Devils",
    #     "sport": "mens_power5_basketball",
    #     "conference": "ACC",
    #     "threshold_overrides": {},
    #     "notes": "ACC Power 5 team",
    # },
}


# ==============================================================================
# ACCESSOR FUNCTIONS
# ==============================================================================

def get_sport_config(sport: str = None) -> dict:
    """Return config dict for specified sport. Defaults to ACTIVE_SPORT."""
    sport = sport or ACTIVE_SPORT
    if sport not in SPORT_CONFIGS:
        raise KeyError(
            f"Sport '{sport}' not in SPORT_CONFIGS. Available: {list(SPORT_CONFIGS.keys())}"
        )
    return SPORT_CONFIGS[sport]


def get_team_config(team: str = None) -> dict:
    """Return team config with sport defaults merged with team overrides."""
    team = team or ACTIVE_TEAM
    team_cfg   = TEAM_CONFIGS.get(team, {})
    sport_name = team_cfg.get("sport", ACTIVE_SPORT)
    sport_cfg  = get_sport_config(sport_name)

    # Merge: start with sport defaults, apply team overrides
    merged = dict(sport_cfg)
    merged["thresholds"] = {
        **sport_cfg["thresholds"],
        **team_cfg.get("threshold_overrides", {}),
    }
    merged["team_display_name"] = team_cfg.get("display_name", team)
    merged["team_notes"]        = team_cfg.get("notes", "")
    merged["conference"]        = team_cfg.get("conference", "N/A")
    return merged


def get_thresholds(team: str = None) -> dict:
    """Shortcut — thresholds for active team."""
    return get_team_config(team)["thresholds"]


def get_position_groups(sport: str = None) -> dict:
    """Shortcut — position groups for active sport."""
    return get_sport_config(sport)["position_groups"]


def get_compliance_info(sport: str = None) -> dict:
    """Shortcut — compliance/legal info for active sport."""
    return get_sport_config(sport)["compliance"]


def list_supported_sports() -> list:
    return list(SPORT_CONFIGS.keys())


def list_supported_teams() -> list:
    return list(TEAM_CONFIGS.keys())


def get_teams_by_sport(sport: str) -> list:
    """Return all teams configured for a given sport."""
    return [team for team, cfg in TEAM_CONFIGS.items() if cfg.get("sport") == sport]


# Maps dashboard.py's WAIMS_SPORT values ("wnba"/"mens") to the demo team
# whose thresholds should be active. Update this if a second team is ever
# added for either sport.
SPORT_KEY_TO_TEAM = {
    "wnba": "dallas_wings",
    "mens": "arkansas_razorbacks",
}


def get_thresholds_for_sport_key(sport_key: str) -> dict:
    """Thresholds for dashboard.py's WAIMS_SPORT value ("wnba" or "mens").
    Falls back to the WNBA defaults for an unrecognized key.
    """
    team = SPORT_KEY_TO_TEAM.get(sport_key, "dallas_wings")
    return get_thresholds(team)
