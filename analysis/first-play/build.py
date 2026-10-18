"""Build one row per team per game with that team's first offensive play and game outcomes.

Usage: python3 build.py   (reads data/pbp_YYYY.parquet)  ->  team_games.csv

First offensive play = the team's first snap with play_type run or pass. Penalties that
wipe out the play (no_play), kneels, spikes and 2-point tries are skipped. Type goes by
result: a QB scramble is a run, a sack is a pass (negative yards).
Regular season 2016-2025, games with a final score.
"""
import numpy as np
import pandas as pd

COLS = ['game_id', 'play_id', 'season', 'week', 'season_type', 'posteam', 'defteam',
        'home_team', 'away_team', 'home_score', 'away_score', 'play_type', 'yards_gained',
        'qb_scramble', 'sack', 'two_point_attempt', 'qtr', 'score_differential', 'touchdown',
        'first_down', 'fixed_drive_result']

p = pd.concat([pd.read_parquet(f'data/pbp_{y}.parquet', columns=COLS) for y in range(2016, 2026)])
p = p[(p.season_type == 'REG') & p.home_score.notna()]
p = p[p.play_type.isin(['run', 'pass']) & (p.two_point_attempt != 1)].sort_values(['game_id', 'play_id'])
p['is_pass'] = (p.play_type == 'pass').astype(int)
# Neutral = quarters 1-3, score within 7: game script isn't forcing the play call
p['neutral'] = (p.qtr <= 3) & (p.score_differential.abs() <= 7)

grp = p.groupby(['game_id', 'posteam'])
first = grp.head(1).set_index(['game_id', 'posteam'], drop=False)
# Pass rates leave the first play out, so it can't predict itself
rest = p.drop(grp.head(1).index)
rgrp = rest.groupby(['game_id', 'posteam'])
t = pd.DataFrame({
    'season': first.season, 'week': first.week, 'opp': first.defteam,
    'home': first.posteam == first.home_team,
    'first_type': first.play_type, 'first_yds': first.yards_gained,
    'first_scramble': first.qb_scramble.fillna(0).astype(int), 'first_sack': first.sack.fillna(0).astype(int),
    'first_first_down': first.first_down.fillna(0).astype(int),
    'first_drive_result': first.fixed_drive_result,
    'plays': grp.size(), 'total_yds': grp.yards_gained.sum(),
    'pass_rate': rgrp.is_pass.mean(), 'rest_plays': rgrp.size(),
    'neutral_plays': rgrp.neutral.sum(),
    'neutral_pass_rate': rest[rest.neutral].groupby(['game_id', 'posteam']).is_pass.mean(),
}).rename_axis(['game_id', 'team']).reset_index()
t['rest_yds'] = t.total_yds - t.first_yds

scores = p.groupby('game_id')[['home_team', 'home_score', 'away_score']].first()
t = t.join(scores, on='game_id')
t['pf'] = np.where(t.home, t.home_score, t.away_score)
t['pa'] = np.where(t.home, t.away_score, t.home_score)
t['margin'] = t.pf - t.pa
t['win'] = np.sign(t.margin) / 2 + .5  # tie = .5
t = t.drop(columns=['home_team', 'home_score', 'away_score'])

# Season pass rate for the team, leaving this game out
s = t.assign(passes=t.pass_rate * t.rest_plays).groupby(['season', 'team'])[['passes', 'rest_plays']].transform('sum')
t['season_pass_rate_ex'] = (s.passes - t.pass_rate * t.rest_plays) / (s.rest_plays - t.rest_plays)

# Attach the opponent's first play
o = t[['game_id', 'team', 'first_type', 'first_yds', 'total_yds']].rename(
    columns={'team': 'opp', 'first_type': 'opp_first_type', 'first_yds': 'opp_first_yds', 'total_yds': 'opp_total_yds'})
t = t.merge(o, on=['game_id', 'opp'])
t.to_csv('team_games.csv', index=False)
print(f'{len(t)} team-games, {t.game_id.nunique()} games')
