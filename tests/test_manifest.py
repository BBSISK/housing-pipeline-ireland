"""Offline tests for the bronze manifest: immutability, hashing, row counts, verify and freshness."""

import datetime as dt
import json
import zipfile

from housing_pipeline import manifest


def write_json(path, items):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(items), encoding="utf-8")
    return path


def test_run_dir_never_returns_an_existing_folder(tmp_path):
    day = dt.date(2026, 10, 11)
    first = manifest.run_dir(tmp_path, today=day)
    assert first.name == "2026-10-11"
    first.mkdir()
    second = manifest.run_dir(tmp_path, today=day, now=dt.datetime(2026, 10, 11, 21, 30, 5))
    assert second.name == "2026-10-11_213005"
    assert sorted([first.name, second.name])[-1] == second.name  # newest sorts last


def test_count_rows_json_and_zip(tmp_path):
    assert manifest.count_rows(write_json(tmp_path / "a.json", [1, 2, 3])) == 3
    z = tmp_path / "PPR-ALL.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("PPR-ALL.csv", 'Date,Address\r\n01/01/2024,"1 Main St, Lucan"\r\n02/01/2024,"2 Main St"\r\n'.encode("cp1252"))
    assert manifest.count_rows(z) == 2


def test_record_appends_once_with_hash_and_rows(tmp_path):
    m = tmp_path / "bronze" / "manifest.csv"
    f = write_json(tmp_path / "bronze" / "planning" / "2026-10-10" / "south-dublin.json", [{"a": 1}, {"a": 2}])
    manifest.record("planning", "https://example.ie", f, 2, manifest=m, root=tmp_path)
    manifest.record("planning", "https://example.ie", f, 2, manifest=m, root=tmp_path)  # same file again
    rows = manifest.read_manifest(m)
    assert len(rows) == 1
    assert rows[0]["file"] == "bronze/planning/2026-10-10/south-dublin.json"
    assert rows[0]["rows"] == "2"
    assert rows[0]["sha256"] == manifest.sha256(f)


def test_same_as_previous_detects_unchanged_source(tmp_path):
    m = tmp_path / "manifest.csv"
    a = write_json(tmp_path / "pqs" / "2026-10-10" / "questions.json", [1, 2])
    b = write_json(tmp_path / "pqs" / "2026-10-11" / "questions.json", [1, 2])
    manifest.record("pqs", "u", a, 2, manifest=m, root=tmp_path)
    assert manifest.same_as_previous("pqs", "questions.json", manifest.sha256(b), m) == "pqs/2026-10-10/questions.json"
    assert manifest.same_as_previous("pqs", "members.json", manifest.sha256(b), m) is None


def test_verify_flags_changed_and_missing(tmp_path):
    m = tmp_path / "manifest.csv"
    keep = write_json(tmp_path / "ppr" / "d1" / "x.json", [1])
    tamper = write_json(tmp_path / "ppr" / "d2" / "x.json", [1])
    gone = write_json(tmp_path / "ppr" / "d3" / "x.json", [1])
    for f in (keep, tamper, gone):
        manifest.record("ppr", "u", f, 1, manifest=m, root=tmp_path)
    tamper.write_text("[1, 2]")
    gone.unlink()
    result = manifest.verify(m, root=tmp_path)
    assert result["ok"] == 1
    assert result["changed"] == ["ppr/d2/x.json"]
    assert result["missing"] == ["ppr/d3/x.json"]


def test_backfill_registers_existing_files(tmp_path):
    bronze = tmp_path / "bronze"
    m = bronze / "manifest.csv"
    write_json(bronze / "planning" / "2026-10-10" / "south-dublin.json", [{}, {}, {}])
    write_json(bronze / "pqs" / "2026-10-11" / "questions.json", [{}])
    write_json(bronze / "pqs" / "2026-10-11" / "members.json", [{}, {}])
    assert manifest.backfill(bronze, m, tmp_path) == 3
    assert manifest.backfill(bronze, m, tmp_path) == 0  # idempotent
    rows = {r["file"]: r["rows"] for r in manifest.read_manifest(m)}
    assert rows["bronze/planning/2026-10-10/south-dublin.json"] == "3"


def test_status_compares_age_with_cadence(tmp_path):
    m = tmp_path / "manifest.csv"
    f = write_json(tmp_path / "pqs" / "d" / "questions.json", [1])
    landed = dt.datetime(2026, 10, 1, tzinfo=dt.timezone.utc)
    manifest.record("pqs", "u", f, 1, manifest=m, root=tmp_path, landed_at=landed)
    report = {s["source"]: s for s in manifest.status(m, now=dt.datetime(2026, 10, 11, tzinfo=dt.timezone.utc))}
    assert report["pqs"]["fresh"] is False      # daily source, 10 days old
    assert report["pqs"]["age_days"] == 10.0
    assert report["ppr"]["last"] is None        # never landed
