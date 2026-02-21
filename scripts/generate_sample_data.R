# ==============================================================================
# WAIMS-R: Production Monitoring System
# Sample Data Generator - February 2026 Context
# ==============================================================================
#
# PURPOSE:
#   Creates realistic monitoring data for demonstration purposes.
#   Context: February 2026 (off-season training period)
#   Most recent season: 2025 (May-October 2025)
#
# SCENARIO OPTIONS:
#   1. Off-season training (Dec 2025 - Feb 2026) - DEFAULT
#   2. End of 2025 season (Aug-Oct 2025) - retrospective
#
# USAGE:
#   source("scripts/generate_sample_data.R")
#
# DEPENDENCIES:
#   - tidyverse, lubridate, fs
#   - config.R (must be sourced first)
#
# AUTHOR: Chris Cothern
# DATE: 2026-02-19
# VERSION: 1.0.1 (Updated for 2025/2026 context)
# ==============================================================================

library(tidyverse)
library(lubridate)
library(fs)

source("scripts/config.R")

set.seed(42)

log_msg("=== GENERATING SAMPLE DATA ===")
log_msg(glue("Current date: {Sys.Date()}"))
log_msg("Context: Off-season training (2025 season completed)")

# ==============================================================================
# CONFIGURATION - CHOOSE SCENARIO
# ==============================================================================

# Choose which period to simulate:
SCENARIO <- "OFF_SEASON"  # Options: "OFF_SEASON", "END_OF_SEASON_2025"

if (SCENARIO == "OFF_SEASON") {
  # Simulate current off-season training (Dec 2025 - Feb 2026)
  start_date <- as.Date("2025-12-01")
  end_date <- Sys.Date()  # Today (Feb 19, 2026)
  log_msg("Scenario: Off-season training (Dec 2025 - Feb 2026)")
  
} else if (SCENARIO == "END_OF_SEASON_2025") {
  # Simulate end of 2025 season + playoffs (Aug-Oct 2025)
  start_date <- as.Date("2025-08-01")
  end_date <- as.Date("2025-10-20")
  log_msg("Scenario: End of 2025 season (Aug-Oct 2025)")
}

# ==============================================================================
# PROFESSIONAL BASKETBALL ROSTER
# ==============================================================================

# Generic roster (12 players)
# Customize with actual team roster for production use
roster <- tibble(
  athlete_id   = sprintf("ATH_%03d", 1:12),
  display_name = c(
    "Player A",          # Franchise player (high usage, injury history)
    "Player B",          # Veteran guard
    "Player C",          # All-Star forward
    "Player D",          # Starting center
    "Player E",          # Rotation forward
    "Player F",          # Rising star
    "Player G",          # Rotation guard
    "Player H",          # Depth guard
    "Player I",          # Backup center
    "Player J",          # Young prospect
    "Player K",          # Rotation forward
    "Player L"           # Versatile forward
  ),
  position = c("G","G","F","C","F","F","G","G","C","G","F","F"),
  role_tier = c(
    "Starter",   # Player A
    "Starter",   # Player B
    "Starter",   # Player C
    "Starter",   # Player D
    "Rotation",  # Player E
    "Rotation",  # Player F
    "Rotation",  # Player G
    "Bench",     # Player H
    "Bench",     # Player I
    "Bench",     # Player J
    "Bench",     # Player K
    "Bench"      # Player L
  ),
  gps_id = sprintf("GPS_%03d", 1:12),
  force_plate_id = sprintf("FP_%03d", 1:12),
  wearable_id = sprintf("WR_%03d", 1:12),
  status_active = 1,
  injury_history_count = c(3,1,4,2,3,1,1,0,1,0,2,1)  # Player A: 3 prior injuries
)

write_csv(roster, path(dirs$ref, "athlete_roster.csv"))
log_msg(glue("Created roster: {nrow(roster)} players"))

# ==============================================================================
# DATE RANGE
# ==============================================================================

dates <- seq.Date(start_date, end_date, by = "day")
log_msg(glue("Date range: {start_date} to {end_date} ({length(dates)} days)"))

