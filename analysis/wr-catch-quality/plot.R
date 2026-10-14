# Why do receivers miss catches? Same WR group as the targets vs. PPR chart
# (top 60 by total PPR + ALWAYS_INCLUDE, with EXCLUDE_GAMES left out).
#
#   Catch probability: nflfastR's model of how often a target like this is
#     caught (air yards, field position, pass location, down, ...). Averaged
#     over a player's targets it says how hard his targets are.
#   Catch % over expected: actual catch rate minus that average, on the
#     targets that have a catch probability.
#   Drop rate: Pro Football Reference drops / targets.
#
# Outputs: wr_catch_quality_2026.png (drop rate vs. catch % over expected)
#          wr_catch_quality_2026.csv and .md (the full table)
#
# install.packages(c("nflreadr", "nflplotR", "ggplot2", "dplyr", "ggrepel"))
# Run from this folder: Rscript plot.R

library(nflreadr)
library(nflplotR)
library(ggplot2)
library(dplyr)
library(ggrepel)
source("../lib/quadrant_plot.R")

SEASON <- 2026
N_PLAYERS <- 60
ALWAYS_INCLUDE <- c("KC Concepcion")
EXCLUDE_GAMES <- tibble::tribble(
  ~player_display_name, ~week, ~reason,
  "KC Concepcion",      5,     "injured"
)

stats <- load_player_stats(seasons = SEASON, summary_level = "reg")
weekly <- load_player_stats(seasons = SEASON, summary_level = "week")
pbp <- load_pbp(seasons = SEASON)
pfr <- load_pfr_advstats(seasons = SEASON, stat_type = "rec", summary_level = "week")
players <- load_players()

if (nrow(EXCLUDE_GAMES)) stats <- drop_excluded_games(stats, EXCLUDE_GAMES, weekly)

wr <- stats |>
  filter(position == "WR") |>
  arrange(desc(fantasy_points_ppr)) |>
  filter(row_number() <= N_PLAYERS | player_display_name %in% ALWAYS_INCLUDE) |>
  select(player_id, player_display_name, recent_team, games, targets, receptions)

# player_id + week pairs to leave out of the play-by-play and drop data
excluded_ids <- weekly |>
  inner_join(EXCLUDE_GAMES, by = c("player_display_name", "week")) |>
  distinct(player_id, week)

# Every regular-season target (real pass attempts only: no sacks, no 2-pt tries)
targets_pbp <- pbp |>
  filter(season_type == "REG", pass_attempt == 1, sack == 0, two_point_attempt == 0,
         !is.na(receiver_player_id)) |>
  anti_join(excluded_ids, by = c("receiver_player_id" = "player_id", "week")) |>
  filter(receiver_player_id %in% wr$player_id)

# Catch probability only exists when the throw has a recorded depth;
# expected-catch numbers use just those targets
catch_model <- targets_pbp |>
  filter(!is.na(cp)) |>
  group_by(player_id = receiver_player_id) |>
  summarise(
    cp_targets = n(),
    cp_catches = sum(complete_pass),
    avg_catch_prob = mean(cp)
  )

# Drops: link PFR ids via the player list, falling back to name + team
pfr_ids <- players |>
  filter(gsis_id %in% wr$player_id, !is.na(pfr_id), pfr_id != "") |>
  select(player_id = gsis_id, pfr_id)
missing_ids <- wr |>
  anti_join(pfr_ids, by = "player_id") |>
  inner_join(distinct(pfr, pfr_player_name, team, pfr_player_id),
             by = c("player_display_name" = "pfr_player_name", "recent_team" = "team")) |>
  select(player_id, pfr_id = pfr_player_id)
pfr_ids <- bind_rows(pfr_ids, missing_ids)

drops <- pfr |>
  filter(game_type == "REG") |>
  inner_join(pfr_ids, by = c("pfr_player_id" = "pfr_id")) |>
  anti_join(excluded_ids, by = c("player_id", "week")) |>
  group_by(player_id) |>
  summarise(drops = sum(receiving_drop, na.rm = TRUE))

