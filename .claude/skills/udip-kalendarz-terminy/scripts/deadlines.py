#!/usr/bin/env python3
"""CLI: termin odpowiedzi na wniosek UDIP. Logika: udip/deadlines.py.

  python3 deadlines.py 2026-11-07 [--extend-days 30 | --extend-months 2]
  python3 deadlines.py --holidays 2026
  python3 deadlines.py --selftest
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from udip.deadlines import *  # noqa: E402,F401,F403  (import tego pliku daje to samo co udip.deadlines)
from udip.deadlines import (UDIP_DAYS, deadline_days, deadline_extended, deadline_safe, easter_sunday,  # noqa: E402
                            polish_holidays, urgency)


def _selftest() -> int:
    cases = [
        # (wpływ, oczekiwany termin 14 dni, opis)
        (date(2026, 11, 2), date(2026, 11, 16), "zwykły poniedziałek → poniedziałek"),
        (date(2026, 11, 7), date(2026, 11, 23), "21.11 to sobota → poniedziałek 23.11"),
        (date(2026, 10, 18), date(2026, 11, 2), "1.11 niedziela (Wszystkich Świętych) → 2.11"),
        (date(2026, 10, 28), date(2026, 11, 12), "11.11 środa (święto) → 12.11"),
        (date(2026, 12, 10), date(2026, 12, 28), "24.12 czw. Wigilia; 14 dni = 24.12 → 28.12 (25, 26 wolne, 27 niedz.)"),
        (date(2026, 12, 18), date(2027, 1, 4), "1.01.2027 piątek → 4.01 (2–3 weekend)"),
        (date(2026, 3, 22), date(2026, 4, 7), "5.04.2026 Wielkanoc, 6.04 poniedziałek → 7.04"),
        (date(2026, 5, 20), date(2026, 6, 3), "3.06 środa, nie święto"),
        (date(2026, 5, 21), date(2026, 6, 5), "4.06.2026 Boże Ciało → 5.06"),
        (date(2024, 12, 10), date(2024, 12, 24), "2024: Wigilia nie była wolna"),
    ]
    fails = 0
    for rec, exp, desc in cases:
        got = deadline_days(rec)
        ok = got == exp
        fails += not ok
        print(f"{'OK ' if ok else 'BŁĄD'} wpływ {rec} → {got} (oczek. {exp}) – {desc}")
    # przedłużenia
    got, _ = deadline_extended(date(2026, 12, 31), months=2)
    exp = date(2027, 3, 1)  # 28.02.2027 niedziela → 1.03
    fails += got != exp
    print(f"{'OK ' if got == exp else 'BŁĄD'} 2 mies. od 31.12.2026 → {got} (oczek. {exp})")
    got, w = deadline_extended(date(2026, 11, 2), extension_days=90)
    exp = date(2027, 1, 4)  # cap: 2.01.2027 sobota → 4.01
    fails += got != exp
    print(f"{'OK ' if got == exp else 'BŁĄD'} kwerenda +90 dni ucięta do 2 mies. → {got}; ostrzeżeń: {len(w)}")
    # pilność
    for due, today, exp in [
        (date(2026, 11, 23), date(2026, 11, 20), "tomorrow"),  # piątek przed poniedziałkiem
        (date(2026, 11, 23), date(2026, 11, 23), "today"),
        (date(2026, 11, 23), date(2026, 11, 24), "overdue"),
        (date(2026, 11, 26), date(2026, 11, 23), "soon"),
        (date(2026, 12, 15), date(2026, 11, 23), "ok"),
    ]:
        got = urgency(due, today)
        fails += got != exp
        print(f"{'OK ' if got == exp else 'BŁĄD'} pilność termin {due}, dziś {today} → {got} (oczek. {exp})")
    got = deadline_safe(date(2026, 12, 10))
    fails += got != date(2026, 12, 23)
    print(f"{'OK ' if got == date(2026, 12, 23) else 'BŁĄD'} termin bezpieczny dla wpływu 10.12.2026 → {got} (oczek. 2026-12-23)")
    assert easter_sunday(2026) == date(2026, 4, 5) and easter_sunday(2027) == date(2027, 3, 28)
    print(f"\nWynik: {'wszystkie testy OK' if not fails else f'{fails} błędów'}")
    return 1 if fails else 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Termin odpowiedzi na wniosek UDIP")
    p.add_argument("received", nargs="?", help="data wpływu RRRR-MM-DD")
    p.add_argument("--days", type=int, default=UDIP_DAYS)
    p.add_argument("--extend-days", type=int, help="kwerenda: dodatkowe dni")
    p.add_argument("--extend-months", type=int, help="przedłużenie w miesiącach (maks. 2)")
    p.add_argument("--holidays", type=int, metavar="ROK", help="wypisz dni wolne w roku")
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args(argv)
    if a.selftest:
        return _selftest()
    if a.holidays:
        for d, n in sorted(polish_holidays(a.holidays).items()):
            print(d.isoformat(), d.strftime("%a"), n)
        return 0
    if not a.received:
        p.error("podaj datę wpływu albo --selftest")
    rec = date.fromisoformat(a.received)
    print("Termin podstawowy (art. 13 UDIP + art. 57 § 4 KPA):", deadline_days(rec, a.days).isoformat())
    print("Termin bezpieczny (bez przesunięcia na dzień roboczy):", deadline_safe(rec, a.days).isoformat())
    if a.extend_days is not None or a.extend_months is not None:
        d, w = deadline_extended(rec, a.extend_days, a.extend_months)
        print("Termin po przedłużeniu:", d.isoformat())
        for x in w:
            print("  !", x)
    return 0


if __name__ == "__main__":
    sys.exit(main())
