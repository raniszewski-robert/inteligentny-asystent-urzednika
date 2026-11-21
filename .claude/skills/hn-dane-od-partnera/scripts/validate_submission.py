#!/usr/bin/env python3
"""Walidator formatu pliku wynikowego przed wyslaniem do Partnera.

Porownuje plik z wzorcem (sample submission od Partnera) albo z plikiem testowym:
  python3 validate_submission.py wynik.csv --sample sample_submission.csv --key id
  python3 validate_submission.py wynik.csv --test test.csv --key id --pred-col etykieta --labels A,B,C
  python3 validate_submission.py wynik.csv --test test.csv --key id --pred-col wartosc --numeric --min 0 --max 1

Sprawdza: kolumny i ich kolejnosc, liczbe wierszy, zbior i unikalnosc kluczy, puste wartosci,
dozwolone etykiety, zakres liczb, separator i kodowanie (dla CSV, wzgledem wzorca).
Kod wyjscia: 0 = poprawny, 1 = bledy.
Zaleznosci: pandas (BSD-3).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import read_table  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("submission")
    ap.add_argument("--sample", help="wzorcowy plik wynikowy od Partnera")
    ap.add_argument("--test", help="plik testowy (zrodlo kluczy), gdy nie ma wzorca")
    ap.add_argument("--key", help="kolumna klucza")
    ap.add_argument("--pred-col", help="kolumna predykcji (domyslnie: wszystkie poza kluczem)")
    ap.add_argument("--labels", help="dozwolone etykiety, po przecinku")
    ap.add_argument("--numeric", action="store_true", help="predykcja ma byc liczba")
    ap.add_argument("--min", type=float, dest="vmin")
    ap.add_argument("--max", type=float, dest="vmax")
    args = ap.parse_args()

    errors, notes = [], []
    try:
        sub, sub_info = read_table(args.submission)
    except Exception as exc:
        print(f"BLAD: nie da sie wczytac {args.submission}: {type(exc).__name__}: {exc}")
        return 1
    ref, ref_info, ref_name = None, {}, None
    if args.sample:
        ref, ref_info = read_table(args.sample)
        ref_name = "wzorzec"
        if list(sub.columns) != list(ref.columns):
            errors.append(f"kolumny {list(sub.columns)} roznia sie od wzorca {list(ref.columns)} (nazwy albo kolejnosc)")
        for field in ("separator", "encoding", "format"):
            if ref_info.get(field) != sub_info.get(field):
                level = errors if field == "format" else notes
                level.append(f"{field}: plik ma {sub_info.get(field)}, wzorzec {ref_info.get(field)}")
        for col in ref.columns:
            if col in sub.columns and col != args.key:
                if pd.api.types.is_numeric_dtype(ref[col]) and not pd.api.types.is_numeric_dtype(sub[col]):
                    errors.append(f"kolumna `{col}` jest liczbowa we wzorcu, a w pliku nie")
    elif args.test:
        ref, _ = read_table(args.test)
        ref_name = "plik testowy"
    else:
        notes.append("bez --sample i --test sprawdzam tylko spojnosc wewnetrzna pliku")

    if ref is not None and len(sub) != len(ref):
        errors.append(f"liczba wierszy {len(sub)} != {len(ref)} ({ref_name})")
    if args.key:
        if args.key not in sub.columns:
            errors.append(f"brak kolumny klucza `{args.key}`")
        else:
            dup = int(sub[args.key].duplicated().sum())
            if dup:
                errors.append(f"{dup} powtorzonych kluczy")
            if ref is not None and args.key in ref.columns:
                a, b = set(sub[args.key].astype(str)), set(ref[args.key].astype(str))
                if a != b:
                    errors.append(f"zbior kluczy sie rozni: brakuje {len(b - a)}, nadmiarowych {len(a - b)}; przyklad brakujacego: {sorted(b - a)[:3]}")
                elif list(sub[args.key].astype(str)) != list(ref[args.key].astype(str)):
                    notes.append("kolejnosc kluczy inna niz we wzorcu: zapytaj Partnera, czy ma znaczenie, albo posortuj jak we wzorcu")

    pred_cols = [args.pred_col] if args.pred_col else [c for c in sub.columns if c != args.key]
    for col in pred_cols:
        if col not in sub.columns:
            errors.append(f"brak kolumny predykcji `{col}`")
            continue
        s = sub[col]
        n_na = int(s.isna().sum())
        if n_na:
            errors.append(f"`{col}`: {n_na} pustych wartosci")
        if args.labels:
            allowed = {x.strip() for x in args.labels.split(",")}
            bad = sorted(set(s.dropna().astype(str)) - allowed)
            if bad:
                errors.append(f"`{col}`: niedozwolone etykiety {bad[:10]} (dozwolone: {sorted(allowed)})")
        elif args.sample and col in ref.columns and not pd.api.types.is_numeric_dtype(ref[col]):
            known = set(ref[col].dropna().astype(str))
            bad = sorted(set(s.dropna().astype(str)) - known)
            if bad and len(known) <= 50:
                notes.append(f"`{col}`: wartosci spoza wzorca {bad[:10]}; jesli wzorzec pokazuje wszystkie klasy, to blad")
        if args.numeric or args.vmin is not None or args.vmax is not None:
            num = pd.to_numeric(s, errors="coerce")
            if num.isna().sum() > n_na:
                errors.append(f"`{col}`: {int(num.isna().sum()) - n_na} wartosci nie jest liczba")
            if args.vmin is not None and (num < args.vmin).any():
                errors.append(f"`{col}`: {int((num < args.vmin).sum())} wartosci ponizej {args.vmin}")
            if args.vmax is not None and (num > args.vmax).any():
                errors.append(f"`{col}`: {int((num > args.vmax).sum())} wartosci powyzej {args.vmax}")

    print(f"Plik: {args.submission}  wiersze: {len(sub)}  kolumny: {list(sub.columns)}  format: {sub_info}")
    for n in notes:
        print(f"  UWAGA: {n}")
    if errors:
        print("BLEDY:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("OK: format pliku wynikowego jest poprawny.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
