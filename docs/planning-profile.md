# National Planning Applications — South Dublin County Council — data profile (HOUSE-9)

Source file: `south-dublin.json`  
Profiled: 2026-10-10  
Personal fields (applicant name and address) are excluded at download.

## Size and coverage
- Applications: **33,304**
- Received: 02 Jan 1992 to 30 Sep 2026 (35 blank)
- Duplicate application numbers: 1

### Applications by year received
| Year | Applications |
|---|---|
| 1992 | 7 |
| 1993 | 6 |
| 1994 | 6 |
| 1995 | 15 |
| 1996 | 21 |
| 1997 | 13 |
| 1998 | 156 |
| 1999 | 1,197 |
| 2000 | 1,594 |
| 2001 | 1,580 |
| 2002 | 1,369 |
| 2003 | 1,529 |
| 2004 | 1,688 |
| 2005 | 1,779 |
| 2006 | 1,974 |
| 2007 | 1,976 |
| 2008 | 1,529 |
| 2009 | 978 |
| 2010 | 889 |
| 2011 | 793 |
| 2012 | 671 |
| 2013 | 718 |
| 2014 | 696 |
| 2015 | 830 |
| 2016 | 939 |
| 2017 | 951 |
| 2018 | 999 |
| 2019 | 1,011 |
| 2020 | 982 |
| 2021 | 1,123 |
| 2022 | 1,065 |
| 2023 | 1,022 |
| 2024 | 1,075 |
| 2025 | 1,174 |
| 2026 | 914 |

## Completeness (share of blank values)
| Field | Blank |
|---|---|
| OBJECTID | 0.0% |
| PlanningAuthority | 0.0% |
| ApplicationNumber | 0.0% |
| DevelopmentDescription | 0.0% |
| DevelopmentAddress | 0.0% |
| DevelopmentPostcode | 91.6% |
| ITMEasting | 100.0% |
| ITMNorthing | 100.0% |
| ApplicationStatus | 0.3% |
| ApplicationType | 0.0% |
| Decision | 0.6% |
| LandUseCode | 100.0% |
| AreaofSite | 0.0% |
| NumResidentialUnits | 67.4% |
| OneOffHouse | 0.0% |
| FloorArea | 22.2% |
| ReceivedDate | 0.1% |
| WithdrawnDate | 98.6% |
| DecisionDate | 0.6% |
| DecisionDueDate | 1.7% |
| GrantDate | 31.4% |
| ExpiryDate | 84.6% |
| AppealRefNumber | 90.8% |
| AppealStatus | 91.9% |
| AppealDecision | 91.0% |
| AppealDecisionDate | 91.0% |
| LinkAppDetails | 0.0% |
| ETL_DATE | 0.0% |

## Location
- ITMEasting/ITMNorthing attribute columns blank: 33,304
- No location at all (attributes and service geometry both missing): 0
- Coordinates outside Ireland's ITM bounds: 0

## Decisions
- Distinct free-text decision values: **62**

### Grouped
| Group | Applications |
|---|---|
| Granted | 24,270 |
| Refused | 4,963 |
| Invalid | 1,626 |
| Other | 1,110 |
| Withdrawn | 879 |
| Further information | 258 |
| (blank) | 198 |

### Most common raw values
| Decision | Applications |
|---|---|
| Grant Permission | 20,959 |
| Refuse Permission | 3,904 |
| Grant Permission for Retention | 1,845 |
| Invalid - Site Notice | 1,049 |
| Grant Permission & Grant Retention | 736 |
| Declared Exempt | 629 |
| Declared Withdrawn | 455 |
| Withdraw the Application | 419 |
| Declared Not Exempt | 378 |
| Grant Extension of Duration of Permission | 370 |
| Refuse Permission for Retention | 337 |
| Invalid Application | 312 |
| Invalidate Application | 265 |
| Request Additional Information | 241 |
|  | 198 |

### Application status (top 15)
| Status | Applications |
|---|---|
| Decision | 24,536 |
| Appeal decided | 2,658 |
| Final Grant | 2,479 |
| Officer Allocation | 1,880 |
| Decision Following A.I. | 595 |
| Registered Application | 251 |
| Unregistered application | 186 |
| Invalid Application | 170 |
|  | 86 |
| Invalid - Site Notice | 79 |
| Referral | 64 |
| Application under appeal | 57 |
| AI Requested | 47 |
| Pre-Reg | 45 |
| Decision Request A.I. | 34 |

### Application type (top 15)
| Type | Applications |
|---|---|
| Permission | 27,120 |
| Retention | 2,534 |
| Declaration of Exemption Sect. 5 | 1,149 |
| Permission and Retention | 1,008 |
| Extension Of Duration Of Permission | 474 |
| Outline Permission | 349 |
| SDZ Application | 250 |
| Application Under Part 8 | 204 |
| SHD3-Application to ABP | 49 |
| Approval | 47 |
| Further Extension of Duration of Permission | 46 |
| Perm. following Grant of Outline Perm. | 29 |
| SDZ Application Clonburris | 13 |
| Section 179A Social Housing Exemption | 8 |
| LRD3-Application | 8 |

