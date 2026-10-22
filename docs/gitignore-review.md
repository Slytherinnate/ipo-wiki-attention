# .gitignore review (draft, 2026-10-22; no repo initialised yet)

## Already ignored (OK)
- `.env`: keys.
- `data/raw/` (includes `data/raw/tiingo/`), `data/local_only/` (`ipo_returns.csv`): Tiingo data, licensed, local only.
- `data/cache/` (8.4 GB): SEC/Wikimedia caches.
- `data/processed/analysis_set.csv`, `analysis_table.parquet`, `analysis_views/`, `analysis_views_meta.csv`, `market_cap.csv`: per-firm tables joined to returns.

## Would currently be committed

| Path | OK to commit? | Note |
|---|---|---|
| `README.md`, `docs/`, `plan.md`, `requirements.txt` | yes | `docs/licenses/` quotes the Tiingo email; that's fine, but check you're happy publishing it |
| `scripts/`, `app/`, `tests/` | yes | keys only read from the environment |
| `data/public/*.csv` | yes | aggregates, n ≥ 15, test-enforced |
| `figures/*.png` | yes | aggregates only |
| `notebooks/01_eda.ipynb` | **NO, as saved** | saved outputs include LOCAL ONLY per-firm cells (outlier table with returns, per-firm scatter). Strip outputs before committing (`jupyter nbconvert --clear-output --inplace`) or add a pre-commit strip |
| `notebooks/02_model.ipynb` | yes, after a check | outputs are aggregates; strip outputs anyway for consistency |
| `verify/` (958 MB) | **NO** | contains `tiingo_*.log`, `tiingo_fixes_log.csv`, `tiingo_recover_log.csv` (per-ticker Tiingo-derived), `verify/prices/`, and large dump samples (`m.bz2`) |
| `data/universe/` (35 MB) | decide | SEC-derived per-firm data (US government public data) and review worksheets. `titles_v2_all.csv` / `ipo_deals_all.csv` carry `first_trade_conf = tiingo_corrected` and `first_trade_source` for 45 rows (a date derived from the Tiingo first bar). Not prices, but per-ticker Tiingo-derived facts, so safest to ignore. The OneDrive xlsx copies also contain review notes |
| `data/processed/views/`, `views_2024/` (8 MB) | probably yes | per-CIK pageviews (CC0), no returns; but they identify firms in the matched set. Fine under Wikimedia CC0 |
| `scripts/__pycache__/`, `.ipynb_checkpoints/` | no | add patterns |

## Proposed additions (not applied)
```
verify/
data/universe/
data/processed/views/        # optional: only if you prefer not to publish per-firm pageviews
data/processed/views_2024/   # optional, same reason
__pycache__/
.ipynb_checkpoints/
*.xlsx
```
Plus: strip notebook outputs before every commit.

## Addendum (2026-10-22 11:25 MDT): secondary price-source mentions in files marked "yes"
The plan's LOCAL-ONLY rule says material derived from a secondary public price source is never committed, published or cited. Several files in the "yes" row above still mention it, and two contain local-only results or describe the Oct 19 fetches:

| File | Mentions | What's there | Suggestion |
|---|---|---|---|
| `plan.md` | 7 | "122 agree / 2 disagree" cross-check result, year_source note, Rubrik first-trade example | keep local (add to .gitignore) |
| `docs/price-source-tos-survey.md` | 3 | quotes the ToS ban on automated access and describes the Oct 19 curl/browser-UA fetches | keep local |
| `docs/setup-checklist.md` | 3 | local-only gitignore block + note on year_source | keep local or redact lines 87-94 |
| `docs/analysis-tasks.md` | 1 | local-only note | keep local or redact line 56 |
| `docs/build-report-2026-10-20.md` | 1 | sources line | redact the mention or keep local |
| `docs/review-checklist.md` | 1 | "never open price sites" rule naming it | harmless, but could drop the name |
| `data/universe/backup_*/build-report-2026-10-20.md` | 1 each | copies of the build report | covered if `data/universe/` is ignored |

Clean: `README.md`, `docs/report.md`, `scripts/`, `app/`, `tests/`, `data/public/`, `figures/`.
Tests re-run 11:21 MDT: `test_public_aggregates.py` ALL PASS, `test_app.py` APP PASS (28 renders).

Proposed extra .gitignore lines (not applied):
```
plan.md
docs/price-source-tos-survey.md
docs/setup-checklist.md
docs/analysis-tasks.md
docs/build-report-2026-10-20.md
```
