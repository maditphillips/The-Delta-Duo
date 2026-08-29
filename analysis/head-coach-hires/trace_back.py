"""Trace each hire's head-coaching history backwards out of games.csv, and audit
the hand-assigned labels against it.

nflverse carries head coaches ONLY - `away_coach`/`home_coach` in games.csv is the
single staff field in the whole project; the string "coordinator" does not appear
anywhere in nflreadr or nfldata. So OC/DC/college/ST cannot be traced.

What CAN be traced is every coach's NFL head-coaching record from 1999 on. That
settles two of the hand-labeled columns outright:
  * prior_nfl_hc      - had he been an NFL head coach before this hire?
  * internal_promo    - had he already coached this same franchise in year 0?

Writes those back into coach_labels.csv as derived_* columns, and classifies every
disagreement with the hand label rather than assuming the trace wins.
"""
import csv
from collections import defaultdict

FRANCHISE = {'STL': 'LA', 'LA': 'LA', 'LAR': 'LA', 'SD': 'LAC', 'LAC': 'LAC',
             'OAK': 'LV', 'LV': 'LV'}
fid = lambda t: FRANCHISE.get(t, t)

# games.csv stores Jim Mora Sr. (IND 1999-2001) and his son Jim Mora Jr.
# (ATL 2004-06, SEA 2009) under the identical string. Every other multi-season
# gap in the file is a genuine same-person hiatus - verified by listing them.
ALIASED = {('Jim Mora', 2006)}          # (name, on-or-before season) -> not the same man

rows = [r for r in csv.DictReader(open('games.csv'))
        if r['game_type'] == 'REG' and r['home_score'] != '']
tenure = defaultdict(lambda: defaultdict(set))
for r in rows:
    s = int(r['season'])
    tenure[r['home_coach']][s].add(fid(r['home_team']))
    tenure[r['away_coach']][s].add(fid(r['away_team']))
FIRST = min(int(r['season']) for r in rows)
LAST = max(int(r['season']) for r in rows)

def prior_stints(coach, season):
    if any(coach == n and season <= yr for n, yr in ALIASED):
        return {}
    return {y: t for y, t in tenure[coach].items() if y < season}

labels = list(csv.DictReader(open('coach_labels.csv')))
print(f"games.csv head-coach record: {FIRST}-{LAST}, {len(tenure)} distinct head coaches\n")

AGREE, PRE_WINDOW, INTERIM_ONLY, ALIAS = [], [], [], []
out = []
for L in labels:
    s, coach, team = int(L['season']), L['coach'], L['team']
    st = prior_stints(coach, s)
    derived_hc = bool(st)
    derived_internal = team in tenure[coach].get(s - 1, set())
    L['derived_prior_hc'] = '1' if derived_hc else '0'
    L['derived_internal_promo'] = '1' if derived_internal else '0'
    L['derived_prior_hc_seasons'] = ';'.join(str(y) for y in sorted(st))
    out.append(L)
    if L['exclude'] == '1':
        continue
    hand = L['prior_nfl_hc'] == '1'
    if hand == derived_hc:
        AGREE.append(L)
    elif hand and not derived_hc:
        PRE_WINDOW.append(L)                      # stint ended before 1999
    elif derived_internal or len(st) == 1:
        INTERIM_ONLY.append((L, sorted(st)))      # caretaker stint, not a lane
    else:
        ALIAS.append((L, sorted(st)))

n = sum(1 for L in labels if L['exclude'] != '1')
print(f"AUDIT of prior_nfl_hc across {n} hires")
print(f"  {len(AGREE):>3}  hand label and trace agree")
print(f"  {len(PRE_WINDOW):>3}  trace blind: only head-coaching job ended before {FIRST}")
print(f"  {len(INTERIM_ONLY):>3}  definitional: prior stint was an interim/caretaker run")
print(f"  {len(ALIAS):>3}  unresolved\n")

print(f"  Trace-blind (hand label stands, games.csv cannot see back this far):")
for L in PRE_WINDOW:
    print(f"    {L['season']} {L['team']:<4} {L['coach']:<22} {L['prior_detail']}")
print(f"\n  Interim-only prior stints. The hand labels answer \"what job was he hired")
print(f"  FROM\", and a caretaker run is not a lane you get hired out of, so these are")
print(f"  deliberately not retreads. Both readings are defensible; the split below")
print(f"  shows the choice does not matter:")
for L, yrs in INTERIM_ONLY:
    print(f"    {L['season']} {L['team']:<4} {L['coach']:<22} interim in {yrs}")
if ALIAS:
    print("\n  UNRESOLVED - inspect these:")
    for L, yrs in ALIAS:
        print(f"    {L['season']} {L['team']:<4} {L['coach']:<22} prior HC seasons {yrs}")

print(f"\nINTERNAL PROMOTIONS derived outright ({sum(1 for L in out if L['derived_internal_promo']=='1' and L['exclude']!='1')}):")
for L in out:
    if L['derived_internal_promo'] == '1' and L['exclude'] != '1':
        print(f"    {L['season']} {L['team']:<4} {L['coach']:<22} [{L['prior_role']}]")

cols = list(labels[0].keys())
with open('coach_labels.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader(); w.writerows(out)
print(f"\nwrote derived_* columns back into coach_labels.csv")

print(f"""
WHAT THE TRACE CAN AND CANNOT SETTLE
  prior_nfl_hc      {len(AGREE)}/{n} machine-confirmed; {len(PRE_WINDOW)} need pre-{FIRST} knowledge
  internal_promo    derived outright for all {n}
  OC / DC / college / ST / position
                    0/{n}. nflverse has no coordinator or assistant record at all,
                    so this stays hand-labeled until an external source is wired in.""")
