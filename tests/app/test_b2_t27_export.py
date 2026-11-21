"""T27 through the app: standalone file → decide all → approve → audit badge, footer and clean metadata in the DOCX."""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

import docx
from fastapi.testclient import TestClient

from app.main import app
from tests.app._b2_seed import isolate

DEMO = Path(__file__).resolve().parents[2] / "docs" / "deck" / "demo_dane_osobowe.docx"


def test_standalone_export_hardened(tmp_path, monkeypatch):
    isolate(tmp_path, monkeypatch)
    c = TestClient(app)
    c.cookies.set("urzednik", "PK")
    r = c.post("/anonimizacja", files={"plik": (DEMO.name, DEMO.read_bytes())}, follow_redirects=False)
    url = r.headers["location"]
    c.post(url, data={"action": "wszystkie"})
    r = c.post(url, data={"action": "zatwierdz"}, follow_redirects=True)
    assert "audit-badge" in r.text and "bez trafień" in r.text, r.text[:400]
    d = c.get(f"{url}/eksport/zanonimizowana.docx")
    assert d.status_code == 200
    doc = docx.Document(io.BytesIO(d.content))
    body = "\n".join(p.text for p in doc.paragraphs)
    assert "44051401359" not in body and "Nowak-Kowalska" not in body and "██████" in body
    foot = doc.sections[0].footer.paragraphs[0].text
    assert "Wyłączenie jawności" in foot and "numery PESEL" in foot and "PK" in foot
    core = zipfile.ZipFile(io.BytesIO(d.content)).read("docProps/core.xml").decode()
    assert "python-docx" not in core and "creator" not in core
