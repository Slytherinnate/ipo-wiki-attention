"""
deep_search_miss.py: deeper automated search for the SEARCH_MISS rows in
titles_v2_all.csv (Caleb approved, Oct 20 2026). Nothing is deleted.

Four IDs are checked for each candidate article:
  CIK      candidate's Wikidata item has P5531 = this CIK
  TICKER   candidate's Wikidata item lists P249 = an EDGAR ticker, OR the
           wikitext has the ticker next to NYSE/Nasdaq (e.g. {{Nasdaq|XXXX}})
  NAME     article title (or one of its redirects) equals the normalized
           legal name / a former EDGAR name / a stripped variant
  EXCHANGE wikitext mentions the company's EDGAR exchange (NYSE / Nasdaq)
Candidate sources (methods), all logged:
  M1 Wikidata haswbstatement:P5531=<10-digit CIK> (live, not the cached map)
  M2 cached Wikidata ticker map (P414/P249), no name filter
  M3 Wikipedia search on each name variant (current + EDGAR formerNames,
     stripped of Inc/Corp/Holdings/Therapeutics/... ), top 5, redirects resolved
  M4 exact-title lookup of each name variant (catches redirect titles)
Classes:
  FOUND_STRONG          >=2 IDs incl. CIK or TICKER (not disambig, not list page)
                        -> AUTO_KEEP, views pulled (-120..+60, redirects summed, 0-fill)
  FOUND_CANDIDATE       some ID evidence but not strong -> REVIEW (code SEARCH_CANDIDATE)
  NO_ARTICLE_CONFIRMED  every method ran cleanly, no candidate has any ID
                        -> DROP_NO_ARTICLE_CONFIRMED (row kept in titles file)
  UNCERTAIN             a method failed (API error) -> stays REVIEW SEARCH_MISS
Rate limit: shared 3 req/s limiter (180/min) from match_all; descriptive UA.
Checkpoint: data/universe/checkpoints/deep_<CIK>_<year>.json
"""
import csv, datetime as dt, json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
import match_all as ma          # sets up limiter, v2 helpers, views cache
v2 = ma.v2
WD = "https://www.wikidata.org/w/api.php"
CK = "data/universe/checkpoints"
# v2 (Oct 20): strip only legal-form words. v1 also stripped descriptive words
# (Global, Therapeutics, ...), so "Venture Global" matched the page "Venture".
SUFFIX = r"\b(inc|incorporated|corp|corporation|co|company|holdings?|ltd|limited|plc|llc|lp|l\.p|sa|s\.a|nv|n\.v|ag|se|bv|b\.v|/de/|/md/|/nv/|/ca/|the)\b"
LOOSE = r"\b(therapeutics|pharmaceuticals?|biosciences?|biotherapeutics|technologies|technology|international|global|group)\b"


def norm(x):
    x = re.sub(r"\(.*?\)", " ", x.lower())
    x = re.sub(SUFFIX, " ", x)
    return re.sub(r"[^a-z0-9]+", " ", x).strip()


def variants(cik, legal):
    d = json.load(open(f"data/cache/subs/{cik}.json"))
    names = [legal] + [f.get("name", "") for f in d.get("formerNames", [])]
    out = []
    for n in names:
        loose = re.sub(r"\s+", " ", re.sub(LOOSE, " ", norm(n))).strip()
        for v in (n, re.sub(r"[,.]", " ", n), norm(n).title(), loose.title() if len(loose) >= 5 else ""):
            v = re.sub(r"\s+", " ", v).strip()
            if v and v not in out and len(norm(v)) >= 3:
                out.append(v)
    return out, {norm(n) for n in names if norm(n)}


