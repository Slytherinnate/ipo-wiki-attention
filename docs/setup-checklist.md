# Setup checklist (2 hours)

Matches plan.md v3 (returns core, 30 h). Tick each box. Times are estimates.

## 1. Python and a virtual environment (20 min)
- [ ] Install Python 3.12 or 3.13 from https://www.python.org/downloads/. On Windows, tick "Add python.exe to PATH". *(The box runs 3.13.5. Any 3.12+ should work, but that hasn't been tested on Caleb's laptop.)*
- [ ] Check it in a terminal: `python --version`, which should print 3.12 or higher.
- [ ] Create the project folder and environment:
  ```
  mkdir wiki-attention && cd wiki-attention
  python -m venv .venv
  # Windows:  .venv\Scripts\activate      macOS/Linux:  source .venv/bin/activate
  ```
  Your prompt now starts with `(.venv)`. **Activate it every time you open a new terminal.**

## 2. Packages (10 min)
These are the latest versions on PyPI as of Oct 20, 2026. Pinning them means the code behaves the same later. Save this as `requirements.txt`:
```
requests==2.34.2
pandas==3.0.6
numpy==2.5.4
duckdb==1.5.6
pyarrow==26.0.0
scipy==1.18.1
statsmodels==0.15.0
plotly==7.1.0
streamlit==1.66.0
python-dotenv==1.2.4
jupyterlab==4.6.4
ruptures==1.1.10
```
- [ ] Run `pip install -r requirements.txt`.
- [ ] Run `python -c "import pandas, duckdb, scipy, statsmodels, streamlit, dotenv; print('ok')"`. It should print `ok`.
- If one version fails to install on your OS, remove that pin (just the package name) and record what installed with `pip freeze > requirements.lock.txt`.

