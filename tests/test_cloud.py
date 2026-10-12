"""Offline tests for the keyless bronze upload, using a fake container (no Azure, no credentials)."""

import pytest

from housing_pipeline import cloud, manifest


class FakeBlob:
    def __init__(self, name, metadata):
        self.name, self.metadata = name, metadata


class FakeContainer:
    def __init__(self, existing=None):
        self.blobs = dict(existing or {})
        self.uploads = []

    def list_blobs(self, include=None):
        return [FakeBlob(n, {"sha256": h}) for n, h in self.blobs.items()]

    def upload_blob(self, name, data, overwrite, metadata):
        assert overwrite is False
        self.uploads.append((name, data.read(), metadata))
        self.blobs[name] = metadata["sha256"]


def test_blob_name_strips_bronze_prefix():
    assert cloud.blob_name("bronze/ppr/2026-10-08/PPR-ALL.zip") == "ppr/2026-10-08/PPR-ALL.zip"
    with pytest.raises(ValueError):
        cloud.blob_name("docs/data-profile.md")


def test_plan_upload_skip_conflict_missing(tmp_path):
    for p in ["bronze/a/1.json", "bronze/b/2.json", "bronze/c/3.json"]:
        (tmp_path / p).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / p).write_text("[]")
    rows = [
        {"file": "bronze/a/1.json", "sha256": "h1", "rows": "0"},  # new
        {"file": "bronze/b/2.json", "sha256": "h2", "rows": "0"},  # same hash already there
        {"file": "bronze/c/3.json", "sha256": "h3", "rows": "0"},  # different content already there
        {"file": "bronze/d/4.json", "sha256": "h4", "rows": "0"},  # not on disk
    ]
    actions = {p.blob: p.action for p in cloud.plan(rows, {"b/2.json": "h2", "c/3.json": "OTHER"}, root=tmp_path)}
    assert actions == {"a/1.json": "upload", "b/2.json": "skip", "c/3.json": "conflict", "d/4.json": "missing"}


def landed(tmp_path, rel, text, source="pqs"):
    f = tmp_path / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text)
    m = tmp_path / "bronze" / "manifest.csv"
    manifest.record(source, "u", f, len(text), manifest=m, root=tmp_path)
    return f, manifest.read_manifest(m)


def test_upload_writes_hash_metadata_and_is_idempotent(tmp_path):
    f, rows = landed(tmp_path, "bronze/pqs/2026-10-11/questions.json", "[1, 2]")
    container = FakeContainer()
    assert cloud.upload("acct", container, rows, tmp_path) == {"upload": 1, "skip": 0, "missing": 0}
    name, _, meta = container.uploads[0]
    assert name == "pqs/2026-10-11/questions.json"
    assert meta["sha256"] == manifest.sha256(f)
    assert cloud.upload("acct", container, rows, tmp_path) == {"upload": 0, "skip": 1, "missing": 0}


def test_upload_refuses_to_change_existing_bronze(tmp_path):
    _, rows = landed(tmp_path, "bronze/ppr/d/x.json", "[1]", source="ppr")
    container = FakeContainer({"ppr/d/x.json": "something-else"})
    with pytest.raises(RuntimeError, match="must never change"):
        cloud.upload("acct", container, rows, tmp_path)
    assert container.uploads == []
