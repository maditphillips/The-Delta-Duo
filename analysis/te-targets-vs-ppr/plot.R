# Top 40 TEs of the 2026 season by total PPR points (plus any extra names in
# ALWAYS_INCLUDE): targets per game (x) vs. PPR points per game (y).
# Quadrants split at the median of the plotted players on each axis.
#
# install.packages(c("nflreadr", "nflplotR", "ggplot2", "dplyr", "ggrepel"))
# Run from this folder: Rscript plot.R   -> writes the PNG here

library(nflreadr)
library(nflplotR)
library(ggplot2)
library(dplyr)
library(ggrepel)
source("../lib/quadrant_plot.R")

SEASON <- 2026
N_PLAYERS <- 40
# Players to plot even if they fall outside the top N (full display name)
ALWAYS_INCLUDE <- character(0)
# Games to leave out of a player's season (e.g. left early with an injury).
# Their targets, PPR points and the game itself are removed from the totals.
EXCLUDE_GAMES <- tibble::tibble(player_display_name = character(), week = integer(), reason = character())

stats <- load_player_stats(seasons = SEASON, summary_level = "reg")

if (nrow(EXCLUDE_GAMES)) {
  weekly <- load_player_stats(seasons = SEASON, summary_level = "week")
  stats <- drop_excluded_games(stats, EXCLUDE_GAMES, weekly)
}

te <- stats |>
  filter(position == "TE") |>
  arrange(desc(fantasy_points_ppr)) |>
  filter(row_number() <= N_PLAYERS | player_display_name %in% ALWAYS_INCLUDE) |>
  mutate(
    label = short_name(player_display_name),
    targets_pg = targets / games,
    ppr_pg = fantasy_points_ppr / games
  )

# Only name the always-include players who didn't make the top N on their own
extras <- te$player_display_name[-seq_len(N_PLAYERS)]
group_text <- paste0("Top ", N_PLAYERS, " TEs by total PPR points",
                     if (length(extras)) paste0(" + ", paste(extras, collapse = ", ")) else "")

per_game <- quadrant_plot(
  te, "targets_pg", "ppr_pg",
  x_label = "Targets per game", y_label = "PPR points per game",
  title = paste(SEASON, "Tight Ends: Targets vs. PPR Points, Per Game"),
  subtitle_lead = group_text,
  x_unit = "targets/game", y_unit = "PPR pts/game",
  caption = paste(c(excluded_note(EXCLUDE_GAMES), "Per game = season total divided by games played.",
                    "Data: nflverse via nflreadr | Plot: nflplotR"), collapse = " ")
)

save_quadrant_plot(per_game, "te_targets_vs_ppr_per_game_2026.png")
