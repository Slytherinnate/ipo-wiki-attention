# Review checklist: manual review of `data/universe/review_worksheet.xlsx`

> **Updated 2026-10-20.** This replaces the per-year `review_YYYY.csv` procedure. It matches the current rules: deep search, sector crosswalk v2, the 424B1 additions, and the Tiingo date corrections. The old 1.5 h cap no longer applies. **The budget is now about 13.5 h of review plus about 1.5 h of QA, roughly 15 h in total.**

## 0. The rules in one screen
- **Strong match** means the Wikipedia article's company is ours by **CIK** (Wikidata P5531 equals the CIK) **or by ticker and name together**. A ticker alone is never enough, because tickers get reused (for example ACT was Actavis before it was Enact).
- **Own standalone article only.** A redirect to a *section* of another page doesn't count, and neither does a list page or a parent company's page. For example, "Venture Global LNG" redirects to "Liquefied natural gas#Trade", so it counts as no article.
- **Sources allowed:** Wikipedia (the article, its history and its move log), Wikidata, and SEC EDGAR pages (company page, 424B4/424B1, 8-K press releases). **Never open price or quote sites** (Yahoo, Google Finance, Nasdaq quote pages, secondary price aggregators and so on), including for dates.
- **Never edit script columns.** Only fill the 6 blank columns at the right of the sheet.
- **When in doubt, choose `unsure` and write a note.** Don't guess.

## 1. Columns you fill (dropdowns in the .xlsx; allowed values are on the `allowed_values` sheet)
| Column | Allowed values | Fill when |
|---|---|---|
| `decision` | `keep`, `drop`, `unsure` | every row with a TITLE task |
| `chosen_title` | the exact Wikipedia page heading, copied from the page | `decision=keep` and the title differs from `final_title`, or `final_title` is blank |
| `sector_confirm` | `ok`, or one of the 10 sector names | every row with a SECTOR task |
| `date_confirm` | `ok`, `wrong`, `unresolved` | every row with a DATE task (if `wrong`, put the correct date `YYYY-MM-DD` and its source in `notes`) |
| `review_code` | one code from section 5 | every row |
| `notes` | one short sentence | whenever you chose `unsure`, `wrong` or a changed sector, or anything was odd |

Tip: filter on `session`, then work top to bottom in `order`.

## 2. Links in every row
- `wikipedia_url`: the script's current title. `candidate_url`: the deep-search best candidate. `wikipedia_search_url`: full-text search on the legal name.
- `wikidata_url` / `wikidata_search_url`: check P5531 (CIK), P414 (exchange) with its P249 qualifier (ticker), and the en-wiki sitelink.
- `edgar_company_url`: legal name, **former names**, tickers, exchange, SIC. `edgar_filing_url`: the IPO prospectus (the cover page shows the ticker, exchange and price). `edgar_8k_url`: the 8-K list (the pricing or closing press release around the IPO date).

## 3. Step-by-step per row type (with counts in the current worksheet)

### Session 1 (about 36 min): quick wins
**DATE_CHECK: 5 rows (about 4 min each).** These are Adamas One, Visionary Holdings, Newton Golf, Springview and 3 E Network. Our EDGAR-based first trade date (`date_to_check`) disagreed with the first trading day in our licensed price feed by 1 to 2 trading days.
1. Open `edgar_8k_url`. Find the 8-K filed within about 10 days of `filing_date_424b4`, and open its press-release exhibit (EX-99.1).
2. Look for "began trading on …", "expected to begin trading on …", or the pricing date. Shares normally start trading the business day after pricing, unless the release says otherwise.
3. If there's no 8-K, open `edgar_filing_url` and search for "begin trading" and "Prospectus dated".
4. If the date matches `date_to_check`: `date_confirm=ok`, `review_code=DATE_CONFIRMED`. If it doesn't match: `date_confirm=wrong`, put the date and source in `notes` (e.g. "2024-10-17 per 8-K EX-99.1"), `review_code=DATE_CORRECTED`. If nothing states it: `date_confirm=unresolved`, `review_code=DATE_UNRESOLVED`. That row stays out of the return tests.
5. These rows also have a TITLE task. Do it as well, using the procedure for their `script_reasons`.

