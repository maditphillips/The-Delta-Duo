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

stats <- load_player_stats(seasons = SEASON, summary_level = "reg")

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

totals <- quadrant_plot(
  wr, "targets", "fantasy_points_ppr",
  x_label = "Total targets", y_label = "Total PPR points",
  title = paste(SEASON, "Wide Receivers: Targets vs. PPR Points"),
  subtitle_lead = group_text,
  x_unit = "targets", y_unit = "PPR pts", x_digits = 0
)

per_game <- quadrant_plot(
  wr, "targets_pg", "ppr_pg",
  x_label = "Targets per game", y_label = "PPR points per game",
  title = paste(SEASON, "Wide Receivers: Targets vs. PPR Points, Per Game"),
  subtitle_lead = group_text,
  x_unit = "targets/game", y_unit = "PPR pts/game",
  caption = "Per game = season total divided by games played. Data: nflverse via nflreadr | Plot: nflplotR"
)

save_quadrant_plot(totals, "wr_targets_vs_ppr_2026.png")
save_quadrant_plot(per_game, "wr_targets_vs_ppr_per_game_2026.png")
