"""Step 17: build the expanded variable set for the blown-lead model (2020-2025 games).

Usage: python3 features.py DATA_DIR  ->  writes model2_features.csv (one row per team-game where the team led by 1-16
entering the 4th quarter or at halftime)

DATA_DIR holds: pbp_slim.parquet, pbp_deep.parquet, play_by_play_YYYY.parquet (2017-2025, for timeouts),
games.csv, contracts.csv.gz (nflverse/OverTheCap historical contracts), rosters/r_YYYY.parquet, draft_picks.csv, players.csv.

Variables that describe HOW a lead is lost inside the same game (4th-quarter pressure, penalties, 3-and-outs, turnovers,
run rate late) are entered as the team's SEASON tendency with the current game left out ("loo"), so the model asks
"do teams that tend to do X blow more leads" rather than "did the game where they blew it look bad".
Everything measured before the period starts (1st-half explosives, snaps so far, timeouts left, rest, opponent QB) is
taken from that game directly.
"""
import sys, os, glob
import numpy as np
import pandas as pd

d = sys.argv[1]
out = os.path.dirname(os.path.abspath(__file__))
Y0, Y1 = 2020, 2025

EVERY = None  # every (season, team, game_id) 2020-2025, filled in below

def loo(df, keys, num, den, name):
    """Leave-one-game-out season rate: (season num - game num) / (season den - game den), for EVERY game the team
    played (a game with no qualifying plays just contributes 0 to the numerator and denominator)."""
    g = df.groupby(keys + ['game_id'])[[num, den]].sum().reset_index()
    base = EVERY.rename(columns={'team': keys[1]})
    g = base.merge(g, on=keys + ['game_id'], how='left').fillna({num: 0, den: 0})
    s = g.groupby(keys)[[num, den]].transform('sum')
    g[name] = (s[num] - g[num]) / (s[den] - g[den]).replace(0, np.nan)
    return g[keys + ['game_id', name]]

# ---------------- base game rows (from team_games + flags) ----------------
t = pd.read_csv(f'{out}/team_games.csv')
t = t[t.season.between(2017, Y1)].copy()
p = pd.read_parquet(f'{d}/pbp_slim.parquet', columns=['game_id', 'season', 'qtr', 'total_home_score', 'total_away_score', 'home_wp'])
p = p[p.season.between(2017, Y1)]
p['m'] = p.total_home_score - p.total_away_score
gm = p.groupby('game_id').agg(home_max=('m', 'max'), away_max=('m', lambda x: -x.min()))
gm = gm.join(p[p.qtr <= 2].groupby('game_id').m.last().rename('m2')).join(p[p.qtr <= 3].groupby('game_id').m.last().rename('m3'))
t = t.merge(gm.reset_index(), on='game_id')
t['home'] = (t.game_id.str.split('_').str[-1] == t.team).astype(int)
sgn = np.where(t.home == 1, 1, -1)
t['lead_half'] = sgn * t.m2
t['lead_q4'] = sgn * t.m3
t['led10'] = np.where(t.home == 1, t.home_max, t.away_max) >= 10
t['lost'] = (t.pf < t.pa).astype(int)
t['blew10'] = t.led10 & (t.lost == 1)
t['blew_q4'] = (t.lead_q4 > 0) & (t.lost == 1)
t['blew_any'] = t.blew10 | t.blew_q4
t = t.sort_values(['team', 'season', 'week'])

# History: blown leads last season, in previous 10 games, and in the previous game
t['prev_game_blew'] = t.groupby('team').blew_any.shift(1).fillna(False).astype(int)
t['blown_prev10'] = t.groupby('team').blew_any.transform(lambda s: s.shift(1).rolling(10, min_periods=1).sum()).fillna(0)
ss = t.groupby(['team', 'season']).agg(b=('blew_any', 'sum'), c=('led10', 'sum')).reset_index()
ss['blown_rate_prev_season'] = ss.b / ss.c.replace(0, np.nan)
ss['season'] += 1
t = t.merge(ss[['team', 'season', 'blown_rate_prev_season']], on=['team', 'season'], how='left')

