"""Step 17b: roster variables for the blown-lead model, merged onto features.py output.

Usage: python3 features_roster.py DATA_DIR  ->  writes model2_features.csv

  edge_draft_skill / cb_draft_skill: the team's average draft value over expected (career AV vs picks within 6 slots,
      same draft) for edge rushers / cornerbacks it drafted in the previous 5 drafts. Same method as draft.py.
  edge_cap_pct / cb_cap_pct: share of the salary cap (OverTheCap average per year, as % of cap when signed) committed
      to edge rushers / cornerbacks on that season's roster, using each player's most recent contract signed by then.
      Approximate: matched by name + position; counts a contract while its term runs.
  def_age / def_exp: snap-weighted average age and NFL experience of the defenders on the field (2020-2025 tracking).
  collapse_exposure: average number of earlier blown leads (lost after leading by 10+ or leading entering the 4th)
      that this game's defenders (10+ snaps) were on the field for, in the 4th quarter, with this team, in the current
      or previous two seasons. Tracking starts in 2020, so 2020-21 values are undercounted.
"""
import sys, os, glob
import numpy as np
import pandas as pd

d = sys.argv[1]
out = os.path.dirname(os.path.abspath(__file__))
x = pd.read_pickle(f'{d}/features_stage1.pkl')

# --- draft skill at EDGE / CB
dp = pd.read_csv(f'{d}/draft_picks.csv')
pl = pd.read_csv(f'{d}/players.csv', usecols=['gsis_id', 'pff_position'], low_memory=False).drop_duplicates('gsis_id')
dp = dp[dp.season.between(2010, 2025)].merge(pl, on='gsis_id', how='left')
pos = dp.pff_position.fillna(dp.position)
dp['grp'] = np.select([pos.isin(['ED', 'DE', 'OLB', 'EDGE']), pos.isin(['CB'])], ['EDGE', 'CB'], 'other')
dp['w_av'] = dp.w_av.fillna(0)
dp['exp_av'] = dp.groupby('season', group_keys=False).apply(
    lambda g: pd.Series([g.loc[(g.pick - pk).abs() <= 6, 'w_av'].mean() for pk in g.pick], index=g.index))
dp['over'] = dp.w_av - dp.exp_av
rows = []
for team in dp.team.unique():
    for s in range(2020, 2026):
        w = dp[(dp.team == team) & dp.season.between(s - 5, s - 1)]
        rows.append({'team': team, 'season': s, 'edge_draft_skill': w[w.grp == 'EDGE'].over.mean(),
                     'cb_draft_skill': w[w.grp == 'CB'].over.mean()})
ds = pd.DataFrame(rows)
fix = {'GNB': 'GB', 'KAN': 'KC', 'NWE': 'NE', 'NOR': 'NO', 'SFO': 'SF', 'TAM': 'TB', 'LVR': 'LV', 'OAK': 'LV', 'SDG': 'LAC',
       'STL': 'LA', 'LAR': 'LA'}
ds['team'] = ds.team.replace(fix)
ds = ds.groupby(['team', 'season'], as_index=False).mean()

# --- cap share on EDGE / CB
c = pd.read_csv(f'{d}/contracts.csv.gz')
c = c[c.position.isin(['ED', 'CB']) & c.year_signed.notna()].copy()
c['end'] = c.year_signed + c.years.fillna(1)
ro = pd.concat([pd.read_parquet(f, columns=['season', 'team', 'full_name', 'gsis_id', 'week']) for f in glob.glob(f'{d}/rosters/r_*.parquet')])
ro = ro[ro.season.between(2020, 2025)]
ro = ro.groupby(['season', 'gsis_id', 'full_name']).team.agg(lambda s: s.mode()[0]).reset_index()
cap_rows = []
cc = c.sort_values('year_signed')
for s in range(2020, 2026):
    act = cc[(cc.year_signed <= s) & (cc.end > s)].drop_duplicates('player', keep='last')
    m = ro[ro.season == s].merge(act[['player', 'position', 'apy_cap_pct']], left_on='full_name', right_on='player')
    m['ED'] = np.where(m.position == 'ED', m.apy_cap_pct, 0); m['CB'] = np.where(m.position == 'CB', m.apy_cap_pct, 0)
    cap_rows.append(m.groupby('team')[['ED', 'CB']].sum().reset_index().assign(season=s))
cap = pd.concat(cap_rows).rename(columns={'ED': 'edge_cap_pct', 'CB': 'cb_cap_pct'})
cap['team'] = cap.team.replace({'LAR': 'LA'})

# --- defenders on the field: age, experience, past-collapse exposure (2020-2025 participation)
q = pd.read_parquet(f'{d}/pbp_deep.parquet', columns=['game_id', 'season', 'week', 'qtr', 'defteam', 'defense_players', 'play_type'])
q = q[q.season.between(2020, 2025) & q.defense_players.notna() & (q.defense_players != '') & q.play_type.isin(['pass', 'run'])]
q['ids'] = q.defense_players.str.split(';')
ex = q.explode('ids')
r = pd.concat([pd.read_parquet(f, columns=['season', 'gsis_id', 'birth_date', 'years_exp']) for f in glob.glob(f'{d}/rosters/r_*.parquet')])
r = r.dropna(subset=['gsis_id']).drop_duplicates(['season', 'gsis_id'])
ex = ex.merge(r, left_on=['season', 'ids'], right_on=['season', 'gsis_id'], how='left')
ex['age'] = ex.season - pd.to_datetime(ex.birth_date, errors='coerce').dt.year
ae = ex.groupby(['season', 'defteam']).agg(def_age=('age', 'mean'), def_exp=('years_exp', 'mean')).reset_index().rename(columns={'defteam': 'team'})

snaps = ex.groupby(['game_id', 'defteam', 'ids']).size().rename('n').reset_index()
q4ids = ex[ex.qtr == 4].groupby(['game_id', 'defteam']).ids.agg(set)
gorder = q.groupby(['game_id', 'defteam']).agg(season=('season', 'first'), week=('week', 'first')).reset_index()
blew = x.set_index(['game_id', 'team']).blew_any
exp_rows = []
for team, gg in gorder.groupby('defteam'):
    witnessed = {}  # player -> list of seasons in which he was on the field for a team collapse
    for _, row in gg.sort_values(['season', 'week']).iterrows():
        players = set(snaps[(snaps.game_id == row.game_id) & (snaps.defteam == team) & (snaps.n >= 10)].ids)
        counts = [sum(1 for s_ in witnessed.get(pid, []) if row.season - s_ <= 2) for pid in players]
        exp_rows.append({'game_id': row.game_id, 'team': team, 'collapse_exposure': np.mean(counts) if counts else np.nan})
        if blew.get((row.game_id, team), False):
            for pid in q4ids.get((row.game_id, team), set()):
                witnessed.setdefault(pid, []).append(row.season)
ce = pd.DataFrame(exp_rows)

x = x.merge(ds, on=['team', 'season'], how='left').merge(cap, on=['team', 'season'], how='left')
x = x.merge(ae, on=['team', 'season'], how='left').merge(ce, on=['game_id', 'team'], how='left')
x.to_csv(f'{out}/model2_features.csv', index=False)
cols = ['edge_draft_skill', 'cb_draft_skill', 'edge_cap_pct', 'cb_cap_pct', 'def_age', 'def_exp', 'collapse_exposure']
print(x[cols].describe().T.round(3))
print(x[x.team == 'BAL'].groupby('season')[cols].mean().round(3))
