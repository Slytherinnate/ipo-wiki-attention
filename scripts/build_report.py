"""Build docs/build-report-<date>.md tables from the pipeline outputs (no API calls)."""
import datetime as dt
import pandas as pd

deals = pd.read_csv("data/universe/ipo_deals_all.csv", dtype=str).fillna("")
t = pd.read_csv("data/universe/titles_v2_all.csv", dtype=str).fillna("")
op = deals[deals.status == "OPERATING"]


def md(df):
    return df.to_markdown()


stage = pd.DataFrame({
    "universe_prospectus": deals.groupby("year").size(),
    "excluded_spac_fund": deals[deals.status == "EXCLUDED"].groupby("year").size(),
    "operating": op.groupby("year").size(),
    "from_424b1": op[op.form_type == "424B1"].groupby("year").size(),
    "attention_only": op[op.attention_only == "1"].groupby("year").size(),
    "priced": op[op.offer_price != ""].groupby("year").size(),
    "matched": t[~t.decision.str.startswith("DROP") & (t.final_title != "")].groupby("year").size(),
    "auto_keep": t[t.decision == "AUTO_KEEP"].groupby("year").size(),
    "review": t[t.decision == "REVIEW"].groupby("year").size(),
    "review_search_left": t[(t.decision == "REVIEW") & t.reasons.str.contains("SEARCH_MISS|SEARCH_CANDIDATE")].groupby("year").size(),
    "views_files": t[~t.decision.str.startswith("DROP") & (t.final_title != "")].groupby("year").size(),
    "no_article": t[t.decision.isin(["DROP_NO_ARTICLE","DROP_TINY_NO_ARTICLE","DROP_NO_ARTICLE_CONFIRMED"])].groupby("year").size(),
}).fillna(0).astype(int)
stage.loc["total"] = stage.sum()

sec = pd.DataFrame({
    "operating": op.groupby("sector").size(),
    "priced": op[op.offer_price != ""].groupby("sector").size(),
    "auto_keep": t[t.decision == "AUTO_KEEP"].groupby("sector").size(),
    "review": t[t.decision == "REVIEW"].groupby("sector").size(),
    "no_article": t[t.decision.isin(["DROP_NO_ARTICLE","DROP_TINY_NO_ARTICLE","DROP_NO_ARTICLE_CONFIRMED"])].groupby("sector").size(),
}).fillna(0).astype(int).sort_values("operating", ascending=False)
sec["kept_or_review"] = sec.auto_keep + sec.review
sec.loc["total"] = sec.sum()

cov = pd.DataFrame({
    "offer_price_%": op.groupby("year").apply(lambda x: (x.offer_price != "").mean() * 100),
    "shares_%": op.groupby("year").apply(lambda x: (x.shares_offered_base != "").mean() * 100),
    "gross_%": op.groupby("year").apply(lambda x: (x.gross_proceeds != "").mean() * 100),
    "underwriters_%": op.groupby("year").apply(lambda x: (x.underwriters_on_cover != "").mean() * 100),
    "uw_block_exact_%": op.groupby("year").apply(lambda x: (~x.deal_flags.str.contains("UW_BLOCK_GUESSED")).mean() * 100),
    "trade_date_any_%": op.groupby("year").apply(lambda x: (x.first_trade_date != "").mean() * 100),
}).round(1)
cov.loc["all"] = [(op.offer_price != "").mean() * 100, (op.shares_offered_base != "").mean() * 100,
                  (op.gross_proceeds != "").mean() * 100, (op.underwriters_on_cover != "").mean() * 100,
                  (~op.deal_flags.str.contains("UW_BLOCK_GUESSED")).mean() * 100, (op.first_trade_date != "").mean() * 100]
cov = cov.round(1)
conf = op.groupby("year").first_trade_conf.value_counts().unstack().fillna(0).astype(int)
conf.loc["total"] = conf.sum()
dflags = op.deal_flags.str.split().explode().value_counts()
rv = t[t.decision == "REVIEW"]
rreasons = rv.reasons.str.split().explode().value_counts()
methods = t.match_method.value_counts()
open("verify/report_tables.md", "w").write("\n\n".join([
    "## Stage counts by year\n" + md(stage), "## By sector\n" + md(sec), "## Deal-field coverage % (operating rows)\n" + md(cov),
    "## First-trade-date confidence\n" + md(conf), "## Deal flags (operating rows)\n" + md(dflags.to_frame()),
    "## Review reasons (REVIEW rows; a row can have several)\n" + md(rreasons.to_frame()),
    "## Match method (all operating rows)\n" + md(methods.to_frame()),
    f"## Views files\n{len(t[~t.decision.str.startswith('DROP') & (t.final_title != '')])} rows -> data/processed/views/<CIK>.csv (181 days each)"]))
print(open("verify/report_tables.md").read())
