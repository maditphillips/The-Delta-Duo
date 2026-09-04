#!/usr/bin/env python3
"""Post-ACL return study for NFL running backs.

For every tear in acl_cohort.csv:
  PRE  = the 8 regular-season games the back played immediately before the tear
         (the game he was hurt in is dropped, since he left it partway through)
  Y1   = every regular-season game he played in the first season he came back
  Y2   = the season after that

Every Y1 change is then compared against age- and workload-matched *healthy* backs
making the same season-to-season step, so normal running-back decline is netted out.

    python3 analyze.py > FINDINGS.txt
"""
import os, sys, numpy as np, pandas as pd
from scipy import stats

HERE  = os.path.dirname(os.path.abspath(__file__))
DATA  = os.environ.get('RB_ACL_DATA', os.path.join(HERE, '.data'))
PRE_N = 8

VOL = ['carries_pg','targets_pg','touches_pg','opp_pg','rush_share','tgt_share','snaps_pg','snap_pct']
EFF = ['ypc','yds_per_touch','epa_per_rush','success_rate','explosive_rate','stuff_rate',
       'rush_fd_rate','yds_per_tgt','ngs_ryoe_att']
PRD = ['rush_yds_pg','scrim_yds_pg','ppr_pg']

gl    = pd.read_parquet(f'{DATA}/player_gamelog.parquet')
rush  = pd.read_parquet(f'{DATA}/rush_plays.parquet')
targ  = pd.read_parquet(f'{DATA}/target_plays.parquet')
snaps = pd.concat([pd.read_parquet(f) for f in
                   sorted(__import__('glob').glob(f'{DATA}/snaps/*.parquet'))], ignore_index=True)
tg    = pd.read_parquet(f'{DATA}/team_games.parquet')
pl    = pd.read_parquet(f'{DATA}/players.parquet')
ngs   = pd.read_parquet(f'{DATA}/ngs_rushing.parquet')
ngs   = ngs[(ngs.week > 0) & (ngs.season_type == 'REG')]

glr      = gl[gl.season_type == 'REG'].copy()
rush_i   = rush.set_index(['rusher_player_id','game_id']).sort_index()
targ_i   = targ.set_index(['receiver_player_id','game_id']).sort_index()
gsis2pfr = pl.dropna(subset=['gsis_id']).set_index('gsis_id').pfr_id.to_dict()
snaps_i  = snaps.dropna(subset=['pfr_player_id']).set_index(['pfr_player_id','game_id']).sort_index()
birth    = pl.dropna(subset=['gsis_id']).set_index('gsis_id').birth_date.to_dict()
rb_ids   = set(pl.loc[pl.position.isin(['RB','HB']), 'gsis_id'].dropna())
ngs_key  = set(zip(ngs.player_gsis_id, ngs.season, ngs.week))
ngs_i    = ngs.set_index(['player_gsis_id','season','week'])

tgr   = tg[tg.season_type == 'REG'].copy(); tgr['game_date'] = pd.to_datetime(tgr.game_date)
sched = {k: v.sort_values('game_date') for k, v in tgr.groupby(['season','team'])}
gps   = (tgr.groupby('season').size() / tgr.groupby('season').team.nunique()).round().to_dict()


