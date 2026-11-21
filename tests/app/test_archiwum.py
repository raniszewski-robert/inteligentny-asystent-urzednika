"""T17: Archiwum / Baza wiedzy – search with filters, law upload searchable by §, adding a case changes the next search."""
from __future__ import annotations

import io

from docx import Document
from fastapi.testclient import TestClient

from app.main import app
from app.routes.archiwum import law_chunks

# Synthetic excerpt in the structure of the UMB order on UDIP (the real PDF is kept by the team, outside the repo).
ORDER = [
    "Zarządzenie Prezydenta Miasta Bydgoszczy w sprawie zasad i trybu udostępniania informacji publicznej",
    "§ 1. Zarządzenie określa zasady udostępniania informacji publicznej w Urzędzie Miasta Bydgoszczy.",
    "§ 8. Informację publiczną udostępnia się w Biuletynie Informacji Publicznej.",
    "§ 11. Wydział przygotowuje projekt odpowiedzi oraz dokonuje anonimizacji danych osobowych.",
    "§ 12. Decyzje o odmowie udostępnienia informacji publicznej oraz o umorzeniu postępowania podpisuje Prezydent Miasta "
    "lub osoba przez niego upoważniona.",
    "§ 13. Wnioski rejestruje Biuro Komunikacji Społecznej.",
]


def _docx(paragraphs: list[str]) -> bytes:
    d = Document()
    for p in paragraphs:
        d.add_paragraph(p)
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


def test_archive_lists_umb_cases_and_filters(fresh_db):
    c = TestClient(app)
    html = c.get("/archiwum").text
    assert "Sprawy w archiwum: 10." in html and "BKS.IV.1431.543.2026" in html
    r = c.get("/archiwum", params={"q": "bezdomne zwierzęta schronisko"}).text
    assert "BKS.IV.1431.543.2026" in r and "BKS.IV.1431.293.2025" in r
    r = c.get("/archiwum", params={"q": "bezdomne zwierzęta schronisko", "rok": "2025"}).text
    assert "BKS.IV.1431.293.2025" in r and "BKS.IV.1431.543.2026" not in r
    r = c.get("/archiwum", params={"q": "bezdomne zwierzęta schronisko", "wydzial": "WE"}).text
    assert "Brak spraw" in r


def test_archive_case_page(fresh_db):
    c = TestClient(app)
    r = c.get("/archiwum/sprawa/BKS.IV.1431.307.2025")
    assert r.status_code == 200 and "Odpowiedź" in r.text and "uczniów" in r.text
    assert c.get("/archiwum/sprawa/NIE.MA").status_code == 404


def test_law_upload_makes_paragraph_searchable(fresh_db):
    c = TestClient(app)
    assert "§ 12" not in c.get("/archiwum", params={"q": "kto podpisuje decyzje"}).text
    r = c.post("/archiwum/przepisy", data={"title": "Zarządzenie UDIP"},
               files={"plik": ("zarzadzenie_udip.docx", _docx(ORDER))})
    assert "Dodano akt „Zarządzenie UDIP”: 6 fragmentów" in r.text
    r = c.get("/archiwum", params={"q": "kto podpisuje decyzje"}).text
    hits = r[r.index("<h2>Przepisy</h2>"):]
    assert hits.index("Zarządzenie UDIP § 12") < hits.index("</ol>")
    assert hits.split("<li>")[1].count("§ 12") >= 1  # first hit is § 12
    law = c.get("/archiwum/przepis/1")
    assert law.status_code == 200 and 'id="p12"' in law.text


def test_law_chunks_without_paragraphs():
    ch = law_chunks({"id": 3, "title": "Ustawa", "text": "słowo " * 450})
    assert len(ch) == 3 and ch[0]["title"] == "Ustawa"


def test_adding_a_case_changes_next_search(fresh_db):
    c = TestClient(app)
    q = {"q": "hulajnogi elektryczne wypożyczalnie"}
    before = c.get("/archiwum", params=q).text
    assert "BKS.IV.1431.900.2025" not in before
    r = c.post("/archiwum/import", data={"id": "BKS.IV.1431.900.2025", "date": "2025-05-05", "title": "Wypożyczalnie hulajnóg elektrycznych",
                                         "departments": "zdmikp", "request_text": "Ile wypożyczalni hulajnóg elektrycznych działa w Bydgoszczy?",
                                         "response_text": "W Bydgoszczy działają trzy wypożyczalnie hulajnóg elektrycznych."},
               follow_redirects=False)
    assert r.status_code == 303 and "dodano=BKS.IV.1431.900.2025" in r.headers["location"]
    after = c.get("/archiwum", params=q).text
    assert "BKS.IV.1431.900.2025" in after
    page = c.get(r.headers["location"]).text
    assert "nowa</span>" in page
    assert "ZDMiKP" in c.get("/archiwum/sprawa/BKS.IV.1431.900.2025").text


def test_folder_import_pairs_files(fresh_db):
    c = TestClient(app)
    files = [("pliki", ("BKS.IV.1431.901.2025_wniosek.txt", "Wniosek o liczbę latarni ulicznych w Fordonie.".encode())),
             ("pliki", ("BKS.IV.1431.901.2025_odpowiedz.txt", "W Fordonie jest 1200 latarni ulicznych.".encode()))]
    r = c.post("/archiwum/import", files=files, follow_redirects=False)
    assert r.status_code == 303
    html = c.get("/archiwum", params={"q": "latarnie Fordon"}).text
    assert "BKS.IV.1431.901.2025" in html
    assert "Nie zaimportowano" in c.post("/archiwum/import", files=[("pliki", ("x.exe", b"MZ"))]).text


def test_import_requires_number_and_text(fresh_db):
    r = TestClient(app).post("/archiwum/import", data={"id": "", "request_text": ""})
    assert "Podaj numer sprawy" in r.text
