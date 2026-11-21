"""A request already in the archive never lists itself as a similar case, also in per-question routing reasons."""
from datetime import date
from pathlib import Path

from udip.analyze import analyze_rules, load_departments
from udip.ingest import read_any
from udip.search import Archive, load_archive

UMB = Path(__file__).resolve().parents[2] / "data-partner" / "umb"


def test_per_question_routing_excludes_own_archive_record():
    arch = Archive(load_archive(UMB / "archiwum_umb.jsonl"))
    text = read_any(UMB / "probki" / "Wniosek - BKS.IV.1431.599.2026.docx")["text"]
    an = analyze_rules(text, arch, load_departments(), date(2026, 11, 22))
    assert len(an["questions"]) == 2
    assert "BKS.IV.1431.599.2026" not in [s["id"] for s in an["similar_cases"]]
    reasons = " ".join(r for q in an["questions"] for x in q["routing"] for r in x.get("reasons", []))
    assert "BKS.IV.1431.599.2026" not in reasons
    assert an["questions"][0]["routing"][0]["department"] == "WE"
