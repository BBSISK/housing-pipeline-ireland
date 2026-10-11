"""Oireachtas parliamentary questions (PQs): download to bronze and profile the housing ones.

Usage (from the repo root, venv active):

    python -m housing_pipeline.pqs download            # last 30 days
    python -m housing_pipeline.pqs download --days 60
    python -m housing_pipeline.pqs profile

`download` saves every oral and written question in the window, plus the current Dáil
members list (for constituencies), to bronze/pqs/<today>/. Nothing is filtered at download:
bronze is the raw record. `profile` keeps questions addressed to the housing department and
writes docs/pqs-profile.md.

The API is open (no key): https://api.oireachtas.ie/
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
from typing import Callable

import pandas as pd

from housing_pipeline.ppr import SOUTH_DUBLIN_KEYWORDS

API = "https://api.oireachtas.ie/v1"
REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
BRONZE = REPO_ROOT / "bronze" / "pqs"
PAGE_SIZE = 500
CURRENT_DAIL = 34  # elected November 2024

# Questions are addressed to a department by a short name, e.g. "Housing".
HOUSING_DEPARTMENT = re.compile(r"housing", re.I)
DETAILS_SUPPLIED = re.compile(r"details supplied", re.I)
NUMBER = re.compile(r"\b\d[\d,]*\b")
# Every question starts with its order-paper number ("356. ") and ends with a PQ
# reference ("[66495/26]"). Strip both before looking for figures or places.
LEADING_NUMBER = re.compile(r"^\s*\d+\.\s*")
PQ_REFERENCE = re.compile(r"\s*\[\d+/\d+\]\s*$")


def clean_text(text: str) -> str:
    return PQ_REFERENCE.sub("", LEADING_NUMBER.sub("", str(text or "")))


def fetch_json(path: str, params: dict) -> dict:
    import requests

    response = requests.get(f"{API}/{path}", params=params, timeout=120)
    response.raise_for_status()
    return response.json()


def download_questions(start: dt.date, end: dt.date, fetch: Callable[[str, dict], dict] = fetch_json) -> list[dict]:
    """Page through /questions with limit/skip until a short page comes back."""
    results: list[dict] = []
    skip = 0
    while True:
        page = fetch(
            "questions",
            {
                "date_start": start.isoformat(),
                "date_end": end.isoformat(),
                "qtype": "oral,written",
                "limit": PAGE_SIZE,
                "skip": skip,
            },
        )
        batch = page.get("results", [])
        results.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        skip += PAGE_SIZE
    return results


def download_members(fetch: Callable[[str, dict], dict] = fetch_json) -> list[dict]:
    page = fetch("members", {"chamber": "dail", "house_no": CURRENT_DAIL, "limit": 500})
    return page.get("results", [])


def download(days: int = 30, force: bool = False) -> pathlib.Path:
    today = dt.date.today()
    target_dir = BRONZE / today.isoformat()
    questions_file = target_dir / "questions.json"
    if questions_file.exists() and not force:
        print(f"Already downloaded today: {questions_file}")
        return target_dir
    questions = download_questions(today - dt.timedelta(days=days), today)
    members = download_members()
    target_dir.mkdir(parents=True, exist_ok=True)
    questions_file.write_text(json.dumps(questions), encoding="utf-8")
    (target_dir / "members.json").write_text(json.dumps(members), encoding="utf-8")
    print(f"Saved {len(questions):,} questions and {len(members)} members to {target_dir}")
    return target_dir


def flatten_questions(results: list[dict]) -> pd.DataFrame:
    rows = []
    for item in results:
        q = item.get("question", {})
        by = q.get("by") or {}
        to = q.get("to") or {}
        rows.append(
            {
                "uri": q.get("uri"),
                "date": q.get("date"),
                "question_type": q.get("questionType"),
                "question_number": q.get("questionNumber"),
                "member_code": by.get("memberCode"),
                "member": by.get("showAs"),
                "department": to.get("showAs"),
                "text": q.get("showAs") or "",
                "debate_section": (q.get("debateSection") or {}).get("showAs"),
            }
        )
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


def member_constituencies(members: list[dict]) -> dict[str, str]:
    """memberCode -> constituency name, from each member's Dáil membership."""
    lookup: dict[str, str] = {}
    for item in members:
        member = item.get("member", {})
        code = member.get("memberCode")
        for m in member.get("memberships", []):
            membership = m.get("membership", {})
            for r in membership.get("represents", []):
                rep = r.get("represent", {})
                if rep.get("representType") == "constituency" and code:
                    lookup[code] = rep.get("showAs")
    return lookup


