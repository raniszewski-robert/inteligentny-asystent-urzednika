"""T02: SQLite schema (CONTRACTS §4), helpers, seed."""
from __future__ import annotations

import sqlite3
import subprocess
import sys
from contextlib import closing
from datetime import date
from pathlib import Path

import pytest

from udip import db
from udip.search import Archive

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def tmp_data(tmp_path, monkeypatch):
    monkeypatch.setenv("UDIP_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("UDIP_TODAY", "2026-11-22")
    return tmp_path


def _columns(table: str) -> list[str]:
    with closing(db.connect()) as con:
        return [r[1] for r in con.execute(f"PRAGMA table_info({table})")]


def test_schema_matches_contract():
    db.init()
    assert db.db_path().parent == Path(db.config.data_dir())
    assert _columns("cases") == ["id", "number", "received", "summary", "applicant_label", "initials", "status", "extension_days",
                                 "extension_until", "answered", "departments", "analysis", "is_demo", "created_at"]
    assert _columns("status_history") == ["id", "case_id", "from_status", "to_status", "at", "by", "note"]
    assert _columns("documents") == ["id", "case_id", "kind", "filename", "department", "text", "quality", "path", "created_at"]
    assert _columns("drafts") == ["id", "case_id", "version", "ltype", "text", "spans", "report", "final_to_send", "final_anonymized", "created_at"]
    assert _columns("archive") == ["id", "date", "title", "request_text", "response_text", "departments", "source"]
    assert _columns("laws") == ["id", "title", "filename", "text", "created_at"]


def test_fresh_seed_10_cases_10_archive():
    r = db.seed()
    assert len(r["cases_added"]) == 10 and len(db.list_cases()) == 10
    assert len(db.archive_records()) == 10 and r["issues"]
    c = db.case_by_number("BKS.IV.1431.543.2026")
    assert c["departments"] and isinstance(c["departments"], list) and c["is_demo"] == 0
    assert [x["received"] for x in db.list_cases()] == sorted(x["received"] for x in db.list_cases())
    assert {x["received"][:4] for x in db.list_cases(2025)} == {"2025"}


def test_reseed_is_idempotent_and_keeps_clerk_changes():
    db.seed()
    cid = db.list_cases()[0]["id"]
    db.set_status(cid, "b_zapytania_wyslane", "AK")
    snap = (db.list_cases(), db.archive_records())
    r = db.seed()
    assert r["cases_added"] == [] and len(r["cases_skipped"]) == 10
    assert (db.list_cases(), db.archive_records()) == snap
    assert db.get_case(cid)["status"] == "b_zapytania_wyslane" and len(db.history(cid)) == 1


def test_seed_demo_and_reset():
    db.seed(demo_today=date(2026, 11, 22))
    cases = db.list_cases()
    assert len(cases) == 10 and all(c["is_demo"] == 1 for c in cases)
    assert {c["status"] for c in cases} >= {"a_brak_dzialan", "c_kwerenda", "e_odpowiedz_wyslana"}
    cid = cases[0]["id"]
    db.set_status(cid, "e_odpowiedz_wyslana", "AK")
    r = db.seed(demo_today=date(2026, 12, 1), reset=True)
    assert len(r["cases_replaced"]) == 10 and len(db.list_cases()) == 10
    assert db.get_case(cid) is None and db.history(cid) == []


def test_seed_with_synthetic_extends_archive():
    db.seed(with_synthetic=True)
    recs = db.archive_records()
    assert len(recs) > 50 and {r["source"] for r in recs} >= {"umb", "syntetyczne"}
    assert Archive(recs).search("schronisko dla zwierząt koszty", k=3)


def test_status_history_insert():
    cid = db.create_case(number="BKS.IV.1431.1.2026", received="2026-11-10", summary="Oświetlenie", departments=["WGK"])
    assert db.get_case(cid)["status"] == "a_brak_dzialan"
    db.set_status(cid, "b_zapytania_wyslane", "AK", note="WGK, WIM")
    db.set_status(cid, "e_odpowiedz_wyslana", "AK", at="2026-11-20T10:00:00")
    h = db.history(cid)
    assert [(x["from_status"], x["to_status"], x["by"]) for x in h] == [("a_brak_dzialan", "b_zapytania_wyslane", "AK"),
                                                                        ("b_zapytania_wyslane", "e_odpowiedz_wyslana", "AK")]
    assert h[0]["note"] == "WGK, WIM" and h[1]["at"] == "2026-11-20T10:00:00"
    c = db.get_case(cid)
    assert c["status"] == "e_odpowiedz_wyslana" and c["answered"] == "2026-11-20" and c["departments"] == ["WGK"]


def test_set_status_answered_defaults_to_working_date():
    cid = db.create_case(number="X.1.2026", received="2026-11-10")
    db.set_status(cid, "e_odpowiedz_wyslana", "AK")
    assert db.get_case(cid)["answered"] == "2026-11-22"


def test_set_status_rejects_bad_input():
    cid = db.create_case(number="X.2.2026", received="2026-11-10")
    with pytest.raises(ValueError):
        db.set_status(cid, "z_nieznany", "AK")
    with pytest.raises(KeyError):
        db.set_status(9999, "b_zapytania_wyslane", "AK")
    assert db.history(cid) == []


def test_create_case_validation_and_json_text():
    with pytest.raises(TypeError):
        db.create_case(number="X.3.2026", foo=1)
    with pytest.raises(ValueError):
        db.create_case(number="X.3.2026", status="zly")
    cid = db.create_case(number="X.4.2026", received="2026-11-10", departments='["WE"]', analysis='{"mode": "udip"}')
    c = db.get_case(cid)
    assert c["departments"] == ["WE"] and c["analysis"] == {"mode": "udip"}
    with pytest.raises(sqlite3.IntegrityError):
        db.create_case(number="X.4.2026", received="2026-11-11")
    db.update_case(cid, departments=["WE", "WOA"], extension_days=30)
    assert db.get_case(cid)["departments"] == ["WE", "WOA"] and db.get_case(cid)["extension_days"] == 30


def test_documents_and_drafts():
    from udip.anonymize import detect
    cid = db.create_case(number="X.5.2026", received="2026-11-10")
    d1 = db.add_document(cid, "request", "wniosek.docx", "Treść", quality=0.8)
    db.add_document(cid, "dept_answer", "WGK.txt", "Odpowiedź", department="WGK", path=Path("/tmp/x"))
    with pytest.raises(ValueError):
        db.add_document(cid, "zly", "a", "b")
    assert [d["id"] for d in db.documents(cid, "request")] == [d1] and len(db.documents(cid)) == 2
    spans = detect("Pisze Jan Kowalski, PESEL 44051401359.", provider="rules")
    v1 = db.save_draft(cid, "udostepnienie", "Tekst 1", spans, {"mode_used": "template"})
    v2 = db.save_draft(cid, "udostepnienie", "Tekst 2", [], {})
    assert db.get_draft(cid)["id"] == v2 and db.get_draft(cid)["version"] == 2
    first = db.get_draft(cid, 1)
    assert first["id"] == v1 and first["report"] == {"mode_used": "template"} and first["spans"][0]["type"]
    db.set_draft_finals(v1, "do wysyłki", "zanonimizowana")
    assert db.get_draft(cid, 1)["final_anonymized"] == "zanonimizowana"


def test_archive_and_laws():
    db.add_archive("A1", "2026-01-02", "Schronisko", "Ile psów?", "839 psom", ["WGK"], "import")
    db.add_archive("A1", "2026-01-02", "Schronisko", "Ile psów?", "839 psom", ["WGK", "SCHRONISKO"], "import")
    recs = db.archive_records()
    assert len(recs) == 1 and recs[0]["departments"] == ["WGK", "SCHRONISKO"]
    lid = db.add_law("Ustawa o dostępie do informacji publicznej", "udip.txt", "Art. 13. Udostępnianie informacji publicznej")
    laws = db.law_records()
    assert laws[0]["id"] == str(lid) and Archive(laws).search("udostępnianie informacji termin art. 13")


def test_seed_cli(tmp_data):
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "seed.py"), "--demo-today", "2026-11-22"], capture_output=True, text=True,
                       cwd=ROOT, timeout=120)
    assert r.returncode == 0, r.stderr
    assert "dodane 10" in r.stdout and (tmp_data / "udip.sqlite").exists()
    r2 = subprocess.run([sys.executable, str(ROOT / "scripts" / "seed.py")], capture_output=True, text=True, cwd=ROOT, timeout=120)
    assert "dodane 0, pominięte (już są) 10" in r2.stdout
