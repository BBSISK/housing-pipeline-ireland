"""Offline tests for the planning downloader and profiler, using a fake ArcGIS service."""

import pytest

from housing_pipeline import planning

MS_2024_01_10 = 1704844800000
MS_2024_03_01 = 1709251200000
MS_2023_12_01 = 1701388800000


def record(i, **overrides):
    base = {
        "OBJECTID": i,
        "PlanningAuthority": "South Dublin County Council",
        "ApplicationNumber": f"SD24A/{i:04d}",
        "DevelopmentDescription": "Single storey extension to rear",
        "DevelopmentAddress": f"{i} Main Street, Lucan",
        "DevelopmentPostcode": None,
        "ITMEasting": 702000.0,
        "ITMNorthing": 735000.0,
        "ApplicationStatus": "DECISION MADE",
        "ApplicationType": "PERMISSION",
        "Decision": "GRANT PERMISSION",
        "NumResidentialUnits": 0,
        "ReceivedDate": MS_2024_01_10,
        "DecisionDate": MS_2024_03_01,
        "GrantDate": MS_2024_03_01,
        "ExpiryDate": None,
    }
    base.update(overrides)
    return base


def fake_service(pages):
    calls = []

    def fetch(params):
        calls.append(params)
        return pages[len(calls) - 1]

    return fetch, calls


def test_download_pages_until_no_more():
    pages = [
        {"features": [{"attributes": record(1)}, {"attributes": record(2)}], "exceededTransferLimit": True},
        {"features": [{"attributes": record(3)}]},
    ]
    fetch, calls = fake_service(pages)
    records = planning.download_records(fetch=fetch)
    assert len(records) == 3
    assert [c["resultOffset"] for c in calls] == [0, 2]
    assert "South Dublin County Council" in calls[0]["where"]
    assert calls[0]["returnGeometry"] == "true"
    assert calls[0]["outSR"] == 2157


def test_download_copies_geometry_into_record():
    blank_attrs = record(1, ITMEasting=None, ITMNorthing=None)
    feature = {"attributes": blank_attrs, "geometry": {"x": 703500.0, "y": 734200.0}}
    fetch, _ = fake_service([{"features": [feature]}])
    [rec] = planning.download_records(fetch=fetch)
    assert rec["GeomEasting"] == 703500.0
    assert rec["GeomNorthing"] == 734200.0


def test_profile_falls_back_to_geometry_when_itm_columns_blank():
    records = [
        record(1, ITMEasting=None, ITMNorthing=None, GeomEasting=703500.0, GeomNorthing=734200.0),
        record(2, ITMEasting=None, ITMNorthing=None, GeomEasting=None, GeomNorthing=None),
    ]
    p = planning.profile(planning.to_frame(records))
    assert p["coords_attr_missing"] == 2
    assert p["coords_missing"] == 1


def test_download_never_requests_personal_fields():
    for field in planning.PERSONAL_FIELDS:
        assert field not in planning.FIELDS


def test_download_fails_if_service_returns_personal_fields():
    leaked = record(1, ApplicantSurname="Murphy")
    fetch, _ = fake_service([{"features": [{"attributes": leaked}]}])
    with pytest.raises(RuntimeError, match="Personal fields"):
        planning.download_records(fetch=fetch)


@pytest.mark.parametrize(
    "raw, group",
    [
        ("GRANT PERMISSION", "Granted"),
        ("Grant Permission & Grant Retention", "Granted"),
        ("REFUSE PERMISSION", "Refused"),
        ("Request Additional Information", "Further information"),
        ("APPLICATION WITHDRAWN", "Withdrawn"),
        ("Invalid Application", "Invalid"),
        (None, "(blank)"),
        ("Split decision", "Other"),
    ],
)
def test_decision_group(raw, group):
    assert planning.decision_group(raw) == group


def test_profile_finds_quality_issues():
    records = [
        record(1),
        record(2, DevelopmentDescription="Construction of 42 no. residential units", NumResidentialUnits=None),
        record(3, DevelopmentDescription="Demolition and 12 apartments", NumResidentialUnits=12),
        record(4, ITMEasting=0, ITMNorthing=0),
        record(5, ITMEasting=150000.0),
        record(6, ApplicationNumber="SD24A/0001"),
        record(7, DecisionDate=MS_2023_12_01, Decision="REFUSE PERMISSION"),
    ]
    p = planning.profile(planning.to_frame(records))
    assert p["rows"] == 7
    assert p["coords_missing"] == 1
    assert p["coords_out_of_bounds"] == 1
    assert p["units_present"] == 1
    assert p["housing_words_but_no_units"] == 1
    assert p["duplicate_application_numbers"] == 1
    assert p["decision_before_received"] == 1
    assert p["decision_groups"]["Granted"] == 6
    assert p["decision_groups"]["Refused"] == 1
    assert len(p["sample_descriptions"]) == 2


def test_render_markdown_has_sections():
    df = planning.to_frame([record(1), record(2, DevelopmentDescription="Two houses")])
    md = planning.render_markdown(planning.profile(df), "south-dublin.json")
    for heading in ["## Size and coverage", "## Completeness", "## Decisions", "## Residential units", "excluded at download"]:
        assert heading in md
