#!/usr/bin/env python3
"""Baseline ekstrakcji informacji bez GPU i bez LLM: wzorce dla polskich dokumentow urzedowych.

Wyciaga z tekstu albo PDF-ow: daty, kwoty w zl, NIP, PESEL, REGON, KRS, e-mail, telefon, kod pocztowy, rachunek.
NIP, PESEL i REGON sa sprawdzane suma kontrolna. To punkt odniesienia dla rozwiazania z LLM:
jesli LLM nie wygrywa z wzorcami na danym polu, zostaw wzorce (sa darmowe, szybkie i deterministyczne).

  python3 extract_fields.py run dokumenty/ --out wynik.jsonl          # pliki .txt i .pdf
  python3 extract_fields.py eval --pred wynik.jsonl --gold zloty.jsonl  # precyzja, czulosc, F1 na pole

Format JSONL: {"doc": "nazwa_pliku", "fields": {"nip": ["..."], "data": ["..."]}}
Porownanie po normalizacji (bez spacji i myslnikow w identyfikatorach, male litery).
Zaleznosci: pypdf (BSD-3) dla PDF-ow.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import find_entities  # noqa: E402


def read_doc(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        from pypdf import PdfReader
        return "\n".join((page.extract_text() or "") for page in PdfReader(str(path)).pages)
    return path.read_text(encoding="utf-8", errors="replace")


def normalize(field: str, value: str) -> str:
    v = value.strip().lower()
    if field in {"nip", "pesel", "regon", "krs", "iban", "telefon"}:
        v = re.sub(r"[\s\-]|^pl|^\+48", "", v)
    elif field == "kwota":
        v = re.sub(r"[^\d,]", "", v).rstrip(",")
        if "," not in v:
            v += ",00"
    else:
        v = re.sub(r"\s+", " ", v)
    return v


def cmd_run(args) -> int:
    root = Path(args.path)
    files = [root] if root.is_file() else sorted(p for p in root.rglob("*") if p.suffix.lower() in {".txt", ".pdf", ".md"})
    if not files:
        print(f"BLAD: brak plikow .txt, .md ani .pdf w {root}", file=sys.stderr)
        return 2
    empty = 0
    with open(args.out, "w", encoding="utf-8") as fh:
        for f in files:
            text = read_doc(f)
            empty += len(text.strip()) < 20
            fields = {k: sorted(set(v)) for k, v in find_entities(text).items()}
            fh.write(json.dumps({"doc": f.name, "fields": fields}, ensure_ascii=False) + "\n")
    print(f"Przetworzono {len(files)} dokumentow, zapisano {args.out}.")
    if empty:
        print(f"UWAGA: {empty} dokumentow bez tekstu (skany?). Wzorce ich nie przeczytaja; potrzebny OCR albo model czytajacy obrazy.")
    return 0


def load(path: str) -> dict[str, dict[str, set[str]]]:
    out = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rec = json.loads(line)
            out[rec["doc"]] = {k: {normalize(k, x) for x in (v if isinstance(v, list) else [v])} for k, v in rec.get("fields", {}).items()}
    return out


def cmd_eval(args) -> int:
    pred, gold = load(args.pred), load(args.gold)
    missing = sorted(set(gold) - set(pred))
    if missing:
        print(f"UWAGA: {len(missing)} dokumentow ze zlotego zbioru nie ma predykcji (liczone jako pominiete pola), np. {missing[:3]}")
    stats = defaultdict(lambda: [0, 0, 0])  # tp, fp, fn
    for doc, gold_fields in gold.items():
        pred_fields = pred.get(doc, {})
        for field in set(gold_fields) | set(pred_fields):
            g, p = gold_fields.get(field, set()), pred_fields.get(field, set())
            stats[field][0] += len(g & p)
            stats[field][1] += len(p - g)
            stats[field][2] += len(g - p)
    print(f"{'pole':<14} {'precyzja':>9} {'czulosc':>9} {'F1':>7} {'TP':>5} {'FP':>5} {'FN':>5}")
    f1s, tot = [], [0, 0, 0]
    result = {}
    for field in sorted(stats):
        tp, fp, fn = stats[field]
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        f1s.append(f1)
        tot = [a + b for a, b in zip(tot, (tp, fp, fn))]
        result[field] = {"precision": prec, "recall": rec, "f1": f1, "tp": tp, "fp": fp, "fn": fn}
        print(f"{field:<14} {prec:>9.3f} {rec:>9.3f} {f1:>7.3f} {tp:>5} {fp:>5} {fn:>5}")
    tp, fp, fn = tot
    micro_p = tp / (tp + fp) if tp + fp else 0.0
    micro_r = tp / (tp + fn) if tp + fn else 0.0
    micro = 2 * micro_p * micro_r / (micro_p + micro_r) if micro_p + micro_r else 0.0
    macro = sum(f1s) / len(f1s) if f1s else 0.0
    print(f"F1 macro (srednia po polach): {macro:.3f}   F1 micro: {micro:.3f}   dokumentow: {len(gold)}")
    if args.out:
        Path(args.out).write_text(json.dumps({"f1_macro": macro, "f1_micro": micro, "fields": result}, indent=2), encoding="utf-8")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="wyciagnij pola z plikow")
    r.add_argument("path")
    r.add_argument("--out", default="extracted.jsonl")
    r.set_defaults(func=cmd_run)
    e = sub.add_parser("eval", help="porownaj predykcje ze zlotym zbiorem")
    e.add_argument("--pred", required=True)
    e.add_argument("--gold", required=True)
    e.add_argument("--out")
    e.set_defaults(func=cmd_eval)
    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
