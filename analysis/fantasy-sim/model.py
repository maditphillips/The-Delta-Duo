"""Shared pieces: load nflverse weekly stats + schedule, build player-season rows
as of a cutoff week, and the rest-of-season rate estimator."""
import csv
from collections import defaultdict

POSITIONS = ('QB', 'RB', 'WR', 'TE')


def load_weeks(season):
    """player_id -> {'name', 'pos', 'weeks': {week: (team, ppr)}} for REG games."""
    out = {}
    for r in csv.DictReader(open(f'w{season}.csv')):
        if r['season_type'] != 'REG' or r['position_group'] not in POSITIONS:
            continue
        p = out.setdefault(r['player_id'], {'name': r['player_display_name'],
                                            'pos': r['position_group'], 'weeks': {}})
        p['weeks'][int(r['week'])] = (r['team'], float(r['fantasy_points_ppr'] or 0))
    return out


def load_schedule():
    """season -> team -> sorted list of REG weeks the team plays."""
    sched = defaultdict(lambda: defaultdict(list))
    for r in csv.DictReader(open('games.csv')):
        if r['game_type'] != 'REG':
            continue
        s, wk = int(r['season']), int(r['week'])
        sched[s][r['home_team']].append(wk)
        sched[s][r['away_team']].append(wk)
    for s in sched:
        for t in sched[s]:
            sched[s][t].sort()
    return sched


def season_line(p):
    """(games, points) over a whole season for one player's weekly dict."""
    if p is None:
        return 0, 0.0
    return len(p['weeks']), sum(v[1] for v in p['weeks'].values())


def build_rows(season, cutoff, weeks, sched):
    """One row per player who appeared in weeks 1..cutoff of `season`.

    weeks: {season: load_weeks(season)} covering season, season-1, season-2.
    Carries the inputs the estimator needs and, when the season is complete,
    the actual rest-of-season outcome.
    """
    cur, prev1, prev2 = weeks[season], weeks.get(season - 1, {}), weeks.get(season - 2, {})
    rows = []
    for pid, p in cur.items():
        early = {w: v for w, v in p['weeks'].items() if w <= cutoff}
        if not early:
            continue
        team = early[max(early)][0]
        team_weeks = sched[season].get(team, [])
        remaining = sum(1 for w in team_weeks if w > cutoff)
        late = [v[1] for w, v in p['weeks'].items() if w > cutoff]
        g1, pts1 = season_line(prev1.get(pid))
        g2, pts2 = season_line(prev2.get(pid))
        rows.append({
            'id': pid, 'name': p['name'], 'pos': p['pos'], 'team': team,
            'g0': len(early), 'pts0': sum(v[1] for v in early.values()),
            'g1': g1, 'pts1': pts1, 'g2': g2, 'pts2': pts2,
            'remaining': remaining,
            'ros_pts': sum(late),  # actual, meaningful only for finished seasons
            'season_pts': sum(v[1] for v in p['weeks'].values()),
        })
    return rows


def features(row, cutoff):
    """Regression inputs. Points-per-game-played this season and the two prior
    seasons (0 when absent), plus how often the player was on the field."""
    ppg = lambda pts, g: pts / g if g else 0.0
    return [1.0,
            ppg(row['pts0'], row['g0']), row['g0'] / cutoff,
            ppg(row['pts1'], row['g1']), min(row['g1'], 17) / 17, 1.0 if row['g1'] else 0.0,
            ppg(row['pts2'], row['g2']), 1.0 if row['g2'] else 0.0]


FEATURE_NAMES = ['intercept', 'ppg_now', 'played_share_now', 'ppg_last', 'games_last',
                 'has_last', 'ppg_2ago', 'has_2ago']


def solve(xs, ys, ridge=1e-6):
    """Ordinary least squares via the normal equations (tiny ridge for safety)."""
    n = len(xs[0])
    A = [[sum(x[i] * x[j] for x in xs) + (ridge if i == j else 0) for j in range(n)] for i in range(n)]
    b = [sum(x[i] * y for x, y in zip(xs, ys)) for i in range(n)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(A[r][c]))
        A[c], A[p], b[c], b[p] = A[p], A[c], b[p], b[c]
        for r in range(n):
            if r != c:
                f = A[r][c] / A[c][c]
                A[r] = [ar - f * ac for ar, ac in zip(A[r], A[c])]
                b[r] -= f * b[c]
    return [b[i] / A[i][i] for i in range(n)]


def predict(coef, row, cutoff, floor=0.1):
    """Expected rest-of-season points per remaining team game."""
    return max(floor, sum(c * f for c, f in zip(coef, features(row, cutoff))))
