#!/usr/bin/env python3
"""Sprawdza tabele kryteriow w pliku decyzji: suma wag, kryteria bez funkcji lub dowodu.

Szuka pierwszej tabeli markdown, ktorej naglowek zawiera kolumny „Kryterium" i „Waga".
Kolumny rozpoznaje po nazwach: Kryterium, Waga, Funkcja..., Dowod..., Kto, Status.

  python3 criteria_check.py godzina-zero/decyzja_risk_miner.md

Kod wyjscia: 0 = tabela spojna, 1 = sa ostrzezenia, 2 = nie znaleziono tabeli.
Zaleznosci: tylko biblioteka standardowa.
"""
from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def parse_weight(raw: str) -> float | None:
    """Waga to najwieksza liczba w komorce: „40%" -> 40, „0–10 pkt" -> 10, „max 20 pkt" -> 20."""
    nums = [float(x.replace(",", ".")) for x in re.findall(r"\d+(?:[.,]\d+)?", raw)]
    return max(nums) if nums else None


def find_table(lines: list[str]):
    for i, line in enumerate(lines):
        if "|" not in line:
            continue
        head = [norm(c) for c in cells(line)]
        if any(h.startswith("kryterium") for h in head) and any(h.startswith("waga") for h in head):
            if i + 1 < len(lines) and re.match(r"^\s*\|?[\s:|-]+\|?\s*$", lines[i + 1]):
                rows = []
                for row in lines[i + 2:]:
                    if "|" not in row:
                        break
                    rows.append(cells(row))
                return head, rows
    return None, None


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    path = Path(sys.argv[1])
    head, rows = find_table(path.read_text(encoding="utf-8").splitlines())
    if head is None:
        print(f"BLAD: w {path} nie ma tabeli z kolumnami Kryterium i Waga.")
        return 2

    def col(prefix: str) -> int | None:
        return next((i for i, h in enumerate(head) if h.startswith(prefix)), None)

    c_name, c_w = col("kryterium"), col("waga")
    c_fn, c_ev, c_who, c_st = col("funkcja"), col("dowod"), col("kto"), col("status")

    def get(row: list[str], idx: int | None) -> str:
        return row[idx].strip() if idx is not None and idx < len(row) else ""

    items, warnings = [], []
    for row in rows:
        name = get(row, c_name)
        if not name:
            continue
        w_raw = get(row, c_w)
        w = parse_weight(w_raw)
        if w is None:
            warnings.append(f"'{name}': brak liczby w kolumnie Waga ('{w_raw}')")
        items.append({"name": name, "w": w or 0.0, "w_raw": w_raw, "fn": get(row, c_fn), "ev": get(row, c_ev),
                      "who": get(row, c_who), "st": norm(get(row, c_st))})

    if not items:
        print("BLAD: tabela kryteriow jest pusta. Przepisz kryteria i wagi z pelnej tresci zadania.")
        return 2

    total = sum(it["w"] for it in items)
    percent = any("%" in it["w_raw"] for it in items)
    done_words = {"gotowe", "gotowy", "zrobione", "done", "ok"}
    no_fn = [it for it in items if not it["fn"]]
    no_ev = [it for it in items if not it["ev"]]
    no_who = [it for it in items if not it["who"]]
    done_w = sum(it["w"] for it in items if it["st"] in done_words)
    uncovered = sum(it["w"] for it in no_ev)

    print(f"Kryteriow: {len(items)}   suma wag: {total:g}{'%' if percent else ''}")
    if percent and abs(total - 100) > 0.5:
        warnings.append(f"wagi w procentach sumuja sie do {total:g}, a nie do 100: sprawdz, czy przepisano wszystkie kryteria")
    if total > 0:
        print(f"Waga z zaplanowanym dowodem: {total - uncovered:g} ({(total - uncovered) / total:.0%})")
        print(f"Waga z gotowym dowodem (Status = gotowe): {done_w:g} ({done_w / total:.0%})")

    print("\nKryteria wedlug wagi:")
    for it in sorted(items, key=lambda x: -x["w"]):
        flags = [t for t, cond in (("BRAK FUNKCJI", not it["fn"]), ("BRAK DOWODU", not it["ev"]), ("BRAK OSOBY", not it["who"])) if cond]
        print(f"  {it['w']:>6g}  {it['name'][:60]:<60} {' '.join(flags)}")

    if no_fn:
        warnings.append(f"{len(no_fn)} kryteriow bez funkcji")
    if no_ev:
        share = f" ({uncovered / total:.0%} wagi)" if total > 0 else ""
        warnings.append(f"{len(no_ev)} kryteriow bez dowodu{share}: juror nie da punktow za cos, czego nie zobaczy")
    if no_who:
        warnings.append(f"{len(no_who)} kryteriow bez osoby odpowiedzialnej")
    if total > 0 and uncovered / total > 0.30:
        warnings.append("ponad 30% wagi bez dowodu: to sygnal 'nie bierzemy' albo plan do poprawy")

    if warnings:
        print("\nOSTRZEZENIA:")
        for w in warnings:
            print(f"  - {w}")
        return 1
    print("\nOK: kazde kryterium ma funkcje, dowod i osobe.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
