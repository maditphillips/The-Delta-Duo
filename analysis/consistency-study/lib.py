import pandas as pd, numpy as np
D = pd.read_parquet('hppr_weekly.parquet')

def season_table(seasons, maxweek=17, mingames=14, zeros=False):
    """One row per qualifying player-season with mean/sd/cv/boom/bust/floor."""
    d = D[(D.season.isin(seasons)) & (D.week<=maxweek)].copy()
    if zeros:
        # add 0-point weeks for weeks the player's team played but he did not appear
        team_weeks = d[['season','week','team']].drop_duplicates()
        pl = d[['player_id','player_display_name','position','season','team']].drop_duplicates(
             subset=['player_id','season'], keep='last')
        full = pl.merge(team_weeks, on=['season','team'])
        d = full.merge(d[['player_id','season','week','hppr']], on=['player_id','season','week'], how='left')
        d['hppr'] = d.hppr.fillna(0.0)
    rows=[]
    for (pid,name,pos,season), grp in d.groupby(['player_id','player_display_name','position','season']):
        v = grp.hppr.values
        if len(v) < mingames: continue
        m = v.mean()
        if m <= 0: continue
        rows.append(dict(player_id=pid, name=name, position=pos, season=season, g=len(v),
            mean=m, median=float(np.median(v)), sd=v.std(ddof=1), cv=v.std(ddof=1)/m,
            skew=float(pd.Series(v).skew()),
            boom=float((v > 1.5*m).mean()), bust=float((v < 0.5*m).mean()),
            floor=float((v >= 0.75*m).mean())))
    return pd.DataFrame(rows)

def scores_map(seasons, maxweek=17, mingames=14):
    """player-season -> array of weekly scores, for resampling."""
    d = D[(D.season.isin(seasons)) & (D.week<=maxweek)]
    out={}
    for (pid,season), grp in d.groupby(['player_id','season']):
        if len(grp) >= mingames: out[(pid,season)] = grp.hppr.values
    return out
