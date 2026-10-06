# Shared quadrant chart: one logo per player, name labels, and four shaded
# quadrants split at the median of the plotted players on each axis.
# Needs nflplotR, ggplot2, ggrepel and tibble.

# Buy/sell labels for usage (x) vs. fantasy points (y) charts
POINTS_QUADRANTS <- c(
  top_left     = "SELL CANDIDATES\nPoints without the usage",
  top_right    = "JUGGERNAUTS\nVolume and production",
  bottom_left  = "LOST CAUSES\nLittle volume, little production",
  bottom_right = "TRADE TARGETS\nOpportunity not yet cashed in"
)

# "Amon-Ra St. Brown" -> "A. St. Brown". When two players would get the same
# short name (Bijan and Brian Robinson), both keep their full names.
short_name <- function(full_name) {
  short <- paste0(substr(full_name, 1, 1), ". ", sub("^\\S+\\s+", "", full_name))
  dup <- short %in% short[duplicated(short)]
  ifelse(dup, full_name, short)
}

quadrant_plot <- function(data, x, y, x_label, y_label, title, subtitle_lead,
                          x_unit, y_unit, x_digits = 1, y_digits = 1,
                          quadrant_text = POINTS_QUADRANTS,
                          caption = "Data: nflverse via nflreadr | Plot: nflplotR") {
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
    x_lim[1], x_mid,    y_mid,    y_lim[2], "#FCE9DC",  # top left
    x_mid,    x_lim[2], y_mid,    y_lim[2], "#DFF1E4",  # top right
    x_lim[1], x_mid,    y_lim[1], y_mid,    "#EEEEEE",  # bottom left
    x_mid,    x_lim[2], y_lim[1], y_mid,    "#DDEAF7"   # bottom right
  )

  quadrant_labels <- tibble::tribble(
    ~x,       ~y,       ~hjust, ~vjust, ~text,
    x_lim[1], y_lim[2], 0,      1,      quadrant_text[["top_left"]],
    x_lim[2], y_lim[2], 1,      1,      quadrant_text[["top_right"]],
    x_lim[1], y_lim[1], 0,      0,      quadrant_text[["bottom_left"]],
    x_lim[2], y_lim[1], 1,      0,      quadrant_text[["bottom_right"]]
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
      point.size = 7, box.padding = 0.3, min.segment.length = 0,
      segment.colour = "grey60", segment.size = 0.25,
      max.overlaps = Inf, seed = 2026
    ) +
    scale_x_continuous(limits = x_lim, expand = c(0, 0)) +
    scale_y_continuous(limits = y_lim, expand = c(0, 0)) +
    labs(
      title = title,
      subtitle = paste0(subtitle_lead, ". Dashed lines = median of the group (",
                        format(round(x_mid, x_digits), nsmall = x_digits), " ", x_unit, ", ",
                        format(round(y_mid, y_digits), nsmall = y_digits), " ", y_unit, ")."),
      x = x_label,
      y = y_label,
      caption = caption
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

save_quadrant_plot <- function(p, file) {
  out <- file.path(getwd(), file)
  ggsave(out, p, width = 12, height = 10, dpi = 300)
  message("Saved ", out)
}