# Schedule context: rest, short week, Thursday, primetime, spread, opponent QB
g = pd.read_csv(f'{d}/games.csv')
g['primetime'] = (g.gametime.fillna('13:00') >= '19:00').astype(int)
g['thursday'] = (g.weekday == 'Thursday').astype(int)
t = t.merge(g[['game_id', 'spread_line', 'home_rest', 'away_rest', 'primetime', 'thursday', 'home_qb_id', 'away_qb_id', 'div_game']],
            on='game_id', how='left')
sgn = np.where(t.home == 1, 1, -1)  # recompute: rows were re-sorted above
t['exp_margin'] = sgn * t.spread_line
t['rest_days'] = np.where(t.home == 1, t.home_rest, t.away_rest)
t['rest_diff'] = t.rest_days - np.where(t.home == 1, t.away_rest, t.home_rest)
t['short_week'] = (t.rest_days <= 5).astype(int)
t['opp_qb_id'] = np.where(t.home == 1, t.away_qb_id, t.home_qb_id)
t = t[t.season.between(Y0, Y1)]

# ---------------- play-level data ----------------
EVERY = pd.concat([pd.DataFrame({'game_id': g.game_id, 'season': g.season, 'team': g.home_team}),
                   pd.DataFrame({'game_id': g.game_id, 'season': g.season, 'team': g.away_team})])
EVERY = EVERY[EVERY.season.between(Y0, Y1) & EVERY.game_id.isin(t.game_id)]
q = pd.read_parquet(f'{d}/pbp_deep.parquet')
q = q[q.season.between(Y0, Y1) & (q.qtr <= 4)]
sc = q[q.play_type.isin(['pass', 'run']) & (q.qb_kneel == 0) & (q.qb_spike == 0)].copy()
sc['lead_def'] = -sc.score_differential
db = sc[sc.qb_dropback == 1].copy()
db['pressure'] = db.was_pressure.astype(float)
db['ttt'] = db.time_to_throw.astype(float)
db['man'] = (db.defense_man_zone_type == 'MAN_COVERAGE').where(db.defense_man_zone_type.isin(['MAN_COVERAGE', 'ZONE_COVERAGE'])).astype(float)
db['c0'] = (db.defense_coverage_type == 'COVER_0').where(db.defense_coverage_type.notna()).astype(float)
db['blitz'] = (db.number_of_pass_rushers >= 5).where(db.number_of_pass_rushers.notna()).astype(float)
db['one'] = 1.0
db['has_pr'] = db.pressure.notna().astype(float); db['pressure0'] = db.pressure.fillna(0)

feats = []
# Defense, season style (all snaps) -- kept from the first model
style = db.groupby(['season', 'defteam']).agg(man_rate=('man', 'mean'), cover0_rate=('c0', 'mean'), blitz_rate=('blitz', 'mean'),
                                             pressure_rate=('pressure', 'mean')).reset_index().rename(columns={'defteam': 'team'})
# Defense, 4th quarter only (leave-one-game-out)
q4d = db[db.qtr == 4].copy()
feats.append(loo(q4d.rename(columns={'defteam': 'team'}), ['season', 'team'], 'pressure0', 'has_pr', 'q4_pressure_loo'))
comp = q4d[q4d.complete_pass == 1].copy(); comp['yac'] = comp.yards_after_catch.fillna(0)
feats.append(loo(comp.rename(columns={'defteam': 'team'}), ['season', 'team'], 'yac', 'one', 'q4_yac_allowed_loo'))
pen = q[(q.qtr == 4) & (q.penalty == 1) & (q.penalty_team == q.defteam)].copy()
pen['one'] = 1.0; pen['dpi'] = (pen.penalty_type == 'Defensive Pass Interference').astype(float)
gl = t[['season', 'team', 'game_id']].copy(); gl['g'] = 1.0
pc = pen.groupby(['season', 'defteam', 'game_id'])[['one', 'dpi']].sum().reset_index().rename(columns={'defteam': 'team'})
pc = gl.merge(pc, on=['season', 'team', 'game_id'], how='left').fillna({'one': 0, 'dpi': 0})
allg = t[['season', 'team', 'game_id']]
# per-game counts need every game of the season, not just lead games
every = pd.concat([pd.DataFrame({'game_id': g.game_id, 'season': g.season, 'team': g.home_team}),
                   pd.DataFrame({'game_id': g.game_id, 'season': g.season, 'team': g.away_team})])
