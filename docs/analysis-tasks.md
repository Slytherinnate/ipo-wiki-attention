# Analysis tasks: EDA, Modeling, Viz, Write-up

Matches plan.md v3. Budgets: EDA 3 h (180 min), Modeling 6 h (360), Viz 4 h (240), Write-up 3.5 h (210), total 16.5 h. Minutes are estimates, and every task's minutes add up to its section budget.

**Inputs from earlier steps:**
- `titles_v2_*.csv` and `review_*.csv` with `keep_drop`;
- `data/processed/views_*/<CIK>.csv`;
- `offer_prices_*.csv`;
- `data/prices/<TICKER>.csv` (vendor data, local only).

---

## Part 0: Pre-registration (do this BEFORE looking at any returns; 20 min, counted in EDA)
Write this section into `docs/preregistration.md` and commit it **with a date before the first returns calculation**. Changing it later is allowed, but the change must be logged with a reason.

**Hypotheses:**
- **H1 (primary):** higher pre-IPO attention goes with a higher first-day return. Spearman ρ(A_pre, R1) > 0 across all kept IPOs.
- **H2:** higher pre-IPO attention goes with a lower 30-day return *relative to the first close* (attention-driven overpricing that fades). ρ(A_pre, R30_from_close) < 0.
- **H3:** the attention–R1 relationship differs by sector. Interaction terms are jointly non-zero.
- **H4 (descriptive, not tested):** attention peaks on or after the IPO day rather than before (the lead/lag event-study chart).

**Metric definitions (exact):**
- **Day 0** = `first_trade_date` (review column), or the first price date on or after `filing_date_424b4`.
- **Attention window, pre:** days −30 to −1 relative to day 0 (calendar days), summed daily user views across the main title and `old_titles`. A missing day counts as 0.
- **A_pre** = log(1 + pre-window views). **A_post** = log(1 + views on days 0 to +29).
- **Normalized attention** (robustness): A_pre minus the log of the median daily views of the 50 controls over the same calendar window. This adjusts for site-wide traffic changes over time.
- **Article created after day 0, or no article:** A_pre = 0 (log(1+0)). Also add a dummy `has_article_pre` (1 if the article existed before day −30).
- **Offer price P0** = `offer_price_checked` if filled, otherwise `offer_price`.
- **R_open** = Open(day 0) / P0 − 1, "the pop".
- **R1** (first-day return) = Close(day 0) / P0 − 1.
- **R30** = Close(trading day 30, where day 0 is trading day 1) / P0 − 1.
- **R30_from_close** = Close(trading day 30) / Close(day 0) − 1.
- **Prices:** unadjusted for day 0. For day 30, check for splits between day 0 and day 30. If there's a split, use split-adjusted prices for both endpoints.
- **Sector:** the SIC-based `sector`. Sectors with fewer than 15 kept IPOs are merged into `Other (small sectors)`, decided once, before modeling.
- **Exclusions:** `keep_drop=drop`, `offer_price_status=unresolved`, `review_code=DATE_UNRESOLVED`, and IPOs without prices. Count every exclusion in a table; never drop silently.

**Statistical methods:**
- **Spearman rank correlation**, chosen because returns are skewed. Report ρ, an n, and a **95% bootstrap CI** (10,000 resamples, percentile method, seed 42).
- **OLS regression:** `R1 ~ A_pre + log(P0) + sector dummies + year dummies`, with **HC3 robust standard errors** (statsmodels). The same for R30 and R30_from_close.
  - H3 adds `A_pre × sector` interactions, tested jointly with a Wald F-test.
  - *log(offer size) would be better than log(P0), but share counts aren't parsed yet. Add them if time allows (unverified feasibility).*
- **Multiple comparisons:** per-sector correlations (one per sector × 3 return measures) get **Benjamini–Hochberg FDR at q = 0.10**. H1–H3 are the pre-registered primary tests and get no correction, but are reported as such.
- **Effect size in plain words:** "moving from the 25th to the 75th percentile of A_pre goes with an X-point change in median R1."