# ==============================================================================
# SESSION TYPE LOGIC
# ==============================================================================

# Off-season: Mostly gym/practice, no games
# In-season: Mix of practices and games

if (SCENARIO == "OFF_SEASON") {
  # Off-season pattern: Mon-Fri training, weekends off
  is_training_day <- function(d) {
    wday(d, week_start = 1) %in% c(1,2,3,4,5)  # Mon-Fri
  }
  game_days <- as.Date(character(0))  # No games in off-season
  
} else {
  # In-season pattern: practices most days, games 3-4x per week
  is_training_day <- function(d) {
    wday(d, week_start = 1) %in% c(1,2,3,4,5,6)  # Mon-Sat
  }
  # Simulate game days (roughly every 2-3 days)
  game_days <- sample(dates[is_training_day(dates)], 
                      size = round(length(dates) * 0.4), 
                      replace = FALSE)
}

# ==============================================================================
# GPS / PRACTICE LOAD DATA
# ==============================================================================

log_msg("Generating GPS/practice load data...")

gps_data <- expand_grid(date = dates, gps_id = roster$gps_id) %>%
  left_join(roster %>% select(gps_id, display_name, position, role_tier), by = "gps_id") %>%
  mutate(
    is_game = date %in% game_days,
    is_practice = is_training_day(date) & !is_game,
    session_type = case_when(
      is_game ~ "GAME",
      is_practice ~ "PRACTICE",
      TRUE ~ "OFF"
    ),
    
    # Off-season loads are lower (strength focus, not game prep)
    load_multiplier = if_else(SCENARIO == "OFF_SEASON", 0.7, 1.0),
    
    # Minutes vary by role and session type
    minutes = case_when(
      session_type == "OFF" ~ 0,
      session_type == "GAME" & role_tier == "Starter" ~ pmax(10, rnorm(n(), 28, 5)),
      session_type == "GAME" & role_tier == "Rotation" ~ pmax(5, rnorm(n(), 18, 6)),
      session_type == "GAME" & role_tier == "Bench" ~ pmax(0, rnorm(n(), 8, 5)),
      session_type == "PRACTICE" ~ pmax(15, rnorm(n(), 60, 15) * load_multiplier),
      TRUE ~ 0
    ),
    
    # Distance scales with minutes
    distance_m = if_else(session_type != "OFF",
                         minutes * rnorm(n(), 75, 15) * load_multiplier, 0),
    
    # High-intensity distance (guards higher)
    hid_m = if_else(session_type != "OFF",
                    if_else(position == "G",
                            distance_m * rnorm(n(), 0.18, 0.04),
                            distance_m * rnorm(n(), 0.12, 0.03)),
                    0),
    
    # Peak speed
    peak_speed_m_s = if_else(session_type != "OFF",
                             pmax(5.0, rnorm(n(), 7.5, 0.8)), NA_real_),
    
    # Accelerations/decelerations (game > practice > off-season)
    accel_hi_count = case_when(
      session_type == "GAME" ~ pmax(0, round(rnorm(n(), 35, 12))),
      session_type == "PRACTICE" ~ pmax(0, round(rnorm(n(), 22, 8) * load_multiplier)),
      TRUE ~ 0L
    ),
    
    decel_hi_count = case_when(
      session_type == "GAME" ~ pmax(0, round(rnorm(n(), 38, 13))),
      session_type == "PRACTICE" ~ pmax(0, round(rnorm(n(), 24, 9) * load_multiplier)),
      TRUE ~ 0L
    ),
    
    # Player load index (composite metric)
    player_load = distance_m/100 + accel_hi_count*1.5 + decel_hi_count*1.5 + hid_m/40
  )

# Add realistic scenario: High-usage player accumulation
# Player A: Gradual load increase (off-season preparation for next season)
if (SCENARIO == "OFF_SEASON") {
  gps_data <- gps_data %>%
    mutate(
      # Player A ramping up for 2026 season
      player_load = if_else(
        display_name == "Player A" & row_number() > n()/2,
        player_load * runif(n(), 1.1, 1.3),  # Increase in second half
        player_load
      )
    )
}

