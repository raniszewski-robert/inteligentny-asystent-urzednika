"""Shared setup for lane B2 tests: a temporary udip.db with case 543 (request + two department answers)."""
from __future__ import annotations

import json
from pathlib import Path

FIX = Path(__file__).resolve().parents[1] / "fixtures" / "draft_543.json"


def isolate(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("UDIP_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("UDIP_TODAY", "2026-11-22")
    monkeypatch.setenv("UDIP_PROVIDER", "rules")


def seed_543() -> int:
    from udip import db
    fx = json.loads(FIX.read_text(encoding="utf-8"))
    cid = db.create_case(number=fx["number"], received=fx["received"], status="b_zapytania_wyslane",
                         summary="Opieka nad bezdomnymi zwierzętami i ich wyłapywanie w 2025 r.",
                         applicant_label="Stowarzyszenie", initials="PK", departments=["SCHRONISKO", "WGK"])
    db.add_document(cid, "request", "wniosek.txt", fx["request"])
    for name, text in fx["answers"]:
        db.add_document(cid, "dept_answer", name, text, department=name.split(".")[0])
    return cid


def seed_case(number: str, request: str, answers: list[tuple[str, str]], received: str = "2026-11-16") -> int:
    from udip import db
    cid = db.create_case(number=number, received=received, status="b_zapytania_wyslane", summary="Sprawa testowa",
                         departments=[a[0].split(".")[0] for a in answers])
    db.add_document(cid, "request", "wniosek.txt", request)
    for name, text in answers:
        db.add_document(cid, "dept_answer", name, text, department=name.split(".")[0])
    return cid
