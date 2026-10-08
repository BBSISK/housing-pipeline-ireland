# Housing Pipeline Ireland

**Where is housing being planned in Ireland, what actually sells, at what price — and what are TDs asking about it?**

A data pipeline that joins three public Irish data sources that were never designed to fit together,
then exposes the result to AI agents through an MCP server.

> Status: **Sprint 1 — ingestion foundations** (started 8 Oct 2026). Pilot area: South Dublin County Council.

## Sources

| Source | Publisher | Refresh | Licence |
|---|---|---|---|
| [Residential Property Price Register](https://www.propertypriceregister.ie/) | PSRA | Weekly | PSRA terms; attribution to PSRA |
| [National Planning Applications](https://data.gov.ie/dataset/national-planning-applications) | Dept of Housing, Local Government and Heritage | Weekly | CC BY 4.0 |
| [Oireachtas parliamentary questions](https://api.oireachtas.ie/) | Houses of the Oireachtas | Daily | Oireachtas (Open Data) PSI Licence |

Contains Irish public sector data licensed under the terms above. Raw data is not stored in this repo;
only download manifests (source, timestamp, row count, file hash) are committed.

## The hard problem

Property sales have free-text addresses and no coordinates or Eircodes. Planning applications have
coordinates (Irish Transverse Mercator) and free-text descriptions. Linking "permission granted here"
to "homes later sold here" means geocoding, coordinate conversion, text extraction and fuzzy matching —
each with a measured confidence, and uncertain matches routed for review rather than trusted.

## Architecture (planned)

1. **Ingest** — scheduled Azure Functions land raw files, unchanged, in Blob Storage (bronze)
2. **Clean** — validation rules; rejected rows logged with the rule that failed (silver)
3. **Enrich** — Azure Maps geocoding; ITM → WGS84; LLM extraction of unit counts, scored against a hand-labelled set
4. **Match** — planning permissions to later sales, by distance and time, with confidence scores
5. **Model** — star schema in SQL, hand-written queries
6. **Quality** — SPC control charts on load volumes and area prices; freshness checks per source
7. **MCP server** — read-only tools over the modelled data
8. **Agents** — Q&A agent grounded only in MCP tools; weekly housing brief
9. **Evaluation** — answers checked against SQL ground truth

## Security

Keyless from the first commit. No API keys or passwords anywhere:

| Where code runs | Signs in as |
|---|---|
| Laptop | `az login` |
| GitHub Actions | GitHub OIDC (federated credential) |
| Azure Functions | System-assigned managed identity |

Key-based access is switched off on every Azure resource, roles are least-privilege and defined in
Terraform, and a test (`tests/test_no_keys.py`) fails if any module reads a key-style setting.

## Delivery

Scrum in Jira (project HOUSE), two-week sprints. One branch per story (`HOUSE-12-...`), commit messages
start with the Jira key, every change goes through a pull request with green CI.

## Run the tests

```
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest -q
```
