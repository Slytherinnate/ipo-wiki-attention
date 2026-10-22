"""
check_titles.py: pre-fill and flag Wikipedia titles before the data pull.

What it does, for each row of candidates.csv (name, category, event_type, sector, guess_title,
ipo_year, year_source):
  1. Asks the MediaWiki Action API whether the page exists, whether it is a
     redirect (and where it points), and whether it is a disambiguation page.
  2. Asks for the move log (renames) of the final title.
  3. Asks the Pageviews API for the first date with data and the 2024 median
     daily views (user traffic only).
  4. Writes titles.csv with flags. Caleb reviews it and fills in shared_flag,
     event dates, source_url and keep_drop by hand.

Run:  python scripts/check_titles.py candidates.csv titles.csv
Needs: pip install requests
"""
import csv
import statistics
import sys
import time
from urllib.parse import quote

import requests

# Wikimedia asks for a descriptive User-Agent with contact info.
# https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_User-Agent_Policy
HEADERS = {"User-Agent": "CalebHavens-DSPortfolio/0.1 (wiki-attention title check; calebhavens08@gmail.com) python-requests"}
ACTION_API = "https://en.wikipedia.org/w/api.php"
PAGEVIEWS = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user"

PAUSE = 0.4          # seconds between calls, so ~150/min, under the 200/min limit
LOW_VIEWS = 100      # median daily views below this get a LOW_VIEWS flag (tunable)

session = requests.Session()
session.headers.update(HEADERS)


def get_json(url, params=None):
    """One polite GET. Waits PAUSE seconds, retries on 429/503 per Retry-After."""
    for attempt in range(4):
        time.sleep(PAUSE)
        r = session.get(url, params=params, timeout=30)
        if r.status_code in (429, 503):
            wait = int(r.headers.get("Retry-After", 5 * (attempt + 1)))
            print(f"  server busy, waiting {wait}s")
            time.sleep(wait)
            continue
        if r.status_code == 404:          # pageviews API: no data for this title
            return None
        r.raise_for_status()
        return r.json()
    return None


def page_info(titles):
    """Look up up to 50 titles in one call. Returns {asked_title: info dict}."""
    data = get_json(ACTION_API, {
        "action": "query", "format": "json", "formatversion": 2,
        "titles": "|".join(titles), "redirects": 1,
        "prop": "info|pageprops", "ppprop": "disambiguation",
    })["query"]
    # The API reports title fixes in steps: normalized (case/underscores), then redirects.
    step = {t: t for t in titles}
    for n in data.get("normalized", []):
        for k, v in step.items():
            if v == n["from"]:
                step[k] = n["to"]
    redirected_from = {}
    for rd in data.get("redirects", []):
        for k, v in step.items():
            if v == rd["from"]:
                redirected_from[k] = rd["from"]
                step[k] = rd["to"]
    pages = {p["title"]: p for p in data.get("pages", [])}
    out = {}
    for asked, final in step.items():
        p = pages.get(final, {})
        out[asked] = {
            "final_title": final,
            "redirect_from": redirected_from.get(asked, ""),
            "missing": p.get("missing", False) or not p,
            "is_disambig": "disambiguation" in p.get("pageprops", {}),
        }
    return out


def move_log(title):
    """Renames involving this title (moves FROM it). Returns 'date: old -> new; ...'."""
    data = get_json(ACTION_API, {
        "action": "query", "format": "json", "formatversion": 2,
        "list": "logevents", "letype": "move", "letitle": title, "lelimit": 10,
    })
    events = data["query"]["logevents"] if data else []
    return "; ".join(f'{e["timestamp"][:10]}: {e["title"]} -> {e.get("params", {}).get("target_title", "?")}'
                     for e in events)


def pageview_stats(title):
    """First date with data (since July 2015) and the 2024 median daily views."""
    t = quote(title.replace(" ", "_"), safe="")
    data = get_json(f"{PAGEVIEWS}/{t}/daily/2015070100/2025123100")
    items = data["items"] if data else []
    if not items:
        return "", ""
    first = items[0]["timestamp"][:8]
    first = f"{first[:4]}-{first[4:6]}-{first[6:]}"
    # The API leaves out zero-view days, so pad 2024 up to 366 days with zeros.
    views_2024 = [i["views"] for i in items if i["timestamp"].startswith("2024")]
    views_2024 += [0] * (366 - len(views_2024))
    return first, statistics.median(views_2024)


def main(in_path, out_path):
    with open(in_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # Step 1: page info, 50 titles per call.
    guesses = [r["guess_title"] for r in rows]
    info = {}
    for i in range(0, len(guesses), 50):
        info.update(page_info(guesses[i:i + 50]))

    fields = ["name", "category", "event_type", "sector", "ipo_year", "year_source", "final_title", "redirect_from", "is_disambig", "shared_flag",
              "rename_log", "first_data_date", "median_daily_views_2024", "flags",
              "announce_date", "release_date", "source_url", "keep_drop"]
    out = []
    for n, r in enumerate(rows, 1):
        i = info[r["guess_title"]]
        print(f"[{n}/{len(rows)}] {r['guess_title']} -> {i['final_title']}")
        flags = []
        rec = {k: "" for k in fields}
        rec.update(name=r["name"], category=r["category"],
                   event_type=r.get("event_type", ""), sector=r.get("sector", ""),
                   ipo_year=r.get("ipo_year", ""), year_source=r.get("year_source", ""), final_title=i["final_title"],
                   redirect_from=i["redirect_from"], is_disambig="yes" if i["is_disambig"] else "")
        if i["missing"]:
            flags.append("MISSING")
        else:
            if i["redirect_from"]:
                flags.append("REDIRECT")
            if i["is_disambig"]:
                flags.append("DISAMBIG")
            # Steps 2 and 3 only make sense for pages that exist.
            rec["rename_log"] = move_log(i["final_title"])
            if rec["rename_log"]:
                flags.append("RENAMED")
            first, median = pageview_stats(i["final_title"])
            rec["first_data_date"], rec["median_daily_views_2024"] = first, median
            if median == "":
                flags.append("NO_VIEWS")
            elif median < LOW_VIEWS:
                flags.append("LOW_VIEWS")
            if first and first > "2023-01-01":
                flags.append("STARTS_LATE")   # page created mid-window
        rec["flags"] = " ".join(flags)
        out.append(rec)

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out)
    print(f"wrote {len(out)} rows to {out_path}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "candidates.csv",
         sys.argv[2] if len(sys.argv) > 2 else "titles.csv")