def profile(questions: pd.DataFrame, constituencies: dict[str, str]) -> dict:
    housing = questions[questions["department"].fillna("").str.contains(HOUSING_DEPARTMENT)].copy()
    housing["constituency"] = housing["member_code"].map(constituencies)
    housing["body"] = housing["text"].map(clean_text)
    text = housing["body"].str.lower()
    place_pattern = r"\b(?:" + "|".join(SOUTH_DUBLIN_KEYWORDS + ["south dublin"]) + r")\b"
    mentions_sd = text.str.contains(place_pattern, regex=True)

    return {
        "rows": len(questions),
        "date_min": questions["date"].min(),
        "date_max": questions["date"].max(),
        "departments": questions["department"].fillna("(blank)").value_counts().head(25).to_dict(),
        "department_distinct": int(questions["department"].nunique()),
        "housing_rows": len(housing),
        "housing_share": len(housing) / len(questions) if len(questions) else 0,
        "housing_types": housing["question_type"].value_counts().to_dict(),
        "housing_by_week": housing["date"].dt.to_period("W").astype(str).value_counts().sort_index().to_dict(),
        "top_members": housing["member"].value_counts().head(15).to_dict(),
        "top_constituencies": housing["constituency"].fillna("(not matched)").value_counts().head(15).to_dict(),
        "constituency_unmatched": int(housing["constituency"].isna().sum()),
        "blank_text": int((housing["text"].str.strip() == "").sum()),
        "duplicate_uris": int(questions["uri"].duplicated().sum()),
        "details_supplied": int(housing["text"].str.contains(DETAILS_SUPPLIED).sum()),
        "with_numbers": int(housing["body"].str.contains(NUMBER).sum()),
        "with_pq_reference": int(housing["text"].str.contains(PQ_REFERENCE).sum()),
        "south_dublin_mentions": int(mentions_sd.sum()),
        "south_dublin_samples": housing[mentions_sd]["text"].head(5).tolist(),
        "text_length": housing["text"].str.len().describe().round(0).to_dict(),
        "samples": housing.sample(n=min(10, len(housing)), random_state=42)[["date", "member", "text"]].to_dict("records")
        if len(housing)
        else [],
    }


def render_markdown(p: dict, source_dir: str) -> str:
    def table(d: dict, a: str, b: str) -> list[str]:
        return [f"| {a} | {b} |", "|---|---|", *[f"| {k} | {v:,} |" for k, v in d.items()]]

    def clean(s: str, n: int = 300) -> str:
        return " ".join(str(s).split())[:n].replace("|", "/")

    lines = [
        "# Oireachtas parliamentary questions — housing — data profile (HOUSE-10)",
        "",
        f"Source: `{source_dir}`  ",
        f"Profiled: {dt.date.today().isoformat()}",
        "",
        "## Size and coverage",
        f"- All questions in window: **{p['rows']:,}** ({p['date_min']:%d %b %Y} to {p['date_max']:%d %b %Y})",
        f"- Addressed to housing: **{p['housing_rows']:,}** ({p['housing_share']:.1%})",
        f"- Duplicate question URIs: {p['duplicate_uris']:,}",
        "",
        f"### Departments (top 25 of {p['department_distinct']})",
        *table(p["departments"], "Department", "Questions"),
        "",
        "### Housing questions by type",
        *table(p["housing_types"], "Type", "Questions"),
        "",
        "### Housing questions by week",
        *table(p["housing_by_week"], "Week", "Questions"),
        "",
        "## Who asks",
        "### Top 15 TDs",
        *table(p["top_members"], "TD", "Questions"),
        "",
        "### Top 15 constituencies",
        *table(p["top_constituencies"], "Constituency", "Questions"),
        "",
        f"- Questions whose TD couldn't be matched to a constituency: {p['constituency_unmatched']:,}",
        "",
        "## Text",
        f"- Blank question text: {p['blank_text']:,}",
        f"- Contain '(details supplied)' redactions: {p['details_supplied']:,}",
        f"- End with a PQ reference like [66495/26]: {p['with_pq_reference']:,}",
        f"- Contain a figure once the question number and PQ reference are removed: {p['with_numbers']:,}",
        f"- Mention a South Dublin place: **{p['south_dublin_mentions']:,}**",
        "- Length (characters): " + ", ".join(f"{k}: {v:,.0f}" for k, v in p["text_length"].items()),
        "",
        "### South Dublin mentions (first 5)",
        *[f"- {clean(s)}" for s in p["south_dublin_samples"]],
        "",
        "### Random sample of 10 housing questions",
        "| Date | TD | Question |",
        "|---|---|---|",
        *[f"| {s['date']:%d %b} | {s['member']} | {clean(s['text'])} |" for s in p["samples"]],
        "",
        "## Top 5 quality issues",
        "_Written up in docs/data-profile.md._",
        "",
    ]
    return "\n".join(lines)


def newest_bronze_dir() -> pathlib.Path:
    dirs = sorted(d for d in BRONZE.glob("*") if (d / "questions.json").exists())
    if not dirs:
        raise FileNotFoundError("No PQ download in bronze/pqs/. Run the download step first.")
    return dirs[-1]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    dl = sub.add_parser("download")
    dl.add_argument("--days", type=int, default=30)
    dl.add_argument("--force", action="store_true", help="Download again even if today's files exist")
    sub.add_parser("profile")
    args = parser.parse_args(argv)

    if args.command == "download":
        download(days=args.days, force=args.force)
        return

    source = newest_bronze_dir()
    questions = flatten_questions(json.loads((source / "questions.json").read_text(encoding="utf-8")))
    members = json.loads((source / "members.json").read_text(encoding="utf-8"))
    out = REPO_ROOT / "docs" / "pqs-profile.md"
    out.write_text(render_markdown(profile(questions, member_constituencies(members)), source.name), encoding="utf-8")
    print(f"Profiled {len(questions):,} questions -> {out}")


if __name__ == "__main__":
    main()
