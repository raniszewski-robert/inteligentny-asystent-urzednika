"""T11: LLM request analysis with a fake transport; None on failure, the hook keeps the rules."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import udip.analyze as A
import udip.anonymize as N
import udip.draft as D
import udip.llm as L
from udip.llm_tasks import analysis, anonymization, drafting, routing

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "tests" / "fixtures"
TODAY = date(2026, 11, 22)
GOLD = json.loads((ROOT / "docs/eval/umb_gold.json").read_text(encoding="utf-8"))["cases"]

ANALYSIS = {"questions": ["Ile wydano na schronisko w 2025 r.?", "Ile psów adoptowano?"], "mode": "udip",
            "flags": [{"type": "informacja_przetworzona?", "message": "dane z wielu lat"},
                      {"type": "informacja_przetworzona?", "message": "dubel"},
                      {"type": "wiele_komorek", "message": "schronisko i WGK"}],
            "summary": "Koszty schroniska dla zwierząt i adopcje psów w Bydgoszczy w roku 2025 oraz plany na rok 2026",
            "applicant_type": "osoba_fizyczna"}


def by_task(answers: dict):
    """Fake answer chosen by the task's system prompt."""
    def pick(system, user, schema):
        for marker, ans in answers.items():
            if marker in system:
                return ans(user) if callable(ans) else ans
        return {}
    return pick


def test_analyze_llm_normalises(fake):
    fake(ANALYSIS)
    a = analysis.analyze_llm("1. Ile wydano na schronisko w 2025 r.?\n2. Ile psów adoptowano?")
    assert a["questions"] == ANALYSIS["questions"] and a["mode"] == "udip"
    assert len(a["summary"].rstrip("…").split()) <= 12 and a["summary"].endswith("…")
    assert [f["type"] for f in a["flags"]] == ["informacja_przetworzona?", "wiele_komorek"]


def test_analyze_llm_rejects_bad_schema_and_failures(fake):
    fake(dict(ANALYSIS, mode="tryb_wymyslony"), dict(ANALYSIS, questions=[]), RuntimeError("timeout"), "nie JSON")
    assert [analysis.analyze_llm("Wniosek o informację " + str(i)) for i in range(4)] == [None] * 4
    assert analysis.analyze_llm("") is None


def test_analyze_hook_with_llm_tasks(fake):
    fake(by_task({"rejestruje wnioski": ANALYSIS,
                  "wskazujesz komórki": {"departments": [{"department": "SCHRONISKO", "reason": "prowadzi schronisko"},
                                                         {"department": "SCHRONISKO", "reason": "dubel"}]}}))
    res = A.analyze("1. Ile wydano na schronisko w 2025 r.?\n2. Ile psów adoptowano ze schroniska?", None, A.load_departments(), TODAY)
    assert res["llm_used"] and res["provider"] == "anthropic:sonnet" and res["summary"]
    assert all(q["llm_routing"] == [{"department": "SCHRONISKO", "reason": "prowadzi schronisko"}] for q in res["questions"])
    assert any(f.get("source") == "llm" and f["type"] == "wiele_komorek" for f in res["flags"])


def test_analyze_fallback_keeps_rules(fake):
    fake(RuntimeError("API down"))
    text = "1. Ile wydano na schronisko w 2025 r.?\n2. Ile psów adoptowano?"
    rules = A.analyze(text, None, A.load_departments(), TODAY, provider="rules")
    res = A.analyze(text, None, A.load_departments(), TODAY)
    assert res["llm_used"] is False and "summary" not in res and res["questions"] == rules["questions"]


def test_injection_in_request_keeps_schema(fake):
    text = (ROOT / "tests/llm/fixtures/injection_pl.txt").read_text(encoding="utf-8")
    t = fake({"kategoria": "KANAREK-7Q", "priorytet": "wysoki"})
    assert analysis.analyze_llm(text) is None
    assert t.calls[0]["user"].count("</wniosek>") == 1


