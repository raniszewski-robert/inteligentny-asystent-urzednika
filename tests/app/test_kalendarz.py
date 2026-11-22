"""T04: Kalendarz – demo cases, urgency colours, status change with history, XLSX import, exports."""
from __future__ import annotations

import re
from pathlib import Path

from fastapi.testclient import TestClient

from app import store
from app.main import app

UMB = Path(__file__).resolve().parents[2] / "data-partner" / "umb"


def _client():
    return TestClient(app)


def test_demo_cases_with_urgency_colours(fresh_db):
    c = _client()
    c.post("/kalendarz/demo", data={"akcja": "wczytaj"})
    html = c.get("/kalendarz?rok=wszystkie").text
    rows = re.findall(r'<tr class="u-(\w+)" id="sprawa-\d+">', html)
    assert len(rows) == 10
    assert len(set(rows)) >= 4
    assert "Tryb demonstracyjny" in html and "demo</span>" in html
    nums = [r["number"] for r in store.list_cases()]
    assert len(nums) == 10


def test_order_oldest_first(fresh_db):
    c = _client()
    c.get("/kalendarz")
    cases = store.list_cases()
    html = c.get("/kalendarz?rok=wszystkie").text
    pos = [html.index(x["number"]) for x in sorted(cases, key=lambda x: (x["received"], x["number"]))]
    assert pos == sorted(pos)


def test_status_change_persists_with_history(fresh_db):
    c = _client()
    c.cookies.set("urzednik", "Pracownik 2")
    c.get("/kalendarz")
    case = next(x for x in store.list_cases() if x["status"] == "a_brak_dzialan")
    r = c.post(f"/sprawy/{case['id']}/status", data={"status": "c_kwerenda", "rok": "wszystkie"}, headers={"HX-Request": "true"})
    assert r.status_code == 200 and r.text.startswith('<section id="rejestr">')
    assert "do 2 mies." in r.text
    c.post(f"/sprawy/{case['id']}/status", data={"status": "c_kwerenda", "extension_days": "30", "rok": "wszystkie"},
           headers={"HX-Request": "true"})
    got = store.get_case(case["id"])
    assert got["status"] == "c_kwerenda" and got["extension_days"] == 30
    h = store.history(case["id"])
    assert [(x["from_status"], x["to_status"], x["by"]) for x in h] == [("a_brak_dzialan", "c_kwerenda", "Pracownik 2")]
    html = c.get("/kalendarz?rok=wszystkie").text
    assert "Kwerenda: +30 dni" in html and "Pracownik 2</div>" in html


def test_status_change_without_htmx_redirects(fresh_db):
    c = _client()
    c.get("/kalendarz")
    case = store.list_cases()[0]
    r = c.post(f"/sprawy/{case['id']}/status", data={"status": "e_odpowiedz_wyslana"}, follow_redirects=False)
    assert r.status_code == 303
    assert store.get_case(case["id"])["answered"]
    assert c.post("/sprawy/99999/status", data={"status": "a_brak_dzialan"}).status_code == 404


def test_import_umb_xlsx_shows_six_discrepancies(fresh_db):
    c = _client()
    with open(UMB / "kalendarium_umb.xlsx", "rb") as f:
        r = c.post("/kalendarz/import", files={"plik": ("kalendarium_umb.xlsx", f)})
    assert r.status_code == 200
    assert "Niespójności w arkuszu: 6" in r.text
    assert r.text.count("<li>BKS.IV.1431.") == 6


def test_import_rejects_non_xlsx(fresh_db):
    r = _client().post("/kalendarz/import", files={"plik": ("x.txt", b"abc")})
    assert "Wybierz arkusz Excel" in r.text


def test_exports(fresh_db):
    c = _client()
    csv_ = c.get("/kalendarz/eksport.csv?rok=wszystkie")
    assert csv_.status_code == 200 and "Numer sprawy;" in csv_.text and csv_.text.count("BKS.IV.1431.") == 10
    ics = c.get("/kalendarz/eksport.ics?rok=wszystkie")
    assert ics.text.startswith("BEGIN:VCALENDAR") and ics.text.count("BEGIN:VEVENT") == 9  # one case is closed


def test_year_filter(fresh_db):
    c = _client()
    c.get("/kalendarz")
    html = c.get("/kalendarz?rok=2025").text
    assert "Brak wniosków z 2025 r." in html


def test_status_e_calls_archive_hook(fresh_db, monkeypatch):
    import sys
    import types
    calls = []
    mod = types.ModuleType("app.b2_store")
    mod.archive_sent_letter = lambda cid: calls.append(cid) or False
    monkeypatch.setitem(sys.modules, "app.b2_store", mod)
    c = _client()
    c.get("/kalendarz")
    case = next(x for x in store.list_cases() if x["status"] != "e_odpowiedz_wyslana")
    c.post(f"/sprawy/{case['id']}/status", data={"status": "d_odpowiedz_przygotowana"}, follow_redirects=False)
    c.post(f"/sprawy/{case['id']}/status", data={"status": "e_odpowiedz_wyslana"}, follow_redirects=False)
    assert calls == [case["id"]]


def test_kanban_board_and_table_view_switch(fresh_db):
    c = _client()
    r = c.get("/kalendarz?rok=wszystkie")
    assert r.status_code == 200
    assert 'data-view="tablica"' in r.text
    for col_title in ("a) Brak działań", "b) Zapytania w wydziałach", "c) Kwerenda / przedłużenie", "d–e) Gotowe i wysłane"):
        assert col_title in r.text
    cards = re.findall(r'<article class="kcard u-\w+" draggable="true" data-case-id="\d+">', r.text)
    assert len(cards) == 10
    assert c.get("/static/board.js").status_code == 200

    tab = c.get("/kalendarz?rok=wszystkie&uklad=tabela")
    assert tab.status_code == 200 and 'data-view="tabela"' in tab.text

    case = next(x for x in store.list_cases() if x["status"] == "a_brak_dzialan")
    swap_tab = c.post(
        f"/sprawy/{case['id']}/status",
        data={"status": "b_zapytania_wyslane", "rok": "wszystkie", "uklad": "tabela"},
        headers={"HX-Request": "true"},
    )
    assert swap_tab.status_code == 200 and 'data-view="tabela"' in swap_tab.text

    swap_board = c.post(
        f"/sprawy/{case['id']}/status",
        data={"status": "c_kwerenda", "rok": "wszystkie", "uklad": "tablica"},
        headers={"HX-Request": "true"},
    )
    assert swap_board.status_code == 200 and 'data-view="tablica"' in swap_board.text

