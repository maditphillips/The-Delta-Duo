"""Step 6: the Ravens offense with a 2nd-half lead -- how run-heavy, is it a choice, and does it work?

Usage: python3 deep_offense.py DATA_DIR  (pbp_deep.parquet, see deep_defense.py)  ->  writes deep_offense.csv,
       deep_offense_by_season.csv, deep_offense_box.csv

Plays the team runs while up 1-16. Groups: BAL Q4 lead, BAL Q3 lead, BAL 1H lead, NFL Q4 lead.
"""
import sys, os
import numpy as np
import pandas as pd

d = sys.argv[1]
out = os.path.dirname(os.path.abspath(__file__))
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 40)
p = pd.read_parquet(f'{d}/pbp_deep.parquet')
p = p[(p.qtr <= 4) & p.play_type.isin(['pass', 'run']) & (p.qb_kneel == 0) & (p.qb_spike == 0)].reset_index(drop=True)
p = p[p.score_differential.between(1, 16)].copy()
p['period'] = np.select([p.qtr <= 2, p.qtr == 3], ['1H', 'Q3'], 'Q4')
p['grp'] = np.where(p.posteam == 'BAL', 'BAL', 'NFL')
p['mins_left'] = p.game_seconds_remaining / 60

def personnel(s, pos):
    if not isinstance(s, str) or not s:
        return np.nan
    for part in s.split(','):
        k, q = part.split()
        if q == pos:
            return int(k)
    return 0
p['te'] = p.offense_personnel.map(lambda s: personnel(s, 'TE'))
p['ol'] = p.offense_personnel.map(lambda s: personnel(s, 'OL'))
p['wr'] = p.offense_personnel.map(lambda s: personnel(s, 'WR'))
p['heavy'] = ((p.te >= 2) | (p.ol >= 6)).where(p.te.notna())
p['three_wr'] = (p.wr >= 3).where(p.wr.notna())
p['under_center'] = 1 - p.shotgun
p['box'] = p.defenders_in_box.fillna(p.n_defense_box)
p['stacked_box'] = (p.box >= 8).where(p.box.notna())
p['early'] = p.down.isin([1, 2])
p['early_pass'] = np.where(p.early, p['pass'], np.nan)
p['first_down_pass'] = np.where(p.down == 1, p['pass'], np.nan)
p['third'] = p.down == 3
p['third_dist'] = np.where(p.third, p.ydstogo, np.nan)
p['third_long'] = np.where(p.third, p.ydstogo >= 7, np.nan)
p['third_conv'] = np.where(p.third, p.first_down.fillna(0), np.nan)
p['pa'] = np.where(p['pass'] == 1, p.is_play_action.astype(float), np.nan)
p['motion'] = p.is_motion.astype(float)
p['qb_designed_run'] = np.where(p.rush == 1, (p.rusher_player_name == p.passer_player_name) | p.rusher_player_name.isin(['L.Jackson', 'T.Huntley']), np.nan)
p['run_epa'] = np.where(p.rush == 1, p.epa, np.nan)
p['pass_epa'] = np.where(p['pass'] == 1, p.epa, np.nan)
p['early_run_epa'] = np.where(p.early & (p.rush == 1), p.epa, np.nan)
p['early_pass_epa'] = np.where(p.early & (p['pass'] == 1), p.epa, np.nan)
p['run_success'] = np.where(p.rush == 1, p.success, np.nan)
p['stuff'] = np.where(p.rush == 1, p.yards_gained <= 0, np.nan)

