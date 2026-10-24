"""SEC-only first-trade dates and IPO checks (Oct 24 2026; replaces apply_tiingo_fixes.py).

Why: Tiingo's terms (docs/licenses/tiingo-reply-2026-10-20.md, rule 1c) treat using Tiingo data
to validate another dataset as a substitute. apply_tiingo_fixes.py had moved 45 EDGAR-derived
first-trade dates to Tiingo's first price bar and marked 13 firms "already listed" from Tiingo's
ticker metadata. This script undoes both and uses SEC EDGAR evidence only.

Inputs (all cached SEC data, no new requests): data/universe/backup_pre_reanchor_1901/
(the universe files as they were before any Tiingo-based change), data/cache/424b4/ (424B4 text),
data/cache/subs/<CIK>.json (EDGAR submissions).

1. Dates: first_trade_date / first_trade_conf come from parse_424b4.py's SEC rules only
   (stated > next trading day after the prospectus date > closing date minus settlement cycle).
   The 424B4 text is searched again for explicit trading-date wording ("expected to begin /
   commence trading on <date>"); a hit sets first_trade_conf=stated. Otherwise the date is kept.
   sec_date_flag (universe-wide, never from Tiingo):
     SEC_CLOSING_SAME_DAY  closing date minus the settlement cycle equals the prospectus date,
                           i.e. the cover hints the stock traded on the pricing date. Date NOT
                           moved: SEC data cannot settle it (decision for Caleb).
     SEC_CLOSING_OTHER     closing-implied date differs from both. Date not moved.
2. Already-listed check (replaces Tiingo meta startDate): attention_only=1,
   attention_reason=pre_listed_sec if EDGAR shows a 10-K, 10-Q, 20-F or 40-F filed before the
   424B4, or the 424B4 says the shares are currently listed / quoted / traded on a market.
   Direct listings keep attention_reason=direct_listing.
Outputs: data/universe/titles_v2_all.csv, ipo_deals_all.csv, review_all.csv (local only).
"""
import datetime as dt, html, json, os, re, sys
import pandas as pd, holidays
sys.path.insert(0, os.path.dirname(__file__))
H = holidays.NYSE(years=range(2018, 2027))
BK = "data/universe/backup_pre_reanchor_1901"
FILES = {f.split("_")[-1].rsplit(".", 1)[0]: f for f in os.listdir("data/cache/424b4")}
TRADE = re.compile(r"(?:expected to|will|anticipate[sd]? (?:that )?(?:our [^.]{0,40})?(?:will )?)\s*(?:begin|commence) trading[^.]{0,80}?on\s+([A-Z][a-z]+ \d{1,2}, \d{4})")
LISTED = re.compile(r"(?:common stock|ordinary shares|shares|ADSs)[^.]{0,60}\b(?:is|are) (?:currently|presently) (?:listed|quoted|traded)\b", re.I)
PERIODIC = {"10-K", "10-Q", "20-F", "40-F"}


def back(d, n):
    while n:
        d -= dt.timedelta(days=1)
        if d.weekday() < 5 and d not in H:
            n -= 1
    return d


def text(acc):
    f = FILES.get(acc)
    if not f:
        return ""
    raw = open(os.path.join("data/cache/424b4", f), errors="replace").read()[:600000]
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw)))


def prior_periodic(cik, before):
    p = f"data/cache/subs/{cik}.json"
    if not os.path.exists(p) or not before:
        return False
    r = json.load(open(p)).get("filings", {}).get("recent", {})
    return any(f in PERIODIC and d < before for f, d in zip(r.get("form", []), r.get("filingDate", [])))


def check(r):
    out = {"sec_date_flag": "", "sec_prior_listing": ""}
    t = text(r["accession"]) if r.get("accession") else ""
    m = TRADE.search(t[:300000])
    if m:
        try:
            out["first_trade_date"] = dt.datetime.strptime(m.group(1), "%B %d, %Y").date().isoformat()
            out["first_trade_conf"] = "stated"
        except ValueError:
            pass
    if r["first_trade_conf"] == "derived" and r["closing_date"] and r["prospectus_date"] and "first_trade_conf" not in out:
        c = dt.date.fromisoformat(r["closing_date"])
        imp = back(c, 1 if c >= dt.date(2024, 5, 28) else 2).isoformat()
        if imp == r["prospectus_date"]:
            out["sec_date_flag"] = "SEC_CLOSING_SAME_DAY"
        elif imp != r["first_trade_date"]:
            out["sec_date_flag"] = "SEC_CLOSING_OTHER"
    why = []
    if prior_periodic(r["cik"], r["filing_date_424b4"]):
        why.append("prior_periodic_report")
    if LISTED.search(t[:60000]):
        why.append("cover_says_listed")
    out["sec_prior_listing"] = " ".join(why)
    return out


stats = {}
for name in ("ipo_deals_all.csv", "titles_v2_all.csv"):
    d = pd.read_csv(f"{BK}/{name}", dtype=str).fillna("")
    d["attention_reason"] = ""
    d.loc[d.attention_only == "1", "attention_reason"] = "direct_listing"
    d["first_trade_source"] = "SEC 424B4 (parse_424b4.py rules)"
    for c in ("sec_date_flag", "sec_prior_listing"):
        d[c] = ""
    for i, r in d.iterrows():
        if not r.get("accession") or r.get("first_trade_conf", "") == "":
            continue
        o = check(r)
        for k, v in o.items():
            d.at[i, k] = v
        if o["sec_prior_listing"] and d.at[i, "attention_only"] != "1":
            d.at[i, "attention_only"], d.at[i, "attention_reason"] = "1", "pre_listed_sec"
    if name == "titles_v2_all.csv":
        d[d.decision == "REVIEW"].to_csv("data/universe/review_all.csv", index=False)
        stats = {"conf": d.first_trade_conf.value_counts().to_dict(), "flag": d.sec_date_flag.value_counts().to_dict(),
                 "pre_listed_sec": int((d.attention_reason == "pre_listed_sec").sum()),
                 "pre_listed_sec_kept_rows": int(((d.attention_reason == "pre_listed_sec") & d.decision.isin(["AUTO_KEEP", "REVIEW"])).sum())}
    d.to_csv(f"data/universe/{name}", index=False)
print(stats)
