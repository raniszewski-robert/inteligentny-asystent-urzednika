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
    assert 'aria-pressed="true">Do BIP' in r.text


def test_default_folder_is_the_one_with_a_draft(client):
    client.get(f"/sprawy/{client.cid}/projekt")
    r = client.get("/biurko")
    assert "Otwarta teczka: " in r.text and 'class="sheet"' in r.text


def test_send_version_and_unknown_folder(client):
    client.get(f"/sprawy/{client.cid}/projekt")
    r = client.get(f"/biurko?teczka={client.cid}&wersja=wysylka")
    assert 'aria-pressed="true">Do wysyłki' in r.text
    assert client.get("/biurko?teczka=99999").status_code == 200


def test_plural_and_stamp():
    from app.routes.biurko import plural, stamp
    assert [plural(n, "teczka", "teczki", "teczek") for n in (1, 2, 5, 12, 22)] == ["teczka", "teczki", "teczek", "teczek", "teczki"]
    assert stamp({"urgency": "overdue"}) == "Po terminie"
    assert stamp({"urgency": "ok", "working_days_left": 1}) == "1 dzień"
    assert stamp({"urgency": "ok", "working_days_left": 6}) == "6 dni"
