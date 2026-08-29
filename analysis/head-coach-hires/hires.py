import json
from collections import defaultdict
ts = json.load(open('team_seasons.json'))
by = {(o['season'], o['team']): o for o in ts}
hires = []
for o in sorted(ts, key=lambda x: (x['season'], x['team'])):
    prev = by.get((o['season']-1, o['team']))
    if not prev: continue
    if o['opening_coach'] != prev['opening_coach']:
        hires.append({'season': o['season'], 'team': o['team'],
                      'coach': o['opening_coach'],
                      'prev_coach': prev['opening_coach'],
                      'internal_interim': o['opening_coach'] == prev['primary_coach'] or (
                          prev['n_coaches'] > 1 and o['opening_coach'] in ()),
                      'prev_w': prev['w'], 'prev_g': prev['g']})
print('total hires 2000-2025:', len(hires))
for h in hires:
    print(f"{h['season']}\t{h['team']}\t{h['coach']}\t(prev: {h['prev_coach']}, {h['prev_w']}-{h['prev_g']-h['prev_w']})")
json.dump(hires, open('hires_raw.json','w'), indent=0)
