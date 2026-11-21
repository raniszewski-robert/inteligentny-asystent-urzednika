"""T13: LLM anonymization pass and routing justification with a fake transport."""
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


def test_spans_llm_locates_offsets_itself(fake):
    text = "Pisze Zenobiusz  Wąchocki z Fordonu. Pan Zenobiusz  Wąchocki choruje na cukrzycę."
    fake({"items": [{"text": "Zenobiusz Wąchocki", "type": "OSOBA", "reason": "imię i nazwisko", "confidence": 0.9},
                    {"text": "Wąchocki", "type": "OSOBA", "reason": "nazwisko", "confidence": 0.8},
                    {"text": "choruje na cukrzycę", "type": "DANE_WRAZLIWE", "reason": "zdrowie", "confidence": 0.7},
                    {"text": "nie ma w tekście", "type": "OSOBA", "reason": "x", "confidence": 0.9}]})
    out = anonymization.spans_llm(text)
    assert [text[s["start"]:s["end"]] for s in out] == ["Zenobiusz  Wąchocki", "Zenobiusz  Wąchocki", "choruje na cukrzycę"]
    assert all(s["text"] == text[s["start"]:s["end"]] for s in out)


def test_detect_llm_spans_are_review_and_recall_not_lower(fake):
    pii = ROOT / "data-samples/syntetyczne/pii"
    gold = json.loads((pii / "gold.json").read_text(encoding="utf-8"))
    tot = hit_rules = hit_union = 0
    for g in gold:
        p = (pii.parent / g["file"]) if (pii.parent / g["file"]).is_file() else pii / g["file"]
        if not p.is_file():
            continue
        text = p.read_text(encoding="utf-8")
        # fake model: proposes every gold fragment plus one false alarm
        fake({"items": [{"text": s["text"], "type": "OSOBA" if s["type"] not in anonymization.TYPES else s["type"],
                         "reason": "model", "confidence": 0.7} for s in g["spans"]]
                       + [{"text": "Urząd Miasta", "type": "OSOBA", "reason": "fałszywy alarm", "confidence": 0.4}]})
        rules = N.detect(text, provider="rules")
        union = N.detect(text)
        llm_spans = [s for s in union if s.reason.startswith("model:")]
        assert all(s.status == "review" for s in llm_spans)  # 0 accepted-by-default
        for s in g["spans"]:
            tot += 1
            hit_rules += any(x.start < s["end"] and s["start"] < x.end for x in rules)
            hit_union += any(x.start < s["end"] and s["start"] < x.end for x in union)
    assert tot > 20 and hit_union >= hit_rules and hit_union == tot


def test_spans_llm_failure_is_none(fake):
    fake(RuntimeError("down"))
    assert anonymization.spans_llm("Jan Kowalski pisze.") is None
    text = "Pisze Jan Kowalski, PESEL 44051401359."
    assert [s.text for s in N.detect(text)] == [s.text for s in N.detect(text, provider="rules")]


# ------------------------------------------------------------------ T13 routing


def test_route_llm_filters(fake):
    deps = A.load_departments()
    t = fake({"departments": [{"department": "WE", "reason": "szkoły  podstawowe"}, {"department": "WE", "reason": "dubel"},
                              {"department": "WOA", "reason": "druga"}]},
             {"departments": [{"department": "NIEISTNIEJE", "reason": "x"}]}, {"departments": []})
    assert routing.route_llm("Ilu uczniów jest w szkołach podstawowych?", deps) == [
        {"department": "WE", "reason": "szkoły podstawowe"}, {"department": "WOA", "reason": "druga"}]
    assert "BKS |" not in t.calls[0]["system"] and "SCHRONISKO |" in t.calls[0]["system"]
    assert routing.route_llm("Pytanie?", deps) is None      # unknown id → schema error → rules
    assert routing.route_llm("Pytanie 2?", deps) is None    # empty → rules
    assert routing.route_llm("", deps) is None


def test_route_batch_llm_used_for_local_provider(fake):
    deps = A.load_departments()
    t = fake(by_task({
        "rejestruje wnioski": ANALYSIS,
        "wskazujesz komórki": {"items": [
            {"no": 1, "departments": [{"department": "SCHRONISKO", "reason": "opieka nad zwierzętami"}]},
            {"no": 2, "departments": [{"department": "WGK", "reason": "umowy i koszty"}]},
        ]},
    }))
    res = A.analyze("1. Ile wydano na schronisko w 2025 r.?\n2. Ile psów adoptowano?", None, deps, TODAY,
                    provider="openai_compat:bielik")
    assert res["llm_used"] and res["provider"] == "openai_compat:bielik"
    assert res["questions"][0]["llm_routing"] == [{"department": "SCHRONISKO", "reason": "opieka nad zwierzętami"}]
    assert res["questions"][1]["llm_routing"] == [{"department": "WGK", "reason": "umowy i koszty"}]
    assert len(t.calls) == 2  # 1 analysis + 1 batched routing call (not 1 + N)


def test_umb_gold_is_consistent():
    ids = {d["id"] for d in A.load_departments()}
    assert len(GOLD) == 10
    for cid, g in GOLD.items():
        assert g["questions"] in g["questions_ok"]
        assert all(d in ids or d.startswith("ZEWN") for d in g["departments"]), cid
