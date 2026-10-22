"""
build_ipo_universe.py: build a list of US IPOs from SEC EDGAR, then match
each company to its English Wikipedia article through Wikidata.

How it works (all free, public SEC and Wikimedia data):
  1. EDGAR quarterly form index (www.sec.gov/Archives/edgar/full-index/YYYY/QTRn/form.idx)
     lists every filing. We keep form 424B4, the final prospectus filed when
     an offering is priced.
  2. 424B4 is also used for follow-on offerings, so for each company we read
     its submissions JSON (data.sec.gov/submissions/CIK##########.json) and
     keep it only if it was NOT already a reporting company (no 10-K/10-Q/20-F
     filed before) and it filed an S-1/F-1/S-11 registration. That is our IPO test.
  3. Flags: SPAC (SIC 6770 or "Acquisition" in name, excluded), FOREIGN
     (F-1 or 20-F filer, likely ADR, kept but flagged), FUND (SIC 6726, excluded).
  4. Sector = broad group from the company's SIC code (see SECTOR_RANGES).
  5. Wikidata: one SPARQL query fetches every item that has an SEC Central
     Index Key (property P5531) and an English Wikipedia article.

SEC fair access: max 10 requests/second, declared User-Agent with contact.
https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data

Run:  python scripts/build_ipo_universe.py 2024 [2025 ...]
Out:  data/universe/ipo_universe_YYYY.csv  (+ cached raw files in data/cache/)
"""
import csv
import json
import os
import sys
import time

import requests

SEC_UA = {"User-Agent": "Caleb Havens calebhavens08@gmail.com", "Accept-Encoding": "gzip, deflate"}
WIKI_UA = {"User-Agent": "CalebHavens-DSPortfolio/0.2 (wiki-attention IPO study; calebhavens08@gmail.com)"}
CACHE = "data/cache"
OUT = "data/universe"
SEC_PAUSE = 0.15          # ~7 requests/second, under SEC's 10/s limit

# Broad sectors from SIC code ranges. SIC titles come from the SEC list
# (https://www.sec.gov/search-filings/standard-industrial-classification-sic-code-list);
# the grouping into GICS-style sector names is OUR approximation, not an
# official crosswalk. First matching range wins, so specific ranges go first.
SECTOR_RANGES = [
    ((2830, 2836), "Health Care"), ((3841, 3851), "Health Care"), ((5047, 5047), "Health Care"),
    ((5122, 5122), "Health Care"), ((8000, 8099), "Health Care"), ((8731, 8734), "Health Care"),
    ((3570, 3579), "Information Technology"), ((3600, 3699), "Information Technology"),
    ((3820, 3829), "Information Technology"), ((7370, 7379), "Information Technology"),
    ((4800, 4899), "Communication Services"), ((2710, 2799), "Communication Services"),
    ((7810, 7819), "Communication Services"),
    ((1300, 1399), "Energy"), ((2900, 2999), "Energy"), ((4610, 4619), "Energy"), ((4920, 4925), "Energy"),
    ((4900, 4999), "Utilities"),
    ((6798, 6798), "Real Estate"), ((6500, 6599), "Real Estate"),
    ((6000, 6799), "Financials"),
    ((1000, 1499), "Materials"), ((2600, 2699), "Materials"), ((2800, 2829), "Materials"),
    ((2840, 2899), "Consumer Staples"), ((3300, 3399), "Materials"),
    ((2000, 2199), "Consumer Staples"), ((5400, 5499), "Consumer Staples"), ((5140, 5149), "Consumer Staples"),
    ((3710, 3716), "Consumer Discretionary"), ((5000, 5999), "Consumer Discretionary"),
    ((7000, 7099), "Consumer Discretionary"), ((7900, 7999), "Consumer Discretionary"),
    ((8200, 8299), "Consumer Discretionary"), ((2200, 2399), "Consumer Discretionary"),
    ((3000, 3999), "Industrials"), ((1500, 1799), "Industrials"), ((4000, 4799), "Industrials"),
    ((7300, 7399), "Industrials"), ((8700, 8799), "Industrials"),
]


def sic_to_sector(sic):
    try:
        s = int(sic)
    except (TypeError, ValueError):
        return "Unknown"
    for (lo, hi), name in SECTOR_RANGES:
        if lo <= s <= hi:
            return name
    return "Other"


def sec_get(url, cache_name):
    """GET from SEC with caching, so re-runs don't hit SEC again."""
    path = os.path.join(CACHE, cache_name)
    if os.path.exists(path):
        return open(path, encoding="utf-8", errors="replace").read()
    time.sleep(SEC_PAUSE)
    r = requests.get(url, headers=SEC_UA, timeout=60)
    if r.status_code == 404:
        return ""
    r.raise_for_status()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write(r.text)
    return r.text