every = every[every.season.between(Y0, Y1)]
pc = every.merge(pen.groupby(['defteam', 'game_id'])[['one', 'dpi']].sum().reset_index().rename(columns={'defteam': 'team'}),
                 on=['team', 'game_id'], how='left').fillna({'one': 0, 'dpi': 0})
pc['g'] = 1.0
feats.append(loo(pc, ['season', 'team'], 'one', 'g', 'q4_def_penalties_pg_loo'))
feats.append(loo(pc, ['season', 'team'], 'dpi', 'g', 'q4_dpi_pg_loo'))
# Game-level, before the 4th: defensive snaps through Q3, explosive plays allowed in the 1st half
snaps = sc[sc.qtr <= 3].groupby(['game_id', 'defteam']).size().rename('def_snaps_thru_q3').reset_index().rename(columns={'defteam': 'team'})
ex = sc[sc.qtr <= 2].assign(ex=lambda x: ((x['pass'] == 1) & (x.yards_gained >= 20)) | ((x.rush == 1) & (x.yards_gained >= 10)))
ex1h = ex.groupby(['game_id', 'defteam']).ex.sum().rename('explosives_allowed_1h').reset_index().rename(columns={'defteam': 'team'})
# Opponent tendencies: Q4 pass rate when trailing, QB time to throw (season, leave-one-out), opponent QB EPA/dropback
trail = sc[(sc.qtr == 4) & (sc.score_differential < 0)].copy(); trail['one'] = 1.0; trail['pass_f'] = trail['pass'].astype(float)
opp_pr = loo(trail.rename(columns={'posteam': 'opp'}), ['season', 'opp'], 'pass_f', 'one', 'opp_q4_pass_rate_trailing_loo')
ot = db.copy(); ot['has_t'] = ot.ttt.notna().astype(float); ot['ttt0'] = ot.ttt.fillna(0)
opp_ttt = loo(ot.rename(columns={'posteam': 'opp'}), ['season', 'opp'], 'ttt0', 'has_t', 'opp_time_to_throw_loo')
qbe = db[db.passer_player_name.notna()].copy(); qbe['epa0'] = qbe.epa.fillna(0)
# passer id: map passer name within team-season to opp_qb_id via games.csv names is fragile; use the opponent offense's
# dropback EPA from its other games instead (the starting QB plays most dropbacks)
opp_epa = loo(qbe.rename(columns={'posteam': 'opp'}), ['season', 'opp'], 'epa0', 'one', 'opp_pass_epa_loo')

# Offense tendencies when leading (leave-one-out): run rate last 5 min, 3-and-outs in Q4, QB turnovers in Q4
lead_off = sc[sc.score_differential.between(1, 16)].copy()
l5 = lead_off[(lead_off.qtr == 4) & (lead_off.game_seconds_remaining <= 300)].copy(); l5['one'] = 1.0; l5['run'] = l5.rush.astype(float)
feats.append(loo(l5.rename(columns={'posteam': 'team'}), ['season', 'team'], 'run', 'one', 'run_rate_last5_leading_loo'))
qs = pd.read_parquet(f'{d}/pbp_slim.parquet', columns=['game_id', 'season', 'qtr', 'posteam', 'fixed_drive', 'drive_play_count', 'fixed_drive_result'])
qs = qs[qs.season.between(Y0, Y1)]
dr = qs[(qs.qtr == 4) & qs.fixed_drive.notna() & qs.posteam.notna()].groupby(['game_id', 'fixed_drive']).agg(
    season=('season', 'first'), team=('posteam', 'first'), plays=('drive_play_count', 'first'), res=('fixed_drive_result', 'first')).reset_index()
