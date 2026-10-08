"""Property Price Register (PPR): download to bronze and profile.

Usage (from the repo root, venv active):

    python -m housing_pipeline.ppr download
    python -m housing_pipeline.ppr profile

`download` saves the full register ZIP, unchanged, to bronze/ppr/<today>/.
`profile` reads the newest ZIP in bronze/ppr/ and writes docs/ppr-profile.md.

If the automatic download fails (the PSRA site can be slow or change its link),
download "Download All" manually from https://www.propertypriceregister.ie/ and run:

    python -m housing_pipeline.ppr profile --file ~/Downloads/PPR-ALL.zip
"""

from __future__ import annotations

import argparse
import datetime as dt
import io
import pathlib
import re
import zipfile

import pandas as pd

DOWNLOAD_URL = (
    "https://www.propertypriceregister.ie/website/npsra/ppr/npsra-ppr.nsf/"
    "Downloads/PPR-ALL.zip/$FILE/PPR-ALL.zip"
)
REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
BRONZE = REPO_ROOT / "bronze" / "ppr"

# The register's own headers are long and contain symbols, so map them to short names.
# Matching is on the start of the header, because the exact wording has varied over the years.
COLUMN_PREFIXES = {
    "date of sale": "date_of_sale",
    "address": "address",
    "county": "county",
    "eircode": "eircode",
    "price": "price_raw",
    "not full market price": "not_full_market_price",
    "vat exclusive": "vat_exclusive",
    "description of property": "description",
    "property size description": "size_description",
}

# First-pass keyword list for South Dublin County Council areas. The register records
# only the county, not the council, so this is a rough filter for profiling only.
# Sprint 3 replaces it with geocoding plus the council boundary.
SOUTH_DUBLIN_KEYWORDS = [
    "lucan", "adamstown", "clondalkin", "tallaght", "jobstown", "citywest",
    "saggart", "rathcoole", "newcastle", "brittas", "rathfarnham", "templeogue",
    "firhouse", "knocklyon", "ballyboden", "ballyroan", "palmerstown",
    "kingswood", "greenhills", "kilnamanagh", "perrystown", "ballyfermot",
]


def normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename = {}
    for col in df.columns:
        key = col.strip().lower()
        for prefix, short in COLUMN_PREFIXES.items():
            if key.startswith(prefix):
                rename[col] = short
                break
    return df.rename(columns=rename)


