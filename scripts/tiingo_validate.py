"""Offline validation of data/local_only/ipo_returns.csv (no Tiingo requests,
no comparison with any other price dataset; only EDGAR/our own dates and the
Tiingo meta for the same ticker). Adds returns_status:
  OK                  name matches, first Tiingo bar == our first_trade_date
  OK_DATE_MINUS1      first bar is 1 trading day before our derived date
                      (priced and traded the same day); our date is wrong, Tiingo's first bar is used
  OK_DATE_UNCHECKED   we had no first_trade_date (attention_only rows are not in this file)
  INVALID_TICKER_REUSE   Tiingo's company for this ticker is a different company
                      (no word overlap with legal or any EDGAR former name)
  INVALID_PRIOR_LISTING  ticker history starts > 5 days before our date
                      (already listed: uplisting / foreign-listed ADS / follow-on) -> not an IPO pop
  INVALID_LATE_START  first bar > 2 days after our date (missing first days)
  NO_DATA             no ticker / not in Tiingo / no prices in window
Name check v2: words of length >= 2 (v1 used >= 3, which missed XP, C3.ai, KE),
compared against the legal name AND all EDGAR formerNames.
Output: data/local_only/ipo_returns.csv (columns added, LOCAL ONLY)."""
import datetime as dt, json, re
import pandas as pd
STOP = {"inc", "corp", "corporation", "holdings", "holding", "group", "ltd", "plc", "company", "class", "common",
        "stock", "the", "co", "llc", "sa", "nv", "ag", "de", "a", "ads", "adr", "limited", "international", "global"}
w = lambda x: {t for t in re.sub(r"[^a-z0-9]+", " ", (x or "").lower().replace("'", "").replace("’", "")).split() if len(t) >= 2 and t not in STOP}
import holidays
H = holidays.NYSE(years=range(2018, 2027))


def tgap(a, b):
    s, n, d = (1 if b > a else -1), 0, a
    while d != b:
        d += dt.timedelta(days=s)
        if d.weekday() < 5 and d not in H:
            n += s
    return n


p = "data/local_only/ipo_returns.csv"
r = pd.read_csv(p, dtype=str).fillna("")
out = []
for x in r.itertuples():
    f = set(x.flags.split())
    if f & {"NO_TICKER", "NOT_IN_TIINGO", "NO_PRICES_IN_WINDOW"} or x._asdict().get("pop", "") == "" and not x.tiingo_first_date:
        out.append(("NO_DATA", "")); continue
    subs = json.load(open(f"data/cache/subs/{x.cik}.json"))
    names = [x.legal_name, subs.get("name", "")] + [n.get("name", "") for n in subs.get("formerNames", [])]
    same = bool(w(x.tiingo_name) & set().union(*[w(n) for n in names]))
    anchor = dt.date.fromisoformat(x.first_trade_date) if x.first_trade_date else None
    first = dt.date.fromisoformat(x.tiingo_first_date)
    ms = dt.date.fromisoformat(x.tiingo_start[:10]) if x.tiingo_start else None
    if not same:
        out.append(("INVALID_TICKER_REUSE", "")); continue
    if anchor and ms and (anchor - ms).days > 5:
        out.append(("INVALID_PRIOR_LISTING", "")); continue
    if not anchor:
        out.append(("OK_DATE_UNCHECKED", "")); continue
    gap = tgap(anchor, first)          # NYSE trading days (v2; v1 used calendar days)
    if gap == 0:
        out.append(("OK", ""))
    elif gap == -1:                    # priced and traded the same day
        out.append(("OK_DATE_MINUS1", first.isoformat()))
    elif gap > 2:
        out.append(("INVALID_LATE_START", ""))
    else:                              # +1, +2 or <= -2 trading days: human check
        out.append(("CHECK_DATE_GAP", ""))
r["returns_status"] = [o[0] for o in out]
r["first_trade_date_corrected"] = [o[1] for o in out]
r.to_csv(p, index=False)
print(r.returns_status.value_counts().to_string())
print(pd.crosstab(r.decision, r.returns_status))
print(r[r.returns_status == "INVALID_TICKER_REUSE"][["legal_name", "tiingo_ticker", "tiingo_name"]].to_string())
print(r[r.returns_status.isin(["CHECK_DATE_GAP", "INVALID_LATE_START"])][["legal_name", "first_trade_date", "tiingo_first_date", "first_trade_conf"]].to_string())
