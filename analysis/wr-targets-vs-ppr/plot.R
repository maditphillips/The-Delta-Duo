# Top 60 WRs of the 2026 season (plus any extra names in ALWAYS_INCLUDE),
# plotted two ways:
#   1. total targets (x) vs. total PPR points (y)
#   2. targets per game (x) vs. PPR points per game (y), using games played
# Quadrants split at the median of the plotted players on each axis.
#
# install.packages(c("nflreadr", "nflplotR", "ggplot2", "dplyr", "ggrepel"))
# Run from this folder: Rscript plot.R   -> writes both PNGs here

library(nflreadr)
library(nflplotR)
library(ggplot2)
library(dplyr)
library(ggrepel)
source("../lib/quadrant_plot.R")

SEASON <- 2026
N_PLAYERS <- 60
# Players to plot even if they fall outside the top N (full display name)
ALWAYS_INCLUDE <- c("KC Concepcion")
# Games to leave out of a player's season (e.g. left early with an injury).
# Their targets, PPR points and the game itself are removed from the totals.
EXCLUDE_GAMES <- tibble::tribble(
  ~player_display_name, ~week, ~reason,
  "KC Concepcion",      5,     "injured"
)

stats <- load_player_stats(seasons = SEASON, summary_level = "reg")

if (nrow(EXCLUDE_GAMES)) {
  weekly <- load_player_stats(seasons = SEASON, summary_level = "week")
  removed <- weekly |>
    inner_join(EXCLUDE_GAMES, by = c("player_display_name", "week")) |>
    group_by(player_id) |>
    summarise(
      drop_games = n(),
      drop_targets = sum(targets),
      drop_ppr = sum(fantasy_points_ppr)
    )
  stats <- stats |>
    left_join(removed, by = "player_id") |>
    mutate(
      games = games - coalesce(drop_games, 0L),
      targets = targets - coalesce(drop_targets, 0L),
      fantasy_points_ppr = fantasy_points_ppr - coalesce(drop_ppr, 0)
    )
}

# The group is picked by total PPR points so both charts show the same players
wr <- stats |>
  filter(position == "WR") |>
  arrange(desc(fantasy_points_ppr)) |>
  filter(row_number() <= N_PLAYERS | player_display_name %in% ALWAYS_INCLUDE) |>
  mutate(
    label = short_name(player_display_name),
    targets_pg = targets / games,
    ppr_pg = fantasy_points_ppr / games
  )

# Only name the always-include players who didn't make the top N on their own
extras <- wr$player_display_name[-seq_len(N_PLAYERS)]
group_text <- paste0("Top ", N_PLAYERS, " WRs by total PPR points",
                     if (length(extras)) paste0(" + ", paste(extras, collapse = ", ")) else "")
# e.g. "Left out: KC Concepcion Week 5 (injured)."
exclude_note <- if (nrow(EXCLUDE_GAMES)) {
  paste0("Left out: ", paste0(EXCLUDE_GAMES$player_display_name, " Week ", EXCLUDE_GAMES$week,
                              " (", EXCLUDE_GAMES$reason, ")", collapse = "; "), ".")
}

totals <- quadrant_plot(
  wr, "targets", "fantasy_points_ppr",
  x_label = "Total targets", y_label = "Total PPR points",
  title = paste(SEASON, "Wide Receivers: Targets vs. PPR Points"),
  subtitle_lead = group_text,
  x_unit = "targets", y_unit = "PPR pts", x_digits = 0,
  caption = paste(c(exclude_note, "Data: nflverse via nflreadr | Plot: nflplotR"), collapse = " ")
)

per_game <- quadrant_plot(
  wr, "targets_pg", "ppr_pg",
  x_label = "Targets per game", y_label = "PPR points per game",
  title = paste(SEASON, "Wide Receivers: Targets vs. PPR Points, Per Game"),
  subtitle_lead = group_text,
  x_unit = "targets/game", y_unit = "PPR pts/game",
  caption = paste(c(exclude_note, "Per game = season total divided by games played.",
                    "Data: nflverse via nflreadr | Plot: nflplotR"), collapse = " ")
)

save_quadrant_plot(totals, "wr_targets_vs_ppr_2026.png")
save_quadrant_plot(per_game, "wr_targets_vs_ppr_per_game_2026.png")