def metrics(pid, rows):
    n = len(rows)
    if n == 0:
        return {}
    gids = list(rows.game_id)
    try:    rp = rush_i.loc[(pid, gids), :]
    except KeyError: rp = rush.iloc[0:0]
    try:    tp = targ_i.loc[(pid, gids), :]
    except KeyError: tp = targ.iloc[0:0]

    car, tgt = len(rp), len(tp)
    ry   = float(rp.yards_gained.sum()) if car else 0.0
    rec  = float(tp.complete_pass.sum()) if tgt else 0.0
    recy = float(tp.yards_gained.sum()) if tgt else 0.0
    tch  = car + rec
    tds  = (float(rp.touchdown.sum()) if car else 0.0) + (float(tp.touchdown.sum()) if tgt else 0.0)

    m = dict(games=n, carries_pg=car/n, targets_pg=tgt/n, touches_pg=tch/n, opp_pg=(car+tgt)/n,
             rush_yds_pg=ry/n, scrim_yds_pg=(ry+recy)/n,
             rush_share=car/rows.team_carries.sum() if rows.team_carries.sum() else np.nan,
             tgt_share=tgt/rows.team_targets.sum() if rows.team_targets.sum() else np.nan,
             ypc=ry/car if car else np.nan, yds_per_touch=(ry+recy)/tch if tch else np.nan,
             epa_per_rush=float(rp.epa.mean()) if car else np.nan,
             success_rate=float(rp.success.mean()) if car else np.nan,
             explosive_rate=float((rp.yards_gained >= 10).mean()) if car else np.nan,
             stuff_rate=float((rp.yards_gained <= 0).mean()) if car else np.nan,
             rush_fd_rate=float(rp.first_down.mean()) if car else np.nan,
             catch_rate=rec/tgt if tgt else np.nan, yds_per_tgt=recy/tgt if tgt else np.nan,
             epa_per_tgt=float(tp.epa.mean()) if tgt else np.nan,
             ppr_pg=(0.1*(ry+recy) + 6*tds + rec)/n,
             carries_tot=car, touches_tot=tch, scrim_yds_tot=ry+recy)

    pfr = gsis2pfr.get(pid); m['snaps_pg'] = m['snap_pct'] = np.nan
    if pfr and not pd.isna(pfr):
        try:
            s = snaps_i.loc[(pfr, gids), :]
            if len(s):
                m['snaps_pg'] = float(s.offense_snaps.mean())
                m['snap_pct'] = float(s.offense_pct.mean())
        except KeyError:
            pass

    keys = [(pid, s, w) for s, w in zip(rows.season, rows.week) if (pid, s, w) in ngs_key]
    if keys:
        nn = ngs_i.loc[keys].reset_index()
        nn = nn[nn.rush_attempts > 0]
        if len(nn):
            w = nn.rush_attempts
            m['ngs_ryoe_att']   = float(np.average(nn.rush_yards_over_expected_per_att, weights=w))
            m['ngs_efficiency'] = float(np.average(nn.efficiency, weights=w))
            m['ngs_8plus_box']  = float(np.average(nn.percent_attempts_gte_eight_defenders, weights=w))
            m['ngs_att']        = int(w.sum())
    return m


def missed(d1, t1, s1, d2, t2, s2):
    """Regular-season games the back's team(s) played while he was out."""
    a = sched.get((s1, t1)); n = 0
    if s2 == s1:
        return int(((a.game_date > d1) & (a.game_date < d2)).sum()) if a is not None else 0
    if a is not None:
        n += int((a.game_date > d1).sum())
    for s in range(int(s1) + 1, int(s2)):
        n += int(gps.get(float(s), 16))
    b = sched.get((s2, t2))
    if b is not None:
        n += int((b.game_date < d2).sum())
    return n


def build_cohort():
    coh, recs = pd.read_csv(f'{HERE}/acl_cohort.csv', parse_dates=['injury_date']), []
    for _, r in coh.iterrows():
        pid = r.gsis_id
        g = glr[glr.gsis_id == pid].sort_values('game_date').reset_index(drop=True)
        before, after = g[g.game_date <= r.injury_date], g[g.game_date > r.injury_date]
        if before.empty:
            continue
        inj = before.iloc[-1]
        pre = (before.iloc[:-1] if r.mechanism == 'game' else before).tail(PRE_N)
        bd = birth.get(pid)
        rec = dict(player=r.player, gsis_id=pid, team=r.team, injury_date=r.injury_date,
                   injury_year=r.injury_date.year, injury_nfl_season=int(inj.season),
                   mechanism=r.mechanism, confidence=r.confidence, date_basis=r.date_basis, note=r.note,
                   last_game=inj.game_date, last_game_sw=f"{int(inj.season)}w{int(inj.week)}",
                   career_games_pre=len(before),
                   age_at_injury=round((r.injury_date - pd.Timestamp(bd)).days/365.25, 1)
                                 if pd.notna(bd) else np.nan)
        if after.empty:
            rec.update(returned=False)
        else:
            b = after.iloc[0]; big = after[after.carries >= 10]
            rec.update(returned=True, return_date=b.game_date, return_season=int(b.season),
                       return_week=int(b.week), return_team=b.team,
                       days_to_return=(b.game_date - r.injury_date).days,
                       games_missed=missed(inj.game_date, inj.team, inj.season,
                                           b.game_date, b.team, b.season),
                       days_to_10carry_game=(big.iloc[0].game_date - r.injury_date).days if len(big) else np.nan)
        rec.update({f'pre_{k}': v for k, v in metrics(pid, pre).items()})
        if rec.get('returned'):
            y1 = g[(g.season == rec['return_season']) & (g.game_date >= rec['return_date'])]
            rec.update({f'y1_{k}': v for k, v in metrics(pid, y1).items()})
            rec['y1_team_games'] = len(sched.get((float(rec['return_season']), rec['return_team']), []))
            y2 = g[g.season == rec['return_season'] + 1]
            if len(y2):
                rec.update({f'y2_{k}': v for k, v in metrics(pid, y2).items()})
        recs.append(rec)
    res = pd.DataFrame(recs)
    res['baseline_ok'] = (res.pre_games >= 4) & (res.pre_touches_pg >= 5)
    return res


