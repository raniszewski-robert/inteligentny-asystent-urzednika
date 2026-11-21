"""T05: Nowy wniosek – upload, analysis, quality warning, confirm into the register."""
from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app import store
from app.main import app

UMB = Path(__file__).resolve().parents[2] / "data-partner" / "umb"
F599 = UMB / "probki" / "Wniosek - BKS.IV.1431.599.2026.docx"


def _upload(c, path: Path):
    with open(path, "rb") as f:
        return c.post("/wniosek/nowy", data={"akcja": "analizuj"}, files={"plik": (path.name, f)})


def test_form_renders(fresh_db):
    r = TestClient(app).get("/wniosek/nowy")
    assert r.status_code == 200 and 'name="plik"' in r.text and 'aria-current="page"' in r.text


def test_upload_599_shows_questions_similar_case_and_department(fresh_db):
    r = _upload(TestClient(app), F599)
    assert r.status_code == 200
    html = r.text
    assert html.count('<fieldset class="routing">') == 2
    assert "BKS.IV.1431.307.2025" in html and "starsza niż rok" in html
    assert 'value="WE" checked' in html
    assert 'name="number" type="text" value="BKS.IV.1431.' in html


def test_low_quality_text_shows_manual_entry_warning(fresh_db):
    junk = "EEEE HHHH xqzt prw kkkk ŁŁŁŁ zzzz 1234 brrrr mmmmm qwrt " * 8
    r = TestClient(app).post("/wniosek/nowy", data={"akcja": "analizuj"}, files={"plik": ("Wniosek - skan.txt", junk.encode())})
    assert "Tekst do wpisania ręcznie" in r.text and 'id="ostrzezenie-jakosc"' in r.text


def test_wrong_format_and_empty(fresh_db):
    c = TestClient(app)
    assert "Obsługiwane formaty" in c.post("/wniosek/nowy", data={"akcja": "analizuj"}, files={"plik": ("a.exe", b"MZ")}).text
    assert "Dodaj plik wniosku" in c.post("/wniosek/nowy", data={"akcja": "analizuj"}).text


def test_confirm_creates_case_visible_in_calendar(fresh_db):
    c = TestClient(app)
    c.cookies.set("urzednik", "Pracownik 3")
    text = (UMB / "przypadek_543" / "wniosek.txt").read_text(encoding="utf-8")
    page = c.post("/wniosek/nowy", data={"akcja": "analizuj", "tekst": text}).text
    assert "Pytania i wydziały" in page
    r = c.post("/wniosek/nowy", data={"akcja": "zapisz", "tekst": text, "number": "BKS.IV.1431.700.2026", "received": "2026-11-20",
                                      "initials": "Pracownik 3", "summary": "Schronisko – psy i koty", "status": "b_zapytania_wyslane",
                                      "dep_1": ["WGK"], "dep_2": ["WGK", "SCHRONISKO"]}, follow_redirects=False)
    assert r.status_code == 303
    cid = int(r.headers["location"].rsplit("/", 1)[1])
    case = store.get_case(cid)
    assert case["number"] == "BKS.IV.1431.700.2026" and case["status"] == "b_zapytania_wyslane"
    assert case["departments"] == ["WGK", "SCHRONISKO"]
    assert case["analysis"]["questions"]
    assert [d["kind"] for d in store.documents(cid)] == ["request"]
    assert [(h["to_status"], h["by"]) for h in store.history(cid)] == [("b_zapytania_wyslane", "Pracownik 3")]
    assert "BKS.IV.1431.700.2026" in c.get("/kalendarz?rok=2026").text
    dup = c.post("/wniosek/nowy", data={"akcja": "zapisz", "tekst": text, "number": "BKS.IV.1431.700.2026", "received": "2026-11-20"})
    assert "jest już w rejestrze" in dup.text


def test_next_number(fresh_db):
    store.list_cases()
    assert store.next_number(2026) == "BKS.IV.1431.600.2026"
    assert store.next_number(2031) == "BKS.IV.1431.1.2031"