**SECTOR_ONLY: 16 rows (about 1 min each).** These are auto-kept rows whose sector is one of the **29 judgment overrides** in `docs/sector-crosswalk.md`. The other 13 overrides are review rows; do their SECTOR task alongside their TITLE task.
1. Read `sector_override_reason`. Open `edgar_company_url` and read the business description, or the first paragraph of the 424B4 "Prospectus Summary".
2. Ask: is the company's main revenue source what the reason says?
3. If yes: `sector_confirm=ok`, `review_code=SECTOR_CONFIRMED`. If no: choose the better sector, `review_code=SECTOR_CHANGED`, and give a one-line reason in `notes`.
4. Rules of thumb (GICS-style, not official GICS):
   - Payments and fintech go in Financials.
   - Ride-hailing goes in Industrials.
   - Delivery and travel marketplaces go in Consumer Discretionary; grocery goes in Consumer Staples.
   - Healthcare software goes in Health Care.
   - Ad tech and online media go in Other (Communication Services is grouped into Other).

### Session 2 (about 3.2 h): deep-search results
**FOUND_CANDIDATE: 48 rows (about 2.5 min each).** Deep search found a page with *some* evidence, listed in `deep_candidates` as `Title [IDS]`, where IDS are CIK, TICKER, NAME and EXCHANGE.
1. Open `candidate_url`, then check the infobox and lead.
   - Is it a standalone article about *this company*, not a person, product, parent company or list?
   - Is the ticker or exchange in the infobox the same as `tickers`/`exchanges`?
   - Is the company name (or a former name from `edgar_company_url`) in the title or lead?
2. Strong (ticker and name match, or Wikidata P5531 equals our CIK): `decision=keep`, `chosen_title=<heading>`, `review_code=CANDIDATE_CONFIRMED`.
3. If the candidate is wrong, try the other titles in `deep_candidates`, then the search protocol in section 4.
   - A verified article is found: keep it with `review_code=MATCH_FOUND_MANUAL`.
   - Nothing verified: `decision=drop`, `review_code=CANDIDATE_REJECTED`.
4. If the only "article" is a section redirect: `decision=drop`, `review_code=SECTION_REDIRECT_ONLY`.

**SEARCH_MISS_UNCERTAIN: 23 rows (about 3 min each).** Deep search failed partway (an API error), so nothing has been ruled out. Run section 4 in full.
- Found and verified: `keep`, `MATCH_FOUND_MANUAL`.
- Nothing found: `drop`, `NO_ARTICLE`.
- Only a section redirect: `drop`, `SECTION_REDIRECT_ONLY`.

### Session 3 (about 1.6 h): wrong-page risks
**NAME_MISMATCH: 29 rows (about 2 min each).** The ticker was found on a page whose title shares no word with the company name.
1. Open `wikipedia_url`.
2. If it's the same company under a new or old name (check the former names at `edgar_company_url`): `keep`, `chosen_title`, `REDIRECT_OK`.
3. If it's a parent or subsidiary: use `PARENT_SUB_FIXED` if a separate article for the issuer exists. Use `PARENT_SUB_PROXY` if the page's lead is about the issuer's business (say which in `notes`).
4. Otherwise, if it's a fund, index or another company that happens to list the ticker: `drop`, `WRONG_TARGET`. Then run section 4 once.

**DISAMBIG: 22 rows (about 1.5 min each).** Open the disambiguation page.
- An entry exists for the company: `keep`, `chosen_title`, `DISAMBIG_RESOLVED`.
- No entry for the company: run section 4, then `drop` with `NO_ARTICLE` if nothing is found.

**LIST_PAGE: 2 rows (about 2 min each).** List pages never count.
- Section 4 finds a real article: `keep`, `MATCH_FOUND_MANUAL`.
- Otherwise: `drop`, `WRONG_TARGET`.

### Session 4 (about 7.1 h; split into 4 blocks of about 70 rows): search hits that weren't ticker-verified
**SEARCH_UNVERIFIED: 281 rows (about 1.5 min each).** These are top search hits that share a word with the name but weren't ticker-verified.
1. Open `wikipedia_url`. Check the infobox ticker and exchange, or the lead text, against `tickers`/`exchanges` and the legal name.
2. Both ticker and name match: `keep`, `review_code=REDIRECT_OK` if the title differs from the legal name, else `MATCH_FOUND_MANUAL`.
3. A different entity (person, place, product, word): `drop`, `WRONG_TARGET`, then run section 4 once. Keep the verified article if you find one.
4. Same name but no ticker on the page (common for small issuers): keep only if Wikidata P5531 equals the CIK, or the article names the IPO or exchange listing. Otherwise choose `unsure` and add a note.

### Session 5 (about 1 h): attention-data checks
**NO_PRE_IPO_DATA: 38 rows (about 1.5 min each).** The page view data starts less than 30 days before the IPO.
1. Check that the title is right, as in Session 4.
2. Open the article's history (`?action=history`, then the oldest edit).
   - Created after, or within 30 days before, the IPO: `keep`, `ARTICLE_AFTER_IPO`. The model treats pre-IPO attention as 0.
   - Created earlier: check the move log (`Special:Log?type=move&page=<title>`). If there's an old title, put it in `notes` as "old title: X", with `OLD_TITLES_ADDED`.

