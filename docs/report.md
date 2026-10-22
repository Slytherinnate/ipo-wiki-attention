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

**Prices (Tiingo).** End-of-day prices for the first trading day and about 30 days later, used only to compute returns. Under the license, only aggregates over at least 15 IPOs are published. Tiingo data was not used to validate any other dataset.

**Usable sample.** 306 firms have views and a valid day-30 return; 286 also have a valid first-day return (see §5 on the 20 placeholder closes). By year: 2019: 46, 2020: 57, 2021: 123, 2022: 11, 2023: 15, 2024: 27, 2025: 27. 2021 is 40% of the sample.

## 3. Methods

**Returns.** First-day return = first close / offer price − 1. Day-30 return = close about 30 calendar days after the first trading day / offer price − 1. Models use ln(1 + return).

**Attention.** The test variable is ln(1 + total views in days −30 to −1). Daily-view comparisons use each firm's average daily views before (days −30..−1) and after (+1..+30), next to its IPO-day (day 0) views, so all three are on the same per-day scale.

**Firms without a pre-IPO article.** 48 firms had no Wikipedia article until after listing. Two treatments were fixed in advance:
- **Spec A (main):** keep them, count them as zero attention, and add a no-article dummy.
- **Spec B (robustness):** drop them.

**Pre-registered model.** The spec was written into `plan.md` and the model notebook *before* the model was run: OLS of ln(1 + return) on ln(1 + pre-IPO 30-day views), with year fixed effects, a foreign-issuer flag and ln(offer price) as controls, using HC3 heteroskedasticity-robust standard errors. The coefficient is reported per doubling of views (coef × ln 2), which is roughly the % change in (1 + return).

**Decision rule.** Attention counts as confirmed for an outcome only if p < 0.05 in Spec A *and* Spec B has the same sign. The rule was added to the spec before running and approved. There is no adjustment across the two outcomes, and that is stated.

**Everything else is exploratory:** sector splits, the variable scan (Benjamini–Hochberg adjusted) and the market-cap analysis.

## 4. Results

### 4.1 Baselines

| | n | Mean | Median | SD | IQR | % positive |
|---|---|---|---|---|---|---|
| First-day return | 286 | 33.2% | 22.4% | 51.7% | 43.1% | 77.3% |
| Day-30 return | 306 | 41.2% | 19.9% | 134.3% | 54.9% | 71.6% |

Three firms have day-30 returns above +500%. They stay in the sample: the models use log returns, and the rank-based checks are insensitive to them. By article group, firms without a pre-IPO article had a median first-day return of 28.0% (n = 46) and a median day-30 return of 29.1% (n = 48). Firms with an article and pre-IPO views had 21.4% (n = 227) and 19.0% (n = 244). A Kruskal–Wallis test across article groups finds no significant difference (first-day p = 0.18; day-30 p = 0.28).

Attention spikes on IPO day. The cross-firm median of daily views averages about 93 per day over the month before, is 540 on day 0, and averages about 122 per day over the month after (main spec, n = 306).

### 4.2 Confirmatory model

| Outcome | Spec | n | Per doubling of views | 95% CI | p | R² | Controls-only R² |
|---|---|---|---|---|---|---|---|
| First-day | A (main) | 286 | +0.88% | +0.03% to +1.73% | 0.042 | 0.128 | 0.120 |
| First-day | B (robust) | 240 | +0.82% | −0.03% to +1.68% | 0.058 | 0.156 | 0.147 |
| Day-30 | A (main) | 306 | +0.23% | −1.03% to +1.50% | 0.717 | 0.101 | 0.101 |
| Day-30 | B (robust) | 258 | +0.26% | −0.97% to +1.50% | 0.675 | 0.108 | 0.108 |

- **First-day:** meets the decision rule, but only just. The effect is small, about one percentage point of (1 + return) per doubling of views, and adds less than 0.01 to R².
- **Day-30:** null.
- **No-article dummy (Spec A):** the largest attention-related term. It is +0.23 for first-day (p < 0.001) and +0.24 for day-30 (p = 0.032). Firms whose article appeared only after listing did *better*, which is hard to square with "attention causes the pop".

### 4.3 Sector heterogeneity (exploratory)