dr['tao'] = ((dr.plays <= 3) & (dr.res == 'Punt')).astype(float); dr['one'] = 1.0
feats.append(loo(dr, ['season', 'team'], 'tao', 'one', 'q4_three_and_out_rate_loo'))
q4o = sc[(sc.qtr == 4) & (sc.qb_dropback == 1)].copy(); q4o['one'] = 1.0
q4o['qb_to'] = ((q4o.interception == 1) | ((q4o.fumble_lost == 1) & (q4o['pass'] == 1))).astype(float)
feats.append(loo(q4o.rename(columns={'posteam': 'team'}), ['season', 'team'], 'qb_to', 'one', 'q4_qb_turnover_rate_loo'))

# Timeouts left entering the 4th (own and opponent): from raw play-by-play
to = []
for y in range(Y0, Y1 + 1):
    r = pd.read_parquet(f'{d}/pbp_{y}.parquet', columns=['game_id', 'qtr', 'home_timeouts_remaining', 'away_timeouts_remaining', 'home_team'])
    to.append(r[r.qtr == 4].groupby('game_id').first().reset_index())
to = pd.concat(to)

# ---------------- assemble ----------------
x = t.merge(style, on=['season', 'team'], how='left')
for f_ in feats:
    x = x.merge(f_, on=['season', 'team', 'game_id'], how='left')
x = x.merge(snaps, on=['game_id', 'team'], how='left').merge(ex1h, on=['game_id', 'team'], how='left')
for o_ in (opp_pr, opp_ttt, opp_epa):
    x = x.merge(o_, on=['season', 'opp', 'game_id'], how='left')
x = x.merge(to[['game_id', 'home_timeouts_remaining', 'away_timeouts_remaining']], on='game_id', how='left')
x['own_timeouts_q4'] = np.where(x.home == 1, x.home_timeouts_remaining, x.away_timeouts_remaining)
x['opp_timeouts_q4'] = np.where(x.home == 1, x.away_timeouts_remaining, x.home_timeouts_remaining)

# 1st-half defensive EPA (season, all games) and new head coach -- kept from the first model
x = x.merge(sc[sc.qtr <= 2].groupby(['season', 'defteam']).epa.mean().rename('def_epa_1h').reset_index().rename(columns={'defteam': 'team'}),
            on=['season', 'team'], how='left')
pp = pd.read_parquet(f'{d}/pbp_slim.parquet', columns=['season', 'home_team', 'away_team', 'home_coach', 'away_coach'])
hc = pd.concat([pp[['season', 'home_team', 'home_coach']].set_axis(['season', 'team', 'coach'], axis=1),
                pp[['season', 'away_team', 'away_coach']].set_axis(['season', 'team', 'coach'], axis=1)])
hc = hc.groupby(['team', 'season']).coach.agg(lambda c: c.mode()[0]).reset_index().sort_values(['team', 'season'])
hc['new_hc'] = (hc.coach != hc.groupby('team').coach.shift()).astype(int)
x = x.merge(hc[['team', 'season', 'new_hc', 'coach']], on=['team', 'season'], how='left')

# ---------------- roster: draft skill, cap spending, age/experience, past-collapse exposure ----------------
dv = pd.read_csv(f'{out}/draft_value_all.csv') if os.path.exists(f'{out}/draft_value_all.csv') else None
x.to_pickle(f'{d}/features_stage1.pkl')
print('stage 1 rows', len(x), 'cols', x.shape[1])
