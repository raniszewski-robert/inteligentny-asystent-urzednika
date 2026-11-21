"""T24: dispatch packet (sub-deadline, message, reply form), deterministic Ad mapping (tier 1 markers, tier 2 rules with a
margin, unassigned with provenance) and department_dispatches."""
from __future__ import annotations

import io
import json
import re
from datetime import date
from pathlib import Path

import docx
import pytest

from udip import db, dispatch
from udip.analyze import split_questions
from udip.draft import assign, build, make_draft
from udip.ingest import read_any

ROOT = Path(__file__).resolve().parents[2]
CASE = ROOT / "data-partner" / "umb" / "przypadek_543"
GOLD = json.loads((ROOT / "docs" / "eval" / "umb_gold.json").read_text(encoding="utf-8"))["cases"]["BKS.IV.1431.543.2026"]
REQ = (CASE / "wniosek.txt").read_text(encoding="utf-8")
RAW = [(f.name, f.read_text(encoding="utf-8")) for f in (CASE / "SCHRONISKO.txt", CASE / "WGK.txt")]
QS = split_questions(REQ)
CASE_543 = {"number": "BKS.IV.1431.543.2026", "received": "2026-08-14", "summary": "Opieka nad bezdomnymi zwierzętami"}
S2 = "Miasto nie zawierało umów z podmiotami zewnętrznymi"   # the two sentences the v1 heuristic misplaced (Ad 5, Ad 4)
S5 = "Umowa 1/2022/SZ"


def _ad(text: str, n: int) -> str:
    return text.split(f"\nAd {n}\n", 1)[1].split("\nAd ", 1)[0].split("\n\nŁączę", 1)[0] if f"\nAd {n}\n" in text else ""


def _draft(answers, **kw):
    return make_draft(REQ, answers, date(2026, 8, 14), number="BKS.IV.1431.543.2026", today=date(2026, 11, 22), sign="[podpis]", **kw)


# ---------------------------------------------------------------- sub-deadline


def test_sub_deadline_three_working_days_before_legal_due():
    # wpływ pt 14.08.2026 → termin ustawowy pt 28.08.2026 → wydział do wt 25.08
    assert dispatch.sub_deadline(date(2026, 8, 14), date(2026, 8, 17)) == date(2026, 8, 25)


def test_sub_deadline_at_least_two_working_days_from_today():
    # sprawa przekazana późno: dziś czw 27.08 → pon 31.08 (po terminie ustawowym; packet ostrzega)
    assert dispatch.sub_deadline(date(2026, 8, 14), date(2026, 8, 27)) == date(2026, 8, 31)
    _, text, sub, legal = dispatch.message_text(CASE_543, "WGK", [{"no": 1, "text": QS[0]}], today=date(2026, 8, 27))
    assert sub > legal and text.startswith("[UWAGA")


def test_sub_deadline_skips_statutory_holidays():
    # wpływ 29.10.2026 → termin 12.11 (czw); wstecz 3 dni robocze z pominięciem 11.11 i weekendu → pt 06.11
    assert dispatch.sub_deadline(date(2026, 10, 29), date(2026, 11, 2)) == date(2026, 11, 6)


def test_sub_deadline_with_extended_due():
    assert dispatch.sub_deadline(date(2026, 8, 14), date(2026, 9, 1), due=date(2026, 10, 14)) == date(2026, 10, 9)


# ---------------------------------------------------------------- packet


def test_packet_has_only_that_departments_questions_deadline_and_anonymisation_reminder():
    qs = [{"no": 3, "text": QS[2]}, {"no": 4, "text": QS[3]}]
    p = dispatch.packet(CASE_543, "SCHRONISKO", qs, today=date(2026, 8, 17))
    m = p["message_text"]
    assert "BKS.IV.1431.543.2026" in m and "Schronisko dla Zwierząt" in m
    assert "[Ad 3] " + QS[2] in m and "[Ad 4] " + QS[3] in m
    assert "[Ad 1]" not in m and "[Ad 5]" not in m and QS[0] not in m
    assert "25 sierpnia 2026 r." in m and "28 sierpnia 2026 r." in m  # termin wydziału i ustawowy
    assert "§ 11 ust. 8" in m and "zanonimizowan" in m
    assert p["sub_deadline"] == date(2026, 8, 25)
    d = docx.Document(io.BytesIO(p["reply_form_docx"]))
    paras = [x.text for x in d.paragraphs]
    assert "[Ad 3] Pytanie: " + QS[2] in paras and "[Ad 4] Pytanie: " + QS[3] in paras
    assert paras.count("Odpowiedź wydziału:") == 2
    assert dispatch.parse_reply("\n".join(paras)) == {}  # an empty form maps nothing (and is not read as text)