Spec A was re-estimated within each sector with at least 15 firms (HC1 standard errors, since HC3 is undefined when a sector has a year with a single firm). Of 12 tests in Spec A, one has p < 0.05: Health Care day-30, −5.2% per doubling, p = 0.016, n = 43. With 12 tests, about one false positive is expected at that level, and it doesn't hold in Spec B (p = 0.26). No sector shows a reliable first-day effect; Information Technology is the closest (+1.5% per doubling, p = 0.12, n = 105). The "Other" group (n = 14) falls below the publishing threshold and is suppressed.

### 4.4 Reverse direction: the pop drives attention

Grouping firms by first-day return (quintiles of 57–58 firms):

| First-day return quintile | Median first-day return | Median daily views, 30d before | Median views, IPO day | Median daily views, 30d after | Median after/before ratio |
|---|---|---|---|---|---|
| 1 (weakest) | −7.9% | 48.2 | 216 | 61.5 | 1.00 |
| 2 | 8.7% | 171.0 | 604 | 167.8 | 1.03 |
| 3 | 22.6% | 51.4 | 342 | 108.6 | 1.10 |
| 4 | 40.0% | 124.0 | 1,005 | 165.6 | 1.21 |
| 5 (strongest) | 85.4% | 172.3 | 1,363 | 224.3 | 1.31 |

Pre-IPO attention bounces around across quintiles. IPO-day attention and the after/before ratio rise steadily with the size of the pop. In the exploratory scan, ln(IPO-day views) vs first-day return has Spearman 0.17 (n = 286), and 0.33 among firms with a pre-IPO article (n = 240). These are among the strongest associations in the data, and they run from returns to attention.

### 4.5 Company size (post-hoc)

*Added after the main results, at the author's request. Not pre-registered.*

IPO market cap was defined as offer price × shares outstanding immediately after the offering, as stated in the 424B4. Multi-class structures use the stated total, or the "assuming exchange of all units" figure for Up-C structures. ADS deals were converted with the ADS ratio. It is available for 282 of 306 firms; the rest were left missing rather than guessed. No market prices were used.

- **Size tracks attention strongly.** Spearman with pre-IPO views is 0.46, with IPO-day views 0.49, and with post-IPO views 0.51 (n = 282).
- **Size doesn't track returns.** Spearman is −0.02 with first-day return (n = 264) and −0.01 with day-30 return (n = 282).
- **With size as a control,** the first-day attention coefficient rises to **+1.14% per doubling (p = 0.016, n = 264)**, against +0.87% (p = 0.055) on the same 264 firms without it. Among firms of similar size, the better-known ones pop slightly more. Day-30 stays null.

| Size tier | n | Median daily views, before | IPO day | Median daily views, after | Median first-day | Median day-30 |
|---|---|---|---|---|---|---|
| Micro (<$0.3B) | 18 | 2.7 | 23 | 7.9 | 13.5% (n = 16) | 12.5% |
| Small ($0.3–2B) | 89 | 37.0 | 210 | 50.8 | 25.8% | 21.4% |
| Mid ($2–10B) | 137 | 172.3 | 819 | 201.5 | 21.9% | 19.8% |
| Large (>$10B) | 38 | 376.0 | 3,221 | 518.4 | 21.4% | 27.3% |

Returns are roughly flat above micro-cap. The micro tier is small and noisy.

## 5. Limitations

- **Survivorship and matching.** Only IPOs with a confirmed Wikipedia article and usable price data are analysed: 306 of 1,410 operating-company IPOs. Firms with no findable article (the most obscure ones) are absent by construction.
- **Placeholder first-day closes.** For 20 firms the vendor's first close equals the offer price exactly, which is very unlikely for a real session. Their first-day return is treated as missing and their day-30 return kept.
- **Articles created after the IPO.** 48 firms have no pre-IPO article, and their attention is either zero by assumption (Spec A) or excluded (Spec B). Article creation is itself partly a *response* to the IPO.
- **Market-cap coverage.** 282 of 306. The missing cases are mostly complex multi-class and Up-C structures, so they are not missing at random. Treatment of classes and units also varies somewhat across firms.
- **Exclusions.** One Euronext Paris listing was excluded from the US-IPO set. Ten matched firms were dropped for invalid price histories: 8 with a prior listing, 1 reused ticker, 1 late price start.
- **Dates.** 15 usable firms have an unconfirmed first trading date and are anchored on the prospectus filing date.
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