def first_424b4s(year):
    """{cik: (company name, first 424B4 date in that year)} from the 4 quarterly indexes."""
    found = {}
    for q in range(1, 5):
        text = sec_get(f"https://www.sec.gov/Archives/edgar/full-index/{year}/QTR{q}/form.idx",
                       f"index/{year}Q{q}.idx")
        for line in text.splitlines():
            if not line.startswith("424B4 "):
                continue
            # Fixed-width-ish: form, name..., CIK, date, file. Split from the right.
            parts = line.split()
            cik, date = parts[-3], parts[-2]
            name = " ".join(parts[1:-3])
            if cik not in found or date < found[cik][1]:
                found[cik] = (name, date)
    return found


def classify(cik, name, date):
    """Read the submissions JSON and decide: IPO or not, plus flags."""
    txt = sec_get(f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json", f"subs/{cik}.json")
    if not txt:
        return None
    d = json.loads(txt)
    rec = d["filings"]["recent"]
    forms = list(zip(rec["form"], rec["filingDate"]))
    before = [f for f, dt in forms if dt < date]
    flags = []
    # Already public? Periodic reports before the 424B4 mean this is a follow-on.
    if any(f in ("10-K", "10-Q", "20-F", "40-F", "10-K405") for f in before):
        return None
    if any(f == "424B4" for f, dt in forms if dt < date):
        return None
    reg = {f for f, dt in forms if f in ("S-1", "F-1", "S-11", "S-1/A", "F-1/A", "S-11/A")}
    if not reg:
        flags.append("NO_REG_IN_RECENT")   # older history may be truncated; review
    sic = d.get("sic", "")
    low = name.lower()
    if sic == "6770" or "acquisition" in low or "spac" in low:
        flags.append("SPAC")
    if sic == "6726" or "fund" in low or " trust" in low:
        flags.append("FUND_OR_TRUST")
    if {"F-1", "F-1/A", "20-F"} & {f for f, _ in forms}:
        flags.append("FOREIGN_ADR")
    return {
        "cik": cik, "name": d.get("name", name), "filing_date_424b4": date,
        "tickers": " ".join(d.get("tickers", [])), "exchanges": " ".join(x or "" for x in d.get("exchanges", [])),
        "sic": sic, "sic_description": d.get("sicDescription", ""), "sector": sic_to_sector(sic),
        "state_of_inc": d.get("stateOfIncorporation", ""), "flags": " ".join(flags),
    }


def wikidata_cik_map():
    """{cik (no leading zeros): (wikidata QID, enwiki title)} via one SPARQL query."""
    path = os.path.join(CACHE, "wikidata_cik.json")
    if not os.path.exists(path):
        q = """SELECT ?item ?cik ?title WHERE {
                 ?item wdt:P5531 ?cik .
                 ?article schema:about ?item ; schema:isPartOf <https://en.wikipedia.org/> ; schema:name ?title .
               }"""
        r = requests.get("https://query.wikidata.org/sparql", params={"query": q, "format": "json"},
                         headers=WIKI_UA, timeout=300)
        r.raise_for_status()
        os.makedirs(CACHE, exist_ok=True)
        open(path, "w").write(r.text)
    out = {}
    for b in json.load(open(path))["results"]["bindings"]:
        cik = b["cik"]["value"].lstrip("0")
        out[cik] = (b["item"]["value"].rsplit("/", 1)[-1], b["title"]["value"])
    return out


def main(years):
    os.makedirs(OUT, exist_ok=True)
    wd = wikidata_cik_map()
    print(f"Wikidata items with CIK + enwiki article: {len(wd)}")
    for year in years:
        cands = first_424b4s(year)
        print(f"{year}: {len(cands)} companies filed a 424B4")
        rows = []
        for i, (cik, (name, date)) in enumerate(sorted(cands.items()), 1):
            r = classify(cik, name, date)
            if r is None:
                continue
            qid, title = wd.get(cik.lstrip("0"), ("", ""))
            r.update(wikidata_qid=qid, wiki_title=title, match_method="wikidata_cik" if title else "")
            rows.append(r)
            if i % 50 == 0:
                print(f"  checked {i}/{len(cands)}")
        path = os.path.join(OUT, f"ipo_universe_{year}.csv")
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"{year}: {len(rows)} first-time offerings written to {path}")


if __name__ == "__main__":
    main(sys.argv[1:] or ["2024"])
