"""
match_all.py: Wikipedia matching v2 + pageview windows for ALL years (2019-2025).

Input : data/universe/ipo_deals_all.csv (from parse_424b4.py)
Output: data/universe/titles_v2_all.csv  every row, with decision + reasons
        data/universe/review_all.csv     REVIEW rows only, with review_sections
                                         pointing to docs/review-checklist.md and
                                         the blank review columns Caleb fills
        data/processed/views/<CIK>.csv   date,views  (anchor-120 .. anchor+60,
                                         missing days = 0, all titles summed)
Anchor date = first_trade_date (stated/derived from the 424B4) else the 424B4
filing date.

Match order (logged in match_method):
  1. wikidata_cik     Wikidata item with P5531 = CIK (from build_ipo_universe.py)
  2. wikidata_ticker  Wikidata P414 NYSE/Nasdaq + P249 ticker = EDGAR ticker,
                      accepted only if the title shares a 4+ letter word with
                      the legal name (tickers are recycled)
  3. search_ticker_verified / search_top_hit (check_titles_v2.search_title)
Decision rules = check_titles_v2.decide (unchanged). Rate limit: PAUSE 0.35 s
(~170 req/min < 200/min). Checkpoint per row: checkpoints/match_<CIK>.json;
raw per-title daily views cached in data/cache/pv/.
"""
import csv, datetime as dt, json, os, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(__file__))
import check_titles_v2 as v2

CK = "data/universe/checkpoints"
PVC = "data/cache/pv"
v2.BLOCKING.add("NAME_MISMATCH")

# Speed-up: 4 worker threads share one global rate limiter of 3 req/s
# (= 180 req/min, under Wikimedia's 200/min). v2.PAUSE is set to 0 and every
# call first waits for a slot. requests.Session is replaced per thread.
import threading, time, requests
_lock, _next = threading.Lock(), [0.0]
_local = threading.local()
_orig_get = v2.get
def _slot():
    with _lock:
        now = time.time()
        wait = max(0.0, _next[0] - now)
        _next[0] = max(now, _next[0]) + 1 / 3.0
    time.sleep(wait)
class _S:
    def get(self, *a, **k):
        if not hasattr(_local, "s"):
            _local.s = requests.Session(); _local.s.headers.update(v2.UA)
        _slot()
        return _local.s.get(*a, **k)
v2.s = _S()
v2.PAUSE = 0
TICK = json.load(open("data/cache/wikidata_tickers.json"))
SECTION = {"SEARCH_UNVERIFIED": "3.1", "DISAMBIG": "3.7", "NO_PRE_IPO_DATA": "3.6", "NO_VIEWS": "3.5",
           "LIST_PAGE": "3.2/3.3", "NAME_MISMATCH": "3.3", "QID_MISMATCH": "3.3", "MANY_REDIRECTS": "3.4", "FOREIGN_ADR": "3.9",
           "NO_PRICE_FOUND": "3.8", "UNITS": "3.8", "WARRANTS_ON_COVER": "3.8", "DATE_UNKNOWN": "3.10"}
REVIEW_COLS = ["keep_drop", "review_code", "review_title", "old_titles", "verified_by", "first_trade_date_checked",
               "date_source", "offer_price_checked", "offer_price_status", "listing_type", "reviewer_notes",
               "reviewed_on"]


def views_cached(title):
    fn = os.path.join(PVC, title.replace("/", "%2F")[:180] + ".json")
    if os.path.exists(fn):
        return json.load(open(fn))
    d = v2.daily_views(title)
    json.dump(d, open(fn, "w"))
    return d


