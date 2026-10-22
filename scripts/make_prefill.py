#!/usr/bin/env python3
"""Build data/universe/prefill.csv: Wikidata CIK check, infobox ticker check, suggested first-trade date.
Sources: enwiki API, Wikidata API, SEC EDGAR full-text search (efts). Raw responses cached in verify/prefill_cache/."""
import csv, json, re, os, time, hashlib, datetime as dt, urllib.parse, urllib.request
import pandas as pd
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, 'verify/prefill_cache'); os.makedirs(CACHE, exist_ok=True)
UA = 'Caleb Havens calebhavens08@gmail.com'
_last = {}
def get(url, host_delay):
    key = hashlib.sha1(url.encode()).hexdigest()
    p = os.path.join(CACHE, key + '.txt')
    if os.path.exists(p): return open(p, encoding='utf-8').read()
    h = urllib.parse.urlparse(url).netloc
    w = host_delay - (time.time() - _last.get(h, 0))
    if w > 0: time.sleep(w)
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept-Encoding': 'identity'})
            txt = urllib.request.urlopen(req, timeout=40).read().decode('utf-8', 'replace'); break
        except Exception as e:
            code = getattr(e, 'code', None)
            if code == 404: txt = ''; break
            time.sleep(2 * (attempt + 1)); txt = None
    _last[h] = time.time()
    if txt is None: return None
    open(p, 'w', encoding='utf-8').write(txt); return txt

def wapi(params):
    params = dict(params, format='json', formatversion=2)
    return json.loads(get('https://en.wikipedia.org/w/api.php?' + urllib.parse.urlencode(params), 0.3) or '{}')

df = pd.read_csv(os.path.join(ROOT, 'data/universe/review_worksheet.csv'), dtype=str)
def title_of(r):
    for c in ('final_title', 'deep_best_title'):
        if isinstance(r[c], str) and r[c].strip(): return r[c].strip()
    if isinstance(r['deep_candidates'], str) and r['deep_candidates'].strip():
        return re.sub(r'\s*\[[A-Z_]+\]$', '', re.split(r'\s*[|;]\s*', r['deep_candidates'].strip())[0]).strip()
    return None
df['t'] = df.apply(title_of, axis=1)

# ---- Wikipedia: resolve, pageprops, wikitext (batches of 50)
info = {}
titles = sorted(set(df.t.dropna()))
for i in range(0, len(titles), 50):
    b = titles[i:i+50]
    j = wapi({'action': 'query', 'titles': '|'.join(b), 'redirects': 1, 'prop': 'pageprops|revisions', 'rvprop': 'content', 'rvslots': 'main', 'ppprop': 'wikibase_item|disambiguation'})
    q = j.get('query', {}); m = {}
    for n in q.get('normalized', []): m[n['from']] = n['to']
    rd = {x['from']: x['to'] for x in q.get('redirects', [])}
    pages = {p['title']: p for p in q.get('pages', [])}
    for t in b:
        t2 = m.get(t, t); t3 = rd.get(t2, t2)
        p = pages.get(t3)
        if not p or p.get('missing'): info[t] = {'page_resolved_title': ''}; continue
        pp = p.get('pageprops', {})
        wt = p['revisions'][0]['slots']['main']['content'] if p.get('revisions') else ''
        info[t] = {'page_resolved_title': t3, 'page_is_disambig': 'yes' if 'disambiguation' in pp else 'no', 'wd_qid': pp.get('wikibase_item', ''), 'wt': wt}
# page creation (one per title)
for t, d in info.items():
    if not d.get('page_resolved_title'): continue
    j = wapi({'action': 'query', 'titles': d['page_resolved_title'], 'prop': 'revisions', 'rvlimit': 1, 'rvdir': 'newer', 'rvprop': 'timestamp'})
    try: d['page_created'] = j['query']['pages'][0]['revisions'][0]['timestamp'][:10]
    except Exception: d['page_created'] = ''
# ---- Wikidata
qids = sorted({d['wd_qid'] for d in info.values() if d.get('wd_qid')})
wd = {}
for i in range(0, len(qids), 50):
    j = json.loads(get('https://www.wikidata.org/w/api.php?' + urllib.parse.urlencode({'action': 'wbgetentities', 'ids': '|'.join(qids[i:i+50]), 'props': 'claims', 'format': 'json'}), 0.5) or '{}')
    for q, e in j.get('entities', {}).items():
        cl = e.get('claims', {})
        ciks = [c['mainsnak'].get('datavalue', {}).get('value', '') for c in cl.get('P5531', [])]
        tk = []
        for c in cl.get('P414', []):
            for s in c.get('qualifiers', {}).get('P249', []):
                v = s.get('datavalue', {}).get('value');
                if v: tk.append(v)
        wd[q] = (ciks, tk)
