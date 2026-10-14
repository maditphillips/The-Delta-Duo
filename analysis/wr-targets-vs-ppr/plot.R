# Top 60 WRs of the 2026 season (plus any extra names in ALWAYS_INCLUDE),
# plotted two ways:
#   1. total targets (x) vs. total PPR points (y)
#   2. targets per game (x) vs. PPR points per game (y), using games played
#   3. targets per game (x) vs. receptions per game (y), with the group's
#      overall catch rate drawn as a diagonal
# Quadrants split at the median of the plotted players on each axis.
#
# install.packages(c("nflreadr", "nflplotR", "ggplot2", "dplyr", "ggrepel"))
# Run from this folder: Rscript plot.R   -> writes the three PNGs here

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
  stats <- drop_excluded_games(stats, EXCLUDE_GAMES, weekly)
}

# The group is picked by total PPR points so both charts show the same players
wr <- stats |>
  filter(position == "WR") |>
  arrange(desc(fantasy_points_ppr)) |>
  filter(row_number() <= N_PLAYERS | player_display_name %in% ALWAYS_INCLUDE) |>
  mutate(
    label = short_name(player_display_name),
    targets_pg = targets / games,
    ppr_pg = fantasy_points_ppr / games,
    receptions_pg = receptions / games
  )

exclude_note <- excluded_note(EXCLUDE_GAMES)

totals <- quadrant_plot(
  wr, "targets", "fantasy_points_ppr",
  x_label = "Total targets", y_label = "Total PPR points",
  title = paste(SEASON, "Wide Receivers: Targets vs. PPR Points"),
  x_unit = "targets", y_unit = "PPR pts", x_digits = 0,
  caption = paste(c(exclude_note, "Data: nflverse via nflreadr | Plot: nflplotR"), collapse = " ")
)

per_game <- quadrant_plot(
  wr, "targets_pg", "ppr_pg",
  x_label = "Targets per game", y_label = "PPR points per game",
  title = paste(SEASON, "Wide Receivers: Targets vs. PPR Points, Per Game"),
  x_unit = "targets/game", y_unit = "PPR pts/game",
  caption = paste(c(exclude_note, "Per game = season total divided by games played.",
                    "Data: nflverse via nflreadr | Plot: nflplotR"), collapse = " ")
)

# Group catch rate: all receptions / all targets across the plotted players
catch_rate <- sum(wr$receptions) / sum(wr$targets)

catches <- quadrant_plot(
  wr, "targets_pg", "receptions_pg",
  x_label = "Targets per game", y_label = "Receptions per game",
  title = paste(SEASON, "Wide Receivers: Targets vs. Receptions, Per Game"),
  x_unit = "targets/game", y_unit = "receptions/game",
  quadrant_text = c(
    top_left     = "SURE HANDS\nCatches without heavy volume",
    top_right    = "VOLUME CATCHERS\nTargets and catches",
    bottom_left  = "LIMITED ROLES\nFew targets, few catches",
    bottom_right = "LEAKY VOLUME\nTargets not turning into catches"
  ),
  ref_slope = catch_rate, label_force = 6,
  ref_label = paste0("Group catch rate: ", round(100 * catch_rate), "%"),
  caption = paste0(
    "Above the orange line = catches more of their targets than the group; below = fewer.\n",
    paste(c(exclude_note, "Per game = season total divided by games played.",
            "Data: nflverse via nflreadr | Plot: nflplotR"), collapse = " ")
  )
)

save_quadrant_plot(totals, "wr_targets_vs_ppr_2026.png")
save_quadrant_plot(per_game, "wr_targets_vs_ppr_per_game_2026.png")
save_quadrant_plot(catches, "wr_targets_vs_receptions_per_game_2026.png")
