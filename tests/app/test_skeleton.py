"""T03: the app starts, serves the layout, links every top-level route, loads nothing from the network."""
from __future__ import annotations

import re

from fastapi.testclient import TestClient

from app.common import NAV
from app.main import app

client = TestClient(app)


def test_root_redirects_to_desk():
    r = client.get("/", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/biurko"


def test_layout_header_and_nav():
    r = client.get("/kalendarz")
    assert r.status_code == 200
    html = r.text
    assert "Urząd Miasta Bydgoszczy · Biuro Komunikacji Społecznej" in html
    for path in ["/biurko", "/kalendarz", "/wniosek/nowy", "/archiwum", "/anonimizacja", "/ustawienia"]:
        assert f'href="{path}"' in html
    assert [p for p, _ in NAV] == ["/biurko", "/kalendarz", "/wniosek/nowy", "/archiwum", "/anonimizacja", "/ustawienia"]
    assert 'aria-current="page"' in html


def test_no_external_resources():
    html = client.get("/kalendarz").text
    refs = re.findall(r'(?:src|href)="([^"]+)"', html)
    assert refs and not [u for u in refs if u.startswith(("http:", "https:", "//"))]
    assert client.get("/static/htmx.min.js").status_code == 200
    css = client.get("/static/app.css").text
    assert "url(http" not in css and "@import" not in css


def test_clerk_cookie():
    c = TestClient(app)
    r = c.post("/urzednik", data={"urzednik": "Pracownik 2"}, headers={"referer": "http://testserver/archiwum"},
               follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/archiwum"
    assert 'value="Pracownik 2" selected' in c.get("/kalendarz").text
    c.post("/urzednik", data={"urzednik": "Ktoś obcy"}, follow_redirects=False)
    assert 'value="Pracownik 2" selected' in c.get("/kalendarz").text


def test_404_uses_layout():
    r = client.get("/nie-ma-takiej")
    assert r.status_code == 404 and "Nie znaleziono" in r.text and "Biuro Komunikacji" in r.text
