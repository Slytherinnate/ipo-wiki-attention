"""Static PNGs for the write-up, drawn only from data/public/*.csv (main spec: INCLUDE_NO_ARTICLE=True)."""
import pandas as pd, numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt, os
P = 'data/public'; os.makedirs('figures', exist_ok=True)
c = pd.read_csv(f'{P}/attention_curve.csv'); c = c[~c.suppressed]
fig, ax = plt.subplots(figsize=(9, 4.8))
ax.axvspan(-30, 0, color='tab:blue', alpha=0.08, label='Attention window used in the model (30 days before IPO)')
cc = c[c.include_no_article]
for g, col, lw in [('All', 'tab:blue', 2.2), ('Article with pre-IPO views', 'tab:orange', 1.4)]:
    d = cc[cc.group == g].sort_values('rel_day')
    sm = d.median_views.rolling(7, center=True, min_periods=1).median()
    sm[d.rel_day.abs().values <= 3] = d.median_views[d.rel_day.abs().values <= 3]  # keep the IPO spike unsmoothed
    lab = 'All firms' if g == 'All' else 'Firms with a pre-IPO article'
    ax.plot(d.rel_day, sm, c=col, lw=lw, label=f'{lab} (n={int(d.n.iloc[0])})')
ax.axvline(0, ls='--', c='grey'); ax.set_yscale('log')
ax.set(xlabel='Days from first trading day (0 = IPO day)', ylabel='Median daily Wikipedia views (log scale)')
ax.set_title('Wikipedia attention around IPO day\nmedian views per day across firms, 7-day rolling median (IPO week unsmoothed)', fontsize=10)
fig.text(0.01, 0.01, 'The 48 firms with no article before the IPO sit at 0 views/day and cannot be drawn on a log scale; they are included in "All firms".', fontsize=7.5, color='dimgrey')
ax.legend(fontsize=8, loc='upper left'); fig.tight_layout(rect=(0, 0.04, 1, 1)); fig.savefig('figures/attention_curve.png', dpi=150)
b = pd.read_csv(f'{P}/attention_bins.csv'); b = b[b.include_no_article & (b.bins == 5)]
fig, ax = plt.subplots(figsize=(7, 4.5))
for o, d in b.groupby('outcome'):
    ax.plot(d.bin, d.median_return * 100, marker='o', label={'first_day': 'First-day return', 'day_30': 'Day-30 return'}[o])
ax.set(xlabel='Pre-IPO 30-day views quintile (1 = least attention)', ylabel='Median return (%)', title='Returns by pre-IPO attention quintile'); ax.set_xticks(range(1, 6)); ax.legend()
fig.tight_layout(); fig.savefig('figures/binned_returns.png', dpi=150)
m = pd.read_csv(f'{P}/model_coefficients.csv'); m = m[(m.model == 'confirmatory') & (m.term == 'log_pre30')]
lab = m.apply(lambda r: f"{'First-day' if r.outcome == 'first_day' else 'Day-30'} · Spec {r.spec} (n={int(r.n)})", axis=1)
k = np.log(2) * 100
fig, ax = plt.subplots(figsize=(7, 3.5)); y = np.arange(len(m))
ax.errorbar(m.coef * k, y, xerr=[(m.coef - m.ci_low) * k, (m.ci_high - m.coef) * k], fmt='o', capsize=4)
ax.axvline(0, c='grey', ls='--'); ax.set_yticks(y, lab)
ax.set(xlabel='Effect of doubling pre-IPO views on log(1+return), ×100 (≈ %), 95% CI', title='Confirmatory OLS, HC3 SEs\n(controls: year FE, foreign issuer, log offer price)')
fig.tight_layout(); fig.savefig('figures/coef_plot.png', dpi=150)
r = pd.read_csv(f'{P}/pop_vs_post_views.csv'); r = r[r.include_no_article]
fig, ax = plt.subplots(figsize=(7, 4.5)); w = .27
for i, (c, l) in enumerate((('median_daily_views_pre', 'Before (daily avg, −30..−1)'), ('median_daily_views_day0', 'IPO day'), ('median_daily_views_post', 'After (daily avg, +1..+30)'))):
    ax.bar(r.pop_quintile + (i-1)*w, r[c], w, label=l)
ax.set_yscale('log')
ax.set(xlabel='First-day return quintile (1 = weakest pop)', ylabel='Median daily views (log)', title='Does the pop drive attention? Views before vs after, by pop size'); ax.legend()
fig.tight_layout(); fig.savefig('figures/reverse_pop_attention.png', dpi=150)
z = pd.read_csv(f'{P}/market_cap_tiers.csv'); z = z[z.include_no_article & (z.grouping == 'tier') & ~z.suppressed]
order = ['micro (<$0.3B)', 'small ($0.3-2B)', 'mid ($2-10B)', 'large (>$10B)']; z = z.set_index('group').loc[[o for o in order if o in set(z.group)]]
fig, axs = plt.subplots(1, 2, figsize=(12, 4.5)); x = np.arange(len(z)); w = .27
for i, (c, l) in enumerate((('median_daily_views_pre', 'Before (daily avg, −30..−1)'), ('median_daily_views_day0', 'IPO day'), ('median_daily_views_post', 'After (daily avg, +1..+30)'))): axs[0].bar(x + (i-1)*w, z[c], w, label=l)
axs[0].set_yscale('log'); axs[0].set_xticks(x, [f'{g}\nn={int(n)}' for g, n in zip(z.index, z.n)], fontsize=8); axs[0].set(ylabel='Median daily views (log)', title='Attention by IPO size tier'); axs[0].legend(fontsize=8)
for i, (c, l) in enumerate((('median_first_day_return', 'First-day'), ('median_day30_return', 'Day-30'))): axs[1].bar(x + (i-.5)*.38, z[c]*100, .38, label=l)
axs[1].set_xticks(x, z.index, fontsize=8); axs[1].set(ylabel='Median return (%)', title='Returns by IPO size tier'); axs[1].legend(fontsize=8)
fig.suptitle('Exploratory (post-hoc): IPO market cap = offer price x post-offering shares (SEC 424B4)', fontsize=10); fig.tight_layout(); fig.savefig('figures/size_tiers.png', dpi=150)
print(os.listdir('figures'))
