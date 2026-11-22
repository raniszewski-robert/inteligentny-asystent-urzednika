"""Biurko: stos teczek otwartych spraw z pieczątkami i otwarta teczka z projektem pisma na kartce."""
from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.app._b2_seed import isolate, seed_543


@pytest.fixture()
def client(tmp_path, monkeypatch):
    isolate(tmp_path, monkeypatch)
    c = TestClient(app)
    c.cid = seed_543()
    return c


def test_desk_without_drafts_shows_folders(client):
    r = client.get("/biurko")
    assert r.status_code == 200
    assert "Na biurku" in r.text and "Otwarta teczka" in r.text
    assert 'href="/biurko" aria-current="page"' in r.text
    assert "niedziela, 22 listopada 2026" in r.text
    assert re.search(r'class="stamp stamp-(overdue|today|tomorrow|soon|ok)"', r.text)
    assert "Połóż nowy wniosek" in r.text and "Szafa (archiwum)" in r.text


def test_open_folder_shows_letter_numbers_and_notes(client):
    assert client.get(f"/sprawy/{client.cid}/projekt").status_code == 200  # tworzy projekt, wersja 1
    r = client.get(f"/biurko?teczka={client.cid}")
    assert r.status_code == 200
    assert "Otwarta teczka: " in r.text and "BKS.IV.1431.543.2026" in r.text
    assert 'class="sheet"' in r.text and '<strong>Ad 1</strong>' in r.text
    assert re.search(r'<span class="num-ok"[^>]*>839</span>', r.text)
    assert "liczby zgadzają się z odpowiedzią: SCHRONISKO, WGK" in r.text
    assert f'href="/sprawy/{client.cid}/anonimizacja">Zatwierdź i podpisz' in r.text
    assert "brak danych adresata do ukrycia" in r.text and "Do wysyłki</a>" not in r.text  # no addressee → one version


def test_default_folder_is_the_one_with_a_draft(client):
    client.get(f"/sprawy/{client.cid}/projekt")
    r = client.get("/biurko")
    assert "Otwarta teczka: " in r.text and 'class="sheet"' in r.text


def test_send_and_bip_versions_differ_by_addressee(client):
    from app import b2_store
    client.get(f"/sprawy/{client.cid}/projekt")
    d = b2_store.get_draft(client.cid)
    text = d["text"].replace("[adresat – uzupełnij z rejestru]", "Anna Nowak-Kowalska\nul. Słoneczna 7/12\n85-001 Bydgoszcz")
    assert text != d["text"]
    r = client.post(f"/sprawy/{client.cid}/projekt", data={"action": "zapisz", "text": text, "base_version": d["version"]})
    assert r.status_code in (200, 303)
    d2 = b2_store.get_draft(client.cid)
    spans = [dict(s, status="accepted") for s in d2["spans"]]
    assert any(s.get("addressee") for s in spans), "adresat w nagłówku powinien dostać flagę addressee"
    b2_store.set_spans(d2["id"], spans)
    send = client.get(f"/biurko?teczka={client.cid}&wersja=wysylka").text
    bip = client.get(f"/biurko?teczka={client.cid}&wersja=bip").text
    assert 'aria-pressed="true">Do wysyłki' in send and 'aria-pressed="true">Do BIP' in bip
    assert "Słoneczna 7/12" in send and '<mark class="sp sp-accepted"' in bip
    head_send, head_bip = send.split('class="sheet-body"')[1].split("Szanowni")[0], bip.split('class="sheet-body"')[1].split("Szanowni")[0]
    assert "sp-accepted" not in head_send and "Anna Nowak-Kowalska" in head_send  # do wysyłki: adresat jawny
    assert "sp-accepted" in head_bip  # do BIP: dane adresata zaczernione


def test_unknown_folder(client):
    assert client.get("/biurko?teczka=99999").status_code == 200


def test_plural_and_stamp():
    from app.routes.biurko import plural, stamp
    assert [plural(n, "teczka", "teczki", "teczek") for n in (1, 2, 5, 12, 22)] == ["teczka", "teczki", "teczek", "teczek", "teczki"]
    assert stamp({"urgency": "overdue"}) == "Po terminie"
    assert stamp({"urgency": "ok", "working_days_left": 1}) == "1 dzień"
    assert stamp({"urgency": "ok", "working_days_left": 6}) == "6 dni"


def test_number_check_ignores_addressee_header(client):
    from app import b2_store
    client.get(f"/sprawy/{client.cid}/projekt")
    d = b2_store.get_draft(client.cid)
    text = d["text"].replace("[adresat – uzupełnij z rejestru]", "Anna Nowak-Kowalska\nul. Słoneczna 7/12\n85-001 Bydgoszcz")
    client.post(f"/sprawy/{client.cid}/projekt", data={"action": "zapisz", "text": text, "base_version": d["version"]})
    assert b2_store.get_draft(client.cid)["report"].get("number_check_edit") == []
    d2 = b2_store.get_draft(client.cid)
    bad = d2["text"].replace("839 psom", "939 psom")
    client.post(f"/sprawy/{client.cid}/projekt", data={"action": "zapisz", "text": bad, "base_version": d2["version"]})
    assert b2_store.get_draft(client.cid)["report"].get("number_check_edit")  # a changed figure in „Ad” is still caught
