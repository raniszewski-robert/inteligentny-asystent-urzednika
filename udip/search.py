"""Wyszukiwanie podobnych wniosków w archiwum (BM25, bez zależności, działa offline).

Archiwum: JSONL z polami id, date (RRRR-MM-DD), title, request_text, response_text, departments (lista id komórek).
Indeks liczy się w pamięci (setki–tysiące spraw: milisekundy). Dla >50 tys. spraw: SQLite FTS5 albo embeddingi (research/04).

CLI: .claude/skills/udip-archiwum-i-wydzialy/scripts/search.py
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter
from datetime import date
from pathlib import Path

from .textpl import tokens


class BM25:
    def __init__(self, docs: list[list[str]], k1: float = 1.4, b: float = 0.75):
        self.docs = docs
        self.k1, self.b = k1, b
        self.N = len(docs)
        self.avgdl = sum(map(len, docs)) / max(self.N, 1)
        self.tf = [Counter(d) for d in docs]
        df = Counter(t for d in docs for t in set(d))
        self.idf = {t: math.log(1 + (self.N - n + 0.5) / (n + 0.5)) for t, n in df.items()}

    def score(self, q: list[str], i: int) -> float:
        tf, dl, s = self.tf[i], len(self.docs[i]), 0.0
        for t in set(q):
            if t in tf:
                f = tf[t]
                s += self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
        return s


def load_archive(path: Path) -> list[dict]:
    recs = []
    for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            try:
                recs.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"Pominięto linię {n}: {e}", file=sys.stderr)
    return recs


def request_core(text: str) -> str:
    """Sama treść żądania, bez nagłówka z danymi wnioskodawcy i formułek (one zaszumiają podobieństwo)."""
    from .analyze import split_questions  # import leniwy: analyze importuje search
    return " ".join(split_questions(text))


def doc_tokens(r: dict) -> list[str]:
    # tytuł liczony podwójnie: krótki, gęsty w treść
    return (tokens(r.get("title", "")) * 2 + tokens(request_core(r.get("request_text", "")))
            + tokens(r.get("response_text", ""))[:300])


class Archive:
    def __init__(self, records: list[dict]):
        self.records = records
        self.bm25 = BM25([doc_tokens(r) for r in records])

    def search(self, query: str, k: int = 5, since: date | None = None, exclude_id: str | None = None) -> list[dict]:
        q = tokens(request_core(query)) or tokens(query)
        res = []
        for i, r in enumerate(self.records):
            if exclude_id and r.get("id") == exclude_id:
                continue
            if since and r.get("date") and date.fromisoformat(r["date"]) < since:
                continue
            s = self.bm25.score(q, i)
            if s > 0:
                shared = sorted(set(q) & set(self.bm25.docs[i]), key=lambda t: (-self.bm25.idf.get(t, 0), t))[:6]  # remis: alfabetycznie (stały wynik)
                res.append({"id": r.get("id"), "date": r.get("date"), "title": r.get("title"), "score": round(s, 2),
                            "departments": r.get("departments", []), "matched_terms": shared,
                            "response_excerpt": (r.get("response_text") or "")[:300]})
        res.sort(key=lambda x: -x["score"])
        if res:  # względny próg: odrzuć wyniki < 25% najlepszego (szum)
            top = res[0]["score"]
            res = [x for x in res if x["score"] >= 0.25 * top]
        return res[:k]
