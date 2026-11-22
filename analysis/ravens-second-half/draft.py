"""Step 12: are the Ravens good at drafting except pass rushers? Value over expected by position, 2010-2025 drafts.

Usage: python3 draft.py DATA_DIR  (nflverse draft_picks.csv + players.csv)  ->  writes draft_value.csv, draft_ravens_edge.csv

Value = w_av (Pro Football Reference weighted career Approximate Value, all teams). Expected = average w_av of all
picks within 6 slots of the same pick in the same draft year, so older drafts and recent drafts are compared fairly.
Position group uses the player's PFF position from nflverse players.csv (ED = edge, DI = interior line), so edge rushers
listed as "LB" at the draft land in EDGE; falls back to the draft position when missing.
GM eras: Ozzie Newsome through the 2018 draft, Eric DeCosta from 2019.
"""
import sys, os
import numpy as np
import pandas as pd

d = sys.argv[1]
out = os.path.dirname(os.path.abspath(__file__))
pd.set_option('display.width', 220)
dp = pd.read_csv(f'{d}/draft_picks.csv')
pl = pd.read_csv(f'{d}/players.csv', usecols=['gsis_id', 'pff_position'], low_memory=False).rename(columns={'pff_position': 'pos_now'})
dp = dp[dp.season.between(2010, 2025)].merge(pl.drop_duplicates('gsis_id'), on='gsis_id', how='left')
dp['pos'] = dp.pos_now.fillna(dp.position)
G = {'EDGE': ['ED', 'DE', 'OLB', 'EDGE'], 'IDL': ['DI', 'DT', 'NT', 'DL'], 'LB': ['LB', 'ILB', 'MLB'],
     'CB': ['CB'], 'S': ['S', 'SAF', 'FS', 'SS'], 'DB (unspecified)': ['DB'],
     'QB': ['QB'], 'RB': ['RB', 'FB', 'HB'], 'WR': ['WR'], 'TE': ['TE'], 'OL': ['T', 'G', 'C', 'OL', 'OT', 'OG', 'IOL']}
lookup = {p: g for g, ps in G.items() for p in ps}
dp['grp'] = dp.pos.map(lookup).fillna('ST/other')
dp['w_av'] = dp.w_av.fillna(0)
dp = dp.sort_values(['season', 'pick'])
dp['exp_av'] = dp.groupby('season').apply(
    lambda g: pd.Series([g.loc[(g.pick - pk).abs() <= 6, 'w_av'].mean() for pk in g.pick], index=g.index)).reset_index(level=0, drop=True)
dp['over_exp'] = dp.w_av - dp.exp_av
dp['hit'] = dp.w_av > dp.exp_av
dp['era'] = np.where(dp.season >= 2019, 'DeCosta 2019-25', 'Newsome 2010-18')
dp['early'] = dp['round'] <= 3

def summarize(x):
    return pd.Series({'picks': len(x), 'early_picks': x.early.sum(), 'av_over_exp_per_pick': x.over_exp.mean(),
                      'av_over_exp_early': x[x.early].over_exp.mean(), 'hit_rate': x.hit.mean()})
bal = dp[dp.team == 'BAL']
rows = []
for era in ['Newsome 2010-18', 'DeCosta 2019-25']:
    for grp, g in bal[bal.era == era].groupby('grp'):
        r = summarize(g); r['era'] = era; r['grp'] = grp; rows.append(r)
    r = summarize(bal[bal.era == era]); r['era'] = era; r['grp'] = 'ALL'; rows.append(r)
t = pd.DataFrame(rows).set_index(['era', 'grp'])
# League: each team's value over expected on EDGE picks, DeCosta era window, rank
lg = dp[dp.season >= 2019].groupby(['team']).apply(lambda g: pd.Series({
    'all_over_exp': g.over_exp.mean(), 'edge_over_exp': g[g.grp == 'EDGE'].over_exp.mean(), 'edge_picks': (g.grp == 'EDGE').sum(),
    'edge_early_picks': ((g.grp == 'EDGE') & g.early).sum()}))
lg['all_rank'] = lg.all_over_exp.rank(ascending=False, method='min')
lg['edge_rank'] = lg.edge_over_exp.rank(ascending=False, method='min')
t.round(2).to_csv(f'{out}/draft_value.csv')
print('=== Ravens draft value over expected (AV) by position group ==='); print(t.round(2).to_string())
print('\n2019-2025 drafts, all 32 teams: BAL', lg.loc['BAL'].round(2).to_dict())
print('Teams with most EDGE picks 2019-25:', lg.edge_picks.sort_values(ascending=False).head(5).to_dict())
e = bal[bal.grp == 'EDGE'][['season', 'round', 'pick', 'pfr_player_name', 'pos', 'w_av', 'exp_av', 'over_exp', 'def_sacks', 'games']]
e.round(1).to_csv(f'{out}/draft_ravens_edge.csv', index=False)
print('\n=== Ravens EDGE picks 2010-2025 ==='); print(e.round(1).to_string(index=False))

c = bal[bal.grp.isin(['CB', 'DB (unspecified)'])][['season', 'round', 'pick', 'pfr_player_name', 'pos', 'w_av', 'exp_av', 'over_exp', 'games']]
c.round(1).to_csv(f'{out}/draft_ravens_cb.csv', index=False)
print('\n=== Ravens CB picks 2010-2025 ==='); print(c.round(1).to_string(index=False))
lgc = dp[dp.season >= 2019].groupby('team').apply(lambda g: g[g.grp == 'CB'].over_exp.mean())
print('CB over-expected rank 2019-25 (1 = best):', int(lgc.rank(ascending=False, method='min')['BAL']))
