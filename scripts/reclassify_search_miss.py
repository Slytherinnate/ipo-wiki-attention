"""Rule change (Caleb, Oct 20 2026): a search hit unrelated to the company (or
no hit at all) is no longer DROP_NO_ARTICLE. It becomes REVIEW with reason
SEARCH_MISS (checklist 3.1), unless the deal is clearly tiny:
gross_proceeds < $25M -> DROP_TINY_NO_ARTICLE. A missing gross_proceeds is not
treated as tiny (it goes to REVIEW). No API calls; rewrites titles_v2_all.csv
and review_all.csv and logs every change to verify/reclassify_log.csv.
SEARCH_MISS rows have no verified title, so no views file exists yet: views are
pulled after Caleb fills review_title."""
import pandas as pd
TINY = 25e6
t = pd.read_csv("data/universe/titles_v2_all.csv", dtype=str).fillna("")
m = t.decision == "DROP_NO_ARTICLE"
g = pd.to_numeric(t.gross_proceeds, errors="coerce")
tiny = m & (g < TINY)
miss = m & ~tiny
log = t.loc[m, ["year", "cik", "legal_name", "final_title", "gross_proceeds"]].copy()
log["old"] = "DROP_NO_ARTICLE"
t.loc[tiny, "decision"] = "DROP_TINY_NO_ARTICLE"
t.loc[miss, "decision"] = "REVIEW"
t.loc[miss, "reasons"] = (t.loc[miss, "reasons"] + " SEARCH_MISS").str.strip()
t.loc[miss, "review_sections"] = (t.loc[miss, "review_sections"] + " 3.1").str.strip()
t.loc[miss, "search_hit_discarded"] = t.loc[miss, "final_title"]
t.loc[miss, "final_title"] = ""
log["new"] = t.loc[m, "decision"]
t["reasons"] = t.reasons.str.replace("search hit unrelated to company name", "", regex=False).str.strip()
# carry Caleb's later decisions from the deals table (old checkpoints predate them)
dd = pd.read_csv("data/universe/ipo_deals_all.csv", dtype=str).fillna("").set_index(["cik", "year"])
key = list(zip(t.cik, t.year))
for c in ("sector", "sector_original", "attention_only", "form_type", "first_trade_date", "first_trade_conf"):
    t[c] = [dd.at[k, c] if k in dd.index else "" for k in key]
log.to_csv("verify/reclassify_log.csv", index=False)
t.to_csv("data/universe/titles_v2_all.csv", index=False)
t[t.decision == "REVIEW"].to_csv("data/universe/review_all.csv", index=False)
print("SEARCH_MISS -> REVIEW:", miss.sum(), "| tiny -> DROP_TINY_NO_ARTICLE:", tiny.sum())