## Residential units
- Applications with units > 0: 5,706
- Units blank or zero: 27,598
- Description mentions homes but units blank/zero: **8,981**
- Total units recorded: 87,946; largest single application: 1,144

## Date logic checks
- Decision date before received date: 20
- Grant date after expiry date: 262

## Description length (characters)
count: 33,304, mean: 277, std: 392, min: 4, 25%: 94, 50%: 171, 75%: 303, max: 11,193

## Sample descriptions mentioning homes (Sprint 3 extraction test set)
| Application | Units field | Description |
|---|---|---|
| SD18B/0521 | nan | (a) Ground floor kitchen extension of 20sq.m; (b) first floor extension of 39sq.m to provide an additional bedroom with walk-in wardrobe and bathroom; total area of extension to house is 59sq.m. |
| SD03A/0538 | 1.0 | Building of private dwelling in side garden and rearrangement of existing entrance to accommodate proposed development. |
| SD09A/0096 | 1.0 | 2 storey, 2-bed detached house to side garden with shared access and associated works; demolish existing shed. |
| SD21B/0408 | nan | Two storey extension to the rear with an extended area at ground floor to the kitchen / dining room area; a first floor extension to side over the existing ground floor along with alterations to the roof to extend to the back, side and front of the house with a new dormer window and rooflight to the back of the house |
| SD17B/0211 | nan | Retention of separate existing single storey structure/studio comprising 40sq.m. to rear of existing house. |
| SD26B/0164W | nan | Vehicular entrance driveway with gate to front of existing house, including dishing of public footpath and associated site works. |
| SD228/0001 | nan | 118 residential units made up of houses, duplexes, triplexes, an apartment building, landscape works, total site area approx. 2.5 ha (net). The works comprise: 11 Three-bed houses 11 Four-bed houses 25 Duplex Units comprising 2 units each (i.e. – 50 units) 9 3 stacked simplexes comprising 3 units each (i.e. – 27 units) A 4 storey Apartment building comprising 19 Apartments 112 parking spaces, 24 v |
| SD12A/0048 | nan | Construct a new GIS (Gas Insulated Switchgear) 110kV electricity substation and to carry out ancillary site works: (1) all necessary site works for construction of a concrete compound area to the southwest of the existing ADSIL facility; (2) construction of an ESB GIS substation control building within the fenced compound area; (3) construction of a client control building and a transformer bay to |
| SD20B/0290 | nan | Extensions and alterations to an existing two storey semi-detached dwelling comprising of a two storey extension to the side, a part single storey pitched roof extension the rear; internal alterations; elevational alterations which include enlarged roof lights to the existing single storey roof pitch to the rear; all associated site & landscaping works. The proposed works result in an increase of  |
| SD06A/0624 | 1.0 | (a) Construction of new 3 bedroom 2 storey house attached to side of existing house; (b) new boundary wall of 1.8m in height to rear of new proposed house; (c) one new additional car parking space; (d) block up existing side window at ground floor level. |
| SD20B/0299 | nan | Construction of a new single storey, side extension to the house and include 1 rooflight. Works also include all associated site works. |
| SD21A/0121 | 2.0 | Construction of 2 two and a half storey, three-bedroom terrace houses and associated site works attached to the existing two and a half storey house at No. 6 Station Grove which was constructed in 2006; the 2 houses will complete this partially finished housing development which was originally granted permission under planning reference SD05A/0125. |
| SD19A/0225 | 4.0 | Change of use of the first floor from offices in No. 43 and restaurant in No. 44 to 3 two bedroom apartments and 1 one bedroom apartment and an interconnecting doorway between the two existing ground floor shop at No. 43 and the takeaway food shop at No. 44 Tower Road; new stone-clad shopfront with an aluminium glazing system and signage in the fascia over each unit. |
| SD09B/0064 | nan | Two storey extension over existing store to the side and a single storey extension to the rear of dwelling house. |
| SD21B/0092 | nan | Remove existing porch and replace with a new single storey garage to front of house; relocate front entrance door to side of new build and all associated site works. |
| SD13B/0203 | nan | Replace flat roof to front of house with apex tiled roof. |
| S00B/0373 | 0.0 | Construct a single storey flat roof extension to the rear and side of existing two storey house. |
| SD11B/0150 | nan | Ground and first floor level extensions to front; ground and first floor extension to side, including joining of existing detached garage to side to main house and alteration of roof over existing garage; ground and first floor level extensions to rear; alteration and extension of main roof pitch and profile, including 3 new dormers to rear, new bay at front and new flat roof central portion; conv |
| SD22B/0289 | nan | Erection of Solar Panels to the front and rear of the main pitched roof to the main house at 8 Larkfield Green, Ballyowen, Lucan, Co Dublin. |
| SD11B/0037 | nan | Construction of a single storey extension to the rear of the existing two storey dwelling. |

## Top 5 quality issues
_Written up in docs/data-profile.md._
