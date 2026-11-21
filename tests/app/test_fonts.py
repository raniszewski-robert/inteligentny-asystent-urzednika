"""The UI font (Lato) is vendored and served offline, with its licence next to it."""
from fastapi.testclient import TestClient

from app.main import app


def test_lato_served_offline():
    c = TestClient(app)
    page = c.get("/kalendarz").text
    assert "/static/fonts/lato.css" in page and "fonts.googleapis" not in page
    css = c.get("/static/fonts/lato.css")
    assert css.status_code == 200 and "font-family: 'Lato'" in css.text
    for f in ("lato-latin-400-normal.woff2", "lato-latin-ext-400-normal.woff2", "lato-latin-700-normal.woff2"):
        r = c.get(f"/static/fonts/{f}")
        assert r.status_code == 200 and r.content[:4] == b"wOF2"
    assert "Open Font License" in c.get("/static/fonts/OFL.txt").text
