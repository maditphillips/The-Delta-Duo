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

MARK_COLOUR <- "#C2410C"
# Light green / red bands for split = "ref_line"
ABOVE_FILL <- "#DFF1E4"
BELOW_FILL <- "#F9DEDC"

# Remove specific player-weeks (e.g. a game a player left early injured) from
# season totals. `exclude` has player_display_name, week and reason columns;
# `weekly` is load_player_stats(summary_level = "week") for the same season.
drop_excluded_games <- function(stats, exclude, weekly) {
  removed <- weekly |>
    dplyr::inner_join(exclude, by = c("player_display_name", "week")) |>
    dplyr::group_by(player_id) |>
    dplyr::summarise(
      drop_games = dplyr::n(),
      drop_targets = sum(targets),
      drop_carries = sum(carries),
      drop_receptions = sum(receptions),
      drop_ppr = sum(fantasy_points_ppr)
    )
  stats |>
    dplyr::left_join(removed, by = "player_id") |>
    dplyr::mutate(
      games = games - dplyr::coalesce(drop_games, 0L),
      targets = targets - dplyr::coalesce(drop_targets, 0L),
      carries = carries - dplyr::coalesce(drop_carries, 0L),
      receptions = receptions - dplyr::coalesce(drop_receptions, 0L),
      fantasy_points_ppr = fantasy_points_ppr - dplyr::coalesce(drop_ppr, 0)
    ) |>
    dplyr::select(-starts_with("drop_"))
}

# "Left out: KC Concepcion Week 5 (injured)." or NULL when nothing is excluded
excluded_note <- function(exclude) {
  if (nrow(exclude) == 0) return(NULL)
  paste0("Left out: ", paste0(exclude$player_display_name, " Week ", exclude$week,
                              " (", exclude$reason, ")", collapse = "; "), ".")
}

# "Amon-Ra St. Brown" -> "A. St. Brown". When two players would get the same
# short name (Bijan and Brian Robinson), both keep their full names.
short_name <- function(full_name) {
  short <- paste0(substr(full_name, 1, 1), ". ", sub("^\\S+\\s+", "", full_name))
  dup <- short %in% short[duplicated(short)]
  ifelse(dup, full_name, short)
}

