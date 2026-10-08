# Property Price Register — data profile (HOUSE-8)

Source file: `PPR-ALL.zip`  
Profiled: 2026-10-08

## Size and coverage
- Rows: **810,390**
- Sale dates: 01 Jan 2010 to 02 Oct 2026 (0 unparseable)
- Dublin rows: 253,994; South Dublin by keyword (rough): 40,773

### Rows by year
| Year | Rows |
|---|---|
| 2010 | 21,005 |
| 2011 | 18,446 |
| 2012 | 25,375 |
| 2013 | 30,227 |
| 2014 | 43,677 |
| 2015 | 49,166 |
| 2016 | 49,941 |
| 2017 | 55,023 |
| 2018 | 57,464 |
| 2019 | 59,067 |
| 2020 | 49,561 |
| 2021 | 59,608 |
| 2022 | 62,763 |
| 2023 | 63,387 |
| 2024 | 61,570 |
| 2025 | 62,099 |
| 2026 | 42,011 |

### Rows by county
| County | Rows |
|---|---|
| Dublin | 253,994 |
| Cork | 89,684 |
| Kildare | 44,228 |
| Galway | 39,024 |
| Meath | 33,674 |
| Limerick | 29,688 |
| Wexford | 28,341 |
| Wicklow | 27,395 |
| Louth | 22,816 |
| Waterford | 22,188 |
| Kerry | 21,944 |
| Tipperary | 21,647 |
| Donegal | 21,484 |
| Mayo | 19,270 |
| Clare | 18,102 |
| Westmeath | 15,666 |
| Laois | 13,496 |
| Kilkenny | 13,088 |
| Cavan | 11,940 |
| Sligo | 11,792 |
| Roscommon | 11,415 |
| Offaly | 10,360 |
| Carlow | 8,838 |
| Leitrim | 7,120 |
| Longford | 6,824 |
| Monaghan | 6,372 |

## Completeness (share of blank values)
| Column | Blank |
|---|---|
| date_of_sale | 0.0% |
| address | 0.0% |
| county | 0.0% |
| eircode | 68.8% |
| price_raw | 0.0% |
| not_full_market_price | 0.0% |
| vat_exclusive | 0.0% |
| description | 0.0% |
| size_description | 93.5% |

## Prices
- Unparseable: 0
- min: €5,001, p01: €24,057, median: €245,000, p99: €1,425,000, max: €387,665,198
- Under €10,000: 1,100; over €5m: 1,056
- Flagged 'not full market price': 41,283
- VAT exclusive (new builds, price excludes 13.5% VAT): 142,876

## Property description values
| Value | Rows |
|---|---|
| Second-Hand Dwelling house /Apartment | 665,086 |
| New Dwelling house /Apartment | 145,255 |
| Teach/Árasán Cónaithe Atháimhe | 45 |
| Teach/Árasán Cónaithe Nua | 3 |
| Teach/?ras?n C?naithe Nua | 1 |

## Exact duplicate rows: 1,085

## Messy address samples (kept for Sprint 3 normalisation tests)
- `33 RAGIAN ROAD, BALLSBRIDGE, DUBLIN 4`
- `48 KILLIANS COURT, MULLAGH`
- `CARROWTRASNA, CARROWMORE LACKEN, BALLINA`
- `No. 11 Blackrock Court, Quay Road, Ballina`
- `No. 11, Charlotte Quay`
- `No. 12, Charlotte Quay`
- `No. 13, Charlotte Quay`
- `No. 18, Charlotte Quay`
- `11 CASTLE COURT, BIRR`
- `12 CASTLE COURT, BIRR`

## Top 5 quality issues
_Write these up after reading the numbers above: issue, example, proposed fix._