def parse_price(value: object) -> float | None:
    """'€343,000.00' (or a mis-decoded euro sign) -> 343000.0. Unparseable -> None."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    digits = re.sub(r"[^0-9.]", "", str(value))
    if not digits or digits.count(".") > 1:
        return None
    return float(digits)


def read_register(zip_path: pathlib.Path) -> pd.DataFrame:
    """Read the CSV inside the PPR ZIP. The file is Windows-1252, not UTF-8."""
    with zipfile.ZipFile(zip_path) as zf:
        csv_names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if len(csv_names) != 1:
            raise ValueError(f"Expected one CSV in {zip_path.name}, found {csv_names}")
        raw = zf.read(csv_names[0])
    df = pd.read_csv(io.BytesIO(raw), encoding="cp1252", dtype=str, keep_default_na=False)
    df = normalise_columns(df)
    df["price"] = df["price_raw"].map(parse_price)
    df["sale_date"] = pd.to_datetime(df["date_of_sale"], format="%d/%m/%Y", errors="coerce")
    return df


def blank(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip() == ""


def profile(df: pd.DataFrame) -> dict:
    prices = df["price"].dropna()
    dublin = df[df["county"].str.strip().str.lower() == "dublin"]
    pattern = "|".join(SOUTH_DUBLIN_KEYWORDS)
    south_dublin = dublin[dublin["address"].str.lower().str.contains(pattern, regex=True)]

    return {
        "rows": len(df),
        "date_min": df["sale_date"].min(),
        "date_max": df["sale_date"].max(),
        "unparseable_dates": int(df["sale_date"].isna().sum()),
        "rows_by_year": df["sale_date"].dt.year.value_counts().sort_index().to_dict(),
        "rows_by_county": df["county"].value_counts().to_dict(),
        "blank_rate": {
            col: round(float(blank(df[col]).mean()), 4)
            for col in COLUMN_PREFIXES.values()
            if col in df.columns
        },
        "unparseable_prices": int(df["price"].isna().sum()),
        "price_stats": {
            "min": prices.min(),
            "p01": prices.quantile(0.01),
            "median": prices.median(),
            "p99": prices.quantile(0.99),
            "max": prices.max(),
        },
        "under_10k": int((prices < 10_000).sum()),
        "over_5m": int((prices > 5_000_000).sum()),
        "not_full_market_price": int((df["not_full_market_price"].str.strip().str.lower() == "yes").sum()),
        "vat_exclusive": int((df["vat_exclusive"].str.strip().str.lower() == "yes").sum()),
        "description_values": df["description"].value_counts().to_dict(),
        "exact_duplicate_rows": int(df.duplicated(subset=list(COLUMN_PREFIXES.values())[:-1]).sum()),
        "dublin_rows": len(dublin),
        "south_dublin_keyword_rows": len(south_dublin),
        "messy_address_samples": messy_addresses(df),
    }


def messy_addresses(df: pd.DataFrame, n: int = 10) -> list[str]:
    """Addresses that will be hard to geocode: no comma, all caps, very short, or with apartment prefixes."""
    addr = df["address"].astype(str)
    flags = (
        ~addr.str.contains(",")
        | (addr == addr.str.upper())
        | (addr.str.len() < 15)
        | addr.str.lower().str.contains(r"\bapt\b|\bapartment\b|\bno\.?\s*\d", regex=True)
    )
    return addr[flags].drop_duplicates().head(n).tolist()


def render_markdown(p: dict, source_file: str) -> str:
    def fmt_money(x: float) -> str:
        return f"€{x:,.0f}"

    lines = [
        "# Property Price Register — data profile (HOUSE-8)",
        "",
        f"Source file: `{source_file}`  ",
        f"Profiled: {dt.date.today().isoformat()}",
        "",
        "## Size and coverage",
        f"- Rows: **{p['rows']:,}**",
        f"- Sale dates: {p['date_min']:%d %b %Y} to {p['date_max']:%d %b %Y}"
        f" ({p['unparseable_dates']} unparseable)",
        f"- Dublin rows: {p['dublin_rows']:,}; South Dublin by keyword (rough): {p['south_dublin_keyword_rows']:,}",
        "",
        "### Rows by year",
        "| Year | Rows |",
        "|---|---|",
        *[f"| {int(y)} | {n:,} |" for y, n in p["rows_by_year"].items()],
        "",
        "### Rows by county",
        "| County | Rows |",
        "|---|---|",
        *[f"| {c} | {n:,} |" for c, n in p["rows_by_county"].items()],
        "",
        "## Completeness (share of blank values)",
        "| Column | Blank |",
        "|---|---|",
        *[f"| {c} | {r:.1%} |" for c, r in p["blank_rate"].items()],
        "",
        "## Prices",
        f"- Unparseable: {p['unparseable_prices']}",
        "- " + ", ".join(f"{k}: {fmt_money(v)}" for k, v in p["price_stats"].items()),
        f"- Under €10,000: {p['under_10k']:,}; over €5m: {p['over_5m']:,}",
        f"- Flagged 'not full market price': {p['not_full_market_price']:,}",
        f"- VAT exclusive (new builds, price excludes 13.5% VAT): {p['vat_exclusive']:,}",
        "",
        "## Property description values",
        "| Value | Rows |",
        "|---|---|",
        *[f"| {v} | {n:,} |" for v, n in p["description_values"].items()],
        "",
        f"## Exact duplicate rows: {p['exact_duplicate_rows']:,}",
        "",
        "## Messy address samples (kept for Sprint 3 normalisation tests)",
        *[f"- `{a}`" for a in p["messy_address_samples"]],
        "",
        "## Top 5 quality issues",
        "_Write these up after reading the numbers above: issue, example, proposed fix._",
        "",
    ]
    return "\n".join(lines)


def download(url: str = DOWNLOAD_URL) -> pathlib.Path:
    import requests

    target_dir = BRONZE / dt.date.today().isoformat()
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "PPR-ALL.zip"
    if target.exists():
        print(f"Already downloaded today: {target}")
        return target
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    target.write_bytes(response.content)
    print(f"Saved {len(response.content):,} bytes to {target}")
    return target


def newest_bronze_zip() -> pathlib.Path:
    zips = sorted(BRONZE.glob("*/PPR-ALL.zip"))
    if not zips:
        raise FileNotFoundError("No PPR ZIP in bronze/ppr/. Run the download step first, or pass --file.")
    return zips[-1]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("download")
    prof = sub.add_parser("profile")
    prof.add_argument("--file", type=pathlib.Path, help="Profile this ZIP instead of the newest bronze one")
    args = parser.parse_args(argv)

    if args.command == "download":
        download()
        return

    zip_path = args.file.expanduser() if args.file else newest_bronze_zip()
    df = read_register(zip_path)
    report = render_markdown(profile(df), zip_path.name)
    out = REPO_ROOT / "docs" / "ppr-profile.md"
    out.write_text(report, encoding="utf-8")
    print(f"Profiled {len(df):,} rows -> {out}")


if __name__ == "__main__":
    main()
