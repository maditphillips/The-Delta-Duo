# Top 60 WRs of the 2026 season (plus any extra names in ALWAYS_INCLUDE),
# plotted two ways:
#   1. total targets (x) vs. total PPR points (y)
#   2. targets per game (x) vs. PPR points per game (y), using games played
# Quadrants split at the median of the plotted players on each axis.
#
# install.packages(c("nflreadr", "nflplotR", "ggplot2", "dplyr", "ggrepel"))
# Run: Rscript plot.R   -> writes both PNGs next to this file

library(nflreadr)
library(nflplotR)
library(ggplot2)
library(dplyr)
library(ggrepel)

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
    # "Amon-Ra St. Brown" -> "A. St. Brown"
    label = paste0(substr(player_display_name, 1, 1), ". ",
                   sub("^\\S+\\s+", "", player_display_name)),
    targets_pg = targets / games,
    ppr_pg = fantasy_points_ppr / games
  )

# Only name the always-include players who didn't make the top N on their own
extras <- wr$player_display_name[-seq_len(N_PLAYERS)]
group_text <- paste0("Top ", N_PLAYERS, " WRs by total PPR points",
                     if (length(extras)) paste0(" + ", paste(extras, collapse = ", ")) else "")

quadrant_plot <- function(data, x, y, x_label, y_label, title, x_unit, y_unit, digits) {
  xv <- data[[x]]
  yv <- data[[y]]
  x_mid <- median(xv)
  y_mid <- median(yv)

  # Pad the axes so logos and labels at the edges aren't clipped
  x_pad <- diff(range(xv)) * 0.08
  y_pad <- diff(range(yv)) * 0.08
  x_lim <- c(min(xv) - x_pad, max(xv) + x_pad)
  # Extra room at top and bottom for the quadrant titles
  y_lim <- c(min(yv) - 1.8 * y_pad, max(yv) + 1.8 * y_pad)

  quadrants <- tibble::tribble(
    ~xmin,    ~xmax,    ~ymin,    ~ymax,    ~fill,
    x_lim[1], x_mid,    y_mid,    y_lim[2], "#FCE9DC",  # sell candidates
    x_mid,    x_lim[2], y_mid,    y_lim[2], "#DFF1E4",  # juggernauts
    x_lim[1], x_mid,    y_lim[1], y_mid,    "#EEEEEE",  # lost causes
    x_mid,    x_lim[2], y_lim[1], y_mid,    "#DDEAF7"   # trade targets
  )

  quadrant_labels <- tibble::tribble(
    ~x,       ~y,       ~hjust, ~vjust, ~text,
    x_lim[1], y_lim[2], 0,      1,      "SELL CANDIDATES\nPoints without the usage",
    x_lim[2], y_lim[2], 1,      1,      "JUGGERNAUTS\nVolume and production",
    x_lim[1], y_lim[1], 0,      0,      "LOST CAUSES\nLittle volume, little production",
    x_lim[2], y_lim[1], 1,      0,      "TRADE TARGETS\nOpportunity not yet cashed in"
  )

  ggplot(data, aes(x = .data[[x]], y = .data[[y]])) +
    geom_rect(
      data = quadrants, inherit.aes = FALSE,
      aes(xmin = xmin, xmax = xmax, ymin = ymin, ymax = ymax, fill = fill)
    ) +
    scale_fill_identity() +
    geom_vline(xintercept = x_mid, linetype = "dashed", colour = "grey55", linewidth = 0.4) +
    geom_hline(yintercept = y_mid, linetype = "dashed", colour = "grey55", linewidth = 0.4) +
    geom_text(
      data = quadrant_labels, inherit.aes = FALSE,
      aes(x = x, y = y, label = text, hjust = hjust, vjust = vjust),
      size = 3.2, fontface = "bold", colour = "grey30", lineheight = 0.95,
      nudge_x = c(1, -1, 1, -1) * x_pad * 0.15,
      nudge_y = c(-1, -1, 1, 1) * y_pad * 0.15
    ) +
    geom_nfl_logos(aes(team_abbr = recent_team), width = 0.026, alpha = 0.95) +
    geom_text_repel(
      aes(label = label),
      size = 2.7, colour = "grey15", force = 2,
      point.size = 4, box.padding = 0.4, min.segment.length = 0.3,
      segment.colour = "grey60", segment.size = 0.25,
      max.overlaps = Inf, seed = 2026
    ) +
    scale_x_continuous(limits = x_lim, expand = c(0, 0)) +
    scale_y_continuous(limits = y_lim, expand = c(0, 0)) +
    labs(
      title = title,
      subtitle = paste0(group_text, ". Dashed lines = median of the group (",
                        round(x_mid, digits), " ", x_unit, ", ",
                        round(y_mid, 1), " ", y_unit, ")."),
      x = x_label,
      y = y_label,
      caption = "Data: nflverse via nflreadr | Plot: nflplotR"
    ) +
    theme_minimal(base_size = 11) +
    theme(
      panel.grid = element_blank(),
      plot.title = element_text(face = "bold", size = 15),
      plot.subtitle = element_text(colour = "grey35"),
      plot.caption = element_text(colour = "grey50", size = 8),
      plot.background = element_rect(fill = "white", colour = NA),
      plot.margin = margin(12, 16, 10, 12)
    )
}

totals <- quadrant_plot(
  wr, "targets", "fantasy_points_ppr",
  x_label = "Total targets", y_label = "Total PPR points",
  title = paste(SEASON, "Wide Receivers: Targets vs. PPR Points"),
  x_unit = "targets", y_unit = "PPR pts", digits = 0
)

per_game <- quadrant_plot(
  wr, "targets_pg", "ppr_pg",
  x_label = "Targets per game", y_label = "PPR points per game",
  title = paste(SEASON, "Wide Receivers: Targets vs. PPR Points, Per Game"),
  x_unit = "targets/game", y_unit = "PPR pts/game", digits = 1
) +
  labs(caption = "Per game = season total divided by games played. Data: nflverse via nflreadr | Plot: nflplotR")

for (plot_out in list(
  list(p = totals, file = "wr_targets_vs_ppr_2026.png"),
  list(p = per_game, file = "wr_targets_vs_ppr_per_game_2026.png")
)) {
  out <- file.path(getwd(), plot_out$file)
  ggsave(out, plot_out$p, width = 12, height = 10, dpi = 300)
  message("Saved ", out)
}
