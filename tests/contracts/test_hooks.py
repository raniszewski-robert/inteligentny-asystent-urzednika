"""T00 contract tests: udip.* delegates to real code and the LLM hook points behave as CONTRACTS §2 says."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

import udip.analyze as A
import udip.anonymize as N
import udip.draft as D
import udip.llm as L
from udip.llm_tasks import analysis, anonymization, drafting, routing

FIX = Path(__file__).resolve().parents[1] / "fixtures"
TODAY = date(2026, 11, 22)


@pytest.fixture
def llm_on(monkeypatch):
    monkeypatch.setattr(L, "available", lambda: True)
    monkeypatch.setenv("UDIP_PROVIDER", "anthropic:sonnet")


def test_rules_path_matches_fixture():
    fx = json.loads((FIX / "analysis_599.json").read_text(encoding="utf-8"))
    from udip.search import Archive, load_archive
    arch = Archive(load_archive(Path(__file__).resolve().parents[2] / "data-partner/umb/archiwum_umb.jsonl"))
    res = A.analyze(fx["text"], arch, A.load_departments(), TODAY)
    assert res["llm_used"] is False and res["provider"] == "rules"
    assert [s["id"] for s in res["similar_cases"]] == [s["id"] for s in fx["analysis"]["similar_cases"]]


def test_provider_falls_back_to_rules_without_key(monkeypatch):
    monkeypatch.setenv("UDIP_PROVIDER", "anthropic:sonnet")
    assert L.provider_for(None) == "rules"
    assert L.complete_json("t", "s", "u", {}) is None


def test_analyze_hook_merges_llm(llm_on, monkeypatch):
    text = "1. Ile wydano na schronisko w 2025 r.?\n2. Ile psów adoptowano?"
    monkeypatch.setattr(analysis, "analyze_llm", lambda t, **kw: {"questions": ["a", "b", "c"], "mode": "udip", "summary": "Schronisko",
                                                           "applicant_type": "osoba", "flags": [{"type": "x", "message": "m"}]})
    monkeypatch.setattr(routing, "route_llm", lambda q, deps, **kw: [{"department": "WGK", "reason": "schronisko"}])
    res = A.analyze(text, None, A.load_departments(), TODAY)
    assert res["llm_used"] and res["summary"] == "Schronisko"
    assert len(res["questions"]) == 2 and any(f["type"] == "liczba_pytan" for f in res["flags"])
    assert all(q["llm_routing"][0]["department"] == "WGK" for q in res["questions"])


def test_analyze_hook_none_keeps_rules(llm_on):
    res = A.analyze("Proszę o informację o budżecie schroniska.", None, A.load_departments(), TODAY)
    assert res["llm_used"] is False and "summary" not in res


def test_detect_hook_adds_review_spans(llm_on, monkeypatch):
    text = "Pisze Zenobiusz Wąchocki z Fordonu, PESEL 44051401359."
    monkeypatch.setattr(anonymization, "spans_llm", lambda t, **kw: [{"start": 6, "end": 25, "type": "OSOBA", "reason": "imię"},
                                                               {"start": 44, "end": 55, "type": "PESEL"}])
    rules = N.detect(text, provider="rules")
    spans = N.detect(text)
    added = [s for s in spans if s.reason.startswith("model:")]
    assert all(s.status == "review" for s in added)
    assert len(spans) == len(rules) + len(added) and not any(s.start == 44 for s in added)  # overlap with PESEL dropped


def _case543():
    fx = json.loads((FIX / "draft_543.json").read_text(encoding="utf-8"))
    return fx["request"], [tuple(a) for a in fx["answers"]]


def test_draft_llm_mode_falls_back_without_llm():
    req, ans = _case543()
    d = D.make_draft(req, ans, date(2026, 8, 14), mode="llm", today=TODAY)
    assert d["report"]["mode_used"] == "template" and "839 psom" in d["text"]


def test_draft_llm_hook_number_check(llm_on, monkeypatch):
    req, ans = _case543()
    n = D.make_draft(req, ans, date(2026, 8, 14), today=TODAY)["report"]["questions"]
    monkeypatch.setattr(drafting, "paragraphs_llm", lambda qs, a, **kw: [{"no": i + 1, "text": "Kwota 999 999 zł.", "sources": []} for i in range(len(qs))])
    d = D.make_draft(req, ans, date(2026, 8, 14), mode="llm", today=TODAY)
    assert n == 5 and d["report"]["mode_used"] == "template" and d["report"].get("llm_rejected")


def test_draft_llm_hook_accepts_grounded_paragraphs(llm_on, monkeypatch):
    req, ans = _case543()
    monkeypatch.setattr(drafting, "paragraphs_llm", lambda qs, a, **kw: [{"no": i + 1, "text": t or "Brak odpowiedzi.", "sources": [s]}
                                                                   for i, (s, t) in enumerate(a)])
    d = D.make_draft(req, ans, date(2026, 8, 14), mode="llm", today=TODAY)
    assert d["report"]["mode_used"] == "llm"


def test_hooks_pass_explicit_provider(llm_on, monkeypatch):
    seen = []
    monkeypatch.setattr(analysis, "analyze_llm", lambda t, provider=None: seen.append(("a", provider)))
    monkeypatch.setattr(routing, "route_llm", lambda q, deps, provider=None: seen.append(("r", provider)))
    monkeypatch.setattr(anonymization, "spans_llm", lambda t, provider=None: seen.append(("s", provider)))
    monkeypatch.setattr(drafting, "paragraphs_llm", lambda qs, a, provider=None: seen.append(("d", provider)))
    A.analyze("Proszę o informację o budżecie schroniska.", None, A.load_departments(), TODAY, provider="anthropic:haiku")
    N.detect("Jan Kowalski", provider="anthropic:haiku")
    req, ans = _case543()
    D.make_draft(req, ans, date(2026, 8, 14), mode="llm", today=TODAY, provider="anthropic:haiku")
    assert {k for k, _ in seen} == {"a", "r", "s", "d"} and all(p == "anthropic:haiku" for _, p in seen)


def test_ad_headings_are_not_numbers():
    src = ["Wydano 3 143 761,14 zł."]
    paras = ["Ad 10", "Wydano 3 143 761,14 zł.", "Ad 11. Wydano 3 143 761,14 zł."]
    assert D.check_numbers(paras, src) == []
    assert D.omitted_numbers(paras, src) == []
