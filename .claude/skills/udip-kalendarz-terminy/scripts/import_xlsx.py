#!/usr/bin/env python3
"""CLI: import arkusza kalendarium UMB (xlsx) → rejestr JSON + raport niespójności. Logika: udip/importer.py.

  python3 import_xlsx.py arkusz.xlsx --out rejestr.json [--report niespojnosci.md] [--archive archiwum.jsonl] [--demo-today RRRR-MM-DD]
Zależność: openpyxl (MIT).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from udip.importer import *  # noqa: E402,F401,F403  (import tego pliku daje to samo co udip.importer)
from udip.importer import convert, demo_shift, extension_to_days, fill_departments  # noqa: E402
from udip.search import load_archive  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("xlsx", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--report", type=Path)
    p.add_argument("--archive", type=Path, help="archiwum JSONL: uzupełnij wydziały spraw o tym samym numerze")
    p.add_argument("--demo-today", help="tryb demo: przesuń daty wpływu względem tego dnia i otwórz sprawy, by pokazać podświetlenia")
    a = p.parse_args(argv)
    recs, issues = convert(a.xlsx)
    if a.archive:
        fill_departments(recs, load_archive(a.archive))
    if a.demo_today:
        recs = demo_shift(recs, date.fromisoformat(a.demo_today))
    extension_to_days(recs)
    a.out.write_text(json.dumps({"requests": [{k: v for k, v in r.items() if k != "applicant_label"} | {"notes": (r["notes"] + " " + r["applicant_label"]).strip()} for r in recs]},
                                ensure_ascii=False, indent=2), encoding="utf-8")
    rep = "# Niespójności w arkuszu\n\n" + "\n".join(f"- {i}" for i in issues) + f"\n\nZaimportowano {len(recs)} wniosków.\n"
    (a.report.write_text(rep, encoding="utf-8") if a.report else None)
    print(rep)
    return 0


if __name__ == "__main__":
    sys.exit(main())
