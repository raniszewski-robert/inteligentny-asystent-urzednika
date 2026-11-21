"""T19: the jury path end to end, only through the HTTP routes a clerk's browser uses.

upload request (/wniosek/nowy) → confirm into the calendar → department answers (/sprawy/{id}/odpowiedzi)
→ draft (/sprawy/{id}/projekt) → decide every span (/sprawy/{id}/anonimizacja) → DOCX/TXT exports
→ status e (POST /sprawy/{id}/status) → /archiwum search finds the case.

The database is read only to learn which spans were accepted, so the exports can be checked for leaks.
"""
from __future__ import annotations

import html
import io
import re
import zipfile
from pathlib import Path

import docx
import pytest

UMB = Path(__file__).resolve().parents[2] / "data-partner" / "umb"
CASE = UMB / "przypadek_543"
PROBKI = UMB / "probki"


# ---- helpers: read a page the way a browser submits it -------------------------------------------------------------

def _value(page: str, name: str) -> str:
    m = re.search(rf'<input[^>]*name="{re.escape(name)}"[^>]*value="([^"]*)"', page)
    return html.unescape(m.group(1)) if m else ""


def _textarea(page: str, name: str) -> str | None:
    m = re.search(rf'<textarea[^>]*name="{re.escape(name)}"[^>]*>(.*?)</textarea>', page, re.S)
    if not m:
        return None
    body = html.unescape(m.group(1))
    return body[1:] if body.startswith("\n") else body  # browsers drop the newline right after <textarea>


def _checked(page: str, prefix: str) -> list[tuple[str, str]]:
    out = []
    for tag in re.findall(rf'<input[^>]*name="{prefix}[^"]*"[^>]*>', page):
        if " checked" in tag:
            out.append((re.search(r'name="([^"]+)"', tag).group(1), html.unescape(re.search(r'value="([^"]*)"', tag).group(1))))
    return out


def _form(pairs: list[tuple[str, str]]) -> dict[str, list[str]]:
    """Repeated form fields as dict of lists (this httpx treats a list of pairs passed as data= as raw content)."""
    out: dict[str, list[str]] = {}
    for k, v in pairs:
        out.setdefault(k, []).append(v)
    return out


def _upload_request(client, path: Path):
    with open(path, "rb") as f:
        r = client.post("/wniosek/nowy", data={"akcja": "analizuj"}, files={"plik": (path.name, f)})
    assert r.status_code == 200, r.text[:500]
    return r.text


def _confirm(client, page: str, status: str = "b_zapytania_wyslane"):
    """Press 'Zapisz w kalendarzu' with the defaults the analysis page proposes."""
    data: list[tuple[str, str]] = [("akcja", "zapisz"), ("tekst", _textarea(page, "tekst") or ""), ("status", status)]
    for k in ("plik_nazwa", "plik_zapis", "jakosc", "number", "received", "initials", "applicant_label"):
        data.append((k, _value(page, k)))
    data.append(("summary", _textarea(page, "summary") or ""))
    data += _checked(page, "dep_")
    return client.post("/wniosek/nowy", data=_form(data), follow_redirects=False), dict(data)


def _docx_everything(data: bytes) -> str:
    """Visible text of every paragraph and table plus the tag-stripped XML of every part of the package."""
    d = docx.Document(io.BytesIO(data))
    parts = [p.text for p in d.paragraphs]
    parts += [c.text for t in d.tables for row in t.rows for c in row.cells]
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for name in z.namelist():
            if name.endswith((".xml", ".rels")):
                parts.append(re.sub(r"<[^>]+>", "", z.read(name).decode("utf-8", "replace")))
    return "\n".join(parts)


def _assert_no_leak(output: str, secrets: list[str], where: str) -> None:
    flat = re.sub(r"\s+", " ", output)
    for s in secrets:
        assert s not in output and re.sub(r"\s+", " ", s) not in flat, f"{where}: wyciek {s!r}"


# ---- the path ----------------------------------------------------------------------------------------------------

APPLICANT = "Anna Nowak-Kowalska\nul. Słoneczna 7/12\n85-001 Bydgoszcz\nanna.nowak@example.com\n\n"
SIGNATURE = "\n\nZ poważaniem\nAnna Nowak-Kowalska\ntel. 601 234 567\n"