def test_dispatch_questions_groups_by_chosen_department():
    case = {"analysis": {"questions": [{"no": 1, "text": "a", "routing": [{"department": "WGK"}]},
                                       {"no": 2, "text": "b", "routing": [{"department": "WGK"}]},
                                       {"no": 3, "text": "c", "routing": [{"department": "WGK"}]}],
                         "chosen_departments": {"2": ["WGK", "SCHRONISKO"], "3": ["SCHRONISKO"]}}}
    g = dispatch.dispatch_questions(case)
    assert [q["no"] for q in g["WGK"]] == [1, 2] and [q["no"] for q in g["SCHRONISKO"]] == [2, 3]


# ---------------------------------------------------------------- tier 1: markers


@pytest.mark.parametrize("text, expected", [
    ("Uprzejmie informuję:\nAd 1. Pierwsza odpowiedź.\nAd 2. Druga odpowiedź.", {1: "Pierwsza odpowiedź.", 2: "Druga odpowiedź."}),
    ("Ad. 1 Tak.\nAd. 3 Nie.", {1: "Tak.", 3: "Nie."}),
    ("[Ad 2] Zrobione.\n[Ad 4] Nie dotyczy.\n\nSprawę prowadzi: Jan Kowalski", {2: "Zrobione.", 4: "Nie dotyczy."}),
    ("Ad 1\nTreść w akapicie.\nAd 2\nDruga.\nZ poważaniem\nX", {1: "Treść w akapicie.", 2: "Druga."}),
    ("[Ad 1] Pytanie: z kim gmina miała umowy?\nOdpowiedź wydziału:\nZ nikim.", {1: "Z nikim."}),
])
def test_parse_reply_markers(text, expected):
    assert dispatch.parse_reply(text) == expected


def test_parse_reply_without_markers_is_none():
    assert dispatch.parse_reply(RAW[0][1]) is None
    assert dispatch.parse_reply("Pomoc ad hoc w 2025 r. objęła 12 osób.") is None


def _fill(form: bytes, answers: dict[int, str]) -> bytes:
    d = docx.Document(io.BytesIO(form))
    ps = d.paragraphs
    current = None
    for i, p in enumerate(ps):
        m = re.match(r"\[Ad (\d+)\]", p.text)
        if m:
            current = int(m.group(1))
        if p.text == "Odpowiedź wydziału:" and current in answers:
            ps[i + 1].text = answers[current]
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


def test_543_filled_reply_forms_map_deterministically(tmp_path):
    """AC 1: the packet's reply form, filled by the departments and uploaded back → 100 % deterministic mapping."""
    q = [{"no": i, "text": t} for i, t in enumerate(QS, 1)]
    wgk = dispatch.packet(CASE_543, "WGK", q[:2], today=date(2026, 8, 17))
    sch = dispatch.packet(CASE_543, "SCHRONISKO", q[1:], today=date(2026, 8, 17))
    files = {
        "WGK_formularz.docx": _fill(wgk["reply_form_docx"], {1: "Wyłapywanie bezdomnych zwierząt w 2025 r. realizowało Schronisko dla "
                                                                "Zwierząt w Bydgoszczy; Wydział nie udzielał w tym zakresie zleceń podmiotom zewnętrznym."}),
        "SCHRONISKO_formularz.docx": _fill(sch["reply_form_docx"], {
            2: "Opiekę nad domowymi zwierzętami bezdomnymi sprawuje Schronisko dla Zwierząt w Bydgoszczy. Miasto nie zawierało umów "
               "z podmiotami zewnętrznymi w zakresie opieki nad domowymi zwierzętami bezdomnymi.",
            3: "Schronisko zapewniło opiekę w 2025 r. 839 psom oraz 560 kotom.",
            4: "Budżet schroniska w 2025 r. wyniósł 3.143.761,14 zł.",
            5: "W 2025 r. realizowana była Umowa 1/2022/SZ zawarta między Schroniskiem a Kliniką Weterynaryjną."}),
    }
    answers = []
    for name, data in files.items():
        (tmp_path / name).write_bytes(data)
        answers.append((name, read_any(tmp_path / name)["text"]))
    d = _draft(answers)
    rep, text = d["report"], d["text"]
    assert rep["unassigned"] == [] and rep["gaps"] == []
    assert rep["provenance"] and all(p["tier"] == "marker" and p["confidence"] == 1.0 for p in rep["provenance"])
    assert rep["assignment_tiers"]["rules"] == 0
    assert S2 in _ad(text, 2) and "839 psom" in _ad(text, 3) and "3.143.761,14" in _ad(text, 4) and S5 in _ad(text, 5)
    assert "Pytanie:" not in text and "Odpowiedź wydziału" not in text and "Sprawę prowadzi" not in text
    assert not rep["number_check_template"]


