"""Step 5: 4th-quarter pass defense with a 1-16 point lead -- what is the defense calling?

Usage: python3 deep_defense.py DATA_DIR  (DATA_DIR holds pbp_deep.parquet: nflverse pbp 2020-2026 joined to
       pbp_participation 2020-2025 and ftn_charting 2022-2026)  ->  writes deep_defense.csv, deep_defense_coverage.csv,
       deep_defense_by_season.csv, deep_defense_starters.csv

Groups (opponent dropbacks): BAL Q4 lead, BAL 1H lead (same defense, earlier), NFL Q4 lead (other 31 teams).
"""
import sys, os
import numpy as np
import pandas as pd

d = sys.argv[1]
out = os.path.dirname(os.path.abspath(__file__))
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 40)
p = pd.read_parquet(f'{d}/pbp_deep.parquet')
p = p[(p.qtr <= 4) & p.play_type.isin(['pass', 'run']) & (p.qb_kneel == 0) & (p.qb_spike == 0)].reset_index(drop=True)
p['lead'] = -p.score_differential                      # defense's lead
p['period'] = np.select([p.qtr <= 2, p.qtr == 3], ['1H', 'Q3'], 'Q4')
p['grp'] = np.where(p.defteam == 'BAL', 'BAL', 'NFL')
p['mins_left'] = p.game_seconds_remaining / 60

db = p[(p.qb_dropback == 1) & p.lead.between(1, 16)].copy()
db['att'] = (db.complete_pass == 1) | (db.incomplete_pass == 1) | (db.interception == 1)
db['short'] = db.air_yards < 10
db['deep'] = db.air_yards >= 15
db['middle'] = db.pass_location == 'middle'
db['pressure'] = db.was_pressure.astype(float)
db['rushers'] = db.number_of_pass_rushers.fillna(db.n_pass_rushers)
db['four_or_less'] = db.rushers <= 4
db['blitz'] = (db.n_blitzers > 0).where(db.n_blitzers.notna())
db['man'] = (db.defense_man_zone_type == 'MAN_COVERAGE').where(db.defense_man_zone_type.isin(['MAN_COVERAGE', 'ZONE_COVERAGE']))
db['cov'] = db.defense_coverage_type
def count_dbs(s):
    """Defensive backs on the field from either personnel format ('2 DL, 4 LB, 5 DB' or '3 CB, 1 FS, 1 SS, ...')."""
    if not isinstance(s, str) or not s:
        return np.nan
    n = 0
    for part in s.split(','):
        k, pos = part.split()
        if pos in ('DB', 'CB', 'FS', 'SS', 'S'):
            n += int(k)
    return n
db['n_db'] = db.defense_personnel.map(count_dbs)
db['dime_plus'] = (db.n_db >= 6).where(db.n_db.notna())
db['first_down'] = db.first_down.fillna(0)
db['explosive'] = db.yards_gained >= 20
db['third'] = db.down == 3
db['third_conv'] = np.where(db.third, db.first_down, np.nan)
db['third_dist'] = np.where(db.third, db.ydstogo, np.nan)
db['yac'] = np.where(db.complete_pass == 1, db.yards_after_catch, np.nan)
db['air_comp'] = np.where(db.complete_pass == 1, db.air_yards, np.nan)
db['contested'] = db.is_contested_ball.astype(float)
db['catchable'] = db.is_catchable_ball.astype(float)

M = {'dropbacks': ('epa', 'count'), 'epa_per_dropback': ('epa', 'mean'), 'success_allowed': ('success', 'mean'),
     'comp_pct_over_expected': ('cpoe', 'mean'), 'first_down_rate': ('first_down', 'mean'),
     'explosive_20plus': ('explosive', 'mean'), 'third_conv': ('third_conv', 'mean'), 'third_avg_distance': ('third_dist', 'mean'),
     'avg_air_yards': ('air_yards', 'mean'), 'short_throw_share': ('short', 'mean'), 'deep_throw_share': ('deep', 'mean'),
     'middle_share': ('middle', 'mean'), 'yac_per_catch': ('yac', 'mean'), 'air_yds_per_catch': ('air_comp', 'mean'),
     'sack_rate': ('sack', 'mean'), 'int_rate': ('interception', 'mean'),
     'pressure_rate': ('pressure', 'mean'), 'time_to_throw': ('time_to_throw', 'mean'), 'avg_rushers': ('rushers', 'mean'),
     'rush4_or_less': ('four_or_less', 'mean'), 'blitz_rate': ('blitz', 'mean'), 'man_rate': ('man', 'mean'),
     'dime_or_more_DBs': ('dime_plus', 'mean'), 'contested_rate': ('contested', 'mean')}
agg = lambda x: x.agg(**{k: pd.NamedAgg(*v) for k, v in M.items()})
G = {'BAL Q4 lead': db[(db.grp == 'BAL') & (db.period == 'Q4')],
     'BAL 1H lead': db[(db.grp == 'BAL') & (db.period == '1H')],
     'NFL Q4 lead': db[(db.grp == 'NFL') & (db.period == 'Q4')],
     'BAL Q4 lead, last 5 min': db[(db.grp == 'BAL') & (db.period == 'Q4') & (db.mins_left <= 5)],
     'NFL Q4 lead, last 5 min': db[(db.grp == 'NFL') & (db.period == 'Q4') & (db.mins_left <= 5)]}
res = pd.DataFrame({k: agg(v.assign(k=1).groupby('k')).iloc[0] for k, v in G.items()})
q4 = db[db.period == 'Q4']
rk = agg(q4.groupby('defteam')).rank(ascending=False, method='min')
res['BAL rank of 32 in Q4 (1=highest)'] = rk.loc['BAL']
res.round(3).to_csv(f'{out}/deep_defense.csv')
print('=== Opponent dropbacks, defense leading 1-16 ==='); print(res.round(3).to_string())