## 3. Git and GitHub (20 min)
- [ ] Install git (https://git-scm.com/downloads). Then:
  `git config --global user.name "Caleb Havens"` and `git config --global user.email "<your email>"`.
- [ ] On github.com, create a **public** repo `wiki-attention` with no README, then:
  ```
  git init
  git branch -M main
  git remote add origin https://github.com/<your-username>/wiki-attention.git
  ```

## 4. Folder layout (5 min)
```
wiki-attention/
├── README.md
├── LICENSE                 # MIT for code
├── requirements.txt
├── .gitignore
├── .env                    # API keys. NEVER committed
├── .env.example            # same names, fake values. Committed
├── config/                 # candidates.csv (LOCAL-ONLY, gitignored); candidates_public.csv (no year_source)
├── scripts/                # build_ipo_universe.py, check_titles_v2.py, offer_price.py, ...
├── data/
│   ├── cache/              # raw SEC/Wikimedia downloads (ignored)
│   ├── universe/           # ipo_universe_*.csv, titles_v2_*.csv, review_*.csv, offer_prices_*.csv
│   ├── processed/          # views (CC0, OK to commit)
│   └── prices/             # vendor prices. NEVER committed
├── docs/                   # these guides + licenses/
├── notebooks/
├── reports/figures/
└── app/
```
- [ ] Create it: `mkdir config scripts data data/cache data/universe data/processed data/prices docs docs/licenses notebooks reports reports/figures app`
- [ ] Copy the existing scripts (`build_ipo_universe.py`, `check_titles_v2.py`, `offer_price.py`, `check_titles.py`) into `scripts/`.

## 5. .gitignore (5 min)
Save this as `.gitignore`:
```
.venv/
__pycache__/
.ipynb_checkpoints/
.env
*.key
data/cache/
data/raw/
data/raw/tiingo/          # Tiingo raw EOD + meta: LOCAL ONLY, never commit (Tiingo terms 1b)
data/local_only/ipo_returns*.csv  # per-IPO pop/30-day returns from Tiingo: LOCAL ONLY
data/prices/
data/returns_per_ipo*.csv
*.bz2
.DS_Store

# --- local-only (third-party data). Never publish, never delete ---
config/candidates.csv
candidates.csv
titles.csv
data/universe/thirdparty_*
data/local_only/
```
> **LOCAL-ONLY: never publish.** The `year_source` column (in `candidates.csv` and `titles.csv`) and the early offer-price cross-check came from a secondary public price source. Keep these files on your laptop and don't delete them, but never commit, publish or cite them. Never fetch third-party price sites from scripts. Published IPO years, dates and prices come from SEC EDGAR only. If you want the AI-launch, big-cap and control rows public, export a copy **without** the `ipo_year` and `year_source` columns (e.g. `config/candidates_public.csv`) and commit only that.
- [ ] Check it: `git status` must **not** list `.env` or anything in `data/prices/`.

## 6. Alpha Vantage key and educational application (15 min)
- [ ] Go to https://www.alphavantage.co/support/#api-key and click "Get Free API Key". *(The terms say the EULA takes effect when you click "Get Free API Key". I haven't verified the exact form fields.)*
- [ ] Read the terms first: https://www.alphavantage.co/terms_of_service/. Note in particular:
  - the license is "personal, non-commercial use";
  - use becomes "commercial" if you are "employed or have an active affiliation with a… investment bank, money manager…". **Re-check this if you take a job at a financial institution.**
- [ ] The free tier is 25 requests per day. The support page also says "unlimited API requests for verified open-source or educational projects." **How you apply for that is unverified.** Ask in the email in step 8.
- [ ] Save a copy of the terms page as PDF or HTML in `docs/licenses/alphavantage-terms-2026-10-20.*`.

## 7. Store the key and User-Agents in .env (5 min)
`.env` (never commit):
```
ALPHAVANTAGE_API_KEY=paste_your_key_here
SEC_USER_AGENT=Caleb Havens calebhavens08@gmail.com
WIKI_USER_AGENT=CalebHavens-DSPortfolio/0.3 (wiki-attention IPO study; calebhavens08@gmail.com)
```
`.env.example` (commit):
```
ALPHAVANTAGE_API_KEY=your_key_here
SEC_USER_AGENT=Your Name your@email.com
WIKI_USER_AGENT=YourProject/0.1 (description; your@email.com)
```
In scripts, read them like this:
```python
from dotenv import load_dotenv; import os
load_dotenv()
KEY = os.environ["ALPHAVANTAGE_API_KEY"]
```
- **Why the User-Agents:**
  - SEC asks you to "declare your user agent" and sets a "max request rate: 10 requests/second" (https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data).
  - Wikimedia asks for a descriptive agent with contact info (https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_User-Agent_Policy) and limits clients to 200 requests per minute (https://www.mediawiki.org/wiki/Wikimedia_APIs/Rate_limits).
- [ ] The current scripts hard-code these strings. Switching them to `os.environ` is a 5-minute edit: do it now.

## 8. License-confirmation email (10 min)
Send this from your own email. The address is unverified: the terms list **premium@alphavantage.co** for commercial questions, and the support page has a contact form. Use whichever you prefer. Save the reply in `docs/licenses/`.

> **Subject:** Educational project: permission to publish aggregate statistics
>
> Hi Alpha Vantage team,
>
> I'm a student starting a computational data science degree in January 2027, building a personal, non-commercial portfolio project. It asks whether Wikipedia pageview attention before US IPOs (2019–2025, about 200–450 companies) relates to first-day and 30-day returns, by sector.
>
> I'd use your free API (TIME_SERIES_DAILY) to fetch daily prices for each IPO's first ~30 trading days. I would **not** publish or redistribute any raw prices. The public GitHub repo and dashboard would show only **aggregate statistics**: sector-level medians, distributions and correlation/regression results. My code would download the data fresh for anyone re-running it with their own key.
>
> Three questions:
> 1. Is publishing those aggregate results on GitHub allowed under your terms?
> 2. Could this project qualify for the "verified open-source or educational" unlimited tier, and how do I apply?
> 3. Does your daily data include tickers that have since been delisted or acquired? Many of these IPOs no longer trade.
>
> Thank you,
> Caleb Havens

- [ ] Sent? Note the date in `docs/licenses/README.md`. **Don't publish any return statistics until you have a written yes.** Until then, everything stays local.

## 9. Smoke test (15 min)
Save as `scripts/smoke_test.py` and run `python scripts/smoke_test.py`:
```python
"""Checks that the SEC, Wikimedia and Alpha Vantage connections work. 3 requests total."""
import os, requests
from dotenv import load_dotenv
load_dotenv()

sec = requests.get("https://data.sec.gov/submissions/CIK0001713445.json",          # Reddit, Inc.
                   headers={"User-Agent": os.environ["SEC_USER_AGENT"]}, timeout=30)
print("SEC:", sec.status_code, sec.json().get("name"))                               # expect 200 Reddit, Inc.

wm = requests.get("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/"
                  "all-access/user/Reddit/daily/2024030100/2024033100",
                  headers={"User-Agent": os.environ["WIKI_USER_AGENT"]}, timeout=30)
print("Wikimedia:", wm.status_code, len(wm.json().get("items", [])), "days")        # expect 200 31 days

av = requests.get("https://www.alphavantage.co/query",
                  params={"function": "TIME_SERIES_DAILY", "symbol": "RDDT", "outputsize": "full",
                          "apikey": os.environ["ALPHAVANTAGE_API_KEY"]}, timeout=60)
data = av.json()
series = data.get("Time Series (Daily)", {})
print("Alpha Vantage:", av.status_code, "days:", len(series), "first:", min(series) if series else data)
# expect a first date of 2024-03-21 (Reddit's first trade). Anything else (or a note/error message) -> write it down.
```
- **Unverified:**
  - The Alpha Vantage function name and the `outputsize=full` behavior on the free tier haven't been tested. If the response is a message instead of data, save it in `docs/licenses/` and adjust.
  - The CIK `1713445` is Reddit's, taken from our 2024 index files.
- [ ] Commit:
  `git add . && git status` (check that no `.env` or prices are listed), then `git commit -m "Project setup" && git push -u origin main`.

## Done when
- [ ] The venv works and all packages import.
- [ ] The repo is pushed, with `.env` and `data/prices/` absent from GitHub.
- [ ] The key is in `.env`, and the email has been sent.
- [ ] The smoke test shows SEC 200, Wikimedia 200, and an Alpha Vantage result recorded (whatever it is).
