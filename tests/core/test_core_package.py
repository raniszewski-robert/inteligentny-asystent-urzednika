"""Core udip/ package guarantees: self-contained data, rules-by-default analysis/drafting, deterministic search."""
from __future__ import annotations

import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UMB = ROOT / "data-partner" / "umb"


def test_bridge_removed_and_no_skill_dirs_on_path():
    import udip.analyze  # noqa: F401
    import udip.draft  # noqa: F401
    assert not (ROOT / "udip" / "_skills.py").exists()
    assert not [p for p in sys.path if ".claude" in p and "skills" in p]


def test_data_lives_in_udip_data():
    from udip.analyze import DEFAULT_DEPTS, load_departments
    from udip.anonymize import DATA, FIRST_NAMES
    from udip.letters import LETTER_TYPES
    data = ROOT / "udip" / "data"
    assert DEFAULT_DEPTS == data / "departments.json" and DATA == data
    assert len(load_departments()) > 40 and len(FIRST_NAMES) > 100 and "udostepnienie" in LETTER_TYPES


def test_analyze_rules_by_default():
    from udip.analyze import analyze, load_departments
    from udip.search import Archive, load_archive
    req = (UMB / "przypadek_543/wniosek.txt").read_text(encoding="utf-8")
    arch = Archive(load_archive(UMB / "archiwum_umb.jsonl"))
    res = analyze(req, arch, load_departments(), date(2026, 11, 22))
    assert res["provider"] == "rules" and res["llm_used"] is False and len(res["questions"]) == 5


def test_draft_llm_mode_falls_back_to_template_in_rules_provider(monkeypatch):
    from udip.draft import make_draft
    monkeypatch.setenv("UDIP_PROVIDER", "rules")
    req = (UMB / "przypadek_543/wniosek.txt").read_text(encoding="utf-8")
    ans = (UMB / "przypadek_543/SCHRONISKO.txt").read_text(encoding="utf-8")
    out = make_draft(req, [("SCHRONISKO", ans)], date(2026, 8, 14), today=date(2026, 11, 22), mode="llm")
    rep = out["report"]
    assert rep["mode_used"] == "template" and "provider rules" in (rep.get("llm_error") or "")


def test_import_fills_departments_and_extensions():
    from udip.importer import convert, extension_to_days, fill_departments
    from udip.search import load_archive
    recs, _ = convert(UMB / "kalendarium_umb.xlsx")
    lib = extension_to_days(fill_departments(recs, load_archive(UMB / "archiwum_umb.jsonl")))
    assert len(lib) == 10
    assert any(x["departments"] for x in lib) and all("extension_until" not in x for x in lib)


def test_draft_spans_stay_rules_only(monkeypatch):
    """make_draft proposes anonymization by rules only; model spans belong to the anonymization screen (detect)."""
    import udip.llm as L
    from udip.draft import make_draft
    from udip.llm_tasks import anonymization
    monkeypatch.setattr(L, "available", lambda: True)
    monkeypatch.setenv("UDIP_PROVIDER", "anthropic:sonnet")
    monkeypatch.setattr(anonymization, "spans_llm", lambda t: [{"start": 0, "end": 5, "type": "OSOBA"}])
    req = (UMB / "przypadek_543/wniosek.txt").read_text(encoding="utf-8")
    d = make_draft(req, [], date(2026, 8, 14), today=date(2026, 11, 22))
    assert not any(s["reason"].startswith("model:") for s in d["spans"])


def test_search_matched_terms_deterministic():
    code = ("from udip.search import Archive, load_archive; import json;"
            f"a = Archive(load_archive(r'{UMB / 'archiwum_umb.jsonl'}'));"
            "print(json.dumps(a.search('schronisko psy koty bezdomne zwierzęta opieka')))")
    outs = {subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=ROOT,
                           env={"PYTHONHASHSEED": s, "PATH": ""}).stdout for s in ("1", "2", "3")}
    assert len(outs) == 1 and outs != {""}
