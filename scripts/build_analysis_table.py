"""Step 3: analysis_set + pageview windows + local Tiingo-derived returns (ipo_returns.csv) + offer data.
Local only. Returns used as outcomes only (no validation use). usable_* require returns_status in
OK/OK_DATE_UNCHECKED and non-null return."""
import pandas as pd,numpy as np
s=pd.read_csv('data/processed/analysis_set.csv',dtype={'cik':str})
m=pd.read_csv('data/processed/analysis_views_meta.csv',dtype={'cik':str})
r=pd.read_csv('data/local_only/ipo_returns.csv',dtype={'cik':str})[['cik','offer_price','pop','ret30','day30_date','returns_status','flags','first_trade_date']].rename(columns={'first_trade_date':'ret_first_trade_date','flags':'ret_flags'})
o=pd.read_csv('data/universe/titles_v2_all.csv',dtype={'cik':str})[['cik','gross_proceeds','shares_offered_base','underwriters_on_cover','deal_flags']]
rows=[]
for c in s.cik:
    try: v=pd.read_csv(f'data/processed/analysis_views/{c}.csv')
    except FileNotFoundError: rows.append({'cik':c});continue
    g=lambda a,b:int(v[(v.rel_day>=a)&(v.rel_day<=b)].views.sum())
    rows.append({'cik':c,'views_pre120':g(-120,-1),'views_pre30':g(-30,-1),'views_pre7':g(-7,-1),'views_day0':g(0,0),'views_post30':g(1,30),'views_post60':g(1,60)})
t=s.merge(m.drop(columns=['final_title'],errors='ignore'),on='cik',how='left').merge(pd.DataFrame(rows),on='cik',how='left').merge(r,on='cik',how='left').merge(o,on='cik',how='left')
ok=t.returns_status.isin(['OK','OK_DATE_UNCHECKED'])
t['has_views']=t.status.eq('OK')
t['usable_day1']=t.us_ipo_set&t.has_views&ok&t['pop'].notna()
t['usable_day30']=t.us_ipo_set&t.has_views&ok&t.ret30.notna()
t['date_mismatch']=t.ret_first_trade_date.notna()&t.first_trade_date.notna()&(t.ret_first_trade_date!=t.first_trade_date)
t['zero_pre_days']=t.pre_days_with_data.fillna(0).eq(0)
t.to_parquet('data/processed/analysis_table.parquet',index=False)
print(len(t),'views',t.has_views.sum(),'ret rows',t.returns_status.notna().sum(),t.returns_status.value_counts(dropna=False).to_dict())
print('day1',t.usable_day1.sum(),'day30',t.usable_day30.sum(),'both',(t.usable_day1&t.usable_day30).sum(),'date_mismatch',t.date_mismatch.sum(),'OK_DATE_UNCHECKED used',(t.usable_day1&t.returns_status.eq('OK_DATE_UNCHECKED')).sum())
