# Data profile — Sprint 1

One section per source: what was pulled, when, and the top 5 quality issues, each with
evidence from the data and a proposed fix. The full generated numbers for each source
are in their own profile file (e.g. `docs/ppr-profile.md`).

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
_To do._

## Oireachtas housing PQs, last 30 days (HOUSE-10)
_To do._
