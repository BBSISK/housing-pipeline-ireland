"""Upload bronze files to Azure Blob Storage, keyless.

Usage (from the repo root, venv active, after `az login`):

    python -m housing_pipeline.cloud upload --account <storage account name>

Every file in bronze/manifest.csv is uploaded to the `bronze` container at the same path
(without the leading "bronze/"), with its SHA-256 and row count as blob metadata. A blob that
already exists with the same hash is skipped, so re-running is safe and cheap. Nothing is ever
overwritten with different content: a hash mismatch stops the upload.

Sign-in is DefaultAzureCredential: your `az login` on the laptop, a managed identity in Azure.
There is no key or connection string anywhere.
"""

from __future__ import annotations

import argparse
import pathlib
from dataclasses import dataclass

from housing_pipeline import manifest

CONTAINER = "bronze"


@dataclass
class Planned:
    local: pathlib.Path
    blob: str
    sha256: str
    rows: str
    action: str  # "upload" | "skip" | "conflict" | "missing"


def blob_name(manifest_path: str) -> str:
    """bronze/ppr/2026-10-08/PPR-ALL.zip -> ppr/2026-10-08/PPR-ALL.zip"""
    prefix = "bronze/"
    if not manifest_path.startswith(prefix):
        raise ValueError(f"Not a bronze file: {manifest_path}")
    return manifest_path[len(prefix):]


def plan(rows: list[dict], existing: dict[str, str | None], root: pathlib.Path = manifest.REPO_ROOT) -> list[Planned]:
    """Decide what to do with each manifest row.

    `existing` maps blob name -> its stored sha256 metadata (None if the blob has none).
    """
    out = []
    for row in rows:
        local = root / row["file"]
        name = blob_name(row["file"])
        if not local.exists():
            action = "missing"
        elif name not in existing:
            action = "upload"
        elif existing[name] == row["sha256"]:
            action = "skip"
        else:
            action = "conflict"
        out.append(Planned(local, name, row["sha256"], row.get("rows", ""), action))
    return out


def container_client(account: str):
    from azure.identity import DefaultAzureCredential
    from azure.storage.blob import BlobServiceClient

    service = BlobServiceClient(f"https://{account}.blob.core.windows.net", credential=DefaultAzureCredential())
    return service.get_container_client(CONTAINER)


def existing_hashes(container) -> dict[str, str | None]:
    return {b.name: (b.metadata or {}).get("sha256") for b in container.list_blobs(include=["metadata"])}


def upload(account: str, container=None, rows: list[dict] | None = None,
           root: pathlib.Path = manifest.REPO_ROOT) -> dict:
    container = container or container_client(account)
    rows = manifest.read_manifest() if rows is None else rows
    planned = plan(rows, existing_hashes(container), root=root)
    conflicts = [p.blob for p in planned if p.action == "conflict"]
    if conflicts:
        raise RuntimeError(f"Blob already exists with different content (bronze must never change): {conflicts}")
    for p in planned:
        if p.action == "upload":
            with p.local.open("rb") as data:
                container.upload_blob(p.blob, data, overwrite=False,
                                      metadata={"sha256": p.sha256, "rows": str(p.rows)})
            print(f"uploaded  {p.blob}")
        elif p.action == "skip":
            print(f"unchanged {p.blob}")
        else:
            print(f"MISSING   {p.local} (in manifest, not on disk)")
    return {a: sum(1 for p in planned if p.action == a) for a in ("upload", "skip", "missing")}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    up = sub.add_parser("upload")
    up.add_argument("--account", required=True, help="Storage account name (terraform output storage_account)")
    args = parser.parse_args(argv)
    counts = upload(args.account)
    print(f"Uploaded {counts['upload']}, unchanged {counts['skip']}, missing locally {counts['missing']}")


if __name__ == "__main__":
    main()
