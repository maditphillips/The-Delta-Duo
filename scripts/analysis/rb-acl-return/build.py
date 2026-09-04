#!/usr/bin/env python3
"""Turn the fetched nflverse tables into one row per (player, game he actually played).

Participation is the union of three signals, so it works across the whole 1999-2025 span:
a rushing attempt, a target, or an offensive snap (snap counts only exist from 2012).
Writes player_gamelog.parquet and team_games.parquet into the data directory.
"""
import os, sys, glob, pandas as pd, numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get('RB_ACL_DATA', os.path.join(HERE, '.data'))


def main():
    games = pd.read_parquet(f'{DATA}/games.parquet')
    rush  = pd.read_parquet(f'{DATA}/rush_plays.parquet')
    targ  = pd.read_parquet(f'{DATA}/target_plays.parquet')
    pl    = pd.read_parquet(f'{DATA}/players.parquet')
    snaps = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(f'{DATA}/snaps/*.parquet'))],
                      ignore_index=True)

    games['game_date'] = pd.to_datetime(games.game_date)
    tg = pd.concat([games.assign(team=games.home_team), games.assign(team=games.away_team)],
                   ignore_index=True)[['game_id','season','week','season_type','game_date','team']]
    tg.sort_values(['season','week','game_date']).to_parquet(f'{DATA}/team_games.parquet')

    r = (rush.groupby(['rusher_player_id','game_id'], as_index=False)
             .agg(team=('posteam','first'), season=('season','first'), week=('week','first'),
                  season_type=('season_type','first'), carries=('yards_gained','size'),
                  rush_yards=('yards_gained','sum'))
             .rename(columns={'rusher_player_id':'gsis_id'}))
    c = (targ.groupby(['receiver_player_id','game_id'], as_index=False)
             .agg(team_r=('posteam','first'), season_r=('season','first'), week_r=('week','first'),
                  season_type_r=('season_type','first'), targets=('complete_pass','size'),
                  receptions=('complete_pass','sum'), rec_yards=('yards_gained','sum'))
             .rename(columns={'receiver_player_id':'gsis_id'}))
    gl = r.merge(c, on=['gsis_id','game_id'], how='outer')

    pfr2gsis = pl.dropna(subset=['pfr_id','gsis_id']).set_index('pfr_id').gsis_id.to_dict()
    snaps['gsis_id'] = snaps.pfr_player_id.map(pfr2gsis)
    s = (snaps.dropna(subset=['gsis_id'])
              .groupby(['gsis_id','game_id'], as_index=False)
              .agg(off_snaps=('offense_snaps','sum'), off_pct=('offense_pct','max'),
                   team_s=('team','first'), season_s=('season','first'), week_s=('week','first'),
                   season_type_s=('game_type','first')))
    gl = gl.merge(s, on=['gsis_id','game_id'], how='outer')

    for a, b in [('team','team_r'), ('season','season_r'), ('week','week_r'), ('season_type','season_type_r'),
                 ('team','team_s'), ('season','season_s'), ('week','week_s'), ('season_type','season_type_s')]:
        if b in gl:
            gl[a] = gl[a].fillna(gl[b])
    gl = gl.drop(columns=[x for x in gl.columns if x.endswith(('_r','_s')) and x != 'rush_yards'])
    gl['season_type'] = gl.season_type.replace({'WC':'POST','DIV':'POST','CON':'POST','SB':'POST'})

    gl = gl.merge(tg[['game_id','team','game_date']], on=['game_id','team'], how='left')
    num = ['carries','rush_yards','targets','receptions','rec_yards','off_snaps']
    gl[num] = gl[num].fillna(0)
    gl['touches'] = gl.carries + gl.receptions

    tr = rush.groupby(['game_id','posteam'], as_index=False).agg(team_carries=('yards_gained','size'))
    tt = targ.groupby(['game_id','posteam'], as_index=False).agg(team_targets=('complete_pass','size'))
    tc = tr.merge(tt, on=['game_id','posteam'], how='outer').rename(columns={'posteam':'team'})
    gl = gl.merge(tc, on=['game_id','team'], how='left')

    gl['player'] = gl.gsis_id.map(pl.set_index('gsis_id').display_name.to_dict())
    gl['pos']    = gl.gsis_id.map(pl.set_index('gsis_id').position.to_dict())
    gl = gl.sort_values(['gsis_id','game_date']).reset_index(drop=True)
    gl.to_parquet(f'{DATA}/player_gamelog.parquet')
    print(f'{len(gl):,} player-games, {gl.game_date.min().date()} to {gl.game_date.max().date()}')


if __name__ == '__main__':
    sys.exit(main())
