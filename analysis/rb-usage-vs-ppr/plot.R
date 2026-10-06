# Top 50 RBs of the 2026 season by total PPR points (plus any extra names in
# ALWAYS_INCLUDE), plotted three ways, all per game played:
#   1. targets (x) vs. PPR points (y)
#   2. carries (x) vs. PPR points (y)
#   3. carries (x) vs. targets (y)
# Quadrants split at the median of the plotted players on each axis.
#
# install.packages(c("nflreadr", "nflplotR", "ggplot2", "dplyr", "ggrepel"))
# The top TOP_N RBs in total PPR get a big rank number beside their logo.
#
# Run from this folder: Rscript plot.R   -> writes the three PNGs here

library(nflreadr)
library(nflplotR)
library(ggplot2)
library(dplyr)
library(ggrepel)
source("../lib/quadrant_plot.R")

SEASON <- 2026
N_PLAYERS <- 50
# Players to plot even if they fall outside the top N (full display name)
ALWAYS_INCLUDE <- character(0)
# How many of the top RBs (by total PPR) get a rank number (0 = none)
TOP_N <- 10

stats <- load_player_stats(seasons = SEASON, summary_level = "reg")

# The group is picked by total PPR points so all three charts show the same players
rb <- stats |>
  filter(position == "RB") |>
  arrange(desc(fantasy_points_ppr)) |>
  mutate(ppr_rank = row_number()) |>
  filter(ppr_rank <= N_PLAYERS | player_display_name %in% ALWAYS_INCLUDE) |>
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
data_credit <- "Per game = season total divided by games played. Data: nflverse via nflreadr | Plot: nflplotR"

charts <- list(
  list(
    file = "rb_targets_vs_ppr_per_game_2026", x = "targets_pg", y = "ppr_pg",
    x_label = "Targets per game", y_label = "PPR points per game",
    title = "Running Backs: Targets vs. PPR Points, Per Game",
    x_unit = "targets/game", y_unit = "PPR pts/game",
    quadrant_text = POINTS_QUADRANTS
  ),
  list(
    file = "rb_carries_vs_ppr_per_game_2026", x = "carries_pg", y = "ppr_pg",
    x_label = "Carries per game", y_label = "PPR points per game",
    title = "Running Backs: Carries vs. PPR Points, Per Game",
    x_unit = "carries/game", y_unit = "PPR pts/game",
    quadrant_text = POINTS_QUADRANTS
  ),
  list(
    file = "rb_carries_vs_targets_per_game_2026", x = "carries_pg", y = "targets_pg",
    x_label = "Carries per game", y_label = "Targets per game",
    title = "Running Backs: Carries vs. Targets, Per Game",
    x_unit = "carries/game", y_unit = "targets/game",
    quadrant_text = c(
      top_left     = "PASS-GAME BACKS\nTargets without the carries",
      top_right    = "WORKHORSES\nCarries and targets",
      bottom_left  = "LIMITED ROLES\nFew carries, few targets",
      bottom_right = "EARLY-DOWN GRINDERS\nCarries without the targets"
    )
  )
)

rank_note <- if (TOP_N > 0) paste0("Big numbers = RB rank in total PPR (top ", TOP_N, ").")

for (ch in charts) {
  p <- quadrant_plot(
    rb, ch$x, ch$y,
    x_label = ch$x_label, y_label = ch$y_label,
    title = paste(SEASON, ch$title),
    subtitle_lead = group_text,
    x_unit = ch$x_unit, y_unit = ch$y_unit,
    quadrant_text = ch$quadrant_text,
    caption = paste(c(rank_note, data_credit), collapse = " "),
    rank_col = "ppr_rank", top_n = TOP_N, mark_top = "number"
  )
  save_quadrant_plot(p, paste0(ch$file, ".png"))
}
