# Best and worst wide receiver matchups for an upcoming week, built with
# nflverse + nflplotR.
#
# Offense side: each WR's PPR points per game so far (his baseline).
# Defense side: PPR points each defense has allowed to WRs, compared with what
#   those same WRs score in their other games. A defense that held receivers
#   below their own norms is tough; one that let them beat their norms is soft.
#   That gap, per game, divided by the league's WR points per team-game, is the
#   defense factor. It is shrunk halfway to 1 because three games is little data.
# Projection = baseline x the opponent's defense factor.
# Matchup edge = projection - baseline, in PPR points.
#
# Pool: WRs with 2+ games and 5+ targets per game, not listed Out or Doubtful
# on the week's injury report, in games not yet played.
#
# Usage:  Rscript wr_matchups.R [season] [week]
# Writes: wr_matchups.png and wr_matchups.csv next to this file.

suppressPackageStartupMessages({
  library(nflreadr)
  library(nflplotR)
  library(dplyr)
  library(ggplot2)
  library(patchwork)
})

args <- commandArgs(trailingOnly = TRUE)
season <- if (length(args) >= 1) as.integer(args[1]) else 2026L
week_n <- if (length(args) >= 2) as.integer(args[2]) else 4L

out_dir <- local({
  f <- sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE))
  if (length(f)) dirname(normalizePath(f)) else getwd()
})

font <- if ("Roboto" %in% systemfonts::system_fonts()$family) "Roboto" else "sans"

shrink <- 0.5        # weight on the observed defense factor
min_tgt_pg <- 5      # pool: targets per game
show_n <- 12         # rows shown in each of best / worst

# ---- data --------------------------------------------------------------

# load_schedules() reads github.com/.../raw/...; fall back to the same file on
# raw.githubusercontent.com where only that host is reachable.
schedule <- tryCatch(
  load_schedules(season),
  error = function(e) NULL, warning = function(w) NULL
)
if (is.null(schedule) || !"week" %in% names(schedule)) {
  schedule <- read.csv(
    "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"
  ) |> filter(season == !!season)
}

games <- schedule |>
  filter(game_type == "REG", week == week_n, is.na(result)) |>
  mutate(
    home_implied = (total_line + spread_line) / 2,
    away_implied = (total_line - spread_line) / 2
  )

# One row per team playing this week (games already played are left out).
slate <- bind_rows(
  games |> transmute(team = home_team, opp = away_team, implied = home_implied, home = TRUE),
  games |> transmute(team = away_team, opp = home_team, implied = away_implied, home = FALSE)
)

stats <- load_player_stats(season) |>
  filter(season_type == "REG", week < week_n)

wr_games <- stats |>
  filter(position == "WR") |>
  group_by(player_id) |>
  mutate(
    g = n(),
    # This WR's average in his other games: what the defense "should" allow.
    expected = if_else(g > 1, (sum(fantasy_points_ppr) - fantasy_points_ppr) / (g - 1), NA_real_)
  ) |>
  ungroup()

league_wr_pg <- wr_games |>
  group_by(team, week) |>
  summarise(pts = sum(fantasy_points_ppr), .groups = "drop") |>
  pull(pts) |>
  mean()

defense <- wr_games |>
  filter(!is.na(expected)) |>
  group_by(def = opponent_team, week) |>
  summarise(actual = sum(fantasy_points_ppr), expected = sum(expected), .groups = "drop") |>
  group_by(def) |>
  summarise(
    allowed_pg = mean(actual),
    over_exp_pg = mean(actual - expected),
    .groups = "drop"
  ) |>
  mutate(factor = 1 + shrink * over_exp_pg / league_wr_pg)

injuries <- tryCatch(
  load_injuries(season) |>
    filter(week == week_n, report_status %in% c("Out", "Doubtful")) |>
    pull(gsis_id),
  error = function(e) character()
)

