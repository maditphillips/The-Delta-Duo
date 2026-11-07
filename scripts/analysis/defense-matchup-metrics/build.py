#!/usr/bin/env python3
"""Turn the raw nflverse pulls into two analysis tables.

team_games.parquet   one row per (game, offense, defense): sums and counts for every
                     defensive metric, from the offense's side. "What the offense did"
                     and "what the defense allowed" are the same row.
player_games.parquet one row per (player, game) for QBs, RBs, WRs and TEs, with fantasy
                     points and the role filters analyze.py uses.

Regular season only.
"""
import os, sys, glob, numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get('DMM_DATA', os.path.join(HERE, '.data'))

POS_MAP = {'QB': 'QB', 'RB': 'RB', 'FB': 'RB', 'HB': 'RB', 'WR': 'WR', 'TE': 'TE'}


def load(sub):
    return pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(os.path.join(DATA, sub, '*.parquet')))],
                     ignore_index=True)


def main():
    pbp   = load('pbp_slim')
    stats = load('stats')
    sch   = pd.read_parquet(os.path.join(DATA, 'schedules.parquet'))

    pbp   = pbp[(pbp.season_type == 'REG') & (pbp.two_point_attempt != 1) & pbp.posteam.notna()].copy()
    stats = stats[stats.season_type == 'REG'].copy()
    stats['pos'] = stats.position.map(POS_MAP)

    # one position per player id (most common listing), used to tag rushers / targets in pbp
    pos_of = (stats.dropna(subset=['pos']).groupby(['player_id', 'pos']).size()
                   .reset_index(name='n').sort_values('n').drop_duplicates('player_id', keep='last')
                   .set_index('player_id').pos)
    pbp['rusher_pos'] = pbp.rusher_player_id.map(pos_of)
    pbp['recv_pos']   = pbp.receiver_player_id.map(pos_of)

    f = lambda c: pbp[c].fillna(0).astype(float)
    wp, hsr = pbp.wp, pbp.half_seconds_remaining
    comp    = wp.between(0.10, 0.90)
    neutral = wp.between(0.20, 0.80) & (hsr > 120)

    R   = (f('rush_attempt') == 1) & (f('qb_scramble') == 0)          # designed runs, any ball carrier
    RB  = R & (pbp.rusher_pos == 'RB')
    DB  = f('qb_dropback') == 1                                         # dropbacks incl. sacks, scrambles
    PA  = f('pass_attempt') == 1                                        # pass attempts incl. sacks
    ATT = PA & (f('sack') == 0)                                         # true attempts
    PLY = R | DB
    epa, yds, succ = f('epa'), f('yards_gained'), f('success')

    col = {}
    def put(name, mask, val=1.0):
        col[name] = np.where(mask, val, 0.0)

    put('plays', PLY);            put('tot_epa', PLY, epa);        put('tot_succ', PLY, succ)
    # run defense
    put('r_n', R);                put('r_epa', R, epa);            put('r_succ', R, succ)
    put('r_yds', R, yds);         put('r_td', R, f('rush_touchdown'))
    put('r_stuff', R & (yds <= 0));  put('r_expl', R & (yds >= 10))
    put('rc_n', R & comp);        put('rc_epa', R & comp, epa);    put('rc_succ', R & comp, succ)
    put('rn_n', R & neutral);     put('rn_epa', R & neutral, epa); put('rn_succ', R & neutral, succ)
    put('rbr_n', RB);             put('rbr_yds', RB, yds);         put('rbr_epa', RB, epa)
    # pass defense
    put('db_n', DB);              put('db_epa', DB, epa);          put('db_succ', DB, succ)
    put('dbc_n', DB & comp);      put('dbc_epa', DB & comp, epa)
    put('dbn_n', DB & neutral);   put('dbn_epa', DB & neutral, epa); put('dbn_succ', DB & neutral, succ)
    put('pa_n', PA)
    put('anya_num', PA, yds + 20 * f('pass_touchdown') - 45 * f('interception'))
    put('sacks', PA & (f('sack') == 1));  put('hits', PA, f('qb_hit').clip(upper=1) + f('sack')); col['hits'] = np.minimum(col['hits'], 1)
    put('ints', PA, f('interception'))
    put('att_n', ATT);            put('cmp', ATT, f('complete_pass')); put('att_yds', ATT, yds)
    put('air', ATT & pbp.air_yards.notna(), f('air_yards')); put('air_n', ATT & pbp.air_yards.notna())
    put('yac', ATT & (f('complete_pass') == 1), f('yards_after_catch'))
    put('cpoe_sum', ATT & pbp.cpoe.notna(), f('cpoe')); put('cpoe_n', ATT & pbp.cpoe.notna())
    put('p_expl', ATT & (yds >= 20)); put('p_td', ATT, f('pass_touchdown'))
    X = PLY & pbp.xpass.notna()
    put('proe_sum', X, f('pass') - f('xpass')); put('proe_n', X)
    put('pass_n', PLY, f('pass'))
    # targets by receiver position
    for p in ('RB', 'WR', 'TE'):
        T = ATT & (pbp.recv_pos == p)
        put(f'{p.lower()}_t_n', T); put(f'{p.lower()}_t_epa', T, epa); put(f'{p.lower()}_t_yds', T, yds)

    c = pd.DataFrame(col)
    for k in ('game_id', 'season', 'week', 'posteam', 'defteam'):
        c[k] = pbp[k].values
    tg = c.groupby(['game_id', 'season', 'week', 'posteam', 'defteam'], as_index=False).sum()
    tg = tg.rename(columns={'posteam': 'off', 'defteam': 'def'})

    # fantasy production by position, from the official weekly stat lines
    s = stats.dropna(subset=['pos']).copy()
    s['tds'] = s[['passing_tds', 'rushing_tds', 'receiving_tds']].fillna(0).sum(axis=1)
    agg = s.groupby(['game_id', 'team', 'pos']).agg(
        ppr=('fantasy_points_ppr', 'sum'), std=('fantasy_points', 'sum'),
        rush_yds=('rushing_yards', 'sum'), rec_yds=('receiving_yards', 'sum'),
        pass_yds=('passing_yards', 'sum'), tgt=('targets', 'sum'), rec=('receptions', 'sum'),
        td=('tds', 'sum')).unstack('pos').fillna(0)
    agg.columns = [f'{p.lower()}_{m}' for m, p in agg.columns]
    agg = agg.reset_index().rename(columns={'team': 'off'})
    tg = tg.merge(agg, on=['game_id', 'off'], how='left')

    # points and Vegas lines (nflverse spread_line: + = home favoured)
    sc = sch[sch.game_type == 'REG'].copy()
    old = {'STL': 'LA', 'SD': 'LAC', 'OAK': 'LV'}            # pbp uses the franchises' current codes
    for k in ('home_team', 'away_team'):
        sc[k] = sc[k].replace(old)
    rows = []
    for side, opp in (('home', 'away'), ('away', 'home')):
        sgn = 1 if side == 'home' else -1
        rows.append(pd.DataFrame({'game_id': sc.game_id, 'off': sc[f'{side}_team'],
                                  'pts': sc[f'{side}_score'],
                                  'implied': (sc.total_line + sgn * sc.spread_line) / 2,
                                  'spread': sgn * sc.spread_line, 'total_line': sc.total_line,
                                  'start_qb': sc[f'{side}_qb_id']}))
    tg = tg.merge(pd.concat(rows), on=['game_id', 'off'], how='left')
    tg['games'] = 1.0
    tg.to_parquet(os.path.join(DATA, 'team_games.parquet'))

    pg = stats.dropna(subset=['pos'])[['player_id', 'player_display_name', 'pos', 'season', 'week',
                                       'game_id', 'team', 'opponent_team', 'attempts', 'carries',
                                       'targets', 'fantasy_points', 'fantasy_points_ppr']].copy()
    pg = pg.rename(columns={'team': 'off', 'opponent_team': 'def',
                            'fantasy_points': 'std', 'fantasy_points_ppr': 'ppr'})
    pg['half'] = (pg['std'] + pg['ppr']) / 2
    pg['touched'] = (pg[['attempts', 'carries', 'targets']].fillna(0).sum(axis=1) > 0)
    pg = pg.merge(tg[['game_id', 'off', 'start_qb']], on=['game_id', 'off'], how='left')
    pg['is_start_qb'] = (pg.pos == 'QB') & (pg.player_id == pg.start_qb)
    pg.drop(columns='start_qb').to_parquet(os.path.join(DATA, 'player_games.parquet'))

    print(f'team_games {len(tg):,} rows  player_games {len(pg):,} rows  seasons {tg.season.min()}-{tg.season.max()}')
    miss = tg[['rb_ppr', 'implied']].isna().mean()
    print('missing share:', miss.round(4).to_dict())


if __name__ == '__main__':
    sys.exit(main())
