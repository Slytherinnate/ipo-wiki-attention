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
a1.set_ylim(0, chg.max() * 1.25); a1.set_ylabel('Increase in daily\npage views (%)')
a1.set_title('Increase in Wikipedia page views after the IPO\n(% above viewership before the IPO)', fontsize=10)
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
nice = {'micro (<$0.3B)': 'Micro\nunder \\$300M', 'small ($0.3-2B)': 'Small\n\\$300M to \\$2B', 'mid ($2-10B)': 'Mid\n\\$2B to \\$10B', 'large (>$10B)': 'Large\nover \\$10B'}
fig, (a1, a2) = plt.subplots(2, 1, figsize=(8, 6.6), sharex=True, gridspec_kw={'hspace': .4}); x = np.arange(len(z))
v = z.median_daily_views_pre; a1.bar(x, v, color=plt.cm.Blues(np.linspace(.35, .9, len(z))))
for xi, val in zip(x, v): a1.text(xi, val + v.max() * .02, f'{val:,.0f}', ha='center', fontsize=10, fontweight='bold')
a1.set_ylim(0, v.max() * 1.18); a1.set_ylabel('Daily page views')
a1.set_title('How many people read about the company each day in the month before its IPO', fontsize=10)
r1 = z.median_first_day_return * 100; a2.bar(x, r1, color=plt.cm.Oranges(np.linspace(.35, .9, len(z))))
for xi, val in zip(x, r1): a2.text(xi, val + .6, f'+{val:.0f}%', ha='center', fontsize=10, fontweight='bold')
a2.set_ylim(0, r1.max() * 1.22); a2.set_ylabel('Stock price move\non day one (%)')
a2.set_title('Stock price move on IPO day (closing price vs IPO price)', fontsize=10)
a2.set_xticks(x, [f'{nice[g]}\n({int(n)} IPOs)' for g, n in zip(z.index, z.n)], fontsize=9)
a2.set_xlabel('Company value at IPO')
fig.suptitle('Bigger companies get far more attention, but not bigger first-day jumps', fontsize=11.5, fontweight='bold')
fig.text(.01, -.07, 'Company value = IPO share price x shares outstanding after the IPO, from each company\'s prospectus filed with the SEC.\nMedians per group. Size was examined after the main analysis (exploratory).', fontsize=7.5, color='dimgrey')
fig.savefig('figures/size_tiers.png', dpi=150, bbox_inches='tight')
print(os.listdir('figures'))
