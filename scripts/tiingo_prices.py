"""
tiingo_prices.py: first-day "pop" and 30-trading-day return per IPO from Tiingo EOD.

LICENSE RULES (docs/licenses/tiingo-reply-2026-10-20.md):
  * raw Tiingo data stays local: data/raw/tiingo/ (gitignored)
  * per-ticker prices/returns are never published: output goes to
    data/local_only/ipo_returns.csv (gitignored); only aggregates over 15+ IPOs
    may be published
  * Tiingo data is never compared against / used to validate any other price dataset
  * key: env TIINGO_API_KEY, sent only in the "Authorization: Token" header;
    never printed, never in URLs, logs or cache file names
Method:
  1. ticker = EDGAR submissions ticker, else the symbol named on the 424B4 cover
     ('under the symbol "XXXX"'), which also covers delisted/acquired companies
  2. (metadata lookup removed Oct 24 2026: Tiingo no longer judges identity or listing history)
  3. GET /tiingo/daily/<ticker>/prices?startDate=<anchor-7d>&endDate=<anchor+70d>
  4. NO checks against Tiingo (Oct 24 2026): dates, identity and sample come from SEC only;
     a missing bar on the SEC date means a missing return (see one())
  5. pop = close(day 0)/offer - 1; ret30 = close(trading day 30)/offer - 1, day 0 =
     first trading day. Uses UNADJUSTED close (offer price is unadjusted). If a
     splitFactor != 1 occurs inside the window, unadjusted closes after the split
     are rescaled to pre-split terms (close * cumulative split factor) and the
     row is flagged SPLIT_IN_WINDOW. Dividends are ignored (price return).
Rate limit: 1 request/second (far under Power plan limits), 4 retries with
backoff on 429/5xx/timeouts. Cache: data/raw/tiingo/{meta,prices}/<ticker>_<start>.json
Run: python scripts/tiingo_prices.py --test | --all   [--offline = cached prices only]
"""
import csv, datetime as dt, html, json, os, re, sys, time
import requests

BASE = "https://api.tiingo.com/tiingo/daily"
RAW = "data/raw/tiingo"
OUT = "data/local_only/ipo_returns.csv"
TEST = ["1638826", "1643269", "1874178", "1639438", "1795586"]   # filled below by name lookup
TEST_NAMES = ["Progyny", "Sumo Logic", "Rivian", "CAVA", "Chime Financial"]
_last = [0.0]


def get(path, params=None):
    key = os.environ.get("TIINGO_API_KEY")
    if not key:
        raise SystemExit("TIINGO_API_KEY not set")
    h = {"Authorization": "Token " + key, "Content-Type": "application/json",
         "User-Agent": "CalebHavens-DSPortfolio/0.3 (calebhavens08@gmail.com)"}
    for attempt in range(5):
        wait = 1.0 - (time.time() - _last[0])
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()
        try:
            r = requests.get(BASE + path, params=params, headers=h, timeout=30)
        except requests.RequestException as e:
            print(f"  network error {type(e).__name__}, retry {attempt + 1}", flush=True)
            time.sleep(5 * (attempt + 1)); continue
        if r.status_code == 404:
            return None
        if r.status_code in (429, 500, 502, 503, 504):
            print(f"  HTTP {r.status_code}, retry {attempt + 1}", flush=True)
            time.sleep(10 * (attempt + 1)); continue
        if r.status_code in (401, 403):
            raise SystemExit(f"HTTP {r.status_code} from Tiingo (auth/plan) on {path}")
        r.raise_for_status()
        return r.json()
    raise RuntimeError("Tiingo failed after retries: " + path)


OFFLINE = "--offline" in sys.argv   # cache only, never calls the API


def cached(kind, name, fn):
    p = os.path.join(RAW, kind, re.sub(r"[^A-Za-z0-9_.-]", "_", name) + ".json")
    if os.path.exists(p):
        return json.load(open(p))
    if OFFLINE:
        return None
    data = fn()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(data, open(p, "w"))
    return data


def cover_symbol(row):
    """Symbol named on the cached 424B4/424B1 cover, e.g. under the symbol "SUMO"."""
    acc = row["accession"]
    for f in os.listdir("data/cache/424b4"):
        if acc in f:
            t = html.unescape(re.sub(r"<[^>]+>", " ", open(os.path.join("data/cache/424b4", f), errors="replace").read()[:300000]))
            m = re.search(r"under the (?:trading )?symbols? [“\"']\s*([A-Z.]{1,6})\s*[”\"']", t)
            return m.group(1).rstrip(".") if m else ""
    return ""


