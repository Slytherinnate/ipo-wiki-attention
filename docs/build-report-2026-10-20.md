# Build report: non-price data 2019-2025 (Oct 20, 2026; updated evening: 424B1, deep search, sector v2, Tiingo pull)

Sources: SEC EDGAR (form indexes, submissions JSON, 424B4 covers; about 7 req/s), Wikidata SPARQL, the Wikipedia Action API and the Wikimedia pageviews API (180 req/min or less). No third-party price sites were fetched.
Scripts: `parse_424b4.py` (steps 1-3), `recall_check.py`, `wikidata_ticker_map.py`, `match_all.py` (steps 4-5), `reclassify_search_miss.py`, `build_report.py`. Checkpoints are in `data/universe/checkpoints/` (deal_*, match_*), and the per-title pageview cache is in `data/cache/pv/`.

## Decision log
1. **SPAC flag bug fixed.** The old rule was `"spac" in name`, which matched "Space", "Aerospace", "Rackspace" and "Squarespace". The new rule is SIC 6770, or "acquisition/SPAC/blank check" in the company's name *as of the 424B4 date* (taken from the EDGAR index), or "blank check company" on the 424B4 cover. This restored real IPOs including Circle, Firefly Aerospace, Gemini, Rackspace, Squarespace, Petco, Sun Country, SkyWater and Hydrofarm. Logs: `verify/flag_fix_log*.csv`.
2. **Not-equity filings excluded.** "Funding LLC" securitizations, and covers that show notes or certificates with no shares, are excluded as FUND_OR_TRUST / NOT_EQUITY.
3. **Direct listings are flagged, not excluded.** There are 25 operating rows with DIRECT_LISTING, including Palantir, Coinbase, Slack, Asana and Roblox. They have no offer price, and their first-trade date is blanked because the 424B4 date is not the listing date.
4. **First-trade date.** "stated" means the 424B4 says when trading begins. "derived" means the next NYSE trading day after "Prospectus dated X". "derived_closing" means the closing date minus T+2 (T+1 from 2024-05-28). 15 known IPOs were spot-checked against dates I'm confident of (for example Reddit 3/21/24, Arm 9/14/23, CoreWeave 3/28/25, Cava 6/15/23) and all 15 matched.
5. **Underwriters.** These are taken from the bank block between "expect to deliver" and "Prospectus dated". UW_BLOCK_GUESSED means that block wasn't found and the script fell back to the first 10k characters, so the list is less reliable.
6. **Match order.** Wikidata CIK, then Wikidata ticker (which must share a word with the company name), then ticker-verified search, then the top search hit. NAME_MISMATCH is a new review reason: the ticker was verified on a page whose title doesn't share a word with the company name.
7. **Rule change (Caleb).** An unrelated or missing search hit now goes to REVIEW with SEARCH_MISS (section 3.1) instead of being dropped. The exception is a clearly tiny deal (gross proceeds under $25M), which becomes DROP_TINY_NO_ARTICLE. This moved 529 rows to review and dropped 256. SEARCH_MISS rows get a views file only after a title has been verified.
8. **Anchor date** for views = first_trade_date if known, else the 424B4 filing date. The views window runs from day -120 to day +60 (181 days), missing days are 0, and views from up to 15 redirects are summed.

9. **424B1 IPOs added (Caleb, Oct 20).** Script `add_424b1.py` uses the same filters, plus no earlier 424B1 and not already in the universe. It added 113 companies: 53 operating and 60 excluded as SPACs/funds. The new column `form_type` says 424B4 or 424B1. The column `filing_date_424b4` keeps its name but holds the 424B1 date for those rows.
10. **Follow-on style filers (Caleb confirmed).** Companies that filed a 10-K/10-Q/20-F before their prospectus are excluded from the universe. This was already the rule, so no rows changed.
11. **Direct listings (Caleb confirmed).** `attention_only=1` (26 rows). They are kept in the attention analysis and excluded from the first-day and 30-day return tests.
12. **Sectors.** Communication Services, Utilities and Unknown are grouped into Other. The original sector is kept in `sector_original`.
13. **No size floor (Caleb).** All deals are kept. The $25M tiny cutoff applies only to rows with no Wikipedia article.

