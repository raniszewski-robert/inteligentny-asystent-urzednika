"""T08 Anonimizacja: grey → black after acceptance, zero leaks in exported DOCX/TXT, standalone upload, archive on send.

The leak bar: open every exported DOCX (all paragraphs, tables, headers, footers, and the raw XML of every part)
and search it for the text of every accepted span. None may appear.
"""
from __future__ import annotations

import html as h
import io
import re
import zipfile

import docx
import pytest
from fastapi.testclient import TestClient

from app import b2_redact as rd
from app import b2_store as store
from app.main import app
from tests.app._b2_seed import isolate, seed_543, seed_case

PII = {
    "PESEL": "44051401359",
    "DOWOD": "ABA300000",
    "IBAN": "PL61 1090 1014 0000 0712 1981 2874",
    "ADRES": "ul. Długa 15/4",
    "URODZENIE": "ur. 14.05.1944 r. w Toruniu",
    "PODPIS": "Anna Kowalska-Wiśniewska",
    "TELEFON": "+48 601 234 567",
    "EMAIL": "anna.kw@example.com",
}

TEST_FILE = f"""Bydgoszcz, 2 listopada 2026 r.

{PII['PODPIS']}
{PII['ADRES']}
85-034 Bydgoszcz
tel. {PII['TELEFON']}
e-mail: {PII['EMAIL']}

Prezydent Miasta Bydgoszczy

WNIOSEK

Ja, niżej podpisana, {PII['URODZENIE']}, PESEL {PII['PESEL']}, legitymująca się dowodem osobistym {PII['DOWOD']},
proszę o zwrot opłaty na rachunek {PII['IBAN']}.
Wnioskodawczyni choruje na cukrzycę i leczy się w poradni przy ul. Długa 15/4 razem z Janem Nowakiem.

Z poważaniem
{PII['PODPIS']}
"""


@pytest.fixture()
def client(tmp_path, monkeypatch):
    isolate(tmp_path, monkeypatch)
    return TestClient(app)


def docx_everything(data: bytes) -> str:
    """Visible text plus the tag-stripped XML of every part of the package."""
    parts = [rd.docx_text(data)]
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for name in z.namelist():
            if name.endswith((".xml", ".rels")):
                parts.append(re.sub(r"<[^>]+>", "", z.read(name).decode("utf-8", "replace")))
    return "\n".join(parts)


def assert_no_leak(output: str, secrets: list[str]):
    flat = re.sub(r"\s+", " ", output)
    for s in secrets:
        assert s not in output and re.sub(r"\s+", " ", s) not in flat, f"wyciek: {s!r}"


def _token(r) -> str:
    return re.search(r"/anonimizacja/([a-f0-9]{16})", str(r.url)).group(1)


def _form(page: str) -> dict:
    """Current decisions as the browser would post them."""
    return {m.group(1): m.group(2) for m in re.finditer(
        r'<select id="(st_[^"]+)"[^>]*>.*?<option value="([^"]+)"[^>]*selected', page, re.S)}


def _accepted_texts(text: str, spans: list[dict]) -> list[str]:
    return [text[s["start"]:s["end"]] for s in spans if s["status"] == "accepted"]


# ---- standalone mode: what the jury does --------------------------------------------------------------------------

