"""
WAIMS Sport Configuration
==========================
Sport-specific threshold defaults, GPS metric priorities, position groups,
compliance notes, and validation scope settings.

Currently supports WNBA basketball.

Springbok Analytics note
-------------------------
Springbok Analytics is an independent MRI (Match and Rotation Intelligence) platform
used by NBA/WNBA teams for lineup analytics and play data.
Second Spectrum is a separate company and the official NBA/WNBA optical tracking provider.
In WAIMS V2/V3, both Springbok Analytics and Second Spectrum are potential data sources
for live game load and contextual performance data — not sport configs.
See V2 roadmap: optical tracking integration for game-context load.

Adding a new team
-----------------
Add a new entry to TEAM_CONFIGS dict below with team-specific threshold
calibrations. The sport-level defaults apply unless overridden.

Usage
-----
    from sport_config import get_sport_config, get_team_config

    config       = get_sport_config()            # WNBA basketball defaults
    team_config  = get_team_config("dallas_wings")  # team-specific overrides
    thresholds   = config["thresholds"]
    positions    = config["position_groups"]
"""

# ==============================================================================
# ACTIVE DEFAULTS
# ==============================================================================
ACTIVE_SPORT = "wnba_basketball"
ACTIVE_TEAM  = "dallas_wings"


# ==============================================================================
# WNBA BASKETBALL — SPORT-LEVEL CONFIG
# ==============================================================================

SPORT_CONFIGS = {

    "wnba_basketball": {
        "display_name": "WNBA Basketball",
        "population":   "female",

        # Readiness formula weights (must sum to 100)
        "readiness_weights": {
            "cmj_zscore":   35,
            "rsi_modified": 25,
            "sleep_hours":  20,
            "soreness":     10,
            "mood_stress":  10,
        },

        # Absolute thresholds — evidence-based defaults
        # These are the STARTING POINT. Adjusted per team via TEAM_CONFIGS below.
        "thresholds": {
            "sleep_minimum_hrs":      6.0,   # hard floor (Walsh 2021)
            "sleep_flag_hrs":         7.0,   # flag threshold (Walsh 2021)
            "sleep_target_hrs":       9.0,   # optimal target (Mah 2011 WNBA RCT)
            "soreness_action":        7,     # >7 requires action (Hulin 2016)
            "acwr_flag":              1.5,   # contextual flag only (Impellizzeri 2020)
            "acwr_caution":           1.3,
            "cmj_zscore_flag":       -1.0,
            "cmj_zscore_high":       -1.5,
            "rsi_zscore_flag":       -1.0,
            "minutes_4day_flag":      120,   # heavy legs flag
            "minutes_4day_b2b_flag":  80,    # lower threshold on B2B nights
        },

        # Position groups for Command Center positional strip
        # V2: positional decel/load norms should be calculated within these groups
        "position_groups": {
            "Guards":   ["G", "PG", "SG", "G/F"],
            "Wings":    ["F", "SF", "SG/SF", "G/F"],
            "Bigs":     ["C", "PF", "C/PF", "F/C"],
        },

        # GPS configuration
        "gps_priority_metric":   "decel_count",
        "gps_secondary_metrics": ["hsr_distance", "sprint_distance", "accel_count",
                                   "practice_minutes"],
        "gps_note": (
            "Deceleration count is the primary GPS metric for basketball injury risk. "
            "HSR and sprint distance miss ~70% of multidirectional load (Boskovic 2024 GPS 3.0). "
            "V2: Springbok Analytics (independent MRI platform) and Second Spectrum (official NBA/WNBA "
            "context for decel events in game settings."
        ),

        # Positional GPS norms — V2 feature
        # TODO V2: Calculate positional baseline windows per position group
        # Guards accumulate higher decel counts than bigs — population norm inappropriate
        "positional_gps_norms": {
            "enabled": False,   # V2 — not yet implemented
            "note": (
                "Individualized positional decel thresholds needed in V2. "
                "A point guard's decel profile differs structurally from a center. "
                "Use position-group z-scores rather than whole-team baseline."
            ),
        },

        # Schedule / recovery
        "typical_recovery_days":  1,
        "b2b_common":             True,
        "season_games":           40,
        "acwr_chronic_window":    28,
        "rolling_baseline_days":  14,   # shorter than soccer/rugby lit

        # Validation scope
        "primary_injury_target":  "non_contact_soft_tissue",
        "contact_injury_excluded": True,
        "validation_note": (
            "Non-contact soft tissue injuries are the primary target. "
            "Contact injuries explicitly excluded — no monitoring system "
            "predicts collision events."
        ),

        # Compliance / legal
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
            "Walsh et al. 2021 BJSM (sleep consensus — all athlete populations)",
            "Mah et al. 2011 (sleep extension RCT, female basketball players)",
            "Pimenta et al. 2026 SR/meta (WNBA — sleep extension +12-18% performance)",
            "Saw et al. 2016 SR (subjective wellness, 56 studies)",
            "Boskovic et al. 2024 GPS 3.0 (decel count priority)",
            "Impellizzeri et al. 2020 BJSM (ACWR limitations)",
        ],
    },
}


# ==============================================================================
# TEAM-LEVEL OVERRIDES
# Teams can adjust thresholds from sport-level defaults after calibration
# with coaching and medical staff. No override = sport default applies.
# ==============================================================================

TEAM_CONFIGS = {

    "dallas_wings": {
        "display_name": "WNBA Demo Team",
        "sport":        "wnba_basketball",
        "demo":         True,
        "threshold_overrides": {},  # No overrides yet — using sport defaults
        "notes": (
            "Demo team. All data synthetic. Thresholds use WNBA sport defaults. "
            "In production: calibrate thresholds with Wings coaching and medical staff."
        ),
    },

    # Add real teams here as WAIMS is deployed
    # "team_name": {
    #     "display_name": "Team Name",
    #     "sport": "wnba_basketball",
    #     "threshold_overrides": {
    #         "minutes_4day_flag": 110,  # team-specific calibration
    #     },
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
    return merged


def get_thresholds(team: str = None) -> dict:
    """Shortcut — thresholds for active team (sport defaults + team overrides)."""
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
