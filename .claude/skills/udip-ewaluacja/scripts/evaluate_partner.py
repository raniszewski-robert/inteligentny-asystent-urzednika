#!/usr/bin/env python3
"""Ewaluacja na prawdziwych próbkach UMB (leave-one-out): podobne sprawy i wydział.

Dla każdej sprawy z archiwum_umb.jsonl: zapytanie = treść wniosku, archiwum = pozostałe sprawy (bez filtra roku).
Pary „bliźniacze” (ten sam temat w innym roku/wniosku) zdefiniowane w TWINS na podstawie arkusza kalendarium UMB.
  python3 evaluate_partner.py ../../../../data-partner/umb/archiwum_umb.jsonl
"""
import json
import sys
from datetime import date
from pathlib import Path

SK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SK.parents[1]))  # repo: pakiet udip
from udip.analyze import analyze, load_departments  # noqa: E402
from udip.search import Archive  # noqa: E402

TWINS = [("BKS.IV.1431.293.2025", "BKS.IV.1431.543.2026"),  # bezdomne zwierzęta 2024 vs 2025
         ("BKS.IV.1431.307.2025", "BKS.IV.1431.599.2026"),  # liczba uczniów i cudzoziemców
         ("BKS.IV.1431.509.2026", "BKS.IV.1431.590.2026")]  # kompleks Astoria


def main() -> int:
    recs = [json.loads(l) for l in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines() if l.strip()]
    deps = load_departments()
    twin = {a: b for a, b in TWINS} | {b: a for a, b in TWINS}
    hit_twin, n_twin, top1, top3, n_dep = 0, 0, 0, 0, 0
    print("| Sprawa | Oczekiwany wydział | Propozycja (top 3) | Podobne (top 3) | Bliźniak w top 3 |\n|---|---|---|---|---|")
    for r in recs:
        others = Archive([x for x in recs if x["id"] != r["id"]])
        res = analyze(r["request_text"], others, deps, date(2026, 11, 22), since_days=0, provider="rules")
        sim = [s["id"].replace("BKS.IV.1431.", "") for s in res["similar_cases"][:3]]
        got = [d["department"] for d in res["departments_overall"][:3]]
        exp = [d for d in r["departments"] if not d.startswith("ZEWN")]
        tw = ""
        if r["id"] in twin:
            n_twin += 1
            ok = twin[r["id"]].replace("BKS.IV.1431.", "") in sim
            hit_twin += ok
            tw = "tak" if ok else "NIE"
        if exp:
            n_dep += 1
            top1 += got[:1] and got[0] in exp
            top3 += any(g in exp for g in got)
        print(f"| {r['id'].replace('BKS.IV.1431.', '')} | {', '.join(r['departments'])} | {', '.join(got)} | {', '.join(sim)} | {tw} |")
    print(f"\nBliźniak w top 3: {hit_twin}/{n_twin}. Wydział: top-1 {top1}/{n_dep}, top-3 {top3}/{n_dep} (sprawy z wydziałem UMB).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
