suppressPackageStartupMessages({library(ggplot2); library(nflplotR); library(dplyr)})
d <- read.csv("plot.csv", stringsAsFactors = FALSE)
nick <- c(LV="Raiders",CLE="Browns",LA="Rams",ARI="Cardinals",JAX="Jaguars",HOU="Texans",BUF="Bills",
          CHI="Bears",DET="Lions",TEN="Titans",NYJ="Jets",WAS="Commanders",CIN="Bengals")
fmt <- function(x) ifelse(is.na(x) | x=="", "now", format(as.Date(x), "%b %Y"))
d <- d |>
  mutate(group = ifelse(kind=="done", "LONGEST GAPS (ENDED)", "DROUGHTS STILL GOING"),
         group = factor(group, c("LONGEST GAPS (ENDED)","DROUGHTS STILL GOING")),
         label = paste0(nick[team], "  ", fmt(start), " to ", fmt(end)),
         id = paste(team, start)) |>
  arrange(desc(group), games) |>
  mutate(y = row_number() + ifelse(kind == "done", 1.6, 0),
         value_lab = paste0(games, " games", ifelse(kind=="ongoing", " & counting", "")))

ink <- "#1f2328"; muted <- "#6b7280"; grid <- "#e5e7eb"
p <- ggplot(d, aes(y = y, x = games)) +
  geom_col(aes(fill = team, alpha = kind), width = 0.72, orientation = "y") +
  annotate("segment", x = 37, xend = 37, y = 0.4, yend = max(d$y) + 0.5, linetype = "22", colour = "#FF3C00", linewidth = 0.6) +
  geom_nfl_logos(aes(x = games + 4.5, team_abbr = team), height = 0.05) +
  geom_text(aes(x = games + 9.5, label = value_lab), hjust = 0, size = 3.6, colour = ink, fontface = "bold") +
  annotate("text", x = -1.5, y = c(max(d$y) + 1, 5.9), label = c("LONGEST GAPS (ENDED)", "DROUGHTS STILL GOING"), hjust = 1, size = 3.3, colour = "#FF3C00", fontface = "bold") +
  scale_fill_nfl(alpha = 1) +
  scale_alpha_manual(values = c(done = 1, ongoing = 1), guide = "none") +
  scale_y_continuous(breaks = d$y, labels = d$label) +
  scale_x_continuous(breaks = seq(0, 120, 20), expand = c(0, 0)) +
  coord_cartesian(xlim = c(0, 145), clip = "off") +
  labs(title = "Longest NFL droughts between 3-game winning streaks",
       subtitle = paste0("Games played from the last win of one 3+ game win streak to the 3rd win of the next. 1999 to present, playoffs included.\n",
                         "Orange line: the Browns' drought that ended Oct 1, 2026 with a win over Pittsburgh (37 games, Dec 2023 to Oct 2026)."),
       x = "Games between 3-game win streaks", y = NULL,
       caption = "Data: nflverse  |  Chart: nflplotR  |  Ties end a streak. Relocated teams combined (Raiders, Rams).") +
  theme_minimal(base_size = 12) +
  theme(plot.title = element_text(face = "bold", size = 17, colour = ink),
        plot.subtitle = element_text(colour = muted, size = 10.5, lineheight = 1.15, margin = margin(b = 12)),
        plot.caption = element_text(colour = muted, size = 8.5, hjust = 0),
        plot.caption.position = "plot",
        plot.title.position = "plot",
        axis.text.y = element_text(colour = ink, face = "bold", size = 10.5), axis.text.x = element_text(colour = muted),
        axis.title.x = element_text(colour = muted, size = 10, margin = margin(t = 8)),
        panel.grid.major.y = element_blank(), panel.grid.minor = element_blank(),
        panel.grid.major.x = element_line(colour = grid, linewidth = 0.4),
        strip.placement = "outside", strip.text.y.left = element_text(angle = 90, face = "bold", colour = ink, size = 10),
        panel.spacing.y = unit(14, "pt"),
        plot.background = element_rect(fill = "white", colour = NA),
        plot.margin = margin(18, 22, 12, 12))
ggsave("three_game_streak_droughts.png", p, width = 11, height = 8.5, dpi = 200)
