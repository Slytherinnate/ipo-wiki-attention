"""Parse post-offering shares outstanding from cached 424B4 text (data/cache/424b4, no new SEC calls
needed when cached). Market cap = offer price x shares outstanding after the offering (base deal,
pre-greenshoe as stated in the summary). Multiple share classes: summed (flag MULTI_CLASS).
ADS deals: shares are ordinary shares, so cap = offer per ADS x ordinary shares / ADS ratio (flag ADS).
Output data/processed/market_cap.csv (local only). No vendor prices used."""
import re, html, os, pandas as pd, json
NUM = r'(\d{1,3}(?:,\d{3})+|\d{4,})'
WORDN = {'one':1,'two':2,'three':3,'four':4,'five':5,'six':6,'seven':7,'eight':8,'nine':9,'ten':10,'twelve':12,'fifteen':15,'twenty':20,'twenty-five':25,'thirty':30,'forty':40,'fifty':50,'seventy-five':75,'one hundred':100}
def clean(s):
    s = re.sub(r'<[^>]+>', ' ', s); s = html.unescape(s); return re.sub(r'\s+', ' ', s)
ANCH = re.compile(r'outstanding (?:immediately )?(?:after|following|upon)(?: giving effect to| the (?:completion|closing) of)? (?:this|the) (?:initial public )?offering', re.I)
RATIO = re.compile(r'(?:ADSs?|American [Dd]epositary [Ss]hares?)[^.]{0,80}?(?:each\s+)?represent(?:s|ing)?\s+(?:the right to receive\s+)?(one[- ]third|one[- ]half|\d+|' + '|'.join(sorted(WORDN, key=len, reverse=True)) + r')(?:\s*\(\d+\))?\s+(?:of (?:our|an?)\s+)?(?:Class [AB]\s+)?(?:ordinary|common) shares?', re.I)
RATIO2 = re.compile(r'(\d+|' + '|'.join(sorted(WORDN, key=len, reverse=True)) + r')\s+ADSs\s+represent\s+one\s+(?:Class [AB]\s+)?(?:ordinary|common) share', re.I)
def parse(t):
    hits = []
    for m in ANCH.finditer(t):
        lab = t[max(0, m.start()-160):m.start()]
        tail = t[m.end():m.end()+260]
        if re.match(r'[^0-9]{0,160}?(?:excludes|does not include|is based on)', tail, re.I): continue
        n = re.search(NUM, tail)
        if not n or n.start() > 220: continue
        lab = re.split(r'[.;)]\s|\d(?=[^\d]*$)', lab)[-1]
        hits.append((m.start(), lab, int(n.group(1).replace(',', '')), tail[:n.start()]))
    if not hits: return None
    s0 = hits[0][0]; blk = [h for h in hits if h[0] - s0 < 5000]
    full = [h for h in blk if re.search(r'assuming (?:the )?(?:exchange|conversion|redemption) of all', h[3] + h[1], re.I)]
    seen, tot, cls = set(), 0, []
    total = [h for h in blk if re.search(r'\btotal\b', h[1], re.I) or len(re.findall(r'(?:class|series)\s+[a-z0-9]\b', h[1], re.I)) >= 2]
    if full:
        tot = full[0][2]; cls = [f'fully-exchanged:{tot}']; seen = {'full', 'x'}
    elif total:
        tot = total[0][2]; cls = [f'stated-total:{tot}']; seen = {'total', 'x'}
    else:
        for _, lab, n, _t in blk:
            l = lab.lower()
            if re.search(r'\bads|depositary', l): continue
            k = re.search(r'(?:class|series)\s+([a-z0-9])\b', l); k = k.group(1) if k else 'single'
            if k in seen or n in [int(c.split(':')[1]) for c in cls]: continue   # same count repeated for another class = duplicate line
            seen.add(k); tot += n; cls.append(f'{k}:{n}')
    if not tot: return None
    head = t[:600000]; ratio = None
    m = RATIO.search(head)
    if m:
        g = m.group(1).lower().replace('-', ' ')
        ratio = {'one third': 1/3, 'one half': .5}.get(g) or (int(g) if g.isdigit() else WORDN.get(g))
    m2 = RATIO2.search(head)
    if m2:
        g = m2.group(1).lower(); ratio = 1 / (int(g) if g.isdigit() else WORDN[g])
    ads = bool(re.search(r'American Depositary Shares|\bADSs\b', t[:8000]))
    return dict(shares_out_after=tot, classes=' '.join(cls), n_classes=len(seen), ads_listed=ads, ads_ratio=ratio, snippet=t[max(0, s0-80):s0+300])
t = pd.read_parquet('data/processed/analysis_table.parquet'); u = t[t.usable_day30]
d = pd.read_csv('data/universe/ipo_deals_all.csv', dtype=str)[['cik', 'accession']]
u = u.merge(d, on='cik', how='left'); rows = []
for _, r in u.iterrows():
    f = f'data/cache/424b4/edgar_data_{r.cik}_{r.accession}.txt'
    cf = f'/workspace/rev/clean/{r.cik}.txt'
    p = parse(open(cf).read()) if os.path.exists(cf) else None
    row = dict(cik=r.cik, offer_price=float(r.offer_price))
    if p:
        row.update(p); flags = []
        if p['n_classes'] > 1: flags.append('MULTI_CLASS')
        eq = p['shares_out_after']
        if p['ads_listed']:
            flags.append('ADS')
            if p['ads_ratio']: eq = eq / p['ads_ratio']
            else: flags.append('ADS_RATIO_UNKNOWN')
        off = float(r.shares_offered_base or 0)
        if eq < off * 0.999: flags.append('SUSPECT_LT_OFFERED')
        elif off and eq < off * 1.6: flags.append('LOW_POST_TO_OFFERED')   # likely an Up-C/multi-class structure where only the public class was read
        row['market_cap'] = None if ({'ADS_RATIO_UNKNOWN', 'SUSPECT_LT_OFFERED', 'LOW_POST_TO_OFFERED'} & set(flags)) else float(r.offer_price) * eq
        row['cap_flags'] = ' '.join(flags)
    else: row['cap_flags'] = 'NOT_PARSED'
    rows.append(row)
o = pd.DataFrame(rows); o.to_csv('data/processed/market_cap.csv', index=False)
print(len(o), 'parsed', o.market_cap.notna().sum(), o.cap_flags.str.split().explode().value_counts().to_dict())
print(o.market_cap.describe())
