#!/usr/bin/env python3
"""Pomiar jakości: wyszukiwanie podobnych spraw, wskazanie wydziału, anonimizacja.

  python3 evaluate.py --data ../../../../data-samples/syntetyczne --today 2026-11-22 [--report wynik.md]

Metryki:
- wyszukiwanie: hit@5 (czy w top 5 jest choć jedna trafna sprawa z ostatniego roku), MRR;
- wydział: top-1 i top-3 per pytanie (pytanie i → oczekiwany wydział i);
- anonimizacja: precision, recall, F1 na spanach (trafienie = nakładanie ≥ 50% złotego spanu), osobno per typ,
  oraz „wyciek” = złoty span, z którego po redakcji zostaje ≥ 3 znaki jawne.
Dane wejściowe w formacie gen_synthetic.py; dane Partnera przerób do tego formatu (SKILL.md, „Dane Partnera”).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

SK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SK.parents[1]))  # repo: pakiet udip
from udip.analyze import analyze, load_departments  # noqa: E402
from udip.anonymize import detect  # noqa: E402
from udip.search import Archive, load_archive  # noqa: E402


def eval_retrieval_routing(data: Path, today: date) -> dict:
    arch = Archive(load_archive(data / "archiwum.jsonl"))
    deps = load_departments()
    gold = json.loads((data / "testy" / "gold.json").read_text(encoding="utf-8"))
    hits, rr, top1, top3, nq, rows = 0, 0.0, 0, 0, 0, []
    for g in gold:
        text = (data / "testy" / g["file"]).read_text(encoding="utf-8")
        res = analyze(text, arch, deps, today, provider="rules")
        ids = [s["id"] for s in res["similar_cases"]]
        rel = set(g["relevant_archive_ids_last_year"])
        rank = next((i + 1 for i, x in enumerate(ids) if x in rel), None)
        hits += bool(rank)
        rr += 1 / rank if rank else 0
        for qi, exp in enumerate(g["departments"]):
            if qi >= len(res["questions"]):
                break
            got = [r["department"] for r in res["questions"][qi]["routing"]]
            nq += 1
            top1 += bool(got[:1] == [exp])
            top3 += exp in got[:3]
            rows.append((g["file"], qi + 1, exp, got[:3]))
    n = len(gold)
    return {"tests": n, "hit@5": round(hits / n, 3), "MRR": round(rr / n, 3), "questions": nq,
            "dept_top1": round(top1 / nq, 3), "dept_top3": round(top3 / nq, 3), "errors": [r for r in rows if r[2] != (r[3][:1] or [None])[0]]}


def overlap(a: dict, b: dict) -> int:
    return max(0, min(a["end"], b["end"]) - max(a["start"], b["start"]))


def eval_anonymization(data: Path, keep: list[str] | None = None) -> dict:
    gold_all = json.loads((data / "pii" / "gold.json").read_text(encoding="utf-8"))
    tp = fp = fn = leaks = 0
    per = defaultdict(lambda: [0, 0, 0])
    misses = []
    for doc in gold_all:
        text = (data / doc["file"]).read_text(encoding="utf-8")
        pred = [s.__dict__ for s in detect(text, keep, provider="rules")]
        gold = doc["spans"]
        matched_pred = set()
        for g in gold:
            hit = [i for i, p in enumerate(pred) if overlap(p, g) >= 0.5 * (g["end"] - g["start"])]
            if hit:
                tp += 1
                per[g["type"]][0] += 1
                matched_pred.update(hit)
            else:
                fn += 1
                per[g["type"]][2] += 1
                misses.append((doc["file"], g["type"], g["text"]))
            covered = sum(1 for k in range(g["start"], g["end"]) if any(p["start"] <= k < p["end"] for p in pred))
            leaks += (g["end"] - g["start"] - covered) >= 3
        for i, p in enumerate(pred):
            if i not in matched_pred and not any(overlap(p, g) > 0 for g in gold):
                fp += 1
                per[p["type"]][1] += 1
    P = tp / (tp + fp) if tp + fp else 0
    R = tp / (tp + fn) if tp + fn else 0
    return {"docs": len(gold_all), "gold_spans": tp + fn, "precision": round(P, 3), "recall": round(R, 3),
            "f1": round(2 * P * R / (P + R), 3) if P + R else 0, "leaks": leaks,
            "per_type": {t: {"tp": v[0], "fp": v[1], "fn": v[2]} for t, v in sorted(per.items())}, "misses": misses[:15]}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--data", type=Path, required=True)
    p.add_argument("--today", default=date.today().isoformat())
    p.add_argument("--report", type=Path)
    a = p.parse_args(argv)
    rr = eval_retrieval_routing(a.data, date.fromisoformat(a.today))
    an = eval_anonymization(a.data)
    lines = ["# Wynik ewaluacji", "",
             f"Dane: `{a.data}`, dzień odniesienia {a.today}.", "",
             "| Moduł | Metryka | Wynik |", "|---|---|---|",
             f"| Podobne sprawy (ostatni rok) | hit@5 / MRR na {rr['tests']} wnioskach | {rr['hit@5']} / {rr['MRR']} |",
             f"| Wskazanie wydziału | top-1 / top-3 na {rr['questions']} pytaniach | {rr['dept_top1']} / {rr['dept_top3']} |",
             f"| Anonimizacja | P / R / F1 na {an['gold_spans']} spanach w {an['docs']} dok. | {an['precision']} / {an['recall']} / {an['f1']} |",
             f"| Anonimizacja | wycieki (≥3 jawne znaki złotego spanu) | {an['leaks']} |", "",
             "Per typ (tp/fp/fn): " + "; ".join(f"{t} {v['tp']}/{v['fp']}/{v['fn']}" for t, v in an["per_type"].items()), "",
             "Błędy wydziału (plik, pytanie, oczekiwany, top-3): " + ("; ".join(f"{f} q{q} {e} → {g}" for f, q, e, g in rr["errors"]) or "brak"), "",
             "Pominięte spany: " + ("; ".join(f"{f} {t} „{x}”" for f, t, x in an["misses"]) or "brak")]
    out = "\n".join(lines)
    print(out)
    if a.report:
        a.report.write_text(out + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
