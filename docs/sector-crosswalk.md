# Sector crosswalk v2 (SIC -> GICS-style), Oct 20 2026

There is **no official SIC-to-GICS crosswalk**. Our sectors are a documented approximation. SIC codes and titles come from the SEC company submissions JSON and the SEC SIC code list (https://www.sec.gov/search-filings/standard-industrial-classification-sic-code-list). The sector names follow GICS-style naming, but these are NOT GICS assignments, which are proprietary to MSCI and S&P. Script: `scripts/sector_v2.py`. All changed rows are listed in `verify/sector_v2_changes.csv`.

**Precedence:**
1. Company override (`data/universe/sector_overrides.csv`, 29 rows). These cover only SIC 7389 "Business Services, NEC" and 7340, the catch-all codes, and only for rows that are auto-kept or in review. Each override is based on the company's stated business and is our judgment, to be verified.
2. The v2 SIC rules below, where the first match wins.
3. The v1 SIC ranges in `build_ipo_universe.py`.
4. Other.

Rows whose SIC is ambiguous (7389, 7340, 7380, 8742, 3990, 0700) and have no override are marked `sector_flag=SECTOR_AMBIGUOUS_SIC`. Caleb's grouping (Communication Services, Utilities and Unknown into Other) is applied last. The `sector_original` column (v1) is unchanged; the new columns are `sector_v2_raw`, `sector_rule` and `sector_flag`.

## Rule changes vs v1
- SIC 2840-2844 -> Consumer Staples: R01 soaps/cosmetics -> Staples
- SIC 2850-2899 -> Materials: R02 paints/agri/misc chemicals -> Materials (v1 Staples)
- SIC 2400-2499 -> Materials: R03 lumber & wood -> Materials (v1 Other)
- SIC 2510-2519 -> Consumer Discretionary: R04 household furniture -> Cons Disc (v1 Other)
- SIC 2520-2599 -> Industrials: R05 office/store furniture & fixtures -> Industrials (v1 Other)
- SIC 3020-3021 -> Consumer Discretionary: R06 rubber/plastic footwear -> Cons Disc
- SIC 3100-3199 -> Consumer Discretionary: R07 leather & footwear -> Cons Disc
- SIC 3200-3299 -> Materials: R08 glass/stone/clay/concrete -> Materials
- SIC 3533-3533 -> Energy: R09 oil & gas field machinery -> Energy (equipment & services)
- SIC 3630-3639 -> Consumer Discretionary: R10 household appliances -> Cons Disc (v1 IT)
- SIC 3651-3652 -> Consumer Discretionary: R11 household audio/video -> Cons Disc (v1 IT)
- SIC 3751-3751 -> Consumer Discretionary: R12 motorcycles/bicycles -> Cons Disc
- SIC 3826-3826 -> Health Care: R13 laboratory analytical instruments -> Health Care (life-science tools)
- SIC 3910-3915 -> Consumer Discretionary: R14 jewelry -> Cons Disc
- SIC 3940-3949 -> Consumer Discretionary: R15 toys/sporting & athletic goods -> Cons Disc
- SIC 4950-4959 -> Industrials: R16 sanitary/waste services -> Industrials (v1 Utilities)
- SIC 1520-1531 -> Consumer Discretionary: R17 residential builders/operative builders -> Cons Disc (homebuilding)
- SIC 5912-5912 -> Consumer Staples: R18 drug stores -> Staples (v1 Cons Disc)
- SIC 7310-7319 -> Communication Services: R19 advertising -> Communication Services (media)
- SIC 100-299 -> Consumer Staples: R20 crops & livestock -> Staples (v1 Other); 0700 agri services left Other + ambiguous
- SIC 7200-7299 -> Consumer Discretionary: R21 personal services -> Cons Disc (v1 Other)
- SIC 7500-7699 -> Consumer Discretionary: R22 auto repair/misc repair -> Cons Disc (v1 Other)
- SIC 8350-8351 -> Consumer Discretionary: R23 child day care -> Cons Disc (v1 Other)

## Sector counts, operating IPOs (v1 vs v2, both with Caleb's grouping)
|                        |   before_v1_grouped |   after_v2_grouped |   change |
|:-----------------------|--------------------:|-------------------:|---------:|
| Consumer Discretionary |                 165 |                204 |       39 |
| Consumer Staples       |                  45 |                 47 |        2 |
| Energy                 |                  23 |                 28 |        5 |
| Financials             |                 131 |                137 |        6 |
| Health Care            |                 464 |                481 |       17 |
| Industrials            |                 196 |                142 |      -54 |
| Information Technology |                 288 |                270 |      -18 |
| Materials              |                  17 |                 22 |        5 |
| Other                  |                  54 |                 51 |       -3 |
| Real Estate            |                  27 |                 28 |        1 |

## Rule usage among changed rows
| sector_rule                                                  |   count |
|:-------------------------------------------------------------|--------:|
| R13 laboratory analytical instruments -> Health Care (life-s |      14 |
| R19 advertising -> Communication Services (media)            |      12 |
| R17 residential builders/operative builders -> Cons Disc (ho |       7 |
| R15 toys/sporting & athletic goods -> Cons Disc              |       6 |
| R10 household appliances -> Cons Disc (v1 IT)                |       5 |
| R22 auto repair/misc repair -> Cons Disc (v1 Other)          |       5 |
| R09 oil & gas field machinery -> Energy (equipment & service |       5 |
| R16 sanitary/waste services -> Industrials (v1 Utilities)    |       3 |
| R21 personal services -> Cons Disc (v1 Other)                |       3 |
| R02 paints/agri/misc chemicals -> Materials (v1 Staples)     |       3 |
| R20 crops & livestock -> Staples (v1 Other); 0700 agri servi |       3 |
| R12 motorcycles/bicycles -> Cons Disc                        |       2 |
| R11 household audio/video -> Cons Disc (v1 IT)               |       2 |
| R14 jewelry -> Cons Disc                                     |       2 |
| R07 leather & footwear -> Cons Disc                          |       2 |
| OVERRIDE: patient-intake software for healthcare providers   |       1 |
| OVERRIDE: B2B chemicals e-commerce platform                  |       1 |
| OVERRIDE: online business-news media                         |       1 |
| OVERRIDE: telehealth platform                                |       1 |
| OVERRIDE: healthcare navigation services                     |       1 |
| OVERRIDE: lodging marketplace (hotels/leisure-style)         |       1 |
| R04 household furniture -> Cons Disc (v1 Other)              |       1 |
| OVERRIDE: restaurant delivery marketplace                    |       1 |
| OVERRIDE: payment processing                                 |       1 |
| OVERRIDE: restaurant ordering software                       |       1 |
| OVERRIDE: cross-border payments                              |       1 |
| OVERRIDE: remittance payments                                |       1 |
| OVERRIDE: online marketing/advertising                       |       1 |
| OVERRIDE: flexible office space                              |       1 |
| OVERRIDE: online Q&A community (interactive media)           |       1 |
| OVERRIDE: bill payment processing                            |       1 |
| OVERRIDE: e-commerce fraud-prevention software               |       1 |
| R06 rubber/plastic footwear -> Cons Disc                     |       1 |
| OVERRIDE: emerging-market payments                           |       1 |
| R05 office/store furniture & fixtures -> Industrials (v1 Oth |       1 |
| OVERRIDE: consumer e-commerce/rewards app                    |       1 |
| OVERRIDE: grocery delivery (Instacart); staples distribution |       1 |
| R03 lumber & wood -> Materials (v1 Other)                    |       1 |
| R18 drug stores -> Staples (v1 Cons Disc)                    |       1 |
| R23 child day care -> Cons Disc (v1 Other)                   |       1 |
| OVERRIDE: payments/fintech super-app                         |       1 |
| OVERRIDE: AI software services                               |       1 |

Changed: 101 of 1410 operating rows. Remaining SECTOR_AMBIGUOUS_SIC rows: 34
