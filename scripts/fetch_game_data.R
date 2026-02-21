# ==============================================================================
# WAIMS-R: Athlete Availability Intelligence & Monitoring System
# Game Data Integration - wehoop Package
# ==============================================================================
#
# PURPOSE:
#   Fetches WNBA game data using wehoop R package (ESPN API access).
#   Provides play-by-play, box scores, and player statistics from games.
#   Complements practice data from GPS/Kinexon with official game tracking.
#
# DATA SOURCE:
#   wehoop package by sportsdataverse - https://github.com/sportsdataverse/wehoop
#   Accesses ESPN WNBA API for game statistics
#
# CURRENT CONTEXT:
#   Date: February 2026
#   Most recent completed season: 2025 (May-October 2025)
#   Next season: 2026 (starts May 2026)
#
# USAGE:
#   source("scripts/fetch_game_data.R")
#   game_data <- get_team_game_data(team_abbreviation = "DAL", season = 2025)
#
# DEPENDENCIES:
#   - wehoop: WNBA data access
#   - tidyverse: Data manipulation
#   - lubridate: Date handling
#
# AUTHOR: Chris Cothern
# DATE: 2026-02-19
# VERSION: 1.0.1 (Updated for 2025 season)
# ==============================================================================

library(wehoop)
library(tidyverse)
library(lubridate)

source("scripts/config.R")

# ==============================================================================
# WEHOOP GAME DATA FUNCTIONS
# ==============================================================================

#' Fetch Team's Recent Games from wehoop
#' 
#' Retrieves game statistics for a specific team from ESPN API via wehoop.
#' Returns player box scores with game load metrics.
#' 
#' @param team_abbreviation Character. Team abbreviation (e.g., "DAL", "PHX", "LA")
#' @param season Integer. Season year (default: 2025 - most recent completed)
#' @param last_n_games Integer. Number of recent games to fetch (default: 10)
#' 
#' @return Tibble with game statistics per player per game
#' 
#' @details
#' Available metrics from wehoop player box scores:
#'   - minutes: Minutes played
#'   - points, rebounds, assists, steals, blocks
#'   - field_goals_made, field_goals_attempted, field_goal_pct
#'   - three_point_field_goals_made, three_point_field_goals_attempted
#'   - free_throws_made, free_throws_attempted
#'   - plus_minus: +/- statistic
#' 
#' Note: wehoop does NOT provide GPS/distance data - that requires GPS hardware.
#' This function provides statistical outputs only.
#' 
#' Current Context (Feb 2026):
#'   - 2025 season: COMPLETE (May-October 2025)
#'   - 2026 season: Starts May 2026
#'   - Default season = 2025 (most recent)
#' 
#' @examples
#' # Get last 5 games from 2025 season for Dallas
#' dal_games <- get_team_game_data("DAL", season = 2025, last_n_games = 5)
#' 
#' # Get full 2025 season for Phoenix Mercury
#' phx_games <- get_team_game_data("PHX", season = 2025, last_n_games = 50)
#' 
#' # Compare 2025 vs 2024
#' dal_2025 <- get_team_game_data("DAL", season = 2025)
#' dal_2024 <- get_team_game_data("DAL", season = 2024)
get_team_game_data <- function(team_abbreviation, 
                                season = 2025,  # Default to 2025 (most recent)
                                last_n_games = 10) {
  
  log_msg(glue("Fetching game data for {team_abbreviation} - {season} season"))
  
  tryCatch({
    # Load WNBA player box scores for specified season
    player_box <- load_wnba_player_box(seasons = season)
    
    # Filter to specific team
    team_games <- player_box %>%
      filter(team_short_display_name == team_abbreviation | 
             team_abbreviation == !!team_abbreviation) %>%
      arrange(desc(game_date)) %>%
      group_by(athlete_display_name) %>%
      slice(1:last_n_games) %>%
      ungroup()
    
    # Standardize column names to match WAIMS schema
    game_data_clean <- team_games %>%
      transmute(
        athlete_name = athlete_display_name,
        athlete_id_espn = athlete_id,  # ESPN's athlete ID
        date = as.Date(game_date),
        opponent = opponent_team_short_display_name,
        home_away = team_home_away,
        
        # Game statistics
        minutes_played = minutes,
        points,
        rebounds = total_rebounds,
        assists,
        steals,
        blocks,
        turnovers,
        fouls,
        
        # Shooting
        fg_made = field_goals_made,
        fg_attempted = field_goals_attempted,
        fg_pct = field_goal_pct,
        three_pt_made = three_point_field_goals_made,
        three_pt_attempted = three_point_field_goals_attempted,
        ft_made = free_throws_made,
        ft_attempted = free_throws_attempted,
        
        # Advanced
        plus_minus,
        
        # Session type flag
        session_type = "GAME",
        
        # Game outcome
        team_score,
        opponent_score,
        team_winner
      )
    
    log_msg(glue("Retrieved {nrow(game_data_clean)} game records for {team_abbreviation}"))
    
    return(game_data_clean)
    
  }, error = function(e) {
    log_msg(glue("Error fetching game data: {e$message}"), "ERROR")
    log_msg("Check: (1) team abbreviation? (2) internet? (3) season available?", "ERROR")
    return(tibble())  # Return empty tibble on error
  })
}

