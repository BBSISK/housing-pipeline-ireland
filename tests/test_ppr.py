"""Offline tests for the PPR profiler, using a tiny fake register in the real file format."""

import zipfile

import pytest

from housing_pipeline import ppr

HEADER = (
    "Date of Sale (dd/mm/yyyy),Address,County,Eircode,Price (€),"
    "Not Full Market Price,VAT Exclusive,Description of Property,Property Size Description\r\n"
)
ROWS = [
    '01/02/2024,"12 Main Street, Lucan",Dublin,,"€350,000.00",No,No,Second-Hand Dwelling house /Apartment,',
    '15/06/2024,"APT 4 THE GREEN TALLAGHT",Dublin,D24X123,"€295,000.00",No,No,Second-Hand Dwelling house /Apartment,',
    '20/09/2025,"5 Oak Road, Ranelagh",Dublin,,"€6,250,000.00",No,No,Second-Hand Dwelling house /Apartment,',
    '03/03/2025,"Site 3, Ballymore",Westmeath,,"€8,000.00",Yes,No,Second-Hand Dwelling house /Apartment,',
    '10/10/2025,"7 New Lane, Adamstown, Lucan",Dublin,,"€400,000.00",No,Yes,New Dwelling house /Apartment,greater than or equal to 38 sq metres and less than 125 sq metres',
    '01/02/2024,"12 Main Street, Lucan",Dublin,,"€350,000.00",No,No,Second-Hand Dwelling house /Apartment,',
]


@pytest.fixture
def fake_zip(tmp_path):
    csv_bytes = (HEADER + "\r\n".join(ROWS) + "\r\n").encode("cp1252")
    path = tmp_path / "PPR-ALL.zip"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("PPR-ALL.csv", csv_bytes)
    return path


def test_parse_price_handles_euro_and_commas():
    assert ppr.parse_price("€343,000.00") == 343000.0
    assert ppr.parse_price("\x80343,000.00") == 343000.0
    assert ppr.parse_price("") is None
    assert ppr.parse_price("n/a") is None


def test_read_register_normalises_columns_and_types(fake_zip):
    df = ppr.read_register(fake_zip)
    for col in ["date_of_sale", "address", "county", "eircode", "price", "sale_date", "vat_exclusive"]:
        assert col in df.columns
    assert len(df) == 6
    assert df["price"].max() == 6_250_000.0
    assert df["sale_date"].notna().all()


def test_profile_counts_quality_issues(fake_zip):
    p = ppr.profile(ppr.read_register(fake_zip))
    assert p["rows"] == 6
    assert p["under_10k"] == 1
    assert p["over_5m"] == 1
    assert p["not_full_market_price"] == 1
    assert p["vat_exclusive"] == 1
    assert p["exact_duplicate_rows"] == 1
    assert p["dublin_rows"] == 5
    assert p["south_dublin_keyword_rows"] == 4  # two Lucan rows (one a duplicate), Tallaght, Adamstown
    assert p["blank_rate"]["eircode"] == pytest.approx(5 / 6, abs=1e-3)
    assert "APT 4 THE GREEN TALLAGHT" in p["messy_address_samples"]


def test_render_markdown_has_sections(fake_zip):
    md = ppr.render_markdown(ppr.profile(ppr.read_register(fake_zip)), "PPR-ALL.zip")
    for heading in ["## Size and coverage", "## Completeness", "## Prices", "## Top 5 quality issues"]:
        assert heading in md


def test_read_register_rejects_zip_without_single_csv(tmp_path):
    path = tmp_path / "bad.zip"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("readme.txt", "nothing here")
    with pytest.raises(ValueError):
        ppr.read_register(path)
