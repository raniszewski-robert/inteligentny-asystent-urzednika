"""The UI fonts (IBM Plex Sans, Source Serif 4) are vendored and served offline, with their licences next to them."""
from fastapi.testclient import TestClient

from app.main import app


def test_fonts_served_offline():
    c = TestClient(app)
    page = c.get("/kalendarz").text
    assert "/static/fonts/fonts.css" in page and "fonts.googleapis" not in page
    css = c.get("/static/fonts/fonts.css")
    assert css.status_code == 200
    assert "font-family: 'IBM Plex Sans'" in css.text and "font-family: 'Source Serif 4'" in css.text
    assert "http" not in css.text.replace("http://scripts.sil.org", "")
    for f in ("ibm-plex-sans-latin-400-normal.woff2", "ibm-plex-sans-latin-ext-400-normal.woff2",
              "ibm-plex-sans-latin-600-normal.woff2", "source-serif-4-latin-ext-600-normal.woff2"):
        r = c.get(f"/static/fonts/{f}")
        assert r.status_code == 200 and r.content[:4] == b"wOF2"
    for lic in ("OFL-IBM-Plex-Sans.txt", "OFL-Source-Serif-4.txt", "OFL-Caveat.txt"):
        assert "Open Font License" in c.get(f"/static/fonts/{lic}").text


def test_every_font_face_file_exists():
    import re
    c = TestClient(app)
    css = c.get("/static/fonts/fonts.css").text
    urls = re.findall(r"url\((/static/fonts/[^)]+)\)", css)
    assert len(urls) == 16
    assert all(c.get(u).status_code == 200 for u in urls)