#' Calculate Game Load Metrics
#' 
#' Estimates physical load from game statistics (minutes, rebounds, etc.).
#' 
#' @param game_data Tibble from get_team_game_data()
#' 
#' @return Tibble with added load estimate column
#' 
#' @details
#' Creates a simple game load index based on:
#'   - Minutes played (baseline)
#'   - Rebounds (contact/jumping load)
#'   - Defensive actions (steals + blocks = high-intensity efforts)
#'   - Turnovers (negative proxy for decision quality under fatigue)
#' 
#' Formula: load_index = minutes * (1 + rebounds/10 + (steals + blocks)/5)
#' 
#' Note: This is a PROXY only. True game load requires GPS/optical tracking.
#' 
#' @examples
#' game_data <- get_team_game_data("DAL", 2025)
#' game_data_with_load <- calculate_game_load(game_data)
calculate_game_load <- function(game_data) {
  
  game_data_with_load <- game_data %>%
    mutate(
      # Simple load index (proxy - not true GPS load)
      # Weights minutes by physical demands (rebounds, defensive actions)
      game_load_index = minutes_played * (1 + rebounds/10 + (steals + blocks)/5),
      
      # Flag high-minute games (>30 min = starter load)
      high_minutes = minutes_played >= 30,
      
      # Flag high-intensity games (lots of defensive actions)
      high_intensity = (steals + blocks) >= 5
    )
  
  log_msg(glue("Calculated game load for {nrow(game_data_with_load)} records"))
  
  return(game_data_with_load)
}

#' Map ESPN Athlete IDs to Internal Athlete IDs
#' 
#' Matches ESPN athlete IDs from wehoop to your internal athlete_id system.
#' 
#' @param game_data Tibble with athlete_id_espn column
#' @param roster_mapping Tibble with athlete_id and athlete_id_espn columns
#' 
#' @return Tibble with athlete_id added (internal ID system)
#' 
#' @details
#' You need to create a mapping file: ref/espn_id_mapping.csv
#' 
#' Format:
#' athlete_id,athlete_id_espn,display_name
#' ATH_001,1234567,Player A
#' ATH_002,7654321,Player B
#' ...
#' 
#' This allows wehoop game data to join with your GPS/wellness data.
#' 
#' @examples
#' # Create mapping (one-time setup)
#' mapping <- tibble(
#'   athlete_id = c("ATH_001", "ATH_002"),
#'   athlete_id_espn = c("1234567", "7654321"),
#'   display_name = c("Player A", "Player B")
#' )
#' write_csv(mapping, "ref/espn_id_mapping.csv")
#' 
#' # Map game data to internal IDs
#' game_data <- get_team_game_data("DAL", 2025)
#' mapping <- read_csv("ref/espn_id_mapping.csv")
#' game_data_mapped <- map_athlete_ids(game_data, mapping)
map_athlete_ids <- function(game_data, roster_mapping) {
  
  game_data_mapped <- game_data %>%
    left_join(
      roster_mapping %>% select(athlete_id, athlete_id_espn),
      by = "athlete_id_espn"
    )
  
  # Check for unmapped athletes
  unmapped <- game_data_mapped %>% filter(is.na(athlete_id))
  
  if (nrow(unmapped) > 0) {
    log_msg(glue("WARNING: {nrow(unmapped)} records with unmapped athlete IDs"), "WARNING")
    log_msg("Update ref/espn_id_mapping.csv with these athlete_id_espn values:", "WARNING")
    unmapped %>%
      distinct(athlete_name, athlete_id_espn) %>%
      pmap(~ log_msg(glue("  {..1}: {..2}"), "WARNING"))
  }
  
  return(game_data_mapped)
}

#' Export Game Data to RAW Folder
#' 
#' Saves wehoop game data as CSV in raw/game_tracking/ folder for ingestion.
#' 
#' @param game_data Tibble with game statistics
#' @param output_date Date for filename (default: today)
#' 
#' @return File path to saved CSV
#' 
#' @details
#' Saves to: raw/game_tracking/YYYYMMDD_wehoop_games.csv
#' This file can then be ingested by ingest_data.R script.
#' 
#' @examples
#' game_data <- get_team_game_data("DAL", 2025, last_n_games = 5)
#' game_data <- calculate_game_load(game_data)
#' export_game_data(game_data)
export_game_data <- function(game_data, output_date = Sys.Date()) {
  
  # Create game_tracking folder if doesn't exist
  game_tracking_dir <- path(dirs$raw_gps, "..", "game_tracking")
  dir_create(game_tracking_dir)
  
  # Create filename
  filename <- glue("{format(output_date, '%Y%m%d')}_wehoop_games.csv")
  filepath <- path(game_tracking_dir, filename)
  
  # Save CSV
  write_csv(game_data, filepath)
  
  log_msg(glue("Exported game data to: {filepath}"))
  log_msg(glue("  Records: {nrow(game_data)}"))
  log_msg(glue("  Date range: {min(game_data$date)} to {max(game_data$date)}"))
  
  return(filepath)
}

