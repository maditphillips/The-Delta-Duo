# Finish-odds charts from sim_2026.csv, one PNG per position.
#
#   Rscript plot.R [season]      -> plots/finish_odds_<pos>_<season>.png
#
# Needs ggplot2 and nflplotR (team logos ship inside nflplotR).
suppressPackageStartupMessages({
  library(ggplot2)
  library(nflplotR)
})

args <- commandArgs(trailingOnly = TRUE)
season <- if (length(args)) as.integer(args[1]) else 2026L
sim <- read.csv(sprintf("sim_%d.csv", season), stringsAsFactors = FALSE)
dir.create("plots", showWarnings = FALSE)
cutoff <- max(sim$games_so_far)  # every regular starter has played every week so far

N_ROWS <- 24
INK <- "#1d2125"; INK_2 <- "#5c6670"; MUTED <- "#8a949c"; SURFACE <- "#fcfcfb"
# one-hue ordinal ramp (validated), dark = best tier; misses are neutral gray
TIER_FILL <- c("#104281", "#2a78d6", "#86b6ef", "#e3e1dc")

# tier cut points per position: best tier, middle, deep, outside
CUTS <- list(QB = c(6, 12, 24), TE = c(6, 12, 24), RB = c(12, 24, 36), WR = c(12, 24, 36))
LONG <- c(QB = "quarterbacks", RB = "running backs", WR = "wide receivers", TE = "tight ends")

plot_pos <- function(pos) {
  cuts <- CUTS[[pos]]
  d <- sim[sim$pos == pos, ]
  d <- head(d[order(-d$p50_pts, -d$mean_pts), ], N_ROWS)
  d$label <- factor(d$player, levels = rev(d$player))

  cum <- sapply(cuts, function(k) d[[paste0("top", k)]])
  shares <- cbind(cum[, 1], cum[, 2] - cum[, 1], cum[, 3] - cum[, 2], 1 - cum[, 3])
  tiers <- c(sprintf("Top %d", cuts[1]), sprintf("%d-%d", cuts[1] + 1, cuts[2]),
             sprintf("%d-%d", cuts[2] + 1, cuts[3]), sprintf("Outside top %d", cuts[3]))
  long <- data.frame(
    label = rep(d$label, 4),
    tier = factor(rep(tiers, each = nrow(d)), levels = rev(tiers)),
    share = pmax(0, as.vector(shares))
  )

  pct <- function(x) ifelse(x >= 0.005, sprintf("%.0f%%", 100 * x), "<1%")
  # in-bar labels only on the best tier, and only when the segment is wide enough
  best <- data.frame(label = d$label, share = cum[, 1])
  best <- best[best$share >= 0.08, ]

  ggplot(long, aes(x = share, y = label)) +
    geom_col(aes(fill = tier), width = 0.72, colour = SURFACE, linewidth = 0.6) +
    geom_text(data = best, aes(x = share - 0.012, label = pct(share)),
              hjust = 1, size = 3, colour = "white", fontface = "bold") +
    geom_nfl_logos(data = d, aes(x = -0.045, y = label, team_abbr = team), width = 0.032) +
    geom_text(data = d, aes(x = 1.06, label = pct(top1)), size = 3.1, colour = INK) +
    geom_text(data = d, aes(x = 1.19, label = sprintf("%.0f", p50_pts)), size = 3.1, colour = INK) +
    annotate("text", x = c(1.06, 1.19), y = N_ROWS + 0.9, label = c("#1", "Median pts"),
             size = 2.9, colour = INK_2, fontface = "bold") +
    scale_fill_manual(values = setNames(rev(TIER_FILL), rev(tiers)), breaks = tiers, name = NULL) +
    scale_x_continuous(breaks = seq(0, 1, 0.25), labels = function(x) paste0(100 * x, "%"),
                       expand = expansion(0)) +
    scale_y_discrete(expand = expansion(add = c(0.6, 1.4))) +
    coord_cartesian(xlim = c(-0.08, 1.26), clip = "off") +
    labs(
      title = sprintf("Where %d's %s finish", season, LONG[[pos]]),
      subtitle = sprintf(paste0("Share of 10,000 simulated seasons landing in each PPR finish tier.\n",
                                "Weeks 1-%d are real; weeks %d-18 are simulated. Top %d by median points."),
                         cutoff, cutoff + 1, N_ROWS),
      x = NULL, y = NULL,
      caption = "Data: nflverse  |  Logos: nflplotR  |  The Delta Duo"
    ) +
    theme_minimal(base_size = 11) +
    theme(
      plot.background = element_rect(fill = SURFACE, colour = NA),
      panel.grid = element_blank(),
      panel.grid.major.x = element_line(colour = "#e8e6e1", linewidth = 0.3),
      axis.text.y = element_text(colour = INK, size = 9.5, margin = margin(r = 22)),
      axis.text.x = element_text(colour = MUTED, size = 8.5),
      plot.title = element_text(colour = INK, face = "bold", size = 15),
      plot.subtitle = element_text(colour = INK_2, size = 9.5, margin = margin(b = 10)),
      plot.caption = element_text(colour = MUTED, size = 8),
      plot.title.position = "plot",
      legend.position = "top", legend.justification = "left",
      legend.text = element_text(colour = INK_2, size = 9),
      legend.key.size = unit(10, "pt"),
      plot.margin = margin(16, 16, 12, 12)
    )
}

for (pos in names(CUTS)) {
  out <- sprintf("plots/finish_odds_%s_%d.png", tolower(pos), season)
  ggsave(out, plot_pos(pos), width = 8, height = 9, dpi = 200, bg = SURFACE)
  cat("->", out, "\n")
}
