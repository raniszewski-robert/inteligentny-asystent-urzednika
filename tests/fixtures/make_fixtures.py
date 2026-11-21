"""Regenerate the T00 fixtures from today's code: python tests/fixtures/make_fixtures.py"""
from __future__ import annotations

import json
import sys
from dataclasses import fields
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from udip.analyze import analyze, load_departments  # noqa: E402
from udip.draft import make_draft  # noqa: E402
from udip.importer import convert, demo_shift  # noqa: E402
from udip.ingest import read_any  # noqa: E402
from udip.register import Request, rows  # noqa: E402
from udip.search import Archive, load_archive  # noqa: E402

TODAY = date(2026, 11, 22)
UMB = ROOT / "data-partner" / "umb"
OUT = Path(__file__).resolve().parent


def dump(name: str, obj) -> None:
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print("wrote", name)


def main() -> None:
    deps = load_departments()
    arch = Archive(load_archive(UMB / "archiwum_umb.jsonl"))
    doc = read_any(UMB / "probki" / "Wniosek - BKS.IV.1431.599.2026.docx")
    an = analyze(doc["text"], arch, deps, TODAY, provider="rules")
    dump("analysis_599.json", {"today": TODAY.isoformat(), "file": doc["file"], "text": doc["text"], "analysis": an})

    c = UMB / "przypadek_543"
    req = (c / "wniosek.txt").read_text(encoding="utf-8")
    answers = [(f.name, f.read_text(encoding="utf-8")) for f in [c / "SCHRONISKO.txt", c / "WGK.txt"]]
    d = make_draft(req, answers, date(2026, 8, 14), "udostepnienie", number="BKS.IV.1431.543.2026", today=TODAY, sign="[podpis]")
    dump("draft_543.json", {"today": TODAY.isoformat(), "request": req, "answers": answers, "received": "2026-08-14",
                            "number": "BKS.IV.1431.543.2026", "draft": d})

    recs, issues = convert(UMB / "kalendarium_umb.xlsx")
    names = {f.name for f in fields(Request)}
    demo = demo_shift(recs, TODAY)
    reqs = [Request(**{k: v for k, v in r.items() if k in names}) for r in demo]
    dump("rows_demo.json", {"today": TODAY.isoformat(), "issues": issues, "requests": demo, "rows": rows(reqs, TODAY)})


if __name__ == "__main__":
    main()
