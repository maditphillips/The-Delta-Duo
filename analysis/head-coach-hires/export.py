exec(open('analyze.py').read().split("def row(")[0])
import json
B=['OC','DC','Prev NFL HC','College','Other']
def agg(g,key,yr):
    v=[r[f'{key}_y{yr}'] for r in g if r.get(f'y{yr}')]
    if not v: return None
    lo,hi=ci95(v)
    return {'n':len(v),'mean':round(mean(v),2),'med':round(st.median(v),2),
            'lo':round(lo,2),'hi':round(hi,2),'pct':round(100*sum(1 for x in v if x>0)/len(v))}
out={'buckets':{},'all':{},'era':{},'meta':{}}
for key in ('d_wins','d_w17','r_w17','d_pf','d_pa','d_net','r_net'):
    out['all'][key]={yr:agg(ACTIVE,key,yr) for yr in (1,2,3)}
for b in B:
    g=[r for r in ACTIVE if r['bucket']==b]
    out['buckets'][b]={'n':len(g),'prevW':round(mean([r['y0']['w'] for r in g]),2),
        'prevPct':round(mean([r['y0']['win_pct'] for r in g]),3)}
    for key in ('d_wins','d_w17','r_w17','d_pf','d_pa','d_net','r_net'):
        out['buckets'][b][key]={yr:agg(g,key,yr) for yr in (1,2,3)}
    for yr in (2,3):
        gg=[r for r in g if r.get(f'y{yr}')]
        out['buckets'][b][f'kept_y{yr}']=round(100*sum(r[f'kept_y{yr}'] for r in gg)/len(gg))
for yr in (2,3):
    gg=[r for r in ACTIVE if r.get(f'y{yr}')]
    out['all'][f'kept_y{yr}']=round(100*sum(r[f'kept_y{yr}'] for r in gg)/len(gg))
for lo,hi in ((2000,2008),(2009,2016),(2017,2025)):
    k=f'{lo}-{hi}'; out['era'][k]={}
    for b in ['ALL']+B:
        g=[r for r in ACTIVE if lo<=r['season']<=hi and r.get('y1') and (b=='ALL' or r['bucket']==b)]
        out['era'][k][b]={'n':len(g),'raw':round(mean([r['d_w17_y1'] for r in g]),2),
            'resid':round(mean([r['r_w17_y1'] for r in g]),2),
            'dnet':round(mean([r['d_net_y1'] for r in g]),2),
            'dpf':round(mean([r['d_pf_y1'] for r in g]),2),
            'dpa':round(mean([r['d_pa_y1'] for r in g]),2)}
# modern OC roster
mods=sorted([r for r in ACTIVE if r['season']>=2017 and r['bucket']=='OC' and r.get('y1')],
            key=lambda r:-r['d_w17_y1'])
out['modern_oc']=[{'season':r['season'],'team':r['team'],'coach':r['coach'],
    'w0':r['y0']['w'],'g0':r['y0']['g'],'w1':r['y1']['w'],'g1':r['y1']['g'],
    'pace':round(r['d_w17_y1'],2),'resid':round(r['r_w17_y1'],2),
    'dnet':round(r['d_net_y1'],2)} for r in mods]
out['meta']={'n_hires':len(ACTIVE),'n_excluded':len(recs)-len(ACTIVE),
    'seasons':'2000-2025','n_control':len(ctrl),
    'model':{k:[round(a,4),round(b,4)] for k,(a,b) in MODELS.items()},
    'share_ge3':round(100*sum(1 for r in ACTIVE if r.get('y1') and r['d_w17_y1']>=3)/
                      sum(1 for r in ACTIVE if r.get('y1'))),
    'share_le0':round(100*sum(1 for r in ACTIVE if r.get('y1') and r['d_w17_y1']<=0)/
                      sum(1 for r in ACTIVE if r.get('y1')))}
# modern OC vs rest significance
def welch(a,b):
    ma,mb=mean(a),mean(b); va,vb=st.variance(a),st.variance(b)
    se=math.sqrt(va/len(a)+vb/len(b)); t=(ma-mb)/se
    return round(t,2), round(2*(1-0.5*(1+math.erf(abs(t)/math.sqrt(2)))),4)
mo=[r['r_w17_y1'] for r in ACTIVE if r['season']>=2017 and r['bucket']=='OC' and r.get('y1')]
me=[r['r_w17_y1'] for r in ACTIVE if r['season']>=2017 and r['bucket']!='OC' and r.get('y1')]
oo=[r['r_w17_y1'] for r in ACTIVE if r['season']<2017 and r['bucket']=='OC' and r.get('y1')]
out['meta']['modern_oc_vs_rest']=welch(mo,me)
out['meta']['modern_oc_vs_old_oc']=welch(mo,oo)
out['meta']['modern_oc_y']= {yr: round(mean([r[f'd_w17_y{yr}'] for r in ACTIVE
    if r['season']>=2017 and r['bucket']=='OC' and r.get(f'y{yr}')]),2) for yr in (1,2,3)}
json.dump(out, open('report_data.json','w'), indent=1)
print(json.dumps(out['meta'], indent=1))
print('buckets:', {b: out['buckets'][b]['n'] for b in B})