def run(r):
    ev = {"methods": {}, "candidates": {}}
    cik10 = f"{int(r['cik']):010d}"
    tickers = [t.upper() for t in r["tickers"].split() if t]
    cands = {}                                     # title -> set(method)
    ok = True
    # M1 live Wikidata CIK
    d = v2.get(WD, {"action": "query", "list": "search", "srsearch": f"haswbstatement:P5531={cik10}",
                    "format": "json", "formatversion": 2})
    qids = [h["title"] for h in d["query"]["search"]] if d and "query" in d else None
    if qids is None:
        ok = False
    ev["methods"]["M1_wikidata_cik"] = qids
    if qids:
        e = v2.get(WD, {"action": "wbgetentities", "ids": "|".join(qids[:5]), "props": "sitelinks",
                        "sitefilter": "enwiki", "format": "json"})
        for q, ent in (e or {}).get("entities", {}).items():
            t = ent.get("sitelinks", {}).get("enwiki", {}).get("title")
            if t:
                cands.setdefault(t, set()).add("M1")
    # M2 ticker map
    m2 = []
    for tk in tickers:
        for c in ma.TICK.get(tk, []):
            cands.setdefault(c["title"], set()).add("M2"); m2.append(c["title"])
    ev["methods"]["M2_wikidata_ticker"] = m2
    # M3 search + M4 exact titles
    vs, namekeys = variants(r["cik"], r["legal_name"])
    m3, m4 = [], []
    for v in vs[:6]:
        d = v2.get(v2.API, {"action": "query", "list": "search", "srsearch": v, "srlimit": 5,
                            "format": "json", "formatversion": 2})
        if d is None or "query" not in d:
            if d is None or "error" not in d:
                ok = False
            continue        # an API "error" for an odd search string is logged, not fatal
        for h in d["query"]["search"]:
            cands.setdefault(h["title"], set()).add("M3"); m3.append(h["title"])
    d = v2.get(v2.API, {"action": "query", "titles": "|".join(vs[:40]), "redirects": 1,
                        "format": "json", "formatversion": 2})
    for p in (d or {}).get("query", {}).get("pages", []):
        if not p.get("missing"):
            cands.setdefault(p["title"], set()).add("M4"); m4.append(p["title"])
    # M5 Wikidata entity search by name -> enwiki sitelink
    m5 = []
    for v in vs[:3]:
        d = v2.get(WD, {"action": "wbsearchentities", "search": v, "language": "en", "limit": 5, "format": "json"})
        ids = [x["id"] for x in (d or {}).get("search", [])]
        if ids:
            e = v2.get(WD, {"action": "wbgetentities", "ids": "|".join(ids), "props": "sitelinks",
                            "sitefilter": "enwiki", "format": "json"})
            for q, ent in (e or {}).get("entities", {}).items():
                tt = ent.get("sitelinks", {}).get("enwiki", {}).get("title")
                if tt:
                    cands.setdefault(tt, set()).add("M5"); m5.append(tt)
    ev["methods"]["M3_search"] = sorted(set(m3)); ev["methods"]["M4_exact_title"] = m4
    ev["methods"]["M5_wikidata_name"] = m5
    ev["name_variants"] = vs
    # Evidence per candidate (batched, 20 titles per call)
    titles = [t for t in cands if not t.startswith(("List of", "Companies listed"))]
    info = {}
    for i in range(0, len(titles), 20):
        d = v2.get(v2.API, {"action": "query", "titles": "|".join(titles[i:i + 20]), "redirects": 1,
                            "prop": "revisions|pageprops|redirects", "rvprop": "content", "rvslots": "main",
                            "ppprop": "disambiguation|wikibase_item", "rdlimit": "max", "rdnamespace": 0,
                            "format": "json", "formatversion": 2})
        if d is None or "query" not in d:
            ok = False; continue
        rmap = {x["from"]: x["to"] for x in d["query"].get("redirects", [])}
        for p in d["query"]["pages"]:
            if p.get("missing") or not p.get("revisions"):
                continue
            info[p["title"]] = {"text": p["revisions"][0]["slots"]["main"].get("content", "")[:60000],
                                "qid": p.get("pageprops", {}).get("wikibase_item", ""),
                                "disambig": "disambiguation" in p.get("pageprops", {}),
                                "redirects": [x["title"] for x in p.get("redirects", [])]}
        for src, dst in rmap.items():
            if src in cands and dst in info:
                cands.setdefault(dst, set()).update(cands[src])
    qids = [v["qid"] for v in info.values() if v["qid"]]
    claims = {}
    for i in range(0, len(qids), 50):
        e = v2.get(WD, {"action": "wbgetentities", "ids": "|".join(qids[i:i + 50]), "props": "claims",
                        "format": "json"})
        if e is None:
            ok = False; continue
        for q, ent in e.get("entities", {}).items():
            cl = ent.get("claims", {})
            val = lambda pid: {str(c["mainsnak"].get("datavalue", {}).get("value", "")) for c in cl.get(pid, [])}
            tk = set()
            for c in cl.get("P414", []):
                for qq in c.get("qualifiers", {}).get("P249", []):
                    tk.add(str(qq.get("datavalue", {}).get("value", "")).upper())
            tk |= {x.upper() for x in val("P249")}
            claims[q] = {"cik": {x.lstrip("0") for x in val("P5531")}, "tickers": tk}
    exch = r["exchanges"].upper()
    for t, v in info.items():
        c = claims.get(v["qid"], {"cik": set(), "tickers": set()})
        txt = v["text"]
        ids = set()
        if r["cik"].lstrip("0") in c["cik"]:
            ids.add("CIK")
        if any(tk in c["tickers"] for tk in tickers) or any(
                re.search(r"(NYSE|Nasdaq|NASDAQ|nyse|nasdaq)[^\n]{0,40}\b" + re.escape(tk) + r"\b", txt) for tk in tickers):
            ids.add("TICKER")
        if namekeys & ({norm(t)} | {norm(x) for x in v["redirects"]}):
            ids.add("NAME")
        if ("NYSE" in exch and re.search(r"\bNYSE\b|New York Stock Exchange", txt)) or (
                "NASDAQ" in exch and re.search(r"(?i)\bnasdaq\b", txt)):
            ids.add("EXCHANGE")
        ev["candidates"][t] = {"methods": sorted(cands.get(t, [])), "ids": sorted(ids), "qid": v["qid"],
                               "disambig": v["disambig"]}
    ev["all_methods_ok"] = ok
    ev["class"], ev["best_title"] = classify(ev)
    return ev


