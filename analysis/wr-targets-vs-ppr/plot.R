# Top 60 WRs of the 2026 season (plus any extra names in ALWAYS_INCLUDE):
# total targets (x) vs. total PPR points (y).
# Quadrants split at the median of the plotted players on each axis.
#
# install.packages(c("nflreadr", "nflplotR", "ggplot2", "dplyr", "ggrepel"))
# Run: Rscript plot.R   -> writes wr_targets_vs_ppr_2026.png next to this file

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

wr <- stats |>
  filter(position == "WR") |>
  arrange(desc(fantasy_points_ppr)) |>
  filter(row_number() <= N_PLAYERS | player_display_name %in% ALWAYS_INCLUDE) |>
  mutate(
    # "Amon-Ra St. Brown" -> "A. St. Brown"
    label = paste0(substr(player_display_name, 1, 1), ". ",
                   sub("^\\S+\\s+", "", player_display_name))
  )

x_mid <- median(wr$targets)
y_mid <- median(wr$fantasy_points_ppr)

# Pad the axes so logos and labels at the edges aren't clipped
x_pad <- diff(range(wr$targets)) * 0.08
y_pad <- diff(range(wr$fantasy_points_ppr)) * 0.08
x_lim <- c(min(wr$targets) - x_pad, max(wr$targets) + x_pad)
# Extra room at top and bottom for the quadrant titles
y_lim <- c(min(wr$fantasy_points_ppr) - 1.8 * y_pad, max(wr$fantasy_points_ppr) + 1.8 * y_pad)

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

p <- ggplot(wr, aes(x = targets, y = fantasy_points_ppr)) +
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
    title = paste(SEASON, "Wide Receivers: Targets vs. PPR Points"),
    subtitle = paste0("Top ", N_PLAYERS, " WRs by PPR points",
                      if (length(ALWAYS_INCLUDE)) paste0(" + ", paste(ALWAYS_INCLUDE, collapse = ", ")) else "",
                      ". Dashed lines = median of the group (",
                      x_mid, " targets, ", round(y_mid, 1), " PPR pts)."),
    x = "Total targets",
    y = "Total PPR points",
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

out <- file.path(getwd(), "wr_targets_vs_ppr_2026.png")
ggsave(out, p, width = 12, height = 10, dpi = 300)
message("Saved ", out)
