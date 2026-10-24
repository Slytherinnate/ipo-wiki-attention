# Wikipedia attention and IPO returns, 2019–2025

*Draft, first pass (2026-10-22). All figures are aggregates over at least 15 firms.*

## 1. Motivation

IPO first-day "pops" are large and well documented. A common story is that retail attention drives them: the more people look a company up before it lists, the more demand there is on day one. Wikipedia pageviews are a free, daily, public measure of that attention. This project asks a narrow question: **does pre-IPO Wikipedia attention predict first-day or 30-day returns, and does it differ by sector?**

## 2. Data

**IPO universe (SEC EDGAR).** Final prospectuses (424B4, plus 424B1 where no 424B4 exists) filed 2019–2025 were collected from EDGAR. SPACs, funds and trusts were excluded (1,293 filings), along with companies that had already filed periodic reports. That left **1,410 operating-company IPOs**. Offer prices, shares offered and sector (SIC codes mapped to GICS-style sector names by a documented crosswalk; not official GICS) come from the prospectus and EDGAR submissions.

**Matching to Wikipedia.** Each company was matched to an English Wikipedia article in this order:
1. A Wikidata item carrying the company's SEC CIK.
2. Failing that, a Wikidata ticker/exchange match that also shares a name word.
3. Failing that, a Wikipedia search accepted only if the article text shows the ticker.

Matches with any doubt went to manual review: **468 rows**, worked through against a written checklist (`docs/review-checklist.md`). A match needed either a CIK match, or ticker plus name. The review had a QA pass covering decision/code consistency, exact titles, field scopes, articles created after the IPO, ADR notes and duplicate titles. The result: 220 automatic matches plus 148 manual keeps, **352 matched firms**. One of them, listed on Euronext Paris rather than a US exchange, was moved out of the US-IPO set, leaving **351**.

**Attention (Wikimedia Pageviews REST API).** Daily pageviews (user agent only, all access) for each article, summed with its redirects and known former titles, so that renames don't erase history. The window runs from 120 days before to 60 days after the first trading day. 345 of 352 matched firms have views; the 7 without views all got their article after the IPO and have no views in the window.

**Prices (Tiingo).** End-of-day prices on the SEC-derived first trading day and about 30 trading days later, used only to compute returns. Under the license, only aggregates over at least 15 IPOs are published. First-trade dates, firm identity and sample membership come from SEC filings only. An earlier build (Oct 20–23, 2026) did use Tiingo's first price date to move 45 EDGAR-derived dates and Tiingo's ticker metadata to exclude firms; that was removed on Oct 24, 2026, and every number here was rebuilt without it (see `plan.md`).

**Usable sample.** 294 firms have views and a valid day-30 return; 287 also have a valid first-day return (see §5 on placeholder closes). By year: 2019: 47, 2020: 50, 2021: 121, 2022: 11, 2023: 15, 2024: 27, 2025: 23. 2021 is 41% of the sample.

## 3. Methods

**Returns.** First-day return = close on the SEC-derived first trading day / offer price − 1. Day-30 return = close 30 trading days later / offer price − 1. If the price data has no bar on the SEC date, the return is missing; the date is never moved to fit the price data. Models use ln(1 + return).

**Attention.** The test variable is ln(1 + total views in days −30 to −1). Daily-view comparisons use each firm's average daily views before (days −30..−1) and after (+1..+30), next to its IPO-day (day 0) views, so all three are on the same per-day scale.

**Firms without a pre-IPO article.** 49 firms had no Wikipedia article until after listing. Two treatments were fixed in advance:
- **Spec A (main):** keep them, count them as zero attention, and add a no-article dummy.
- **Spec B (robustness):** drop them.

**Pre-registered model.** The spec was written into `plan.md` and the model notebook *before* the model was run: OLS of ln(1 + return) on ln(1 + pre-IPO 30-day views), with year fixed effects, a foreign-issuer flag and ln(offer price) as controls, using HC3 heteroskedasticity-robust standard errors. The coefficient is reported per doubling of views (coef × ln 2), which is roughly the % change in (1 + return).

**Decision rule.** Attention counts as confirmed for an outcome only if p < 0.05 in Spec A *and* Spec B has the same sign. The rule was added to the spec before running and approved. There is no adjustment across the two outcomes, and that is stated.

**Everything else is exploratory:** sector splits, the variable scan (Benjamini–Hochberg adjusted) and the market-cap analysis.

## 4. Results

### 4.1 Baselines

| | n | Mean | Median | SD | IQR | % positive |
|---|---|---|---|---|---|---|
| First-day return | 287 | 33.1% | 21.9% | 51.4% | 39.7% | 78.4% |
| Day-30 return | 294 | 41.9% | 20.0% | 135.4% | 51.9% | 73.8% |

