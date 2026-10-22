"""Wikipedia attention and IPO returns — reads ONLY data/public/*.csv (aggregates, every group n>=15).
Run: streamlit run app/streamlit_app.py"""
from pathlib import Path
import numpy as np, pandas as pd, plotly.express as px, plotly.graph_objects as go, streamlit as st
PUB = Path(__file__).resolve().parents[1] / 'data' / 'public'
SUP = 'suppressed (n<15)'
st.set_page_config(page_title='Wikipedia attention & IPO returns', layout='wide')

@st.cache_data
def load(name): return pd.read_csv(PUB / f'{name}.csv')
curve, base, bins, coefs, rev, meta, size = (load(n) for n in ('attention_curve', 'return_baselines', 'attention_bins', 'model_coefficients', 'pop_vs_post_views', 'meta_counts', 'market_cap_tiers'))

st.sidebar.title('Settings')
inc = st.sidebar.toggle('Include IPOs with no pre-IPO Wikipedia article', value=True,
                        help='On (main spec): firms whose article appeared only after the IPO count as zero attention. Off (robustness): they are excluded.')
sectors = sorted(s for s in base[(base.dimension == 'sector')].group.unique())
sector = st.sidebar.selectbox('Sector', ['All'] + sectors)
page = st.sidebar.radio('Section', ['Overview', 'Attention around IPO day', 'Does attention predict returns?', 'Pop drives attention', 'By sector', 'Company size', 'Methods & limitations'])
st.sidebar.caption('All figures are aggregates over ≥15 firms. Smaller groups are shown as "suppressed (n<15)".')

def sel(d): return d[d.include_no_article == inc]
def show(d, cols, pct=()):
    out = d.copy()
    for c in cols:
        out[c] = [SUP if s else (f'{v*100:.1f}%' if c in pct else (f'{v:.1f}' if isinstance(v, float) else v)) for v, s in zip(out[c], out.suppressed)]
    out['n'] = [SUP if s else str(int(v)) for v, s in zip(out.n, out.suppressed)]
    return out.drop(columns=['suppressed', 'include_no_article'], errors='ignore')
def base_table(dim, grp=None):
    d = sel(base); d = d[d.dimension == dim] if grp is None else d[(d.dimension == dim) & (d.group == grp)]
    d = d.assign(outcome=d.outcome.map({'first_day': 'First-day', 'day_30': 'Day-30'}))
    return show(d[['outcome', 'group', 'n', 'median', 'mean', 'iqr', 'pct_positive', 'suppressed']], ['median', 'mean', 'iqr'], pct=('median', 'mean', 'iqr')).assign(pct_positive=lambda x: [v if v == SUP else f'{float(v):.0f}%' for v in x.pct_positive])
cA = coefs[(coefs.model == 'confirmatory') & (coefs.term == 'log_pre30')]
def eff(o, s): r = cA[(cA.outcome == o) & (cA.spec == s)].iloc[0]; return r

if page == 'Overview':
    st.title('Does Wikipedia attention before an IPO predict its returns?')
    a, b = eff('first_day', 'A'), eff('day_30', 'A')
    st.markdown(f"""**Short answer: barely, and only on day one.** In US IPOs from 2019–2025, doubling a company's Wikipedia views in the 30 days before listing goes with about
**{a.per_doubling*100:.1f}%** higher (1 + first-day return) (95% CI {a.ci_low*np.log(2)*100:.1f}% to {a.ci_high*np.log(2)*100:.1f}%, p = {a.p:.3f}). By day 30 the link is gone
({b.per_doubling*100:+.1f}%, p = {b.p:.2f}). The bigger pattern runs the **other way**: companies that pop get far more attention *after* the IPO.""")
    n = meta.set_index(['key', 'include_no_article']).n
    c1, c2, c3 = st.columns(3)
    c1.metric('IPOs with a day-30 return', int(n[('n_usable_day30', inc)])); c2.metric('IPOs with a first-day return', int(n[('n_usable_first_day', inc)]))
    c3.metric('Setting', 'Main spec' if inc else 'Robustness (no-article excluded)')
    st.subheader('Return baselines' + ('' if sector == 'All' else f' — {sector}'))
    st.dataframe(base_table('All') if sector == 'All' else base_table('sector', sector), hide_index=True, width='stretch')
    st.subheader('By article group'); st.dataframe(base_table('article'), hide_index=True, width='stretch')
    st.subheader('By year'); st.dataframe(base_table('year'), hide_index=True, width='stretch')

