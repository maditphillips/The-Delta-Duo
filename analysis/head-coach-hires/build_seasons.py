"""Build team-season records (regular season) from nflverse games.csv."""
import csv, json
from collections import defaultdict

# franchise continuity: map historical codes to a stable franchise id
FRANCHISE = {'STL':'LA','LA':'LA','LAR':'LA','SD':'LAC','LAC':'LAC',
             'OAK':'LV','LV':'LV','SL':'LA'}
def fid(t): return FRANCHISE.get(t, t)

rows = [r for r in csv.DictReader(open('games.csv'))
        if r['game_type'] == 'REG' and r['home_score'] != '']

ts = defaultdict(lambda: {'w':0,'l':0,'t':0,'pf':0,'pa':0,'g':0,
                          'coach_games':defaultdict(int), 'wk1_coach':None,
                          'coach_by_week':{}})
for r in rows:
    s, wk = int(r['season']), int(r['week'])
    hs, as_ = int(r['home_score']), int(r['away_score'])
    for team, coach, pf, pa in ((r['home_team'], r['home_coach'], hs, as_),
                                (r['away_team'], r['away_coach'], as_, hs)):
        d = ts[(s, fid(team))]
        d['g'] += 1; d['pf'] += pf; d['pa'] += pa
        d['coach_games'][coach] += 1
        d['coach_by_week'][wk] = coach
        if pf > pa: d['w'] += 1
        elif pf < pa: d['l'] += 1
        else: d['t'] += 1

out = []
for (s, team), d in sorted(ts.items()):
    wk1 = d['coach_by_week'][min(d['coach_by_week'])]
    coaches = sorted(d['coach_games'].items(), key=lambda kv: -kv[1])
    out.append({
        'season': s, 'team': team, 'g': d['g'],
        'w': d['w'], 'l': d['l'], 't': d['t'],
        'win_pct': round((d['w'] + 0.5 * d['t']) / d['g'], 6),
        'pf': d['pf'], 'pa': d['pa'], 'net': d['pf'] - d['pa'],
        'pf_pg': round(d['pf'] / d['g'], 4), 'pa_pg': round(d['pa'] / d['g'], 4),
        'net_pg': round((d['pf'] - d['pa']) / d['g'], 4),
        'opening_coach': wk1,
        'primary_coach': coaches[0][0],
        'n_coaches': len(coaches),
        'midseason_change': len(coaches) > 1,
    })
json.dump(out, open('team_seasons.json','w'), indent=0)
print('team-seasons:', len(out))
print('seasons:', min(o['season'] for o in out), '-', max(o['season'] for o in out))
import collections
print('games/season sample:', collections.Counter(o['g'] for o in out))
print('midseason changes:', sum(o['midseason_change'] for o in out))