receivers <- wr_games |>
  group_by(player_id) |>
  summarise(
    name = last(player_display_name),
    team = last(team),
    games = n(),
    tgt_pg = sum(targets) / n(),
    ppr_pg = sum(fantasy_points_ppr) / n(),
    .groups = "drop"
  ) |>
  filter(games >= 2, tgt_pg >= min_tgt_pg, !player_id %in% injuries) |>
  inner_join(slate, by = "team") |>
  left_join(defense |> select(opp = def, factor, over_exp_pg), by = "opp") |>
  mutate(proj = ppr_pg * factor, edge = proj - ppr_pg) |>
  arrange(desc(edge))

write.csv(
  receivers |> select(name, team, opp, games, tgt_pg, ppr_pg, factor, proj, edge, implied),
  file.path(out_dir, "wr_matchups.csv"), row.names = FALSE
)

# ---- graphic -----------------------------------------------------------

ink <- "#111111"
muted <- "#6b6b6b"
grid <- "#d9dee4"
good <- "#1a9850"
bad <- "#d73027"

base_theme <- theme_void(base_family = font) +
  theme(
    plot.title = element_text(face = "bold", size = 20, hjust = 0.5, colour = ink),
    plot.subtitle = element_text(size = 12, hjust = 0.5, colour = muted,
                                 margin = margin(t = 3, b = 8)),
    axis.text.x = element_text(size = 10, colour = muted, margin = margin(t = 4)),
    plot.margin = margin(6, 16, 6, 16)
  )

# Left: every defense, ranked by WR points allowed over expected.
def_plot <- defense |>
  arrange(desc(over_exp_pg)) |>
  mutate(row = row_number())

lim_d <- max(abs(def_plot$over_exp_pg)) * 1.25

p_def <- ggplot(def_plot, aes(y = row)) +
  geom_vline(xintercept = 0, colour = muted, linewidth = 0.4) +
  geom_col(aes(x = over_exp_pg, fill = over_exp_pg > 0), orientation = "y", width = 0.7) +
  geom_nfl_logos(aes(x = -lim_d - 3.6, team_abbr = def), height = 0.026) +
  geom_text(aes(x = -lim_d - 2.4, label = def),
            family = font, fontface = "bold", size = 3.8, colour = ink, hjust = 0) +
  geom_text(
    aes(x = over_exp_pg + if_else(over_exp_pg > 0, 0.4, -0.4),
        label = sprintf("%+.1f", over_exp_pg),
        hjust = if_else(over_exp_pg > 0, 0, 1)),
    family = font, fontface = "bold", size = 3.8, colour = ink
  ) +
  annotate("text", x = lim_d * 0.95, y = 33, label = "Soft >",
           family = font, fontface = "bold", size = 4, colour = good, hjust = 1) +
  annotate("text", x = -lim_d * 0.95, y = 33, label = "< Tough",
           family = font, fontface = "bold", size = 4, colour = bad, hjust = 0) +
  scale_fill_manual(values = c(`TRUE` = good, `FALSE` = bad), guide = "none") +
  scale_x_continuous(breaks = seq(-15, 15, 5), expand = expansion(0)) +
  scale_y_reverse(expand = expansion(add = c(0.7, 1.4))) +
  coord_cartesian(xlim = c(-lim_d - 4.8, lim_d), clip = "off") +
  labs(
    title = "WR defense",
    subtitle = "PPR points allowed to WRs per game,\nabove or below what those WRs score elsewhere"
  ) +
  base_theme

# Right: the best and worst receiver matchups.
picks <- bind_rows(
  receivers |> slice_max(edge, n = show_n, with_ties = FALSE),
  receivers |> slice_min(edge, n = show_n, with_ties = FALSE) |> arrange(desc(edge))
) |>
  mutate(row = row_number() + if_else(row_number() > show_n, 1L, 0L))

lim_e <- max(abs(picks$edge)) * 1.15
x_name <- -lim_e - 10.5
x_team <- -lim_e - 11.6
x_vs <- -lim_e - 3.6
x_opp <- -lim_e - 2.4

