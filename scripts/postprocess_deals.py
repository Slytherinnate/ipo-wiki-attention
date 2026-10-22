"""Post-process ipo_deals_all.csv (idempotent; Caleb decisions Oct 20 2026):
- form_type blank -> 424B4 (rows parsed before 424B1 support)
- DIRECT_LISTING: first_trade_date blanked (424B4 date != listing date), attention_only=1
  (in attention analysis, excluded from first-day/30-day return tests)
- sector: Communication Services, Utilities, Unknown -> Other
- follow-on style (already-reporting) filers: already excluded by the universe rule
  (10-K/10-Q/20-F before the prospectus), confirmed by Caleb; nothing to drop here."""
import pandas as pd
GROUP = {"Communication Services": "Other", "Utilities": "Other", "Unknown": "Other"}
p = "data/universe/ipo_deals_all.csv"
d = pd.read_csv(p, dtype=str).fillna("")
d.loc[d.form_type == "", "form_type"] = "424B4"
dl = d.deal_flags.str.contains("DIRECT_LISTING")
d.loc[dl, ["first_trade_date"]] = ""
d.loc[dl, "first_trade_conf"] = "unknown"
d["attention_only"] = dl.astype(int).astype(str)
d["sector_original"] = d.get("sector_original", d.sector).where(d.get("sector_original", d.sector) != "", d.sector)
d["sector"] = d.sector_original.replace(GROUP)
d.to_csv(p, index=False)
o = d[d.status == "OPERATING"]
print("operating", len(o), "by form", o.form_type.value_counts().to_dict(), "attention_only", (o.attention_only == "1").sum())
