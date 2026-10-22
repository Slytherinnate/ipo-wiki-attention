"""Build data/public/*.csv: aggregates only, every published group n >= 15.
Reads local data/processed/analysis_table.parquet (never published). Groups with n < 15 are
written as a row with suppressed=True and every value (including n) blank. Precomputes both
INCLUDE_NO_ARTICLE settings (column include_no_article). No names, tickers, CIKs, prices or per-firm rows."""
import numpy as np, pandas as pd, statsmodels.formula.api as smf, os
MIN_N = 15
OUT = 'data/public'; os.makedirs(OUT, exist_ok=True)
t = pd.read_parquet('data/processed/analysis_table.parquet')
df = t[t.usable_day30].copy()
# Per-firm daily averages so before / IPO day / after are on the same per-day scale.
# Published values are medians of these per-firm daily averages (days -30..-1, day 0, days +1..+30).
df['daily_pre'] = df.views_pre30 / 30; df['daily_day0'] = df.views_day0; df['daily_post'] = df.views_post30 / 30
df['log_pre30'] = np.log1p(df.views_pre30); df['log_offer'] = np.log(df.offer_price.astype(float))
df['foreign'] = df.foreign_issuer.astype(int); df['no_article'] = (~df.has_pre_ipo_article).astype(int)
df['year'] = df.year.astype(int).astype(str)
df['article_group'] = np.select([~df.has_pre_ipo_article, df.views_pre30 == 0], ['No article before IPO', 'Article, zero pre-IPO views'], 'Article with pre-IPO views')
vc = df.sector.value_counts(); df['sector_group'] = df.sector.where(df.sector.map(vc) >= MIN_N, 'Other')
SETTINGS = {True: df, False: df[df.has_pre_ipo_article]}

def finish(rows, name, value_cols):
    d = pd.DataFrame(rows)
    small = d.n < MIN_N
    d['suppressed'] = small
    d.loc[small, value_cols + ['n']] = np.nan
    assert (d.loc[~d.suppressed, 'n'] >= MIN_N).all(), name
    d.to_csv(f'{OUT}/{name}.csv', index=False); return d

def groups(d):
    yield 'All', 'All', d
    for dim in ('sector_group', 'year', 'article_group'):
        for k, g in d.groupby(dim): yield dim.replace('_group', ''), k, g

# 1 attention curve
views = {c: pd.read_csv(f'data/processed/analysis_views/{c}.csv') for c in df.cik}
rows = []
for inc, d in SETTINGS.items():
    for dim, k, g in groups(d):
        if dim == 'year': continue
        m = pd.concat([views[c] for c in g.cik]).groupby('rel_day').views
        for day, med in m.median().items():
            rows.append(dict(include_no_article=inc, dimension=dim, group=k, rel_day=day, n=len(g), median_views=med, p25_views=m.quantile(.25)[day], p75_views=m.quantile(.75)[day]))
finish(rows, 'attention_curve', ['median_views', 'p25_views', 'p75_views'])

# 2 baselines
V = ['mean', 'median', 'sd', 'p25', 'p75', 'iqr', 'pct_positive']
rows = []
for inc, d in SETTINGS.items():
    for dim, k, g in groups(d):
        for y, lab in (('pop', 'first_day'), ('ret30', 'day_30')):
            x = g[y].dropna()
            rows.append(dict(include_no_article=inc, dimension=dim, group=k, outcome=lab, n=len(x), mean=x.mean(), median=x.median(), sd=x.std(),
                             p25=x.quantile(.25), p75=x.quantile(.75), iqr=x.quantile(.75)-x.quantile(.25), pct_positive=100*(x > 0).mean()))
finish(rows, 'return_baselines', V)

# 3 binned attention vs returns (bins by rank so tied zeros split evenly; bins with n<15 suppressed)
rows = []
for inc, d in SETTINGS.items():
    for nb in (5, 10):
        for y, lab in (('pop', 'first_day'), ('ret30', 'day_30')):
            g = d.dropna(subset=[y]).copy()
            g['bin'] = pd.qcut(g.log_pre30.rank(method='first'), nb, labels=False) + 1
            for b, gb in g.groupby('bin'):
                rows.append(dict(include_no_article=inc, bins=nb, bin=int(b), outcome=lab, n=len(gb), median_daily_views_pre=gb.daily_pre.median(),
                                 median_return=gb[y].median(), mean_return=gb[y].mean(), p25_return=gb[y].quantile(.25), p75_return=gb[y].quantile(.75)))
finish(rows, 'attention_bins', ['median_daily_views_pre', 'median_return', 'mean_return', 'p25_return', 'p75_return'])

# 4 models (pre-registered spec; see plan.md 2026-10-22)
CTRL = 'C(year) + foreign + log_offer'
rows = []
for y, lab in (('pop_log', 'first_day'), ('ret30_log', 'day_30')):
    for spec, inc, extra in (('A', True, '+ no_article'), ('B', False, '')):
        d = SETTINGS[inc].dropna(subset=[y])
        m = smf.ols(f'{y} ~ log_pre30 {extra} + {CTRL}', d).fit(cov_type='HC3')
        b = smf.ols(f'{y} ~ {CTRL} {extra}', d).fit(cov_type='HC3')
        for term in ('log_pre30', 'no_article', 'foreign', 'log_offer'):
            if term not in m.params: continue
            ci = m.conf_int().loc[term]
            rows.append(dict(model='confirmatory', spec=spec, include_no_article=inc, outcome=lab, term=term, n=int(m.nobs), coef=m.params[term], ci_low=ci[0], ci_high=ci[1],
                             p=m.pvalues[term], per_doubling=m.params[term]*np.log(2) if term == 'log_pre30' else np.nan, r2=m.rsquared, r2_controls_only=b.rsquared, se_type='HC3'))
