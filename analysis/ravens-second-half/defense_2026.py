"""Step 7: the 2026 defense (first head-coach change in the span) vs the Ravens' 2020-2025 defense and the 2026 NFL.

Usage: python3 defense_2026.py DATA_DIR  (pbp_deep.parquet)  ->  writes defense_2026.csv, defense_2026_games.csv

2026 has no nflverse participation data yet (no coverage, man/zone, pressure or time to throw).
FTN charting covers 2022-2026, so blitz, rushers, box, contested/catchable balls are comparable for 2022-2026.
Because 2026 has only 34 Q4 dropbacks with a lead, we widen the lens to all 2nd-half dropbacks and to
2nd-half dropbacks with any lead.
"""
import sys, os
import numpy as np
import pandas as pd

d = sys.argv[1]
out = os.path.dirname(os.path.abspath(__file__))
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 40)
p = pd.read_parquet(f'{d}/pbp_deep.parquet')
p = p[(p.qtr <= 4) & p.play_type.isin(['pass', 'run']) & (p.qb_kneel == 0) & (p.qb_spike == 0)].copy()
p['half'] = np.where(p.qtr <= 2, '1H', '2H')
p['lead'] = -p.score_differential
p['explosive'] = ((p['pass'] == 1) & (p.yards_gained >= 20)) | ((p.rush == 1) & (p.yards_gained >= 10))
p['first_down'] = p.first_down.fillna(0)
p['third_conv'] = np.where(p.down == 3, p.first_down, np.nan)
p['blitz'] = (p.n_blitzers > 0).where(p.n_blitzers.notna())
p['rush4'] = (p.n_pass_rushers <= 4).where(p.n_pass_rushers.notna())
p['contested'] = p.is_contested_ball.astype(float)
p['catchable'] = p.is_catchable_ball.astype(float)
p['screen'] = p.is_screen_pass.astype(float)
p['takeaway'] = (p.interception == 1) | (p.fumble_lost == 1)
p['air_comp'] = np.where(p.complete_pass == 1, p.air_yards, np.nan)
p['yac'] = np.where(p.complete_pass == 1, p.yards_after_catch, np.nan)
p['era'] = np.select([p.season == 2026, p.season >= 2022], ['2026', '2022-25'], '2020-21')
dbk = p[p.qb_dropback == 1]
run = p[p.rush == 1]

PASS = {'dropbacks': ('epa', 'count'), 'pass_epa_allowed': ('epa', 'mean'), 'success_allowed': ('success', 'mean'),
        'explosive_pass_20plus': ('explosive', 'mean'), 'cpoe_allowed': ('cpoe', 'mean'), 'first_down_rate': ('first_down', 'mean'),
        'third_conv': ('third_conv', 'mean'), 'air_yds_per_catch': ('air_comp', 'mean'), 'yac_per_catch': ('yac', 'mean'),
        'sack_rate': ('sack', 'mean'), 'takeaway_rate': ('takeaway', 'mean'), 'blitz_rate': ('blitz', 'mean'),
        'rush4_or_less': ('rush4', 'mean'), 'contested_rate': ('contested', 'mean'), 'screen_share': ('screen', 'mean')}
RUN = {'runs': ('epa', 'count'), 'run_epa_allowed': ('epa', 'mean'), 'run_success_allowed': ('success', 'mean'),
       'run_10plus_allowed': ('explosive', 'mean')}
agg = lambda x, M: x.agg(**{k: pd.NamedAgg(*v) for k, v in M.items()})
one = lambda x, M: agg(x.assign(k=1).groupby('k'), M).iloc[0]

def block(sel, name):
    """BAL by era vs 2026 NFL for one situation; plus BAL 2026 rank of 32."""
    a, r = dbk[sel(dbk)], run[sel(run)]
    cols = {}
    for era in ['2020-21', '2022-25', '2026']:
        cols[f'BAL {era}'] = pd.concat([one(a[(a.defteam == 'BAL') & (a.era == era)], PASS), one(r[(r.defteam == 'BAL') & (r.era == era)], RUN)])
    cols['NFL 2026'] = pd.concat([one(a[(a.defteam != 'BAL') & (a.season == 2026)], PASS), one(r[(r.defteam != 'BAL') & (r.season == 2026)], RUN)])
    rk = pd.concat([agg(a[a.season == 2026].groupby('defteam'), PASS), agg(r[r.season == 2026].groupby('defteam'), RUN)], axis=1)
    cols['BAL 2026 rank (1=highest)'] = rk.rank(ascending=False, method='min').loc['BAL']
    t = pd.DataFrame(cols)
    t.columns = pd.MultiIndex.from_product([[name], t.columns])
    return t

res = pd.concat([block(lambda x: x.half == '1H', '1st half, all scores'),
                 block(lambda x: x.half == '2H', '2nd half, all scores'),
                 block(lambda x: (x.half == '2H') & (x.lead >= 1), '2nd half, leading'),
                 block(lambda x: (x.qtr == 4) & x.lead.between(1, 16), 'Q4, leading 1-16')], axis=1)
res.round(3).to_csv(f'{out}/defense_2026.csv')
for name in res.columns.levels[0]:
    print(f'\n=== {name} ===')
    print(res[name].round(3).to_string())

# 2026 game by game: where did the 2nd-half points come from?
g = p[(p.defteam == 'BAL') & (p.season == 2026) & (p.half == '2H')]
games = g.groupby(['week', 'posteam']).agg(plays=('epa', 'size'), dropbacks=('qb_dropback', 'sum'),
                                          pass_epa=('epa', lambda e: e[g.loc[e.index, 'qb_dropback'] == 1].mean()),
                                          run_epa=('epa', lambda e: e[g.loc[e.index, 'rush'] == 1].mean()),
                                          explosive_plays=('explosive', 'sum'), blitz_rate=('blitz', 'mean'),
                                          takeaways=('takeaway', 'sum')).reset_index()
t = pd.read_csv(f'{out}/team_games.csv')
t = t[(t.team == 'BAL') & (t.season == 2026)][['week', 'h1_pf', 'h1_pa', 'h2_pf', 'h2_pa']]
games = games.merge(t, on='week')
games.round(3).to_csv(f'{out}/defense_2026_games.csv', index=False)
print('\n=== 2026, Ravens defense in 2nd halves, by game ==='); print(games.round(2).to_string(index=False))