# ---- infobox
TPL = r'\{\{\s*(NASDAQ|Nasdaq|NYSE|NYSE American|NYSE American|NYSE Arca|NYSE MKT|AMEX|NYSEAmerican|OTC Pink|LSE|HKEX|SEHK|TSX|ASX)\s*\|\s*([A-Za-z0-9.\-]+)'
def infobox(wt):
    m = re.search(r'\|\s*traded_as\s*=(.*?)(?=\n\s*\|\s*[a-z_]+\s*=|\n\}\})', wt or '', re.S)
    seg = m.group(1) if m else ''
    hits = re.findall(TPL, seg, re.I) or re.findall(TPL, (wt or '')[:6000], re.I)
    ex = []; tk = []
    for e, t in hits:
        if t.upper() not in tk: tk.append(t.upper()); ex.append(e.upper())
    if not tk and seg:  # plain "NASDAQ: XYZ"
        for e, t in re.findall(r'(NASDAQ|NYSE)\s*:\s*\[*([A-Z.]{1,6})', seg, re.I):
            tk.append(t.upper()); ex.append(e.upper())
    return tk, ex
def norm(t): return re.sub(r'[.\-]', '', t.upper())

# ---- EDGAR
MON = r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s+(\d{4})'
Q = '"begin trading" OR "commence trading" OR "began trading" OR "expected to begin trading" OR "approved for listing"'
PAT = re.compile(r'(?:begin|began|commence|commenced|start|started)\s+trading[^.]{0,160}?\bon\s+(?:\w+,\s+)?' + MON, re.I)
def pdate(m): return dt.datetime.strptime(f'{m[0]} {m[1]} {m[2]}', '%B %d %Y').date()
HOL = {dt.date(*x) for x in [(2015,1,1),(2015,1,19),(2015,2,16),(2015,4,3),(2015,5,25),(2015,7,3),(2015,9,7),(2015,11,26),(2015,12,25),(2016,1,1),(2016,1,18),(2016,2,15),(2016,3,25),(2016,5,30),(2016,7,4),(2016,9,5),(2016,11,24),(2016,12,26),(2017,1,2),(2017,1,16),(2017,2,20),(2017,4,14),(2017,5,29),(2017,7,4),(2017,9,4),(2017,11,23),(2017,12,25),(2018,1,1),(2018,1,15),(2018,2,19),(2018,3,30),(2018,5,28),(2018,7,4),(2018,9,3),(2018,11,22),(2018,12,5),(2018,12,25),(2019,1,1),(2019,1,21),(2019,2,18),(2019,4,19),(2019,5,27),(2019,7,4),(2019,9,2),(2019,11,28),(2019,12,25),(2020,1,1),(2020,1,20),(2020,2,17),(2020,4,10),(2020,5,25),(2020,7,3),(2020,9,7),(2020,11,26),(2020,12,25),(2021,1,1),(2021,1,18),(2021,2,15),(2021,4,2),(2021,5,31),(2021,7,5),(2021,9,6),(2021,11,25),(2021,12,24),(2022,1,17),(2022,2,21),(2022,4,15),(2022,5,30),(2022,6,20),(2022,7,4),(2022,9,5),(2022,11,24),(2022,12,26),(2023,1,2),(2023,1,16),(2023,2,20),(2023,4,7),(2023,5,29),(2023,6,19),(2023,7,4),(2023,9,4),(2023,11,23),(2023,12,25),(2024,1,1),(2024,1,15),(2024,2,19),(2024,3,29),(2024,5,27),(2024,6,19),(2024,7,4),(2024,9,2),(2024,11,28),(2024,12,25),(2025,1,1),(2025,1,9),(2025,1,20),(2025,2,17),(2025,4,18),(2025,5,26),(2025,6,19),(2025,7,4),(2025,9,1),(2025,11,27),(2025,12,25)]}
def next_td(d):
    d += dt.timedelta(1)
    while d.weekday() >= 5 or d in HOL: d += dt.timedelta(1)
    return d