p_wr <- ggplot(picks, aes(y = row)) +
  geom_rect(
    data = filter(picks, row %% 2 == 1),
    aes(xmin = x_team - 0.8, xmax = lim_e + 9, ymin = row - 0.5, ymax = row + 0.5),
    fill = "#eef2f6", inherit.aes = FALSE
  ) +
  geom_vline(xintercept = 0, colour = muted, linewidth = 0.4) +
  geom_col(aes(x = edge, fill = edge > 0), orientation = "y", width = 0.7) +
  geom_nfl_logos(aes(x = x_team, team_abbr = team), height = 0.03) +
  geom_text(aes(x = x_name, label = name),
            family = font, fontface = "bold", size = 5, colour = ink, hjust = 0) +
  geom_text(aes(x = x_vs, label = if_else(home, "vs", "@")),
            family = font, size = 4.2, colour = muted) +
  geom_nfl_logos(aes(x = x_opp, team_abbr = opp), height = 0.03) +
  geom_text(
    aes(x = edge + if_else(edge > 0, 0.15, -0.15),
        label = sprintf("%+.1f", edge),
        hjust = if_else(edge > 0, 0, 1)),
    family = font, fontface = "bold", size = 4.4, colour = ink
  ) +
  geom_text(aes(x = lim_e + 3, label = sprintf("%.1f", ppr_pg)),
            family = font, size = 4.4, colour = muted) +
  geom_text(aes(x = lim_e + 6.5, label = sprintf("%.1f", proj)),
            family = font, fontface = "bold", size = 4.4, colour = ink) +
  annotate("text", x = c(lim_e + 3, lim_e + 6.5), y = 0, label = c("Avg", "Proj."),
           family = font, fontface = "bold", size = 3.8, colour = ink) +
  annotate("text", x = x_team - 0.6, y = 0, label = "BEST MATCHUPS",
           family = font, fontface = "bold", size = 4.6, colour = good, hjust = 0) +
  annotate("text", x = x_team - 0.6, y = show_n + 1, label = "TOUGHEST MATCHUPS",
           family = font, fontface = "bold", size = 4.6, colour = bad, hjust = 0) +
  scale_fill_manual(values = c(`TRUE` = good, `FALSE` = bad), guide = "none") +
  scale_x_continuous(breaks = seq(-4, 4, 2), labels = function(x) sprintf("%+g", x),
                     expand = expansion(0)) +
  scale_y_reverse(expand = expansion(add = c(0.6, 1.2))) +
  coord_cartesian(xlim = c(x_team - 0.8, lim_e + 9), clip = "off") +
  labs(
    title = "Receiver matchups",
    subtitle = "Projected PPR points gained or lost vs. the WR's average"
  ) +
  base_theme

p <- (p_def | p_wr) + plot_layout(widths = c(1, 1.9)) +
  plot_annotation(
    title = sprintf("WEEK %d WR MATCHUPS", week_n),
    subtitle = sprintf(
      "Based on weeks 1-%d, %d  |  WRs with 5+ targets per game, not Out or Doubtful",
      week_n - 1, season
    ),
    caption = paste0(
      "Projection = WR's PPR per game x opponent factor (defense's over/under, as a share of ",
      sprintf("%.1f", league_wr_pg),
      " WR points per team-game, shrunk halfway to zero).  ",
      "Data: nflverse  |  Chart: The Delta Duo"
    ),
    theme = theme(
      plot.background = element_rect(fill = "white", colour = NA),
      plot.title = element_text(family = font, face = "bold", size = 34,
                                hjust = 0.5, colour = ink, margin = margin(t = 10)),
      plot.subtitle = element_text(family = font, size = 16, hjust = 0.5,
                                   colour = muted, margin = margin(t = 6, b = 14)),
      plot.caption = element_text(family = font, size = 11, colour = muted,
                                  hjust = 0.5, margin = margin(t = 14, b = 6))
    )
  )

ragg::agg_png(file.path(out_dir, "wr_matchups.png"),
              width = 2700, height = 1700, res = 130)
print(p)
invisible(dev.off())

message("Wrote ", file.path(out_dir, "wr_matchups.png"))
