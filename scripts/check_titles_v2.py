"""
check_titles_v2.py: for each IPO in the universe, find/verify the Wikipedia
article, add up views across its old titles, and decide auto-keep vs. review.

Input : data/universe/ipo_universe_YYYY.csv (from build_ipo_universe.py)
Output: data/universe/titles_v2_YYYY.csv (every row, with a decision)
        data/universe/review_YYYY.csv   (only rows Caleb needs to look at)
        data/processed/views_YYYY/<CIK>.csv (daily views, all titles summed)

Decision rules (in order):
  DROP_EXCLUDED : SPAC or fund/trust (not an operating-company IPO)
  DROP_NO_ARTICLE : no Wikidata CIK match and the search API found nothing
  AUTO_KEEP : matched by Wikidata CIK, or a search hit whose article cites
              the company's ticker next to NYSE/Nasdaq; not a disambiguation page,
              and pageview data exists at least 30 days before the 424B4 date
  REVIEW : unverified-but-plausible search match (shares a word with the
           company name), disambig, list page, no pre-IPO data, no views.
  (An unverified search hit sharing no word with the name -> DROP_NO_ARTICLE.)
  FOREIGN_ADR / MANY_REDIRECTS are informational, not blocking.
  Re-apply rules without API calls: python scripts/check_titles_v2.py --redecide 2024

Old titles: Wikipedia keeps a redirect at the old name when a page is moved,
so the redirects pointing at the article cover old titles. Their pageviews
are added to the main title's views day by day (cap: MAX_REDIRECTS).

Run: python scripts/check_titles_v2.py 2024
"""
import csv
import datetime as dt
import os
import sys
import time
from collections import defaultdict
from urllib.parse import quote

import requests

UA = {"User-Agent": "CalebHavens-DSPortfolio/0.2 (wiki-attention IPO study; calebhavens08@gmail.com)"}
API = "https://en.wikipedia.org/w/api.php"
PV = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user"
PAUSE = 0.35          # ~170 calls/min, under Wikimedia's 200/min
MAX_REDIRECTS = 15    # old titles summed per article (most have far fewer)
s = requests.Session()
s.headers.update(UA)


def get(url, params=None):
    for attempt in range(4):
        time.sleep(PAUSE)
        try:
            r = s.get(url, params=params, timeout=30)
        except requests.RequestException:      # timeout or dropped connection: wait, retry
            time.sleep(5 * (attempt + 1))
            continue
        if r.status_code in (429, 503):
            time.sleep(int(r.headers.get("Retry-After", 5 * (attempt + 1))))
            continue
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()
    return None


def search_title(name, tickers):
    """Fallback when Wikidata has no CIK match.
    Search Wikipedia for the company name, then open the top 3 hits and accept
    the first whose wikitext mentions one of the company's tickers next to an
    exchange (e.g. {{NYSE|RDDT}}). Returns (title, method)."""
    import re
    clean = name.replace(",", " ")
    for junk in (" Inc.", " Inc", " INC.", " INC", " Corp.", " Corp", " Corporation", " Holdings",
                 " Holding", " Ltd.", " Ltd", " plc", " /DE/", " LLC", " Co.", " Group"):
        clean = clean.replace(junk, " ")
    d = get(API, {"action": "query", "list": "search", "srsearch": clean.strip(),
                  "srlimit": 3, "format": "json", "formatversion": 2})
    hits = [h["title"] for h in (d["query"]["search"] if d else [])]
    if not hits:
        return "", ""
    if tickers:
        d = get(API, {"action": "query", "titles": "|".join(hits), "prop": "revisions", "rvprop": "content",
                      "rvslots": "main", "redirects": 1, "format": "json", "formatversion": 2})
        texts = {p["title"]: p["revisions"][0]["slots"]["main"]["content"]
                 for p in d["query"]["pages"] if p.get("revisions")}
        for t in texts:
            if t.startswith(("List of", "Companies listed")):
                continue                      # index pages list many tickers
            for tk in tickers.split():
                if re.search(r"(NYSE|Nasdaq|NASDAQ|nasdaq|nyse)[^\n]{0,40}\b" + re.escape(tk) + r"\b", texts[t]):
                    return t, "search_ticker_verified"
    return hits[0], "search_top_hit"


def page_details(title):
    """Resolve redirects; return final title, disambig?, wikidata id, redirect titles."""
    d = get(API, {"action": "query", "titles": title, "redirects": 1, "format": "json", "formatversion": 2,
                  "prop": "pageprops|redirects", "ppprop": "disambiguation|wikibase_item",
                  "rdlimit": "max", "rdnamespace": 0})
    p = d["query"]["pages"][0]
    if p.get("missing"):
        return None
    props = p.get("pageprops", {})
    return {"final_title": p["title"], "is_disambig": "disambiguation" in props,
            "qid": props.get("wikibase_item", ""),
            "redirects": [r["title"] for r in p.get("redirects", [])]}


def daily_views(title):
    t = quote(title.replace(" ", "_"), safe="")
    d = get(f"{PV}/{t}/daily/2015070100/2025123100")
    return {i["timestamp"][:8]: i["views"] for i in d["items"]} if d else {}


BLOCKING = {"SEARCH_UNVERIFIED", "DISAMBIG", "NO_PRE_IPO_DATA", "NO_VIEWS", "LIST_PAGE", "QID_MISMATCH"}
# FOREIGN_ADR, MANY_REDIRECTS and NO_REG_IN_RECENT are kept as information
# columns but do not block auto-keep (Caleb can filter on them later).


