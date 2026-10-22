"""Adds (Caleb, 2026-10-22): pop_close_eq_offer flag -> pop set missing (day-30 kept);
capped (1st/99th pct winsorised) and log returns for regressions; scan variables
(attention trend, exchange, foreign issuer, article creation date via Wikipedia API, cached)."""
import pandas as pd,numpy as np,json,os,sys,datetime as dt
sys.path.insert(0,'scripts');import check_titles_v2 as v2
t=pd.read_parquet('data/processed/analysis_table.parquet')
if 'pop_raw' not in t: t['pop_raw']=t['pop']
t['pop_close_eq_offer']=t.pop_raw.eq(0)&t.usable_day1
t['pop']=t.pop_raw.mask(t.pop_close_eq_offer)
t['usable_day1']=t.us_ipo_set&t.has_views&t.returns_status.isin(['OK','OK_DATE_UNCHECKED'])&t['pop'].notna()
u=t.usable_day30
for c in ('pop','ret30'):
    lo,hi=t.loc[u,c].quantile([.01,.99])
    t[c+'_capped']=t[c].clip(lo,hi); t[c+'_log']=np.log1p(t[c])
# views-based scan variables
for c in t.cik[t.has_views.fillna(False)]:
    v=pd.read_csv(f'data/processed/analysis_views/{c}.csv')
    s=lambda a,b:v[(v.rel_day>=a)&(v.rel_day<=b)].views.sum()
    t.loc[t.cik==c,'attn_trend']=(s(-30,-1)+1)/((s(-120,-31)+1)/3)
t['exchange']=np.where(t.exchanges.fillna('').str.contains('NYSE'),'NYSE',np.where(t.exchanges.fillna('').str.contains('Nasdaq'),'Nasdaq','Other'))
t['foreign_issuer']=t.foreign_flag.eq('yes')
fn='data/cache/article_created.json';cr=json.load(open(fn)) if os.path.exists(fn) else {}
for ti in t.title[~t.title.isin(cr)]:
    d=v2.get(v2.API,{'action':'query','titles':ti,'redirects':1,'prop':'revisions','rvlimit':1,'rvdir':'newer','rvprop':'timestamp','format':'json','formatversion':2})
    try: cr[ti]=d['query']['pages'][0]['revisions'][0]['timestamp'][:10]
    except Exception: cr[ti]=None
    json.dump(cr,open(fn,'w'))
t['article_created']=t.title.map(cr)
t['article_age_days']=(pd.to_datetime(t.anchor_date)-pd.to_datetime(t.article_created)).dt.days
t.to_parquet('data/processed/analysis_table.parquet',index=False)
w=t[t.usable_day30]
print('flagged',t.pop_close_eq_offer.sum(),'usable day1',t.usable_day1.sum(),'day30',t.usable_day30.sum(),'median ret30',repr(w.ret30.median()),'created missing',w.article_created.isna().sum())