**Robustness checks (each one is a single row in the results table):**
1. Normalized attention instead of raw.
2. Excluding `foreign_ads` and `foreign_ordinary` rows.
3. Excluding `PARENT_SUB_PROXY` rows.
4. Excluding articles created less than 30 days before the IPO (`has_article_pre = 0`).
5. Winsorizing returns at the 1st and 99th percentiles.
6. A pre-window of −14 to −1 instead of −30 to −1.
7. By era: 2019–2021 vs. 2022–2025.
8. Placebo: shuffle A_pre across IPOs 1,000 times and record how often |ρ| is at least the real value (a permutation p-value).

**Publish / keep-local rule (applies to every output):**
- **LOCAL-ONLY, third-party ToS:** anything derived from a secondary public price source (`year_source`, the early offer-price cross-check, `candidates.csv`, `titles.csv`). It is never published, never cited, and not deleted. Published IPO years, dates and offer prices come **only from SEC EDGAR** (the universe and the 424B4).
- **Publish** (git, README, dashboard):
  - attention data (CC0);
  - offer prices (SEC public filings);
  - aggregate return statistics: medians, IQRs, distributions as binned histograms, ρ, regression coefficients, sector-level tables with n ≥ 15.

  Publishing these **requires the vendor's written OK** (see setup-checklist step 8). Until then, nothing based on returns is pushed.
- **Keep local** (`data/prices/`, `data/returns_per_ipo*.csv`, both gitignored):
  - raw OHLC prices;
  - per-IPO returns;
  - any chart that shows per-IPO price or return points.

  Per-IPO returns + the public P0 would reconstruct the close, which Tiingo's terms explicitly forbid, and Alpha Vantage's terms say nothing about it.

---

## Part 1: EDA (180 min)

| # | Task | Inputs | Output | Min |
|---|---|---|---|---|
| E0 | Pre-registration (Part 0) | — | `docs/preregistration.md` committed | 20 |
| E1 | Build the analysis table: one row per kept IPO (CIK, name, sector, year, day 0, P0, A_pre, A_post, has_article_pre, listing_type, flags) | review/titles CSVs, views, offer prices | `data/analysis_base.parquet` (no prices, publishable) | 35 |
| E2 | Attrition table: universe → operating → article found → kept → has P0 → has prices, per year and sector | all CSVs | `reports/tables/attrition.csv` + bar chart | 25 |
| E3 | Coverage chart: % of IPOs with a pre-IPO article, by sector and year | E1 | `reports/figures/coverage.png` | 15 |
| E4 | Attention distributions: histogram of A_pre, by sector (box plot) | E1 | 2 figures | 20 |
| E5 | Event-study attention chart (H4): median normalized daily views from day −60 to +60, all kept IPOs, with an IQR band | views | `reports/figures/event_study.png` | 30 |
| E6 | Compute returns locally (R_open, R1, R30, R30_from_close) with the exclusion table | prices, E1 | `data/returns_per_ipo.csv` (**local**) | 25 |
| E7 | Returns sanity check: any |R1| > 300% or day-0 gaps > 2 trading days? Check each against the review log | E6 | notes in `notebooks/01_eda.ipynb` | 10 |

**Done when:**
- [ ] Pre-registration committed.
- [ ] The attrition numbers add up at every step.
- [ ] 5 written findings at the top of the notebook (attention and coverage only, no return claims yet).
- [ ] No return values in any committed file.

## Part 2: Modeling (360 min)

