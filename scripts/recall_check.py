"""Recall check: are well-known IPOs of each year in ipo_universe_YYYY.csv?
Expected-absent rows are direct listings (no 424B4 underwritten IPO) and act as
negative controls. Evidence = the EDGAR filing URL of the matched 424B4 row.
Sample chosen from memory of widely reported IPOs; membership is verified only
against EDGAR (no price or news sites). Output: verify/recall_check.csv"""
import csv, json, re
S = {
 "2019": ["Uber", "Lyft", "Zoom", "Pinterest", "Beyond Meat", "CrowdStrike", "Peloton", "Chewy", "Levi Strauss", "Datadog",
          "Cloudflare", "Fastly", "PagerDuty", "Medallia", "Guardant", "Tradeweb", "Avantor", "BILL Holdings", "Sprout Social", "Livongo",
          "!Slack"],
 "2020": ["Snowflake", "Airbnb", "DoorDash", "Unity Software", "ZoomInfo", "Warner Music", "Royalty Pharma", "Lemonade", "Vroom",
          "Rackspace", "JFrog", "Sumo Logic", "Corsair", "BigCommerce", "GoodRx", "Duck Creek", "Jamf", "C3.ai", "Wish", "Shift4",
          "!Palantir", "!Asana"],
 "2021": ["Rivian", "Coupang", "Bumble", "Affirm", "Robinhood", "Duolingo", "Toast", "DigitalOcean", "UiPath", "Oscar Health",
          "Marqeta", "Confluent", "Sprinklr", "Freshworks", "GitLab", "HashiCorp", "Nubank", "Samsara", "Olaplex", "Allbirds",
          "!Coinbase", "!Roblox"],
 "2022": ["Mobileye", "Corebridge", "TPG", "Excelerate", "Bausch", "Credo", "ProFrac", "HilleVax", "Amylyx", "Arcellx",
          "CinCor", "Vigil Neuroscience", "Nuvectis", "Akanda", "Hour Loop", "Austin Gold", "Hanover Bancorp",
          "Amprius", "Intensity", "Atlas Energy", "!Bright Green"],
 "2023": ["Arm Holdings", "Maplebear", "Klaviyo", "Kenvue", "Cava", "Birkenstock", "Nextpower", "Savers Value", "Oddity",
          "Kodiak Gas", "Fidelis Insurance", "Atmus", "Enlight", "Structure Therapeutics", "Acelyrin", "Neumora", "RayzeBio",
          "Apogee Therapeutics", "Instacart", "Turnstone"],
 "2024": ["Reddit", "Rubrik", "Astera Labs", "ServiceTitan", "Ibotta", "Amer Sports", "Viking Holdings", "Loar", "Waystar",
          "Tempus AI", "OneStream", "Lineage", "StandardAero", "Ingram Micro", "UL Solutions", "Kyverna", "CG Oncology", "BrightSpring",
          "Galderma", "Universal Technical"],
 "2025": ["CoreWeave", "Circle Internet", "Figma", "Klarna", "Chime", "eToro", "Hinge Health", "MNTN", "Omada", "Voyager Technologies",
          "Bullish", "Firefly Aerospace", "Gemini Space", "StubHub", "Netskope", "Via Transportation", "Medline", "SailPoint",
          "Venture Global", "Karman"],
}
out = []
for y, names in S.items():
    rows = list(csv.DictReader(open(f"data/universe/ipo_universe_{y}.csv", encoding="utf-8")))
    for n in names:
        neg = n.startswith("!")
        n = n.lstrip("!")
        def names(r):
            d = json.load(open(f"data/cache/subs/{r['cik']}.json"))
            return [d.get("name", "")] + [f.get("name", "") for f in d.get("formerNames", [])]
        hit = [r for r in rows if any(re.search(r"(?i)\b" + re.escape(n), x) for x in names(r)) and "SPAC" not in r["flags"]]
        out.append({"year": y, "company": n, "expected": "absent (direct listing)" if neg else "present",
                    "found": "yes" if hit else "no", "cik": hit[0]["cik"] if hit else "",
                    "edgar_name": hit[0]["name"] if hit else "", "filing_date_424b4": hit[0]["filing_date_424b4"] if hit else "",
                    "evidence": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={hit[0]['cik']}&type=424B4" if hit else ""})
csv.DictWriter(open("verify/recall_check.csv", "w", newline=""), fieldnames=list(out[0])).writeheader()
w = csv.DictWriter(open("verify/recall_check.csv", "a", newline=""), fieldnames=list(out[0])); w.writerows(out)
for o in out:
    if (o["found"] == "yes") == (o["expected"] != "present"):
        print("MISS/UNEXPECTED", o["year"], o["company"], o["expected"], o["found"])
from collections import Counter
c = Counter((o["year"], o["found"]) for o in out if o["expected"] == "present")
for y in S: print(y, c[(y, "yes")], "/", c[(y, "yes")] + c[(y, "no")])