def words(x):
    stop = {"inc", "corp", "corporation", "holdings", "group", "ltd", "plc", "company", "class", "common", "stock", "the"}
    return {w for w in re.sub(r"[^a-z0-9]+", " ", x.lower()).split() if len(w) >= 3 and w not in stop}


def nth_trading_close(prices, i):
    return prices[i] if i < len(prices) else None


def one(row):
    """Returns on the SEC first-trade date only (Oct 24 2026). Tiingo prices are used for returns
    and nothing else: Tiingo never sets or checks a date, a firm's identity, or who is in the sample.
    Ticker = EDGAR submissions ticker, else the 424B4 cover symbol. If EDGAR's company_tickers.json
    assigns that ticker to a different CIK, the ticker was reused: return missing (SEC check).
    Day 0 = the SEC first_trade_date; no SEC date or no Tiingo bar on that date -> return missing."""
    res = {k: row[k] for k in ("year", "cik", "decision", "legal_name", "sector", "offer_price", "first_trade_date", "first_trade_conf")}
    flags = []
    cov = cover_symbol(row)
    edgar = row["tickers"].split()[0] if row["tickers"] else ""
    tk = edgar or cov
    res.update(edgar_ticker=edgar, cover_ticker=cov, tiingo_ticker=tk)
    if not tk:
        res["flags"] = "NO_TICKER"; return res
    owner = SEC_TICKERS.get(tk.upper())
    if owner and owner != str(int(row["cik"])):
        res["flags"] = "SEC_TICKER_REUSE"; return res
    if not row["first_trade_date"]:
        res["flags"] = "NO_SEC_FIRST_TRADE_DATE"; return res
    anchor = dt.date.fromisoformat(row["first_trade_date"])
    s, e = (anchor - dt.timedelta(days=7)).isoformat(), (anchor + dt.timedelta(days=70)).isoformat()
    px = cached("prices", f"{tk}_{s}", lambda: get(f"/{tk}/prices", {"startDate": s, "endDate": e}))
    if not px:
        res["flags"] = "NO_PRICES_IN_WINDOW"; return res
    px = [p for p in px if p["date"][:10] >= row["first_trade_date"]]
    if not px or px[0]["date"][:10] != row["first_trade_date"]:
        res["flags"] = "NO_BAR_ON_SEC_DATE"; return res
    cum, closes = 1.0, []
    for p in px:
        sf = float(p.get("splitFactor") or 1)
        if sf != 1 and p is not px[0]:
            cum *= sf; flags.append("SPLIT_IN_WINDOW")
        closes.append((p["date"][:10], float(p["close"]) * cum, float(p["open"])))
    offer = float(row["offer_price"])
    d0 = closes[0]
    res.update(day0_open=d0[2], day0_close=round(d0[1], 4), pop=round(d0[1] / offer - 1, 4))
    d30 = nth_trading_close(closes, 30)
    if d30:
        res.update(day30_date=d30[0], day30_close=round(d30[1], 4), ret30=round(d30[1] / offer - 1, 4))
    else:
        flags.append("LT_30_TRADING_DAYS")
    res["n_days_window"] = len(closes)
    res["flags"] = " ".join(dict.fromkeys(flags))
    res["returns_status"] = "OK"
    return res


SEC_TICKERS = {v["ticker"].upper(): str(v["cik_str"]) for v in json.load(open("data/cache/company_tickers.json")).values()}


def main(mode):
    rows = list(csv.DictReader(open("data/universe/titles_v2_all.csv", encoding="utf-8")))
    rows = [r for r in rows if r["decision"] in ("AUTO_KEEP", "REVIEW") and r["offer_price"] and r.get("attention_only") != "1"]
    if mode == "--test":
        pick = []
        for n in TEST_NAMES:
            pick += [r for r in rows if r["legal_name"].lower().startswith(n.lower())][:1]
        rows = pick
    out = []
    for i, r in enumerate(rows, 1):
        try:
            res = one(r)
        except (RuntimeError, ValueError, KeyError, TypeError) as e:     # keep going; logged per row
            res = {"year": r["year"], "cik": r["cik"], "decision": r["decision"], "legal_name": r["legal_name"],
                   "flags": f"ERROR {type(e).__name__}"}
        out.append(res)
        print(f"[{i}/{len(rows)}] {r['year']} {r['legal_name'][:30]} -> {res.get('flags', '')}", flush=True)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    path = OUT if mode == "--all" else OUT.replace(".csv", "_test5.csv")
    fields = list(dict.fromkeys(k for o in out for k in o))
    w = csv.DictWriter(open(path, "w", newline="", encoding="utf-8"), fieldnames=fields)
    w.writeheader(); w.writerows(out)
    print("wrote", path)


if __name__ == "__main__":
    main("--all" if "--all" in sys.argv else "--test")
