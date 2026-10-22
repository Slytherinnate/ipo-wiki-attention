"""
parse_424b4.py: finalize the IPO universe and extract deal details from each
company's 424B4 cover (SEC EDGAR only).

For every first-time offering in data/universe/ipo_universe_YYYY.csv it adds:
  accession, filing_url, legal_name, tickers, exchanges, sic, sic_description,
  sector, state_of_inc (+ description), business_country, foreign_flag,
  offer_price, shares_offered_base, gross_proceeds (= price x base shares),
  underwriters_on_cover, prospectus_date, first_trade_date, first_trade_conf,
  deal_flags.
SPACs and funds are kept in the file but not parsed (status=EXCLUDED).

Data sources: EDGAR quarterly form index (cached), submissions JSON (cached),
the first ~600 KB of the 424B4 (cached in data/cache/424b4/).
SEC fair access: <=10 req/s; we sleep 0.15 s between new downloads (~7/s).

First trade date (no price sites):
  stated  = the 424B4 says shares are "expected to begin trading on <date>"
  derived = next NYSE trading day after the prospectus date ("The date of this
            prospectus is ..."). US IPOs usually price after the close and trade
            the next day, but this is an assumption -> confidence "derived".
  unknown = no prospectus date found.

Checkpoint: data/universe/checkpoints/deal_<CIK>.json per company, so a re-run
skips finished rows. Output: data/universe/ipo_deals_all.csv
Run: python scripts/parse_424b4.py 2019 2020 ... 2025
"""
import csv
import datetime as dt
import html
import json
import os
import re
import sys
import time

import holidays
import requests

UA = {"User-Agent": "Caleb Havens calebhavens08@gmail.com"}
CK = "data/universe/checkpoints"
NYSE = holidays.NYSE(years=range(2018, 2027))

PRICE_RE = re.compile(r"(?:initial )?public offering price[^$]{0,250}?\$\s*([\d,]+\.\d{2})", re.I)
UNIT_RE = re.compile(r"\bper unit\b|\bunits?, each consisting\b", re.I)
WARRANT_RE = re.compile(r"\bwarrants?\b", re.I)
RANGE_RE = re.compile(r"between \$\s*([\d.]+) and \$\s*([\d.]+)", re.I)
SHARES_RE = re.compile(r"([\d]{1,3}(?:,\d{3})+)\s+(?:shares|American Depositary Shares|ADSs|ordinary shares|units)", re.I)
PDATE_RE = re.compile(r"(?:date of this prospectus is|prospectus dated)\s+([A-Z][a-z]+\.? \d{1,2}, ?\d{4})", re.I)
DELIVER_RE = re.compile(r"expect(?:s)? to deliver[^.]{0,250}?on(?: or about)?,?\s+([A-Z][a-z]+\.? \d{1,2}, ?\d{4})", re.I)
TRADE_RE = re.compile(r"expect(?:ed)?\s+to\s+(?:begin|commence)\s+trading[^.]{0,160}?on\s+([A-Z][a-z]+ \d{1,2}, \d{4})", re.I)
# Underwriters: names as they commonly appear on 424B4 covers. Order = first appearance.
BANKS = ["Goldman Sachs", "Morgan Stanley", "J.P. Morgan", "BofA Securities", "Citigroup", "Barclays", "Jefferies",
         "Credit Suisse", "Deutsche Bank", "Wells Fargo", "UBS", "RBC Capital Markets", "Evercore", "Piper Sandler",
         "TD Cowen", "Cowen", "SVB Leerink", "Leerink", "Stifel", "William Blair", "Raymond James", "Cantor",
         "Needham", "KeyBanc", "Mizuho", "Guggenheim", "BMO Capital", "Truist", "Baird", "Oppenheimer", "Roth",
         "ThinkEquity", "EF Hutton", "Maxim Group", "Aegis", "Benchmark", "Boustead", "Univest", "D. Boral",
         "Spartan Capital", "Prime Number", "Network 1", "US Tiger", "Joseph Gunnar", "Kingswood", "WestPark",
         "Craig-Hallum", "Ladenburg", "H.C. Wainwright", "Alexander Capital", "Dawson James", "Revere",
         "Allen & Company", "Macquarie", "Nomura", "HSBC", "CICC", "China International Capital", "Tiger Brokers",
         "Futu", "Loop Capital", "Academy Securities", "Siebert", "Ramirez", "Samuel A. Ramirez", "Wedbush",
         "JMP Securities", "Lake Street", "Northland", "B. Riley", "Chardan", "Brookline", "EarlyBird", "Benchmark",
         "Lucid Capital", "Wolfe", "Moelis", "LionTree", "Ziegler", "Janney", "Imperial Capital", "R. F. Lafferty",
         "Bancroft", "AGP", "A.G.P.", "Kingswood", "Craft Capital", "Valuable Capital", "Bancroft Capital", "Merrill Lynch", "Piper Jaffray", "SunTrust", "Credit Agricole", "Santander", "Societe Generale", "BNP Paribas", "Citizens", "Capital One", "Drexel Hamilton", "CastleOak", "Blaylock", "Tigress", "AmeriVet", "Telsey", "Huatai", "Haitong", "CMB International", "Needham & Company"]


