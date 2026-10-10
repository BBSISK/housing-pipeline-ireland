"""National Planning Applications: download one council to bronze, and profile it.

Usage (from the repo root, venv active):

    python -m housing_pipeline.planning download
    python -m housing_pipeline.planning profile

`download` pages through the Department of Housing's ArcGIS feature service for the
pilot council and saves the raw records to bronze/planning/<today>/south-dublin.json.
`profile` reads the newest file and writes docs/planning-profile.md.

Data minimisation: applicant names and applicant addresses are personal data and are
never requested from the service, so they never reach bronze. Only the fields in
FIELDS are downloaded.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
from typing import Callable

import pandas as pd

from housing_pipeline.sources import PILOT_AREA

SERVICE = (
    "https://services.arcgis.com/NzlPQPKn5QF9v2US/arcgis/rest/services/"
    "IrishPlanningApplications/FeatureServer/0/query"
)
REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
BRONZE = REPO_ROOT / "bronze" / "planning"
PAGE_SIZE = 2000
ITM_WKID = 2157  # Irish Transverse Mercator

# Everything we need, and nothing personal. ApplicantForename, ApplicantSurname and
# ApplicantAddress are deliberately left out.
FIELDS = [
    "OBJECTID", "PlanningAuthority", "ApplicationNumber", "DevelopmentDescription",
    "DevelopmentAddress", "DevelopmentPostcode", "ITMEasting", "ITMNorthing",
    "ApplicationStatus", "ApplicationType", "Decision", "LandUseCode", "AreaofSite",
    "NumResidentialUnits", "OneOffHouse", "FloorArea", "ReceivedDate", "WithdrawnDate",
    "DecisionDate", "DecisionDueDate", "GrantDate", "ExpiryDate", "AppealRefNumber",
    "AppealStatus", "AppealDecision", "AppealDecisionDate", "LinkAppDetails", "ETL_DATE",
]
PERSONAL_FIELDS = {"ApplicantForename", "ApplicantSurname", "ApplicantAddress"}
DATE_FIELDS = [f for f in FIELDS if f.endswith("Date") or f == "ETL_DATE"]

# Rough bounding box for the Republic of Ireland in Irish Transverse Mercator (EPSG:2157).
ITM_BOUNDS = {"easting": (410_000, 770_000), "northing": (510_000, 970_000)}

# Words that suggest homes are involved, to compare against the NumResidentialUnits field.
HOUSING_WORDS = re.compile(r"\b(?:dwellings?|houses?|apartments?|residential units?|duplex(?:es)?)\b", re.I)


def fetch_page(params: dict) -> dict:
    import requests

    response = requests.get(SERVICE, params=params, timeout=120)
    response.raise_for_status()
    payload = response.json()
    if "error" in payload:
        raise RuntimeError(f"ArcGIS error: {payload['error']}")
    return payload


def download_records(authority: str = PILOT_AREA, fetch: Callable[[dict], dict] = fetch_page) -> list[dict]:
    """Page through the service until it stops saying there is more."""
    records: list[dict] = []
    offset = 0
    while True:
        params = {
            "where": f"PlanningAuthority='{authority}'",
            "outFields": ",".join(FIELDS),
            # The ITMEasting/ITMNorthing attribute columns are blank for some councils
            # (all of South Dublin), so ask for the point geometry, projected to ITM.
            "returnGeometry": "true",
            "outSR": ITM_WKID,
            "orderByFields": "OBJECTID",
            "resultOffset": offset,
            "resultRecordCount": PAGE_SIZE,
            "f": "json",
        }
        page = fetch(params)
        features = page.get("features", [])
        records.extend(with_geometry(f) for f in features)
        if not features or not page.get("exceededTransferLimit"):
            break
        offset += len(features)
    leaked = PERSONAL_FIELDS & {k for r in records for k in r}
    if leaked:
        raise RuntimeError(f"Personal fields returned by the service: {sorted(leaked)}")
    return records


def with_geometry(feature: dict) -> dict:
    """Attributes plus the point geometry (already in ITM) as GeomEasting/GeomNorthing."""
    record = dict(feature["attributes"])
    geometry = feature.get("geometry") or {}
    record["GeomEasting"] = geometry.get("x")
    record["GeomNorthing"] = geometry.get("y")
    return record


def download(force: bool = False) -> pathlib.Path:
    target_dir = BRONZE / dt.date.today().isoformat()
    target = target_dir / "south-dublin.json"
    if target.exists() and not force:
        print(f"Already downloaded today: {target}")
        return target
    records = download_records()
    target_dir.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(records), encoding="utf-8")
    print(f"Saved {len(records):,} applications to {target}")
    return target


def to_frame(records: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame.from_records(records)
    for col in DATE_FIELDS:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], unit="ms", errors="coerce")
    return df


def blank(series: pd.Series) -> pd.Series:
    return series.isna() | (series.astype(str).str.strip() == "")


def decision_group(value: object) -> str:
    """Collapse the many free-text decision values into a few groups."""
    text = str(value or "").lower()
    if not text.strip() or text == "none":
        return "(blank)"
    if "refus" in text:
        return "Refused"
    if "grant" in text or "permission" in text or "approv" in text:
        return "Granted"
    if "withdraw" in text:
        return "Withdrawn"
    if "invalid" in text:
        return "Invalid"
    if "further information" in text or "additional information" in text:
        return "Further information"
    return "Other"


def profile(df: pd.DataFrame) -> dict:
    received = df["ReceivedDate"]
    attr_missing = df["ITMEasting"].isna() | df["ITMNorthing"].isna() | (df["ITMEasting"] == 0)
    # Prefer the attribute columns; fall back to the service geometry (requested in ITM).
    east = df["ITMEasting"].where(~attr_missing, df.get("GeomEasting"))
    north = df["ITMNorthing"].where(~attr_missing, df.get("GeomNorthing"))
    coords_missing = east.isna() | north.isna() | (east == 0) | (north == 0)
    out_of_bounds = ~coords_missing & ~(
        east.between(*ITM_BOUNDS["easting"]) & north.between(*ITM_BOUNDS["northing"])
    )
    units = pd.to_numeric(df["NumResidentialUnits"], errors="coerce")
    desc = df["DevelopmentDescription"].fillna("")
    mentions_housing = desc.str.contains(HOUSING_WORDS)

    return {
        "rows": len(df),
        "received_min": received.min(),
        "received_max": received.max(),
        "received_blank": int(received.isna().sum()),
        "rows_by_year": received.dt.year.value_counts().sort_index().to_dict(),
        "blank_rate": {c: round(float(blank(df[c]).mean()), 4) for c in FIELDS if c in df.columns},
        "status_values": df["ApplicationStatus"].fillna("(blank)").value_counts().head(15).to_dict(),
        "type_values": df["ApplicationType"].fillna("(blank)").value_counts().head(15).to_dict(),
        "decision_distinct": int(df["Decision"].nunique()),
        "decision_groups": df["Decision"].map(decision_group).value_counts().to_dict(),
        "decision_top": df["Decision"].fillna("(blank)").value_counts().head(15).to_dict(),
        "coords_attr_missing": int(attr_missing.sum()),
        "coords_missing": int(coords_missing.sum()),
        "coords_out_of_bounds": int(out_of_bounds.sum()),
        "units_present": int((units > 0).sum()),
        "units_zero_or_blank": int((units.isna() | (units == 0)).sum()),
        "units_max": units.max(),
        "units_total": units.sum(),
        "housing_words_but_no_units": int((mentions_housing & (units.isna() | (units == 0))).sum()),
        "duplicate_application_numbers": int(df["ApplicationNumber"].duplicated().sum()),
        "description_length": desc.str.len().describe().round(0).to_dict(),
        "grant_after_expiry": int((df["GrantDate"] > df["ExpiryDate"]).sum()),
        "decision_before_received": int((df["DecisionDate"] < df["ReceivedDate"]).sum()),
        "sample_descriptions": sample_descriptions(df),
    }


def sample_descriptions(df: pd.DataFrame, n: int = 20) -> list[dict]:
    """Descriptions that mention housing, for the Sprint 3 extraction test set."""
    desc = df["DevelopmentDescription"].fillna("")
    candidates = df[desc.str.contains(HOUSING_WORDS)]
    if candidates.empty:
        return []
    picked = candidates.sample(n=min(n, len(candidates)), random_state=42)
    return [
        {
            "application": r.ApplicationNumber,
            "units_field": r.NumResidentialUnits,
            "description": " ".join(str(r.DevelopmentDescription).split())[:400],
        }
        for r in picked.itertuples()
    ]


def render_markdown(p: dict, source_file: str) -> str:
    def table(d: dict, a: str, b: str) -> list[str]:
        return [f"| {a} | {b} |", "|---|---|", *[f"| {k} | {v:,} |" for k, v in d.items()]]

    lines = [
        f"# National Planning Applications — {PILOT_AREA} — data profile (HOUSE-9)",
        "",
        f"Source file: `{source_file}`  ",
        f"Profiled: {dt.date.today().isoformat()}  ",
        "Personal fields (applicant name and address) are excluded at download.",
        "",
        "## Size and coverage",
        f"- Applications: **{p['rows']:,}**",
        f"- Received: {p['received_min']:%d %b %Y} to {p['received_max']:%d %b %Y} ({p['received_blank']} blank)",
        f"- Duplicate application numbers: {p['duplicate_application_numbers']:,}",
        "",
        "### Applications by year received",
        *table({int(k): v for k, v in p["rows_by_year"].items()}, "Year", "Applications"),
        "",
        "## Completeness (share of blank values)",
        "| Field | Blank |",
        "|---|---|",
        *[f"| {c} | {r:.1%} |" for c, r in p["blank_rate"].items()],
        "",
        "## Location",
        f"- ITMEasting/ITMNorthing attribute columns blank: {p['coords_attr_missing']:,}",
        f"- No location at all (attributes and service geometry both missing): {p['coords_missing']:,}",
        f"- Coordinates outside Ireland's ITM bounds: {p['coords_out_of_bounds']:,}",
        "",
        "## Decisions",
        f"- Distinct free-text decision values: **{p['decision_distinct']:,}**",
        "",
        "### Grouped",
        *table(p["decision_groups"], "Group", "Applications"),
        "",
        "### Most common raw values",
        *table(p["decision_top"], "Decision", "Applications"),
        "",
        "### Application status (top 15)",
        *table(p["status_values"], "Status", "Applications"),
        "",
        "### Application type (top 15)",
        *table(p["type_values"], "Type", "Applications"),
        "",
        "## Residential units",
        f"- Applications with units > 0: {p['units_present']:,}",
        f"- Units blank or zero: {p['units_zero_or_blank']:,}",
        f"- Description mentions homes but units blank/zero: **{p['housing_words_but_no_units']:,}**",
        f"- Total units recorded: {p['units_total']:,.0f}; largest single application: {p['units_max']:,.0f}",
        "",
        "## Date logic checks",
        f"- Decision date before received date: {p['decision_before_received']:,}",
        f"- Grant date after expiry date: {p['grant_after_expiry']:,}",
        "",
        "## Description length (characters)",
        ", ".join(f"{k}: {v:,.0f}" for k, v in p["description_length"].items()),
        "",
        "## Sample descriptions mentioning homes (Sprint 3 extraction test set)",
        "| Application | Units field | Description |",
        "|---|---|---|",
        *[
            f"| {s['application']} | {s['units_field']} | {s['description'].replace('|', '/')} |"
            for s in p["sample_descriptions"]
        ],
        "",
        "## Top 5 quality issues",
        "_Written up in docs/data-profile.md._",
        "",
    ]
    return "\n".join(lines)


def newest_bronze_file() -> pathlib.Path:
    files = sorted(BRONZE.glob("*/south-dublin.json"))
    if not files:
        raise FileNotFoundError("No planning file in bronze/planning/. Run the download step first.")
    return files[-1]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    dl = sub.add_parser("download")
    dl.add_argument("--force", action="store_true", help="Download again even if today's file exists")
    prof = sub.add_parser("profile")
    prof.add_argument("--file", type=pathlib.Path, help="Profile this JSON file instead of the newest bronze one")
    args = parser.parse_args(argv)

    if args.command == "download":
        download(force=args.force)
        return

    path = args.file.expanduser() if args.file else newest_bronze_file()
    df = to_frame(json.loads(path.read_text(encoding="utf-8")))
    out = REPO_ROOT / "docs" / "planning-profile.md"
    out.write_text(render_markdown(profile(df), path.name), encoding="utf-8")
    print(f"Profiled {len(df):,} applications -> {out}")


if __name__ == "__main__":
    main()