elif page == 'Attention around IPO day':
    st.title('Attention around IPO day')
    st.caption('Median daily Wikipedia views across firms, 120 days before to 60 days after the first trading day. The weekly wiggle is normal: fewer people read on weekends.')
    d = sel(curve)
    d = d[(d.dimension == 'All') | (d.dimension == 'article')] if sector == 'All' else d[(d.dimension == 'sector') & (d.group == sector)]
    if d.suppressed.all(): st.warning(SUP)
    else:
        d = d[~d.suppressed]; d = d.assign(label=d.group + ' (n=' + d.n.astype(int).astype(str) + ')')
        fig = px.line(d, x='rel_day', y='median_views', color='label', labels={'rel_day': 'Days from first trading day', 'median_views': 'Median daily views', 'label': ''})
        fig.add_vline(x=0, line_dash='dash', line_color='grey'); fig.update_yaxes(type='log' if st.checkbox('Log scale', True) else 'linear')
        st.plotly_chart(fig, width='stretch')

elif page == 'Does attention predict returns?':
    st.title('Does pre-IPO attention predict returns?')
    nb = st.radio('Bins', [5, 10], horizontal=True, format_func=lambda x: 'Quintiles' if x == 5 else 'Deciles')
    d = sel(bins); d = d[(d.bins == nb) & ~d.suppressed].assign(outcome=lambda x: x.outcome.map({'first_day': 'First-day', 'day_30': 'Day-30'}))
    fig = px.line(d, x='bin', y=d.median_return * 100, color='outcome', markers=True, hover_data={'n': True, 'median_daily_views_pre': True},
                  labels={'bin': 'Pre-IPO 30-day views bin (1 = least attention)', 'y': 'Median return (%)', 'outcome': ''})
    st.plotly_chart(fig, width='stretch')
    if sector != 'All': st.info('Binned results are shown for all sectors only; per-sector bins would fall below n=15.')
    st.subheader('Confirmatory model (pre-registered 2026-10-22)')
    st.markdown("""OLS of ln(1 + return) on ln(pre-IPO 30-day views + 1), with year fixed effects, foreign issuer, and ln(offer price) as controls, and HC3 robust standard errors.
**Spec A** (main): all firms plus a no-article dummy. **Spec B** (robustness): no-article firms excluded. The effect shown is per **doubling** of views (coef × ln 2).

**Decision rule (set before running):** attention counts as confirmed only if p < 0.05 in Spec A *and* Spec B has the same sign.""")
    d = cA.assign(label=lambda x: x.outcome.map({'first_day': 'First-day', 'day_30': 'Day-30'}) + ' · Spec ' + x.spec + ' (n=' + x.n.astype(int).astype(str) + ')')
    k = np.log(2) * 100
    fig = go.Figure(go.Scatter(x=d.coef * k, y=d.label, mode='markers', error_x=dict(type='data', symmetric=False, array=(d.ci_high - d.coef) * k, arrayminus=(d.coef - d.ci_low) * k)))
    fig.add_vline(x=0, line_dash='dash', line_color='grey'); fig.update_layout(xaxis_title='% change in (1 + return) per doubling of views, 95% CI', height=350)
    st.plotly_chart(fig, width='stretch')
    t = d[['label', 'per_doubling', 'ci_low', 'ci_high', 'p', 'r2', 'r2_controls_only']].assign(per_doubling=lambda x: (x.per_doubling * 100).round(2), ci_low=lambda x: (x.ci_low * k).round(2), ci_high=lambda x: (x.ci_high * k).round(2),
        p=lambda x: x.p.round(3), incremental_r2=lambda x: (x.r2 - x.r2_controls_only).round(4), r2=lambda x: x.r2.round(3)).drop(columns='r2_controls_only')
    st.dataframe(t, hide_index=True, width='stretch')
    st.markdown(f"**Verdict:** first-day: meets the rule (Spec A p = {eff('first_day','A').p:.3f}; Spec B same sign, p = {eff('first_day','B').p:.3f}), but the effect is small and adds about 1% of explained variance. Day-30: no effect.")
    st.caption('The toggle does not change this chart: Spec A and Spec B are the two settings by design.')

