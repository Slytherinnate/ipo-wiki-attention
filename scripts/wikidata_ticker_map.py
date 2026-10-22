"""Download a ticker -> enwiki title map from Wikidata (P414 stock exchange with
qualifier P249 ticker symbol), NYSE (Q13677) and Nasdaq (Q82059) only, one
SPARQL query, cached to data/cache/wikidata_tickers.json. Used as match step 2
(after the CIK P5531 match). A ticker hit must still pass a name-overlap check
in match_all.py because tickers get reused after delistings."""
import json, os, requests
UA = {"User-Agent": "CalebHavens-DSPortfolio/0.2 (wiki-attention IPO study; calebhavens08@gmail.com)",
      "Accept": "application/sparql-results+json"}
Q = """SELECT ?item ?ticker ?exch ?article WHERE {
  VALUES ?exch { wd:Q13677 wd:Q82059 }
  ?item p:P414 ?st . ?st ps:P414 ?exch ; pq:P249 ?ticker .
  ?article schema:about ?item ; schema:isPartOf <https://en.wikipedia.org/> .
}"""
out = "data/cache/wikidata_tickers.json"
if not os.path.exists(out):
    r = requests.get("https://query.wikidata.org/sparql", params={"query": Q}, headers=UA, timeout=120)
    r.raise_for_status()
    m = {}
    for b in r.json()["results"]["bindings"]:
        title = requests.utils.unquote(b["article"]["value"].rsplit("/", 1)[-1]).replace("_", " ")
        m.setdefault(b["ticker"]["value"].upper(), []).append({"qid": b["item"]["value"].rsplit("/", 1)[-1], "title": title})
    json.dump(m, open(out, "w"))
m = json.load(open(out))
print("tickers:", len(m), "example RDDT:", m.get("RDDT"), "ARM:", m.get("ARM"))
