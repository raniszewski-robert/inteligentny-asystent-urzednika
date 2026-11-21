#!/usr/bin/env python3
"""Szybki profil nieznanego zbioru danych: tabela, katalog obrazow albo katalog PDF-ow.

  python3 profile_dataset.py dane.csv --target etykieta --id id --out profil.md
  python3 profile_dataset.py train.csv --compare test.csv --id id     # wycieki miedzy podzialami
  python3 profile_dataset.py katalog_obrazow/                          # klasy = podkatalogi
  python3 profile_dataset.py katalog_pdf/

Wynik: raport markdown na wyjsciu standardowym i (z --out) w pliku.
Zaleznosci: pandas, numpy (BSD-3); Pillow (MIT-CMU) dla obrazow; pypdf (BSD-3) dla PDF-ow.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import IMAGE_EXT, PII_NAME_HINTS, PII_TYPES, TABLE_EXT, find_entities, read_table  # noqa: E402

MAX_PII_ROWS = 2000


def pct(x: float) -> str:
    return f"{x:.1%}"


def md_table(rows: list[list], header: list[str]) -> str:
    def cell(v) -> str:
        return str(v).replace("|", "\\|").replace("\n", " ")
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join(["---"] * len(header)) + "|"]
    lines += ["| " + " | ".join(cell(v) for v in r) + " |" for r in rows]
    return "\n".join(lines)


def kind_of(s: pd.Series) -> str:
    if pd.api.types.is_bool_dtype(s):
        return "bool"
    if pd.api.types.is_numeric_dtype(s):
        return "liczba"
    if pd.api.types.is_datetime64_any_dtype(s):
        return "data"
    return "tekst"


def looks_like_date(s: pd.Series) -> bool:
    sample = s.dropna().astype(str).head(200)
    if sample.empty or sample.str.len().median() > 30 or not sample.str.contains(r"\d{4}|\d{2}[./-]\d{2}").mean() > 0.8:
        return False
    parsed = pd.to_datetime(sample, errors="coerce", format="mixed", dayfirst=True)
    return parsed.notna().mean() > 0.9


def profile_table(df: pd.DataFrame, info: dict, target: str | None, id_col: str | None) -> tuple[list[str], list[str]]:
    out, flags = [], []
    n = len(df)
    out.append(f"Wiersze: **{n}**, kolumny: **{df.shape[1]}**. Format: {info}")
    if n == 0:
        return out + ["Zbior jest pusty."], ["zbior jest pusty"]

    rows, text_cols = [], []
    for col in df.columns:
        s = df[col]
        kind = kind_of(s)
        miss = s.isna().mean()
        nun = s.nunique(dropna=True)
        note = []
        if kind == "tekst":
            lengths = s.dropna().astype(str).str.len()
            med = lengths.median() if not lengths.empty else 0
            if looks_like_date(s):
                note.append("wyglada na date")
            elif med > 60:
                note.append(f"tekst swobodny, mediana {med:.0f} znakow")
                text_cols.append(col)
            elif nun <= max(20, 0.05 * n):
                note.append("kategoria")
        if nun <= 1:
            note.append("STALA")
            flags.append(f"kolumna `{col}` ma jedna wartosc: usun ja z cech")
        elif nun == n and miss == 0 and kind != "liczba":
            note.append("unikalna, mozliwy identyfikator")
        elif nun == n and miss == 0 and kind == "liczba" and pd.api.types.is_integer_dtype(s):
            note.append("unikalna liczba calkowita, mozliwy identyfikator")
        if miss > 0.5:
            flags.append(f"kolumna `{col}` ma {pct(miss)} brakow")
        if kind == "liczba" and nun > 1:
            d = s.describe()
            stats = f"min {d['min']:.4g}, mediana {d['50%']:.4g}, max {d['max']:.4g}"
        else:
            top = s.dropna().astype(str).value_counts().head(3)
            stats = "; ".join(f"{str(k)[:25]} ({v})" for k, v in top.items())
        rows.append([col, kind, pct(miss), nun, stats, ", ".join(note)])
    out += ["", "### Schemat", "", md_table(rows, ["Kolumna", "Typ", "Braki", "Unikalne", "Statystyki albo najczestsze wartosci", "Uwagi"])]

    dup = int(df.duplicated().sum())
    out += ["", "### Duplikaty", "", f"Pelne duplikaty wierszy: **{dup}** ({pct(dup / n)})."]
    if dup:
        flags.append(f"{dup} pelnych duplikatow wierszy: usun przed podzialem, inaczej trafia i do train, i do walidacji")
    if id_col and id_col in df.columns:
        dup_id = int(df[id_col].duplicated().sum())
        out.append(f"Powtorzone wartosci `{id_col}`: **{dup_id}**.")
        if dup_id:
            flags.append(f"identyfikator `{id_col}` nie jest unikalny ({dup_id} powtorzen): rozwaz podzial grupowy po tej kolumnie")
    if target and target in df.columns:
        feats = [c for c in df.columns if c not in (target, id_col)]
        if feats:
            g = df.groupby(feats, dropna=False)[target].nunique()
            conflict = int((g > 1).sum())
            if conflict:
                out.append(f"Identyczne cechy z rozna etykieta: **{conflict}** grup.")
                flags.append(f"{conflict} grup wierszy o identycznych cechach ma rozne etykiety: szum w etykietach ogranicza osiagalny wynik")

    if target:
        out += ["", f"### Cel: `{target}`", ""]
        if target not in df.columns:
            out.append(f"BRAK kolumny `{target}`. Dostepne: {list(df.columns)}")
            flags.append(f"brak kolumny celu `{target}`")
        else:
            y = df[target]
            if y.isna().any():
                flags.append(f"{int(y.isna().sum())} wierszy bez etykiety")
            if kind_of(y) == "liczba" and y.nunique() > 20:
                d = y.describe()
                out.append(f"Wyglada na **regresje**: min {d['min']:.4g}, mediana {d['50%']:.4g}, srednia {d['mean']:.4g}, max {d['max']:.4g}, odch. std. {d['std']:.4g}.")
                skew = y.skew()
                if abs(skew) > 2:
                    flags.append(f"cel jest mocno skosny (skosnosc {skew:.1f}): rozwaz log-transformacje i sprawdz, czy metryka to MAE czy RMSE")
            else:
                vc = y.value_counts(dropna=False)
                out.append(f"Wyglada na **klasyfikacje**, klas: {len(vc)}.")
                out += ["", md_table([[k, v, pct(v / n)] for k, v in vc.head(30).items()], ["Klasa", "Liczba", "Udzial"])]
                ratio = vc.max() / max(vc.min(), 1)
                if ratio >= 5:
                    flags.append(f"klasy niezbalansowane ({ratio:.0f}:1): accuracy bedzie mylace, patrz na F1 macro i uzyj podzialu stratyfikowanego")
                if vc.min() < 5:
                    flags.append(f"najrzadsza klasa ma {vc.min()} przykladow: walidacja dla niej bedzie niestabilna")

    pii_rows = []
    for col in df.columns:
        hits: Counter = Counter()
        if kind_of(df[col]) == "tekst" or col in df.select_dtypes("number").columns:
            sample = df[col].dropna().astype(str).head(MAX_PII_ROWS)
            for value in sample:
                for name, found in find_entities(value, PII_TYPES).items():
                    hits[name] += len(found)
        hint = bool(PII_NAME_HINTS.search(str(col)))
        if hits or hint:
            pii_rows.append([col, "tak" if hint else "", ", ".join(f"{k}: {v}" for k, v in hits.items())])
    out += ["", "### Dane osobowe (heurystyka)", ""]
    if pii_rows:
        out.append(md_table(pii_rows, ["Kolumna", "Nazwa sugeruje dane osobowe", f"Trafienia wzorcow w pierwszych {MAX_PII_ROWS} wartosciach"]))
        flags.append("mozliwe dane osobowe: nie wysylaj tych kolumn do zewnetrznych API bez zgody Partnera, nie commituj danych do repozytorium")
    else:
        out.append("Nie znaleziono numerow PESEL, e-maili, telefonow, rachunkow ani nazw kolumn sugerujacych dane osobowe. To heurystyka: imiona i nazwiska w tekscie swobodnym nie sa wykrywane.")
    if text_cols:
        out += ["", f"Kolumny z tekstem swobodnym: {', '.join(f'`{c}`' for c in text_cols)}."]
    return out, flags


def row_hashes(df: pd.DataFrame, cols: list[str]) -> pd.Series:
    return pd.util.hash_pandas_object(df[cols].astype(str), index=False)


def compare_tables(a: pd.DataFrame, b: pd.DataFrame, id_col: str | None, target: str | None) -> tuple[list[str], list[str]]:
    out, flags = ["", "### Wycieki miedzy podzialami", ""], []
    only_a = [c for c in a.columns if c not in b.columns]
    only_b = [c for c in b.columns if c not in a.columns]
    out.append(f"Kolumny tylko w pierwszym pliku: {only_a or 'brak'}. Tylko w drugim: {only_b or 'brak'}.")
    common = [c for c in a.columns if c in b.columns and c not in (target, id_col)]
    if common:
        ha, hb = set(row_hashes(a, common)), row_hashes(b, common)
        overlap = int(hb.isin(ha).sum())
        out.append(f"Wiersze drugiego pliku o cechach identycznych jak w pierwszym: **{overlap}** z {len(b)} ({pct(overlap / max(len(b), 1))}).")
        if overlap:
            flags.append(f"{overlap} wierszy powtarza sie miedzy plikami: wynik walidacji bedzie zawyzony")
    if id_col and id_col in a.columns and id_col in b.columns:
        shared = len(set(a[id_col]) & set(b[id_col]))
        out.append(f"Wspolne wartosci `{id_col}`: **{shared}**.")
        if shared:
            flags.append(f"{shared} identyfikatorow wystepuje w obu plikach")
    shifts = []
    for col in common:
        if kind_of(a[col]) == "liczba" and kind_of(b[col]) == "liczba" and a[col].std() > 0:
            shift = abs(a[col].mean() - b[col].mean()) / a[col].std()
            if shift > 0.5:
                shifts.append((shift, col))
    if shifts:
        top = ", ".join(f"`{c}` ({s:.1f})" for s, c in sorted(shifts, reverse=True)[:5])
        out.append(f"Kolumny liczbowe o innym rozkladzie w drugim pliku: **{len(shifts)}**. Najwieksze przesuniecia sredniej w odch. std.: {top}.")
        flags.append(f"{len(shifts)} kolumn ma inny rozklad w drugim pliku (najbardziej: {top}): walidacja losowa moze nie odpowiadac testowi Partnera, rozwaz podzial czasowy albo grupowy")
    return out, flags


def profile_images(root: Path, files: list[Path]) -> tuple[list[str], list[str]]:
    from PIL import Image

    out, flags = [], []
    per_class: Counter = Counter()
    hashes: dict[str, list[Path]] = defaultdict(list)
    sizes, modes, corrupt = [], Counter(), []
    for f in files:
        rel = f.relative_to(root)
        per_class[rel.parts[0] if len(rel.parts) > 1 else "(brak podkatalogu)"] += 1
        hashes[hashlib.md5(f.read_bytes()).hexdigest()].append(f)
    step = max(1, len(files) // 500)
    for f in files[::step]:
        try:
            with Image.open(f) as im:
                sizes.append(im.size)
                modes[im.mode] += 1
                im.verify()
        except Exception:
            corrupt.append(f)
    out.append(f"Obrazy: **{len(files)}**, rozszerzenia: {dict(Counter(f.suffix.lower() for f in files))}.")
    out += ["", "### Klasy (podkatalogi)", "", md_table([[k, v, pct(v / len(files))] for k, v in per_class.most_common()], ["Klasa", "Liczba", "Udzial"])]
    if len(per_class) > 1:
        ratio = max(per_class.values()) / max(min(per_class.values()), 1)
        if ratio >= 5:
            flags.append(f"klasy niezbalansowane ({ratio:.0f}:1): patrz na F1 macro")
    else:
        flags.append("brak podkatalogow klas: etykiety sa pewnie w osobnym pliku, zapytaj Partnera")
    if sizes:
        w, h = np.array([s[0] for s in sizes]), np.array([s[1] for s in sizes])
        out += ["", "### Rozmiary (proba do 500 plikow)", "",
                f"Szerokosc: min {w.min()}, mediana {int(np.median(w))}, max {w.max()}. Wysokosc: min {h.min()}, mediana {int(np.median(h))}, max {h.max()}. Tryby koloru: {dict(modes)}."]
    dups = [v for v in hashes.values() if len(v) > 1]
    cross = [v for v in dups if len({p.relative_to(root).parts[0] for p in v}) > 1]
    out += ["", "### Duplikaty", "", f"Grupy identycznych plikow: **{len(dups)}**, w tym miedzy klasami: **{len(cross)}**."]
    if dups:
        flags.append(f"{len(dups)} grup identycznych obrazow: usun przed podzialem")
    if cross:
        flags.append(f"{len(cross)} identycznych obrazow ma rozne klasy: szum w etykietach")
    if corrupt:
        flags.append(f"{len(corrupt)} plikow nie daje sie otworzyc, np. {corrupt[0].name}")
    return out, flags


def profile_pdfs(files: list[Path]) -> tuple[list[str], list[str]]:
    from pypdf import PdfReader

    out, flags, rows = [], [], []
    scanned = broken = 0
    pii: Counter = Counter()
    for f in files[:200]:
        try:
            reader = PdfReader(str(f))
            pages = len(reader.pages)
            text = "".join((reader.pages[i].extract_text() or "") for i in range(min(pages, 3)))
        except Exception as exc:
            broken += 1
            rows.append([f.name, "?", "?", f"BLAD: {type(exc).__name__}"])
            continue
        chars = len(text.strip())
        has_text = chars > 50
        scanned += not has_text
        for name, found in find_entities(text, PII_TYPES).items():
            pii[name] += len(found)
        rows.append([f.name, pages, chars, "tekst" if has_text else "SKAN (brak warstwy tekstowej)"])
    out.append(f"PDF-y: **{len(files)}** (sprawdzono {min(len(files), 200)}). Bez warstwy tekstowej: **{scanned}**. Nieczytelne: **{broken}**.")
    out += ["", md_table(rows[:40], ["Plik", "Strony", "Znaki na 3 pierwszych stronach", "Rodzaj"])]
    if scanned:
        flags.append(f"{scanned} PDF-ow to skany: potrzebny OCR albo model czytajacy obrazy; zaplanuj to wczesnie")
    if broken:
        flags.append(f"{broken} PDF-ow nie daje sie odczytac")
    if pii:
        out += ["", f"Dane osobowe w tekscie (heurystyka): {dict(pii)}."]
        flags.append("PDF-y zawieraja mozliwe dane osobowe: ustal z Partnerem, czy mozna je wysylac do zewnetrznego API")
    return out, flags


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", help="plik tabelaryczny albo katalog")
    ap.add_argument("--target", help="kolumna celu (etykieta albo wartosc)")
    ap.add_argument("--id", dest="id_col", help="kolumna identyfikatora")
    ap.add_argument("--compare", help="drugi plik (np. test) do sprawdzenia wyciekow")
    ap.add_argument("--out", help="zapisz raport do pliku markdown")
    args = ap.parse_args()

    path = Path(args.path)
    if not path.exists():
        print(f"BLAD: nie ma {path}", file=sys.stderr)
        return 2
    out, flags = [f"# Profil danych: `{path}`", ""], []

    if path.is_dir():
        files = sorted(p for p in path.rglob("*") if p.is_file() and not p.name.startswith("."))
        images = [f for f in files if f.suffix.lower() in IMAGE_EXT]
        pdfs = [f for f in files if f.suffix.lower() == ".pdf"]
        tables = [f for f in files if f.suffix.lower() in TABLE_EXT]
        out.append(f"Katalog: {len(files)} plikow. Obrazy: {len(images)}, PDF-y: {len(pdfs)}, pliki tabelaryczne: {len(tables)}, inne: {len(files) - len(images) - len(pdfs) - len(tables)}.")
        if images:
            o, f = profile_images(path, images)
            out += ["", "## Obrazy", "", *o]
            flags += f
        if pdfs:
            o, f = profile_pdfs(pdfs)
            out += ["", "## PDF-y", "", *o]
            flags += f
        if tables:
            out += ["", "## Pliki tabelaryczne w katalogu", "", "Uruchom profil osobno dla kazdego:", ""]
            out += [f"- `{t}` ({t.stat().st_size / 1e6:.2f} MB)" for t in tables[:30]]
        if not (images or pdfs or tables):
            flags.append("nie rozpoznano zadnego obslugiwanego formatu: sprawdz rozszerzenia i zapytaj Partnera o opis danych")
    else:
        try:
            df, info = read_table(path)
        except Exception as exc:
            print(f"BLAD wczytywania {path}: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 2
        o, f = profile_table(df, info, args.target, args.id_col)
        out += o
        flags += f
        if args.compare:
            other, _ = read_table(args.compare)
            o, f = compare_tables(df, other, args.id_col, args.target)
            out += o
            flags += f

    out += ["", "## Na co uwazac", ""]
    out += [f"- {x}" for x in flags] or ["- Brak ostrzezen z automatycznych kontroli."]
    report = "\n".join(out) + "\n"
    print(report)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(report, encoding="utf-8")
        print(f"[zapisano {args.out}]", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
