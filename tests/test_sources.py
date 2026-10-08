from housing_pipeline.sources import PILOT_AREA, SOURCES


def test_three_sources_defined():
    assert set(SOURCES) == {"ppr", "planning", "pqs"}


def test_every_source_has_licence_and_cadence():
    for source in SOURCES.values():
        assert source.licence
        assert source.cadence_days > 0
        assert source.url.startswith("https://")


def test_pilot_area_is_south_dublin():
    assert PILOT_AREA == "South Dublin County Council"
