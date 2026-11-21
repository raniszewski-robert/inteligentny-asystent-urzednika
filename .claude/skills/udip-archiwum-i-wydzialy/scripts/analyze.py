#!/usr/bin/env python3
"""CLI: analiza wniosku UDIP (pytania, tryb, sygnały ryzyka, podobne sprawy, wydziały). Logika: udip/analyze.py.

  python3 analyze.py wniosek.txt --archive archiwum.jsonl [--departments departments.json] [--today 2026-11-23]
Wyjście: JSON. Domyślnie same reguły; --provider anthropic:sonnet (itp.) dokłada LLM przez udip.llm.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from udip.analyze import *  # noqa: E402,F401,F403  (import tego pliku daje to samo co udip.analyze)
from udip.analyze import DEFAULT_DEPTS, analyze, load_departments  # noqa: E402
from udip.search import Archive, load_archive  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Analiza wniosku UDIP")
    p.add_argument("request", type=Path)
    p.add_argument("--archive", type=Path)
    p.add_argument("--departments", type=Path, default=DEFAULT_DEPTS)
    p.add_argument("--today", default=date.today().isoformat())
    p.add_argument("--since-days", type=int, default=365)
    p.add_argument("--out", type=Path)
    p.add_argument("--exclude-id", help="numer sprawy, której nie pokazywać jako podobnej (gdy wniosek jest już w archiwum)")
    p.add_argument("--provider", default="rules", help="rules (domyślnie) albo dostawca LLM z udip.llm, np. anthropic:sonnet")
    a = p.parse_args(argv)
    text = a.request.read_text(encoding="utf-8")
    arch = Archive(load_archive(a.archive)) if a.archive else None
    res = analyze(text, arch, load_departments(a.departments), date.fromisoformat(a.today), a.since_days, a.exclude_id, provider=a.provider)
    js = json.dumps(res, ensure_ascii=False, indent=2)
    (a.out.write_text(js, encoding="utf-8") if a.out else print(js))
    return 0


if __name__ == "__main__":
    sys.exit(main())
