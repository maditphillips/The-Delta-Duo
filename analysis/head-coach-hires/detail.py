exec(open('analyze.py').read().split("def row(")[0])
OC = [r for r in ACTIVE if r['bucket']=='OC' and r.get('y1')]
print('MODERN-ERA OC HIRES (2017-2025), year 1, pace-adjusted win change:')
mods = sorted([r for r in OC if r['season']>=2017], key=lambda r: -r['d_w17_y1'])
for r in mods:
    print(f"  {r['season']} {r['team']:<4} {r['coach']:<20} {r['y0']['w']:>2}W -> {r['y1']['w']:>2}W   "
          f"pace {r['d_w17_y1']:+5.2f}  resid {r['r_w17_y1']:+5.2f}  net/g {r['d_net_y1']:+6.2f}")
v=[r['d_w17_y1'] for r in mods]
print(f"  mean {mean(v):+.2f}  median {st.median(v):+.2f}  n={len(v)}")
print(f"  trimmed (drop best+worst): {mean(sorted(v)[1:-1]):+.2f}")
print(f"  share >= +3 wins: {sum(1 for x in v if x>=3)}/{len(v)}")

print('\nOLD-ERA OC HIRES (2000-2016), year 1:')
old = [r for r in OC if r['season']<2017]
v2=[r['d_w17_y1'] for r in old]
print(f"  mean {mean(v2):+.2f}  median {st.median(v2):+.2f}  n={len(v2)}  share >= +3: {sum(1 for x in v2 if x>=3)}/{len(v2)}")
t,p = None,None
print('\nDistribution of year-1 pace-adjusted win change, ALL 179 hires:')
allv = sorted(r['d_w17_y1'] for r in ACTIVE if r.get('y1'))
import bisect
for q in (0.1,0.25,0.5,0.75,0.9):
    print(f"  p{int(q*100):>2}: {allv[int(q*len(allv))]:+.2f}")
print(f"  share >= +3 wins: {sum(1 for x in allv if x>=3)}/{len(allv)} = {100*sum(1 for x in allv if x>=3)/len(allv):.0f}%")
print(f"  share <= 0:       {sum(1 for x in allv if x<=0)}/{len(allv)} = {100*sum(1 for x in allv if x<=0)/len(allv):.0f}%")

print('\nBIGGEST YEAR-1 JUMPS (any bucket):')
for r in sorted([r for r in ACTIVE if r.get('y1')], key=lambda r:-r['d_w17_y1'])[:10]:
    print(f"  {r['season']} {r['team']:<4} {r['coach']:<20} [{r['bucket']:<11}] {r['y0']['w']:>2}->{r['y1']['w']:<2}  {r['d_w17_y1']:+.2f}")
print('BIGGEST YEAR-1 DROPS:')
for r in sorted([r for r in ACTIVE if r.get('y1')], key=lambda r:r['d_w17_y1'])[:10]:
    print(f"  {r['season']} {r['team']:<4} {r['coach']:<20} [{r['bucket']:<11}] {r['y0']['w']:>2}->{r['y1']['w']:<2}  {r['d_w17_y1']:+.2f}")