# ==============================================================================
# CONVENIENCE WRAPPER FUNCTION
# ==============================================================================

#' Fetch, Process, and Export Team Game Data (All-in-One)
#' 
#' Combines all steps: fetch from wehoop → calculate load → map IDs → export CSV
#' 
#' @param team_abbreviation Character. Team abbreviation
#' @param season Integer. Season year (default: 2025)
#' @param last_n_games Integer. Number of recent games
#' @param roster_mapping Tibble with ID mapping (optional)
#' 
#' @return Tibble with processed game data
#' 
#' @examples
#' # Simple usage (no ID mapping) - 2025 season
#' game_data <- fetch_and_process_games("DAL", season = 2025, last_n_games = 5)
#' 
#' # With ID mapping
#' mapping <- read_csv("ref/espn_id_mapping.csv")
#' game_data <- fetch_and_process_games("DAL", 2025, last_n_games = 10, 
#'                                       roster_mapping = mapping)
#' 
#' # Full 2025 season retrospective
#' game_data <- fetch_and_process_games("PHX", 2025, last_n_games = 50)
fetch_and_process_games <- function(team_abbreviation, 
                                     season = 2025,    # Default to 2025
                                     last_n_games = 10,
                                     roster_mapping = NULL) {
  
  log_msg("=== FETCHING AND PROCESSING GAME DATA ===")
  log_msg(glue("Season: {season} | Team: {team_abbreviation} | Games: {last_n_games}"))
  
  # Step 1: Fetch from wehoop
  game_data <- get_team_game_data(team_abbreviation, season, last_n_games)
  
  if (nrow(game_data) == 0) {
    log_msg("No game data retrieved - check team abbreviation and season", "ERROR")
    return(tibble())
  }
  
  # Step 2: Calculate game load
  game_data <- calculate_game_load(game_data)
  
  # Step 3: Map athlete IDs (if mapping provided)
  if (!is.null(roster_mapping)) {
    game_data <- map_athlete_ids(game_data, roster_mapping)
  } else {
    log_msg("No roster mapping provided - using ESPN athlete IDs only", "WARNING")
  }
  
  # Step 4: Export to RAW folder
  export_game_data(game_data)
  
  log_msg("=== GAME DATA PROCESSING COMPLETE ===")
  
  return(game_data)
}

# ==============================================================================
# USAGE EXAMPLES (Updated for 2025)
# ==============================================================================

# Example 1: Simple fetch for 2025 season
# game_data <- fetch_and_process_games("DAL", 2025, last_n_games = 5)

# Example 2: With athlete ID mapping
# mapping <- read_csv("ref/espn_id_mapping.csv", show_col_types = FALSE)
# game_data <- fetch_and_process_games("DAL", 2025, last_n_games = 10, 
#                                       roster_mapping = mapping)

# Example 3: Full 2025 season retrospective analysis
# game_data <- fetch_and_process_games("PHX", 2025, last_n_games = 50)

# Example 4: Compare 2025 vs 2024 seasons
# games_2025 <- fetch_and_process_games("DAL", 2025, last_n_games = 40)
# games_2024 <- fetch_and_process_games("DAL", 2024, last_n_games = 40)

# ==============================================================================
# LIMITATIONS & NOTES
# ==============================================================================

# IMPORTANT: wehoop provides game STATISTICS, not GPS/distance data
#
# Available from wehoop:
# ✅ Minutes played
# ✅ Points, rebounds, assists, steals, blocks
# ✅ Shooting percentages
# ✅ Plus/minus
# ✅ Game outcomes
#
# NOT available from wehoop (requires GPS hardware):
# ❌ Distance covered (meters)
# ❌ Sprint counts
# ❌ Accelerations/decelerations
# ❌ High-speed running distance
# ❌ Player load (mechanical load)
#
# For true game load data, teams need:
# - Second Spectrum optical tracking (WNBA league-wide)
# - Kinexon GPS (practice only, unless team has in-arena system)
# - Other optical tracking systems
#
# wehoop is excellent for:
# - Retrospective analysis (historical games)
# - Benchmarking (compare to league averages)
# - Integration with practice data
# - Game vs practice load comparison (using load proxies)

# ==============================================================================
# CURRENT CONTEXT (February 2026)
# ==============================================================================

# You are in OFF-SEASON (Feb 2026)
# - 2025 season completed (May-October 2025)
# - 2026 season starts May 2026
# - Use 2025 data for retrospective analysis
# - Current focus: Off-season training monitoring
# - Next focus: 2026 season preparation

# ==============================================================================
# END OF SCRIPT
# ==============================================================================