def strip(h): return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', re.sub(r'&nbsp;|&#160;|&#xa0;', ' ', h, flags=re.I)))
def edgar(cik, d0):
    out = {'sugg_trade_date': '', 'sugg_trade_source': '', 'sugg_trade_source_type': '', 'sugg_trade_snippet': ''}
    if not d0: return out
    d = dt.date.fromisoformat(d0)
    url = 'https://efts.sec.gov/LATEST/search-index?' + urllib.parse.urlencode({'q': Q, 'ciks': cik.zfill(10), 'dateRange': 'custom', 'startdt': str(d - dt.timedelta(30)), 'enddt': str(d + dt.timedelta(10))})
    txt = get(url, 0.25)
    if not txt: out['sugg_trade_source_type'] = 'error'; return out
    hits = json.loads(txt).get('hits', {}).get('hits', [])
    def rank(h):
        f = h['_source'].get('form', ''); return (0 if f in ('8-K', '6-K') else 1 if f.startswith('424B') else 2, h['_source'].get('file_date', ''))
    hits.sort(key=rank)
    pros = None
    for h in hits:
        s = h['_source']; adsh = s['adsh']; fn = h['_id'].split(':', 1)[1]
        doc = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{adsh.replace('-', '')}/{fn}"
        f = s.get('form', '')
        if f in ('8-K', '6-K', '8-K/A', '6-K/A') or f.startswith('424B'):
            body = get(doc, 0.25)
            if body is None: continue
            t = strip(body)
            m = PAT.search(t)
            if m and f[:1] in '86':
                out.update(sugg_trade_date=str(pdate(m.groups())), sugg_trade_source=doc, sugg_trade_source_type=f, sugg_trade_snippet=m.group(0)[:200]); return out
            if f.startswith('424B') and not pros:
                pm = re.search(r'(?:prospectus|the date of this prospectus is)\s+(?:is\s+)?dated\s+' + MON, t, re.I) or re.search(r'The date of this prospectus is\s+' + MON, t, re.I)
                if pm: pros = (pm, doc)
    if pros:
        pm, doc = pros; pd_ = pdate(pm.groups()[-3:])
        out.update(sugg_trade_date=str(next_td(pd_)), sugg_trade_source=doc, sugg_trade_source_type='prospectus+1', sugg_trade_snippet=pm.group(0)[:200])
    return out

rows = []
for n, r in df.iterrows():
    cik = str(int(float(r.cik))); o = {'cik': cik, 'row_type': r.row_type, 'title_checked': r.t or ''}
    d = info.get(r.t, {}) if r.t else {}
    o['page_resolved_title'] = d.get('page_resolved_title', ''); o['page_is_disambig'] = d.get('page_is_disambig', ''); o['page_created'] = d.get('page_created', '')
    q = d.get('wd_qid', ''); o['wd_qid'] = q
    ciks, wtk = wd.get(q, ([], []))
    o['wd_sec_cik'] = ';'.join(ciks); o['wd_ticker'] = ';'.join(dict.fromkeys(wtk))
    o['wd_cik_match'] = 'none' if not ciks else ('yes' if cik.zfill(10) in [c.zfill(10) for c in ciks] else 'no')
    tk, ex = infobox(d.get('wt', ''))
    o['ib_ticker'] = ';'.join(tk); o['ib_exchange'] = ';'.join(ex)
    mine = {norm(x) for x in re.split(r'[;,|/ ]+', str(r.tickers or '')) if x and x != 'nan'}
    o['ib_ticker_match'] = 'none' if not tk else ('yes' if mine & {norm(x) for x in tk} else 'no')
    d0 = r.date_to_check if isinstance(r.date_to_check, str) and r.date_to_check else (r.filing_date_424b4 if isinstance(r.filing_date_424b4, str) else '')
    e = edgar(cik, d0[:10] if d0 else ''); o.update(e)
    o['sugg_matches_date_to_check'] = '' if not (e['sugg_trade_date'] and isinstance(r.date_to_check, str) and r.date_to_check) else ('yes' if e['sugg_trade_date'] == r.date_to_check[:10] else 'no')
    o['sugg_matches_ref_date'] = '' if not (e['sugg_trade_date'] and d0) else ('yes' if e['sugg_trade_date'] == d0[:10] else 'no')
    rows.append(o)
    if n % 50 == 0: print(n, flush=True)
pd.DataFrame(rows).to_csv(os.path.join(ROOT, 'data/universe/prefill.csv'), index=False)
print('done')
