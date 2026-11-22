"""Step 3: what do the Ravens do differently when protecting a lead? 2020-2026.

Usage: python3 behavior.py DATA_DIR  (needs game_flags.csv from blown.py)  ->  writes behavior.csv, behavior_ranks.csv

"Protecting a lead" = the team is up 1-16 points (still a game). Offense = plays the
team runs; defense = plays the opponent runs. Groups:
  BAL 1H lead      - Ravens leading in the 1st half
  BAL 2H lead      - Ravens leading in the 2nd half (3rd + 4th quarters)
  NFL 2H lead      - every other team leading in the 2nd half
  BAL 2H, blown    - Ravens leading in the 2nd half of games they blew (10+ lead lost,
                     85% win chance lost, or led at half and lost the 2nd half)
  BAL 2H, held     - Ravens leading in the 2nd half of games they led and kept control
"""
import sys, os
import numpy as np
import pandas as pd

d = sys.argv[1]
out = os.path.dirname(os.path.abspath(__file__))
p = pd.read_parquet(f'{d}/pbp_slim.parquet')
p = p[p.season.between(2020, 2026) & (p.qtr <= 4)].copy()
f = pd.read_csv(f'{out}/game_flags.csv')
f['blown'] = f.blew10 | f.wp85_lost | f.half_fade
f['held'] = (f.led10 | f.led_half) & ~f.blown
f = f.set_index(['game_id', 'team'])

# Seconds between snaps on the same drive (pace)
# rows are already in game order
p['next_secs'] = p.groupby(['game_id', 'fixed_drive']).game_seconds_remaining.shift(-1)
p['secs_per_play'] = (p.game_seconds_remaining - p.next_secs).where(lambda s: s.between(1, 60))

sc = p.play_type.isin(['pass', 'run']) & (p.qb_kneel == 0) & (p.qb_spike == 0)
pl = p[sc].copy()
pl['half'] = np.where(pl.qtr <= 2, '1H', '2H')
pl['explosive'] = ((pl['pass'] == 1) & (pl.yards_gained >= 20)) | ((pl.rush == 1) & (pl.yards_gained >= 10))
pl['turnover'] = (pl.interception == 1) | (pl.fumble_lost == 1)
pl['early'] = pl.down.isin([1, 2])
pl['third'] = pl.down == 3
pl['third_conv'] = np.where(pl.third, pl.first_down.fillna(0), np.nan)
pl['early_pass'] = np.where(pl.early, pl['pass'], np.nan)
pl['pen_on_me'] = (pl.penalty == 1) & (pl.penalty_team == pl.posteam)
pl['pen_on_def'] = (pl.penalty == 1) & (pl.penalty_team == pl.defteam)

def tag(df, side):
    """side='off': team = posteam, lead = score_differential. side='def': team = defteam."""
    x = df.copy()
    x['team'] = x.posteam if side == 'off' else x.defteam
    x['lead'] = x.score_differential if side == 'off' else -x.score_differential
    x = x[x.lead.between(1, 16)]
    k = pd.MultiIndex.from_arrays([x.game_id, x.team])
    x['blown'] = f.blown.reindex(k).fillna(False).values
    x['held'] = f.held.reindex(k).fillna(False).values
    x['coach_era'] = np.where(x.season >= 2026, 'Minter', 'Harbaugh')
    return x

OFF = {'plays': ('epa', 'count'), 'pass_rate': ('pass', 'mean'), 'early_down_pass_rate': ('early_pass', 'mean'),
       'pass_over_expected': ('pass_oe', 'mean'), 'epa_per_play': ('epa', 'mean'), 'success_rate': ('success', 'mean'),
       'third_down_conv': ('third_conv', 'mean'), 'sack_rate': ('sack', 'mean'), 'turnover_rate': ('turnover', 'mean'),
       'explosive_rate': ('explosive', 'mean'), 'shotgun_rate': ('shotgun', 'mean'), 'no_huddle_rate': ('no_huddle', 'mean'),
       'secs_per_play': ('secs_per_play', 'mean'), 'penalty_rate_on_us': ('pen_on_me', 'mean')}
DEF = {'plays': ('epa', 'count'), 'opp_pass_rate': ('pass', 'mean'), 'epa_allowed': ('epa', 'mean'),
       'success_allowed': ('success', 'mean'), 'third_down_conv_allowed': ('third_conv', 'mean'),
       'sack_rate_forced': ('sack', 'mean'), 'takeaway_rate': ('turnover', 'mean'), 'explosive_allowed': ('explosive', 'mean'),
       'opp_secs_per_play': ('secs_per_play', 'mean'), 'penalty_rate_on_us': ('pen_on_def', 'mean')}

def summarize(x, spec):
    return x.agg(**{k: pd.NamedAgg(*v) for k, v in spec.items()}) if isinstance(x, pd.core.groupby.DataFrameGroupBy) \
        else pd.Series({k: getattr(x[v[0]], v[1])() for k, v in spec.items()})

rows, ranks = [], []
for side, spec in (('offense', OFF), ('defense', DEF)):
    x = tag(pl, 'off' if side == 'offense' else 'def')
    bal = x[x.team == 'BAL']
    groups = {
        'BAL 1H lead': bal[bal.half == '1H'],
        'BAL 2H lead': bal[bal.half == '2H'],
        'NFL 2H lead': x[(x.team != 'BAL') & (x.half == '2H')],
        'BAL 2H, blown games': bal[(bal.half == '2H') & bal.blown],
        'BAL 2H, held games': bal[(bal.half == '2H') & bal.held],
        'BAL 2H lead, Harbaugh 20-25': bal[(bal.half == '2H') & (bal.coach_era == 'Harbaugh')],
        'BAL 2H lead, Minter 26': bal[(bal.half == '2H') & (bal.coach_era == 'Minter')],
        'NFL 1H lead': x[(x.team != 'BAL') & (x.half == '1H')],
    }
    for name, g in groups.items():
        rows.append(summarize(g, spec).rename(f'{side}|{name}'))
    # Rank BAL among 32 teams in 2H-lead situations (1 = highest value)
    t2 = summarize(x[x.half == '2H'].groupby('team'), spec)
    r = t2.rank(ascending=False, method='min').loc['BAL'].rename(f'{side}|BAL rank of 32 (1=highest)')
    ranks.append(r)

res = pd.concat(rows, axis=1).T
res.index = pd.MultiIndex.from_tuples([i.split('|') for i in res.index], names=['side', 'group'])
rk = pd.concat(ranks, axis=1).T
rk.index = pd.MultiIndex.from_tuples([i.split('|') for i in rk.index], names=['side', 'group'])
res.round(4).to_csv(f'{out}/behavior.csv')
rk.to_csv(f'{out}/behavior_ranks.csv')
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 30)
for side in ('offense', 'defense'):
    print(f'\n=== {side.upper()} (team up 1-16) ===')
    print(pd.concat([res.loc[side], rk.loc[side]]).dropna(axis=1, how='all').T.round(3).to_string())
