# Top 60 WRs of the 2026 season (plus any extra names in ALWAYS_INCLUDE),
# plotted two ways:
#   1. total targets (x) vs. total PPR points (y)
#   2. targets per game (x) vs. PPR points per game (y), using games played
#   3. targets per game (x) vs. receptions per game (y), with the group's
#      overall catch rate drawn as a diagonal
#   4. chart 2 with the top N_TE tight ends added (starred), quadrants still
#      split at the WR medians
# Quadrants split at the median of the plotted players on each axis.
#
# install.packages(c("nflreadr", "nflplotR", "ggplot2", "dplyr", "ggrepel"))
# Run from this folder: Rscript plot.R   -> writes the four PNGs here

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
# Top tight ends (by total PPR) to add to the WR + TE version of chart 2
N_TE <- 12
# Tight-end group whose medians are drawn as red dashed lines on that chart
N_TE_MEDIAN <- 40
TE_COLOUR <- "#C62828"  # red for tight-end names on that chart
# Games to leave out of a player's season (e.g. left early with an injury).
# Their targets, PPR points and the game itself are removed from the totals.
EXCLUDE_GAMES <- tibble::tribble(
  ~player_display_name, ~week, ~reason,
  "KC Concepcion",      5,     "injured",
  "Terry McLaurin",     6,     "injured"
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
  split = "ref_line",
  ref_text = c(above = "ABOVE THE GROUP CATCH RATE", below = "BELOW THE GROUP CATCH RATE"),
  subtitle = paste0("Green = catches more of their targets than the group (", round(100 * catch_rate),
                    "% of targets caught); red = fewer."),
  ref_slope = catch_rate, label_force = 6,
  ref_label = paste0("Group catch rate: ", round(100 * catch_rate), "%"),
  caption = paste(c(exclude_note, "Per game = season total divided by games played.",
                    "Data: nflverse via nflreadr | Plot: nflplotR"), collapse = " ")
)

# WR + TE: the WR group plus the top N_TE tight ends. Quadrant lines stay at
# the WR medians so each TE reads as "where would he rank as a receiver".
te <- stats |>
  filter(position == "TE") |>
  arrange(desc(fantasy_points_ppr)) |>
  slice_head(n = N_TE) |>
  mutate(
    label = paste("\u2605", short_name(player_display_name)),
    label_colour = TE_COLOUR,
    targets_pg = targets / games,
    ppr_pg = fantasy_points_ppr / games,
    receptions_pg = receptions / games
  )
wr_te <- bind_rows(wr, te)
te_group <- stats |>
  filter(position == "TE") |>
  arrange(desc(fantasy_points_ppr)) |>
  slice_head(n = N_TE_MEDIAN)
te_x_mid <- median(te_group$targets / te_group$games)
te_y_mid <- median(te_group$fantasy_points_ppr / te_group$games)
wr_x_mid <- median(wr$targets_pg)
wr_y_mid <- median(wr$ppr_pg)

with_tes <- quadrant_plot(
  wr_te, "targets_pg", "ppr_pg",
  x_label = "Targets per game", y_label = "PPR points per game",
  title = paste(SEASON, "Wide Receivers + Top", N_TE, "Tight Ends: Targets vs. PPR Points, Per Game"),
  x_unit = "targets/game", y_unit = "PPR pts/game",
  x_split = wr_x_mid, y_split = wr_y_mid, label_force = 5,
  extra_x = te_x_mid, extra_y = te_y_mid, extra_colour = TE_COLOUR,
  subtitle = paste0(
    "Red \u2605 = tight end (top ", N_TE, " by total PPR). Grey dashed = WR median (",
    format(round(wr_x_mid, 1), nsmall = 1), " targets/game, ", format(round(wr_y_mid, 1), nsmall = 1),
    " PPR pts/game).\nRed dashed = top-", N_TE_MEDIAN, " TE median (",
    format(round(te_x_mid, 1), nsmall = 1), " targets/game, ", format(round(te_y_mid, 1), nsmall = 1),
    " PPR pts/game)."
  ),
  caption = paste(c(exclude_note, "Per game = season total divided by games played.",
                    "Data: nflverse via nflreadr | Plot: nflplotR"), collapse = " ")
)

save_quadrant_plot(totals, "wr_targets_vs_ppr_2026.png")
save_quadrant_plot(per_game, "wr_targets_vs_ppr_per_game_2026.png")
save_quadrant_plot(catches, "wr_targets_vs_receptions_per_game_2026.png")
save_quadrant_plot(with_tes, "wr_te_targets_vs_ppr_per_game_2026.png")
