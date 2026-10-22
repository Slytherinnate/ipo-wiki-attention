"""Step 2: daily pageviews for analysis_set.csv. Method = match_all.py: article + its redirects
(first MAX_REDIRECTS) summed; plus explicit '[bot] old title: X' from worksheet notes.
Window anchor-120..anchor+60, missing days = 0. Uses match_all rate limiter (3 req/s, UA) and
data/cache/pv. Cache ranges end 2025-12-31; titles needing later days are refetched to 2026-10-20.
Output data/processed/analysis_views/<CIK>.csv + analysis_views_meta.csv."""
import os,sys,re,json,csv,datetime as dt
from collections import defaultdict
from urllib.parse import quote
sys.path.insert(0,'scripts');import match_all as M, check_titles_v2 as v2
import pandas as pd,openpyxl,warnings;warnings.filterwarnings('ignore')
s=pd.read_csv('data/processed/analysis_set.csv',dtype=str)
R=list(openpyxl.load_workbook('data/universe/onedrive_f4.xlsx',read_only=True)['review'].iter_rows(values_only=True))
notes={str(r[6]):str(r[40] or '') for r in R[1:]}
OUT='data/processed/analysis_views';os.makedirs(OUT,exist_ok=True)
stats=defaultdict(int);meta=[]
def views(title,need):
    fn=os.path.join(M.PVC,title.replace("/","%2F")[:180]+".json")
    d=json.load(open(fn)) if os.path.exists(fn) else None
    if d is not None and (need<='20251231'): stats['cache_hit']+=1;return d
    if d is not None and d and max(d)>=need: stats['cache_hit']+=1;return d
    t=quote(title.replace(" ","_"),safe="")
    r=v2.get(f"{v2.PV}/{t}/daily/2015070100/2026102000")
    stats['fetched']+=1
    if r is None: stats['fetch_empty_or_404']+=1;d2={}
    else: d2={i["timestamp"][:8]:i["views"] for i in r["items"]}
    json.dump(d2,open(fn,"w"));return d2
for n,r in s.iterrows():
    a=dt.date.fromisoformat(r.anchor_date);need=(a+dt.timedelta(days=60)).strftime('%Y%m%d')
    try: info=v2.page_details(r.title)
    except Exception as e: info=None
    if not info: stats['page_fail']+=1;meta.append(dict(cik=r.cik,status='PAGE_FAIL'));continue
    ts=[info['final_title']]+info['redirects'][:v2.MAX_REDIRECTS]
    for o in re.findall(r'\[bot\] old title: ([^(|]+?)\s*(?:\(|\||$)',notes.get(r.cik,'')):
        if o not in ts: ts.append(o)
    tot=defaultdict(int)
    for t in ts:
        for k,v in views(t,need).items(): tot[k]+=v
    days=[a+dt.timedelta(days=k) for k in range(-120,61)]
    with open(f'{OUT}/{r.cik}.csv','w',newline='') as f:
        w=csv.writer(f);w.writerow(['date','rel_day','views'])
        for k,d in zip(range(-120,61),days): w.writerow([d.isoformat(),k,tot.get(d.strftime('%Y%m%d'),0)])
    first=min(tot) if tot else ''
    meta.append(dict(cik=r.cik,status='OK' if tot else 'NO_VIEWS',final_title=info['final_title'],n_titles=len(ts),
        n_redirects_total=len(info['redirects']),first_data_date=first,
        pre_days_with_data=sum(1 for k,d in zip(range(-120,61),days) if k<0 and d.strftime('%Y%m%d')>=(first or '99'))))
    if n%25==0: print(n,dict(stats),flush=True)
pd.DataFrame(meta).to_csv('data/processed/analysis_views_meta.csv',index=False)
print('DONE',dict(stats))