14. **Deep search on the 554 SEARCH_MISS rows (Caleb approved; `deep_search_miss.py`, evidence in `verify/deep_search_evidence.csv`).** Methods: M1 live Wikidata P5531 CIK lookup; M2 Wikidata ticker map (P414/P249); M3 Wikipedia search on the legal name, EDGAR former names and stripped variants; M4 exact-title lookup with redirects followed; M5 Wikidata name search to an enwiki sitelink. IDs checked per candidate: CIK, TICKER, NAME, EXCHANGE.
    - **FOUND_STRONG** needs a CIK match, or TICKER + NAME. This is tighter than "any 2 of 4 including ticker or CIK" because recycled tickers produced false hits in the first run (Enact matched Actavis via ACT; Paymentus matched Verifone via PAY). Strong rows become AUTO_KEEP and their pageviews are pulled, unless NO_PRE_IPO_DATA applies, in which case they go to REVIEW.
    - **FOUND_CANDIDATE** goes to REVIEW with code SEARCH_CANDIDATE, with the candidate titles listed in `deep_candidates`.
    - **NO_ARTICLE_CONFIRMED** becomes DROP_NO_ARTICLE_CONFIRMED. The row is kept in the file, and the evidence from each method is in the evidence CSV.
    - **UNCERTAIN** means a method hit an API failure. These rows stay in REVIEW as SEARCH_MISS.
    - Name matching was tightened between runs: version 1 stripped descriptive words such as "Global", so "Venture Global" matched the page "Venture". The version 1 checkpoints are kept in `checkpoints_deep_v1/`. Backups are in `backup_pre_deepsearch_1317/`.
    - **Spot check:** the 10 largest confirmed-no-article deals were checked by exact Wikipedia title: SailPoint, Marqeta, Shoals, Maravai, Sotera Health, Full Truck Alliance, Fluence Energy, Waystar, agilon health and RLX Technology. None of them has an English Wikipedia article. "Venture Global LNG" exists only as a redirect to a section of "Liquefied natural gas".

15. **Sector crosswalk v2** (`scripts/sector_v2.py`, `docs/sector-crosswalk.md`). It adds 23 SIC rules and 29 company overrides for the catch-all SIC codes 7389 and 7340, which covers Airbnb, Peloton, Instacart and Birkenstock. 101 of 1,410 operating rows changed sector; every change is in `verify/sector_v2_changes.csv`. 34 rows with an ambiguous SIC remain flagged. `sector_original` (v1) is kept. Backup: `backup_pre_sectorv2_1722/`.
16. **Tiingo EOD pull (licensed; raw data is local only and per-IPO results are in `data/local_only/`, both gitignored).** Only counts appear here; no per-ticker prices or returns are published. Validation (`scripts/tiingo_validate.py`) uses only EDGAR names and our own dates, and Tiingo data is not compared with any other price source. If the first Tiingo bar is 1 trading day before our derived first-trade date, the derived date is treated as wrong (the stock priced and traded the same day) and the Tiingo date is used for returns.