def get(url, cache, byte_range=None):
    if os.path.exists(cache):
        return open(cache, encoding="utf-8", errors="replace").read()
    h = dict(UA)
    if byte_range:
        h["Range"] = byte_range
    for attempt in range(4):
        time.sleep(0.15)
        try:
            r = requests.get(url, headers=h, timeout=60)
        except requests.RequestException:
            time.sleep(5 * (attempt + 1))
            continue
        if r.status_code in (429, 503):
            time.sleep(10 * (attempt + 1))
            continue
        r.raise_for_status()
        text = r.content.decode("latin-1")
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        open(cache, "w", encoding="utf-8").write(text)
        return text
    raise RuntimeError("failed " + url)


def first_424b4_paths(year):
    paths = {}
    for q in range(1, 5):
        for line in open(f"data/cache/index/{year}Q{q}.idx", errors="replace"):
            if line.startswith(("424B4 ", "424B1 ")):
                p = line.split()
                cik, date, path = (p[0], p[-3]), p[-2], p[-1]
                if cik not in paths or date < paths[cik][0]:
                    paths[cik] = (date, path)
    return paths


def next_trading_day(d):
    d += dt.timedelta(days=1)
    while d.weekday() >= 5 or d in NYSE:
        d += dt.timedelta(days=1)
    return d


def parse_date(s):
    s = s.replace(".", "").replace(",", ", ").replace(",  ", ", ")
    for fmt in ("%B %d, %Y", "%b %d, %Y"):
        try:
            return dt.datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def cover_fields(path):
    raw = get("https://www.sec.gov/Archives/" + path, os.path.join("data/cache/424b4", path.replace("/", "_")),
              "bytes=0-600000")
    t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw)))
    head = t[:30000]
    out, flags = {}, []
    m = PRICE_RE.search(t)
    out["offer_price"] = m.group(1).replace(",", "") if m else ""
    if not m:
        flags.append("NO_PRICE_FOUND")
    if UNIT_RE.search(head):
        flags.append("UNITS")
    if WARRANT_RE.search(head[:8000]):
        flags.append("WARRANTS_ON_COVER")
    if RANGE_RE.search(head[:15000]):
        flags.append("PRICE_RANGE_ON_COVER")
    s = SHARES_RE.search(head[:12000])
    out["shares_offered_base"] = s.group(1).replace(",", "") if s else ""
    if not s:
        flags.append("NO_SHARES_FOUND")
    try:
        out["gross_proceeds"] = f"{float(out['offer_price']) * int(out['shares_offered_base']):.0f}"
    except ValueError:
        out["gross_proceeds"] = ""
    # The bookrunner block sits between "expect to deliver ... <date>." and
    # "Prospectus dated ...". Use it when found, else the first 10k chars.
    dv = DELIVER_RE.search(head)
    pdm = PDATE_RE.search(head)
    block = head[dv.end():pdm.start()] if dv and pdm and pdm.start() > dv.end() else head[:10000]
    if not (dv and pdm and pdm.start() > dv.end()):
        flags.append("UW_BLOCK_GUESSED")
    found = []
    for b in BANKS:
        m2 = re.search(r"(?<![A-Za-z])" + re.escape(b) + r"(?![A-Za-z])", block, re.I)
        if m2 and not any(b in x and b != x for x in BANKS if re.search(re.escape(x), block, re.I)):
            found.append((m2.start(), b))
    cd = parse_date(dv.group(1)) if dv else None
    out["closing_date"] = cd.isoformat() if cd else ""
    out["underwriters_on_cover"] = "; ".join(b for _, b in sorted(set(found)))
    pd_ = PDATE_RE.search(t)
    pdate = parse_date(pd_.group(1)) if pd_ else None
    out["prospectus_date"] = pdate.isoformat() if pdate else ""
    tr = TRADE_RE.search(t)
    tdate = parse_date(tr.group(1)) if tr else None
    if tdate:
        out["first_trade_date"], out["first_trade_conf"] = tdate.isoformat(), "stated"
    elif pdate:
        out["first_trade_date"], out["first_trade_conf"] = next_trading_day(pdate).isoformat(), "derived"
    elif cd:
        # No prospectus date (often an image). Closing is normally T+2 trading
        # days (T+1 from 2024-05-28), so step back that many trading days.
        d, n = cd, (1 if cd >= dt.date(2024, 5, 28) else 2)
        while n:
            d -= dt.timedelta(days=1)
            if d.weekday() < 5 and d not in NYSE:
                n -= 1
        out["first_trade_date"], out["first_trade_conf"] = d.isoformat(), "derived_closing"
    else:
        out["first_trade_date"], out["first_trade_conf"] = "", "unknown"
    # Exclusion checks from the cover text (logged as flags):
    if re.search(r"blank[- ]check company", head[:20000], re.I):
        flags.append("SPAC_TEXT")
    if re.search(r"direct listing|registered stockholders|no underwriters|not an underwritten", head[:20000], re.I):
        flags.append("DIRECT_LISTING")
    if not s and re.search(r"\bnotes\b|\bbonds\b|certificates", head[:5000], re.I):
        flags.append("NOT_EQUITY")
    out["deal_flags"] = " ".join(flags)
    return out