wr <- wr |>
  left_join(catch_model, by = "player_id") |>
  left_join(drops, by = "player_id") |>
  mutate(
    drops = coalesce(drops, 0L),
    catch_rate = receptions / targets,
    drop_rate = drops / targets,
    cp_catch_rate = cp_catches / cp_targets,
    catch_over_expected = cp_catch_rate - avg_catch_prob,
    label = short_name(player_display_name),
    drop_pct = 100 * drop_rate,
    cpoe_pts = 100 * catch_over_expected
  )

group_drop_rate <- sum(wr$drops) / sum(wr$targets)
exclude_note <- excluded_note(EXCLUDE_GAMES)

p <- quadrant_plot(
  wr, "drop_pct", "cpoe_pts",
  x_label = "Drop rate (% of targets dropped)",
  y_label = "Catch % over expected (percentage points)",
  title = paste(SEASON, "Wide Receivers: Drops vs. Catching Over Expected"),
  x_unit = "", y_unit = "",
  x_split = 100 * group_drop_rate, y_split = 0,
  subtitle = paste0("Up = catches more than a typical receiver would on the same targets. ",
                    "Right = drops more. Lines: group drop rate (",
                    format(round(100 * group_drop_rate, 1), nsmall = 1), "%) and zero."),
  quadrant_text = c(
    top_left     = "SURE HANDS\nAbove expected, few drops",
    top_right    = "MAKING UP FOR DROPS\nAbove expected despite drops",
    bottom_left  = "NOT THE HANDS\nFew drops, still below expected",
    bottom_right = "DROPS ARE THE PROBLEM\nDrops and below expected"
  ),
  quadrant_fill = c(top_left = ABOVE_FILL, top_right = "#F3F1E4",
                    bottom_left = "#EEEEEE", bottom_right = BELOW_FILL),
  label_force = 4,
  caption = paste0(
    "Expected = nflfastR catch probability for each target (depth, location, down, etc.). Drops: Pro Football Reference.\n",
    paste(c(exclude_note, "Data: nflverse via nflreadr | Plot: nflplotR"), collapse = " ")
  )
)
save_quadrant_plot(p, "wr_catch_quality_2026.png")

# Full table, best catch % over expected first
pct <- function(v) round(100 * v, 1)
tbl <- wr |>
  arrange(desc(catch_over_expected)) |>
  transmute(
    Player = player_display_name,
    Team = recent_team,
    Games = games,
    Targets = targets,
    Catches = receptions,
    `Catch %` = pct(catch_rate),
    `Avg catch probability %` = pct(avg_catch_prob),
    `Catch % over expected` = pct(catch_over_expected),
    Drops = drops,
    `Drop rate %` = pct(drop_rate)
  )
write.csv(tbl, "wr_catch_quality_2026.csv", row.names = FALSE)

md <- c(
  paste("#", SEASON, "Wide Receivers: Catch Quality"),
  "",
  "- **Avg catch probability %**: how often a typical receiver catches targets like his (nflfastR model). Lower = harder targets (deeper, tighter windows, worse spots).",
  "- **Catch % over expected**: his catch rate minus that average, on targets with a catch probability. Positive = catching more than expected.",
  "- **Drop rate %**: Pro Football Reference drops divided by targets.",
  paste0("- Group drop rate: ", pct(group_drop_rate), "%. ", if (!is.null(exclude_note)) exclude_note),
  "",
  paste0("| ", paste(names(tbl), collapse = " | "), " |"),
  paste0("|", paste(rep("---", ncol(tbl)), collapse = "|"), "|"),
  apply(tbl, 1, function(r) paste0("| ", paste(trimws(r), collapse = " | "), " |"))
)
writeLines(md, "wr_catch_quality_2026.md")
message("Saved table to wr_catch_quality_2026.csv and .md")
