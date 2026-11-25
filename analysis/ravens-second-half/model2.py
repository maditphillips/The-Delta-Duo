"""Step 18: expanded blown-lead model -- logistic regression (main), mixed-effects logistic and lasso logistic (checks).

Usage: python3 model2.py  (model2_features.csv from features.py + features_roster.py; optional coordinators_afc.csv,
       coordinators_nfc.csv, psych_groups_user.csv)  ->  writes model2_logit.csv, model2_mixed.csv, model2_lasso.csv,
       model2_ravens.csv, model2_vif.csv

Sample: 2020-2025 games where the team led by 1-16 entering the 4th quarter (and, separately, at halftime).
Outcome: lost the game. Continuous variables standardized (odds ratio per 1 SD); yes/no variables as 0/1.
  Main: logistic regression, errors clustered by team.
  Check 1: mixed-effects logistic (team random intercept; variational Bayes, statsmodels BinomialBayesMixedGLM). Also
           gives each team's leftover tendency after all variables.
  Check 2: lasso logistic (L1 penalty chosen by 10-fold cross-validation); variables it drops to 0 add little.
"""
import os, warnings
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from statsmodels.genmod.bayes_mixed_glm import BinomialBayesMixedGLM
from statsmodels.stats.outliers_influence import variance_inflation_factor
from sklearn.linear_model import LogisticRegressionCV
warnings.filterwarnings('ignore')

out = os.path.dirname(os.path.abspath(__file__))
x = pd.read_csv(f'{out}/model2_features.csv')

# Coordinators (if the research tables exist): new DC / new defensive play caller / DC hired from inside
coord = [pd.read_csv(f'{out}/{f}') for f in ('coordinators_afc.csv', 'coordinators_nfc.csv') if os.path.exists(f'{out}/{f}')]
if coord:
    cd = pd.concat(coord).sort_values(['team', 'season'])
    # Resolve "same as DC" to the DC's name; teams with no titled DC keep the named play caller
    pc = cd.defensive_play_caller.fillna('').astype(str)
    cd['caller'] = np.where(pc.str.lower().str.startswith('same') | (pc == ''), cd.defensive_coordinator.fillna(''), pc)
    cd['caller'] = cd.caller.str.replace(r'\s*\(.*\)', '', regex=True).str.strip()
    prev = cd.groupby('team').caller.shift()
    cd['dc_new'] = pd.to_numeric(cd.dc_new, errors='coerce')
    # 2020 has no previous row in the table, so use the researched "first season as DC" flag for it
    cd['playcaller_new'] = np.where(prev.isna(), cd.dc_new.fillna(0), (cd.caller != prev).astype(int)).astype(int)
    cd['dc_new'] = cd.dc_new.fillna(cd.playcaller_new)
    cd['dc_internal'] = (cd.dc_hire_type.astype(str).str.lower() == 'internal').astype(int)
    cd['dc_returning'] = (cd.dc_hire_type.astype(str).str.lower() == 'returning').astype(int)
    x = x.merge(cd[['team', 'season', 'dc_new', 'playcaller_new', 'dc_internal', 'dc_returning']], on=['team', 'season'], how='left')
# Sports psychologist groups chosen by the user: team,first_season,group (has / none / unsure)
if os.path.exists(f'{out}/psych_groups_user.csv'):
    pg = pd.read_csv(f'{out}/psych_groups_user.csv')
    x = x.merge(pg, on='team', how='left')
    x['psych_has'] = ((x.group == 'has') & (x.season >= x.first_season.fillna(0))).astype(int)
    x['psych_none'] = (x.group == 'none').astype(int)   # reference = unsure

CONT = ['exp_margin', 'LEAD', 'pressure_rate', 'q4_pressure_loo', 'man_rate', 'cover0_rate', 'blitz_rate',
        'q4_yac_allowed_loo', 'q4_def_penalties_pg_loo', 'q4_dpi_pg_loo', 'def_snaps_thru_q3', 'explosives_allowed_1h',
        'opp_q4_pass_rate_trailing_loo', 'opp_time_to_throw_loo', 'opp_pass_epa_loo', 'def_epa_1h',
        'edge_draft_skill', 'cb_draft_skill', 'edge_cap_pct', 'cb_cap_pct', 'def_age', 'def_exp', 'collapse_exposure',
        'run_rate_last5_leading_loo', 'q4_three_and_out_rate_loo', 'q4_qb_turnover_rate_loo',
        'own_timeouts_q4', 'opp_timeouts_q4', 'rest_diff', 'blown_rate_prev_season', 'blown_prev10']
