#!/usr/bin/env python3
"""CLI: podobne wnioski z archiwum (BM25). Logika: udip/search.py.

  python3 search.py archiwum.jsonl --query-file wniosek.txt [--k 5] [--since-days 365] [--today 2026-11-23]
  python3 search.py archiwum.jsonl --query "wydatki na oświetlenie Fordon"
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from udip.search import *  # noqa: E402,F401,F403  (import tego pliku daje to samo co udip.search)
from udip.search import Archive, load_archive  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Podobne wnioski z archiwum (BM25)")
    p.add_argument("archive", type=Path)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--query")
    g.add_argument("--query-file", type=Path)
    p.add_argument("--k", type=int, default=5)
    p.add_argument("--since-days", type=int, help="tylko sprawy z ostatnich N dni (treść zadania: ostatni rok = 365)")
    p.add_argument("--today", default=date.today().isoformat())
    a = p.parse_args(argv)
    q = a.query or a.query_file.read_text(encoding="utf-8")
    since = date.fromisoformat(a.today) - timedelta(days=a.since_days) if a.since_days else None
    arch = Archive(load_archive(a.archive))
    print(json.dumps(arch.search(q, a.k, since), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
