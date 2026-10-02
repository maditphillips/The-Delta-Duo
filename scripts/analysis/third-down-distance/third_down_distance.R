# Third-down conversion rate by distance, built with nflverse + nflplotR.
#
# Off a post ranking every team's third-down conversion rate (weeks 1-3, 2026).
# Same counting rule, split by yards to go at the snap:
#   short  = 1-3 yards
#   medium = 4-6 yards
#   long   = 7+ yards
#
# A third-down play counts when nflverse marks it third_down_converted or
# third_down_failed. That rule reproduces the post's made/att for all 32 teams.
#
# Usage:  Rscript third_down_distance.R [season] [last_week]
# Writes: third_down_distance.png and third_down_distance.csv next to this file.

suppressPackageStartupMessages({
  library(nflreadr)
  library(nflplotR)
  library(dplyr)
  library(ggplot2)
  library(patchwork)
})

args <- commandArgs(trailingOnly = TRUE)
season <- if (length(args) >= 1) as.integer(args[1]) else 2026L
last_week <- if (length(args) >= 2) as.integer(args[2]) else 3L

out_dir <- local({
  f <- sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE))
  if (length(f)) dirname(normalizePath(f)) else getwd()
})

font <- if ("Roboto" %in% systemfonts::system_fonts()$family) "Roboto" else "sans"

# ---- data --------------------------------------------------------------

buckets <- c("Short (1-3 yds)", "Medium (4-6 yds)", "Long (7+ yds)")

plays <- load_pbp(season) |>
  filter(
    season_type == "REG", week <= last_week, down == 3,
    third_down_converted == 1 | third_down_failed == 1
  ) |>
  mutate(bucket = factor(case_when(
    ydstogo <= 3 ~ buckets[1],
    ydstogo <= 6 ~ buckets[2],
    TRUE ~ buckets[3]
  ), levels = buckets))

teams <- load_teams() |> select(team = team_abbr, nick = team_nick)

rates <- plays |>
  group_by(bucket, team = posteam) |>
  summarise(made = sum(third_down_converted), att = n(), .groups = "drop") |>
  mutate(pct = made / att) |>
  left_join(teams, by = "team") |>
  group_by(bucket) |>
  arrange(desc(pct), desc(att), .by_group = TRUE) |>
  mutate(rank = min_rank(desc(pct)), row = row_number()) |>
  ungroup()

league <- plays |>
  group_by(bucket) |>
  summarise(made = sum(third_down_converted), att = n(), pct = made / att)

write.csv(
  rates |> select(bucket, rank, team, made, att, pct),
  file.path(out_dir, "third_down_distance.csv"), row.names = FALSE
)

# ---- graphic -----------------------------------------------------------

ink <- "#111111"
muted <- "#6b6b6b"
stripe <- "#eef2f6"

# Bars run 0-100%; the label columns sit left of zero.
x_min <- -0.64
x_max <- 1.00
x_rank <- -0.60
x_logo <- -0.50
x_name <- -0.43

panel <- function(b) {
  d <- filter(rates, bucket == b)
  lg <- filter(league, bucket == b)
  n <- nrow(d)

  ggplot(d, aes(y = row)) +
    geom_rect(
      data = filter(d, row %% 2 == 1),
      aes(xmin = x_min, xmax = x_max, ymin = row - 0.5, ymax = row + 0.5),
      fill = stripe, inherit.aes = FALSE
    ) +
    geom_vline(xintercept = seq(0, 1, 0.25), colour = "#d9dee4", linewidth = 0.3) +
    geom_vline(xintercept = lg$pct, linetype = "dashed", colour = muted, linewidth = 0.5) +
    geom_col(
      aes(x = pct, fill = team), orientation = "y", width = 0.78
    ) +
    annotate(
      "label", x = lg$pct, y = n + 1.1,
      label = sprintf("NFL avg %.1f%%", 100 * lg$pct),
      family = font, size = 3.4, colour = ink, fill = "white",
      label.size = 0, label.padding = unit(0.12, "lines")
    ) +
    geom_text(aes(x = x_rank, label = paste0(rank, ".")),
              family = font, size = 4.8, colour = muted, hjust = 1) +
    geom_nfl_logos(aes(x = x_logo, team_abbr = team), height = 0.027) +
    geom_text(aes(x = x_name, label = nick),
              family = font, fontface = "bold", size = 5.4, colour = ink, hjust = 0) +
    # Mask the average line behind each % label, in that row's background.
    geom_rect(
      data = d,
      aes(xmin = pct + 0.008, xmax = pct + 0.135, ymin = row - 0.4, ymax = row + 0.4),
      fill = if_else(d$row %% 2 == 1, stripe, "white"), inherit.aes = FALSE
    ) +
    geom_text(aes(x = pct + 0.015, label = sprintf("%.1f%%", 100 * pct)),
              family = font, fontface = "bold", size = 5, colour = ink, hjust = 0) +
    scale_fill_nfl(type = "primary") +
    scale_x_continuous(
      breaks = seq(0, 1, 0.25), labels = scales::percent,
      expand = expansion(0)
    ) +
    scale_y_reverse(expand = expansion(add = c(0.6, 0.7))) +
    coord_cartesian(xlim = c(x_min, x_max), clip = "off") +
    labs(title = b, subtitle = sprintf("NFL: %d / %d", lg$made, lg$att)) +
    theme_void(base_family = font) +
    theme(
      plot.title = element_text(face = "bold", size = 20, hjust = 0.5, colour = ink),
      plot.subtitle = element_text(size = 12, hjust = 0.5, colour = muted,
                                   margin = margin(t = 3, b = 6)),
      axis.text.x = element_text(size = 10, colour = muted, margin = margin(t = 4)),
      plot.margin = margin(4, 14, 4, 14)
    )
}

weeks_label <- if (last_week == 1) "Week 1" else sprintf("Weeks 1-%d", last_week)

p <- wrap_plots(lapply(buckets, panel), nrow = 1) +
  plot_annotation(
    title = "THIRD-DOWN CONVERSION RATE BY DISTANCE",
    subtitle = sprintf("%s, %d  |  distance = yards to go at the snap", weeks_label, season),
    caption = "Data: nflverse  |  Chart: The Delta Duo  |  Small samples: most teams have 7-20 attempts per bucket",
    theme = theme(
      plot.background = element_rect(fill = "white", colour = NA),
      plot.title = element_text(family = font, face = "bold", size = 34,
                                hjust = 0.5, colour = ink, margin = margin(t = 10)),
      plot.subtitle = element_text(family = font, size = 16, hjust = 0.5,
                                   colour = muted, margin = margin(t = 6, b = 14)),
      plot.caption = element_text(family = font, size = 12, colour = muted,
                                  hjust = 0.5, margin = margin(t = 14, b = 6))
    )
  )

ragg::agg_png(file.path(out_dir, "third_down_distance.png"),
              width = 2700, height = 1650, res = 130)
print(p)
invisible(dev.off())

message("Wrote ", file.path(out_dir, "third_down_distance.png"))