def main(years):
    os.makedirs(CK, exist_ok=True)
    rows = []
    for y in years:
        paths = first_424b4_paths(y)
        for r in csv.DictReader(open(f"data/universe/ipo_universe_{y}.csv", encoding="utf-8")):
            ck = os.path.join(CK, f"deal_{r['cik']}_{y}.json")
            if os.path.exists(ck):
                rows.append(json.load(open(ck)))
                continue
            form = r.get("form_type") or "424B4"
            date, path = paths[(form, r["cik"])]
            acc = path.rsplit("/", 1)[-1].replace(".txt", "")
            sub = json.load(open(f"data/cache/subs/{r['cik']}.json"))
            biz = sub.get("addresses", {}).get("business", {}) or {}
            rec = {"year": y, "cik": r["cik"], "legal_name": sub.get("name", r["name"]),
                   "filing_date_424b4": date, "form_type": form, "accession": acc,
                   "filing_url": f"https://www.sec.gov/Archives/edgar/data/{int(r['cik'])}/{acc.replace('-', '')}/",
                   "tickers": " ".join(sub.get("tickers", [])),
                   "exchanges": " ".join(x or "" for x in sub.get("exchanges", [])),
                   "sic": r["sic"], "sic_description": r["sic_description"], "sector": r["sector"],
                   "state_of_inc": sub.get("stateOfIncorporation", ""),
                   "state_of_inc_desc": sub.get("stateOfIncorporationDescription", ""),
                   "business_country": biz.get("country") or biz.get("stateOrCountryDescription") or "",
                   "foreign_flag": "yes" if "FOREIGN_ADR" in r["flags"] else "",
                   "universe_flags": r["flags"], "wikidata_qid": r["wikidata_qid"], "wiki_title_wd": r["wiki_title"]}
            if "SPAC" in r["flags"] or "FUND_OR_TRUST" in r["flags"]:
                rec["status"] = "EXCLUDED"
            else:
                rec["status"] = "OPERATING"
                try:
                    rec.update(cover_fields(path))
                except Exception as e:      # keep going; log the failure in the row
                    rec["deal_flags"] = f"FETCH_ERROR {type(e).__name__}"
            if rec["status"] == "OPERATING" and {"SPAC_TEXT", "NOT_EQUITY"} & set(rec.get("deal_flags", "").split()):
                rec["status"] = "EXCLUDED"
            json.dump(rec, open(ck, "w"))
            rows.append(rec)
        print(y, "done", flush=True)
    fields = sorted({k for r in rows for k in r}, key=lambda k: list(rows[-1]).index(k) if k in rows[-1] else 99)
    with open("data/universe/ipo_deals_all.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print("wrote", len(rows))


if __name__ == "__main__":
    main(sys.argv[1:] or [str(y) for y in range(2019, 2026)])