# Export GPS data
gps_export <- gps_data %>%
  transmute(
    athlete_id = gps_id,
    date,
    session_type,
    minutes = round(minutes, 1),
    distance_m = round(distance_m, 0),
    hid_m = round(hid_m, 0),
    peak_speed_m_s = round(peak_speed_m_s, 2),
    accel_hi_count,
    decel_hi_count,
    player_load = round(player_load, 1)
  )

gps_file <- path(dirs$raw_gps, glue("{format(Sys.Date(), '%Y%m%d')}_gps_practice.csv"))
write_csv(gps_export, gps_file)
log_msg(glue("Created: {gps_file} ({nrow(gps_export)} records)"))

# ==============================================================================
# WELLNESS DATA (Daily Subjective)
# ==============================================================================

log_msg("Generating wellness data...")

wellness <- expand_grid(date = dates, athlete_id = roster$athlete_id) %>%
  left_join(roster %>% select(athlete_id, display_name, injury_history_count), by = "athlete_id") %>%
  left_join(
    gps_data %>% select(gps_id, date, session_type, player_load),
    by = c("date" = "date")
  ) %>%
  group_by(athlete_id) %>%
  arrange(date) %>%
  mutate(
    # Days into current period
    days_in_period = as.numeric(date - min(dates)),
    
    # Off-season = better sleep (less travel, less stress)
    base_sleep = if_else(SCENARIO == "OFF_SEASON", 8.0, 7.5),
    
    # Sleep varies with load
    sleep_hours = pmin(9.5, pmax(5.5,
      base_sleep - (days_in_period / max(days_in_period)) * 0.8 + rnorm(n(), 0, 0.6)
    )),
    
    # Soreness correlates with load
    load_lag1 = lag(player_load, 1, default = 0),
    soreness_0_10 = pmin(10, pmax(0, round(
      1 + injury_history_count * 0.3 + load_lag1 / 40 + rnorm(n(), 0, 1.5)
    ))),
    
    # Fatigue (off-season = lower)
    base_fatigue = if_else(SCENARIO == "OFF_SEASON", 2, 3),
    fatigue_0_10 = pmin(10, pmax(0, round(
      base_fatigue + (days_in_period / max(days_in_period)) * 2 + 
      (10 - sleep_hours) * 0.5 + rnorm(n(), 0, 1.5)
    ))),
    
    # Stress (off-season = lower)
    base_stress = if_else(SCENARIO == "OFF_SEASON", 2, 3),
    stress_0_10 = pmin(10, pmax(0, round(
      base_stress + rnorm(n(), 0, 2.0)
    ))),
    
    # Mood (inverse of stress/fatigue)
    mood_0_10 = pmin(10, pmax(0, round(
      8 - fatigue_0_10 * 0.3 - stress_0_10 * 0.2 + rnorm(n(), 0, 1.0)
    ))),
    
    # Pain (lower in off-season due to recovery time)
    pain_knee_0_10 = pmin(10, pmax(0, round(
      if_else(SCENARIO == "OFF_SEASON", 0.5, 1.5) +
      soreness_0_10 * 0.2 + rnorm(n(), 0, 1.0)
    ))),
    
    free_text = ""
  ) %>%
  ungroup()

wellness_export <- wellness %>%
  transmute(
    date,
    athlete_id,
    sleep_hours = round(sleep_hours, 1),
    soreness_0_10,
    fatigue_0_10,
    stress_0_10,
    mood_0_10,
    pain_knee_0_10,
    free_text
  )

well_file <- path(dirs$raw_wellness, glue("{format(Sys.Date(), '%Y%m%d')}_wellness.csv"))
write_csv(wellness_export, well_file)
log_msg(glue("Created: {well_file} ({nrow(wellness_export)} records)"))

# ==============================================================================
# FORCE PLATE DATA (Weekly Testing)
# ==============================================================================

log_msg("Generating force plate data...")

# Test on Mondays (weekly)
test_dates <- dates[wday(dates, week_start = 1) == 1]

