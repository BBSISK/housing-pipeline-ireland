# Data profile — Sprint 1 (8–22 Oct 2026)

Three public Irish sources, landed raw in `bronze/`, recorded in `bronze/manifest.csv` with SHA-256
hashes, and profiled before anything is built on them. Dashboard: *Housing Pipeline Ireland*
(Claude artifact, linked from the README).

## Summary

| Source | Rows | Covers | Biggest finding |
|---|---|---|---|
| Property Price Register (PSRA) | 810,390 sales | Jan 2010 – 2 Oct 2026, all counties | No Eircode on 68.8%; geography stops at county |
| National Planning Applications (South Dublin) | 33,304 applications | 1992 – 30 Sep 2026 | Coordinate columns 100% blank; fixed via service geometry |
| Oireachtas parliamentary questions | 5,420 questions (349 to Housing) | 16 Sep – 8 Oct 2026 | Department is not the topic; constituencies don't match councils |

**15 quality issues** logged below (5 per source): **2 fixed** in Sprint 1, **10 planned** against
existing stories, **3 need new stories** (PQ topic classification, constituency-to-council overlap,
redaction handling).

**What it means for the design**
- Joining sources needs geocoding and coordinate conversion; neither Eircode nor council is reliable.
- Official fields can't be trusted alone (units, decision): LLM extraction must be scored against
  hand-labelled test sets.
- All three sources file late, so the most recent weeks are incomplete; control charts must allow for it.
- Personal data is excluded at download (planning applicants) and redactions are flagged (PQs).

## Property Price Register (HOUSE-8)

**Pulled:** 8 Oct 2026, full register (`PPR-ALL.zip`, 19.2 MB) → `bronze/ppr/2026-10-08/`
**Size:** 810,390 sales, 1 Jan 2010 – 2 Oct 2026, all 26 counties. Dublin 253,994; South Dublin (rough keyword filter) 40,773.
**Full profile:** [`ppr-profile.md`](ppr-profile.md)

### Top 5 quality issues

**1. No reliable location key.**
Eircode is blank on 68.8% of sales, there are no coordinates, and geography stops at county:
the register cannot say which sales are in South Dublin County Council. Addresses are free
text, typed by conveyancers and never corrected: `33 RAGIAN ROAD, BALLSBRIDGE` (Raglan Road),
`No. 11, Charlotte Quay` (no town or area).
*Fix:* normalise addresses (Sprint 3), geocode them with Azure Maps and keep a confidence
score, treat a present Eircode as the highest-confidence location, and assign council area
from the boundary, not from keywords.

**2. Prices that are not market prices.**
41,283 sales (5.1%) are flagged "not full market price". The price range runs from €5,001 to
€387,665,198; 1,056 sales are over €5m and 1,100 are under €10,000. The very large values look
like bulk or portfolio sales filed as one transaction, so one price covers many homes.
*Fix:* exclude "not full market price" sales from price statistics; flag likely bulk sales
(very high price, and the same date and development across several rows); report medians,
not means; use control limits per area to catch the rest.

**3. New-build prices exclude VAT.**
142,876 sales are VAT-exclusive, almost all of the 145,255 new dwellings. A €400,000 new
build is really about €454,000 to the buyer, so mixing new and second-hand prices understates
new homes. About 2,400 new dwellings are *not* marked VAT-exclusive, which needs checking.
*Fix:* keep the flag, add a VAT-inclusive price (×1.135) for comparisons, and analyse new and
second-hand sales separately.

**4. Duplicate rows.**
1,085 rows exactly match another row on date, address, county, price and flags. Some will be
double filings, but some may be real: several units in one development sold the same day at
the same price under one address.
*Fix:* never drop silently. Flag duplicates, keep them in the reject log with the reason, and
check a sample by hand before choosing a rule.

**5. Inconsistent categories and text encoding.**
The property description has Irish-language versions of the two English categories (49 rows),
and one is corrupted: `Teach/?ras?n C?naithe Nua`. The file is Windows-1252, not UTF-8, so
reading it with the wrong encoding damages fadas.
*Fix:* map every description value to two categories (new / second-hand), read the file
explicitly as cp1252, and add a test that fails on any unmapped value.

### Also noted
- **Property size is 93.5% blank**, so it can't be used for price-per-square-metre analysis.
- **Recent months are undercounted.** Sales are filed weeks or months after they happen, so
  2026 (42,011 so far) and especially the last few months will keep growing. Load-volume
  control charts must allow for this lag, or every recent month will look "out of control".

## National Planning Applications — South Dublin County Council (HOUSE-9)

**Pulled:** 10 Oct 2026 from the Department of Housing's ArcGIS feature service → `bronze/planning/2026-10-10/`
**Size:** 33,304 applications received 1992 – 30 Sep 2026 (reliable from 1999; 7–21 a year before 1998).
**Personal data:** applicant names and addresses are never requested, and a test fails if the service returns them.
**Full profile:** [`planning-profile.md`](planning-profile.md)

### Top 5 quality issues

**1. The coordinate columns are empty.**
`ITMEasting` and `ITMNorthing` are blank on 100% of South Dublin records, and `LandUseCode` is 100%
blank too. The data dictionary promises fields this council doesn't fill. The location does exist,
but only in the map service's point geometry.
*Fix (done, 10 Oct):* the downloader now requests the geometry projected to ITM (EPSG:2157) and
uses it when the columns are blank. Re-profiled: **0 of 33,304 applications have no location, and
0 fall outside Ireland's ITM bounds.** Found by profiling, not by reading the documentation.