def test_marker_beyond_the_question_count_is_unassigned_not_dropped():
    d = _draft([("WGK.txt", "Ad 1. Nie udzielano zleceń.\nAd 7. Zdanie do pytania, którego nie ma.")])
    assert [u["sentence"] for u in d["report"]["unassigned"]] == ["Zdanie do pytania, którego nie ma."]
    assert "którego nie ma" not in d["text"]


# ---------------------------------------------------------------- tier 2: rules, margin, unassigned


def test_543_raw_replies_rules_mode_nothing_silently_wrong():
    """AC 2: raw 543 replies, rules mode. 'Miasto nie zawierało umów…' (v1: Ad 5) fits Ad 2 and Ad 5 equally → unassigned with
    provenance; 'Umowa 1/2022/SZ' (v1: Ad 4) is a numbered document → Ad 5, as in the BKS letter. No placed sentence contradicts
    the BKS letter's paragraphs."""
    d = _draft(RAW)
    rep, text = d["report"], d["text"]
    un = rep["unassigned"]
    assert [(u["source"], u["index"]) for u in un] == [("SCHRONISKO.txt", 1)]
    assert un[0]["sentence"].startswith(S2) and set(un[0]["candidates"]) == {2, 5}
    assert S2 not in text
    assert S5 in _ad(text, 5) and S5 not in _ad(text, 4)
    # BKS letter 543.2026: Ad 1 = S1+S2, Ad 2 = S1 (abbreviated), Ad 3 = S3, Ad 4 = S4, Ad 5 = S5; WGK's sentence belongs to Ad 1
    bks = {("SCHRONISKO.txt", 0): {1, 2}, ("SCHRONISKO.txt", 2): {3}, ("SCHRONISKO.txt", 3): {4}, ("SCHRONISKO.txt", 4): {5},
           ("WGK.txt", 0): {1}}
    for p in rep["provenance"]:
        assert p["para"] in bks[(p["source"], p["index"])], p
    for n, anchors in GOLD["ad_anchors"].items():
        for a in anchors:
            assert any(x in _ad(text, int(n)) for x in a.split("|")), (n, a)
    assert rep["gaps"] == [] and not rep["number_check_template"]


def test_acceptance_test_2_expectations_hold():
    text, rep = build(REQ, RAW, "BKS.IV.1431.543.2026", date(2026, 8, 14), "udostepnienie", "template", "[podpis]", date(2026, 11, 22))
    for must in ("839 psom", "3.143.761,14", "Ad 5", "Łączę wyrazy szacunku", "Schronisko dla Zwierząt"):
        assert must in text
    assert "839 psom" in text.split("Ad 3", 1)[1].split("Ad 4", 1)[0]
    assert not rep["gaps"] and not rep["number_check_template"]


def test_every_draft_sentence_has_provenance():
    """AC 3: every sentence in an 'Ad' paragraph is listed with (source_file, sentence_index), and vice versa."""
    d = _draft(RAW)
    text, prov = d["text"], d["report"]["provenance"]
    srcs = dict(RAW)
    for n in range(1, len(QS) + 1):
        para = _ad(d["text"], n)
        mine = [p for p in prov if p["para"] == n]
        assert mine, n
        assert " ".join(p["sentence"] for p in mine) == para.strip()
        for p in mine:
            assert p["source"] in srcs and isinstance(p["index"], int)
            assert p["sentence"][:30].lower() in re.sub(r"\s+", " ", srcs[p["source"]]).lower()
    for u in d["report"]["unassigned"]:
        assert u["source"] in srcs and isinstance(u["index"], int)
    assert "provenance" in d["report"] and text


