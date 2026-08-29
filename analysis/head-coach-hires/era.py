exec(open('analyze.py').read().split("def row(")[0])
print(f"{'Era':<12}{'Group':<13}{'n':>4}{'prevW':>7}{'Y1 raw':>9}{'Y1 resid':>10}{'Y1 dNet':>9}{'Y1 dPF':>8}{'Y1 dPA':>8}")
print('-'*80)
for lo,hi in ((2000,2008),(2009,2016),(2017,2025)):
    for b in ('ALL','OC','DC','Prev NFL HC','College','Other'):
        g=[r for r in ACTIVE if lo<=r['season']<=hi and r.get('y1') and (b=='ALL' or r['bucket']==b)]
        if not g: continue
        print(f"{str(lo)+'-'+str(hi):<12}{b:<13}{len(g):>4}{mean([r['y0']['w'] for r in g]):>7.1f}"
              f"{mean([r['d_w17_y1'] for r in g]):>+9.2f}{mean([r['r_w17_y1'] for r in g]):>+10.2f}"
              f"{mean([r['d_net_y1'] for r in g]):>+9.2f}{mean([r['d_pf_y1'] for r in g]):>+8.2f}{mean([r['d_pa_y1'] for r in g]):>+8.2f}")
    print('-'*80)

# significance of modern OC vs modern everyone-else
def welch(a,b):
    ma,mb=mean(a),mean(b); va,vb=st.variance(a),st.variance(b)
    se=math.sqrt(va/len(a)+vb/len(b)); t=(ma-mb)/se
    return t, 2*(1-0.5*(1+math.erf(abs(t)/math.sqrt(2))))
mo=[r['r_w17_y1'] for r in ACTIVE if r['season']>=2017 and r['bucket']=='OC' and r.get('y1')]
me=[r['r_w17_y1'] for r in ACTIVE if r['season']>=2017 and r['bucket']!='OC' and r.get('y1')]
t,p=welch(mo,me)
print(f"\n2017-2025 OC (n={len(mo)}, resid {mean(mo):+.2f}) vs all other 2017-25 hires (n={len(me)}, resid {mean(me):+.2f}): t={t:+.2f} p={p:.4f}")
oo=[r['r_w17_y1'] for r in ACTIVE if r['season']<2017 and r['bucket']=='OC' and r.get('y1')]
t,p=welch(mo,oo)
print(f"2017-2025 OC vs 2000-2016 OC (n={len(oo)}, resid {mean(oo):+.2f}): t={t:+.2f} p={p:.4f}")
# does the modern OC edge persist to Y2/Y3?
for yr in (1,2,3):
    g=[r for r in ACTIVE if r['season']>=2017 and r['bucket']=='OC' and r.get(f'y{yr}')]
    print(f"  2017-25 OC  Y{yr}: n={len(g):>2}  raw {mean([r[f'd_w17_y{yr}'] for r in g]):+.2f}  resid {mean([r[f'r_w17_y{yr}'] for r in g]):+.2f}")