Three firms have day-30 returns above +500%. They stay in the sample: the models use log returns, and the rank-based checks are insensitive to them. By article group, firms without a pre-IPO article had a median first-day return of 27.8% (n = 49) and a median day-30 return of 28.2% (n = 49). Firms with an article and pre-IPO views had 20.8% (n = 225) and 19.3% (n = 231). A Kruskal–Wallis test across article groups finds no significant difference (first-day p = 0.15; day-30 p = 0.34).

Attention spikes on IPO day. The cross-firm median of daily views averages about 90 per day over the month before, is 499 on day 0, and averages about 119 per day over the month after (main spec, n = 294).

### 4.2 Confirmatory model

| Outcome | Spec | n | Per doubling of views | 95% CI | p | R² | Controls-only R² |
|---|---|---|---|---|---|---|---|
| First-day | A (main) | 287 | +0.91% | +0.08% to +1.74% | 0.032 | 0.138 | 0.129 |
| First-day | B (robust) | 238 | +0.83% | −0.01% to +1.67% | 0.052 | 0.173 | 0.163 |
| Day-30 | A (main) | 294 | +0.07% | −1.15% to +1.29% | 0.909 | 0.113 | 0.113 |
| Day-30 | B (robust) | 245 | +0.12% | −1.08% to +1.31% | 0.845 | 0.124 | 0.124 |

- **First-day:** meets the decision rule, but only just. The effect is small, about one percentage point of (1 + return) per doubling of views, and adds less than 0.01 to R².
- **Day-30:** null.
- **No-article dummy (Spec A):** the largest attention-related term. It is +0.23 for first-day (p < 0.001) and +0.18 for day-30 (p = 0.10). Firms whose article appeared only after listing did *better*, which is hard to square with "attention causes the pop".

### 4.3 Sector heterogeneity (exploratory)

Spec A was re-estimated within each sector with at least 15 firms (HC1 standard errors, since HC3 is undefined when a sector has a year with a single firm). Of 12 tests in Spec A, one has p < 0.05: Health Care day-30, −4.8% per doubling, p = 0.035, n = 46. With 12 tests, about one false positive is expected at that level, and it doesn't hold in Spec B (p = 0.65). No sector shows a reliable first-day effect; Information Technology is the closest (+1.8% per doubling, p = 0.053, n = 99). The "Other" group (fewer than 15 firms) falls below the publishing threshold and is suppressed.

### 4.4 Reverse direction: the pop drives attention

Grouping firms by first-day return (quintiles of 57–58 firms):

| First-day return quintile | Median first-day return | Median daily views, 30d before | Median views, IPO day | Median daily views, 30d after | Median after/before ratio |
|---|---|---|---|---|---|
| 1 (weakest) | −7.6% | 82.8 | 304 | 69.7 | 1.02 |
| 2 | 8.0% | 137.6 | 363 | 111.0 | 1.00 |
| 3 | 21.9% | 32.7 | 196 | 92.8 | 1.06 |
| 4 | 38.9% | 124.0 | 1,005 | 175.8 | 1.22 |
| 5 (strongest) | 81.1% | 188.2 | 1,197 | 218.3 | 1.30 |

Pre-IPO attention bounces around across quintiles. IPO-day attention and the after/before ratio are highest in the two strongest-pop quintiles. In the exploratory scan, ln(IPO-day views) vs first-day return has Spearman 0.16 (n = 287), and 0.32 among firms with a pre-IPO article (n = 238). These are among the strongest associations in the data, and they run from returns to attention.

### 4.5 Company size (post-hoc)

*Added after the main results, at the author's request. Not pre-registered.*

IPO market cap was defined as offer price × shares outstanding immediately after the offering, as stated in the 424B4. Multi-class structures use the stated total, or the "assuming exchange of all units" figure for Up-C structures. ADS deals were converted with the ADS ratio. It is available for 264 of 294 firms; the rest were left missing rather than guessed. No market prices were used.

- **Size tracks attention strongly.** Spearman with pre-IPO views is 0.49, with IPO-day views 0.52, and with post-IPO views 0.54 (n = 264).
- **Size doesn't track returns.** Spearman is −0.03 with first-day return (n = 258) and −0.03 with day-30 return (n = 264).
- **With size as a control,** the first-day attention coefficient rises to **+1.18% per doubling (p = 0.014, n = 258)**, against +0.84% (p = 0.058) on the same 258 firms without it. Among firms of similar size, the better-known ones pop slightly more. Day-30 stays null.

