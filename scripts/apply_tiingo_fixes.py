"""Apply Caleb-approved fixes (Oct 20 2026, 7 PM). Idempotent; backups in
data/universe/backup_pre_reanchor_*/ and data/local_only/backup/.
(1) Rows with returns_status OK_DATE_MINUS1 (first Tiingo bar exactly 1 NYSE trading day
    before our derived date): first_trade_date := Tiingo first bar date;
    first_trade_conf := tiingo_corrected; first_trade_date_edgar keeps our old value;
    first_trade_source explains. Tiingo is used only to correct OUR estimated date.
    Pageview windows (-120..+60, redirects summed, 0-fill) are rebuilt for those rows
    from the per-title pageview cache (Wikimedia API only for redirect lists).
(2) INVALID_PRIOR_LISTING rows -> attention_only=1, attention_reason=pre_listed
    (direct listings get attention_reason=direct_listing).
Log: verify/tiingo_fixes_log.csv"""
import datetime as dt, os, sys
from collections import defaultdict
import pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
import match_all as ma
v2 = ma.v2
ret = pd.read_csv("data/local_only/ipo_returns.csv", dtype=str).fillna("")
fix = ret[ret.returns_status == "OK_DATE_MINUS1"].set_index(["cik", "year"]).first_trade_date_corrected.to_dict()
pre = set(zip(ret[ret.returns_status == "INVALID_PRIOR_LISTING"].cik, ret[ret.returns_status == "INVALID_PRIOR_LISTING"].year))
log = []
for path in ("data/universe/ipo_deals_all.csv", "data/universe/titles_v2_all.csv"):
    d = pd.read_csv(path, dtype=str).fillna("")
    for c in ("first_trade_date_edgar", "first_trade_source", "attention_reason"):
        if c not in d:
            d[c] = ""
    d.loc[(d.attention_only == "1") & (d.attention_reason == ""), "attention_reason"] = "direct_listing"
    for i, r in d.iterrows():
        k = (r.cik, r.year)
        if k in fix and r.first_trade_conf != "tiingo_corrected":
            d.at[i, "first_trade_date_edgar"] = r.first_trade_date
            d.at[i, "first_trade_date"] = fix[k]
            d.at[i, "first_trade_conf"] = "tiingo_corrected"
            d.at[i, "first_trade_source"] = "EDGAR-derived date was 1 trading day late; corrected to first Tiingo EOD bar (own-date correction only)"
            if path.endswith("titles_v2_all.csv"):
                log.append({"cik": r.cik, "year": r.year, "legal_name": r.legal_name, "change": "reanchor",
                            "old": r.first_trade_date, "new": fix[k]})
        if k in pre and r.attention_reason != "pre_listed":
            d.at[i, "attention_only"], d.at[i, "attention_reason"] = "1", "pre_listed"
            if path.endswith("titles_v2_all.csv"):
                log.append({"cik": r.cik, "year": r.year, "legal_name": r.legal_name, "change": "attention_only pre_listed"})
    if path.endswith("titles_v2_all.csv"):
        rebuilt = 0
        for i, r in d[d.first_trade_conf == "tiingo_corrected"].iterrows():
            if r.decision.startswith("DROP") or not r.final_title:
                continue
            info = v2.page_details(r.final_title)
            total = defaultdict(int)
            for t in [info["final_title"]] + info["redirects"][:v2.MAX_REDIRECTS]:
                for day, v in ma.views_cached(t).items():
                    total[day] += v
            a = dt.date.fromisoformat(r.first_trade_date)
            day = lambda k: (a + dt.timedelta(days=k)).strftime("%Y%m%d")
            d.at[i, "anchor_date"] = a.isoformat()
            d.at[i, "views_30d_pre"] = str(sum(total.get(day(-k), 0) for k in range(1, 31)))
            d.at[i, "views_30d_post"] = str(sum(total.get(day(k), 0) for k in range(0, 30)))
            with open(f"data/processed/views/{r.cik}.csv", "w") as fh:
                fh.write("date,day_rel,views\n")
                for k in range(-120, 61):
                    dd = a + dt.timedelta(days=k)
                    fh.write(f"{dd.isoformat()},{k},{total.get(dd.strftime('%Y%m%d'), 0)}\n")
            rebuilt += 1
        print("views rebuilt:", rebuilt)
        d[d.decision == "REVIEW"].to_csv("data/universe/review_all.csv", index=False)
    d.to_csv(path, index=False)
# keep the local returns file consistent
ret["first_trade_date"] = [fix.get((c, y), f) for c, y, f in zip(ret.cik, ret.year, ret.first_trade_date)]
ret.loc[ret.returns_status == "INVALID_PRIOR_LISTING", "attention_only"] = "1"
ret.to_csv("data/local_only/ipo_returns.csv", index=False)
pd.DataFrame(log).to_csv("verify/tiingo_fixes_log.csv", index=False)
print(pd.DataFrame(log).change.value_counts().to_string() if log else "no changes")
