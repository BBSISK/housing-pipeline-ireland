"""Offline tests for the Oireachtas PQ downloader and profiler, using fake API responses."""

import datetime as dt

from housing_pipeline import pqs


def question(n, department="Housing", text="To ask the Minister for Housing about social housing delivery.",
             member="Jane Doe", code="Jane-Doe.D.2024-11-29", date="2026-10-01", qtype="written"):
    return {
        "question": {
            "uri": f"https://data.oireachtas.ie/question/{n}",
            "date": date,
            "questionType": qtype,
            "questionNumber": n,
            "by": {"showAs": member, "memberCode": code},
            "to": {"showAs": department},
            "showAs": text,
            "debateSection": {"showAs": "Housing Provision"},
        }
    }


def member(code, constituency):
    return {
        "member": {
            "memberCode": code,
            "memberships": [
                {"membership": {"represents": [{"represent": {"showAs": constituency, "representType": "constituency"}}]}}
            ],
        }
    }


def test_download_questions_pages_with_skip(monkeypatch):
    monkeypatch.setattr(pqs, "PAGE_SIZE", 2)
    pages = [
        {"results": [question(1), question(2)]},
        {"results": [question(3)]},
    ]
    calls = []

    def fetch(path, params):
        calls.append((path, params))
        return pages[len(calls) - 1]

    results = pqs.download_questions(dt.date(2026, 9, 1), dt.date(2026, 10, 1), fetch=fetch)
    assert len(results) == 3
    assert [p["skip"] for _, p in calls] == [0, 2]
    assert calls[0][0] == "questions"
    assert calls[0][1]["qtype"] == "oral,written"


def test_clean_text_strips_question_number_and_reference():
    raw = "356. Deputy X asked the Minister for Housing about homes. [66495/26]"
    assert pqs.clean_text(raw) == "Deputy X asked the Minister for Housing about homes."


def test_numbers_ignore_question_number_and_reference():
    df = pqs.flatten_questions([
        question(1, text="12. Deputy X asked about homes. [111/26]"),
        question(2, text="13. Deputy Y asked how many of the 450 homes were built. [112/26]"),
    ])
    p = pqs.profile(df, {})
    assert p["with_numbers"] == 1
    assert p["with_pq_reference"] == 2


def test_member_constituencies():
    lookup = pqs.member_constituencies([member("A.D.1", "Dublin Mid-West"), {"member": {"memberCode": "B"}}])
    assert lookup == {"A.D.1": "Dublin Mid-West"}


def test_profile_filters_housing_and_flags_issues():
    raw = [
        question(1),
        question(2, text="To ask the Minister for Housing the number of homes delivered in Lucan in 2025."),
        question(3, text="To ask the Minister for Housing about a person (details supplied) in Tallaght.",
                 member="John Smith", code="John-Smith.D.1"),
        question(4, department="Foreign", text="To ask the Minister for Foreign Affairs about trade."),
        question(1),  # duplicate URI
    ]
    df = pqs.flatten_questions(raw)
    p = pqs.profile(df, {"Jane-Doe.D.2024-11-29": "Dublin Mid-West"})
    assert p["rows"] == 5
    assert p["housing_rows"] == 4
    assert p["duplicate_uris"] == 1
    assert p["details_supplied"] == 1
    assert p["with_numbers"] == 1
    assert p["south_dublin_mentions"] == 2
    assert p["constituency_unmatched"] == 1
    assert p["top_constituencies"]["Dublin Mid-West"] == 3


def test_render_markdown_has_sections():
    df = pqs.flatten_questions([question(1), question(2, department="Foreign")])
    md = pqs.render_markdown(pqs.profile(df, {}), "2026-10-11")
    for heading in ["## Size and coverage", "## Who asks", "## Text", "## Top 5 quality issues"]:
        assert heading in md
