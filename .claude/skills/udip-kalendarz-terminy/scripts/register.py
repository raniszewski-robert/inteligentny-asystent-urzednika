#!/usr/bin/env python3
"""CLI: rejestr (kalendarz) wniosków UDIP. Logika: udip/register.py.

  python3 register.py demo.json --today 2026-11-23 --html kalendarz.html --csv rejestr.csv --ics terminy.ics
  python3 register.py demo.json --year 2026 --print
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from udip.register import *  # noqa: E402,F401,F403  (import tego pliku daje to samo co udip.register)
from udip.register import load, rows, to_csv, to_html, to_ics  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Rejestr/kalendarz wniosków UDIP")
    p.add_argument("store", type=Path, help="plik JSON z wnioskami")
    p.add_argument("--today", default=date.today().isoformat())
    p.add_argument("--year", type=int)
    p.add_argument("--html", type=Path)
    p.add_argument("--csv", type=Path)
    p.add_argument("--ics", type=Path)
    p.add_argument("--json-out", type=Path, help="wiersze kalendarza jako JSON (dla frontendu)")
    p.add_argument("--print", action="store_true")
    a = p.parse_args(argv)
    today = date.fromisoformat(a.today)
    rs = rows(load(a.store), today, a.year)
    if a.html:
        to_html(rs, a.html, today, a.year)
    if a.csv:
        to_csv(rs, a.csv)
    if a.ics:
        to_ics(rs, a.ics)
    if a.json_out:
        a.json_out.write_text(json.dumps(rs, ensure_ascii=False, indent=2), encoding="utf-8")
    if a.print or not any([a.html, a.csv, a.ics, a.json_out]):
        for r in rs:
            print(f"{r['lp']:>2} {r['number']:<22} wpł. {r['received']} termin {r['due']} [{r['urgency']:<8}] {r['status_label']:<38} {r['summary'][:50]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
