"""The bronze manifest: one line per raw file landed, so every download is traceable.

Usage (from the repo root, venv active):

    python -m housing_pipeline.manifest backfill   # register files already in bronze/
    python -m housing_pipeline.manifest verify     # recompute hashes; flag changed or missing files
    python -m housing_pipeline.manifest status     # freshness per source vs its expected cadence

bronze/manifest.csv is the only file under bronze/ that git tracks. It records, for every raw
file: when it landed, which source, the URL it came from, its path, size, SHA-256 hash and row
count. Raw files are never overwritten: a forced re-download goes into a new run folder.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import pathlib
import zipfile

from housing_pipeline.sources import SOURCES

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
BRONZE_ROOT = REPO_ROOT / "bronze"
MANIFEST = BRONZE_ROOT / "manifest.csv"
COLUMNS = ["landed_at_utc", "source", "url", "file", "bytes", "sha256", "rows"]


# ---------- run folders: immutable by construction ----------

def run_dir(source_root: pathlib.Path, today: dt.date | None = None, now: dt.datetime | None = None) -> pathlib.Path:
    """bronze/<source>/<YYYY-MM-DD>/, or <YYYY-MM-DD>_<HHMMSS>/ if today's folder already exists.

    Never returns an existing folder, so a re-download can never overwrite raw data.
    Folder names sort in time order, so 'newest' is always the last one.
    """
    today = today or dt.date.today()
    candidate = source_root / today.isoformat()
    if not candidate.exists():
        return candidate
    now = now or dt.datetime.now()
    return source_root / f"{today.isoformat()}_{now:%H%M%S}"


def today_dir(source_root: pathlib.Path, today: dt.date | None = None) -> pathlib.Path | None:
    """Today's first run folder if it exists (used to skip a duplicate download)."""
    candidate = source_root / (today or dt.date.today()).isoformat()
    return candidate if candidate.exists() else None


# ---------- hashing and row counts ----------

def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def count_rows(path: pathlib.Path) -> int | None:
    """Rows in a raw file: CSV lines inside a ZIP (minus header), or items in a JSON list."""
    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as zf:
            names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
            if len(names) != 1:
                return None
            text = io.TextIOWrapper(zf.open(names[0]), encoding="cp1252", newline="")
            return max(sum(1 for _ in csv.reader(text)) - 1, 0)
    if path.suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        return len(data) if isinstance(data, list) else None
    return None


# ---------- the manifest itself ----------

