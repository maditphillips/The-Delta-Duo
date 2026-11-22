"""Step 9: does the late-game pass-defense fade follow Ravens coaches to other teams?

Usage: python3 coaching_tree.py DATA_DIR  (pbp_deep.parquet + team_games.csv)  ->  writes coaching_tree.csv, team_season_defense.csv

For every team-season 2020-2026, defense-only measures (rank of 32 within season, 1 = worst / most):
  def_2h_extra_pts  - points allowed in 2nd half minus 1st half
  pass_fade         - pass EPA allowed per dropback, 2nd half minus 1st half (all scores; bigger samples)
  q4_lead_pass_epa  - pass EPA allowed per dropback in Q4 while leading 1-16
  man_rate_q4_lead / cover0_q4_lead - coverage calls in Q4 with a lead (2020-2025 only)
  takeaways_2h      - takeaways per 2nd-half dropback (rank 1 = fewest)
Ravens-tree defenses outside Baltimore (coach list supplied by the user / public record):
  NYG 2022-23 Wink Martindale (DC), SEA 2024-26 Mike Macdonald (HC, calls defense),
  LAC 2024-25 Jesse Minter (DC, play caller), MIA 2024-25 Anthony Weaver (DC, not the play caller).
"""
import sys, os
import numpy as np
import pandas as pd

d = sys.argv[1]
out = os.path.dirname(os.path.abspath(__file__))
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 30)
p = pd.read_parquet(f'{d}/pbp_deep.parquet')
p = p[(p.qtr <= 4) & (p.qb_dropback == 1) & (p.qb_kneel == 0) & (p.qb_spike == 0) & p.epa.notna()].copy()
p['lead'] = -p.score_differential
p['takeaway'] = (p.interception == 1) | (p.fumble_lost == 1)
p['man'] = (p.defense_man_zone_type == 'MAN_COVERAGE').where(p.defense_man_zone_type.isin(['MAN_COVERAGE', 'ZONE_COVERAGE']))
p['c0'] = (p.defense_coverage_type == 'COVER_0').where(p.defense_coverage_type.notna())
k = ['season', 'defteam']
h1 = p[p.qtr <= 2].groupby(k).epa.mean().rename('pass_epa_1h')
h2 = p[p.qtr >= 3].groupby(k).agg(pass_epa_2h=('epa', 'mean'), takeaways_2h=('takeaway', 'mean'))
q4 = p[(p.qtr == 4) & p.lead.between(1, 16)].groupby(k).agg(q4_lead_dropbacks=('epa', 'size'), q4_lead_pass_epa=('epa', 'mean'),
                                                             man_rate_q4_lead=('man', 'mean'), cover0_q4_lead=('c0', 'mean'))
s = pd.concat([h1, h2, q4], axis=1).reset_index().rename(columns={'defteam': 'team'})
s['pass_fade'] = s.pass_epa_2h - s.pass_epa_1h
t = pd.read_csv(f'{out}/team_games.csv')
pts = t[t.season.between(2020, 2026)].groupby(['season', 'team'])[['h1_pa', 'h2_pa']].sum().reset_index()
pts['def_2h_extra_pts'] = pts.h2_pa - pts.h1_pa
s = s.merge(pts, on=['season', 'team'])
g = s.groupby('season')
for c in ['def_2h_extra_pts', 'pass_fade', 'q4_lead_pass_epa', 'man_rate_q4_lead', 'cover0_q4_lead']:
    s[c + '_rk'] = g[c].rank(ascending=False, method='min')
s['takeaways_2h_rk'] = g.takeaways_2h.rank(method='min')
s.round(3).to_csv(f'{out}/team_season_defense.csv', index=False)

TREE = [('BAL', y, 'Ravens (Martindale DC)') for y in (2020, 2021)] + \
       [('BAL', y, 'Ravens (Macdonald DC)') for y in (2022, 2023)] + \
       [('BAL', y, 'Ravens (Orr DC)') for y in (2024, 2025)] + [('BAL', 2026, 'Ravens (Minter HC, calls D)')] + \
       [('NYG', y, 'Giants (Martindale DC)') for y in (2022, 2023)] + \
       [('SEA', y, 'Seahawks (Macdonald HC)') for y in (2024, 2025, 2026)] + \
       [('LAC', y, 'Chargers (Minter DC)') for y in (2024, 2025)] + [('LAC', 2026, 'Chargers (after Minter)')] + \
       [('LAC', y, 'Chargers (before Minter)') for y in (2022, 2023)] + \
       [('MIA', y, 'Dolphins (Weaver DC, not play caller)') for y in (2024, 2025)]
tree = pd.DataFrame(TREE, columns=['team', 'season', 'staff']).merge(s, on=['team', 'season'], how='left')
cols = ['staff', 'season', 'def_2h_extra_pts', 'def_2h_extra_pts_rk', 'pass_epa_1h', 'pass_epa_2h', 'pass_fade', 'pass_fade_rk',
        'q4_lead_dropbacks', 'q4_lead_pass_epa', 'q4_lead_pass_epa_rk', 'man_rate_q4_lead', 'man_rate_q4_lead_rk',
        'cover0_q4_lead', 'cover0_q4_lead_rk', 'takeaways_2h_rk']
tree[cols].round(3).to_csv(f'{out}/coaching_tree.csv', index=False)
print(tree[cols].round(3).to_string(index=False))
print('\nLeague medians:', s[['def_2h_extra_pts', 'pass_fade', 'q4_lead_pass_epa', 'man_rate_q4_lead', 'cover0_q4_lead']].median().round(3).to_dict())
