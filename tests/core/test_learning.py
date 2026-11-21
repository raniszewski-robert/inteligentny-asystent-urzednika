"""T25: three feedback loops – remembered personal-data decisions, routing corrections, laws added to the knowledge base."""
from __future__ import annotations

from pathlib import Path

import pytest

from udip import db, learning
from udip.analyze import load_departments, route
from udip.anonymize import detect, detect_rules

ROOT = Path(__file__).resolve().parents[2]
DEMO_LAW = ROOT / "demo_assets" / "04_nowelizacja_udip_2026_demo.pdf"
DOC1 = "Odpowiedź przygotował dyrektor Marek Zieliński. Dokumentacja Projekt Kaskada objęta jest umową. Wnioskodawca: Anna Nowak."
DOC2 = ("Wyjaśnienia złożył dyrektor Marek Zieliński. Spółka przekazała harmonogram dla Projektu Kaskada w maju.\n"
        "Z poważaniem\nJan Wiśniewski")


@pytest.fixture
def iso(tmp_path, monkeypatch):
    monkeypatch.setenv("UDIP_DATA_DIR", str(tmp_path))
    yield tmp_path


def _by_text(spans):
    return {s.text: s for s in spans}


# ------------------------------------------------------------------ acceptance

def test_remembered_exception_and_business_secret_apply_to_the_next_document(iso):
    first = _by_text(detect_rules(DOC1))
    assert "Marek Zieliński" in first and "Projekt Kaskada" not in first
    learning.remember("Marek Zieliński", "allow", "OSOBA", case_id=1, by="Pracownik 1")       # „Zapamiętaj jako wyjątek”
    learning.remember("Projekt Kaskada", "redact", "TAJEMNICA", case_id=1, by="Pracownik 1")  # tajemnica przedsiębiorcy
    nxt = _by_text(detect(DOC2, provider="rules"))
    assert "Marek Zieliński" not in nxt                      # the official is no longer flagged
    assert "Jan Wiśniewski" in nxt                           # other people still are
    k = nxt["Projektu Kaskada"]                              # inflected form found too
    assert k.type == "TAJEMNICA" and k.status == "suggested" and k.reason == learning.REASON_PII


def test_routing_correction_puts_the_confirmed_department_first(iso):
    deps = load_departments()
    q1 = "Ile psów przyjęło schronisko dla zwierząt w 2025 roku?"
    assert route(q1, deps, [])[0]["department"] == "SCHRONISKO"
    learning.log_routing(q1, "SCHRONISKO", "WGK", case_id=3)
    r = route("Ile psów i kotów przyjęło schronisko dla zwierząt w 2026 roku?", deps, [])
    assert r[0]["department"] == "WGK"
    assert r[0]["reasons"][0] == "Wzmocnione przez 1 korektę urzędnika"
    unrelated = route("Jaki był koszt oświetlenia ulic w 2025 roku?", deps, [])
    assert all("Wzmocnione" not in x for d in unrelated for x in d["reasons"])


def test_uploaded_mock_amendment_appears_in_legal_hits(iso):
    n = learning.add_law(DEMO_LAW, "Nowelizacja UDIP 2026 (demo)")
    assert n == 4  # preamble + § 1–3
    hits = learning.legal_hits("Wnoszę o udostępnienie informacji publicznej w terminie 14 dni od dnia złożenia wniosku.")
    assert hits and hits[0]["ref"] == "§ 1" and hits[0]["new"] and hits[0]["source_file"] == DEMO_LAW.name
    assert "14 dni" in hits[0]["text"]


# ------------------------------------------------------------------ details

def test_confirmations_are_logged_but_do_not_boost(iso):
    q = "Ile psów przyjęło schronisko dla zwierząt w 2025 roku?"
    learning.log_routing(q, "SCHRONISKO", "SCHRONISKO", 1)
    assert learning.boost(q, {"SCHRONISKO": 3.0}) == {}
    assert learning.memory_stats()["routing_all"] == 1 and learning.memory_stats()["routing"] == 0
    for i in range(3):
        learning.log_routing(q, "SCHRONISKO", "WGK", i)
    extra, reason = learning.boost(q, {"SCHRONISKO": 3.0})["WGK"]
    assert extra > 3.0 and reason == "Wzmocnione przez 3 korekty urzędnika"
    assert learning.korekty(5) == "5 korekt" and learning.korekty(22) == "22 korekty" and learning.korekty(12) == "12 korekt"