BIN = ['home', 'new_hc', 'short_week', 'thursday', 'primetime', 'div_game', 'prev_game_blew'] + \
      [c for c in ('dc_new', 'playcaller_new', 'dc_internal', 'dc_returning', 'psych_has', 'psych_none') if c in x]
LABEL = {'exp_margin': 'Pregame spread (favored by)', 'LEAD': 'Size of lead', 'pressure_rate': 'Pressure rate, all snaps (season)',
         'q4_pressure_loo': '4th-quarter pressure rate (season)', 'man_rate': 'Man coverage rate', 'cover0_rate': 'Cover 0 rate',
         'blitz_rate': 'Blitz rate (5+ rushers)', 'q4_yac_allowed_loo': '4th-qtr YAC allowed per catch (missed-tackle stand-in)',
         'q4_def_penalties_pg_loo': '4th-qtr defensive penalties per game', 'q4_dpi_pg_loo': '4th-qtr pass interference per game',
         'def_snaps_thru_q3': 'Defensive snaps before the 4th (fatigue)', 'explosives_allowed_1h': 'Explosive plays allowed, 1st half (this game)',
         'opp_q4_pass_rate_trailing_loo': 'Opponent 4th-qtr pass rate when trailing', 'opp_time_to_throw_loo': 'Opponent QB time to throw',
         'opp_pass_epa_loo': 'Opponent QB quality (EPA per dropback)', 'def_epa_1h': '1st-half defense quality (EPA allowed)',
         'edge_draft_skill': 'Edge-rusher draft value, last 5 drafts', 'cb_draft_skill': 'Cornerback draft value, last 5 drafts',
         'edge_cap_pct': 'Cap share on edge rushers', 'cb_cap_pct': 'Cap share on cornerbacks', 'def_age': 'Defense average age',
         'def_exp': 'Defense average experience', 'collapse_exposure': 'Past collapses defenders were on field for',
         'run_rate_last5_leading_loo': 'Run rate, last 5 min with lead', 'q4_three_and_out_rate_loo': '4th-qtr 3-and-out rate',
         'q4_qb_turnover_rate_loo': '4th-qtr QB turnover rate', 'own_timeouts_q4': 'Own timeouts left entering 4th',
         'opp_timeouts_q4': 'Opponent timeouts left entering 4th', 'rest_diff': 'Rest-day advantage',
         'blown_rate_prev_season': 'Blown-lead rate last season', 'blown_prev10': 'Blown leads in previous 10 games',
         'home': 'Home game', 'new_hc': 'New head coach', 'short_week': 'Short week (5 or fewer days)', 'thursday': 'Thursday game',
         'primetime': 'Primetime game', 'div_game': 'Division game', 'prev_game_blew': 'Blew a lead the week before',
         'dc_new': 'New defensive coordinator', 'playcaller_new': 'New defensive play caller', 'dc_internal': 'DC promoted from inside', 'dc_returning': 'DC returning to a former team',
         'psych_has': 'Has sports psychologist', 'psych_none': 'Confirmed no psychologist', 'ravens': 'Ravens'}

