# Top 40 RBs of the 2026 season by total PPR points (plus any extra names in
# ALWAYS_INCLUDE), plotted three ways, all per game played:
#   1. targets (x) vs. PPR points (y)
#   2. carries (x) vs. PPR points (y)
#   3. carries (x) vs. targets (y)
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
N_PLAYERS <- 40
# Players to plot even if they fall outside the top N (full display name)
ALWAYS_INCLUDE <- character(0)

stats <- load_player_stats(seasons = SEASON, summary_level = "reg")

# The group is picked by total PPR points so all three charts show the same players
rb <- stats |>
  filter(position == "RB") |>
  arrange(desc(fantasy_points_ppr)) |>
  filter(row_number() <= N_PLAYERS | player_display_name %in% ALWAYS_INCLUDE) |>
  mutate(
    label = short_name(player_display_name),
    carries_pg = carries / games,
    targets_pg = targets / games,
    ppr_pg = fantasy_points_ppr / games
  )

# Only name the always-include players who didn't make the top N on their own
extras <- rb$player_display_name[-seq_len(N_PLAYERS)]
group_text <- paste0("Top ", N_PLAYERS, " RBs by total PPR points",
                     if (length(extras)) paste0(" + ", paste(extras, collapse = ", ")) else "")
per_game_caption <- "Per game = season total divided by games played. Data: nflverse via nflreadr | Plot: nflplotR"

targets_ppr <- quadrant_plot(
  rb, "targets_pg", "ppr_pg",
  x_label = "Targets per game", y_label = "PPR points per game",
  title = paste(SEASON, "Running Backs: Targets vs. PPR Points, Per Game"),
  subtitle_lead = group_text,
  x_unit = "targets/game", y_unit = "PPR pts/game",
  caption = per_game_caption
)

carries_ppr <- quadrant_plot(
  rb, "carries_pg", "ppr_pg",
  x_label = "Carries per game", y_label = "PPR points per game",
  title = paste(SEASON, "Running Backs: Carries vs. PPR Points, Per Game"),
  subtitle_lead = group_text,
  x_unit = "carries/game", y_unit = "PPR pts/game",
  caption = per_game_caption
)

carries_targets <- quadrant_plot(
  rb, "carries_pg", "targets_pg",
  x_label = "Carries per game", y_label = "Targets per game",
  title = paste(SEASON, "Running Backs: Carries vs. Targets, Per Game"),
  subtitle_lead = group_text,
  x_unit = "carries/game", y_unit = "targets/game",
  quadrant_text = c(
    top_left     = "PASS-GAME BACKS\nTargets without the carries",
    top_right    = "WORKHORSES\nCarries and targets",
    bottom_left  = "LIMITED ROLES\nFew carries, few targets",
    bottom_right = "EARLY-DOWN GRINDERS\nCarries without the targets"
  ),
  caption = per_game_caption
)

save_quadrant_plot(targets_ppr, "rb_targets_vs_ppr_per_game_2026.png")
save_quadrant_plot(carries_ppr, "rb_carries_vs_ppr_per_game_2026.png")
save_quadrant_plot(carries_targets, "rb_carries_vs_targets_per_game_2026.png")