def test_latest_decision_on_a_phrase_wins(iso):
    a = learning.remember("Projekt Kaskada", "redact", "TAJEMNICA")
    b = learning.remember("projekt  kaskada", "allow", "")
    assert a == b and [r["action"] for r in learning.rules()] == ["allow"]
    with pytest.raises(ValueError):
        learning.remember("x", "allow")
    with pytest.raises(ValueError):
        learning.remember("Projekt", "maybe")


def test_split_law_articles_paragraphs_and_rulings():
    text = ("Ustawa o przykładach\nArt. 1. Zakres ustawy.\nArt. 2a. Definicje.\n§ 3. Przepis wykonawczy.\n"
            "Wyrok WSA w Bydgoszczy\nsygn. akt II SAB/Bd 12/24\nSąd uznał, że informacja o umowach jest publiczna.")
    refs = [r for r, _ in learning.split_law(text)]
    assert refs == ["", "Art. 1", "Art. 2a", "§ 3", "sygn. akt II SAB/Bd 12/24"]


def test_text_law_is_searchable_at_once(iso):
    learning.add_law("Art. 14. Udostępnianie informacji publicznej następuje w sposób i w formie zgodnych z wnioskiem.",
                     "Ustawa o dostępie do informacji publicznej")
    hits = learning.legal_hits("Proszę o udostępnienie informacji w formie elektronicznej, zgodnie z wnioskiem.")
    assert hits and hits[0]["ref"] == "Art. 14"
    assert learning.legal_hits("Ile psów przyjęło schronisko?") == []


def test_memory_stats_and_reset(iso):
    learning.remember("Marek Zieliński", "allow", "OSOBA")
    learning.remember("Projekt Kaskada", "redact", "TAJEMNICA")
    learning.log_routing("Ile psów przyjęło schronisko?", "SCHRONISKO", "WGK")
    learning.add_law("§ 1. Termin 14 dni.", "Demo")
    st = learning.memory_stats()
    assert (st["pii_allow"], st["pii_redact"], st["routing"], st["legal_chunks"], st["laws"]) == (1, 1, 1, 1, 1)
    learning.reset("pii")
    assert learning.memory_stats()["pii_allow"] == 0 and learning.memory_stats()["routing"] == 1
    learning.reset("all")
    assert set(learning.memory_stats().values()) == {0}
    with pytest.raises(ValueError):
        learning.reset("everything")


def test_no_database_means_no_learning_and_no_file(tmp_path, monkeypatch):
    monkeypatch.setenv("UDIP_DATA_DIR", str(tmp_path / "none"))
    (tmp_path / "none").mkdir()
    assert learning.apply_rules(DOC1) == [] and learning.boost("Ile psów przyjęło schronisko?", {}) == {}
    assert learning.legal_hits("termin 14 dni") == [] and learning.memory_stats()["laws"] == 0
    assert not db.db_path().exists()


def test_export_footer_names_business_secret():
    from datetime import date

    from udip.export import metryczka
    txt = metryczka(["TAJEMNICA"], "AB", date(2026, 11, 22))
    assert "tajemnicę przedsiębiorcy" in txt and "(tajemnica przedsiębiorcy)" in txt


# ------------------------------------------------------------------ screens

