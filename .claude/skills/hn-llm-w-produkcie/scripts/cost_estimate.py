#!/usr/bin/env python3
"""Szacunek kosztu i czasu przetwarzania dokumentow przez LLM, do odpowiedzi jury „ile to kosztuje".

  python3 cost_estimate.py --docs 50000 --in-tokens 3000 --out-tokens 400
  python3 cost_estimate.py --docs 50000 --in-tokens 3000 --out-tokens 400 --cached-share 0.6 --latency 4 --parallel 8

Liczy dla kazdego modelu z tabeli cen: koszt calkowity, koszt na dokument, czas przy danej rownoleglosci.
--cached-share: jaka czesc tokenow wejscia to staly prefiks (instrukcje, przyklady) czytany z cache;
odczyt z cache przyjmujemy jako 10% ceny wejscia [?] (sprawdz cennik). Ceny: zobacz DEFAULT_PRICES w llm_client.py.
Zaleznosci: tylko biblioteka standardowa.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from llm_client import DEFAULT_PRICES  # noqa: E402

CACHE_READ_FACTOR = 0.1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--docs", type=int, required=True, help="liczba dokumentow (np. rocznie)")
    ap.add_argument("--in-tokens", type=int, required=True, help="srednio tokenow wejscia na dokument")
    ap.add_argument("--out-tokens", type=int, required=True, help="srednio tokenow wyjscia na dokument")
    ap.add_argument("--cached-share", type=float, default=0.0)
    ap.add_argument("--latency", type=float, default=0.0, help="sekundy na wywolanie (zmierz llm_client.py stats)")
    ap.add_argument("--parallel", type=int, default=1)
    ap.add_argument("--usd-pln", type=float, default=3.7, help="kurs do przeliczenia; sprawdz aktualny")
    args = ap.parse_args()
    if not 0 <= args.cached_share <= 1:
        print("BLAD: --cached-share musi byc w przedziale 0-1", file=sys.stderr)
        return 2

    print(f"{args.docs} dokumentow x ({args.in_tokens} wej. + {args.out_tokens} wyj. tokenow), prefiks z cache: {args.cached_share:.0%}")
    print(f"{'model':<20} {'USD razem':>11} {'PLN razem':>11} {'PLN/dok.':>9}")
    for model, (pin, pout) in DEFAULT_PRICES.items():
        fresh = args.in_tokens * (1 - args.cached_share)
        cached = args.in_tokens * args.cached_share
        per_doc = (fresh * pin + cached * pin * CACHE_READ_FACTOR + args.out_tokens * pout) / 1e6
        total = per_doc * args.docs
        print(f"{model:<20} {total:>11.2f} {total * args.usd_pln:>11.2f} {per_doc * args.usd_pln:>9.4f}")
    print(f"{'model lokalny':<20} {'0.00':>11} {'0.00':>11} {'0.0000':>9}  (+ koszt serwera i utrzymania)")
    if args.latency:
        hours = args.docs * args.latency / args.parallel / 3600
        print(f"Czas: {args.latency} s na dokument, {args.parallel} rownolegle -> {hours:.1f} h dla calego zbioru.")
    print("Ceny z llm_client.DEFAULT_PRICES; przed pitchem sprawdz aktualny cennik i kurs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