def run(lead_col, tag):
    s = x[x[lead_col].between(1, 16)].copy()
    s['LEAD'] = s[lead_col]
    s['ravens'] = (s.team == 'BAL').astype(int)
    s = s.dropna(subset=CONT + BIN).reset_index(drop=True)
    z = s.copy()
    for c in CONT:
        z[c] = (s[c] - s[c].mean()) / s[c].std()
    X = CONT + BIN
    groups = z.team.astype('category').cat.codes.values
    # VIF (collinearity check)
    vif = pd.DataFrame({'variable': [LABEL[v] for v in X],
                        'vif': [variance_inflation_factor(z[X].assign(c=1).values.astype(float), i) for i in range(len(X))]})
    f = 'lost ~ ' + ' + '.join(X)
    res = []
    for spec, form in (('main', f), ('with Ravens', f + ' + ravens')):
        m = smf.logit(form, data=z).fit(disp=0, maxiter=200, cov_type='cluster', cov_kwds={'groups': groups})
        ci = m.conf_int()
        for v in m.params.index.drop('Intercept'):
            res.append({'sample': tag, 'model': spec, 'variable': LABEL[v], 'odds_ratio': np.exp(m.params[v]),
                        'ci_low': np.exp(ci.loc[v, 0]), 'ci_high': np.exp(ci.loc[v, 1]), 'p_value': m.pvalues[v]})
        if spec == 'main':
            b = z[z.team == 'BAL']
            rav = {'sample': tag, 'games': len(b), 'actual_losses': int(b.lost.sum()), 'expected_losses': m.predict(b).sum(),
                   'n_games': len(z), 'n_losses': int(z.lost.sum()), 'pseudo_r2': m.prsquared}
    # Mixed effects: team random intercept
    mm = BinomialBayesMixedGLM.from_formula(f, {'team': '0 + C(team)'}, z).fit_vb()
    fe = pd.Series(mm.fe_mean, index=mm.model.exog_names); sd = pd.Series(mm.fe_sd, index=mm.model.exog_names)
    mixed = pd.DataFrame({'sample': tag, 'variable': [LABEL[v] for v in X], 'odds_ratio': np.exp(fe[X].values),
                          'ci_low': np.exp((fe[X] - 1.96 * sd[X]).values), 'ci_high': np.exp((fe[X] + 1.96 * sd[X]).values)})
    re = pd.Series(mm.random_effects()['Mean'].values, index=[n.split('[')[-1].rstrip(']') for n in mm.model.vc_names])
    rav['ravens_team_effect_odds'] = float(np.exp(re.filter(like='BAL').iloc[0]))
    rav['ravens_team_effect_rank'] = int(re.rank(ascending=False)[re.filter(like='BAL').index[0]])
    # Lasso
    lz = LogisticRegressionCV(Cs=30, cv=10, penalty='l1', solver='saga', scoring='neg_log_loss', max_iter=20000, random_state=0)
    lz.fit(z[X].values.astype(float), z.lost.values)
    lasso = pd.DataFrame({'sample': tag, 'variable': [LABEL[v] for v in X], 'odds_ratio': np.exp(lz.coef_[0]),
                          'kept': lz.coef_[0] != 0})
    return pd.DataFrame(res), mixed, lasso, rav, vif.assign(sample=tag)

R = [run('lead_q4', 'Led by 1-16 entering the 4th'), run('lead_half', 'Led by 1-16 at halftime')]
logit = pd.concat([r[0] for r in R]); mixed = pd.concat([r[1] for r in R]); lasso = pd.concat([r[2] for r in R])
rav = pd.DataFrame([r[3] for r in R]); vif = pd.concat([r[4] for r in R])
for df_, n_ in ((logit, 'logit'), (mixed, 'mixed'), (lasso, 'lasso'), (rav, 'ravens'), (vif, 'vif')):
    df_.round(3).to_csv(f'{out}/model2_{n_}.csv', index=False)
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 200)
for tag in logit['sample'].unique():
    a = logit[(logit['sample'] == tag) & (logit.model == 'main')].set_index('variable')
    b = mixed[mixed['sample'] == tag].set_index('variable')
    c = lasso[lasso['sample'] == tag].set_index('variable')
    tab = pd.DataFrame({'logit_OR': a.odds_ratio, 'p': a.p_value, 'mixed_OR': b.odds_ratio, 'mixed_lo': b.ci_low, 'mixed_hi': b.ci_high,
                        'lasso_OR': c.odds_ratio, 'lasso_kept': c.kept})
    print(f'\n=== {tag} ===')
    print(tab.sort_values('p').round(3).to_string())
    rv = logit[(logit['sample'] == tag) & (logit.model == 'with Ravens') & (logit.variable == 'Ravens')]
    print('Ravens dummy:', rv[['odds_ratio', 'ci_low', 'ci_high', 'p_value']].round(3).to_dict('records'))
print(rav.round(3).to_string(index=False))
print('Max VIF:', vif.groupby('sample').vif.max().round(1).to_dict())
print(vif.sort_values('vif', ascending=False).head(6).round(1).to_string(index=False))