def build_controls():
    """Healthy RB season-to-season transitions: the same PRE -> next-season comparison."""
    rows = []
    for pid, g in glr[glr.gsis_id.isin(rb_ids)].groupby('gsis_id', sort=False):
        g = g.sort_values('game_date'); seasons = sorted(g.season.unique())
        for s in seasons:
            if s + 1 not in seasons:
                continue
            a, b = g[g.season == s], g[g.season == s+1]
            if len(a) < 4 or len(b) < 1:
                continue
            la, fb = a.iloc[-1], b.iloc[0]
            if missed(la.game_date, la.team, la.season, fb.game_date, fb.team, fb.season) > 2:
                continue                                  # missed real time: not a healthy control
            pre = a.tail(PRE_N); pm = metrics(pid, pre)
            if pm.get('touches_pg', 0) < 5 or len(pre) < 4:
                continue
            bd = birth.get(pid)
            r = dict(gsis_id=pid, player=a.player.iloc[0], season=int(s), next_season=int(s+1),
                     age=round((la.game_date - pd.Timestamp(bd)).days/365.25, 1) if pd.notna(bd) else np.nan)
            r.update({f'pre_{k}': v for k, v in pm.items()})
            r.update({f'y1_{k}': v for k, v in metrics(pid, b).items()})
            rows.append(r)
    return pd.DataFrame(rows)


def sect(t): print('\n' + '=' * len(t) + '\n' + t + '\n' + '=' * len(t))