elif page == 'Pop drives attention':
    st.title('Does the first-day pop drive attention afterwards?')
    st.caption('Firms grouped into five equal-size groups by first-day return. Views after the IPO cannot cause the pop, so this tests the reverse direction.')
    d = sel(rev)
    fig = go.Figure([go.Bar(name='Before (daily avg, days −30..−1)', x=d.pop_quintile, y=d.median_daily_views_pre), go.Bar(name='IPO day (day 0)', x=d.pop_quintile, y=d.median_daily_views_day0), go.Bar(name='After (daily avg, days +1..+30)', x=d.pop_quintile, y=d.median_daily_views_post)])
    fig.update_layout(barmode='group', xaxis_title='First-day return quintile (1 = weakest)', yaxis_title='Median daily views (log)', yaxis_type='log')
    st.caption('Each bar is the median across firms of each firm’s average daily views in that period, so before, IPO day and after are on the same per-day scale.')
    st.plotly_chart(fig, width='stretch')
    st.dataframe(d[['pop_quintile', 'n', 'median_first_day_return', 'median_daily_views_pre', 'median_daily_views_day0', 'median_daily_views_post', 'median_post_to_pre_ratio']].assign(median_first_day_return=lambda x: (x.median_first_day_return * 100).round(1).astype(str) + '%', median_post_to_pre_ratio=lambda x: x.median_post_to_pre_ratio.round(2)), hide_index=True, width='stretch')
    if sector != 'All': st.info('Shown for all sectors only (sector quintiles would fall below n=15).')

elif page == 'By sector':
    st.title('By sector')
    st.dataframe(base_table('sector'), hide_index=True, width='stretch')
    st.subheader('Exploratory: attention coefficient per sector')
    st.caption('Secondary analysis: 12 tests per setting, so about one may look significant by chance. HC1 robust SEs. Treat as leads, not findings.')
    s = coefs[(coefs.model == 'sector_exploratory') & (coefs.include_no_article == inc)]
    if sector != 'All': s = s[s.sector == sector]
    ok = s[~s.suppressed].assign(label=lambda x: x.sector + ' · ' + x.outcome.map({'first_day': 'First-day', 'day_30': 'Day-30'}) + ' (n=' + x.n.astype(int).astype(str) + ')')
    k = np.log(2) * 100
    fig = go.Figure(go.Scatter(x=ok.coef * k, y=ok.label, mode='markers', error_x=dict(type='data', symmetric=False, array=(ok.ci_high - ok.coef) * k, arrayminus=(ok.coef - ok.ci_low) * k)))
    fig.add_vline(x=0, line_dash='dash', line_color='grey'); fig.update_layout(xaxis_title='% per doubling of views, 95% CI', height=60 + 35 * max(len(ok), 1))
    st.plotly_chart(fig, width='stretch')
    for _, r in s[s.suppressed].iterrows(): st.write(f'{r.sector} · {r.outcome}: {SUP}')