| # | Task | Output | Min |
|---|---|---|---|
| M1 | Freeze the sector grouping (n ≥ 15 rule) and write it into preregistration.md | updated doc | 10 |
| M2 | H1: Spearman ρ(A_pre, R1), all IPOs, with a bootstrap CI | `reports/tables/h1.csv` | 30 |
| M3 | H2: ρ(A_pre, R30_from_close), plus ρ(A_pre, R30) | `h2.csv` | 25 |
| M4 | OLS regressions with HC3 for R1, R30, R30_from_close | `regressions.csv` (coefficients, SE, CI, n) | 60 |
| M5 | H3: interaction model with a Wald test | `h3.csv` | 40 |
| M6 | Per-sector ρ for 3 return measures, with BH-FDR q = 0.10 | `sector_corr.csv` | 40 |
| M7 | Robustness checks 1–8 | `robustness.csv` (one row each) | 90 |
| M8 | Effect sizes in plain words (25th→75th percentile) | text in notebook | 20 |
| M9 | Assumption checks: residual plot, influential points (Cook's distance), with the top 5 noted in local-only notes | notebook | 30 |
| M10 | Results summary: what supports or rejects H1–H3, honestly | `reports/results_summary.md` | 15 |

**Done when:**
- [ ] Every pre-registered test is reported, including the null results.
- [ ] Every test has an n and a CI.
- [ ] FDR is applied to the sector tests.
- [ ] Robustness results are shown next to the main results.
- [ ] Tables contain only aggregates.

**Pitfalls:**
- Returns are heavy-tailed, so trust Spearman and the bootstrap over plain OLS p-values.
- Small sectors: don't interpret any sector with n < 15.
- Attention can be *caused* by the expected pop (hype). This is correlation, not causation. Say so.

## Part 3: Viz, aggregates only (240 min)
Streamlit app `app/streamlit_app.py`. Reads **only** `analysis_base.parquet` (attention) and the aggregate tables in `reports/tables/`.

| # | Task | Min |
|---|---|---|
| V1 | Page "Coverage": attrition funnel and the coverage by sector and year chart | 35 |
| V2 | Page "Attention": event-study chart with a sector filter; per-IPO attention lookup (attention is CC0, so it's OK) | 50 |
| V3 | Page "Returns" (aggregates only): median R1, R30 and R30_from_close by sector with IQR bars; ρ with CI by sector (forest plot); attention quintile vs. median R1 (bars); every chart shows n | 70 |
| V4 | Page "Method & licenses": data sources, the publish rule, attribution (Wikimedia CC0, SEC EDGAR, the vendor), caveats | 25 |
| V5 | Check that no per-IPO return or price reaches the app: search the code and data for return columns at the per-IPO level | 15 |
| V6 | Deploy (Streamlit Community Cloud or a Pi). Hosting terms weren't re-verified | 30 |
| V7 | 3 screenshots for the README | 15 |

**Done when:**
- [ ] The app loads in under 5 s.
- [ ] Every chart shows n.
- [ ] V5 passes.
- [ ] Deployed, *or* screenshots are included if deployment waits on the license reply.

## Part 4: Write-up (210 min)
`README.md`, structured as an analyst memo.

| # | Task | Min |
|---|---|---|
| W1 | The answer in the first 3 lines (H1–H3 results with n and CI) | 25 |
| W2 | Data and licenses: EDGAR (universe, offer prices), Wikimedia pageviews (CC0), the vendor (quoted terms, plus a note on the permission email) | 25 |
| W3 | Method in 8 bullets: the universe rules, title matching, the review and QA error rate, metric definitions, statistical methods | 35 |
| W4 | 4 key figures (coverage, event study, sector medians, ρ forest plot) | 25 |
| W5 | Limitations: coverage bias toward notable IPOs, causation, 424B4 date ±1 day, the SIC-based sector approximation, possible survivorship bias in the vendor's data, matching error rate, direct listings not included | 35 |
| W6 | Reproduce section: setup, `.env`, script order, "prices are not included; fetch with your own key" | 25 |
| W7 | "What I'd do next" (offer size, a lockup-expiry window, other languages) | 10 |
| W8 | Final check: run the V5 check on the repo, `git status`, and confirm no `.env` or prices are committed; pin the repo | 30 |

**Done when:**
- [ ] A stranger could re-run it from the README.
- [ ] Every number in the README traces back to a table in `reports/tables/`.
- [ ] Limitations are written down.
- [ ] License status is stated.
