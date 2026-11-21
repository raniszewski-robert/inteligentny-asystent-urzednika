"""T12: LLM 'Ad n' paragraphs with a fake transport; the number check in udip.draft rejects bad output."""
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


def _case543():
    fx = json.loads((FIX / "draft_543.json").read_text(encoding="utf-8"))
    return fx["request"], [tuple(a) for a in fx["answers"]]


BKS_543 = {  # paragraphs as placed in the real BKS letter 543 (data-partner/umb/archiwum_umb.jsonl)
    1: "Opiekę nad domowymi zwierzętami bezdomnymi sprawuje Schronisko dla Zwierząt w Bydgoszczy, które jest jednostką budżetową "
       "Miasta Bydgoszczy. Miasto nie zawierało umów z podmiotami zewnętrznymi w zakresie opieki nad domowymi zwierzętami bezdomnymi.",
    2: "Opiekę nad zwierzętami bezdomnymi sprawuje Schronisko dla Zwierząt w Bydgoszczy.",
    3: "Schronisko zapewniło opiekę w 2025 r. 839 psom oraz 560 kotom.",
    4: "Budżet schroniska w 2025 r. wyniósł 3.143.761,14 zł.",
    5: "Informuję, że w 2025 r. realizowana była Umowa 1/2022/SZ zawarta między Schroniskiem a Kliniką Weterynaryjną.",
}


def _paras(texts: dict, prefix=""):
    return {"paragraphs": [{"no": k, "text": prefix.format(k=k) + v, "sources": ["SCHRONISKO.txt", "obcy.txt"]} for k, v in texts.items()]}


def ad_paragraphs(text: str) -> dict[int, str]:
    import re
    parts = re.split(r"(?m)^Ad (\d+)$", text)
    return {int(parts[i]): parts[i + 1] for i in range(1, len(parts) - 1, 2)}


def test_draft_543_llm_matches_bks_placement(fake):
    t = fake(_paras(BKS_543, prefix="Ad {k}. "))
    req, ans = _case543()
    d = D.make_draft(req, ans, date(2026, 8, 14), mode="llm", today=TODAY)
    assert d["report"]["mode_used"] == "llm", d["report"]
    ads = ad_paragraphs(d["text"])
    for no, anchors in GOLD["BKS.IV.1431.543.2026"]["ad_anchors"].items():
        assert all(any(a in ads[int(no)] for a in alt.split("|")) for alt in anchors), (no, ads[int(no)][:80])
    assert "Ad 1. " not in d["text"]  # model heading stripped, one heading per paragraph
    user = t.calls[0]["user"]
    assert user.count("<pytanie") == 5 and user.count("<odpowiedz_wydzialu") == 5 and "839 psom" in user


def test_draft_bad_provider_rejected(fake):
    bad = dict(BKS_543)
    bad[3] = "Schronisko zapewniło opiekę w 2025 r. 839 kotom oraz 560 psom."   # swapped
    bad[4] = "Koszt zadania wyniósł 3.500.000,00 zł."                             # invented
    fake(_paras(bad))
    req, ans = _case543()
    d = D.make_draft(req, ans, date(2026, 8, 14), mode="llm", today=TODAY)
    assert d["report"]["mode_used"] == "template" and d["report"]["llm_rejected"]
    assert "839 psom" in d["text"]


def test_paragraphs_llm_shape_checks(fake):
    qs, ans = ["P1?", "P2?"], [("a.txt", "Fakt 12 sztuk."), ("", "")]
    fake({"paragraphs": [{"no": 1, "text": "Fakt 12 sztuk.", "sources": ["a.txt"]}]},          # missing paragraph
         {"paragraphs": [{"no": 1, "text": "x x x", "sources": []}, {"no": 1, "text": "y y y", "sources": []}]},  # duplicate no
         {"paragraphs": [{"no": 2, "text": "LUKA", "sources": ["a.txt"]}, {"no": 1, "text": "Ad 1: Fakt 12 sztuk.", "sources": ["zmyślony.txt"]}]})
    assert drafting.paragraphs_llm(qs, ans) is None
    assert drafting.paragraphs_llm(["P1 bis?", "P2?"], ans) is None  # other prompt: a schema-valid answer is cached as is
    out = drafting.paragraphs_llm(["P1 ter?", "P2?"], ans)
    assert out == [{"no": 1, "text": "Ad 1\nFakt 12 sztuk.", "sources": ["a.txt"]},
                   {"no": 2, "text": "Ad 2\n" + drafting.GAP, "sources": []}]
    assert drafting.paragraphs_llm(qs, [("", ""), ("", "")]) is None  # nothing to draft from
    assert drafting.paragraphs_llm(qs, ans[:1]) is None


def test_paragraphs_llm_rejects_echoed_questions(fake):
    req, ans = _case543()
    qs = A.split_questions(req)
    fake({"paragraphs": [{"no": i, "text": q, "sources": ["SCHRONISKO.txt"]} for i, q in enumerate(qs, 1)]})
    d = D.make_draft(req, ans, date(2026, 8, 14), mode="llm", today=TODAY)
    assert d["report"]["mode_used"] == "template"
    assert "839 psom" in d["text"]


