"""T07 Projekt pisma: case 543 draft, moving a sentence → version 2, letter types, late-notice warning."""
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
    c.url = f"/sprawy/{seed_543()}/projekt"
    return c


def _text(html: str) -> str:
    import html as h
    m = re.search(r'<textarea id="letter-text"[^>]*>(.*?)</textarea>', html, re.S)
    return h.unescape(m.group(1)).removeprefix("\n")  # the browser drops the first newline


def test_case_543_draft(client):
    r = client.get(client.url)
    assert r.status_code == 200
    text = _text(r.text)
    for n in range(1, 6):
        assert re.search(rf"(?m)^Ad {n}$", text)
    assert "839 psom" in text and "560 kotom" in text and "3.143.761,14 zł" in text
    assert "Kontrola liczb: każda liczba w piśmie występuje w odpowiedziach wydziałów." in r.text
    assert "Liczby, których nie ma w odpowiedziach" not in r.text
    assert "BKS.IV.1431.543.2026" in r.text
    assert 'src="/static/ad_editor.js"' in r.text and 'href="/static/b2.css"' in r.text
    # questions and department answers next to the letter
    assert "SCHRONISKO.txt" in r.text and "WGK.txt" in r.text
    assert client.get("/static/ad_editor.js").status_code == 200


def test_move_sentence_saves_version_2(client):
    page = client.get(client.url).text
    text = _text(page)
    s = "Miasto nie zawierało umów z podmiotami zewnętrznymi w zakresie opieki nad domowymi zwierzętami bezdomnymi."
    # T24: the rules cannot tell Ad 2 from Ad 5 for this sentence, so it waits in the report panel instead of the letter
    assert s not in text and "Zdania bez przypisania" in page
    ad2 = "Opiekę nad domowymi zwierzętami bezdomnymi sprawuje Schronisko dla Zwierząt w Bydgoszczy, które jest jednostką budżetową Miasta Bydgoszczy."
    moved = text.replace(ad2, ad2 + " " + s)
    r = client.post(client.url, data={"action": "zapisz", "text": moved.replace("\n", "\r\n"), "base_version": "1"},
                    follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"].endswith("wersja=2&zapisano=2")
    page = client.get(r.headers["location"]).text
    assert "Zapisano wersję 2." in page and "Treść pisma, wersja 2" in page
    assert ad2 + " " + s in _text(page)
    assert "Liczby, których nie ma w odpowiedziach" not in page
    # version 1 is still there
    assert ad2 + " " + s not in _text(client.get(client.url + "?wersja=1").text)
    # unchanged text does not create version 3
    r = client.post(client.url, data={"action": "zapisz", "text": moved, "base_version": "2"}, follow_redirects=False)
    assert "bez_zmian=1" in r.headers["location"]
    assert "?wersja=3" not in client.get(client.url).text


def test_unassigned_sentence_assigned_from_the_report_panel(client):
    """T24: 'Zdania bez przypisania – wybierz Ad' → POST /projekt/przypisz → a new version with the sentence under that Ad."""
    page = client.get(client.url).text
    s = "Miasto nie zawierało umów z podmiotami zewnętrznymi w zakresie opieki nad domowymi zwierzętami bezdomnymi."
    assert 'name="zdanie" value="SCHRONISKO.txt#1"' in page and "SCHRONISKO.txt, zdanie 2" in page
    r = client.post(client.url + "/przypisz", data={"zdanie": "SCHRONISKO.txt#1", "ad": "1", "base_version": "1"}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"].endswith("wersja=2&zapisano=2")
    page = client.get(r.headers["location"]).text
    text = _text(page)
    assert "Ad 1\n" in text and s in text.split("Ad 1\n", 1)[1].split("\nAd 2", 1)[0]
    assert "Zdania bez przypisania" not in page
    # the decision survives regenerating the draft
    r = client.post(client.url, data={"action": "generuj", "ltype": "udostepnienie"}, follow_redirects=False)
    assert s in _text(client.get(r.headers["location"]).text)


def test_edit_with_wrong_number_is_flagged(client):
    text = _text(client.get(client.url).text)
    r = client.post(client.url, data={"action": "zapisz", "text": text.replace("839 psom", "893 psom"), "base_version": "1"})
    assert r.status_code == 200
    assert "Liczby, których nie ma w odpowiedziach wydziałów" in r.text and "<li>893</li>" in r.text


def test_late_extension_notice_warns(client):
    client.get(client.url)
    r = client.post(client.url, data={"action": "generuj", "ltype": "przedluzenie", "reason": "konieczność kwerendy"})
    assert r.status_code == 200
    assert "po upływie 14 dni" in r.text and "note note-err" in r.text
    text = _text(r.text)
    assert "ze względu na konieczność kwerendy" in text and "Ad 1" not in text


@pytest.mark.parametrize("ltype,field,value", [
    ("odeslanie_art_4_ust_3", "entity", "Wojewódzki Inspektorat Weterynarii w Bydgoszczy"),
    ("odeslanie_bip", "bip_url", "https://bip.um.bydgoszcz.pl/przyklad"),
    ("doprecyzowanie", "reason", "czy chodzi o umowy z 2025 r."),
    ("przetworzona", "reason", "zestawienie wymaga analizy 300 umów"),
    ("brak_danych", "scope", "statystyk adopcji"),
])
def test_letter_types(client, ltype, field, value):
    client.get(client.url)
    r = client.post(client.url, data={"action": "generuj", "ltype": ltype, field: value})
    assert r.status_code == 200
    assert value in _text(r.text)
    assert f'<option value="{ltype}" selected>' in r.text


def test_bad_date_and_unknown_case(client):
    client.get(client.url)
    r = client.post(client.url, data={"action": "generuj", "ltype": "przedluzenie", "until": "jutro"})
    assert "RRRR-MM-DD" in r.text
    assert client.get("/sprawy/99999/projekt").status_code == 404
    assert client.get(client.url + "?wersja=77").status_code == 404


def test_case_page_generate_link(client):
    """The case page (T06) opens GET /sprawy/{id}/projekt?ltype=<key>: new version of that type, then the same on reload."""
    r = client.get(client.url + "?ltype=przedluzenie", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"].endswith("?wersja=1&zapisano=1")
    page = client.get(r.headers["location"]).text
    assert '<option value="przedluzenie" selected>' in page and "po upływie 14 dni" in page
    r = client.get(client.url + "?ltype=przedluzenie", follow_redirects=False)
    assert r.headers["location"].endswith("?wersja=1")
    r = client.get(client.url + "?ltype=udostepnienie", follow_redirects=False)
    assert r.headers["location"].endswith("?wersja=2&zapisano=2")
