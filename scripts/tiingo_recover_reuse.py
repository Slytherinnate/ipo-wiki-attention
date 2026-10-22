"""Recover original-company price history for reused-ticker rows (Caleb approved, Oct 20).
Source: Tiingo's public supported_tickers.csv (data/raw/tiingo/, local only). For each
reused row, candidates = listed tickers whose root is our ticker (same ticker + Q/F/Y/W
suffix, as used after bankruptcy/OTC moves) or the 424B4 cover ticker, with a startDate
within 5 days of our first-trade date on a US venue (NYSE/NASDAQ/AMEX/NYSE MKT/PINK/OTC).
A candidate that is the SAME ticker string as the reused one cannot be reached (the API
returns the current holder), so it is logged UNREACHABLE_SAME_TICKER.
Accepted candidates are pulled with tiingo_prices.one() (same caching, rate limit, checks)
and then re-validated by tiingo_validate.py. Log: verify/tiingo_recover_log.csv"""
import csv, datetime as dt, os, sys
import pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
import tiingo_prices as tp
US = {"NYSE", "NASDAQ", "AMEX", "NYSE MKT", "PINK", "OTC", "OTCQB", "OTCQX", "NYSE ARCA"}
st = pd.read_csv("data/raw/tiingo/supported_tickers.csv", dtype=str).fillna("")
st = st[st.exchange.isin(US)]
p = "data/local_only/ipo_returns.csv"
r = pd.read_csv(p, dtype=str).fillna("")
rows = {x["cik"]: x for x in csv.DictReader(open("data/universe/titles_v2_all.csv", encoding="utf-8"))}
reuse = r[(r.returns_status == "INVALID_TICKER_REUSE") | ((r.returns_status == "NO_DATA") & r["flags"].str.contains("NAME_MISMATCH"))]
log = []
for i, x in reuse.iterrows():
    row = dict(rows[x.cik])
    anchor = row["first_trade_date"] or row["filing_date_424b4"]
    a = dt.date.fromisoformat(anchor)
    roots = {t for t in (x.tiingo_ticker, x.cover_ticker) if t}
    c = st[st.ticker.apply(lambda t: any(t == rt or (t.startswith(rt) and len(t) == len(rt) + 1 and t[-1] in "QFYW") for rt in roots))]
    c = c[c.startDate.apply(lambda s: bool(s) and abs((dt.date.fromisoformat(s) - a).days) <= 5)]
    if c.empty:
        log.append({"cik": x.cik, "legal_name": x.legal_name, "old_ticker": x.tiingo_ticker, "result": "NO_CANDIDATE"}); continue
    reach = c[c.ticker != x.tiingo_ticker]
    if reach.empty:
        log.append({"cik": x.cik, "legal_name": x.legal_name, "old_ticker": x.tiingo_ticker,
                    "candidate": ";".join(c.ticker + "@" + c.startDate), "result": "UNREACHABLE_SAME_TICKER"}); continue
    tk = reach.iloc[0].ticker
    row["tickers"] = tk                      # try the recovered ticker
    res = tp.one(row)
    res["decision"] = x.decision
    res["recovered_from"] = f"{x.tiingo_ticker}->{tk} (supported_tickers start {reach.iloc[0].startDate})"
    keep = {"year", "cik", "decision", "legal_name", "sector", "offer_price", "first_trade_date", "first_trade_conf"}
    for k in r.columns:
        if k not in keep:
            r.at[i, k] = ""          # clear the wrong-company values first
    for k, v in res.items():
        if k not in r.columns:
            r[k] = ""
        r.at[i, k] = str(v)
    log.append({"cik": x.cik, "legal_name": x.legal_name, "old_ticker": x.tiingo_ticker, "candidate": tk,
                "result": "PULLED", "tiingo_name": res.get("tiingo_name", ""), "flags": res.get("flags", "")})
r.to_csv(p, index=False)
pd.DataFrame(log).to_csv("verify/tiingo_recover_log.csv", index=False)
print(pd.DataFrame(log)[["legal_name", "old_ticker", "candidate", "result"] + (["tiingo_name"] if any("tiingo_name" in l for l in log) else [])].to_string())
