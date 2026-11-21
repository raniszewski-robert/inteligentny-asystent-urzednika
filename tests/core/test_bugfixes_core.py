"""Regression tests for core bug fixes: public-address PII matching, short-word DOCX audit, Sunday demo_shift, DB cache."""
from __future__ import annotations

import io
from datetime import date

import docx

from udip import anonymize, db, deadlines, export as ex, importer


def test_public_addr_exact_does_not_skip_private_jezuicka_15():
    pub = anonymize.detect_rules("Siedziba urzędu: ul. Jezuicka 1, 85-102 Bydgoszcz.")
    assert not any(s.type in ("ADRES", "KOD_MIEJSC") for s in pub)

    priv = anonymize.detect_rules("Wnioskodawca mieszka pod adresem ul. Jezuicka 15 oraz ul. Jezuicka 1/4.")
    addrs = [s.text for s in priv if s.type == "ADRES"]
    assert "ul. Jezuicka 15" in addrs
    assert "ul. Jezuicka 1/4" in addrs


def test_audit_docx_short_surname_no_false_positive_on_brak(tmp_path):
    d = docx.Document()
    d.add_paragraph("Brak danych z listopada na temat kotów w maju.")
    buf = io.BytesIO()
    d.save(buf)
    raw = ex.harden_docx(buf.getvalue())
    # Short redacted surnames must not trigger false positives inside unrelated Polish words
    res = ex.audit_docx(raw, ["Rak", "Lis", "Kot", "Maj"])
    assert res["ok"], res["hits"]

    # An actual leaked short surname is still caught
    d2 = docx.Document()
    d2.add_paragraph("Odpowiedź dotyczy osoby: Pan Rak.")
    buf2 = io.BytesIO()
    d2.save(buf2)
    res2 = ex.audit_docx(ex.harden_docx(buf2.getvalue()), ["Rak"])
    assert not res2["ok"] and res2["hits"][0]["secret"] == "Rak"


def test_demo_shift_sunday_overdue_has_negative_working_days():
    sunday = date(2026, 11, 22)
    recs = [{"number": f"BKS.IV.1431.{i}.2026", "received": f"2026-01-{10 + i:02d}", "summary": f"Sprawa {i}"} for i in range(10)]
    shifted = importer.demo_shift(recs, sunday)
    overdue = [r for r in shifted if deadlines.urgency(deadlines.deadline_days(date.fromisoformat(r["received"])), sunday) == "overdue"]
    assert overdue
    for r in overdue:
        due = deadlines.deadline_days(date.fromisoformat(r["received"]))
        assert deadlines.working_days_left(due, sunday) < 0


def test_db_reinitializes_after_file_deletion(tmp_path, monkeypatch):
    monkeypatch.setenv("UDIP_DATA_DIR", str(tmp_path))
    db.init()
    db.create_case(number="BKS.IV.1431.1.2026", received="2026-11-10")
    assert len(db.list_cases()) == 1

    db.db_path().unlink()
    # Connecting to a recreated DB at the exact same path must re-run SCHEMA
    assert db.list_cases() == []
    db.create_case(number="BKS.IV.1431.2.2026", received="2026-11-11")
    assert len(db.list_cases()) == 1
