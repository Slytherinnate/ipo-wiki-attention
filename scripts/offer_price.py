"""
offer_price.py: pull the IPO offer price from a company's 424B4 prospectus.

The 424B4 cover page states the price, e.g. "The initial public offering
price is $34.00 per share" or a table row "Initial public offering price $ 34.00".
We download only the first ~600 KB of the filing (the cover page is at the top),
strip the HTML, and take the first dollar amount after the phrase
"public offering price". Rows where no price is found are flagged for review.

Input : data/universe/ipo_universe_YYYY.csv  (needs cik, filing_date_424b4)
        data/cache/index/YYYYQn.idx          (to find the 424B4 file path)
Output: data/universe/offer_prices_YYYY.csv
Run:    python scripts/offer_price.py 2024 [--only "Reddit, Inc.;Rubrik, Inc."]
SEC fair access: <=10 requests/s and a declared User-Agent.
"""
import csv
import html
import os
import re
import sys
import time

import requests

UA = {"User-Agent": "Caleb Havens calebhavens08@gmail.com"}
PRICE_RE = re.compile(r"public offering price[^$]{0,250}?\$\s*([\d,]+\.\d{2})", re.I)
RANGE_RE = re.compile(r"between \$\s*([\d.]+) and \$\s*([\d.]+)", re.I)   # a red flag on a 424B4


def filing_paths(year):
    """{cik: file path} of each company's first 424B4 in the year."""
    paths = {}
    for q in range(1, 5):
        for line in open(f"data/cache/index/{year}Q{q}.idx", errors="replace"):
            if line.startswith("424B4 "):
                p = line.split()
                cik, date, path = p[-3], p[-2], p[-1]
                if cik not in paths or date < paths[cik][0]:
                    paths[cik] = (date, path)
    return {k: v[1] for k, v in paths.items()}


def cover_text(path):
    cache = os.path.join("data/cache/424b4", path.replace("/", "_"))
    if os.path.exists(cache):
        return open(cache, encoding="utf-8").read()
    time.sleep(0.15)
    r = requests.get("https://www.sec.gov/Archives/" + path, headers={**UA, "Range": "bytes=0-600000"}, timeout=60)
    r.raise_for_status()
    text = re.sub(r"<[^>]+>", " ", r.content.decode("latin-1"))
    text = re.sub(r"\s+", " ", html.unescape(text))
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    open(cache, "w", encoding="utf-8").write(text)
    return text


def main(year, only=None):
    rows = list(csv.DictReader(open(f"data/universe/ipo_universe_{year}.csv", encoding="utf-8")))
    if only:
        rows = [r for r in rows if r["name"] in only]
    paths = filing_paths(year)
    out = []
    for r in rows:
        text = cover_text(paths[r["cik"]])
        m = PRICE_RE.search(text)
        flags = [] if m else ["NO_PRICE_FOUND"]
        if RANGE_RE.search(text[:20000]):
            flags.append("PRICE_RANGE_ON_COVER")
        out.append({"cik": r["cik"], "name": r["name"], "filing_date_424b4": r["filing_date_424b4"],
                    "offer_price": m.group(1).replace(",", "") if m else "",
                    "context": text[max(0, m.start() - 60):m.end() + 20] if m else "",
                    "source": "https://www.sec.gov/Archives/" + paths[r["cik"]], "flags": " ".join(flags)})
        print(out[-1]["name"], out[-1]["offer_price"], out[-1]["flags"])
    with open(f"data/universe/offer_prices_{year}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)


if __name__ == "__main__":
    year = sys.argv[1] if len(sys.argv) > 1 else "2024"
    only = set(sys.argv[3].split(";")) if len(sys.argv) > 3 and sys.argv[2] == "--only" else None
    main(year, only)
