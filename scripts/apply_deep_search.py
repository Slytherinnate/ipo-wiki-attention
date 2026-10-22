"""Apply deep_search_miss.py results to titles_v2_all.csv / review_all.csv.
Idempotent: works from the deep_* checkpoints and the original SEARCH_MISS
tag (kept in reasons). Nothing is deleted. Writes:
  verify/deep_search_evidence.csv  one row per SEARCH_MISS company: class,
     best title, every candidate with its IDs + methods, per-method hits
  data/processed/views/<CIK>.csv   for FOUND_STRONG (-120..+60, redirects summed, 0-fill)
Decisions:
  FOUND_STRONG -> AUTO_KEEP (match_method deep_strong); still REVIEW if the
     standard blocking checks fire (NO_PRE_IPO_DATA / NO_VIEWS), same as v2
  FOUND_CANDIDATE -> REVIEW, reason SEARCH_CANDIDATE (checklist 3.1)
  NO_ARTICLE_CONFIRMED -> DROP_NO_ARTICLE_CONFIRMED
  UNCERTAIN -> REVIEW, reason SEARCH_MISS (unchanged)"""
import csv, datetime as dt, json, os, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(__file__))
import match_all as ma
v2 = ma.v2
p = "data/universe/titles_v2_all.csv"
t = list(csv.DictReader(open(p, encoding="utf-8")))
ev_rows = []
for r in t:
    if "SEARCH_MISS" not in r["reasons"].split() and "SEARCH_CANDIDATE" not in r["reasons"].split() \
            and r.get("deep_class", "") == "":
        continue
    ck = f"data/universe/checkpoints/deep_{r['cik']}_{r['year']}.json"
    if not os.path.exists(ck):
        continue
    e = json.load(open(ck))
    cls, best = e["class"], e.get("best_title", "")
    r["deep_class"], r["deep_best_title"] = cls, best
    cands = e.get("candidates", {})
    r["deep_candidates"] = " | ".join(f"{k} [{','.join(v['ids'])}]" for k, v in
                                      sorted(cands.items(), key=lambda kv: -len(kv[1]["ids"])) if v["ids"])[:500]
    base = [x for x in r["reasons"].split() if x not in ("SEARCH_MISS", "SEARCH_CANDIDATE")]
    if cls == "FOUND_STRONG":
        info = v2.page_details(best)
        total = defaultdict(int)
        titles = [info["final_title"]] + info["redirects"][:v2.MAX_REDIRECTS]
        for x in titles:
            for d, v in ma.views_cached(x).items():
                total[d] += v
        anchor = dt.date.fromisoformat(r.get("first_trade_date") or r["filing_date_424b4"])
        r.update(final_title=info["final_title"], match_method="deep_strong", redirects_summed=len(titles) - 1,
                 anchor_date=anchor.isoformat())
        day = lambda k: (anchor + dt.timedelta(days=k)).strftime("%Y%m%d")
        r["views_30d_pre"] = sum(total.get(day(-k), 0) for k in range(1, 31))
        r["views_30d_post"] = sum(total.get(day(k), 0) for k in range(0, 30))
        reasons = base
        if total:
            f = min(total); r["first_data_date"] = f"{f[:4]}-{f[4:6]}-{f[6:]}"
            if dt.date.fromisoformat(r["first_data_date"]) > anchor - dt.timedelta(days=30):
                reasons.append("NO_PRE_IPO_DATA")
        else:
            reasons.append("NO_VIEWS")
        r["reasons"] = " ".join(reasons + ["SEARCH_MISS_RESOLVED"])
        r["decision"] = "REVIEW" if {"NO_PRE_IPO_DATA", "NO_VIEWS"} & set(reasons) else "AUTO_KEEP"
        with open(f"data/processed/views/{r['cik']}.csv", "w") as fh:
            fh.write("date,day_rel,views\n")
            for k in range(-120, 61):
                d = anchor + dt.timedelta(days=k)
                fh.write(f"{d.isoformat()},{k},{total.get(d.strftime('%Y%m%d'), 0)}\n")
    elif cls == "FOUND_CANDIDATE":
        r["decision"], r["reasons"] = "REVIEW", " ".join(base + ["SEARCH_CANDIDATE"])
    elif cls == "NO_ARTICLE_CONFIRMED":
        r["decision"], r["reasons"] = "DROP_NO_ARTICLE_CONFIRMED", " ".join(base + ["SEARCH_MISS"])
    else:
        r["decision"], r["reasons"] = "REVIEW", " ".join(base + ["SEARCH_MISS"])
    ev_rows.append({"year": r["year"], "cik": r["cik"], "legal_name": r["legal_name"], "tickers": r["tickers"],
                    "class": cls, "best_title": best, "decision": r["decision"],
                    "candidates_with_ids": r["deep_candidates"],
                    "m1_wikidata_cik": "; ".join(e.get("methods", {}).get("M1_wikidata_cik") or []),
                    "m2_wikidata_ticker": "; ".join(e.get("methods", {}).get("M2_wikidata_ticker") or []),
                    "m3_search_hits": "; ".join(e.get("methods", {}).get("M3_search") or [])[:400],
                    "m5_wikidata_name": "; ".join(e.get("methods", {}).get("M5_wikidata_name") or []),
                    "m4_exact_titles": "; ".join(e.get("methods", {}).get("M4_exact_title") or []),
                    "name_variants": "; ".join(e.get("name_variants", [])), "all_methods_ok": e.get("all_methods_ok", ""),
                    "error": e.get("error", "")})
fields = list(dict.fromkeys(k for r in t for k in r))
for path, sub in ((p, t), ("data/universe/review_all.csv", [r for r in t if r["decision"] == "REVIEW"])):
    w = csv.DictWriter(open(path, "w", newline="", encoding="utf-8"), fieldnames=fields, extrasaction="ignore")
    w.writeheader(); w.writerows(sub)
w = csv.DictWriter(open("verify/deep_search_evidence.csv", "w", newline="", encoding="utf-8"), fieldnames=list(ev_rows[0]))
w.writeheader(); w.writerows(ev_rows)
from collections import Counter
print(Counter(e["class"] for e in ev_rows), Counter(e["decision"] for e in ev_rows))
