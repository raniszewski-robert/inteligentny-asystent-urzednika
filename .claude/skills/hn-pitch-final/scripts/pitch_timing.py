#!/usr/bin/env python3
"""Liczy czas mowionego pitchu z pliku scenariusza i porownuje z limitem.

Format scenariusza (markdown):
  ## Problem (0:20)                 naglowek sekcji, opcjonalnie z planowanym czasem w nawiasie
  Tekst mowiony...                  liczony wedlug tempa mowy
  [DEMO 60s]                        wstawka bez slow, liczona jako podany czas (s albo m:ss)
  > notatka dla mowcy               pomijana

  python3 pitch_timing.py pitch_3min.md --limit 180
  python3 pitch_timing.py pitch_5min.md --limit 300 --wpm 120

Tempo domyslne 130 slow na minute: spokojna polszczyzna na scenie [?]. Zmierz swoje tempo na probie
(przeczytaj 1 minute tekstu na glos) i podaj --wpm.
Kod wyjscia: 0 = miesci sie z zapasem 10%, 1 = za dlugo albo bez zapasu.
Zaleznosci: tylko biblioteka standardowa.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def to_seconds(raw: str) -> int:
    raw = raw.strip().lower()
    if ":" in raw:
        m, s = raw.split(":")
        return int(m) * 60 + int(s)
    m = re.match(r"(\d+)\s*(s|sek|min|m)?", raw)
    if not m:
        return 0
    return int(m.group(1)) * (60 if m.group(2) in ("min", "m") else 1)


def fmt(sec: float) -> str:
    return f"{int(sec // 60)}:{int(round(sec % 60)):02d}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("script")
    ap.add_argument("--limit", type=to_seconds, required=True, help="limit w sekundach albo m:ss")
    ap.add_argument("--wpm", type=float, default=130.0)
    args = ap.parse_args()

    sections: list[dict] = []
    cur = {"name": "(przed pierwszym naglowkiem)", "plan": None, "words": 0, "fixed": 0}
    for line in Path(args.script).read_text(encoding="utf-8").splitlines():
        h = re.match(r"^#{2,3}\s+(.*?)(?:\s*\(([\d:]+\s*(?:s|min)?)\))?\s*$", line)
        if h:
            if cur["words"] or cur["fixed"] or cur["plan"]:
                sections.append(cur)
            cur = {"name": h.group(1).strip(), "plan": to_seconds(h.group(2)) if h.group(2) else None, "words": 0, "fixed": 0}
            continue
        if line.startswith(("#", ">")) or not line.strip():
            continue
        for d in re.findall(r"\[(?:DEMO|WIDEO|PAUZA|SLAJD)[^\]]*?([\d:]+\s*(?:s|min)?)\s*\]", line, re.I):
            cur["fixed"] += to_seconds(d)
        spoken = re.sub(r"\[[^\]]*\]", " ", line)
        cur["words"] += len(re.findall(r"\w+", spoken))
    sections.append(cur)

    total = 0.0
    print(f"{'Sekcja':<34} {'slowa':>6} {'wstawki':>8} {'czas':>6} {'plan':>6}")
    for s in sections:
        sec = s["words"] / args.wpm * 60 + s["fixed"]
        total += sec
        plan = fmt(s["plan"]) if s["plan"] else "-"
        flag = "  ZA DLUGO" if s["plan"] and sec > s["plan"] * 1.15 else ""
        print(f"{s['name'][:34]:<34} {s['words']:>6} {s['fixed']:>7}s {fmt(sec):>6} {plan:>6}{flag}")
    margin = args.limit - total
    print(f"\nRazem: {fmt(total)} przy {args.wpm:.0f} slowach/min; limit {fmt(args.limit)}; zapas {fmt(abs(margin))}{' (PRZEKROCZONY)' if margin < 0 else ''}.")
    if margin < 0.1 * args.limit:
        words_to_cut = int((total - 0.9 * args.limit) / 60 * args.wpm) + 1
        print(f"Za malo zapasu: wytnij okolo {max(words_to_cut, 1)} slow albo skroc demo. Jury przerywa po czasie, a pierwsze pytanie zwykle pada wczesniej.")
        return 1
    print("OK: miesci sie z zapasem co najmniej 10%.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