for inc, d0 in SETTINGS.items():
    for s, g in d0.groupby('sector_group'):
        if s == 'Other': continue
        for y, lab in (('pop_log', 'first_day'), ('ret30_log', 'day_30')):
            d = g.dropna(subset=[y])
            if len(d) < MIN_N:
                rows.append(dict(model='sector_exploratory', spec='A' if inc else 'B', include_no_article=inc, outcome=lab, term='log_pre30', sector=s, n=len(d))); continue
            f = f'{y} ~ log_pre30 {"+ no_article" if inc else ""} + {CTRL}'
            m = smf.ols(f, d).fit(cov_type='HC1'); ci = m.conf_int().loc['log_pre30']
            rows.append(dict(model='sector_exploratory', spec='A' if inc else 'B', include_no_article=inc, outcome=lab, term='log_pre30', sector=s, n=int(m.nobs), coef=m.params.log_pre30,
                             ci_low=ci[0], ci_high=ci[1], p=m.pvalues.log_pre30, per_doubling=m.params.log_pre30*np.log(2), r2=m.rsquared, se_type='HC1'))
finish(rows, 'model_coefficients', ['coef', 'ci_low', 'ci_high', 'p', 'per_doubling', 'r2', 'r2_controls_only'])

# 5 pop drives attention: post-IPO views by first-day-return quintile
rows = []
for inc, d in SETTINGS.items():
    g = d.dropna(subset=['pop']).copy()
    g['bin'] = pd.qcut(g['pop'].rank(method='first'), 5, labels=False) + 1
    for b, gb in g.groupby('bin'):
        rows.append(dict(include_no_article=inc, pop_quintile=int(b), n=len(gb), median_first_day_return=gb['pop'].median(), median_daily_views_pre=gb.daily_pre.median(),
                         median_daily_views_day0=gb.daily_day0.median(), median_daily_views_post=gb.daily_post.median(), median_post_to_pre_ratio=((gb.views_post30+1)/(gb.views_pre30+1)).median()))
finish(rows, 'pop_vs_post_views', ['median_first_day_return', 'median_daily_views_pre', 'median_daily_views_day0', 'median_daily_views_post', 'median_post_to_pre_ratio'])

# 6 market-cap size tiers and cap quintiles (exploratory, post-hoc; cap = offer price x post-offering shares from 424B4, no vendor prices)
def tier(c): return pd.cut(c/1e9, [0, .3, 2, 10, np.inf], labels=['micro (<$0.3B)', 'small ($0.3-2B)', 'mid ($2-10B)', 'large (>$10B)'], right=False)
rows = []
for inc, d0 in SETTINGS.items():
    d = d0.dropna(subset=['market_cap']).copy()
    d['tier'] = tier(d.market_cap)
    d['cap_quintile'] = pd.qcut(d.market_cap.rank(method='first'), 5, labels=False) + 1
    for kind, col in (('tier', 'tier'), ('quintile', 'cap_quintile')):
        for k, g in d.groupby(col, observed=True):
            n1 = int(g['pop'].notna().sum())
            rows.append(dict(include_no_article=inc, grouping=kind, group=str(k), n=len(g), median_market_cap_busd=g.market_cap.median()/1e9 if kind == 'quintile' else np.nan,
                             median_daily_views_pre=g.daily_pre.median(), median_daily_views_day0=g.daily_day0.median(), median_daily_views_post=g.daily_post.median(),
                             n_first_day=n1, median_first_day_return=g['pop'].median() if n1 >= MIN_N else np.nan, median_day30_return=g.ret30.median()))
d = finish(rows, 'market_cap_tiers', ['median_market_cap_busd', 'median_daily_views_pre', 'median_daily_views_day0', 'median_daily_views_post', 'n_first_day', 'median_first_day_return', 'median_day30_return'])
assert ((d.n_first_day >= MIN_N) | d.n_first_day.isna()).all() and (d.loc[d.n_first_day.isna() & ~d.suppressed, 'median_first_day_return'].isna()).all()

pd.DataFrame([dict(key='n_usable_day30', include_no_article=i, n=len(d)) for i, d in SETTINGS.items()] +
             [dict(key='n_usable_first_day', include_no_article=i, n=int(d['pop'].notna().sum())) for i, d in SETTINGS.items()] +
             [dict(key='n_placeholder_first_day_missing', include_no_article=True, n=int(df.pop_close_eq_offer.sum()))] +
             [dict(key='n_with_market_cap', include_no_article=i, n=int(d.market_cap.notna().sum())) for i, d in SETTINGS.items()]
             ).assign(suppressed=False).to_csv(f'{OUT}/meta_counts.csv', index=False)
print('wrote', sorted(os.listdir(OUT)))