def test_ambiguous_sentence_goes_to_unassigned_and_the_gap_says_why():
    req = "1. Ile drzew posadzono w parku w 2025 r.?\n2. Ile drzew posadzono przy ulicach w 2025 r.?"
    d = make_draft(req, [("WGK.txt", "Uprzejmie informuję, że posadzono drzewa zgodnie z planem.")], date(2026, 8, 14), today=date(2026, 9, 1))
    rep = d["report"]
    assert len(rep["unassigned"]) == 1 and rep["unassigned"][0]["index"] == 0 and rep["gaps"] == [1, 2]
    assert "czeka na przypisanie" in d["text"] and "zgodnie z planem" not in d["text"]


def test_count_and_amount_sentence_goes_by_vocabulary_among_typed_questions():
    qs = ["Ile gruntów należących do miasta sprzedano w roku 2025? Jaki był przychód?",
          "Ile kosztowało utrzymanie oświetlenia dróg publicznych w roku 2025?"]
    res = assign(qs, [("WMG.txt", "Uprzejmie informuję, że w 2025 r. sprzedano 375 nieruchomości gminnych za łączną kwotę 1 272 139 zł.")])
    assert res["sentences"][0]["no"] == 1 and res["unassigned"] == []


# ---------------------------------------------------------------- clerk's decisions (tier 1)


def test_clerk_assignment_places_and_skips_sentences():
    d = _draft(RAW, assignments={"SCHRONISKO.txt#1": 1})
    assert d["report"]["unassigned"] == [] and S2 in _ad(d["text"], 1)
    p = next(x for x in d["report"]["provenance"] if x["source"] == "SCHRONISKO.txt" and x["index"] == 1)
    assert p["tier"] == "clerk" and p["confidence"] == 1.0
    d = _draft(RAW, assignments={"SCHRONISKO.txt#1": 0})
    assert d["report"]["unassigned"] == [] and S2 not in d["text"]


def test_per_question_upload_maps_whole_file():
    d = _draft([("odp_ad3.txt", "Uprzejmie informuję, że opieką objęto 839 psów i 560 kotów.")], assignments={"odp_ad3.txt": 3})
    assert "839 psów" in _ad(d["text"], 3)
    assert all(p["para"] == 3 and p["tier"] == "clerk" for p in d["report"]["provenance"])


# ---------------------------------------------------------------- department_dispatches


@pytest.fixture
def tmp_data(tmp_path, monkeypatch):
    monkeypatch.setenv("UDIP_DATA_DIR", str(tmp_path))
    return tmp_path


def test_add_dispatch_one_row_per_department_and_init_is_idempotent(tmp_data):
    db.init()
    db.init()
    cid = db.create_case(number="BKS.IV.1431.900.2026", received="2026-08-14")
    a = db.add_dispatch(cid, "WGK", [{"no": 1, "text": "x"}], date(2026, 8, 25), sent_at="2026-08-17T10:00:00")
    b = db.add_dispatch(cid, "SCHRONISKO", [3, 4], "2026-08-25")
    assert db.add_dispatch(cid, "WGK", [{"no": 1, "text": "x"}, {"no": 2, "text": "y"}], "2026-08-26") == a != b
    rows = db.dispatches(cid)
    assert [r["department"] for r in rows] == ["WGK", "SCHRONISKO"]
    assert rows[0]["sub_deadline"] == "2026-08-26" and len(rows[0]["questions"]) == 2 and rows[0]["answered_at"] is None
    db.set_dispatch_answered(cid, "WGK", "2026-08-20T09:00:00")
    db.set_dispatch_answered(cid, "WGK", "2026-08-21T09:00:00")
    assert db.dispatches(cid)[0]["answered_at"] == "2026-08-20T09:00:00"
    db.delete_case(cid)
    assert db.dispatches(cid) == []