@pytest.mark.parametrize("kind", ["txt", "docx", "paste"])
def test_standalone_zero_leaks(client, tmp_path, kind):
    if kind == "txt":
        r = client.post("/anonimizacja", files={"plik": ("wniosek.txt", TEST_FILE.encode("utf-8"), "text/plain")})
    elif kind == "docx":
        d = docx.Document()
        for line in TEST_FILE.split("\n"):
            d.add_paragraph(line)
        buf = io.BytesIO()
        d.save(buf)
        r = client.post("/anonimizacja", files={"plik": ("wniosek.docx", buf.getvalue(), "application/octet-stream")})
    else:
        r = client.post("/anonimizacja", data={"tekst": TEST_FILE})
    assert r.status_code == 200, r.text[:500]
    token = _token(r)
    page = r.text
    # grey before acceptance
    assert 'class="sp sp-suggested" data-id' in page and 'class="sp sp-accepted" data-id' not in page
    for k in ("PESEL", "DOWOD", "IBAN", "ADRES", "URODZENIE", "PODPIS"):
        assert h.escape(PII[k]) in page
    # exports are refused before approval
    assert client.get(f"/anonimizacja/{token}/eksport/zanonimizowana.docx").status_code == 409
    # accept all suggestions → black; approval still refused while review spans remain
    r = client.post(f"/anonimizacja/{token}", data={**_form(page), "action": "akceptuj"})
    assert 'class="sp sp-accepted" data-id' in r.text
    doc = store.get_doc(token)
    if rd.undecided(doc["spans"]):
        r = client.post(f"/anonimizacja/{token}", data={**_form(r.text), "action": "zatwierdz"})
        assert "Bez decyzji" in r.text
        assert client.get(f"/anonimizacja/{token}/eksport/zanonimizowana.docx").status_code == 409
    r = client.post(f"/anonimizacja/{token}", data={**_form(r.text), "action": "wszystkie"})
    r = client.post(f"/anonimizacja/{token}", data={**_form(r.text), "action": "zatwierdz"})
    assert "Anonimizacja zatwierdzona" in r.text
    doc = store.get_doc(token)
    accepted = _accepted_texts(doc["text"], doc["spans"])
    assert len(accepted) >= 8
    secrets = sorted(set(accepted) | set(PII.values()) | {"Kowalska-Wiśniewska", "Janem Nowakiem", "cukrzycę"})

    dx = client.get(f"/anonimizacja/{token}/eksport/zanonimizowana.docx")
    assert dx.status_code == 200 and dx.headers["content-type"].startswith("application/vnd.openxmlformats")
    assert_no_leak(docx_everything(dx.content), secrets)
    assert "Prezydent Miasta Bydgoszczy" in rd.docx_text(dx.content)  # public text stays
    tx = client.get(f"/anonimizacja/{token}/eksport/zanonimizowana.txt")
    assert tx.status_code == 200
    assert_no_leak(tx.text, secrets)
    assert "[PESEL]" in tx.text and "[nr rachunku]" in tx.text
    # no "do wysyłki" version for a standalone file
    assert client.get(f"/anonimizacja/{token}/eksport/do_wysylki.docx").status_code == 404


def test_standalone_manual_fragment_and_toggle(client):
    text = "Notatka służbowa. Rozmowa z kierownikiem budowy Zenobiuszem Xyzackim w sprawie ogrodzenia.\nPESEL 44051401359."
    r = client.post("/anonimizacja", data={"tekst": text})
    token = _token(r)
    form = _form(r.text)
    pesel_id = next(s["id"] for s in store.get_doc(token)["spans"] if s["type"] == "PESEL")
    form[f"st_{pesel_id}"] = "rejected"  # clerk leaves it visible on purpose
    r = client.post(f"/anonimizacja/{token}", data={**form, "manual": "Zenobiuszem Xyzackim", "action": "wszystkie"})
    doc = store.get_doc(token)
    man = [s for s in doc["spans"] if s["type"] == "RECZNIE"]
    assert man and man[0]["status"] == "accepted" and man[0]["text"] == "Zenobiuszem Xyzackim"
    r = client.post(f"/anonimizacja/{token}", data={**_form(r.text), "manual": "Zenobiuszem Xyzackim", "action": "zatwierdz"})
    assert "Anonimizacja zatwierdzona" in r.text
    out = client.get(f"/anonimizacja/{token}/eksport/zanonimizowana.docx").content
    body = docx_everything(out)
    assert_no_leak(body, ["Zenobiuszem Xyzackim", "Xyzackim"])
    assert "44051401359" in body  # rejected = stays visible
    # delete
    client.post(f"/anonimizacja/{token}", data={"action": "usun"})
    assert store.get_doc(token) is None and client.get(f"/anonimizacja/{token}").status_code == 404


