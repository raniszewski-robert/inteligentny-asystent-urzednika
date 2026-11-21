"""Wspolne funkcje skryptow hn-dane-od-partnera: wczytywanie tabel i polskie wzorce danych.

Zaleznosci: pandas (BSD-3), opcjonalnie pyarrow (Apache-2.0) dla Parquet i openpyxl (MIT) dla Excela.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

import pandas as pd

TABLE_EXT = {".csv", ".tsv", ".txt", ".json", ".jsonl", ".ndjson", ".parquet", ".xlsx", ".xlsm"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp", ".tif", ".tiff"}


def sniff_encoding(path: Path) -> str:
    raw = path.open("rb").read(200_000)
    for enc in ("utf-8-sig", "cp1250", "iso-8859-2"):
        try:
            raw.decode(enc)
            return enc
        except UnicodeDecodeError:
            continue
    return "latin-1"


def sniff_sep(path: Path, encoding: str) -> str:
    with path.open("r", encoding=encoding, errors="replace") as fh:
        sample = "".join(fh.readline() for _ in range(30))
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
    except csv.Error:
        first = sample.splitlines()[0] if sample else ""
        return max(",;\t|", key=first.count)


def read_table(path: str | Path, nrows: int | None = None) -> tuple[pd.DataFrame, dict]:
    """Wczytuje CSV/TSV/JSON/JSONL/Parquet/Excel. Zwraca (DataFrame, informacje o formacie)."""
    path = Path(path)
    ext = path.suffix.lower()
    info: dict = {"format": ext.lstrip(".")}
    if ext in {".csv", ".tsv", ".txt"}:
        enc = sniff_encoding(path)
        sep = sniff_sep(path, enc)
        info.update(encoding=enc, separator=repr(sep))
        df = pd.read_csv(path, sep=sep, encoding=enc, nrows=nrows, low_memory=False)
    elif ext in {".jsonl", ".ndjson"}:
        df = pd.read_json(path, lines=True, nrows=nrows)
    elif ext == ".json":
        obj = json.loads(path.read_text(encoding=sniff_encoding(path)))
        if isinstance(obj, dict):
            lists = {k: v for k, v in obj.items() if isinstance(v, list) and v and isinstance(v[0], dict)}
            if lists:
                key = max(lists, key=lambda k: len(lists[k]))
                info["json_key"] = key
                obj = lists[key]
            else:
                obj = [obj]
        df = pd.json_normalize(obj)
        if nrows:
            df = df.head(nrows)
    elif ext == ".parquet":
        df = pd.read_parquet(path)
        if nrows:
            df = df.head(nrows)
    elif ext in {".xlsx", ".xlsm"}:
        sheets = pd.read_excel(path, sheet_name=None, nrows=nrows)
        info["sheets"] = {name: list(s.shape) for name, s in sheets.items()}
        first = next(iter(sheets))
        info["sheet_used"] = first
        df = sheets[first]
    else:
        raise ValueError(f"Nieobslugiwany format: {ext}. Obslugiwane: {sorted(TABLE_EXT)}")
    # Kolumny z listami lub slownikami (JSON) zamieniamy na tekst, zeby dalo sie liczyc duplikaty.
    for col in df.columns:
        if df[col].map(lambda v: isinstance(v, (list, dict))).any():
            df[col] = df[col].map(lambda v: json.dumps(v, ensure_ascii=False, sort_keys=True) if isinstance(v, (list, dict)) else v)
    return df, info


def write_table(df: pd.DataFrame, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".parquet":
        df.to_parquet(path, index=False)
    elif path.suffix.lower() in {".jsonl", ".ndjson"}:
        df.to_json(path, orient="records", lines=True, force_ascii=False)
    else:
        df.to_csv(path, index=False)


# --- polskie identyfikatory i dane osobowe -------------------------------------------------

def _checksum(digits: str, weights: tuple[int, ...]) -> int:
    return sum(int(d) * w for d, w in zip(digits, weights))


def valid_pesel(s: str) -> bool:
    if not re.fullmatch(r"\d{11}", s):
        return False
    month = int(s[2:4]) % 20
    day = int(s[4:6])
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return False
    return (10 - _checksum(s[:10], (1, 3, 7, 9, 1, 3, 7, 9, 1, 3)) % 10) % 10 == int(s[10])


def valid_nip(s: str) -> bool:
    s = re.sub(r"[\s-]", "", s)
    if not re.fullmatch(r"\d{10}", s):
        return False
    c = _checksum(s[:9], (6, 5, 7, 2, 3, 4, 5, 6, 7)) % 11
    return c != 10 and c == int(s[9])


def valid_regon9(s: str) -> bool:
    if not re.fullmatch(r"\d{9}", s):
        return False
    c = _checksum(s[:8], (8, 9, 2, 3, 4, 5, 6, 7)) % 11
    return (0 if c == 10 else c) == int(s[8])


MONTHS = "stycznia|lutego|marca|kwietnia|maja|czerwca|lipca|sierpnia|września|wrzesnia|października|pazdziernika|listopada|grudnia"

PATTERNS: dict[str, re.Pattern] = {
    "pesel": re.compile(r"(?<!\d)\d{11}(?!\d)"),
    "nip": re.compile(r"(?<!\d)(?:\d{10}|\d{3}-\d{3}-\d{2}-\d{2}|\d{3}-\d{2}-\d{2}-\d{3})(?!\d)"),
    "regon": re.compile(r"(?<!\d)\d{9}(?!\d)"),
    "email": re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"),
    "telefon": re.compile(r"(?<![\d-])(?:\+48[ -]?)?\d{3}[ -]\d{3}[ -]\d{3}(?![\d-])"),
    "iban": re.compile(r"(?<![\w])(?:PL ?)?\d{2}(?: ?\d{4}){6}(?!\d)"),
    "kod_pocztowy": re.compile(r"(?<![\d-])\d{2}-\d{3}(?![\d-])"),
    "data": re.compile(rf"(?<!\d)(?:\d{{4}}-\d{{2}}-\d{{2}}|\d{{1,2}}[./-]\d{{1,2}}[./-]\d{{4}}|\d{{1,2}} (?:{MONTHS}) \d{{4}})(?!\d)", re.I),
    "kwota": re.compile(r"(?<![\d,.])\d{1,3}(?:[  .]?\d{3})*(?:,\d{2})?\s?(?:zł|zl|PLN)(?![a-zA-Z])", re.I),
    "krs": re.compile(r"KRS[:\s]*(?:nr\.?\s*)?(\d{10})", re.I),
}
VALIDATORS = {"pesel": valid_pesel, "nip": valid_nip, "regon": valid_regon9}
PII_TYPES = ("pesel", "email", "telefon", "iban")
PII_NAME_HINTS = re.compile(r"pesel|nazwisk|imi[eę]|imie|adres|ulica|telefon|phone|e-?mail|urodz|birth|dow[oó]d|paszport|name$|^name", re.I)


def find_entities(text: str, types: tuple[str, ...] | None = None) -> dict[str, list[str]]:
    """Zwraca znalezione wartosci wedlug typu. Identyfikatory z suma kontrolna sa walidowane."""
    out: dict[str, list[str]] = {}
    for name, pattern in PATTERNS.items():
        if types and name not in types:
            continue
        hits = []
        for m in pattern.finditer(text):
            value = m.group(1) if pattern.groups else m.group(0)
            check = VALIDATORS.get(name)
            if check and not check(value):
                continue
            hits.append(value.strip())
        if hits:
            out[name] = hits
    return out
