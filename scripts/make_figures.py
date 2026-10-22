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
r = pd.read_csv(f'{P}/pop_vs_post_views.csv'); r = r[r.include_no_article].sort_values('pop_quintile')
fig, (a1, a2) = plt.subplots(2, 1, figsize=(8, 6.4), sharex=True, gridspec_kw={'hspace': .35})
x = np.arange(len(r)); cols = plt.cm.Blues(np.linspace(.35, .9, len(r)))
chg = (r.median_post_to_pre_ratio - 1) * 100; pop = r.median_first_day_return * 100
a1.bar(x, chg, color=cols)
for xi, v in zip(x, chg): a1.text(xi, v + .8, f'+{v:.0f}%', ha='center', fontsize=10, fontweight='bold')
a1.set_ylim(0, chg.max() * 1.25); a1.set_ylabel('Change in daily\nreaders (%)')
a1.set_title('Change in daily Wikipedia readers: month after the IPO vs month before', fontsize=10)
a2.bar(x, pop, color=plt.cm.Oranges(np.linspace(.35, .9, len(r)))); a2.axhline(0, c='k', lw=.8)
for xi, v in zip(x, pop): a2.text(xi, v + (2 if v >= 0 else -6), f'{v:+.0f}%', ha='center', fontsize=10, fontweight='bold')
a2.set_ylim(min(pop.min() * 1.8, -5), pop.max() * 1.2); a2.set_ylabel('Stock price move\non day one (%)')
a2.set_title('Stock price move on IPO day (closing price vs IPO price)', fontsize=10)
a2.set_xticks(x, [f'Group {i+1}\n{int(n)} IPOs' for i, n in enumerate(r.n)], fontsize=9)
a2.set_xlabel('IPOs sorted into five equal groups by day-one stock move (smallest to biggest)')
fig.suptitle('The bigger the day-one jump, the more people kept reading about the company', fontsize=11.5, fontweight='bold')
fig.text(.01, -.03, 'Medians per group. IPO day excluded from the readership comparison.', fontsize=7.5, color='dimgrey')
fig.savefig('figures/reverse_pop_attention.png', dpi=150, bbox_inches='tight')
z = pd.read_csv(f'{P}/market_cap_tiers.csv'); z = z[z.include_no_article & (z.grouping == 'tier') & ~z.suppressed]
order = ['micro (<$0.3B)', 'small ($0.3-2B)', 'mid ($2-10B)', 'large (>$10B)']; z = z.set_index('group').loc[[o for o in order if o in set(z.group)]]
fig, axs = plt.subplots(1, 2, figsize=(12, 4.5)); x = np.arange(len(z)); w = .27
for i, (c, l) in enumerate((('median_daily_views_pre', 'Before (daily avg, −30..−1)'), ('median_daily_views_day0', 'IPO day'), ('median_daily_views_post', 'After (daily avg, +1..+30)'))): axs[0].bar(x + (i-1)*w, z[c], w, label=l)
axs[0].set_yscale('log'); axs[0].set_xticks(x, [f'{g}\nn={int(n)}' for g, n in zip(z.index, z.n)], fontsize=8); axs[0].set(ylabel='Median daily views (log)', title='Attention by IPO size tier'); axs[0].legend(fontsize=8)
for i, (c, l) in enumerate((('median_first_day_return', 'First-day'), ('median_day30_return', 'Day-30'))): axs[1].bar(x + (i-.5)*.38, z[c]*100, .38, label=l)
axs[1].set_xticks(x, z.index, fontsize=8); axs[1].set(ylabel='Median return (%)', title='Returns by IPO size tier'); axs[1].legend(fontsize=8)
fig.suptitle('Exploratory (post-hoc): IPO market cap = offer price x post-offering shares (SEC 424B4)', fontsize=10); fig.tight_layout(); fig.savefig('figures/size_tiers.png', dpi=150)
print(os.listdir('figures'))