def test_standalone_edit_redetects_and_keeps_decisions(client):
    r = client.post("/anonimizacja", data={"tekst": "Wniosek złożyła Anna Nowak, PESEL 44051401359."})
    token = _token(r)
    r = client.post(f"/anonimizacja/{token}", data={**_form(r.text), "action": "akceptuj"})
    r = client.post(f"/anonimizacja/{token}", data={**_form(r.text), "action": "zapisz",
                    "edited": "Wniosek złożyła Anna Nowak, PESEL 44051401359, tel. 601 234 567."})
    doc = store.get_doc(token)
    by_type = {s["type"]: s["status"] for s in doc["spans"]}
    assert by_type["PESEL"] == "accepted" and by_type["TELEFON"] == "suggested"


def test_upload_errors(client):
    assert client.post("/anonimizacja", data={}).status_code == 400
    r = client.post("/anonimizacja", files={"plik": ("x.exe", b"MZ", "application/octet-stream")})
    assert r.status_code == 400 and "Obsługiwane pliki" in r.text
    assert client.get("/anonimizacja/../../etc").status_code == 404
    assert client.get("/anonimizacja/0123456789abcdef").status_code == 404
    page = client.get("/anonimizacja")
    assert page.status_code == 200 and 'enctype="multipart/form-data"' in page.text


def test_nested_special_sentence_does_not_leak():
    """A special-category sentence span contains a name span: both accepted must not print the sentence."""
    t = "Wnioskodawca Jan Kowalski choruje na cukrzycę i leczy się w poradni. Mieszka przy ul. Długa 15/4."
    spans = [dict(s, status="accepted") for s in rd.detect_spans(t)]
    assert any(s["type"].startswith("SZCZEGOLNE") for s in spans)
    for v in ("zanonimizowana", "do_wysylki"):
        out = rd.docx_text(rd.export_docx(t, spans, v)) + rd.export_text(t, spans, v)
        assert_no_leak(out, _accepted_texts(t, spans) + ["choruje", "Kowalski"])


# ---- case mode: letter, two versions, archive -----------------------------------------------------------------------

REQUEST = """Jan Wiśniewski
ul. Lipowa 7/2
85-001 Bydgoszcz
jan.wisniewski@example.com

Wniosek o udostępnienie informacji publicznej

Proszę o informację, ile drzew wycięto w 2025 r. w parku przy ul. Gdańskiej.
"""
ANSWER = """WZ.0012.5.2026

Uprzejmie informuję, że w 2025 r. wycięto 14 drzew. Wycinkę zgłosiła mieszkanka Barbara Zielińska, PESEL 44051401359.

Sprawę prowadzi: Ewa Nowak
"""


