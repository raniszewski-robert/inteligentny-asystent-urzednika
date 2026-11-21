#!/usr/bin/env python3
"""Seed the SQLite database ($UDIP_DATA_DIR/udip.sqlite) from the UMB data. Logic: udip.db.seed().

  python scripts/seed.py                              # 10 cases from kalendarium_umb.xlsx + 10 archive cases
  python scripts/seed.py --demo-today 2026-11-22      # dates shifted around that day (demo of the urgency colours)
  python scripts/seed.py --with-synthetic             # also the synthetic archive (data-samples/syntetyczne*)
  python scripts/seed.py --reset --demo-today 2026-11-22   # re-import the sheet's cases (drops their history)
Running it again is safe: existing cases are kept, archive rows are replaced by id.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from udip import db  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Seed bazy asystenta UDIP danymi UMB")
    p.add_argument("--xlsx", type=Path, default=db.UMB / "kalendarium_umb.xlsx", help="arkusz kalendarium (wzór UMB)")
    p.add_argument("--archive", type=Path, default=db.UMB / "archiwum_umb.jsonl", help="archiwum spraw JSONL")
    p.add_argument("--demo-today", help="RRRR-MM-DD: tryb demo, daty wpływu przesunięte względem tego dnia")
    p.add_argument("--with-synthetic", action="store_true", help="dołóż archiwum syntetyczne do bazy wiedzy")
    p.add_argument("--reset", action="store_true", help="usuń i zaimportuj ponownie sprawy z arkusza (z historią statusów)")
    a = p.parse_args(argv)
    r = db.seed(a.xlsx, a.archive, date.fromisoformat(a.demo_today) if a.demo_today else None, a.with_synthetic, a.reset)
    print(f"Baza: {db.db_path()}")
    print(f"Sprawy: dodane {len(r['cases_added'])}, pominięte (już są) {len(r['cases_skipped'])}, zastąpione {len(r['cases_replaced'])}")
    print(f"Archiwum: zapisano {r['archive']} spraw; w bazie {len(db.archive_records())}")
    if r["issues"]:
        print("Niespójności w arkuszu:")
        for i in r["issues"]:
            print(" -", i)
    return 0


if __name__ == "__main__":
    sys.exit(main())
