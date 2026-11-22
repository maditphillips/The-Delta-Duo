"""Step 16: one model for blown leads, all 32 teams, 2020-2025 (2026 lacks coverage data).

Usage: python3 model.py DATA_DIR  (pbp_slim.parquet, pbp_deep.parquet, games.csv, team_games.csv)  ->  writes model_data.csv,
       model_results.csv, model_ravens.csv

Unit: a game where the team led by 1-16 entering the 4th quarter (main) or at halftime (second version); bigger
leads are almost never lost and make the model unstable. Outcome: lost.
Logistic regression, standard errors clustered by team. Predictors:
  Game: exp_margin (pregame Vegas spread, team's view), lead (margin at the start of the period), home.
  Team-season defense (from tracking data, all snaps): man_rate, cover0_rate, blitz_rate (5+ rushers), pressure_rate,
       def_epa_1h (1st-half defensive EPA per play = defense quality before any late fade).
  Team-season offense: proe_lead_2h (pass rate over expected in 2nd halves while leading).
  Staff: new_hc (first season of that head coach with the team), psych_confident, psych_possible
       (reference = no psychologist / unknown; groups from psych_groups.py).
  Then: a Ravens dummy, to see how much of the Ravens' extra blown leads these variables explain.
Continuous team-season variables are standardized (per 1 SD) so odds ratios are comparable.
"""
import sys, os
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

d = sys.argv[1]
out = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, out)
from psych_groups import CONFIDENT, POSSIBLE
pd.set_option('display.width', 220)
YEARS = (2020, 2025)

# --- Team-season style variables
q = pd.read_parquet(f'{d}/pbp_deep.parquet')
q = q[q.season.between(*YEARS) & (q.qtr <= 4) & q.play_type.isin(['pass', 'run']) & (q.qb_kneel == 0) & (q.qb_spike == 0)]
db = q[q.qb_dropback == 1].copy()
db['man'] = (db.defense_man_zone_type == 'MAN_COVERAGE').where(db.defense_man_zone_type.isin(['MAN_COVERAGE', 'ZONE_COVERAGE']))
db['c0'] = (db.defense_coverage_type == 'COVER_0').where(db.defense_coverage_type.notna())
db['blitz'] = (db.number_of_pass_rushers >= 5).where(db.number_of_pass_rushers.notna())
for c_ in ['man', 'c0', 'blitz']:
    db[c_] = db[c_].astype(float)
db['pressure'] = db.was_pressure.astype(float)
dstyle = db.groupby(['season', 'defteam']).agg(man_rate=('man', 'mean'), cover0_rate=('c0', 'mean'),
                                              blitz_rate=('blitz', 'mean'), pressure_rate=('pressure', 'mean'))
d1h = q[q.qtr <= 2].groupby(['season', 'defteam']).epa.mean().rename('def_epa_1h')
lead2h = q[(q.qtr >= 3) & q.score_differential.between(1, 16)]
proe = lead2h.groupby(['season', 'posteam']).pass_oe.mean().rename('proe_lead_2h')
style = dstyle.join(d1h).reset_index().rename(columns={'defteam': 'team'})
style = style.merge(proe.reset_index().rename(columns={'posteam': 'team'}), on=['season', 'team'])

# --- New head coach: first season of that coach with that team (coach = most common in pbp)
p = pd.read_parquet(f'{d}/pbp_slim.parquet', columns=['game_id', 'season', 'home_team', 'away_team', 'home_coach', 'away_coach',
                                                       'qtr', 'total_home_score', 'total_away_score'])
p = p[p.season.between(2015, YEARS[1])]
hc = pd.concat([p[['season', 'home_team', 'home_coach']].set_axis(['season', 'team', 'coach'], axis=1),
                p[['season', 'away_team', 'away_coach']].set_axis(['season', 'team', 'coach'], axis=1)])
hc = hc.groupby(['team', 'season']).coach.agg(lambda c: c.mode()[0]).reset_index().sort_values(['team', 'season'])
hc['new_hc'] = (hc.coach != hc.groupby('team').coach.shift()).astype(int)