**2. The residential units field can't be trusted on its own.**
`NumResidentialUnits` is blank on 67.4% of applications. It misses big schemes: `SD228/0001`
describes 118 homes but has no units recorded. A keyword search is no better: 8,981 descriptions
mention homes with no units recorded, but most are extensions to an existing "house", not new homes.
*Fix:* this is exactly the case for LLM extraction (HOUSE-20): read the description, return new units
and type, and score it against a hand-labelled test set. Use the field where present as a cross-check.

**3. Not every "grant" is new housing.**
Decisions are free text with 62 distinct values. They group cleanly (24,270 granted, 4,963 refused,
1,626 invalid), but "granted" includes 370 extensions of duration, which re-grant an existing
permission, and 1,845 retention permissions for work already built. 629 "Declared Exempt" are
Section 5 declarations, not permissions at all.
*Fix:* classify by application type *and* decision. Count a scheme's homes once: link extensions of
duration back to the original application rather than counting them as new supply.

**4. Big schemes may be decided elsewhere.**
49 applications are "SHD3 – Application to ABP": large Strategic Housing Developments decided by
An Bord Pleanála, not the council. These are exactly the big schemes that matter most, and the
council record may not carry the final decision or unit count.
*Fix:* flag SHD and LRD applications, check a sample against An Bord Pleanála's records, and treat
their decision and units as needing confirmation.

**5. Date logic errors and an unfinished picture.**
20 applications were decided before they were received, 262 have a grant date after their expiry
date, 35 have no received date, and one application number appears twice. About 2,500 applications
have an in-progress status (officer allocation, registered, further information requested). Some
are recent, some may be old records never updated, so check by received date.
*Fix:* date-order validation rules that log failures with the rule that failed; never treat an
in-progress application as refused; re-load weekly and track decisions as they change.

### Also noted
- **Eircode** (`DevelopmentPostcode`) is blank on 91.6% of applications, so it can't be used to join
  planning to sales directly, which confirms the PPR finding.
- **Applications per year** fell from about 1,980 in 2006–07 to about 670 in 2012, and have been
  roughly 1,000–1,175 a year since 2019. That's the housing cycle visible in the data.

## Oireachtas housing PQs, last 30 days (HOUSE-10)

**Pulled:** 11 Oct 2026 from the Oireachtas API (open, no key) → `bronze/pqs/2026-10-11/`: every oral and
written question plus the 176 members of the 34th Dáil (for constituencies).
**Size:** 5,420 questions dated 16 Sep – 8 Oct 2026; **349 (6.4%) addressed to Housing**, 337 written and 12 oral.
All 349 matched to a constituency, with no duplicates and no blank text.
**Full profile:** [`pqs-profile.md`](pqs-profile.md)

### Top 5 quality issues

**1. The department is not the topic.**
The API labels the department "Housing", but the full title is Housing, Local Government *and Heritage*.
The sample includes questions about heritage tourism funding and onshore wind planning guidance, alongside
real housing questions (Traveller accommodation, unspent development contributions, defective blocks).
*Fix:* classify each question's topic (housing supply, social/affordable, planning, defects, heritage,
other) with an LLM, score it against a hand-labelled set, and keep only housing topics downstream.

**2. Geography is by constituency, not place, and the boundaries don't match councils.**
No housing question in the window named a South Dublin place, yet Dublin Mid-West TDs asked 17. TDs
represent constituencies, and constituency boundaries don't line up with council boundaries: South
Dublin County Council is split across more than one constituency.
*Fix:* a constituency-to-council overlap table, plus place extraction from the text, so a question can
be tied to the pilot area either by who asked or by what it names.

**3. Boilerplate in every question.**
Every question starts with its order-paper number (`356.`) and ends with a PQ reference (`[66495/26]`).
My first profile counted "questions containing a figure" as 349 of 349, which was meaningless: it was
catching the boilerplate. Some questions also refer back to earlier ones ("further to Parliamentary
Question Nos. PQ61112/26").
*Fix (done):* strip the number and reference before analysing text, with tests. Re-profiled: **119 of
349 (34%)** contain a real figure (amounts, years, unit counts), which is the useful number. Keep the PQ reference
as its own field, and use the "further to" references to link follow-up questions into threads.

**4. Volume follows the Dáil calendar, not public interest.**
Housing questions per week went 95 → 45 → 174 → 35. The window asked for 30 days but only contains
16 Sep – 8 Oct: questions only exist on sitting days, and the newest appear a few days after they are
asked.
*Fix:* count per sitting week, not per calendar week, before putting PQ volume on a control chart, and
treat the latest few days as incomplete (the same late-filing lag as the Property Price Register).

**5. Redactions and concentration.**
41 housing questions (12%) contain "(details supplied)": a person or property is removed, so those can't
be tied to a place. Volume is also concentrated: the top three TDs asked 61 of 349 (17%), and one
constituency (Dún Laoghaire) leads with 39.
*Fix:* keep redacted questions but flag them as unlocatable; report "number of TDs asking" alongside raw
counts, so one active TD doesn't look like a regional surge.