fp <- expand_grid(date = test_dates, force_plate_id = roster$force_plate_id) %>%
  left_join(roster %>% select(force_plate_id, display_name, position), by = "force_plate_id") %>%
  group_by(force_plate_id) %>%
  arrange(date) %>%
  mutate(
    test_number = row_number(),
    
    # Baseline with individual variation
    baseline_height = 30 + (position == "G") * 5 + rnorm(1, 0, 3),
    
    # Off-season = improving (strength focus)
    # In-season = declining (fatigue accumulation)
    weeks_in = as.numeric(date - min(dates)) / 7,
    progress = if_else(SCENARIO == "OFF_SEASON", weeks_in * 0.3, -weeks_in * 0.5),
    
    # Jump metrics
    jump_height_cm = pmax(20, baseline_height + progress + rnorm(n(), 0, 2)),
    takeoff_velocity_m_s = sqrt(2 * 9.81 * (jump_height_cm / 100)),
    rsi_mod = pmax(0.15, 0.35 + progress * 0.01 + rnorm(n(), 0, 0.05)),
    
    test_type = "CMJ"
  ) %>%
  ungroup()

fp_export <- fp %>%
  transmute(
    athlete_id = force_plate_id,
    date,
    test_type,
    jump_height_cm = round(jump_height_cm, 1),
    takeoff_velocity_m_s = round(takeoff_velocity_m_s, 2),
    rsi_mod = round(rsi_mod, 3)
  )

fp_file <- path(dirs$raw_force, glue("{format(Sys.Date(), '%Y%m%d')}_forceplate.csv"))
write_csv(fp_export, fp_file)
log_msg(glue("Created: {fp_file} ({nrow(fp_export)} records)"))

# ==============================================================================
# WEARABLES DATA (Daily - Plantiga/Similar)
# ==============================================================================

log_msg("Generating wearable data...")

wearable <- expand_grid(date = dates, wearable_id = roster$wearable_id) %>%
  mutate(
    is_active_day = is_training_day(date),
    
    steps = if_else(is_active_day,
                    round(rnorm(n(), 8500, 2000)),
                    round(rnorm(n(), 5000, 1500))),
    
    active_minutes = if_else(is_active_day,
                             pmax(0, rnorm(n(), 90, 25)),
                             pmax(0, rnorm(n(), 45, 20))),
    
    load_proxy = pmax(0, rnorm(n(), 100, 30)),
    symmetry_proxy = pmax(0, pmin(1, rnorm(n(), 0.96, 0.03))),
    impact_proxy = pmax(0, rnorm(n(), 1.0, 0.15))
  )

wearable_export <- wearable %>%
  transmute(
    athlete_id = wearable_id,
    date,
    steps,
    active_minutes = round(active_minutes, 0),
    load_proxy = round(load_proxy, 1),
    symmetry_proxy = round(symmetry_proxy, 3),
    impact_proxy = round(impact_proxy, 2)
  )

wearable_file <- path(dirs$raw_wearables, glue("{format(Sys.Date(), '%Y%m%d')}_wearables.csv"))
write_csv(wearable_export, wearable_file)
log_msg(glue("Created: {wearable_file} ({nrow(wearable_export)} records)"))

# ==============================================================================
# SUMMARY
# ==============================================================================

log_msg("=== SAMPLE DATA GENERATION COMPLETE ===")
log_msg(glue("Scenario: {SCENARIO}"))
log_msg(glue("Date range: {start_date} to {end_date} ({length(dates)} days)"))
log_msg(glue("Roster: {nrow(roster)} players"))
log_msg(glue("GPS records: {nrow(gps_export)}"))
log_msg(glue("Wellness records: {nrow(wellness_export)}"))
log_msg(glue("Force plate records: {nrow(fp_export)}"))
log_msg(glue("Wearable records: {nrow(wearable_export)}"))
log_msg("")
log_msg("CONTEXT: February 2026 - Off-season training")
log_msg("- 2025 season completed (May-October 2025)")
log_msg("- Current: Off-season strength & conditioning")
log_msg("- Next: 2026 season starts May 2026")
log_msg("")
log_msg("Ready to run: source('scripts/run_daily.R')")

# ==============================================================================
# END OF SCRIPT
# ==============================================================================
