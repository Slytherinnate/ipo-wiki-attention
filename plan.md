# Wikipedia Attention Trends: Project Plan

**Question (revised Oct 20, 2026, CURRENT):** Does pre-IPO Wikipedia attention predict first-day and 30-day IPO returns, and does that differ by sector? Lead/lag of attention around the IPO is the descriptive half. Returns are now a **core** section (see "Returns core v3" at the end).

**Earlier question (Oct 19, superseded):** Does Wikipedia attention lead or lag US IPOs (2021–2025), and does that differ by sector? AI model and product launches serve as a second event type for comparison. Big-cap company pages and controls give the baselines. The target audience is DS roles at financial institutions.

> **Pivot note:** the MTG categories are dropped. Older sections below that mention MTG sets are superseded by this pivot and by the "Title checking" section. Read "MTG set" as "IPO" wherever it appears.
**Owner:** Caleb Havens. **Budget:** 22h core plus ~2h setup (24h). It stretches to 30h if you add the optional extras.
**Status:** Draft for approval. Figures marked **[verified]** were checked against Wikimedia's servers on 2026-10-19. Figures marked **[est]** are estimates.

---

## 0. What the data actually is (verified)

- **Source:** https://dumps.wikimedia.org/other/pageview_complete/readme.html. Coverage is "December 2007 to the present" **[verified]**.
- **License:** "All Analytics datasets are available under the Creative Commons Zero (CC0) public domain dedication, unless otherwise specified" (https://dumps.wikimedia.org/legal.html) **[verified]**. You can publish anything derived from it. Credit Wikimedia anyway as a courtesy.
- **Daily file naming [verified]:** `https://dumps.wikimedia.org/other/pageview_complete/YYYY/YYYY-MM/pageviews-YYYYMMDD-user.bz2`. Each day has a sibling file, `...-automated.bz2`. Use `user` (humans) and skip `automated` (bots). That split takes care of most of the bot filtering.
- **Monthly files also exist [verified]:** `.../pageview_complete/monthly/YYYY/YYYY-MM/pageviews-YYYYMM-user.bz2`. Their internal row format is **not verified**, so check it in Setup before relying on them.
- **Real sizes (directory listing, Sept 2025) [verified]:**
  | File | Size |
  |---|---|
  | pageviews-20250901-user.bz2 | 643,651,110 B (~644 MB) |
  | pageviews-20250902-user.bz2 | 691,063,561 B (~691 MB) |
  | pageviews-20250903-user.bz2 | 684,323,643 B (~684 MB) |
  | pageviews-20250901-automated.bz2 | 516,748,347 B |
  | All 30 Sept 2025 daily `user` files | 19,821,517,135 B (~19.8 GB) |
  | pageviews-202509-user.bz2 (monthly) | 5,170,895,091 B (~5.2 GB) |
- **Row format, checked by decompressing the first 2 MB of the 2025-09-01 user file [verified]:** the fields are space-separated.
  `wiki_code  article_title  page_id  access_method  daily_total  hourly_counts`
  Real example: `aa.wikibooks File:2011_Wikimedia_Philippines_Annual_Report.pdf null mobile-web 1 X1`
  - The readme lists only 5 fields (wiki, title, page id, daily total, hourly). Real rows also carry an **access method** (`desktop`, `mobile-web`, ...). Trust the data, not the readme.
  - Missing page IDs appear as the literal string `null`.
  - **Hourly encoding:** a letter is the hour (A=0 ... X=23), followed by a count. `W1X1` means 1 view at 22:00 and 1 view at 23:00. Hours with zero views are omitted.
- **5-vs-6 column caveat [verified as a documented issue]:** the readme says "rows without Page IDs have only 5 columns, while rows with Page IDs have 6. We are applying a fix." In my sample of 181,392 rows, 181,388 had 6 fields, 1 had 5, and 2 were junk with 1–2 fields. **Rule:** split on spaces, require the wiki code to be `en.wikipedia`, take the *last* field as hourly and the second-to-last as the daily total, and count and skip anything else. Never assume field positions blindly.
- **Rows are sorted by wiki code** (the file starts at `aa.wikibooks`). `en.wikipedia` sits somewhere in the middle, so you still have to stream-decompress the file up to and through that point.

## 1. Date range and storage

**Recommendation:** use **2023-01-01 to 2025-12-31** (3 years). That window covers the ChatGPT aftermath, GPT-4/4o/5, Claude 2–4, the Gemini releases, Llama 2–4, and about 12–15 MTG sets. It's enough events to say something, and small enough to process in one weekend.

| Approach | Download volume | Disk kept | Notes |
|---|---|---|---|
| Daily `user` files, 3 yrs | ~720 GB **[est]** (≈19.8 GB/month × 36) | tiny | Too much. Don't. |
| Monthly `user` files, 3 yrs | ~186 GB **[est]** (≈5.2 GB × 36) | tiny | Preferred, if Setup confirms they keep daily granularity |
| Daily files, only ±60 days around each launch | ~40–80 GB per event cluster **[est]** | tiny | Fallback |

**The key habit is stream → filter → delete.** Never keep the raw `.bz2` files. Each one is decompressed as a stream, only rows for your ~200 tracked articles are kept, and the result goes to Parquet. The filtered dataset should be **under 100 MB [est]**. Peak scratch disk is one file at a time (~5–7 GB).

**Download time [est]:** 186 GB at 100 Mbps is about 4–5 h. At 50 Mbps it's about 9 h. Run it overnight on a **Raspberry Pi 4** so your laptop stays free. bz2 decompression on a Pi is slow, so expect it to be CPU-bound. Run one month per Pi, two Pis in parallel. Throughput is not measured; time the first month and extrapolate.

**Alternative worth knowing:** Wikimedia also has a per-article Pageviews REST API (`wikimedia.org/api/rest_v1/metrics/pageviews/per-article/...`). For 200 articles it could replace the dumps entirely. I did **not** verify its terms or limits this session. Using the dumps is the more impressive "big data" skill. The API is your emergency exit if downloads drag.

---

## 2. Tools (all free)

| Tool | What it does here | Cost |
|---|---|---|
| Python 3.12+ | Everything | Free, open source |
| DuckDB (1.5.6 on PyPI today) | SQL over Parquet on your laptop | Free, MIT |
| pandas | Table wrangling | Free, BSD |
| pyarrow | Writing Parquet | Free, Apache-2.0 |
| ruptures (1.1.10) | Changepoint detection | Free, BSD |
| Streamlit (1.66.0) | Dashboard | Free, Apache-2.0. Streamlit Community Cloud hosting is free for public apps **[not re-verified]** |
| matplotlib / plotly | Charts | Free |
| git + GitHub | Version control and portfolio | Free for public repos |
| VS Code + Jupyter | Editor and notebooks | Free |

No API keys, no tokens, no paid services. The real costs are disk space, bandwidth, and your time.

---

## 3. Repo layout

```
wiki-attention/
├── README.md              # the write-up (portfolio front page)
├── LICENSE                # MIT for code; note data is CC0 from Wikimedia
├── requirements.txt
├── .gitignore             # data/raw/, *.bz2, .venv/
├── config/
│   ├── articles.csv       # ~200 tracked titles + category
│   └── launches.csv       # event dates + source URLs
├── src/
│   ├── download.py        # fetch one month/day, resumable
│   ├── filter.py          # stream bz2 → keep tracked rows → parquet
│   ├── parse.py           # hourly-letter decoder + row validation
│   ├── features.py        # daily series, baselines, z-scores
│   └── changepoints.py    # ruptures + lead/lag calc
├── notebooks/
│   ├── 01_eda.ipynb
│   └── 02_modeling.ipynb
├── data/
│   ├── raw/               # scratch, gitignored, emptied after each file
│   └── processed/         # pageviews.parquet (small; OK to commit, CC0)
├── app/
│   └── streamlit_app.py
├── reports/figures/
└── tests/test_parse.py
```

---

## 4. Choosing the ~200 articles and the launch list

**Articles (~200).** Pick them by category, so the analysis can compare categories:
- **AI models and products, ~80:** for example `ChatGPT`, `GPT-4`, `GPT-4o`, `Claude_(language_model)`, `Gemini_(language_model)`, `Llama_(language_model)`, `Grok_(chatbot)`, `Sora_(text-to-video_model)`, `DeepSeek`, and so on.
- **AI companies, ~20:** `OpenAI`, `Anthropic`, `Google_DeepMind`, `XAI_(company)`, `Mistral_AI`, ...
- **MTG sets, ~40:** individual set articles where they exist. Many sets only have a section on `List_of_Magic:_The_Gathering_sets`, so check each one. Missing articles are a finding, not a failure.
- **MTG general, ~10:** `Magic:_The_Gathering`, `Wizards_of_the_Coast`, ...
- **Controls, ~50:** steady, boring pages (`Banana`, `Photosynthesis`, ...). These show what a "no event" series looks like, which is how you avoid fooling yourself.

**Title rules:** use the exact title from the article URL, with underscores and case-sensitive. Check for redirects. Views of a redirect title are counted under the redirect, not the target. The real `page_id` lets you join on ID instead of title, which is safer.

**Launch dates (`launches.csv`):** columns are `event, article, launch_date, announce_date, source_url, source_type`.
- AI: use the company's own announcement blog post or press release as the primary source. Wikipedia's dates are a fallback, and you must cite them as such.
- MTG: use the official Wizards of the Coast release date for each set from magic.wizards.com. The prerelease and preview-season dates are useful extras.
- **Every row needs a source URL. No source, no row.** Record both the announce and release dates when they differ. "Lead vs. lag" depends on which one you measure from.

---

## 5. Sections

### Section 0: Setup (2h, outside the 22h core)
**Goal:** a working environment and proof that you can read one real file.
**Concepts:** virtual environments, git basics, streaming decompression.
**Tools:** Python, venv, git, GitHub, VS Code.
**Steps:**
1. Install Python 3.12 and git. Create the GitHub repo `wiki-attention` and clone it.
2. `python -m venv .venv`, activate it, then `pip install duckdb pandas pyarrow ruptures streamlit plotly jupyter requests`, and run `pip freeze > requirements.txt`.
3. Create the repo layout above and the `.gitignore`.
4. Download the first ~2 MB of one daily file with an HTTP Range request, decompress it with Python's `bz2`, and print 10 lines. Confirm the 6-field format.
5. Download **one monthly** `user` file on a Pi, peek at it, and confirm whether its hourly field holds daily resolution. That decides the daily-vs-monthly choice in section 1.
6. First commit.

**Deliverables:** repo skeleton, `requirements.txt`, a short "format check" note in `notes.md`.
**Done when:** ☐ venv works ☐ 10 real rows printed ☐ monthly format decided ☐ pushed to GitHub.
**Pitfalls:** never commit `.bz2` files (they're 600 MB+ and GitHub rejects anything over 100 MB). Install Python on the Pis as well.

### Section 1: Acquisition and filtering (6h)
**Goal:** `data/processed/pageviews.parquet`, with one row per (article, date, access_method) and daily totals plus 24 hourly columns, for the whole date range.
**Concepts:** streaming I/O, parsing dirty data, defensive validation, idempotent and resumable jobs, Parquet.
**Tools:** Python (`bz2`, `requests`), pyarrow, Raspberry Pis.
**Steps:**
1. Write and test `articles.csv` (section 4). This takes about 1h, and doing it first saves pain later.
2. `parse.py`: a `decode_hourly("W1X1") -> [0,...,1,1]` function, plus a `parse_line()` that applies the 5/6-field rule and returns None for junk. Write `tests/test_parse.py` with real sample lines, including a 5-field line and a junk line.
3. `filter.py`: stream-decompress line by line, keep `en.wikipedia` rows whose title is in your set, write a Parquet file per month, and log the counts (rows read, kept, skipped).
4. `download.py`: download with resume support (Range requests), skip months already processed, and delete the raw file after filtering.
5. Run one month end to end and time it. Then launch the rest on the Pis overnight.
6. Combine the monthly Parquet files and spot-check 3 articles against the Wikimedia pageviews web tool (pageviews.wmcloud.org).

**Deliverables:** `src/parse.py`, `src/filter.py`, `src/download.py`, `tests/test_parse.py`, `data/processed/pageviews.parquet`, `logs/`.
**Done when:** ☐ tests pass ☐ all months processed ☐ skipped-row counts logged ☐ 3 spot checks match ☐ raw scratch is empty.
**Pitfalls:** title case and underscores; redirects; filling the Pi's SD card (use a USB drive); Python's `bz2` being slow, where `lbzip2` piped through the shell is faster on multi-core machines; a download dying halfway (that's why it needs to be resumable).

### Section 2: EDA (4h)
**Goal:** know what normal looks like, so you can recognize abnormal.
**Concepts:** time-series basics, weekly seasonality, log scales, outliers, data-quality checks.
**Tools:** DuckDB SQL, pandas, plotly, Jupyter.
**Steps:**
1. Load the Parquet file in DuckDB. Count articles, days, and missing days per article.
2. Plot 10 articles on a log scale, including controls.
3. Plot the weekly pattern (day-of-week averages). Compare desktop vs. mobile shares.
4. Overlay launch dates from `launches.csv` on 5 AI and 5 MTG series. Eyeball whether views rise before or after.
5. Flag weird spikes that aren't launches (Main Page features, news events, bot leakage) and write them down.
6. Write 5 bullet findings at the top of the notebook.

**Deliverables:** `notebooks/01_eda.ipynb`, 4–6 figures in `reports/figures/`.
**Done when:** ☐ data-quality table ☐ seasonality plot ☐ 10 overlay plots ☐ 5 written findings.
**Pitfalls:** linear-scale charts hiding everything; articles that didn't exist yet (zeros before creation are not "low interest"); confusing announce dates with release dates.

### Section 3: Modeling: spikes, changepoints, lead/lag (5h)
**Goal:** a number per event that answers the question: how many days before (−) or after (+) the launch did attention first shift?
**Concepts:** rolling baselines, z-scores, changepoint detection (PELT), event studies, why correlation is not causation.
**Tools:** pandas, ruptures, numpy.
**Steps:**
1. `features.py`: daily totals, log1p transform, a 28-day rolling median baseline, and a rolling z-score.
2. **Spike rule:** the first day in the window [−60, +30] around the launch where z > 3. The threshold is a choice; document it.
3. **Changepoint:** run `ruptures.Pelt(model="rbf")` on each event window and take the changepoint nearest the launch. Tune the penalty on 3 events, then freeze it.
4. Lead/lag = detected date − launch date (and also − announce date).
5. **Control check:** run the same detector on control articles at random fake "launch" dates. If it "finds" leads there too, your method is noise.
6. Summarize: median lead/lag per category (AI vs. MTG) and the share of events that lead.
7. Optional (+2h): a simple event-study plot, averaging normalized views by days-from-launch per category.

**Deliverables:** `src/features.py`, `src/changepoints.py`, `notebooks/02_modeling.ipynb`, `data/processed/event_results.csv`.
**Done when:** ☐ every event has a lead/lag or a documented "no detection" ☐ control false-positive rate reported ☐ parameters frozen and written down.
**Pitfalls:** tuning the penalty until you get the answer you wanted; leaks and rumors (pre-launch attention may be real news, not anticipation); small sample sizes, so report counts alongside medians.

### Section 4: Visualization and dashboard (4h)
**Goal:** a Streamlit app where someone picks an event and immediately sees the answer.
**Concepts:** dashboard design, caching, deployment.
**Tools:** Streamlit, plotly, DuckDB.
**Steps:**
1. Page 1, "Event explorer": a dropdown for the event, then the series with the launch line, the detected changepoint, and the lead/lag label.
2. Page 2, "Big picture": a lead/lag distribution per category, plus the event-study chart.
3. Page 3, "Method and data": a short explanation, the CC0 credit, and the caveats.
4. `@st.cache_data` for loading. Read the small Parquet file only.
5. Deploy to Streamlit Community Cloud, or serve it from a Pi on your local network.

**Deliverables:** `app/streamlit_app.py`, a public URL or Pi URL, 2–3 screenshots.
**Done when:** ☐ runs locally ☐ deployed ☐ loads in under 5s ☐ a non-technical friend can say what it shows.
**Pitfalls:** too many controls; a raw dump in the app (the processed data only, please); forgetting `requirements.txt` for deployment.

### Section 5: Write-up (3h)
**Goal:** a README that reads like an analyst's memo, not a homework log.
**Concepts:** communicating uncertainty, structuring a portfolio piece.
**Steps:**
1. Lead with the answer: "Attention led launches in X of N AI events (median Y days)..."
2. Data and license (CC0, link), method in 5 bullets, 3 key figures, limitations (rumors, redirects, English Wikipedia only, small N).
3. "What I'd do next" (other languages, Google Trends comparison, forecasting).
4. Reproduce steps: `pip install -r requirements.txt`, `python src/download.py ...`
5. Final pass: clean notebooks, pin the repo on your GitHub profile, add a link from LinkedIn or Handshake.

**Deliverables:** `README.md`, `reports/figures/`, a pinned repo.
**Done when:** ☐ answer in the first 3 lines ☐ limitations section ☐ someone else can reproduce it from the README ☐ dashboard linked.
**Pitfalls:** overclaiming causation; burying the answer under method.

---

## 6. Hour budget

| Section | Core hrs | Optional |
|---|---|---|
| Setup | 2 | |
| Acquisition/filter | 6 | +overnight Pi time (unattended) |
| EDA | 4 | |
| Modeling | 5 | +2 event study |
| Viz | 4 | +1 Pi hosting |
| Write-up | 3 | |
| **Total** | **24** | **up to 27–30** |

Hour figures come from the Research Lead brief and are estimates. Setup is extra and not in the brief. **Marathon tip:** kick off the downloads Friday night, so the data is ready Saturday morning.

## 7. Glossary

- **Pageview:** one request for an article page, as counted by Wikimedia.
- **Dump:** a bulk file of data published for download.
- **bz2:** a compression format. It can be decompressed as a stream, without unpacking the whole file.
- **Streaming:** processing a file line by line instead of loading it all into memory.
- **Parquet:** a compressed, column-oriented file format. It's small and fast for analysis.
- **DuckDB:** a SQL database that runs inside Python with no server.
- **EDA:** exploratory data analysis, getting to know the data before modeling.
- **Seasonality:** a repeating pattern, such as weekend dips.
- **Baseline:** what "normal" looks like (here, a rolling median).
- **Z-score:** how many standard deviations a value sits from the baseline.
- **Changepoint:** the moment a series' behavior shifts.
- **PELT:** the fast changepoint algorithm in ruptures. Its *penalty* controls how many changepoints it finds.
- **Lead/lag:** whether the signal moves before (lead) or after (lag) the event.
- **Event study:** averaging many series aligned on their event day.
- **Control:** a comparison series where nothing should happen.
- **False positive:** a detection where there was nothing real.
- **Redirect:** a Wikipedia title that forwards to another article.
- **CC0:** a public-domain dedication. Use it freely, no conditions.
- **Idempotent:** safe to run twice. The second run doesn't duplicate work.

---

## Verification results (Oct 19, 2026)

Raw outputs are in `verify/`: `readme.html`, `m.bz2` (the first 3 MB only), `monthly_sample.txt`, `api_*.json` / `api_*.hdr`, `timing20.txt`.

### Test 1: Monthly files keep DAILY detail (no hourly)
- **Method:** I fetched only bytes 0–3,000,000 of `monthly/2025/2025-09/pageviews-202509-user.bz2` (a 5.17 GB file) with an HTTP Range request. That decompressed to 367,518 complete rows. **All 367,518 rows have 6 fields.**
- **The readme has no monthly section.** It only documents hour letters A–X (0–23).
- **Real rows:**
  ```
  aa.wikibooks - null desktop 54 G1H1I1J2N1O21P7Q2S2T3U1V1W1X1Y3Z4^2
  aa.wikibooks Category:Candidates_for_speedy_deletion null desktop 4 H1J1Y1[1
  ```
- **Letters:** across 2,000 rows the letters used are exactly the 30 characters `A`–`Z`, `[`, `\`, `]`, `^` (ASCII 65–94). That matches the 30 days of September, so the code is A = day 1 and `^` = day 30. They are **day** letters, not hour letters. Example: `54` = 1+1+1+2+1+21+7+2+2+3+1+1+1+1+3+4+2 ✔.
- **Conclusion:** the monthly files keep daily resolution, and the hourly detail is gone. The plan's monthly route (~186 GB est. for 3 years) gives a daily series, which is enough for daily lead/lag.

### Test 2: REST per-article API
- **Docs:** https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/reference/page-views.html ("These endpoints serve data starting on July 1, 2015"). Agent definitions: https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/concepts/page-views.html (`spider` = bots that identify themselves, `automated` = bots caught by heuristics). Access policy: https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/documentation/access-policy.html. Rate limits: https://www.mediawiki.org/wiki/Wikimedia_APIs/Rate_limits ("new in 2026"). The table there gives **200 req/min** for a compliant User-Agent, **10 req/min** for unidentified clients, ≤3 concurrent requests, and says to honor 429 + Retry-After. User-Agent policy: https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_User-Agent_Policy (descriptive name + contact info; generic agents like curl and python-requests may be blocked).
- **Endpoint:** `https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/{access}/{agent}/{article}/{daily|monthly}/{start}/{end}`
- **Results** (UA `CalebHavens-DSPortfolio/0.1 (wiki-attention study; contact email)`):
  | Call | HTTP | Rows | Time |
  |---|---|---|---|
  | ChatGPT, user, daily, 2023-01-01→2025-12-31 | 200 | **1,096** (every day) | 0.26 s |
  | ChatGPT, monthly | 200 | 36 | 0.20 s |
  | ChatGPT, hourly | **400** "allowed values: [daily, monthly]" | 0 | 0.14 s |
  | Wilds_of_Eldraine, daily | 200 | **4** (views 0–1) | 0.13 s |
  | ChatGPT, user, 2010→2023 | 200 | 28 (first: 2022-12-05) | 0.14 s |
  | Banana, all-agents, 2010→2015 | 200 | 184 (first: **2015-07-01**) | 0.19 s |
- **Agent and access splits:** `user`, `automated`, `spider` and `all-agents` each returned 31 rows for Jan 2025. Access `desktop`, `mobile-app` and `mobile-web` all returned 200. Agent and access splits **are** available, one call per combination.
- **Rows only appear for days with views.** The API leaves out zero-view days, so fill the gaps with 0.
- **Speed:** 20 back-to-back calls took 3.86 s total. Responses carry `cache-control: max-age=14400`. I saw no rate-limit headers.
- **MTG finding:** `Wilds_of_Eldraine` is evidently a redirect or a near-empty title, since its views count under the target article. **Many MTG sets have no standalone en.wikipedia article.** Expect the MTG list to collapse to a few dozen real titles, or use `List_of_Magic:_The_Gathering_sets` plus the redirects. Check every title before analysis.
- **Estimate for 200 articles × 3 years:** 1 call per article (the full daily range fits in one response) = **200 calls**. At ≤200/min plus ~0.2 s per call, that's **about 1–2 minutes**. Adding a per-access split (×3) = 600 calls, **about 3–5 minutes**. [est, from the measured timings]
- **Lost vs. dumps:** hourly counts (the API only offers daily/monthly), data before July 1, 2015, and page_id joins (the API keys on title). Redirect handling is the same problem either way. **Kept:** daily counts, the user/automated/spider split, and the access-method split.

### Recommendation
Use the **API as the main data source.** It takes minutes instead of 186 GB and an overnight Pi job, and daily resolution answers the lead/lag question. Section 1 shrinks from 6h to roughly 3h [est]. Keep **one small dumps exercise** (stream a Range of one daily or monthly file, parse it with the 5/6-field rule, and cross-check 3 articles against the API) so the portfolio still shows bulk-data handling, and use the hours saved for article/redirect curation or the optional hourly analysis. Use the full dumps only if hourly or pre-2015 detail becomes a goal. Hourly detail only matters for same-day launch timing.

---

## Title checking (approved Oct 19, 2026)

Bad titles quietly ruin the analysis: a redirect shows near-zero views, and a broad page mixes many events into one series. So every article gets checked **before** any data is pulled.

### (a) The manual 8-step check (per candidate)
1. **Exact title:** open the article and copy the title from the URL (underscores and case matter).
2. **Redirect?** If the URL bar shows "(Redirected from X)", use the target title, and note X in `redirect_from`.
3. **Shared or broad page?** Is this page about *only* this product, or is it a family page (e.g. one article for all Claude models)? If shared, put a note in `shared_flag`. A shared page blurs lead/lag, so decide keep or drop.
4. **Renames:** check the page history and move log. If the title changed during 2023–2025, views before the move may sit under the old title.
5. **Disambiguation:** if it's a "may refer to" page, find the specific article instead.
6. **API sanity check:** first data date and typical daily views. A page that only starts after the launch can't show a lead.
7. **Launch dates with an official source:** fill `announce_date`, `release_date` and `source_url`.
   - AI: the company's announcement post.
   - **IPOs:** the SEC EDGAR S-1 / 424B prospectus filing (https://www.sec.gov/edgar/search/), or the exchange's listing announcement (NYSE/Nasdaq), or the company's own "announces pricing of IPO" press release. **Wikipedia and IPO-list sites are leads only, never the cited source.**
8. **Log it** in `titles.csv` and set `keep_drop`.

### (b) Script spec: `scripts/check_titles.py`
- **Input:** `candidates.csv` with columns `name, category, guess_title`. Categories: `ipo, ai_model, bigcap, control`; also `event_type` and `sector`.
- **Calls:**
  - MediaWiki Action API, `en.wikipedia.org/w/api.php`. One call per 50 titles: `action=query&redirects=1&prop=info|pageprops&ppprop=disambiguation`. This covers steps 1, 2 and 5.
  - Move log: `list=logevents&letype=move&letitle=<final>` (step 4). Note that this only catches moves *from* the final title. Moves *to* it are logged under the old name, so read `redirect_from` too.
  - Pageviews per-article API, user agent, daily, 2015-07-01→2025-12-31. Gives the first data date and the 2024 median, with missing days padded as 0 (step 6).
- **Politeness:** a descriptive User-Agent with contact info, a 0.4 s pause per call (~150/min, under the 200/min limit), one request at a time, and Retry-After respected on 429/503.
- **Output:** `titles.csv` with columns `name, category, final_title, redirect_from, is_disambig, shared_flag, rename_log, first_data_date, median_daily_views_2024, flags, announce_date, release_date, source_url, keep_drop`.
- **Flags:**
  - `MISSING`: no such page.
  - `REDIRECT`: the guessed title was a redirect.
  - `DISAMBIG`: a disambiguation page.
  - `RENAMED`: the move log has entries.
  - `NO_VIEWS`: no pageview data at all.
  - `LOW_VIEWS`: 2024 median below 100/day, a tunable threshold.
  - `STARTS_LATE`: the first data date is after 2023-01-01.
- **Runtime:** a few minutes for ~240 rows.

### Candidate mix (current `candidates.csv`, 232 rows)
- **ipo, 102 rows.** US IPOs 2021–2025, each with a `sector` (GICS sector names), `ipo_year`, and `year_source`.
  - **[LOCAL-ONLY: never publish]** The year source is a yearly IPO list from a secondary public price source.
  - That source only *confirms the year*. The actual dates must still come from EDGAR or the exchange (step 7).
  - The 2021 list fetched only went back to mid-June 2021, so H1-2021 IPOs aren't included yet.
  - By sector: IT 26, Consumer Discretionary 17, Health Care 15, Financials 14, Industrials 12, Consumer Staples 7, Energy 6, Communication Services 3, Real Estate 1, Utilities 1. For balance, add Energy, Communication Services and Real Estate names at review.
- **ai_model, 60 rows** (`event_type=product_launch`).
- **bigcap, 20 rows.** Already-public large caps (`event_type=none`), used as a reference attention level.
- **control, 50 rows.**
- `titles.csv` additionally carries `event_type, sector, ipo_year, year_source`.

### Optional extension: returns (SUPERSEDED Oct 20: returns are now core, see "Returns core v3")
Join first-day and 30-day returns to test whether pre-IPO attention predicts post-IPO performance. **Price data licensing is unverified.** Don't pick a source (e.g. a free price API or website) until its terms of use have been read and confirm that analysis and publishing derived charts are allowed. Offer prices are in the S-1/424B filings (public SEC documents). Trading prices need a licensed source.

### (c) Workflow
1. **The script pre-fills and flags.** It never decides.
2. **Caleb reviews every row** for:
   - **relevance:** it fits the question;
   - **specificity:** the page is about this one thing (fill `shared_flag`);
   - **accuracy:** the title and dates are right.

   Fix titles in `candidates.csv` and re-run if needed. Then fill the dates and source, and mark `keep_drop` = `keep` or `drop`.
3. **The data pull reads only `keep` rows** from `titles.csv`, using `final_title`.

### First checker run (Oct 19, 2026, 232 rows), from `titles.csv` and `verify/check_titles.log`
Flag counts: MISSING 33, REDIRECT 36, DISAMBIG 0, RENAMED 80, LOW_VIEWS 50, NO_VIEWS 5, STARTS_LATE 53. Only 58 rows came back with no flags.
- **The big lesson is that pageviews follow the title, not the article.** Many current titles were moved recently, so their own history is nearly empty:
  - `Claude (AI)`: 2024 median 0;
  - `Circle Internet Group`, `CoreWeave`, `Astera Labs`: 0–3;
  - `Dutch Bros Coffee`, `Medline Inc.`: no data at all.

  The older views sit under the old titles. **Stitching rule:** for each kept article, sum views across its old titles (`redirect_from`, `rename_log`) by date. Treat LOW_VIEWS = 0 on a renamed page as "check old title," not "no interest." Script v2 should fetch views for each old title too.
- **RENAMED is noisy.** 40 of the 50 controls trip it on old moves from long ago. Read the dates and only care about 2020+ moves.
- **MISSING, 30 IPOs:** many mid-cap IPOs (e.g. Excelerate Energy, OneStream, Hinge Health) have no article under the guessed title. Search for alternative titles, or drop them. Missing coverage is itself a finding ("small IPOs get no Wikipedia page").
- **AI model family pages:** Claude 3/3.5/4/Code, Llama 2/3/4, Grok 3/4 and DeepSeek R1/V3 all redirect to one family page. These are shared pages (step 3), so the per-version launch dates hit the same series.
- **Odd redirects to fix by hand:** Caribou Biosciences → `Rachel Haurwitz` (a person), MNTN → `Maximum Effort`, Project Astra → `Android XR`, Pi (chatbot) → `Inflection AI`. These are probably drops.

---

## Rescope v2 (Oct 19, 2026)

**Goal:** scale from a hand-picked list of about 100 IPOs to every US operating-company IPO from 2019–2025, pulled from SEC EDGAR. Then measure attention for the ones that have a Wikipedia article. AI launches, big caps and controls stay. The budget stays at 20–30 h.

### 1. IPO universe from SEC EDGAR: `scripts/build_ipo_universe.py`
**Method (free, official, verified):**
- **Quarterly form indexes:** `https://www.sec.gov/Archives/edgar/full-index/YYYY/QTRn/form.idx`. Indexes cover 1994Q3 to the present; each file is ~42–58 MB for 2024.
  - Keep form **424B4**, the final prospectus filed when an offering prices.
  - Source: https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data, which documents `/Archives/edgar/full-index` and `/daily-index`.
- **IPO test:** 424B4 is also used for follow-on offerings, so for each filer the script reads `https://data.sec.gov/submissions/CIK##########.json` and keeps the company only if:
  - it filed **no** 10-K/10-Q/20-F/40-F and no earlier 424B4 before this 424B4 (so it wasn't already public; this excludes re-listings and follow-ons);
  - an S-1/F-1/S-11 appears in its filings. If none is found, it gets the flag `NO_REG_IN_RECENT`, because the "recent" list in the JSON can be truncated for heavy filers.
- **Flags:**
  - `SPAC` (SIC 6770 or "Acquisition" in the name): excluded.
  - `FUND_OR_TRUST` (SIC 6726, or "fund"/"trust" in the name): excluded.
  - `FOREIGN_ADR` (any F-1 or 20-F): kept and flagged. Many are small foreign issuers, and some list ADSs.
- **Direct listings** (e.g. Spotify, Roblox) usually don't file a 424B4, so they **aren't captured**. They have to be added by hand or explicitly called out as excluded.
- **SEC fair access:** "Current max request rate: 10 requests/second," and you must declare a User-Agent with contact details (same SEC page). The script sends `Caleb Havens calebhavens08@gmail.com`, sleeps 0.15 s between calls (~7/s), and caches every response under `data/cache/`, so re-runs don't hit SEC again.
- **Date caveat:** the 424B4 filing date is usually the pricing day or one business day later. It is **not** guaranteed to be the first trade date. **[LOCAL-ONLY: never publish; first-trade dates from a secondary public price source]** Spot-checks: Reddit's 424B4 is dated 2024-03-21 and its first trade was 2024-03-21. Rubrik's is 2024-04-26 vs. a first trade of 2024-04-25. For the event study, treat the date as ±1 day, or confirm first trade dates for kept rows from exchange or press-release sources.
- **Sector:** the `sic` field in the submissions JSON is mapped to GICS-style sector names by SIC range (`SECTOR_RANGES` in the script). The SIC titles come from the SEC list (https://www.sec.gov/search-filings/standard-industrial-classification-sic-code-list). **The grouping is our own approximation, not an official SIC→GICS crosswalk.** GICS is proprietary (MSCI/S&P). Say so in the write-up.

**Real prototype counts (full run 2019–2025, all from EDGAR):**

| Year | 424B4 filers | First-time offerings | SPAC | Fund | **Operating IPOs** | of which not foreign-flagged | Wikidata CIK match |
|---|---|---|---|---|---|---|---|
| 2019 | 348 | 218 | 43 | 2 | **173** | 130 | 25 |
| 2020 | 642 | 464 | 204 | 0 | **260** | 198 | 22 |
| 2021 | 1,221 | 1,005 | 559 | 1 | **445** | 344 | 59 |
| 2022 | 314 | 182 | 78 | 2 | **102** | 64 | 5 |
| 2023 | 322 | 162 | 32 | 1 | **129** | 69 | 5 |
| 2024 | 378 | 209 | 51 | 0 | **158** | 77 | 3 |
| 2025 | 527 | 350 | 139 | 0 | **211** | 98 | 5 |
| **Total** | | 2,590 | 1,106 | 6 | **1,478** | 980 | 124 |

The 2024 recall check against known names found Reddit, Astera Labs, Rubrik, ServiceTitan, Lineage, Viking, Tempus AI, Ibotta, UL Solutions, Waystar, Amer Sports, BrightSpring, Loar, OneStream, StandardAero, Ingram Micro, Pony AI, WeRide, Kyverna and Centuri. That's **20/20 found**.

**Per-sector counts, operating IPOs 2019–2025 (real, from SIC):** Health Care 479, Information Technology 310, Industrials 207, Consumer Discretionary 173, Financials 149, Consumer Staples 44, Real Estate 23, Other 22, Energy 21, Materials 17, Communication Services 15, Utilities 13, Unknown 5.
- **Sector gaps:** Utilities (13) is already under 15 at the universe level, and Communication Services (15) is borderline. Both will shrink further after the Wikipedia filter (2024: 1 kept or reviewed in each).
- **Rule:** after the final keep step, any sector with fewer than 15 kept IPOs is reported as **"Other (small sectors)"** or listed as "too small to analyze." Never pad.
- Health Care is dominated by biotech, which matters for interpretation.

### 2. Title matching at scale
- **Wikidata P5531 "Central Index Key" exists** (verified: "number given to an individual or company by the United States Securities and Exchange Commission"). One SPARQL query (query.wikidata.org) gets every item with a CIK and an English Wikipedia article: **3,181 items** in total.
  - **Coverage is thin for IPOs:** only 124 of 1,478 operating IPOs match, and just 3 of 158 in 2024. It's precise but rare.
- **Fallback, implemented in check_titles_v2:** Wikipedia search on the cleaned company name (top 3 hits). A hit counts as **verified** only if its wikitext shows one of the company's SEC tickers next to NYSE/Nasdaq (e.g. `{{NYSE|RDDT}}`), and "List of…" and "Companies listed…" index pages are skipped.
  - In 2024 this verified 21 matches, against 3 from Wikidata.
  - An unverified hit that shares a real word (4+ letters, not a corporate filler word) with the company name goes to review. One that shares no word is dropped as `DROP_NO_ARTICLE`.
- **Possible upgrade (not built):** Wikidata ticker symbol (P249, qualifier on the stock-exchange statement) plus exchange as a second precise key. It hasn't been tested.

### 3. `scripts/check_titles_v2.py`
- Resolves redirects, then reads `pageprops` (disambiguation, wikibase_item) and the **list of redirects pointing at the article**. When a page moves, the old title becomes a redirect, so this covers old names.
- **Sums daily user views across the article and up to 15 redirects.** The flag `MANY_REDIRECTS` is informational. It writes `data/processed/views_YYYY/<CIK>.csv` and computes 30-day pre-IPO and post-IPO view totals.
- **Decision rules:**
  - `DROP_EXCLUDED`: SPAC or fund.
  - `DROP_NO_ARTICLE`: no match, or an unrelated search hit.
  - `AUTO_KEEP`: Wikidata CIK match or ticker-verified match, **and** not a disambiguation page, not a list page, and view data starts ≥30 days before the 424B4 date.
  - `REVIEW`: everything else, such as plausible unverified search hits, disambiguation pages, no pre-IPO data, or no views.
  - `FOREIGN_ADR` and `MANY_REDIRECTS` don't block a keep. Caleb can filter on them.
- `--redecide YEAR` re-applies the rules to an existing file with no API calls.
- **Outputs:** `data/universe/titles_v2_YYYY.csv` (all rows) and `data/universe/review_YYYY.csv` (Caleb's queue only, with a blank `keep_drop` column).

**Real 2024 prototype (209 first-time offerings):** AUTO_KEEP **16**, REVIEW **44**, DROP_NO_ARTICLE **98**, DROP_EXCLUDED **51**.
- Auto-kept: Ibotta, ServiceTitan, Reddit, Tempus AI, Ardent Health, WeRide, Lineage, Ingram Micro, UL Solutions, Silvaco, Rubrik, Pony.ai, Amer Sports→`Salomon Group` (*wrong-ish: verify*), Marex, Webtoon, StandardAero.
- Review reasons: SEARCH_UNVERIFIED 36, LIST_PAGE 5, NO_PRE_IPO_DATA 2 (Astera Labs and Fractyl: articles created at or after the IPO), DISAMBIG 2, NO_VIEWS 1.
- **The review queue is 28% of operating IPOs** (44/158). Most rows are obvious junk, about 30 s each [est]. Some real companies are missed by search (Waystar, OneStream, Kyverna, Centuri, Loar→"Lloyd Loar"), so a quick manual title search on review rows recovers some of them.
- The rate of articles existing **before** the IPO is low. Small and foreign issuers mostly have no article at all. **That gap is itself a finding:** "Wikipedia attention is measurable for only ~X% of IPOs, skewed to large US deals."

**Projection to 2019–2025 [ESTIMATE].** The 2024 rates applied to 1,478 operating IPOs give ~150 auto-keep and ~410 review rows. Earlier years (2019–2021) have more Wikidata matches (25–59 per year) and larger deals, so the measurable share there is probably higher. **Expected final kept set: roughly 200–450 IPOs [est], not 500–1,000.** The universe is ~1,500, but Wikipedia-measurable coverage is the binding limit. Real numbers come from running v2 on each year (~15–20 min per year at the polite rate, [est] from the 2024 run of ~20 min).

### 4. Other event types and controls
- **AI launches (60), big caps (20), and 50 generic controls** stay as in `candidates.csv`.
- **Matched controls, proportional (spec, not built):** for each kept IPO, pick 1 already-public company (SEC `company_tickers.json` + submissions SIC) in the same sector, with a verified Wikipedia article. Assign it a **pseudo-event on the same date.** Same detectors, same windows, so the matched controls give a false-positive rate per sector. The target ratio is 1:1 with kept IPOs (~200–450 [est]).

### 5. Hours (v2, total 29 h)

| Section | Hrs | Notes |
|---|---|---|
| Setup | 2 | as before |
| Universe build (EDGAR) | 3 | script exists; run all years, spot-check 20 dates/sectors |
| Title matching + review queue | 5 | run v2 per year (unattended), review ~400 rows [est] at ~30 s each ≈ 3.5 h |
| Data pull | 1 | views already saved by v2; add AI/big caps/controls via API |
| EDA | 4 | coverage by sector/year is now a headline chart |
| Modeling | 6 | event study by sector, changepoints, matched-control false-positive rate |
| Viz | 4 | sector filter, IPO picker |
| Write-up | 4 | method caveats (424B4 date, SIC grouping, coverage bias) |
| **Total** | **29** | over 30 if review runs long: cap review at the 2 h mark and auto-drop the rest |

### Open risks
1. **Coverage bias:** only large or famous IPOs have pre-IPO articles. The results describe "notable IPOs," not all IPOs. Report coverage per sector and year.
2. **Matching errors:** ticker verification is good but not perfect (Amer Sports → `Salomon Group`, a subsidiary; UL Solutions → `UL (safety organization)`, a parent). Parent and subsidiary pages blur the signal. Spot-check every auto-keep.
3. **Review load:** ~400 rows [est]. The 2 h cap above, plus a better precise key (Wikidata ticker), would cut it.
4. **424B4 date ≠ first trade date** (±1 day). Direct listings are not included.
5. **SIC → GICS-style mapping is approximate,** and GICS itself is proprietary. Call it "SIC-based sector" in the write-up.
6. **Truncated EDGAR "recent" filings** for heavy filers can misclassify a few companies (the `NO_REG_IN_RECENT` flag).
7. **Returns extension:** price-data licensing is still unverified (see above).
8. **Runtime:** v2 makes many pageview calls (article + redirects). 2024 took ~20 min; all years ≈ 2–3 h unattended [est]. Use a Pi.


---

## Returns core v3 (Oct 20, 2026)

**Business question:** does pre-IPO Wikipedia attention (views in the 30 days before the 424B4 date, from the summed redirect series) predict the **first-day return** (first close ÷ offer − 1) and the **30-day return** (close on trading day 30 ÷ offer − 1), and does that differ by sector? Also report open-vs-offer (the "pop").

### A. Offer price from SEC: `scripts/offer_price.py` (built, tested)
- Fetches only the first ~600 KB of each company's 424B4 (the cover page). Takes the first `$xx.xx` after "public offering price" and caches the text in `data/cache/424b4/`. Same SEC User-Agent and ≤10 req/s rule.
- **Test on 5 known 2024 IPOs:** Reddit $34.00, Rubrik $32.00, Astera Labs $36.00, ServiceTitan $71.00, Ibotta $88.00. All 5 match the published pricing.
- **All 158 operating 2024 IPOs:** a price was found for 154 (4 `NO_PRICE_FOUND`). **[LOCAL-ONLY: never publish]** Cross-check against a secondary public price source's 2024 list: **122 agree, 2 disagree** (CCSC Technology $4.00 vs $6.00, mF International $4.50 vs $5.00, both micro-caps, need a manual look), and 30 couldn't be name-matched.
- SEC filings are public records, and the offer price is a fact taken from them. Fine to publish.

### B. Daily price sources: terms as quoted from the primary pages

| Source | Key terms (quoted) | Publish derived results? | Rate / history | Delisted tickers | Verdict |
|---|---|---|---|---|---|
| **Yahoo (yfinance)**, https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html | You may not "access or collect data… from our Services using any automated means… including… scrapers… for any purpose without our express, prior permission" | n/a | n/a | n/a | **Reject:** yfinance is automated collection |
| **Massive (ex-Polygon)**, https://massive.com/legal/market-data-terms-of-service | License "exclusively for your personal, non-business, and non-commercial purposes"; may not distribute "any data, charts, analytics, research, or other works based on… or derived from the Market Data ('Derived Works')" | **No.** Their KB: "Publishing charts or tables built from the data" = "Almost certainly redistribution" | Free "Basic": "5 API Calls / Minute", "2 Years Historical Data", end of day (https://polygon.io/pricing) | unverified | **Reject:** no publishing, and only 2 years of history free |
| **Stooq**, https://stooq.com/terms.html | 5.3 "Redistribution of data found on the website is not allowed without the consent of Stooq." Download page (per a secondary review): "intended solely for personal use" [secondary, unverified on primary] | Not addressed; redistribution banned | API key via CAPTCHA; daily hit limit (numbers unverified). Our scripted fetch got a JavaScript browser check | unverified | **Reject** for a scripted, published project |
| **Nasdaq Data Link**, https://assets.ctfassets.net/…/Data_Link_Terms_and_Conditions_-_effective_11.1.26.pdf | "usage shall be for internal business purposes only"; Derived Data "can only be used for internal business purposes except… upon Provider's prior written approval" | **No**, without written approval | API free for free datasets; whether a free US EOD stock dataset exists is unverified | unverified | **Reject** |
| **Tiingo**, https://app.tiingo.com/tos/ (updated Oct 6, 2026) | Starter (free) plans "may not write, save, archive… or otherwise retain Tiingo Data in any persistent or durable storage". Derived Products may be distributed only if they can't substitute for the data and can't be used "to identify, recover, or reproduce any underlying Tiingo Data". Permitted examples include "percentage returns… provided that their scope, granularity, and presentation do not permit the underlying Tiingo Data to be reconstructed, including through the use of a starting value…" and "aggregated statistics calculated across multiple instruments… such as averages, medians… distributions" | **Yes, for aggregates (sector medians and distributions), on a paid plan.** Per-IPO returns next to the public offer price could reconstruct the close, so **don't publish per-IPO returns** | Paid plan needed to store data. Plan prices and limits: unverified (pricing page is JavaScript) | unverified | **Backup**, paid |
| **Alpha Vantage**, https://www.alphavantage.co/terms_of_service/ | License "for personal, non-commercial use". Commercial includes any purpose "beyond investment analysis, research, testing, monitoring, and any other activities that are private and individual in nature", **and** anyone "currently employed or have an active affiliation with a… investment bank, money manager…" | **Not addressed.** Ask in writing | Support page (https://www.alphavantage.co/support/): free "25 API requests per day and unlimited API requests for verified open-source or educational projects" | unverified (a listing-status endpoint may cover delisted tickers; not checked) | **Primary candidate**, pending written OK |
| **SEC EDGAR** | Public filings | Yes | — | — | Offer price only. **SEC has no daily trading prices** |

**Recommendation:**
1. **Offer price from SEC 424B4** (done, ~98% agreement).
2. **Daily prices from Alpha Vantage.** Caleb signs up for a free key, applies for "educational project" status, and **emails support to confirm** that publishing aggregated sector statistics (medians and distributions of returns, no raw prices) in a public GitHub portfolio is allowed. Save the reply in `docs/licenses/`. Also note: per the terms, the license becomes "commercial" once he's employed at a financial institution, so re-check then.
3. **Fallback: Tiingo paid plan** for one month (price unverified). Its terms explicitly allow publishing aggregate return statistics.
4. **Under any source:** keep raw prices out of git (`data/prices/` in `.gitignore`). Publish only sector-level aggregates and per-IPO *attention* data (CC0). Show per-IPO returns only locally, not in the public dashboard, unless the vendor says otherwise in writing.

**Test status (5 known 2024 IPOs):** the offer-price part is done (above). **The price-source test was NOT run.** Every compliant candidate (Alpha Vantage, Tiingo, Massive) needs Caleb to create an account and API key, which is his action. I didn't scrape Yahoo or bypass Stooq's browser check. Once there's a key, the test is about 10 calls: daily series for RDDT, RBRK, ALAB, TTAN and IBTA covering IPO day through day 30.

**Survivorship bias:** many 2019–2025 IPOs have since been delisted, acquired or renamed (SPAC-era 2021 especially). The universe comes from EDGAR, so it is survivor-free. **Price coverage for delisted tickers on any source is unverified.** Measure it: report "% of IPOs with price data" per year and sector, and never silently drop the missing ones. A missing price for a delisted IPO must show up as missing, not disappear. Ticker changes: use the ticker at the IPO, which comes from the 424B4 cover, not today's ticker.

### C. Method notes
- First trade day = the first date in the price series on or after the 424B4 date. Check it's within 0–2 trading days, otherwise flag it.
- Day-30 = the 30th trading day. Use unadjusted closes for day 1, and split-adjusted for day 30 (or check for splits in the window).
- **Models:** start with the Spearman correlation between log(pre-IPO views + 1) and returns, per sector. Then an OLS of returns on log attention + log offer size + sector + year fixed effects. Report coefficients with confidence intervals. With n ≈ 200–450 [est], keep the model small. Small sectors are grouped into "Other" (rule above).

### D. Hours v3 (total 30)

| Section | Hrs | Change |
|---|---|---|
| Setup (+ API key, license email) | 2 | |
| Universe build (EDGAR) | 3 | done as prototype |
| Offer prices (424B4) | 1.5 | new; script built |
| Daily prices + returns | 3 | new; fetch, coverage, first-day/day-30 calc |
| Title matching + review | 4 | was 5; review capped at 1.5 h |
| EDA | 3 | was 4 |
| Modeling (attention→returns, by sector) | 6 | refocused |
| Viz | 4 | aggregates only in the public app |
| Write-up | 3.5 | was 4; adds license and survivorship notes |
| **Total** | **30** | |

Lead/lag changepoint work is trimmed to a single event-study chart inside Modeling. AI launches, big caps and controls are kept for the attention baselines only (no returns).


---

## LOCAL-ONLY: never publish (decided Oct 20, 2026)
- The **secondary-source cross-check** (IPO-year confirmation, the "122 agree / 2 disagree" offer-price check, and the Rubrik first-trade example) and the **`year_source` column** in `candidates.csv` and `titles.csv` are derived from a secondary public price source.
- They are **LOCAL-ONLY**: kept on disk, never deleted, never committed, published or cited (see the .gitignore "local-only (third-party ToS)" block in docs/setup-checklist.md).
- **That source is never fetched again.** All published IPO years, dates and offer prices come from **SEC EDGAR** (the universe, the 424B4).
- Any mention of that source earlier in this plan is historical. It is not a source for published output.
- 2026-10-20: Deleted secondary-source-derived candidates.csv and titles.csv at Caleb's request (before Tiingo subscription; Tiingo bars validating other datasets). Pipeline uses SEC/Wikidata only. ToS page copies kept in verify/tos/ as compliance records.
- 2026-10-20 decisions: Springview -> manual date check (add to review list); 6 late-start rows excluded from return tests; 10 unrecoverable reused tickers (Sunnova, GAN, Chindata, DiDi, Grandstand, TheRas, Silvergate, G Medical, Alfi, La Rosa) accepted as missing, listed as a known limitation in write-up. No Tiingo email.

## Status notes (2026-10-20 evening)
- Current step: Matching + review (manual pass of 452 rows, ~15 hrs incl QA). Done: setup, universe (1,410 operating IPOs), offer prices (1,354), Tiingo prices/returns (574 usable), pageviews for confirmed matches.
- Pageviews now come from the REST API (not bulk dumps); Pis optional/not needed.
- Charts: plotly/matplotlib + Streamlit. Tableau excluded from this project (future separate Tableau project).
- Hours note: review grew from 1.5 to ~15, so total runs past 30; remaining after review ~16.5 hrs (EDA 3, modeling 6, viz 4, write-up 3.5).
- No new plan versions: future changes go in notes here.

## Status notes (2026-10-22 morning)
- Review + QA complete (468 rows, all checks pass). Final matched set 352 (351 US; Technip adr_only). Usable for returns: 306 (first-day and day-30). Pageviews fetched, 0 failures. Outputs: data/processed/analysis_set.csv, analysis_table.parquet (local only); docs/coverage-2026-10-22.md.
- Sectors (n): IT 112, ConsDisc 62, Health 43, Financials 36, Industrials 23, Staples 16, Other 14 (Other below n>=15 publish bar).
- Open decision: 48 firms have no pre-IPO article (ARTICLE_AFTER_IPO); treat as zero attention vs exclude (n~258).
- Next: EDA (~3 h).
- 2026-10-22 decision: keep all 306; add has_pre_ipo_article flag. Main spec = no-article as zero attention (+ no-article dummy); robustness = exclude (n~258). Streamlit app gets include/exclude toggle; any group falling below n=15 under a toggle is suppressed.

- 2026-10-22 confirmatory model spec, pre-specified before running (notebooks/02_model.ipynb):
  - Sample: US-IPO matched set with a day-30 return (n=306). First-day return is missing for 20 firms whose close equals the offer price (n=286).
  - Outcomes: `pop_log` = ln(1 + first-day return); `ret30_log` = ln(1 + day-30 return).
  - Test variable: `log_pre30` = ln(pre-IPO 30-day views + 1).
  - Controls: year fixed effects, `foreign_issuer`, ln(offer price).
  - Estimator: OLS with HC3 robust standard errors. Report coef, 95% CI, p, n, R².
  - Spec A (main): all firms, plus a `has_pre_ipo_article` dummy (no-article firms count as 0 views).
  - Spec B (robustness): exclude no-article firms.
  - Interpretation: coef × ln 2 ≈ change in ln(1 + return) per doubling of views (≈ % change in 1 + return).
  - Secondary, exploratory: sector heterogeneity per sector with n ≥ 15. Baselines: return descriptives by article group, sector and year (n < 15 suppressed), Kruskal–Wallis across article groups, and a controls-only model to give attention's incremental R².
  - Decision rule: the attention coefficient counts as confirmed only if p < 0.05 in Spec A and has the same sign in Spec B. Each outcome is reported separately; there is no multiple-comparison adjustment across the 2 outcomes × 2 specs, and that is stated.
- 2026-10-22: Caleb approved the pre-specified decision rule (Spec A p<0.05 + Spec B same sign). Result: first-day passes (marginal, +0.9%/doubling, ~1% R2); day-30 null. Next: viz (~4 h).
- 2026-10-22: Viz done (Streamlit app, 7 pages incl. post-hoc Company size; public aggregates n>=15; all views charts on daily-average basis). Next: write-up (~3.5 h), then repo/GitHub setup.