def process(r):
    r = dict(r)
    r.update(final_title="", is_disambig="", redirects_summed=0, first_data_date="", views_30d_pre=0,
             views_30d_post=0, decision="", reasons="", match_method="", name=r["legal_name"])
    reasons = []
    title = r["wiki_title_wd"]
    if title:
        r["match_method"] = "wikidata_cik"
    else:
        for tk in r["tickers"].split():
            for c in TICK.get(tk.upper(), []):
                if v2.name_overlap(r["legal_name"], c["title"]):
                    title, r["match_method"], r["wikidata_qid"] = c["title"], "wikidata_ticker", c["qid"]
                    break
            if title:
                break
    if not title:
        title, method = v2.search_title(r["legal_name"], r["tickers"])
        if not title:
            r["decision"] = "DROP_NO_ARTICLE"
            return r
        r["match_method"] = method
        if method == "search_top_hit":
            reasons.append("SEARCH_UNVERIFIED")
        elif not v2.name_overlap(r["legal_name"], title):
            # ticker found on a page whose title shares no word with the
            # company (e.g. a fund or index page listing holdings) -> review
            reasons.append("NAME_MISMATCH")
    info = v2.page_details(title)
    if info is None:
        r["decision"] = "DROP_NO_ARTICLE"
        return r
    r["final_title"], r["is_disambig"] = info["final_title"], "yes" if info["is_disambig"] else ""
    if r["match_method"].startswith("search") and r.get("wikidata_qid") and info["qid"] != r["wikidata_qid"]:
        reasons.append("QID_MISMATCH")
    if info["is_disambig"]:
        reasons.append("DISAMBIG")
    total = defaultdict(int)
    titles = [info["final_title"]] + info["redirects"][:v2.MAX_REDIRECTS]
    for t in titles:
        for day, v in views_cached(t).items():
            total[day] += v
    r["redirects_summed"] = len(titles) - 1
    if len(info["redirects"]) > v2.MAX_REDIRECTS:
        reasons.append("MANY_REDIRECTS")
    anchor = dt.date.fromisoformat(r.get("first_trade_date") or r["filing_date_424b4"])
    r["anchor_date"] = anchor.isoformat()
    day = lambda k: (anchor + dt.timedelta(days=k)).strftime("%Y%m%d")
    r["views_30d_pre"] = sum(total.get(day(-k), 0) for k in range(1, 31))
    r["views_30d_post"] = sum(total.get(day(k), 0) for k in range(0, 30))
    if total:
        f = min(total)
        r["first_data_date"] = f"{f[:4]}-{f[4:6]}-{f[6:]}"
        if dt.date.fromisoformat(r["first_data_date"]) > anchor - dt.timedelta(days=30):
            reasons.append("NO_PRE_IPO_DATA")
    else:
        reasons.append("NO_VIEWS")
    if r.get("foreign_flag"):
        reasons.append("FOREIGN_ADR")
    r["reasons"] = " ".join(reasons)
    r["decision"] = "PENDING"
    v2.decide(r)
    if not r["decision"].startswith("DROP"):
        os.makedirs("data/processed/views", exist_ok=True)
        with open(f"data/processed/views/{r['cik']}.csv", "w") as fh:
            fh.write("date,day_rel,views\n")
            for k in range(-120, 61):
                d = anchor + dt.timedelta(days=k)
                fh.write(f"{d.isoformat()},{k},{total.get(d.strftime('%Y%m%d'), 0)}\n")
    return r


def main():
    os.makedirs(PVC, exist_ok=True)
    rows = [r for r in csv.DictReader(open("data/universe/ipo_deals_all.csv", encoding="utf-8"))
            if r["status"] == "OPERATING"]
    from concurrent.futures import ThreadPoolExecutor
    def one(item):
        n, r = item
        ck = os.path.join(CK, f"match_{r['cik']}_{r['year']}.json")
        if os.path.exists(ck):
            return json.load(open(ck))
        res = process(r)
        json.dump(res, open(ck, "w"))
        print(f"[{n}/{len(rows)}] {r['year']} {r['legal_name']} -> {res['final_title']} {res['decision']} {res['reasons']}",
              flush=True)
        return res
    with ThreadPoolExecutor(4) as ex:
        out = list(ex.map(one, enumerate(rows, 1)))
    # review sections: title reasons + deal flags (price/date) for kept/review rows
    for r in out:
        extra = r.get("deal_flags", "").split()
        if r.get("first_trade_conf") == "unknown":
            extra.append("DATE_UNKNOWN")
        secs = sorted({SECTION[x] for x in r["reasons"].split() + extra if x in SECTION})
        r["review_sections"] = " ".join(secs)
        for c in REVIEW_COLS:
            r.setdefault(c, "")
    fields = list(dict.fromkeys(k for r in out for k in r))
    for path, sub in (("data/universe/titles_v2_all.csv", out),
                      ("data/universe/review_all.csv", [r for r in out if r["decision"] == "REVIEW"])):
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(sub)
    print("done", len(out))


if __name__ == "__main__":
    main()
