"""Ravens first-half vs second-half point differential by season, 1999-2026.

Usage: python3 halves.py DATA_DIR  (DATA_DIR holds pbp_slim.parquet, built from the
       nflverse play_by_play_YYYY.parquet files)  ->  writes team_games.csv, ravens_by_season.csv here

Second half = 3rd + 4th quarter only (overtime left out). Regular season + playoffs.
"""
import sys, os
import pandas as pd

d = sys.argv[1]
out = os.path.dirname(os.path.abspath(__file__))
p = pd.read_parquet(f'{d}/pbp_slim.parquet')

def score_at(qmax):
    s = p[p.qtr <= qmax].groupby('game_id')[['total_home_score', 'total_away_score']].max()
    return s.rename(columns=lambda c: c.replace('total_', '') + f'_q{qmax}')

g = p.groupby('game_id').agg(season=('season', 'first'), season_type=('season_type', 'first'),
                             week=('week', 'first'), home=('home_team', 'first'), away=('away_team', 'first'),
                             home_final=('home_score', 'first'), away_final=('away_score', 'first'),
                             home_coach=('home_coach', 'first'), away_coach=('away_coach', 'first'))
g = g.join(score_at(2)).join(score_at(4)).fillna(0).reset_index()
rows = []
for s, o in (('home', 'away'), ('away', 'home')):
    rows.append(pd.DataFrame({
        'game_id': g.game_id, 'season': g.season, 'season_type': g.season_type, 'week': g.week,
        'team': g[s], 'opp': g[o], 'coach': g[f'{s}_coach'],
        'h1_pf': g[f'{s}_score_q2'], 'h1_pa': g[f'{o}_score_q2'],
        'h2_pf': g[f'{s}_score_q4'] - g[f'{s}_score_q2'], 'h2_pa': g[f'{o}_score_q4'] - g[f'{o}_score_q2'],
        'pf': g[f'{s}_final'], 'pa': g[f'{o}_final']}))
t = pd.concat(rows)
t['h1_diff'] = t.h1_pf - t.h1_pa
t['h2_diff'] = t.h2_pf - t.h2_pa
t = t.sort_values(['season', 'week', 'team'])
t.to_csv(f'{out}/team_games.csv', index=False)

# League rank of each team's 2nd-half diff that season (1 = best)
by = t.groupby(['season', 'team']).agg(games=('game_id', 'size'), h1_diff=('h1_diff', 'sum'),
                                       h2_diff=('h2_diff', 'sum'), coach=('coach', lambda c: c.mode()[0])).reset_index()
by['h1_rank'] = by.groupby('season').h1_diff.rank(ascending=False, method='min').astype(int)
by['h2_rank'] = by.groupby('season').h2_diff.rank(ascending=False, method='min').astype(int)
by['gap'] = by.h2_diff - by.h1_diff
by['gap_rank'] = by.groupby('season').gap.rank(method='min').astype(int)  # 1 = biggest drop-off
bal = by[by.team == 'BAL'].copy()
bal['pattern'] = (bal.h1_diff > 0) & (bal.h2_diff < 0)
bal.to_csv(f'{out}/ravens_by_season.csv', index=False)
pd.set_option('display.width', 200)
print(bal.to_string(index=False))
print('\nSeasons with + 1st half and - 2nd half:', bal[bal.pattern].season.tolist())

# How often does this pattern happen league-wide?
by['pattern'] = (by.h1_diff > 0) & (by.h2_diff < 0)
print(f'\nLeague-wide, {by.pattern.mean():.1%} of team-seasons fit the pattern.')
since = by[by.season >= 2018]
print('Most pattern seasons since 2018:')
print(since.groupby('team').pattern.sum().sort_values(ascending=False).head(8).to_string())
print('Total 2nd-half minus 1st-half gap since 2018 (most negative = biggest drop-off):')
print(since.groupby('team')[['h1_diff', 'h2_diff', 'gap']].sum().sort_values('gap').head(8).to_string())