# Coverage family: usage and EPA, BAL Q4 vs NFL Q4 vs BAL 1H (2020-2025)
c = db[db['cov'].notna() & (db['cov'] != 'BLOWN')].copy()
c['cell'] = c.grp + ' ' + c.period
c = c[c.cell.isin(['BAL Q4', 'BAL 1H', 'NFL Q4'])]
cov = c.groupby(['cov', 'cell']).agg(n=('epa', 'size'), epa=('epa', 'mean')).unstack()
cov[('share', 'BAL Q4')] = cov[('n', 'BAL Q4')] / cov[('n', 'BAL Q4')].sum()
cov[('share', 'BAL 1H')] = cov[('n', 'BAL 1H')] / cov[('n', 'BAL 1H')].sum()
cov[('share', 'NFL Q4')] = cov[('n', 'NFL Q4')] / cov[('n', 'NFL Q4')].sum()
cov = cov.sort_values(('n', 'BAL Q4'), ascending=False)
cov.round(3).to_csv(f'{out}/deep_defense_coverage.csv')
print('\n=== Coverage, 2020-2025 ==='); print(cov.round(3).to_string())

# Each season: the calling tendencies (rank of 32 within season)
rows = []
for s, g in q4.groupby('season'):
    t = agg(g.groupby('defteam'))
    r = t.rank(ascending=False, method='min')
    row = t.loc['BAL'].to_dict(); row.update({f'{k}_rank': r.loc['BAL', k] for k in ['epa_per_dropback', 'man_rate', 'rush4_or_less', 'pressure_rate', 'avg_air_yards', 'short_throw_share', 'yac_per_catch', 'dime_or_more_DBs']})

    rows.append(pd.Series(row, name=s))
bs = pd.DataFrame(rows)
bs.round(3).to_csv(f'{out}/deep_defense_by_season.csv')
print('\n=== BAL Q4-lead pass defense by season (rank of 32, 1 = highest) ===')
print(bs[['dropbacks', 'epa_per_dropback', 'epa_per_dropback_rank', 'man_rate', 'man_rate_rank', 'rush4_or_less', 'pressure_rate',
          'pressure_rate_rank', 'short_throw_share', 'yac_per_catch', 'yac_per_catch_rank', 'dime_or_more_DBs']].round(3).to_string())

# Starters on the field? Top-11 defenders by season snaps; share of them on field per snap
pp = p[p.defense_players.notna() & (p.defense_players != '')].copy()
pp['ids'] = pp.defense_players.str.split(';')
rows = []
for (s, team), g in pp.groupby(['season', 'defteam']):
    top = g.explode('ids').ids.value_counts().head(11).index
    on = g.ids.apply(lambda l: len(set(l) & set(top)) / 11)
    q4l = (g.period == 'Q4') & g.lead.between(1, 16)
    rows.append({'season': s, 'team': team, 'starters_all': on.mean(), 'starters_q4_lead': on[q4l].mean(),
                 'starters_1h': on[g.period == '1H'].mean()})
st = pd.DataFrame(rows)
st['q4_minus_all'] = st.starters_q4_lead - st.starters_all
st.round(3).to_csv(f'{out}/deep_defense_starters.csv', index=False)
print('\n=== Share of top-11 defenders on field ===')
print(st[st.team == 'BAL'].round(3).to_string(index=False))
print('NFL avg (others):', st[st.team != 'BAL'][['starters_all', 'starters_q4_lead', 'q4_minus_all']].mean().round(3).to_dict())

# Fatigue: defensive snaps already played before the 4th quarter starts
fat = p[p.qtr <= 3].groupby(['game_id', 'defteam']).size().rename('snaps_thru_q3').reset_index()
lead_q4 = p[(p.qtr == 4)].groupby(['game_id', 'defteam']).lead.first().reset_index()
fat = fat.merge(lead_q4, on=['game_id', 'defteam'])
fat = fat[fat.lead.between(1, 16)]
print('\nDefensive snaps through Q3 in games entering Q4 with a 1-16 lead: BAL',
      round(fat[fat.defteam == 'BAL'].snaps_thru_q3.mean(), 1), ' NFL', round(fat[fat.defteam != 'BAL'].snaps_thru_q3.mean(), 1))

# Cover 0 (all-out man, no deep safety) share by season, Q4 lead
c0 = db[(db.period == 'Q4') & db['cov'].notna()].assign(c0=lambda x: x['cov'] == 'COVER_0')
t = c0.groupby(['season', 'defteam']).c0.mean().unstack()
c0s = pd.DataFrame({'BAL': t['BAL'], 'NFL_avg': t.drop(columns='BAL').mean(axis=1),
                    'BAL_rank_of_32': t.rank(axis=1, ascending=False, method='min')['BAL']})
c0s.round(3).to_csv(f'{out}/deep_defense_cover0_by_season.csv')
print('\n=== Cover 0 share, Q4 with a lead ==='); print(c0s.round(3).to_string())

# Man vs zone results, BAL vs NFL, 1H vs Q4 (2020-2025)
mz = db[db.man.notna()].assign(cell=lambda x: x.grp + ' ' + x.period)
mz = mz[mz.cell.isin(['BAL 1H', 'BAL Q4', 'NFL Q4'])]
mzt = mz.groupby(['cell', 'man']).agg(n=('epa', 'size'), epa=('epa', 'mean'), explosive=('explosive', 'mean'),
                                     pressure=('pressure', 'mean'), time_to_throw=('time_to_throw', 'mean')).round(3)
mzt.to_csv(f'{out}/deep_defense_man_zone.csv')
print('\n=== Man (1) vs zone (0) ==='); print(mzt.to_string())