def test_case_letter_two_versions_and_archive(client):
    cid = seed_case("BKS.IV.1431.700.2026", REQUEST, [("WZ.txt", ANSWER)])
    r = client.get(f"/sprawy/{cid}/anonimizacja", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == f"/sprawy/{cid}/projekt"
    client.get(f"/sprawy/{cid}/projekt")
    r = client.get(f"/sprawy/{cid}/anonimizacja")
    assert r.status_code == 200 and "adresat" in r.text
    d = store.get_draft(cid)
    texts = {(s["type"], s["text"]): s for s in d["spans"]}
    assert ("OSOBA", "Jan Wiśniewski") in texts and texts[("OSOBA", "Jan Wiśniewski")]["addressee"]
    assert ("PESEL", "44051401359") in texts and not texts[("PESEL", "44051401359")]["addressee"]
    assert client.get(f"/sprawy/{cid}/eksport/zanonimizowana.docx").status_code == 409
    r = client.post(f"/sprawy/{cid}/anonimizacja", data={**_form(r.text), "action": "wszystkie"})
    assert "UWAGA PRAWNA" in r.text  # third-party data blacked in the body = partial refusal warning
    r = client.post(f"/sprawy/{cid}/anonimizacja", data={**_form(r.text), "action": "zatwierdz"})
    assert "Anonimizacja zatwierdzona" in r.text
    d = store.get_draft(cid)
    assert d["final_anonymized"] and d["final_to_send"]
    addressee = [d["text"][s["start"]:s["end"]] for s in d["spans"] if s.get("addressee")]
    third = [d["text"][s["start"]:s["end"]] for s in d["spans"] if s["status"] == "accepted" and not s.get("addressee")]
    assert "Barbara Zielińska" in third and "44051401359" in third

    anon = client.get(f"/sprawy/{cid}/eksport/zanonimizowana.docx")
    assert anon.status_code == 200
    assert_no_leak(docx_everything(anon.content), addressee + third)
    assert_no_leak(client.get(f"/sprawy/{cid}/eksport/zanonimizowana.txt").text, addressee + third)
    assert "14 drzew" in rd.docx_text(anon.content)

    send = client.get(f"/sprawy/{cid}/eksport/do_wysylki.docx")
    body = rd.docx_text(send.content)
    assert "Jan Wiśniewski" in body and "ul. Lipowa 7/2" in body  # the addressee stays on the letter that is sent
    assert_no_leak(docx_everything(send.content), third)
    assert_no_leak(client.get(f"/sprawy/{cid}/eksport/do_wysylki.txt").text, third)

    # status e → archive, searchable, anonymized
    r = client.post(f"/sprawy/{cid}/anonimizacja", data={"action": "wyslano"})
    assert "Pismo dodano do archiwum" in r.text
    assert store.get_case(cid)["status"] == "e_odpowiedz_wyslana"
    rec = next(a for a in store.archive_records() if a["id"] == "BKS.IV.1431.700.2026")
    assert_no_leak(rec["request_text"] + rec["response_text"], addressee + third)
    from udip.search import Archive
    hits = Archive(store.archive_records()).search("ile drzew wycięto w parku przy ul. Gdańskiej")
    assert hits and hits[0]["id"] == "BKS.IV.1431.700.2026"
    assert any(x["kind"] == "letter" for x in store.documents(cid))


def test_case_decision_change_needs_new_approval(client):
    cid = seed_543()
    client.get(f"/sprawy/{cid}/projekt")
    r = client.get(f"/sprawy/{cid}/anonimizacja")
    r = client.post(f"/sprawy/{cid}/anonimizacja", data={**_form(r.text), "action": "zatwierdz"})
    assert "Anonimizacja zatwierdzona" in r.text  # 543 letter has no personal data in it
    assert client.get(f"/sprawy/{cid}/eksport/do_wysylki.txt").status_code == 200
    r = client.post(f"/sprawy/{cid}/anonimizacja", data={"action": "zapisz", "manual": "Schronisko dla Zwierząt"})
    assert client.get(f"/sprawy/{cid}/eksport/zanonimizowana.docx").status_code == 409
    client.post(f"/sprawy/{cid}/anonimizacja", data={**_form(r.text), "manual": "Schronisko dla Zwierząt", "action": "zatwierdz"})
    out = client.get(f"/sprawy/{cid}/eksport/zanonimizowana.docx").content
    assert_no_leak(docx_everything(out), ["Schronisko dla Zwierząt"])
    assert client.get(f"/sprawy/{cid}/eksport/inne.docx").status_code == 404
    assert client.get("/sprawy/99999/anonimizacja").status_code == 404


def test_static_and_marks(client):
    assert client.get("/static/redaction.js").status_code == 200
    m = rd.marked_html("abc Jan Kowalski choruje.", [
        {"start": 0, "end": 25, "status": "review", "id": "s1", "type": "SZCZEGOLNE_ZDROWIE", "reason": "r"},
        {"start": 4, "end": 16, "status": "accepted", "id": "s2", "type": "OSOBA", "reason": "r"}])
    assert str(m).count("<mark") == 2 and str(m).count("</mark>") == 2
    assert 'data-id="s2"' in m and "sp-accepted" in m


def test_marks_crossing_spans_drawn_in_pieces():
    t = "Pacjent leczy się w poradni przy ul. Długa 15/4 w mieście."
    spans = [{"start": 0, "end": 36, "status": "review", "id": "s1", "type": "SZCZEGOLNE_ZDROWIE", "reason": "r"},
             {"start": 33, "end": 47, "status": "suggested", "id": "s2", "type": "ADRES", "reason": "r"}]
    m = str(rd.marked_html(t, spans))
    assert m.count('data-id="s2"') == 2 and m.count("<mark") == m.count("</mark>") == 3
    assert re.sub(r"<[^>]+>", "", m) == h.escape(t)