@pytest.fixture
def client(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from app import store
    from app.main import app
    monkeypatch.setenv("UDIP_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("UDIP_PROVIDER", "rules")
    monkeypatch.setenv("UDIP_TODAY", "2026-11-22")
    store.reset_backend()
    c = TestClient(app)
    c.cookies.set("urzednik", "Pracownik 1")
    yield c
    store.reset_backend()


def _upload(c, text):
    r = c.post("/anonimizacja", data={"tekst": text}, follow_redirects=False)
    assert r.status_code == 303
    url = r.headers["location"]
    return url, c.get(url).text


def _span_id(html, text):
    import re
    m = re.search(r'<tr data-row="([\w-]+)">\s*<td class="frag"><span title="[^"]*">' + re.escape(text) + "</span>", html)
    assert m, text
    return m.group(1)


def test_anonimizacja_remember_buttons_teach_the_next_upload(client):
    url, html = _upload(client, DOC1)
    assert "Zapamiętaj jako wyjątek" in html and 'formaction="/pamiec"' in html
    sid = _span_id(html, "Marek Zieliński")
    r = client.post("/pamiec", data={"powrot": url, "pamiec": f"allow:{sid}", f"st_{sid}": "suggested"}, follow_redirects=False)
    assert r.status_code == 303 and "msg=zapamietano" in r.headers["location"]
    page = client.get(r.headers["location"]).text
    assert "Zapamiętano." in page
    # the fragment got the matching decision on this document
    assert f'<option value="rejected" selected>' in page.split(f'id="st_{sid}"', 1)[1].split("</select>", 1)[0]
    # mark „Projekt Kaskada” by hand, then remember it as business secret
    client.post(url, data={"powrot": url, "manual": "Projekt Kaskada"})
    html = client.get(url).text
    mid = _span_id(html, "Projekt Kaskada")
    assert "Zapamiętaj jako tajemnicę przedsiębiorcy" in html
    client.post("/pamiec", data={"powrot": url, "pamiec": f"tajemnica:{mid}", "manual": "Projekt Kaskada"})
    _, nxt = _upload(client, DOC2)
    assert "Marek Zieliński" not in nxt.split('class="span-table"', 1)[1]
    row = nxt.split("Projektu Kaskada</span>", 1)[1].split("</tr>", 1)[0]
    assert "wyuczone" in row and "tajemnica przedsiębiorcy" in row


def test_pamiec_rejects_bad_requests(client):
    assert client.post("/pamiec", data={"powrot": "/kalendarz", "pamiec": "allow:s1"}).status_code == 400
    url, _ = _upload(client, DOC1)
    assert client.post("/pamiec", data={"powrot": url, "pamiec": "allow:zz9"}).status_code == 404


def test_archiwum_law_upload_feeds_memory_and_reset(client):
    with open(DEMO_LAW, "rb") as f:
        r = client.post("/archiwum/przepisy", data={"title": "Nowelizacja UDIP 2026 (demo)"}, files={"plik": (DEMO_LAW.name, f)})
    assert r.status_code == 200 and "Pamięć instytucjonalna" in r.text
    assert learning.memory_stats()["legal_chunks"] == 4
    page = client.post("/wniosek/nowy", data={"akcja": "analizuj",
                                              "tekst": "Wnoszę o udostępnienie informacji publicznej w terminie 14 dni od dnia złożenia wniosku."}).text
    assert 'id="przepisy-baza"' in page and "nowo dodany akt prawny" in page and "§ 1" in page
    r = client.post("/archiwum/pamiec/reset", data={"rodzaj": "legal"})
    assert "Usunięto przepisy z podpowiedzi do spraw." in r.text and learning.memory_stats()["legal_chunks"] == 0
    assert client.post("/archiwum/pamiec/reset", data={"rodzaj": "x"}).status_code == 400


def test_new_request_logs_the_clerks_department_choice(client):
    q = "1. Ile psów przyjęło schronisko dla zwierząt w 2025 roku?\n2. Ile kosztowało utrzymanie schroniska?"
    r = client.post("/wniosek/nowy", data={"akcja": "zapisz", "tekst": q, "number": "BKS.IV.1431.950.2026", "received": "2026-11-20",
                                           "initials": "Pracownik 1", "summary": "Schronisko", "status": "a_brak_dzialan",
                                           "dep_1": ["WGK"], "dep_2": ["SCHRONISKO"]}, follow_redirects=False)
    assert r.status_code == 303
    rows = db._q("SELECT question_text, predicted_dept, confirmed_dept FROM routing_feedback ORDER BY id")
    assert [(x["predicted_dept"], x["confirmed_dept"]) for x in rows] == [("SCHRONISKO", "WGK"), ("SCHRONISKO", "SCHRONISKO")]
    assert learning.memory_stats()["routing"] == 1