quadrant_plot <- function(data, x, y, x_label, y_label, title, subtitle_lead = NULL,
                          x_unit, y_unit, x_digits = 1, y_digits = 1,
                          quadrant_text = POINTS_QUADRANTS,
                          quadrant_fill = c(top_left = "#FCE9DC", top_right = "#DFF1E4",
                                            bottom_left = "#EEEEEE", bottom_right = "#DDEAF7"),
                          caption = "Data: nflverse via nflreadr | Plot: nflplotR",
                          rank_col = NULL, top_n = 10,
                          ref_slope = NULL, ref_label = NULL, label_force = 2,
                          split = c("median", "ref_line"),
                          ref_text = c(above = "ABOVE THE LINE", below = "BELOW THE LINE"),
                          subtitle = NULL, x_split = NULL, y_split = NULL,
                          mark_top = c("none", "number", "circle")) {
  # split: "median" shades four boxes split at the group medians; "ref_line"
  # shades green above the ref_slope line and red below it instead
  split <- match.arg(split)
  # mark_top: flag the players ranked 1..top_n in rank_col with a big rank
  # number beside the logo, or a ring around it
  mark_top <- match.arg(mark_top)
  is_top <- if (mark_top == "none") rep(FALSE, nrow(data)) else data[[rank_col]] <= top_n
  top <- data[is_top, ]

  xv <- data[[x]]
  yv <- data[[y]]
  # Quadrant split points: group medians unless given
  x_mid <- if (is.null(x_split)) median(xv) else x_split
  y_mid <- if (is.null(y_split)) median(yv) else y_split

  # Pad the axes so logos and labels at the edges aren't clipped
  x_pad <- diff(range(xv)) * 0.08
  y_pad <- diff(range(yv)) * 0.08
  x_lim <- c(min(xv) - x_pad, max(xv) + x_pad)
  # Extra room at top and bottom for the quadrant titles
  y_lim <- c(min(yv) - 1.8 * y_pad, max(yv) + 1.8 * y_pad)

  quadrants <- tibble::tribble(
    ~xmin,    ~xmax,    ~ymin,    ~ymax,    ~fill,
    x_lim[1], x_mid,    y_mid,    y_lim[2], quadrant_fill[["top_left"]],
    x_mid,    x_lim[2], y_mid,    y_lim[2], quadrant_fill[["top_right"]],
    x_lim[1], x_mid,    y_lim[1], y_mid,    quadrant_fill[["bottom_left"]],
    x_mid,    x_lim[2], y_lim[1], y_mid,    quadrant_fill[["bottom_right"]]
  )

  quadrant_labels <- tibble::tribble(
    ~x,       ~y,       ~hjust, ~vjust, ~text,
    x_lim[1], y_lim[2], 0,      1,      quadrant_text[["top_left"]],
    x_lim[2], y_lim[2], 1,      1,      quadrant_text[["top_right"]],
    x_lim[1], y_lim[1], 0,      0,      quadrant_text[["bottom_left"]],
    x_lim[2], y_lim[1], 1,      0,      quadrant_text[["bottom_right"]]
  )

  # Optional dashed reference line through the origin (y = ref_slope * x),
  # labelled near the right edge
  ref_layer <- if (!is.null(ref_slope)) {
    label_x <- min(x_lim[2], y_lim[2] / ref_slope) - diff(x_lim) * 0.02
    list(
      geom_abline(slope = ref_slope, intercept = 0, linetype = "longdash",
                  colour = MARK_COLOUR, linewidth = 0.5),
      annotate("text", x = label_x, y = ref_slope * label_x, label = ref_label,
               hjust = 1, vjust = -0.6, size = 3.2, fontface = "bold",
               colour = MARK_COLOUR, angle = 0)
    )
  }

  background <- if (split == "median") {
    list(
      geom_rect(
        data = quadrants, inherit.aes = FALSE,
        aes(xmin = xmin, xmax = xmax, ymin = ymin, ymax = ymax, fill = fill)
      ),
      scale_fill_identity(),
      geom_vline(xintercept = x_mid, linetype = "dashed", colour = "grey55", linewidth = 0.4),
      geom_hline(yintercept = y_mid, linetype = "dashed", colour = "grey55", linewidth = 0.4),
      ref_layer,
      geom_text(
        data = quadrant_labels, inherit.aes = FALSE,
        aes(x = x, y = y, label = text, hjust = hjust, vjust = vjust),
        size = 3.2, fontface = "bold", colour = "grey30", lineheight = 0.95,
        nudge_x = c(1, -1, 1, -1) * x_pad * 0.15,
        nudge_y = c(-1, -1, 1, 1) * y_pad * 0.15
      )
    )
  } else {
    # Line clamped to the panel so the two bands meet exactly along it
    band <- tibble::tibble(bx = seq(x_lim[1], x_lim[2], length.out = 200)) |>
      dplyr::mutate(line = pmin(pmax(ref_slope * bx, y_lim[1]), y_lim[2]))
    list(
      geom_ribbon(data = band, inherit.aes = FALSE,
                  aes(x = bx, ymin = line, ymax = y_lim[2]), fill = ABOVE_FILL),
      geom_ribbon(data = band, inherit.aes = FALSE,
                  aes(x = bx, ymin = y_lim[1], ymax = line), fill = BELOW_FILL),
      ref_layer,
      annotate("text", x = x_lim[1] + x_pad * 0.15, y = y_lim[2] - y_pad * 0.15,
               label = ref_text[["above"]], hjust = 0, vjust = 1,
               size = 3.2, fontface = "bold", colour = "grey30", lineheight = 0.95),
      annotate("text", x = x_lim[2] - x_pad * 0.15, y = y_lim[1] + y_pad * 0.15,
               label = ref_text[["below"]], hjust = 1, vjust = 0,
               size = 3.2, fontface = "bold", colour = "grey30", lineheight = 0.95)
    )
  }

  median_text <- paste0("Dashed lines = median of the group (",
                        format(round(x_mid, x_digits), nsmall = x_digits), " ", x_unit, ", ",
                        format(round(y_mid, y_digits), nsmall = y_digits), " ", y_unit, ").")
  if (is.null(subtitle)) {
    subtitle <- paste0(if (length(subtitle_lead)) paste0(subtitle_lead, ". "), median_text)
  }

  top_layer <- switch(mark_top,
    none = NULL,
    number = geom_text(
      data = top, aes(label = .data[[rank_col]]),
      hjust = 1, vjust = 0, nudge_x = -diff(x_lim) * 0.008, nudge_y = diff(y_lim) * 0.008,
      size = 7, fontface = "bold", colour = MARK_COLOUR
    ),
    circle = geom_point(data = top, shape = 21, size = 13, stroke = 1.2,
                        colour = MARK_COLOUR, fill = NA)
  )

  ggplot(data, aes(x = .data[[x]], y = .data[[y]])) +
    background +
    geom_nfl_logos(aes(team_abbr = recent_team), width = 0.026, alpha = 0.95) +
    top_layer +
    geom_text_repel(
      aes(label = label),
      size = 2.7, colour = "grey15", force = label_force,
      # Keep name labels clear of the rank numbers / rings too
      point.size = ifelse(is_top, 12, 7), box.padding = 0.3, min.segment.length = 0,
      segment.colour = "grey60", segment.size = 0.25,
      max.overlaps = Inf, seed = 2026
    ) +
    scale_x_continuous(limits = x_lim, expand = c(0, 0)) +
    scale_y_continuous(limits = y_lim, expand = c(0, 0)) +
    labs(
      title = title,
      subtitle = subtitle,
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
