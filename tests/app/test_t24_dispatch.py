"""T24 on the case page: 'Przekazanie do wydziału' per routed department, reply form DOCX, mark as sent."""
from __future__ import annotations

import html
import io

import docx
from fastapi.testclient import TestClient

from app import store
from app.main import app
from udip import db


def _case_543() -> dict:
    store.list_cases()
    return store.case_by_number("BKS.IV.1431.543.2026")


def test_dispatch_block_form_and_mark_sent(fresh_db):
    c = _case_543()
    cl = TestClient(app)
    assert cl.post(f"/sprawy/{c['id']}/analiza", follow_redirects=False).status_code == 303
    c = store.get_case(c["id"])
    groups = {}
    for no, ids in c["analysis"]["chosen_departments"].items():
        for d in ids:
            groups.setdefault(d, []).append(int(no))
    dep, nos = next(iter(groups.items()))

    page = html.unescape(cl.get(f"/sprawy/{c['id']}").text)
    assert "Przekazanie do wydziału" in page and f"/sprawy/{c['id']}/przekazanie/{dep}.docx" in page
    assert "Treść wiadomości do skopiowania" in page and "§ 11 ust. 8" in page

    r = cl.get(f"/sprawy/{c['id']}/przekazanie/{dep}.docx")
    assert r.status_code == 200 and r.content[:2] == b"PK"
    paras = [p.text for p in docx.Document(io.BytesIO(r.content)).paragraphs]
    assert [p.split("]", 1)[0] for p in paras if p.startswith("[Ad ")] == [f"[Ad {n}" for n in nos]
    msg = cl.get(f"/sprawy/{c['id']}/przekazanie/{dep}")
    assert msg.status_code == 200 and msg.text.startswith("Temat: BKS.IV.1431.543.2026")
    assert cl.get(f"/sprawy/{c['id']}/przekazanie/NIEMA.docx").status_code == 404

    status_before = c["status"]
    r = cl.post(f"/sprawy/{c['id']}/przekazane", data={"department": dep}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == f"/sprawy/{c['id']}#przekazanie"
    rows = db.dispatches(c["id"])
    assert [x["department"] for x in rows] == [dep] and [q["no"] for q in rows[0]["questions"]] == nos and rows[0]["sub_deadline"]
    if status_before == "a_brak_dzialan":
        assert store.get_case(c["id"])["status"] == "b_zapytania_wyslane"
    assert "Oznaczono jako wysłane" in cl.get(f"/sprawy/{c['id']}").text