def read_manifest(manifest: pathlib.Path = MANIFEST) -> list[dict]:
    if not manifest.exists():
        return []
    with manifest.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def record(source: str, url: str, path: pathlib.Path, rows: int | None = None,
           manifest: pathlib.Path = MANIFEST, root: pathlib.Path = REPO_ROOT,
           landed_at: dt.datetime | None = None) -> dict:
    """Append one line for a newly landed file. A file already recorded is not added twice."""
    relative = path.resolve().relative_to(root.resolve()).as_posix()
    existing = {r["file"] for r in read_manifest(manifest)}
    entry = {
        "landed_at_utc": (landed_at or dt.datetime.now(dt.timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": source,
        "url": url,
        "file": relative,
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "rows": "" if rows is None else rows,
    }
    if relative in existing:
        return entry
    manifest.parent.mkdir(parents=True, exist_ok=True)
    new_file = not manifest.exists()
    with manifest.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        if new_file:
            writer.writeheader()
        writer.writerow(entry)
    return entry


def same_as_previous(source: str, filename: str, digest: str, manifest: pathlib.Path = MANIFEST) -> str | None:
    """If the newest earlier file of this name from this source has the same hash, return its path."""
    earlier = [r for r in read_manifest(manifest)
               if r["source"] == source and pathlib.PurePosixPath(r["file"]).name == filename]
    if earlier and earlier[-1]["sha256"] == digest:
        return earlier[-1]["file"]
    return None


def report_landing(source: str, url: str, path: pathlib.Path, manifest: pathlib.Path = MANIFEST,
                   root: pathlib.Path = REPO_ROOT) -> dict:
    """Record a newly landed file and say whether the source has changed since last time."""
    digest = sha256(path)
    previous = same_as_previous(source, path.name, digest, manifest)
    entry = record(source, url, path, count_rows(path), manifest, root)
    print(f"Saved {int(entry['bytes']):,} bytes, {entry['rows']} rows to {path}")
    print(f"Recorded in bronze/manifest.csv (sha256 {digest[:12]}...)")
    if previous:
        print(f"Note: identical to the previous download ({previous}); the source hasn't changed.")
    return entry


# Which files in each source folder are raw data, and where they came from.
RAW_FILES = {
    "ppr": {"PPR-ALL.zip": "ppr"},
    "planning": {"south-dublin.json": "planning"},
    "pqs": {"questions.json": "pqs", "members.json": "pqs"},
}


def backfill(bronze_root: pathlib.Path = BRONZE_ROOT, manifest: pathlib.Path = MANIFEST,
             root: pathlib.Path = REPO_ROOT) -> int:
    """Register raw files already on disk that the manifest doesn't know about."""
    known = {r["file"] for r in read_manifest(manifest)}
    added = 0
    for folder, files in RAW_FILES.items():
        for name, source in files.items():
            for path in sorted((bronze_root / folder).glob(f"*/{name}")):
                relative = path.resolve().relative_to(root.resolve()).as_posix()
                if relative in known:
                    continue
                landed = dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc)
                record(source, SOURCES[source].url, path, count_rows(path), manifest, root, landed)
                added += 1
    return added


def verify(manifest: pathlib.Path = MANIFEST, root: pathlib.Path = REPO_ROOT) -> dict:
    """Recompute every hash. Raw data must never change after landing."""
    result = {"ok": 0, "changed": [], "missing": []}
    for row in read_manifest(manifest):
        path = root / row["file"]
        if not path.exists():
            result["missing"].append(row["file"])
        elif sha256(path) != row["sha256"]:
            result["changed"].append(row["file"])
        else:
            result["ok"] += 1
    return result


def status(manifest: pathlib.Path = MANIFEST, now: dt.datetime | None = None) -> list[dict]:
    """Freshness: last landing per source compared with its expected cadence."""
    now = now or dt.datetime.now(dt.timezone.utc)
    rows = read_manifest(manifest)
    report = []
    for key, source in SOURCES.items():
        landed = [r["landed_at_utc"] for r in rows if r["source"] == key]
        if not landed:
            report.append({"source": key, "last": None, "age_days": None, "cadence_days": source.cadence_days, "fresh": False})
            continue
        last = dt.datetime.strptime(max(landed), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
        age = (now - last).total_seconds() / 86400
        report.append({"source": key, "last": max(landed), "age_days": round(age, 1),
                       "cadence_days": source.cadence_days, "fresh": age <= source.cadence_days})
    return report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["backfill", "verify", "status"])
    args = parser.parse_args(argv)

    if args.command == "backfill":
        print(f"Added {backfill()} file(s) to {MANIFEST.relative_to(REPO_ROOT)}")
    elif args.command == "verify":
        r = verify()
        print(f"Unchanged: {r['ok']}  Changed: {len(r['changed'])}  Missing: {len(r['missing'])}")
        for f in r["changed"]:
            print(f"  CHANGED  {f}")
        for f in r["missing"]:
            print(f"  MISSING  {f}")
        if r["changed"]:
            raise SystemExit(1)
    else:
        for s in status():
            flag = "fresh" if s["fresh"] else "STALE"
            last = s["last"] or "never"
            age = "" if s["age_days"] is None else f"{s['age_days']} days ago, "
            print(f"{s['source']:<9} {flag:<6} last landed {last} ({age}expected every {s['cadence_days']} day(s))")


if __name__ == "__main__":
    main()