def name_overlap(name, title):
    """True if the article title shares a real word (4+ letters) with the company name."""
    stop = {"inc", "corp", "corporation", "holdings", "holding", "group", "ltd", "limited", "company", "technologies",
            "technology", "therapeutics", "international", "global"}
    words = lambda x: {w for w in "".join(c.lower() if c.isalnum() else " " for c in x).split()
                       if len(w) >= 4 and w not in stop}
    return bool(words(name) & words(title))


def decide(r):
    """Apply the decision rules to a row that already has reasons filled in."""
    if r["decision"].startswith("DROP"):
        return r
    reasons = set(r["reasons"].split())
    if r["final_title"].startswith(("List of", "Companies listed")):
        reasons.add("LIST_PAGE")
    if "SEARCH_UNVERIFIED" in reasons and not name_overlap(r["name"], r["final_title"]):
        r["decision"], r["reasons"] = "DROP_NO_ARTICLE", "search hit unrelated to company name"
        return r
    r["reasons"] = " ".join(sorted(reasons))
    r["decision"] = "REVIEW" if reasons & BLOCKING else "AUTO_KEEP"
    return r


def write_outputs(year, out):
    fields = list(out[0].keys()) + (["keep_drop"] if "keep_drop" not in out[0] else [])
    for path, subset in ((f"data/universe/titles_v2_{year}.csv", out),
                         (f"data/universe/review_{year}.csv", [r for r in out if r["decision"] == "REVIEW"])):
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(subset)


def redecide(year):
    """Re-apply decide() to an existing titles_v2 file without calling any API."""
    rows = list(csv.DictReader(open(f"data/universe/titles_v2_{year}.csv", encoding="utf-8")))
    write_outputs(year, [decide(r) for r in rows])


def main(year):
    src = f"data/universe/ipo_universe_{year}.csv"
    rows = list(csv.DictReader(open(src, encoding="utf-8")))
    os.makedirs(f"data/processed/views_{year}", exist_ok=True)
    out = []
    for n, r in enumerate(rows, 1):
        reasons = []
        r.update(final_title="", is_disambig="", redirects_summed=0, first_data_date="",
                 views_30d_pre=0, views_30d_post=0, decision="", reasons="")
        if "SPAC" in r["flags"] or "FUND_OR_TRUST" in r["flags"]:
            r["decision"] = "DROP_EXCLUDED"
            out.append(r)
            continue
        title = r["wiki_title"]
        if not title:
            title, method = search_title(r["name"], r["tickers"])
            if not title:
                r["decision"] = "DROP_NO_ARTICLE"
                out.append(r)
                continue
            r["match_method"] = method
            if method == "search_top_hit":
                reasons.append("SEARCH_UNVERIFIED")
        info = page_details(title)
        if info is None:
            r["decision"] = "DROP_NO_ARTICLE"
            out.append(r)
            continue
        r["final_title"], r["is_disambig"] = info["final_title"], "yes" if info["is_disambig"] else ""
        if r["match_method"] == "search_top_hit" and r.get("wikidata_qid") and info["qid"] != r["wikidata_qid"]:
            reasons.append("QID_MISMATCH")
        if info["is_disambig"]:
            reasons.append("DISAMBIG")
        # Sum views across the article and its redirects (old titles).
        total = defaultdict(int)
        titles = [info["final_title"]] + info["redirects"][:MAX_REDIRECTS]
        for t in titles:
            for day, v in daily_views(t).items():
                total[day] += v
        r["redirects_summed"] = len(titles) - 1
        if len(info["redirects"]) > MAX_REDIRECTS:
            reasons.append("MANY_REDIRECTS")
        ipo = dt.date.fromisoformat(r["filing_date_424b4"])
        pre = {(ipo - dt.timedelta(days=k)).strftime("%Y%m%d") for k in range(1, 31)}
        post = {(ipo + dt.timedelta(days=k)).strftime("%Y%m%d") for k in range(0, 30)}
        r["views_30d_pre"] = sum(total.get(d, 0) for d in pre)
        r["views_30d_post"] = sum(total.get(d, 0) for d in post)
        if total:
            first = min(total)
            r["first_data_date"] = f"{first[:4]}-{first[4:6]}-{first[6:]}"
            if dt.date.fromisoformat(r["first_data_date"]) > ipo - dt.timedelta(days=30):
                reasons.append("NO_PRE_IPO_DATA")
        else:
            reasons.append("NO_VIEWS")
        for f in ("FOREIGN_ADR", "NO_REG_IN_RECENT"):
            if f in r["flags"]:
                reasons.append(f)
        with open(f"data/processed/views_{year}/{r['cik']}.csv", "w") as f:
            f.write("date,views\n" + "".join(f"{d},{total[d]}\n" for d in sorted(total)))
        r["reasons"] = " ".join(reasons)
        r["decision"] = "PENDING"
        decide(r)
        out.append(r)
        print(f"[{n}/{len(rows)}] {r['name']} -> {r['final_title']} {r['decision']} {r['reasons']}")

    write_outputs(year, out)
    print("done", year)


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--redecide":        # re-apply rules only, no API calls
        for y in args[1:]:
            redecide(y)
    else:
        for y in args or ["2024"]:
            main(y)