elif page == 'Company size':
    st.title('Company size')
    st.warning('**Exploratory (post-hoc).** Not part of the pre-registered analysis: this was asked after seeing the main results. Treat it as a lead, not a finding.')
    nc = meta.set_index(['key', 'include_no_article']).n
    st.markdown(f"""**In plain English:** bigger companies get far more Wikipedia attention (median pre-IPO views rise roughly 140× from micro to large caps), but size doesn't track returns, which are about flat above micro-cap (micro caps run lower, but that tier is only ~18 firms, so treat it as noise).
When size is added as a control, the attention effect on first-day returns gets slightly *stronger*: about **+1.14% per doubling of views (p = 0.016, n = 264)**. That's a post-hoc lead to test properly, not a result.

Market cap = offer price × shares outstanding right after the offering, from the SEC 424B4 prospectus (no market prices). Available for **{int(nc[('n_with_market_cap', True)])} of {int(nc[('n_usable_day30', True)])}** IPOs. The missing ones are mostly complex multi-class and Up-C structures, so they're **not missing at random**.""")
    if sector != 'All': st.info('Size tiers are shown for all sectors only (per-sector tiers would fall below n=15).')
    d = sel(size); d = d[d.grouping == 'tier'].copy()
    order = ['micro (<$0.3B)', 'small ($0.3-2B)', 'mid ($2-10B)', 'large (>$10B)']
    d['group'] = pd.Categorical(d.group, order, ordered=True); d = d.sort_values('group')
    tbl = pd.DataFrame({'Tier': d.group.astype(str)})
    for c, lab, f in (('n', 'n', '{:.0f}'), ('median_daily_views_pre', 'Median daily views, 30d before', '{:,.1f}'), ('median_daily_views_day0', 'Median views, IPO day', '{:,.0f}'), ('median_daily_views_post', 'Median daily views, 30d after', '{:,.1f}'),
                      ('median_first_day_return', 'Median first-day return', '{:.1%}'), ('median_day30_return', 'Median day-30 return', '{:.1%}')):
        tbl[lab] = [SUP if (s_ or pd.isna(v)) else f.format(v) for v, s_ in zip(d[c], d.suppressed)]
    st.dataframe(tbl, hide_index=True, width='stretch')
    ok = d[~d.suppressed]
    v = ok.melt(id_vars='group', value_vars=['median_daily_views_pre', 'median_daily_views_day0', 'median_daily_views_post'], var_name='period', value_name='views')
    v['period'] = v.period.map({'median_daily_views_pre': 'Before (daily avg, days −30..−1)', 'median_daily_views_day0': 'IPO day (day 0)', 'median_daily_views_post': 'After (daily avg, days +1..+30)'}); v['group'] = v.group.astype(str)
    fig = px.bar(v, x='group', y='views', color='period', barmode='group', log_y=True, labels={'group': 'Size tier', 'views': 'Median daily views (log)', 'period': ''})
    st.plotly_chart(fig, width='stretch')
    st.caption('Median across firms of each firm’s average daily views in the 30 days before (−30..−1), views on IPO day (0), and average daily views in the 30 days after (+1..+30).')
    r = ok.melt(id_vars='group', value_vars=['median_first_day_return', 'median_day30_return'], var_name='outcome', value_name='ret').dropna()
    r['outcome'] = r.outcome.map({'median_first_day_return': 'First-day', 'median_day30_return': 'Day-30'}); r['ret'] *= 100; r['group'] = r.group.astype(str)
    fig = px.bar(r, x='group', y='ret', color='outcome', barmode='group', labels={'group': 'Size tier', 'ret': 'Median return (%)', 'outcome': ''})
    st.plotly_chart(fig, width='stretch')
    for g in d[d.suppressed].group.astype(str): st.write(f'{g}: {SUP}')

else:
    st.title('Methods & limitations')
    st.markdown("""
**Sample.** US operating-company IPOs from 2019–2025, found in SEC EDGAR 424B4 prospectuses (SPACs and funds excluded). Each was matched to its English Wikipedia article: automatically (Wikidata CIK or a verified ticker), or by manual review of 468 uncertain cases using a strong-match rule (CIK, or ticker plus name). Only confirmed matches are analysed, so firms without a findable article are not in the sample.

**Attention.** Daily human pageviews from the Wikimedia Pageviews API, with the article's redirects and old titles summed. The window runs from 120 days before to 60 days after the first trading day.

**Returns.** First-day return = first close / offer price − 1. Day-30 return = close about 30 days later / offer − 1. Offer prices come from the 424B4. Daily prices are from a licensed vendor (Tiingo). Under its terms only aggregates over at least 15 firms are shown here; no per-company prices or returns are published.

**Limitations.**
- *Survivorship and matching.* Only IPOs with a Wikipedia article and usable price data are included. Firms that are obscure or have since delisted are under-represented.
- *Placeholder first-day closes.* For 20 firms the vendor's first close equals the offer price exactly, which is almost certainly a placeholder. Their first-day return is treated as missing; their day-30 return is kept.
- *Articles created after the IPO.* 48 firms only got a Wikipedia article after listing. The main spec counts them as zero attention (with a dummy); the robustness spec drops them (sidebar toggle).
- *Correlation, not causation.* Attention, hype and deal quality move together. The controls (year, foreign issuer, offer price) don't remove all of that.
- *Multiple comparisons.* The confirmatory test was pre-registered. Sector results and the exploratory scan are not, and should be read as leads.
- *Small groups.* Any group under 15 firms is suppressed everywhere.

**Data sources and licenses.** SEC EDGAR (US government public data). Wikimedia pageviews (CC0). Wikidata (CC0). Wikipedia article metadata (CC BY-SA). Price data © Tiingo, shown only as aggregates of 15 or more firms.
""")