**NO_VIEWS: 4 rows (about 1.5 min each).** Check the title.
- Right page with genuinely low attention: `keep`, `LOW_VIEWS_REAL`. Never drop a row just because its views are small.
- Wrong page: handle it as SEARCH_UNVERIFIED.

**Extra tasks inside other rows:**
- **ADR (156 rows):** use the 424B4 cover to note in `notes` whether the shares are ADS or ordinary shares (e.g. "ADS"). Use `FOREIGN_CHECKED` only if that row has no other code to record. Foreign issuers stay in.
- **MANY_REDIRECTS (43 rows):** check the move log as above for real former main titles from 2018 onward.

## 4. Manual search protocol (run in this order; stop at the first verified hit)
1. Search Wikipedia for the exact legal name without "Inc./Corp./Ltd./Holdings".
2. Search the name + "company".
3. Search each EDGAR **former name** (from `edgar_company_url`).
4. Search the ticker + "NYSE" or "Nasdaq".
5. Use `wikidata_search_url`: an item with P5531 equal to our CIK, or a matching P249 ticker, and an en-wiki sitelink.

A hit is **verified** only if it's a standalone article about the issuer and it meets one of these:
- (a) its Wikidata P5531 equals our CIK; or
- (b) the infobox or lead shows our ticker *and* its name (or a former name) matches.

## 5. Review codes (complete list; the dropdown in the .xlsx)
- **Title matching:** `MATCH_FOUND_MANUAL`, `CANDIDATE_CONFIRMED`, `CANDIDATE_REJECTED`, `NO_ARTICLE`, `SECTION_REDIRECT_ONLY`, `ARTICLE_AFTER_IPO`, `REDIRECT_OK`, `WRONG_TARGET`, `PARENT_SUB_FIXED`, `PARENT_SUB_PROXY`, `OLD_TITLES_ADDED`, `RENAME_IRRELEVANT`, `LOW_VIEWS_REAL`, `DISAMBIG_RESOLVED`
  - `RENAME_IRRELEVANT`: the move log shows a rename that doesn't matter (before 2018 or cosmetic), so no old title is added.
- **Foreign issuers:** `FOREIGN_CHECKED`
- **Dates:** `DATE_CONFIRMED`, `DATE_CORRECTED`, `DATE_UNRESOLVED`
- **Sectors:** `SECTOR_CONFIRMED`, `SECTOR_CHANGED`
- **Time cap:** `NOT_REVIEWED_CAP`, for rows left undone if Caleb stops early. They're dropped from the analysis, never silently skipped.

## 6. Suggested schedule and breaks
- Work in **50-minute blocks with a 10-minute break**. Take a long break after every 3 blocks.
- **Day 1:** Sessions 1, 2 and 3, about 5 h.
- **Day 2:** Session 4, blocks 1–3, about 5.3 h.
- **Day 3:** Session 4, block 4, then Session 5 and QA, about 4.6 h.
- Save the .xlsx after every block. If a row takes more than 5 minutes, choose `unsure`, write a note, and move on.

## 7. QA spot-check (about 1.5 h, at the end)
1. **Auto-keep check:** take a random 30 of the 220 AUTO_KEEP rows in `titles_v2_all.csv` (seed 42). Check each title with the verified rule in section 4. Count the wrong ones.
2. **Re-review check:** take a random 10% of your reviewed rows (seed 42, about 45 rows). Redo each one from scratch without looking at your earlier answer, then compare `decision` and `chosen_title`.
3. **Error rate** = mismatches ÷ rows checked, computed separately for auto-keep and manual. If either is over 10%, re-review that row type.
4. Log the error rates in `data/universe/review-log.csv` as a summary row. Format: `timestamp,year,cik,name,flag,action,old_value,new_value,review_code,minutes,pass`, with `pass` = `review` or `qa`.

```python
import pandas as pd
t = pd.read_csv("data/universe/titles_v2_all.csv", dtype=str)
t[t.decision == "AUTO_KEEP"].sample(30, random_state=42).to_csv("data/universe/qa_autokeep.csv", index=False)
w = pd.read_excel("data/universe/review_worksheet.xlsx", sheet_name="review", dtype=str)
w[w.decision.notna()].sample(frac=0.10, random_state=42).to_csv("data/universe/qa_manual.csv", index=False)
```

> Licence note: the worksheet contains no price, return or Tiingo columns (this is checked by the build script). Don't paste any into it.
