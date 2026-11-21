"""T06: Sprawa – case header, department answers with departments, history with initials, analysis of demo cases."""
from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app import services, store
from app.main import app

C543 = Path(__file__).resolve().parents[2] / "data-partner" / "umb" / "przypadek_543"


def _case(number: str) -> dict:
    store.list_cases()
    return store.case_by_number(number)


def test_case_page_header(fresh_db):
    c = _case("BKS.IV.1431.543.2026")
    html = TestClient(app).get(f"/sprawy/{c['id']}").text
    assert "BKS.IV.1431.543.2026" in html and "Termin ustawowy" in html and "Termin bezpieczny" in html
    assert "Analizuj wniosek" in html  # demo case: request text comes from the UMB archive
    assert TestClient(app).get("/sprawy/99999").status_code == 404


def test_543_with_wgk_and_schronisko_answers(fresh_db):
    c = _case("BKS.IV.1431.543.2026")
    cl = TestClient(app)
    files = [("pliki", ("WGK.txt", (C543 / "WGK.txt").read_bytes())), ("pliki", ("SCHRONISKO.txt", (C543 / "SCHRONISKO.txt").read_bytes()))]
    r = cl.post(f"/sprawy/{c['id']}/odpowiedzi", data={"department": ""}, files=files)
    assert r.status_code == 200
    docs = store.documents(c["id"], "dept_answer")
    assert sorted((d["filename"], d["department"]) for d in docs) == [("SCHRONISKO.txt", "SCHRONISKO"), ("WGK.txt", "WGK")]
    html = cl.get(f"/sprawy/{c['id']}").text
    assert "WGK.txt" in html and "SCHRONISKO.txt" in html
    assert '<option value="WGK" selected>' in html and '<option value="SCHRONISKO" selected>' in html


def test_department_from_signature_not_filename(fresh_db):
    text = (C543 / "WGK.txt").read_text(encoding="utf-8")
    assert services.detect_department("odpowiedz.txt", text) == "WGK"
    assert services.detect_department("pismo.txt", "Bydgoszcz\nSCHRONISKO.0012.31.2026\nBiuro Komunikacji Społecznej") == "SCHRONISKO"
    assert services.detect_department("x.txt", "Wydział Edukacji i Sportu informuje") == "WE"
    assert services.detect_department("x.txt", "Biuro Komunikacji Społecznej w miejscu") == ""


def test_department_correction_and_chosen_department(fresh_db):
    c = _case("BKS.IV.1431.543.2026")
    cl = TestClient(app)
    cl.post(f"/sprawy/{c['id']}/odpowiedzi", data={"department": "WE"}, files=[("pliki", ("a.txt", "Tekst odpowiedzi wydziału.".encode()))])
    d = store.documents(c["id"], "dept_answer")[0]
    assert d["department"] == "WE"
    cl.post(f"/sprawy/{c['id']}/dokumenty/{d['id']}/wydzial", data={"department": "WGK"})
    assert store.documents(c["id"], "dept_answer")[0]["department"] == "WGK"


def test_history_shows_every_change_with_initials(fresh_db):
    c = _case("BKS.IV.1431.599.2026")
    cl = TestClient(app)
    for who, st in (("Pracownik 1", "b_zapytania_wyslane"), ("Pracownik 2", "c_kwerenda"), ("Pracownik 3", "d_odpowiedz_przygotowana")):
        cl.cookies.set("urzednik", who)
        r = cl.post(f"/sprawy/{c['id']}/status", data={"status": st, "widok": "sprawa", "note": ""}, follow_redirects=False)
        assert r.headers["location"] == f"/sprawy/{c['id']}"
    html = cl.get(f"/sprawy/{c['id']}").text
    hist = html[html.index("<h2>Historia</h2>"):]
    for who in ("Pracownik 1", "Pracownik 2", "Pracownik 3"):
        assert f"<td>{who}</td>" in hist
    assert hist.count("→") == 3


def test_analyze_demo_case_from_archive(fresh_db):
    c = _case("BKS.IV.1431.543.2026")
    cl = TestClient(app)
    r = cl.post(f"/sprawy/{c['id']}/analiza", follow_redirects=False)
    assert r.status_code == 303
    got = store.get_case(c["id"])
    assert len(got["analysis"]["questions"]) == 5
    assert all(s["id"] != c["number"] for s in got["analysis"]["similar_cases"])
    html = cl.get(f"/sprawy/{c['id']}").text
    assert html.count('<li><p>') >= 5 and "WGK" in html
    assert [d["kind"] for d in store.documents(c["id"])] == ["request"]


def test_draft_button_links_to_projekt(fresh_db):
    c = _case("BKS.IV.1431.543.2026")
    html = TestClient(app).get(f"/sprawy/{c['id']}").text
    assert f'action="/sprawy/{c["id"]}/projekt"' in html and 'value="udostepnienie"' in html
