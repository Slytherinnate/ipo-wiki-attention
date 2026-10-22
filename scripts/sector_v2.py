"""
sector_v2.py: SIC -> GICS-style sector, crosswalk v2 (Oct 20 2026). Offline.
Documentation: docs/sector-crosswalk.md. SIC titles: SEC SIC code list
(https://www.sec.gov/search-filings/standard-industrial-classification-sic-code-list).
There is no official SIC->GICS crosswalk; this is our documented approximation.
v1 had a catch-all 3000-3999 -> Industrials and 7300-7399 -> Industrials, which put
consumer products (footwear, sporting goods, toys) and internet marketplaces in Industrials.
Order: company override (data/universe/sector_overrides.csv, SIC 7389/7340 rows that are
kept/review) > specific SIC ranges below (first match wins) > v1 ranges > Other.
Ambiguous SICs without an override get flag SECTOR_AMBIGUOUS_SIC.
Caleb's grouping (Communication Services, Utilities, Unknown -> Other) is applied last.
Columns: sector_original (v1, ungrouped, unchanged), sector_v2_raw, sector (v2 grouped),
sector_rule, sector_flag.
"""
import csv, sys, os
import pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
from build_ipo_universe import SECTOR_RANGES as V1

V2_RULES = [   # (lo, hi, sector, rule id) - checked BEFORE the v1 table
    (2840, 2844, "Consumer Staples", "R01 soaps/cosmetics -> Staples"),
    (2850, 2899, "Materials", "R02 paints/agri/misc chemicals -> Materials (v1 Staples)"),
    (2400, 2499, "Materials", "R03 lumber & wood -> Materials (v1 Other)"),
    (2510, 2519, "Consumer Discretionary", "R04 household furniture -> Cons Disc (v1 Other)"),
    (2520, 2599, "Industrials", "R05 office/store furniture & fixtures -> Industrials (v1 Other)"),
    (3020, 3021, "Consumer Discretionary", "R06 rubber/plastic footwear -> Cons Disc"),
    (3100, 3199, "Consumer Discretionary", "R07 leather & footwear -> Cons Disc"),
    (3200, 3299, "Materials", "R08 glass/stone/clay/concrete -> Materials"),
    (3533, 3533, "Energy", "R09 oil & gas field machinery -> Energy (equipment & services)"),
    (3630, 3639, "Consumer Discretionary", "R10 household appliances -> Cons Disc (v1 IT)"),
    (3651, 3652, "Consumer Discretionary", "R11 household audio/video -> Cons Disc (v1 IT)"),
    (3751, 3751, "Consumer Discretionary", "R12 motorcycles/bicycles -> Cons Disc"),
    (3826, 3826, "Health Care", "R13 laboratory analytical instruments -> Health Care (life-science tools)"),
    (3910, 3915, "Consumer Discretionary", "R14 jewelry -> Cons Disc"),
    (3940, 3949, "Consumer Discretionary", "R15 toys/sporting & athletic goods -> Cons Disc"),
    (4950, 4959, "Industrials", "R16 sanitary/waste services -> Industrials (v1 Utilities)"),
    (1520, 1531, "Consumer Discretionary", "R17 residential builders/operative builders -> Cons Disc (homebuilding)"),
    (5912, 5912, "Consumer Staples", "R18 drug stores -> Staples (v1 Cons Disc)"),
    (7310, 7319, "Communication Services", "R19 advertising -> Communication Services (media)"),
    (100, 299, "Consumer Staples", "R20 crops & livestock -> Staples (v1 Other); 0700 agri services left Other + ambiguous"),
    (7200, 7299, "Consumer Discretionary", "R21 personal services -> Cons Disc (v1 Other)"),
    (7500, 7699, "Consumer Discretionary", "R22 auto repair/misc repair -> Cons Disc (v1 Other)"),
    (8350, 8351, "Consumer Discretionary", "R23 child day care -> Cons Disc (v1 Other)"),
]
AMBIGUOUS = {"7389", "7340", "7380", "8742", "3990", "0700"}
GROUP = {"Communication Services": "Other", "Utilities": "Other", "Unknown": "Other"}
ov = {r["cik"]: r for r in csv.DictReader(open("data/universe/sector_overrides.csv"))}


def classify(cik, sic):
    if cik in ov:
        return ov[cik]["sector"], "OVERRIDE: " + ov[cik]["reason"], ""
    try:
        s = int(sic)
    except ValueError:
        return "Unknown", "no SIC", ""
    for lo, hi, sec, rid in V2_RULES:
        if lo <= s <= hi:
            return sec, rid, ""
    for (lo, hi), sec in V1:
        if lo <= s <= hi:
            return sec, f"v1 range {lo}-{hi}", "SECTOR_AMBIGUOUS_SIC" if sic in AMBIGUOUS else ""
    return "Other", "no range", ""


for p in ("data/universe/ipo_deals_all.csv", "data/universe/titles_v2_all.csv"):
    d = pd.read_csv(p, dtype=str).fillna("")
    res = [classify(c, s) for c, s in zip(d.cik, d.sic)]
    d["sector_v2_raw"] = [r[0] for r in res]
    d["sector_rule"] = [r[1] for r in res]
    d["sector_flag"] = [r[2] for r in res]
    d["sector"] = d.sector_v2_raw.replace(GROUP)
    d.to_csv(p, index=False)
t = pd.read_csv("data/universe/titles_v2_all.csv", dtype=str).fillna("")
t[t.decision == "REVIEW"].to_csv("data/universe/review_all.csv", index=False)
d = pd.read_csv("data/universe/ipo_deals_all.csv", dtype=str).fillna("")
o = d[d.status == "OPERATING"]
before = o.sector_original.replace(GROUP).value_counts()
after = o.sector.value_counts()
cmp_ = pd.DataFrame({"before_v1_grouped": before, "after_v2_grouped": after}).fillna(0).astype(int)
cmp_["change"] = cmp_.after_v2_grouped - cmp_.before_v1_grouped
ch = o[o.sector_original.replace(GROUP) != o.sector]
ch[["year", "cik", "legal_name", "sic", "sic_description", "sector_original", "sector", "sector_rule"]].to_csv(
    "verify/sector_v2_changes.csv", index=False)
open("verify/sector_v2_tables.md", "w").write(
    "## Sector counts, operating IPOs (v1 vs v2, both with Caleb's grouping)\n" + cmp_.to_markdown() +
    "\n\n## Rule usage among changed rows\n" + ch.sector_rule.str.slice(0, 60).value_counts().to_frame().to_markdown() +
    f"\n\nChanged: {len(ch)} of {len(o)} operating rows. Remaining SECTOR_AMBIGUOUS_SIC rows: {(o.sector_flag != '').sum()}\n")
print(open("verify/sector_v2_tables.md").read())
print(ch.sample(20, random_state=1)[["legal_name", "sic", "sector_original", "sector"]].to_string())