def main():
    res = build_cohort()
    ctl = build_controls()
    res.to_csv(f'{HERE}/acl_cohort_metrics.csv', index=False)

    sect('1. RETURN TO PLAY')
    ret = res[res.returned == True]
    print(f"episodes: {len(res)}   returned to a regular-season game: {len(ret)} ({len(ret)/len(res):.0%})")
    print("never returned: " + ', '.join(f"{r.player} ({r.injury_year})"
                                         for _, r in res[res.returned != True].iterrows()))
    clean = ret[ret.days_to_return <= 550]
    print(f"\nDays from injury to first regular-season game (n={len(ret)}, all returners)")
    print(f"  mean {ret.days_to_return.mean():.0f}   median {ret.days_to_return.median():.0f}   "
          f"IQR {ret.days_to_return.quantile(.25):.0f}-{ret.days_to_return.quantile(.75):.0f}   "
          f"range {ret.days_to_return.min():.0f}-{ret.days_to_return.max():.0f}")
    print(f"  months: mean {ret.days_to_return.mean()/30.44:.1f}   median {ret.days_to_return.median()/30.44:.1f}")
    late = ', '.join(ret.loc[ret.days_to_return > 550, 'player'])
    print(f"\nExcluding the {len(ret)-len(clean)} multi-year layoffs >550 days ({late})  (n={len(clean)})")
    print(f"  mean {clean.days_to_return.mean():.0f} d ({clean.days_to_return.mean()/30.44:.1f} mo)   "
          f"median {clean.days_to_return.median():.0f} d ({clean.days_to_return.median()/30.44:.1f} mo)   "
          f"IQR {clean.days_to_return.quantile(.25):.0f}-{clean.days_to_return.quantile(.75):.0f}   "
          f"range {clean.days_to_return.min():.0f}-{clean.days_to_return.max():.0f}")
    print(f"  team games missed: mean {clean.games_missed.mean():.1f}  median {clean.games_missed.median():.0f}")
    d10 = clean.days_to_10carry_game.dropna()
    print(f"  days to first 10+ carry game: median {d10.median():.0f} (n={len(d10)})")
    print("\nBy how the tear happened (returners <=550 days):")
    for lab, m in [('in-season game injury', clean.mechanism == 'game'),
                   ('practice / preseason / offseason', clean.mechanism != 'game')]:
        s = clean[m]
        print(f"  {lab:34s} n={len(s):2d}  median {s.days_to_return.median():.0f} d "
              f"({s.days_to_return.median()/30.44:.1f} mo)")
    print("\nBy era (returners <=550 days):")
    for lo, hi in [(1999,2009),(2010,2016),(2017,2024)]:
        s = clean[(clean.injury_year >= lo) & (clean.injury_year <= hi)]
        if len(s):
            print(f"  {lo}-{hi}: n={len(s):2d}  median {s.days_to_return.median():.0f} d  "
                  f"mean {s.days_to_return.mean():.0f} d")

    sect('2. PRE-INJURY vs FIRST YEAR BACK (matched against healthy RBs)')
    an = ret[(ret.baseline_ok == True) & ret.y1_games.notna()].copy()
    print(f"analysis sample: {len(an)} episodes with a usable pre-injury baseline and a return season")
    print(f"control pool: {len(ctl)} healthy RB season-to-season transitions, "
          f"{ctl.season.min()}-{ctl.season.max()}")

    def match(case, band=0.30, agew=2.0, seasw=8):
        c = ctl[(ctl.age.sub(case.age_at_injury).abs() <= agew)
                & (ctl.season.sub(case.injury_nfl_season).abs() <= seasw)
                & (ctl.pre_touches_pg.between(case.pre_touches_pg*(1-band), case.pre_touches_pg*(1+band)))]
        if len(c) < 15:
            return match(case, band+0.20, agew+1.0, seasw+4) if band < 0.9 else ctl
        return c

    rowsA = []
    for _, case in an.iterrows():
        m = match(case)
        r = dict(player=case.player, year=case.injury_year, n_ctl=len(m))
        for k in VOL + EFF + PRD:
            pk, yk = f'pre_{k}', f'y1_{k}'
            if pd.isna(case.get(pk)) or pd.isna(case.get(yk)):
                r[f'{k}__case'] = r[f'{k}__ctl'] = np.nan
                continue
            r[f'{k}__case'] = case[yk] - case[pk]
            cm = m[m[pk].notna() & m[yk].notna()]
            r[f'{k}__ctl'] = (cm[yk] - cm[pk]).median() if len(cm) >= 8 else np.nan
        rowsA.append(r)
    A = pd.DataFrame(rowsA)
    A.to_csv(f'{HERE}/case_vs_control_deltas.csv', index=False)

    print("\nMedians across the cohort. 'ctl chg' is the median year-over-year change for age- and")
    print("workload-matched healthy backs; 'excess' is the per-case case-minus-control median;")
    print("p is a Wilcoxon signed-rank test on that excess.")
    def block(title, keys):
        print(f"\n{title}")
        print(f"{'metric':<18}{'pre':>8}{'year 1':>9}{'chg':>9}{'chg %':>8}   "
              f"{'ctl chg':>9}{'ctl %':>8}   {'excess':>9}{'p':>8}{'n':>5}")
        for k in keys:
            pk, yk = f'pre_{k}', f'y1_{k}'
            s = an[[pk, yk]].dropna()
            if len(s) < 5:
                continue
            pre, y1 = s[pk].median(), s[yk].median()
            both = A[[f'{k}__case', f'{k}__ctl']].dropna()
            exc = both[f'{k}__case'] - both[f'{k}__ctl']
            p = stats.wilcoxon(exc)[1] if len(exc) >= 6 and exc.abs().sum() > 0 else np.nan
            ok = pre and not k.startswith('epa') and abs(pre) > abs(y1 - pre)
            ctlm = both[f'{k}__ctl'].median()
            cpct   = f"{(y1-pre)/abs(pre)*100:+6.1f}%" if ok else '      -'
            ctlpct = f"{ctlm/abs(pre)*100:+6.1f}%"     if ok else '      -'
            print(f"{k:<18}{pre:>8.3f}{y1:>9.3f}{y1-pre:>9.3f}{cpct:>8}   "
                  f"{ctlm:>9.3f}{ctlpct:>8}   {exc.median():>9.3f}{p:>8.3f}{len(exc):>5d}")
    block('VOLUME / OPPORTUNITY', VOL)
    block('EFFICIENCY', EFF)
    block('PRODUCTION', PRD)

    sect('3. AVAILABILITY IN YEAR 1')
    an2 = an.copy(); an2['avail'] = an2.y1_games / an2.y1_team_games
    print(f"games played in the return season: median {an2.y1_games.median():.0f} of "
          f"{an2.y1_team_games.median():.0f} team games ({an2.avail.median():.0%})")
    print(f"  played >=90% of team games: {(an2.avail>=0.9).mean():.0%}")
    print(f"  played <50% of team games:  {(an2.avail<0.5).mean():.0%}")

    sect('4. PER-EPISODE DETAIL')
    cols = ['player','injury_year','age_at_injury','days_to_return','games_missed','return_season',
            'y1_games','pre_touches_pg','y1_touches_pg','pre_ypc','y1_ypc','pre_epa_per_rush',
            'y1_epa_per_rush','pre_success_rate','y1_success_rate','pre_ppr_pg','y1_ppr_pg']
    t = an[cols].copy().sort_values('injury_year')
    t['tch_%'] = (t.y1_touches_pg/t.pre_touches_pg - 1).mul(100).round(0)
    t['ypc_%'] = (t.y1_ypc/t.pre_ypc - 1).mul(100).round(0)
    pd.set_option('display.width', 300)
    print(t.round(3).to_string(index=False))
    t.to_csv(f'{HERE}/per_episode_summary.csv', index=False)

    sect('5. YEAR 2 BACK')
    y2 = an[an.y2_games.notna() & (an.y2_games >= 3)]
    print(f"episodes with a year-2 season of >=3 games: {len(y2)}")
    print(f"{'metric':<18}{'pre':>9}{'year 1':>9}{'year 2':>9}{'y1 vs pre':>11}{'y2 vs pre':>11}")
    for k in ['carries_pg','touches_pg','snap_pct','rush_share','ypc','yds_per_touch',
              'epa_per_rush','success_rate','explosive_rate','scrim_yds_pg','ppr_pg']:
        s3 = y2[[f'pre_{k}', f'y1_{k}', f'y2_{k}']].dropna()
        if len(s3) < 5:
            continue
        a_, b_, c_ = s3[f'pre_{k}'].median(), s3[f'y1_{k}'].median(), s3[f'y2_{k}'].median()
        f1 = f"{(b_-a_)/abs(a_)*100:+9.1f}%" if abs(a_) > abs(b_-a_) else '        -'
        f2 = f"{(c_-a_)/abs(a_)*100:+9.1f}%" if abs(a_) > abs(c_-a_) else '        -'
        print(f"{k:<18}{a_:>9.3f}{b_:>9.3f}{c_:>9.3f}{f1:>11}{f2:>11}")
    print(f"\ngames played: year 1 median {y2.y1_games.median():.0f} | year 2 median {y2.y2_games.median():.0f}")

    sect('6. WHO RECOVERS THE WORKLOAD')
    an3 = an.copy()
    an3['tch_ratio'] = an3.y1_touches_pg / an3.pre_touches_pg
    an3['ypc_ratio'] = an3.y1_ypc / an3.pre_ypc
    print(f"regained >=90% of pre-injury touches/game in year 1: {(an3.tch_ratio>=0.9).mean():.0%} "
          f"({int((an3.tch_ratio>=0.9).sum())}/{len(an3)})")
    print(f"fell below 60% of pre-injury touches/game:           {(an3.tch_ratio<0.6).mean():.0%} "
          f"({int((an3.tch_ratio<0.6).sum())}/{len(an3)})")
    print(f"matched or beat pre-injury yards per carry:          {(an3.ypc_ratio>=1).mean():.0%}")
    for title, cuts in [
        ('By age at the tear', [('25 and under', an3.age_at_injury <= 25), ('over 25', an3.age_at_injury > 25)]),
        ('By pre-injury workload', [('bell cow (>=15 tch/g)', an3.pre_touches_pg >= 15),
                                    ('rotational (<15 tch/g)', an3.pre_touches_pg < 15)]),
        ('By era', [('1999-2012', an3.injury_year <= 2012), ('2013-2024', an3.injury_year > 2012)])]:
        print(f"\n{title}:")
        for lab, m in cuts:
            s4 = an3[m]
            print(f"  {lab:<22} n={len(s4):2d}  touches/g {s4.pre_touches_pg.median():5.1f} -> "
                  f"{s4.y1_touches_pg.median():5.1f} "
                  f"({(s4.y1_touches_pg.median()/s4.pre_touches_pg.median()-1)*100:+.0f}%)"
                  f"   YPC {s4.pre_ypc.median():.2f} -> {s4.y1_ypc.median():.2f}"
                  f"   games {s4.y1_games.median():.0f}   RTP {s4.days_to_return.median():.0f} d")


if __name__ == '__main__':
    sys.exit(main())