# --- Games where the team led at half / entering the 4th
p = p[p.season.between(*YEARS)]
m2 = p[p.qtr <= 2].groupby('game_id')[['total_home_score', 'total_away_score']].max()
m3 = p[p.qtr <= 3].groupby('game_id')[['total_home_score', 'total_away_score']].max()
gm = pd.DataFrame({'m2': m2.total_home_score - m2.total_away_score, 'm3': m3.total_home_score - m3.total_away_score})
t = pd.read_csv(f'{out}/team_games.csv')
t = t[t.season.between(*YEARS)].merge(gm.reset_index(), on='game_id')
spread = pd.read_csv(f'{d}/games.csv', usecols=['game_id', 'spread_line'])
t = t.merge(spread, on='game_id', how='left')
t['home'] = (t.game_id.str.split('_').str[-1] == t.team).astype(int)
sgn = np.where(t.home == 1, 1, -1)
t['exp_margin'] = sgn * t.spread_line
t['lead_half'] = sgn * t.m2
t['lead_q4'] = sgn * t.m3
t['lost'] = (t.pf < t.pa).astype(int)  # ties count as not lost
t = t.merge(style, on=['season', 'team'], how='left').merge(hc[['team', 'season', 'new_hc']], on=['team', 'season'], how='left')
conf = t.team.map(CONFIDENT); poss = t.team.map(POSSIBLE)
t['psych_confident'] = (conf.notna() & (t.season >= conf.fillna(9999))).astype(int)
t['psych_possible'] = (poss.notna() & (t.season >= poss.fillna(9999))).astype(int)
t['ravens'] = (t.team == 'BAL').astype(int)
Z = ['man_rate', 'cover0_rate', 'blitz_rate', 'pressure_rate', 'def_epa_1h', 'proe_lead_2h']
for c in Z:
    t[c] = t[c].astype(float)
    t[c + '_z'] = (t[c] - t[c].mean()) / t[c].std()
t.to_csv(f'{out}/model_data.csv', index=False)

BASE = ('lost ~ exp_margin + {lead} + home + man_rate_z + cover0_rate_z + blitz_rate_z + pressure_rate_z + def_epa_1h_z'
        ' + proe_lead_2h_z + new_hc + psych_confident + psych_possible')
NAMES = {'exp_margin': 'Pregame spread (per point favored)', 'lead_q4': 'Lead entering the 4th (per point)',
         'lead_half': 'Halftime lead (per point)', 'home': 'Home game',
         'man_rate_z': 'Man coverage rate (+1 SD)', 'cover0_rate_z': 'Cover 0 rate (+1 SD)', 'blitz_rate_z': 'Blitz rate, 5+ rushers (+1 SD)',
         'pressure_rate_z': 'Pressure rate (+1 SD)', 'def_epa_1h_z': '1st-half defensive EPA allowed (+1 SD = worse D)',
         'proe_lead_2h_z': 'Pass rate over expected when leading (+1 SD)', 'new_hc': 'First season of new head coach',
         'psych_confident': 'Has psychologist (confident)', 'psych_possible': 'Has psychologist (possible)', 'ravens': 'Ravens'}
rows, rav = [], []
for lead, chance in (('lead_q4', 'Led entering the 4th'), ('lead_half', 'Led at halftime')):
    x = t[t[lead].between(1, 16)].dropna(subset=['exp_margin', 'man_rate', 'def_epa_1h', 'proe_lead_2h'])
    for spec, f in (('without Ravens dummy', BASE.format(lead=lead)), ('with Ravens dummy', BASE.format(lead=lead) + ' + ravens')):
        m = smf.logit(f, data=x).fit(disp=0, cov_type='cluster', cov_kwds={'groups': x.team.astype('category').cat.codes.values})
        ci = m.conf_int()
        for v in m.params.index.drop('Intercept'):
            rows.append({'sample': chance, 'model': spec, 'variable': NAMES.get(v, v), 'odds_ratio': np.exp(m.params[v]),
                         'ci_low': np.exp(ci.loc[v, 0]), 'ci_high': np.exp(ci.loc[v, 1]), 'p_value': m.pvalues[v]})
        if spec == 'without Ravens dummy':
            b = x[x.team == 'BAL']
            pred = m.predict(b)
            rav.append({'sample': chance, 'games': len(b), 'actual_losses': int(b.lost.sum()), 'predicted_losses': pred.sum(),
                        'actual_rate': b.lost.mean(), 'predicted_rate': pred.mean(), 'n_games_model': len(x),
                        'pseudo_r2': m.prsquared})
            # league check: average predicted vs actual for everyone
res = pd.DataFrame(rows)
res.round(3).to_csv(f'{out}/model_results.csv', index=False)
rv = pd.DataFrame(rav)
rv.round(3).to_csv(f'{out}/model_ravens.csv', index=False)
for (s, mdl), g in res.groupby(['sample', 'model'], sort=False):
    print(f'\n=== {s} — {mdl} ===')
    print(g[['variable', 'odds_ratio', 'ci_low', 'ci_high', 'p_value']].round(3).to_string(index=False))
print('\n=== Ravens: actual vs what the model expects (without Ravens dummy) ===')
print(rv.round(3).to_string(index=False))