| Size tier | n | Median daily views, before | IPO day | Median daily views, after | Median first-day | Median day-30 |
|---|---|---|---|---|---|---|
| Micro (<$0.3B) | 17 | 0.0 | 0 | 6.8 | 24.4% (n = 17) | 12.7% |
| Small ($0.3–2B) | 81 | 33.3 | 214 | 47.1 | 25.8% | 25.2% |
| Mid ($2–10B) | 129 | 169.0 | 981 | 201.5 | 22.2% | 20.6% |
| Large (>$10B) | 37 | 382.2 | 3,649 | 567.0 | 21.0% | 28.4% |

Returns are roughly flat above micro-cap. The micro tier is small and noisy.

### 4.6 Outlier handling (post-hoc robustness)

Added after the main results, so treat it as exploratory. The confirmatory model compresses extreme returns with log(1 + return). Dropping extreme firms instead gives the following (first-day return, Spec A controls, HC3):

| Outlier handling | n | Effect per doubling of views | p |
|---|---|---|---|
| log(1 + pop), confirmatory | 287 | +0.91% | 0.032 |
| Raw pop, no adjustment | 287 | +1.62% | 0.013 |
| Raw pop, drop top/bottom 1% | 281 | +0.86% | 0.085 |
| Raw pop, drop top/bottom 5% | 257 | +0.40% | 0.355 |
| Raw pop, drop 1.5×IQR outliers (20 firms, almost all pops above ~100%) | 267 | +0.41% | 0.361 |

The sign is positive under every choice, but the effect shrinks by half or more and loses significance once the largest first-day pops are removed. The attention effect is concentrated in a small group of high-attention IPOs with very large pops. That is consistent with an attention-driven demand story, but it also means the headline estimate rests on relatively few firms.

## 5. Limitations

- **Survivorship and matching.** Only IPOs with a confirmed Wikipedia article and usable price data are analysed: 294 of 1,410 operating-company IPOs. Firms with no findable article (the most obscure ones) are absent by construction.
- **Placeholder first-day closes.** For a few firms (fewer than 15) the vendor's close on the SEC first-trade date equals the offer price exactly, which is very unlikely for a real session. Their first-day return is treated as missing and their day-30 return kept. Separately, a first close below 20% of the offer price is treated as not a real IPO session (in practice a ticker now held by another company); both returns are set missing. This rule drops one firm (Sunnova); keeping it moves the first-day p-value from 0.032 to 0.070.
- **Articles created after the IPO.** 49 firms have no pre-IPO article, and their attention is either zero by assumption (Spec A) or excluded (Spec B). Article creation is itself partly a *response* to the IPO.
- **Market-cap coverage.** 264 of 294. The missing cases are mostly complex multi-class and Up-C structures, so they are not missing at random. Treatment of classes and units also varies somewhat across firms.
- **Exclusions.** One Euronext Paris listing was excluded from the US-IPO set. All exclusion checks use SEC data only. Matched firms without a usable return include: firms whose 424B4 says the shares were already listed or quoted (moved to attention-only), tickers that EDGAR now assigns to a different company, firms with no ticker or no cached prices, and firms whose SEC first-trade date has no price bar.
- **Dates.** First trading dates come from the 424B4 (stated date, else the next trading day after the prospectus date, else the closing date minus the settlement cycle). Some IPOs price and trade on the same day, so a few derived dates may be one day late; SEC data can't settle those, so they are left as derived and flagged locally. 15 matched firms with no SEC first-trade date have no return (they were previously dated from the price data).
- **Correlation, not causation.** Attention, media coverage, deal quality and market conditions move together, and the controls don't remove all of that.
- **Multiple comparisons.** Only the four confirmatory estimates were pre-specified. Sector, scan and size results are leads.
- **Small groups.** Any group under 15 firms (for example "Other" sectors, 2022) is suppressed everywhere.

## 6. Future work

- A pre-registered test of the **size-controlled** attention effect on fresh data (for example 2026 IPOs).
- **Price relative to the filing range**, a standard demand signal. It needs parsing of preliminary prospectuses.
- **Broader coverage**, for example small-cap firms via index membership, to reduce the bias toward well-known firms.

## 7. Acknowledgements and licenses

- SEC EDGAR, https://www.sec.gov/edgar: US government public data.
- Wikimedia Pageviews REST API, https://wikimedia.org/api/rest_v1/: CC0.
- Wikidata, https://www.wikidata.org: CC0.
- Wikipedia metadata via the MediaWiki API, https://en.wikipedia.org/w/api.php (article text is CC BY-SA; only titles, redirects and revision dates were used).
- Tiingo end-of-day prices, https://www.tiingo.com: licensed. Only aggregates over at least 15 IPOs are published.
