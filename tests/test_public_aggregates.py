"""Run: python3 tests/test_public_aggregates.py. Fails if any public CSV could expose a small group or a firm."""
import glob, re, pandas as pd
import warnings; warnings.filterwarnings("ignore")
BAD_COL = re.compile(r'ticker|symbol|cik|name|legal|title|permaticker|price|close|open|accession|url', re.I)
files = glob.glob('data/public/*.csv'); assert files
tick = pd.read_parquet('data/processed/analysis_table.parquet').tickers.dropna().str.split().explode()
tick = set(t for t in tick if len(t) >= 3)
for f in files:
    d = pd.read_csv(f)
    bad = [c for c in d.columns if BAD_COL.search(c)]
    assert not bad, (f, bad)
    assert 'n' in d and 'suppressed' in d, f
    live = d[~d.suppressed.astype(bool)]
    assert (live.n >= 15).all(), (f, live[live.n < 15])
    for c in [c for c in d.columns if c.startswith('n_') and c != 'n']: assert ((live[c] >= 15) | live[c].isna()).all() or 'meta' in f, (f, c)
    sup = d[d.suppressed.astype(bool)]
    num = [c for c in d.select_dtypes('number').columns if c not in ('rel_day', 'bins', 'bin', 'pop_quintile', 'n_first_day')]
    assert sup[num].isna().all().all(), (f, 'suppressed rows carry values')
    strs = set(d.select_dtypes('object').stack().astype(str))
    assert not (strs & tick), (f, 'ticker-like value', strs & tick)
    print('OK', f, len(d), 'rows,', len(sup), 'suppressed')
print('ALL PASS')
