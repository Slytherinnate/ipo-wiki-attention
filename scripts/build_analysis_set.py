"""Step 1: final matched set = AUTO_KEEP rows (titles_v2_all.final_title) + worksheet keeps
(OneDrive review_worksheet.xlsx eTag>=183, chosen_title). Worksheet wins on overlap (16 SECTOR_ONLY).
Anchor = first_trade_date (already re-anchored per build-report-2026-10-20) else 424B4 filing date.
Output data/processed/analysis_set.csv (local only)."""
import openpyxl,warnings,pandas as pd,sys
warnings.filterwarnings('ignore')
X=sys.argv[1] if len(sys.argv)>1 else 'data/universe/onedrive_f4.xlsx'
t=pd.read_csv('data/universe/titles_v2_all.csv',dtype=str)
R=list(openpyxl.load_workbook(X,read_only=True)['review'].iter_rows(values_only=True))
w=pd.DataFrame(R[1:],columns=R[0]);w['cik']=w.cik.astype(str)
wk=w[w.decision=='keep'][['cik','chosen_title','review_code','notes','tasks']].rename(columns={'chosen_title':'title'})
wk['source']='worksheet'
a=t[(t.decision=='AUTO_KEEP')&~t.cik.isin(w.cik)][['cik','final_title']].rename(columns={'final_title':'title'})
a['source']='auto';a['review_code']='AUTO_KEEP'
s=pd.concat([a,wk],ignore_index=True)
s=s.merge(t[['cik','year','legal_name','tickers','exchanges','sector','filing_date_424b4','first_trade_date','first_trade_conf','foreign_flag','universe_flags']],on='cik',how='left')
s['anchor_date']=s.first_trade_date.fillna(s.filing_date_424b4)
s['anchor_source']=s.first_trade_date.map(lambda x:'first_trade_date' if isinstance(x,str) else 'filing_date_424b4')
s['adr_only']=s.notes.fillna('').str.contains('ADR/ADS set only')
s['us_ipo_set']=~s.adr_only
assert not s.cik.duplicated().any() and s.title.notna().all() and not s.title.str.contains('_').any()
s.drop(columns=['notes']).to_csv('data/processed/analysis_set.csv',index=False)
print(len(s),s.source.value_counts().to_dict(),'adr_only',s.adr_only.sum(),'dup titles',s.title.duplicated().sum())
