#!/usr/bin/env python3
"""Dzieli zbior na train i walidacje tak, jak Partner prawdopodobnie liczy wynik.

  python3 make_split.py dane.csv --target etykieta                 # stratyfikowany (klasyfikacja) albo losowy (regresja)
  python3 make_split.py dane.csv --target y --group id_wnioskodawcy # ta sama grupa nigdy po obu stronach
  python3 make_split.py dane.csv --target y --time data_wplywu      # walidacja = najnowsze wiersze

Wybor trybu:
  --time   gdy Partner bedzie oceniac na danych pozniejszych niz treningowe (prognozy, nowe sprawy),
  --group  gdy wiersze naleza do wiekszych jednostek (osoba, firma, dokument, kampania) i test zawiera nowe jednostki,
  inaczej  podzial stratyfikowany po klasie.
Pelne duplikaty wierszy sa usuwane przed podzialem.
Zaleznosci: pandas, numpy, scikit-learn (BSD-3).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
from sklearn.model_selection import GroupShuffleSplit, StratifiedGroupKFold, train_test_split

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import read_table, write_table  # noqa: E402


def is_classification(y: pd.Series) -> bool:
    return not (pd.api.types.is_numeric_dtype(y) and y.nunique() > 20)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path")
    ap.add_argument("--target", required=True)
    ap.add_argument("--group", help="kolumna grupy")
    ap.add_argument("--time", help="kolumna czasu")
    ap.add_argument("--valid-size", type=float, default=0.2)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out-dir", default="split")
    args = ap.parse_args()

    df, _ = read_table(args.path)
    for col in filter(None, [args.target, args.group, args.time]):
        if col not in df.columns:
            print(f"BLAD: brak kolumny `{col}`. Dostepne: {list(df.columns)}", file=sys.stderr)
            return 2
    before = len(df)
    df = df.drop_duplicates().dropna(subset=[args.target]).reset_index(drop=True)
    print(f"Wiersze: {before} -> {len(df)} po usunieciu duplikatow i wierszy bez celu.")
    y = df[args.target]
    clf = is_classification(y)

    if args.time:
        order = pd.to_datetime(df[args.time], errors="coerce", format="mixed", dayfirst=True)
        if order.isna().mean() > 0.1:
            print(f"BLAD: {order.isna().mean():.0%} wartosci `{args.time}` nie da sie odczytac jako daty.", file=sys.stderr)
            return 2
        df = df.assign(_t=order).sort_values("_t").drop(columns="_t").reset_index(drop=True)
        cut = int(len(df) * (1 - args.valid_size))
        train, valid = df.iloc[:cut], df.iloc[cut:]
        mode = f"czasowy po `{args.time}` (walidacja = najnowsze {args.valid_size:.0%})"
    elif args.group:
        groups = df[args.group]
        n_groups = groups.nunique()
        if n_groups < 2:
            print(f"BLAD: kolumna `{args.group}` ma tylko jedna grupe; podzial grupowy nie ma sensu.", file=sys.stderr)
            return 2
        if n_groups < 10:
            print(f"UWAGA: tylko {n_groups} grup; walidacja bedzie niestabilna i moze miec inny rozmiar niz {args.valid_size:.0%}.")
        if clf and y.value_counts().min() >= 2:
            n_splits = min(n_groups, max(2, round(1 / args.valid_size)))
            tr_idx, va_idx = next(StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=args.seed).split(df, y, groups))
            mode = f"grupowy stratyfikowany po `{args.group}`"
        else:
            tr_idx, va_idx = next(GroupShuffleSplit(n_splits=1, test_size=args.valid_size, random_state=args.seed).split(df, y, groups))
            mode = f"grupowy po `{args.group}`"
        train, valid = df.iloc[tr_idx], df.iloc[va_idx]
        shared = set(train[args.group]) & set(valid[args.group])
        assert not shared, f"grupy po obu stronach: {list(shared)[:5]}"
    else:
        strat = y if clf and y.value_counts().min() >= 2 else None
        train, valid = train_test_split(df, test_size=args.valid_size, random_state=args.seed, stratify=strat)
        mode = "stratyfikowany po klasie" if strat is not None else "losowy"

    out = Path(args.out_dir)
    write_table(train, out / "train.csv")
    write_table(valid, out / "valid.csv")
    print(f"Tryb: {mode}. Train: {len(train)}, walidacja: {len(valid)}. Zapisano {out}/train.csv i {out}/valid.csv.")
    if clf:
        dist = pd.DataFrame({"train": train[args.target].value_counts(normalize=True), "valid": valid[args.target].value_counts(normalize=True)}).fillna(0)
        print("Udzial klas:")
        print(dist.round(3).to_string())
        missing = set(valid[args.target]) - set(train[args.target])
        if missing:
            print(f"UWAGA: klasy obecne tylko w walidacji: {sorted(map(str, missing))}")
    else:
        print(f"Srednia celu: train {train[args.target].mean():.4g}, walidacja {valid[args.target].mean():.4g}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
