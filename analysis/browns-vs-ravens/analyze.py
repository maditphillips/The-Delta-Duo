"""Do the Browns beat the Ravens more than they should? 2016-2025 regular seasons.

Usage: python3 analyze.py DATA_DIR   (DATA_DIR holds nflverse games.csv and stats_YYYY.csv,
       the stats_player_week_YYYY.csv release files)  ->  writes games.csv, qb.csv here

Part 1: expected Browns wins vs BAL from (a) a league-wide logistic model of
win chance by season-record gap + home field, and (b) the Vegas moneyline.
Records leave out the game being judged. Ties count as half a win.
Part 2: Browns starting QB fantasy points vs BAL against two baselines, since
nflverse has no projections: his own average in his other games that season, and
what BAL allowed to other starting QBs that season.
"""
import sys
import numpy as np
import pandas as pd

d = sys.argv[1]
SEASONS = range(2016, 2026)
g = pd.read_csv(f'{d}/games.csv')
g = g[g.season.isin(SEASONS) & (g.game_type == 'REG') & g.result.notna()].copy()

# One row per team per game; win = 1, tie = .5
t = pd.concat([
    pd.DataFrame({'game_id': g.game_id, 'season': g.season, 'team': g[s + '_team'],
                  'opp': g[o + '_team'], 'home': s == 'home', 'qb_id': g[s + '_qb_id'],
                  'qb': g[s + '_qb_name'], 'ml': g[s + '_moneyline'], 'opp_ml': g[o + '_moneyline'],
                  'pf': g[s + '_score'], 'pa': g[o + '_score']})
    for s, o in (('home', 'away'), ('away', 'home'))
])
t['win'] = np.sign(t.pf - t.pa) / 2 + .5
rec = t.groupby(['season', 'team']).agg(w=('win', 'sum'), n=('win', 'size')).reset_index()
t = t.merge(rec, on=['season', 'team'])
t = t.merge(rec.rename(columns={'team': 'opp', 'w': 'ow', 'n': 'on'}), on=['season', 'opp'])
t['pct'] = (t.w - t.win) / (t.n - 1)          # record outside this game
t['opct'] = (t.ow - (1 - t.win)) / (t.on - 1)
t['gap'] = t.pct - t.opct

# Logistic fit: win ~ gap + home, on all games league-wide (Newton's method)
X = np.column_stack([np.ones(len(t)), t.gap, t.home * 2 - 1.0])
y = t.win.values
b = np.zeros(3)
for _ in range(25):
    p = 1 / (1 + np.exp(-X @ b))
    b += np.linalg.solve(X.T @ (X * (p * (1 - p))[:, None]), X.T @ (y - p))
t['p_record'] = 1 / (1 + np.exp(-X @ b))

def implied(ml):
    return np.where(ml < 0, -ml / (-ml + 100), 100 / (ml + 100))
a, o = implied(t.ml), implied(t.opp_ml)
t['p_vegas'] = a / (a + o)                     # vig removed

cle = t[(t.team == 'CLE') & (t.opp == 'BAL')].sort_values('game_id').copy()
cle['worse'] = cle.pct < cle.opct
cols = ['game_id', 'qb', 'pf', 'pa', 'win', 'pct', 'opct', 'worse', 'p_record', 'p_vegas']
cle[cols].round(3).to_csv('games.csv', index=False)
print(cle[cols].round(2).to_string(index=False))

rng = np.random.default_rng(0)
def report(df, label):
    print(f'\n== {label}: {len(df)} games, Browns won {df.win.sum():g}')
    for c in ('p_record', 'p_vegas'):
        sims = (rng.random((200_000, len(df))) < df[c].values).sum(1)
        print(f'  {c:9s} expected {df[c].sum():5.2f} wins | '
              f'chance of {df.win.sum():g}+ by luck: {(sims >= df.win.sum()).mean():.1%}')
report(cle, 'All CLE vs BAL')
report(cle[cle.worse], 'CLE had worse record')

# League baseline: how often does the worse-record team win, overall and in division games?
dv = set(g[g.div_game == 1].game_id)
lw = t[t.gap < 0]
lw_cle = lw[(lw.team == 'CLE') & (lw.opp == 'BAL')]
print(f'\nWorse-record team win rate, league: {lw.win.mean():.1%} (n={len(lw)}), '
      f'division games: {lw[lw.game_id.isin(dv)].win.mean():.1%}, '
      f'CLE vs BAL: {lw_cle.win.mean():.1%} (n={len(lw_cle)})')
print(f'Average record gap in those CLE games: {lw_cle.gap.mean():+.3f} '
      f'vs league worse-team average {lw.gap.mean():+.3f}')

# ---- Part 2: fantasy points (standard nflverse fantasy_points and PPR)
s = pd.concat([pd.read_csv(f'{d}/stats_{y}.csv', low_memory=False) for y in SEASONS])
s = s[(s.season_type == 'REG') & (s.position == 'QB')].copy()
s = s.merge(t[['game_id', 'team', 'opp', 'qb_id']], on=['game_id', 'team'])
s = s[s.player_id == s.qb_id].copy()           # starting QBs only
s['vs_bal'] = s.opp == 'BAL'

rows = []
for r in s[(s.team == 'CLE') & s.vs_bal].itertuples():
    own = s[(s.player_id == r.player_id) & (s.season == r.season) & ~s.vs_bal]
    bal = s[(s.season == r.season) & (s.opp == 'BAL') & (s.team != 'CLE')]
    rows.append({'game_id': r.game_id, 'qb': r.player_display_name, 'fpts': r.fantasy_points,
                 'own_avg': own.fantasy_points.mean(), 'own_n': len(own),
                 'bal_allowed': bal.fantasy_points.mean(),
                 'league_qb_avg': s[s.season == r.season].fantasy_points.mean()})
q = pd.DataFrame(rows)
# Expected = QB's own level scaled by how stingy BAL was relative to league
q['expected'] = np.where(q.own_n >= 3, q.own_avg * q.bal_allowed / q.league_qb_avg, np.nan)
q['diff'] = q.fpts - q.expected
q.round(2).to_csv('qb.csv', index=False)
print('\n' + q.round(1).to_string(index=False))
ok = q.dropna()
print(f'\nQB games with 3+ other starts that season: {len(ok)}')
print(f'  actual {ok.fpts.mean():.1f} | own avg {ok.own_avg.mean():.1f} | '
      f'BAL allowed others {ok.bal_allowed.mean():.1f} | adjusted expected {ok.expected.mean():.1f}')
print(f'  beat adjusted expectation in {(ok["diff"] > 0).sum()} of {len(ok)}; '
      f'mean diff {ok["diff"].mean():+.1f}, sd {ok["diff"].std():.1f}, '
      f't = {ok["diff"].mean() / (ok["diff"].std() / np.sqrt(len(ok))):.2f}')

# Same comparison for every starting QB vs every opponent, to see what's normal
own = s.groupby(['player_id', 'season']).fantasy_points.agg(['sum', 'size']).reset_index()
s = s.merge(own, on=['player_id', 'season'])
allow = s.groupby(['season', 'opp']).fantasy_points.agg(['sum', 'size']).reset_index()
s = s.merge(allow, on=['season', 'opp'], suffixes=('', '_d'))
lg = s.groupby('season').fantasy_points.transform('mean')
s = s[s['size'] >= 4]
s['exp'] = ((s['sum'] - s.fantasy_points) / (s['size'] - 1)) * \
           ((s.sum_d - s.fantasy_points) / (s.size_d - 1)) / lg
print(f'  league-wide mean diff for all starting QBs: {(s.fantasy_points - s.exp).mean():+.1f}')
