"""Add first-time IPOs whose final prospectus was filed as a 424B1 (not 424B4)
to data/universe/ipo_universe_YYYY.csv (Caleb, Oct 20 2026).
Same filters as build_ipo_universe.classify (no 10-K/10-Q/20-F before, no
earlier 424B4), plus: no earlier 424B1, and CIK not already in any year's
universe. Name at filing date from the EDGAR index -> SPAC rule as in the fix.
New column form_type (424B4/424B1). The date column keeps its old name
filing_date_424b4 but holds the 424B1 date for those rows (form_type says which).
SEC: cached GETs, 0.15 s pause (~7 req/s), UA with calebhavens08@gmail.com.
Checkpoint: data/universe/checkpoints/b1_<CIK>.json (classify result or null)."""
import csv, json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
import build_ipo_universe as b

SP = re.compile(r"\bacquisition\b|\bspac\b|\bblank check\b", re.I)
CK = "data/universe/checkpoints"
years = [str(y) for y in range(2019, 2026)]
existing = set()
for y in years:
    existing |= {r["cik"] for r in csv.DictReader(open(f"data/universe/ipo_universe_{y}.csv"))}
wd = b.wikidata_cik_map()
for y in years:
    cands = {}
    for q in range(1, 5):
        for line in open(f"data/cache/index/{y}Q{q}.idx", errors="replace"):
            if line.startswith("424B1 "):
                p = line.split(); cik, date = p[-3], p[-2]
                if cik not in cands or date < cands[cik][1]:
                    cands[cik] = (" ".join(p[1:-3]), date)
    p = f"data/universe/ipo_universe_{y}.csv"
    rows = list(csv.DictReader(open(p, encoding="utf-8")))
    for r in rows:
        r.setdefault("form_type", "424B4") or None
        if not r.get("form_type"):
            r["form_type"] = "424B4"
    added = 0
    for cik, (name, date) in sorted(cands.items()):
        if cik in existing:
            continue
        ck = os.path.join(CK, f"b1_{cik}_{y}.json")
        if os.path.exists(ck):
            r = json.load(open(ck))
        else:
            r = b.classify(cik, name, date)
            if r is not None:
                d = json.load(open(f"data/cache/subs/{cik}.json"))["filings"]["recent"]
                if any(f == "424B1" and fd < date for f, fd in zip(d["form"], d["filingDate"])):
                    r = None
            if r is not None:
                fl = set(r["flags"].split()) - {"SPAC"}
                if r["sic"] == "6770" or SP.search(name):
                    fl.add("SPAC")
                r["flags"] = " ".join(sorted(fl))
                qid, title = wd.get(cik.lstrip("0"), ("", ""))
                r.update(wikidata_qid=qid, wiki_title=title, match_method="wikidata_cik" if title else "",
                         name_at_424b4=name, form_type="424B1")
            json.dump(r, open(ck, "w"))
        if r:
            rows.append(r); existing.add(cik); added += 1
    fields = list(dict.fromkeys(k for r in rows for k in r))
    w = csv.DictWriter(open(p, "w", newline="", encoding="utf-8"), fieldnames=fields)
    w.writeheader(); w.writerows(rows)
    print(y, "424B1 candidates", len(cands), "added", added, flush=True)
