"""The three public data sources, in one place.

Each source records where it comes from, how often it changes, and its licence,
so ingestion code, freshness checks and the README all read from one definition.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Source:
    key: str
    name: str
    publisher: str
    url: str
    cadence_days: int  # expected refresh interval, used by freshness checks
    licence: str


SOURCES: dict[str, Source] = {
    "ppr": Source(
        key="ppr",
        name="Residential Property Price Register",
        publisher="Property Services Regulatory Authority (PSRA)",
        url="https://www.propertypriceregister.ie/",
        cadence_days=7,
        licence="PSRA terms of use (public register; attribution to PSRA)",
    ),
    "planning": Source(
        key="planning",
        name="National Planning Applications",
        publisher="Department of Housing, Local Government and Heritage",
        url="https://data.gov.ie/dataset/national-planning-applications",
        cadence_days=7,
        licence="CC BY 4.0",
    ),
    "pqs": Source(
        key="pqs",
        name="Oireachtas parliamentary questions",
        publisher="Houses of the Oireachtas",
        url="https://api.oireachtas.ie/",
        cadence_days=1,
        licence="Oireachtas (Open Data) PSI Licence",
    ),
}

PILOT_AREA = "South Dublin County Council"