M = {'plays': ('epa', 'count'), 'pass_rate': ('pass', 'mean'), 'pass_over_expected': ('pass_oe', 'mean'),
     'expected_pass_rate': ('xpass', 'mean'), 'first_down_pass_rate': ('first_down_pass', 'mean'),
     'early_down_pass_rate': ('early_pass', 'mean'),
     'epa_per_play': ('epa', 'mean'), 'run_epa': ('run_epa', 'mean'), 'pass_epa': ('pass_epa', 'mean'),
     'early_run_epa': ('early_run_epa', 'mean'), 'early_pass_epa': ('early_pass_epa', 'mean'),
     'run_success': ('run_success', 'mean'), 'run_stuffed_rate': ('stuff', 'mean'),
     'third_avg_distance': ('third_dist', 'mean'), 'third_and_7plus_share': ('third_long', 'mean'), 'third_conv': ('third_conv', 'mean'),
     'heavy_personnel': ('heavy', 'mean'), 'three_wr_personnel': ('three_wr', 'mean'), 'under_center': ('under_center', 'mean'),
     'avg_box': ('box', 'mean'), 'stacked_box_8plus': ('stacked_box', 'mean'), 'play_action_rate': ('pa', 'mean'),
     'motion_rate': ('motion', 'mean'), 'qb_designed_run_share': ('qb_designed_run', 'mean')}
agg = lambda x: x.agg(**{k: pd.NamedAgg(*v) for k, v in M.items()})
one = lambda x: agg(x.assign(k=1).groupby('k')).iloc[0]
G = {'BAL 1H lead': p[(p.grp == 'BAL') & (p.period == '1H')], 'BAL Q3 lead': p[(p.grp == 'BAL') & (p.period == 'Q3')],
     'BAL Q4 lead': p[(p.grp == 'BAL') & (p.period == 'Q4')], 'NFL Q4 lead': p[(p.grp == 'NFL') & (p.period == 'Q4')],
     'BAL Q4 lead, >5 min left': p[(p.grp == 'BAL') & (p.period == 'Q4') & (p.mins_left > 5)],
     'NFL Q4 lead, >5 min left': p[(p.grp == 'NFL') & (p.period == 'Q4') & (p.mins_left > 5)]}
res = pd.DataFrame({k: one(v) for k, v in G.items()})
rk = agg(p[p.period == 'Q4'].groupby('posteam')).rank(ascending=False, method='min')
res['BAL rank of 32 in Q4 (1=highest)'] = rk.loc['BAL']
res.round(3).to_csv(f'{out}/deep_offense.csv')
print('=== Offense leading 1-16 ==='); print(res.round(3).to_string())

# By season: pass over expected in 2nd half with a lead, and whether passing out-performed running
h2 = p[p.period != '1H']
rows = []
for s, g in h2.groupby('season'):
    t = agg(g.groupby('posteam'))
    r = t.rank(ascending=False, method='min')
    b = t.loc['BAL']
    rows.append({'season': s, 'plays': b.plays, 'pass_rate': b.pass_rate, 'pass_rate_rank': r.loc['BAL', 'pass_rate'],
                 'pass_over_expected': b.pass_over_expected, 'proe_rank': r.loc['BAL', 'pass_over_expected'],
                 'early_pass_epa': b.early_pass_epa, 'early_run_epa': b.early_run_epa,
                 'nfl_early_pass_epa': g[g.grp == 'NFL'].early_pass_epa.mean(), 'nfl_early_run_epa': g[g.grp == 'NFL'].early_run_epa.mean(),
                 'stacked_box_8plus': b.stacked_box_8plus, 'third_and_7plus_share': b.third_and_7plus_share})
bs = pd.DataFrame(rows).set_index('season')
bs.round(3).to_csv(f'{out}/deep_offense_by_season.csv')
print('\n=== BAL 2nd half with a lead, by season (rank 1 = highest of 32) ==='); print(bs.round(3).to_string())

# Run results by box count, Q3+Q4 lead
r = h2[(h2.rush == 1) & h2.box.notna()].copy()
r['box_bin'] = pd.cut(r.box, [0, 6, 7, 11], labels=['6 or fewer', '7', '8+'])
bx = r.groupby(['box_bin', 'grp'], observed=True).agg(runs=('epa', 'size'), epa=('epa', 'mean'), success=('success', 'mean'),
                                                      ypc=('yards_gained', 'mean')).unstack()
bx.round(3).to_csv(f'{out}/deep_offense_box.csv')
print('\n=== Runs vs box count, 2nd half with a lead ==='); print(bx.round(3).to_string())