17. **Tiingo follow-ups (Caleb approved, 7 PM).** Scripts: `apply_tiingo_fixes.py` and `tiingo_recover_reuse.py`; logs: `verify/tiingo_fixes_log.csv` and `verify/tiingo_recover_log.csv`.
    - **Re-anchored dates:** 45 rows had a first Tiingo bar exactly 1 NYSE trading day before our EDGAR-derived date. Their `first_trade_date` was corrected (`first_trade_conf=tiingo_corrected`); the old value is kept in `first_trade_date_edgar`. 41 pageview windows were rebuilt; the other 4 have no verified title yet.
    - **Trading-day gaps:** the validator now measures gaps in trading days instead of calendar days. Two of the 46 rows first identified as one day early (Visionary, Newton Golf) are really 2 trading days early and moved to CHECK_DATE_GAP. Longeveron (the Presidents' Day weekend case) was added.
    - **Pre-listed rows:** the 13 rows that traded before their IPO now have `attention_only=1` and `attention_reason=pre_listed`. Direct listings have `attention_reason=direct_listing`.
    - **Reused tickers:** using Tiingo's public supported-tickers list, the original company's history was recovered for 4 rows: GoHealth (GOCO to GOCOQ), Cue Health (HLTH to HLTHQ), Tron (TRON to SRM, its former ticker) and Axonex (AXNX to MIMI, its former ticker).
    - **Still unresolved:** 6 rows have the original history listed under the same ticker string, which the API resolves to the current holder: Sunnova, GAN, Chindata, DiDi, Grandstand, TheRas. 4 rows have no candidate in the list: Silvergate, G Medical, Alfi, La Rosa.

## Recall check (`verify/recall_check.csv`, EDGAR link per row)
| Year | Found |
|---|---|
| 2019 | 20/20 |
| 2020 | 18/20 |
| 2021 | 19/20 |
| 2022 | 16/20 |
| 2023 | 19/20 |
| 2024 | 18/20 |
| 2025 | 20/20 |

Most misses are errors in my test sample: wrong year (Intensity, Atlas Energy), a de-SPAC (Amprius), a non-US listing (Galderma), not an IPO (Universal Technical), and duplicates (Instacart = Maplebear, Wish = ContextLogic, which is present). Excluding those, recall is 136/139.

There are three genuine method gaps:
- **424B1 filers** such as Nubank. Between 27 and 68 CIKs a year file a 424B1 without a 424B4 (upper bound; it includes resales).
- **Issuers already filing 10-Ks/10-Qs** before their IPO, such as Hanover Bancorp. The rule treats these as follow-on offerings.
- **Re-IPOs** such as Warner Music. These are excluded by design.

The direct-listing negative controls (Slack, Palantir, Asana, Coinbase, Roblox) are in the universe and flagged DIRECT_LISTING.

## Stage counts by year
| year   |   universe_prospectus |   excluded_spac_fund |   operating |   from_424b1 |   attention_only |   priced |   matched |   auto_keep |   review |   review_search_left |   views_files |   no_article |
|:-------|----------------------:|---------------------:|------------:|-------------:|-----------------:|---------:|----------:|------------:|---------:|---------------------:|--------------:|-------------:|
| 2019   |                   229 |                   61 |         168 |            8 |                6 |      162 |        92 |          39 |       65 |                   12 |            92 |           64 |
| 2020   |                   482 |                  253 |         229 |           15 |                5 |      215 |        88 |          33 |       74 |                   20 |            88 |          122 |
| 2021   |                  1040 |                  621 |         419 |           12 |               10 |      408 |       206 |          91 |      135 |                   20 |           206 |          193 |
| 2022   |                   193 |                   95 |          98 |            3 |                3 |       95 |        34 |           4 |       33 |                    3 |            34 |           61 |
| 2023   |                   172 |                   47 |         125 |            5 |                2 |      120 |        40 |          11 |       32 |                    3 |            40 |           82 |
| 2024   |                   224 |                   63 |         161 |            6 |                2 |      156 |        60 |          18 |       52 |                   10 |            60 |           91 |
| 2025   |                   363 |                  153 |         210 |            4 |               11 |      198 |        80 |          24 |       61 |                    6 |            80 |          125 |
| total  |                  2703 |                 1293 |        1410 |           53 |               39 |     1354 |       600 |         220 |      452 |                   74 |           600 |          738 |

## By sector
| sector                 |   operating |   priced |   auto_keep |   review |   no_article |   kept_or_review |
|:-----------------------|------------:|---------:|------------:|---------:|-------------:|-----------------:|
| Health Care            |         481 |      469 |          19 |      110 |          352 |              129 |
| Information Technology |         270 |      258 |          89 |       90 |           91 |              179 |
| Consumer Discretionary |         204 |      198 |          42 |       85 |           77 |              127 |
| Industrials            |         142 |      139 |          18 |       47 |           77 |               65 |
| Financials             |         137 |      131 |          29 |       56 |           52 |               85 |
| Other                  |          51 |       42 |           7 |       12 |           32 |               19 |
| Consumer Staples       |          47 |       46 |          11 |       20 |           16 |               31 |
| Energy                 |          28 |       24 |           0 |       12 |           16 |               12 |
| Real Estate            |          28 |       25 |           3 |       10 |           15 |               13 |
| Materials              |          22 |       22 |           2 |       10 |           10 |               12 |
| total                  |        1410 |     1354 |         220 |      452 |          738 |              672 |

## Deal-field coverage % (operating rows)
| year   |   offer_price_% |   shares_% |   gross_% |   underwriters_% |   uw_block_exact_% |   trade_date_any_% |
|:-------|----------------:|-----------:|----------:|-----------------:|-------------------:|-------------------:|
| 2019   |            96.4 |       93.5 |      91.1 |             93.5 |               44   |               93.5 |
| 2020   |            93.9 |       95.6 |      90   |             89.1 |               49.3 |               94.3 |
| 2021   |            97.4 |       94.7 |      92.6 |             91.2 |               59.7 |               94.7 |
| 2022   |            96.9 |       89.8 |      86.7 |             80.6 |               59.2 |               89.8 |
| 2023   |            96   |       86.4 |      82.4 |             71.2 |               46.4 |               93.6 |
| 2024   |            96.9 |       85.7 |      82.6 |             68.9 |               55.9 |               92.5 |
| 2025   |            94.3 |       80.5 |      76.2 |             59   |               40.5 |               86.2 |
| all    |            96   |       90.5 |      87.1 |             81.3 |               51.6 |               92.6 |

## First-trade-date confidence
| year   |   derived |   derived_closing |   stated |   tiingo_corrected |   unknown |
|:-------|----------:|------------------:|---------:|-------------------:|----------:|
| 2019   |       122 |                30 |        0 |                  5 |        11 |
| 2020   |       178 |                32 |        3 |                  3 |        13 |
| 2021   |       328 |                52 |        1 |                 16 |        22 |
| 2022   |        82 |                 3 |        0 |                  3 |        10 |
| 2023   |        99 |                13 |        0 |                  5 |         8 |
| 2024   |       135 |                 9 |        0 |                  5 |        12 |
| 2025   |       154 |                18 |        1 |                  8 |        29 |
| total  |      1098 |               157 |        5 |                 45 |       105 |

## Deal flags (operating rows)
| deal_flags           |   count |
|:---------------------|--------:|
| UW_BLOCK_GUESSED     |     682 |
| WARRANTS_ON_COVER    |     249 |
| NO_SHARES_FOUND      |     134 |
| UNITS                |     100 |
| NO_PRICE_FOUND       |      56 |
| DIRECT_LISTING       |      26 |
| PRICE_RANGE_ON_COVER |       5 |

## Review reasons (REVIEW rows; a row can have several)
| reasons              |   count |
|:---------------------|--------:|
| SEARCH_UNVERIFIED    |     309 |
| FOREIGN_ADR          |     149 |
| NO_PRE_IPO_DATA      |      64 |
| SEARCH_CANDIDATE     |      49 |
| MANY_REDIRECTS       |      43 |
| NAME_MISMATCH        |      29 |
| SEARCH_MISS          |      23 |
| DISAMBIG             |      23 |
| NO_VIEWS             |       9 |
| SEARCH_MISS_RESOLVED |       2 |
| LIST_PAGE            |       2 |

## Match method (all operating rows)
| match_method           |   count |
|:-----------------------|--------:|
| search_top_hit         |     971 |
|                        |     148 |
| search_ticker_verified |     115 |
| wikidata_cik           |     114 |
| wikidata_ticker        |      57 |
| deep_strong            |       5 |

## Views files
600 rows -> data/processed/views/<CIK>.csv (181 days each)

## Deep search on 554 SEARCH_MISS rows: class by year
| year   |   FOUND_CANDIDATE |   FOUND_STRONG |   NO_ARTICLE_CONFIRMED |   UNCERTAIN |   total |
|:-------|------------------:|---------------:|-----------------------:|------------:|--------:|
| 2019   |                 5 |              0 |                     58 |           7 |      70 |
| 2020   |                13 |              2 |                    103 |           6 |     124 |
| 2021   |                15 |              1 |                    149 |           5 |     170 |
| 2022   |                 3 |              0 |                     23 |           0 |      26 |
| 2023   |                 1 |              0 |                     33 |           2 |      36 |
| 2024   |                 9 |              1 |                     44 |           1 |      55 |
| 2025   |                 3 |              1 |                     67 |           2 |      73 |
| total  |                49 |              5 |                    477 |          23 |     554 |

## Class by sector
| sector                 |   FOUND_CANDIDATE |   FOUND_STRONG |   NO_ARTICLE_CONFIRMED |   UNCERTAIN |   total |
|:-----------------------|------------------:|---------------:|-----------------------:|------------:|--------:|
| Consumer Discretionary |                 7 |              0 |                     26 |           1 |      34 |
| Consumer Staples       |                 0 |              0 |                      8 |           0 |       8 |
| Energy                 |                 3 |              0 |                     13 |           0 |      16 |
| Financials             |                 5 |              0 |                     38 |           1 |      44 |
| Health Care            |                12 |              1 |                    273 |          16 |     302 |
| Industrials            |                 7 |              2 |                     32 |           2 |      43 |
| Information Technology |                13 |              1 |                     56 |           3 |      73 |
| Materials              |                 1 |              0 |                      5 |           0 |       6 |
| Other                  |                 1 |              0 |                     16 |           0 |      17 |
| Real Estate            |                 0 |              1 |                     10 |           0 |      11 |
| total                  |                49 |              5 |                    477 |          23 |     554 |


## Tiingo returns coverage (642 rows; counts only)
| returns_status        |   count |
|:----------------------|--------:|
| OK                    |     539 |
| NO_DATA               |      41 |
| OK_DATE_UNCHECKED     |      35 |
| INVALID_PRIOR_LISTING |      13 |
| INVALID_LATE_START    |       6 |
| CHECK_DATE_GAP        |       5 |
| INVALID_TICKER_REUSE  |       3 |

Usable returns (status OK or OK_DATE_UNCHECKED; attention-only rows excluded):
| decision   |   2019 |   2020 |   2021 |   2022 |   2023 |   2024 |   2025 |   total |
|:-----------|-------:|-------:|-------:|-------:|-------:|-------:|-------:|--------:|
| AUTO_KEEP  |     34 |     30 |     81 |      4 |      9 |     17 |     23 |     198 |
| REVIEW     |     55 |     61 |    113 |     25 |     26 |     47 |     49 |     376 |
| total      |     89 |     91 |    194 |     29 |     35 |     64 |     72 |     574 |

## Top issues
1. **Review queue is now 452 rows** (it was 932). 49 are SEARCH_CANDIDATE (about 2 min each), 23 are leftover SEARCH_MISS (about 2.5 min each) and 380 have other flags (about 1.5 min each). **Estimate: about 12 h of review plus about 3 h of QA, roughly 15 h in total.** That still takes about half of the 20-30 h budget.
2. **Coverage is low:** 477 of the 554 search misses are confirmed to have no English Wikipedia article (273 of them in Health Care). Only 5 were found strong. Health Care's attention sample will be thin.
3. **Underwriter coverage is 59% in 2025.** Gross-proceeds coverage is 76% in 2025.
4. **The 53 new 424B1 IPOs are lower quality:** 38 have an offer price.
5. **Offer-price flags to review:** see the deal-flag table. Price range from the S-1/A was not attempted (0% coverage).
6. **Pageviews:** files cover day -120 to +60 with missing days = 0. New files were written for the 5 FOUND_STRONG rows.