def test_jury_path_543(client, tmp_path):
    from app import b2_store
    from udip import db

    # 1. Nowy wniosek: the UMB 543 request (already anonymized by UMB) as it arrives, with the applicant's own data
    req = tmp_path / "wniosek_543.txt"
    req.write_text(APPLICANT + (CASE / "wniosek.txt").read_text(encoding="utf-8") + SIGNATURE, encoding="utf-8")
    page = _upload_request(client, req)
    assert page.count('<fieldset class="routing">') == 5, "wniosek 543 ma 5 pytań"
    deps = {v for _, v in _checked(page, "dep_")}
    assert deps, "analiza powinna zaproponować wydziały"

    # 2. Confirm into the calendar
    r, sent = _confirm(client, page)
    assert r.status_code == 303, r.text[:800]
    m = re.fullmatch(r"/sprawy/(\d+)", r.headers["location"])
    assert m, r.headers["location"]
    cid, number = int(m.group(1)), sent["number"]
    assert number and number != "BKS.IV.1431.543.2026"  # a new case next to the seeded demo one
    cal = client.get("/kalendarz?rok=wszystkie")
    assert cal.status_code == 200 and number in cal.text
    case = client.get(f"/sprawy/{cid}")
    assert case.status_code == 200 and number in case.text

    # 3. Department answers, department detected from the file
    files = [("pliki", (p.name, p.read_bytes(), "text/plain")) for p in (CASE / "SCHRONISKO.txt", CASE / "WGK.txt")]
    r = client.post(f"/sprawy/{cid}/odpowiedzi", data={"department": ""}, files=files)
    assert r.status_code == 200, r.text[:500]
    assert "SCHRONISKO.txt" in r.text and "WGK.txt" in r.text
    answers = {d["filename"]: d["department"] for d in db.documents(cid, "dept_answer")}
    assert answers == {"SCHRONISKO.txt": "SCHRONISKO", "WGK.txt": "WGK"}, answers

    # 4. Draft: one 'Ad' paragraph per question, figures from the answers
    r = client.get(f"/sprawy/{cid}/projekt")
    assert r.status_code == 200, r.text[:500]
    letter = html.unescape(r.text)
    for n in range(1, 6):
        assert f"Ad {n}" in letter, f"brak Ad {n}"
    assert "839 psom" in letter

    # 5. Anonymization: exports are refused before approval
    r = client.get(f"/sprawy/{cid}/anonimizacja")
    assert r.status_code == 200
    assert client.get(f"/sprawy/{cid}/eksport/zanonimizowana.docx").status_code == 409
    selects = re.findall(r'name="(st_[^"]+)"', r.text)
    assert selects, "brak fragmentów do decyzji"
    draft = b2_store.get_draft(cid)
    assert {f"st_{s['id']}" for s in draft["spans"]} == set(selects)

    # decide every span (accept all, keep one as rejected to exercise both decisions), then approve
    data = [(name, "accepted") for name in selects]
    data[-1] = (selects[-1], "rejected")
    edited = _textarea(r.text, "edited")
    if edited is not None:
        data.append(("edited", edited))
    data.append(("manual", _textarea(r.text, "manual") or ""))
    r = client.post(f"/sprawy/{cid}/anonimizacja", data=_form(data + [("action", "zatwierdz")]), follow_redirects=False)
    assert r.status_code == 303, html.unescape(r.text)[:1500]
    assert r.headers["location"].endswith("msg=zatwierdzono")
    draft = b2_store.get_draft(cid)
    assert draft["version"] == 1, "zatwierdzenie bez zmian treści nie powinno tworzyć nowej wersji"
    assert not [s for s in draft["spans"] if s["status"] in ("suggested", "review")]
    text = draft["text"]
    accepted = [s for s in draft["spans"] if s["status"] == "accepted"]
    assert accepted
    secret_all = [text[s["start"]:s["end"]] for s in accepted]
    secret_send = [text[s["start"]:s["end"]] for s in accepted if not s.get("addressee")]
    assert any("Nowak-Kowalska" in x for x in secret_all), secret_all  # the applicant's own data was detected and accepted

    # 6. Exports: open every file and look for each accepted span's text
    for version, secrets in (("zanonimizowana", secret_all), ("do_wysylki", secret_send)):
        rd = client.get(f"/sprawy/{cid}/eksport/{version}.docx")
        assert rd.status_code == 200 and rd.content[:2] == b"PK", (version, rd.status_code)
        body = _docx_everything(rd.content)
        assert "839 psom" in body
        _assert_no_leak(body, secrets, f"{version}.docx")
        rt = client.get(f"/sprawy/{cid}/eksport/{version}.txt")
        assert rt.status_code == 200
        assert "839 psom" in rt.text
        _assert_no_leak(rt.text, secrets, f"{version}.txt")

    # 7. Status e from the case page
    r = client.post(f"/sprawy/{cid}/status", data={"status": "e_odpowiedz_wyslana", "widok": "sprawa"}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == f"/sprawy/{cid}"
    case = db.get_case(cid)
    assert case["status"] == "e_odpowiedz_wyslana"
    assert [h["to_status"] for h in db.history(cid)][-1] == "e_odpowiedz_wyslana"

    # 8. Archive search finds the sent case, anonymized
    r = client.get("/archiwum", params={"q": "opieka nad bezdomnymi zwierzętami 839 psom"})
    assert r.status_code == 200
    assert number in r.text, "wyszukiwarka archiwum nie znalazła wysłanej sprawy"
    rec = next(x for x in db.archive_records() if x["id"] == number)
    assert "839 psom" in rec["response_text"]
    _assert_no_leak(rec["response_text"], secret_all, "archiwum")
    r = client.get(f"/archiwum/sprawa/{number}")
    assert r.status_code == 200 and number in r.text


@pytest.mark.parametrize("name", sorted(p.name for p in PROBKI.iterdir()))
def test_probki_upload_and_confirm(client, name):
    """Each UMB sample request (DOCX, PDF) uploads, gets questions, and lands in the calendar."""
    page = _upload_request(client, PROBKI / name)
    assert '<fieldset class="routing">' in page, "brak pytań po analizie"
    r, sent = _confirm(client, page, status="a_brak_dzialan")
    assert r.status_code == 303, html.unescape(r.text)[:800]
    cid = int(r.headers["location"].rsplit("/", 1)[1])
    assert sent["number"] in client.get("/kalendarz?rok=wszystkie").text
    case = client.get(f"/sprawy/{cid}")
    assert case.status_code == 200 and sent["number"] in case.text
