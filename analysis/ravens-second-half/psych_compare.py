"""Step 13: blown leads and late-game fade -- teams with a dedicated sports psychologist vs teams without, vs the Ravens.

Usage: python3 psych_compare.py DATA_DIR  (pbp_slim.parquet, game_flags.csv, team_games.csv)  ->  writes psych_compare.csv,
       psych_compare_teams.csv

Groups (team-seasons, 2020-2026), from sports_psychologists.md -- only the most confident entries:
  HAS: Packers 2020-26 (Chris Carr, full-time Apr 2020), Lions 2021-26 (Michelle Garvin, Jun 2021),
       Bears 2022-26 (Mike Wiley Jr., Jul 2022), Bills 2023-26 (Desaree Festa, 2023 article),
       Chiefs 2022-26 (Shaun Tyrance, VP role covering performance psychology from May 2022; Tyler Bradstreet,
       VP of Performance Psychology, likely 2026), Titans 2026 (Charron Sumler, hired before 2026; single source).
       Their seasons before the hire are dropped (not counted in either group).
  NO (confirmed): Steelers (2022 Post-Gazette column; assumed for all seasons).
  NO (none found): Bengals, Browns, Texans, Colts, Raiders, Chargers, Cowboys, Patriots, Jets, Saints, 49ers, Broncos,
       Dolphins -- searched, nobody named. Not proof of absence.
  BAL: Ravens (confirmed none, 2026 Banner).
Left out as uncertain: Giants, Commanders, Rams, Bucs, Panthers, Falcons, Jaguars, Vikings, Cardinals,
Seahawks, Eagles.
"""
import sys, os
import numpy as np
import pandas as pd

d = sys.argv[1]
out = os.path.dirname(os.path.abspath(__file__))
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 30)
HAS = {'GB': 2020, 'DET': 2021, 'CHI': 2022, 'BUF': 2023, 'KC': 2022, 'TEN': 2026}
NO_CONF = ['PIT']
NO_FOUND = ['CIN', 'CLE', 'HOU', 'IND', 'LV', 'LAC', 'DAL', 'NE', 'NYJ', 'NO', 'SF', 'DEN', 'MIA']

f = pd.read_csv(f'{out}/game_flags.csv')
# Score after 3 quarters -> 4th-quarter leads
p = pd.read_parquet(f'{d}/pbp_slim.parquet', columns=['game_id', 'season', 'qtr', 'total_home_score', 'total_away_score'])
p = p[p.season.between(2020, 2026)]
q3 = p[p.qtr <= 3].groupby('game_id')[['total_home_score', 'total_away_score']].max()
q3['home_m3'] = q3.total_home_score - q3.total_away_score
f = f.merge(q3[['home_m3']].reset_index(), on='game_id', how='left')
home = f.game_id.str.split('_').str[-1] == f.team
f['m3'] = np.where(home, f.home_m3, -f.home_m3)
f['q4_diff'] = (f.pf - f.pa) - f.m3 - np.where(f.pf + f.pa > 0, 0, 0)
# regulation Q4 diff: final regulation margin minus Q3 margin (h1+h2 = regulation)
f['q4_diff'] = (f.h1_diff + f.h2_diff) - f.m3
f['led_q4'] = f.m3 > 0
f['blew_q4'] = f.led_q4 & ~f.won
f['led_q4_7'] = f.m3 >= 7
f['blew_q4_7'] = f.led_q4_7 & ~f.won
f['gap'] = f.h2_diff - f.h1_diff
f['def_extra_2h'] = f.h2_pa - f.h1_pa

def group(r):
    if r.team == 'BAL':
        return 'Ravens'
    if r.team in HAS:
        return 'Has psychologist' if r.season >= HAS[r.team] else None
    if r.team in NO_CONF:
        return 'No psychologist: Steelers (confirmed)'
    if r.team in NO_FOUND:
        return 'No psychologist: none found'
    return None
f['grp'] = f.apply(group, axis=1)
f['tm'] = f.team
g = f[f.grp.notna()].copy()
g2 = g.copy(); g2.loc[g2.grp.str.startswith('No psych'), 'grp'] = 'No psychologist: all (Steelers + none found)'
g = pd.concat([g, g2[g2.grp == 'No psychologist: all (Steelers + none found)']])

def summ(x):
    return pd.Series({
        'teams': x.tm.nunique(), 'team_seasons': x[['tm', 'season']].drop_duplicates().shape[0], 'games': len(x),
        'win_pct': x.won.mean(),
        'h1_diff_pg': x.h1_diff.mean(), 'h2_diff_pg': x.h2_diff.mean(), 'gap_2h_minus_1h_pg': x.gap.mean(),
        'q4_diff_pg': x.q4_diff.mean(), 'def_extra_2h_pts_pg': x.def_extra_2h.mean(),
        'led_by_10_games': x.led10.sum(), 'blew_10_rate': x.blew10.sum() / x.led10.sum(),
        'wp85_games': x.wp85.sum(), 'lost_after_85pct_rate': x.wp85_lost.sum() / x.wp85.sum(),
        'led_at_half': x.led_half.sum(), 'led_half_lost_2h_rate': x.half_fade.sum() / x.led_half.sum(),
        'led_half_lost_game_rate': x.led_half_lost.sum() / x.led_half.sum(),
        'led_entering_q4': x.led_q4.sum(), 'blew_q4_lead_rate': x.blew_q4.sum() / x.led_q4.sum(),
        'led_by_7_entering_q4': x.led_q4_7.sum(), 'blew_q4_7plus_rate': x.blew_q4_7.sum() / x.led_q4_7.sum()})
order = ['Ravens', 'Has psychologist', 'No psychologist: all (Steelers + none found)']
res = g.groupby('grp').apply(summ).T[order]
lg = f[f.grp != 'Ravens']
res['NFL (all other teams)'] = summ(f[f.team != 'BAL'])
res.round(3).to_csv(f'{out}/psych_compare.csv')
print(res.round(3).to_string())

# Per-team view so one team can't hide behind a group average
pt = f[f.grp.notna()].groupby(['grp', 'team']).apply(summ)[['team_seasons', 'games', 'gap_2h_minus_1h_pg', 'q4_diff_pg',
                                                             'def_extra_2h_pts_pg', 'blew_10_rate', 'lost_after_85pct_rate',
                                                             'blew_q4_lead_rate']]
pt.round(3).to_csv(f'{out}/psych_compare_teams.csv')
print('\n=== By team ==='); print(pt.round(2).to_string())

# Where would the Ravens rank among the 18 comparison teams + BAL?
allt = f[f.grp.notna()].groupby('team').apply(summ)
for c in ['gap_2h_minus_1h_pg', 'q4_diff_pg', 'def_extra_2h_pts_pg', 'blew_10_rate', 'lost_after_85pct_rate', 'blew_q4_lead_rate']:
    asc = c in ['gap_2h_minus_1h_pg', 'q4_diff_pg']
    print(f'BAL rank of {len(allt)} on {c} (1 = worst):', int(allt[c].rank(ascending=asc, method="min")['BAL']))