def is_strong(c):
    """Strong = CIK match, or TICKER + NAME. Decision log (Oct 20): ticker +
    exchange alone is NOT strong, because tickers are recycled (first run gave
    Enact -> Actavis via ACT, Paymentus -> Verifone via PAY)."""
    ids = set(c["ids"])
    return not c["disambig"] and ("CIK" in ids or {"TICKER", "NAME"} <= ids)


def classify(ev):
    cs = ev.get("candidates", {})
    rank = lambda t: (is_strong(cs[t]), "CIK" in cs[t]["ids"], len(set(cs[t]["ids"]) - {"EXCHANGE"}), len(cs[t]["ids"]))
    withid = [t for t in cs if set(cs[t]["ids"]) - {"EXCHANGE"}]
    if withid:
        best = max(withid, key=rank)
        return ("FOUND_STRONG" if is_strong(cs[best]) else "FOUND_CANDIDATE"), best
    if not ev.get("all_methods_ok", False):
        return "UNCERTAIN", ""
    return "NO_ARTICLE_CONFIRMED", ""


def main():
    t = list(csv.DictReader(open("data/universe/titles_v2_all.csv", encoding="utf-8")))
    rows = [r for r in t if "SEARCH_MISS" in r["reasons"].split()]
    from concurrent.futures import ThreadPoolExecutor
    def one(item):
        n, r = item
        ck = os.path.join(CK, f"deep_{r['cik']}_{r['year']}.json")
        if os.path.exists(ck):
            return
        try:
            ev = run(r)
        except Exception as e:
            ev = {"class": "UNCERTAIN", "error": repr(e)[:300], "best_title": ""}
        json.dump(ev, open(ck, "w"))
        print(f"[{n}/{len(rows)}] {r['year']} {r['legal_name']} -> {ev['class']} {ev['best_title']}", flush=True)
    with ThreadPoolExecutor(4) as ex:
        list(ex.map(one, enumerate(rows, 1)))
    print("done", len(rows))


if __name__ == "__main__":
    main()
