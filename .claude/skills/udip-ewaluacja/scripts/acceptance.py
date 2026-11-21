#!/usr/bin/env python3
"""Testy akceptacyjne = scenariusz jury z treści zadania (sekcja 6 „Sposób testowania”), end-to-end na danych UMB.

1. Wgranie wniosku (PDF/Word) → podobne sprawy w archiwum.
2. Odpowiedź z wydziału → projekt pisma.
3. Plik z danymi osobowymi → anonimizacja (nic nie wycieka).
4. Stabilność: każdy krok kończy się bez wyjątku na każdym pliku próbki UMB (w tym rękopisie).
5. Kalendarz: 10 wniosków od najstarszego, podświetlenie pilnych, statusy.
6. Wgrywanie danych: import arkusza kalendarium i archiwum odpowiedzi.

  python3 acceptance.py --repo ../../../.. [--today 2026-11-22] [--report wynik.md]
Kod wyjścia 0 = wszystkie testy przeszły.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from datetime import date
from pathlib import Path

SK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SK.parents[1]))  # repo: pakiet udip
from udip.analyze import analyze, load_departments  # noqa: E402
from udip.anonymize import apply as anon_apply, detect  # noqa: E402
from udip.draft import build  # noqa: E402
from udip.importer import convert, demo_shift  # noqa: E402
from udip.ingest import read_any  # noqa: E402
from udip.register import Request, rows  # noqa: E402
from udip.search import Archive, load_archive  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repo", type=Path, default=SK.parents[1])
    p.add_argument("--today", default="2026-11-22")
    p.add_argument("--report", type=Path)
    a = p.parse_args(argv)
    repo, today = a.repo.resolve(), date.fromisoformat(a.today)
    umb = repo / "data-partner" / "umb"
    res: list[tuple[str, bool, str]] = []
    deps = load_departments()
    arch_recs = load_archive(umb / "archiwum_umb.jsonl")

    # 1. Wniosek z pliku → podobne sprawy. Prawdziwa ścieżka: pełne archiwum (z tą sprawą w środku), okno 365 dni,
    #    deduplikacja po identycznym tekście w analyze(); sprawa starsza niż rok wraca jako „older_than_window”.
    t0 = time.time()
    arch_full = Archive(arch_recs)
    for fname, twin, dep in [("Wniosek - BKS.IV.1431.599.2026.docx", "BKS.IV.1431.307.2025", "WE"),
                             ("Wniosek - BKS.IV.1431.293.2025.docx", "BKS.IV.1431.543.2026", "WGK"),
                             ("Wniosek - BKS.IV.1431.590.2026.pdf", None, "WIM")]:
        doc = read_any(umb / "probki" / fname)
        own = fname.split(" - ")[1].rsplit(".", 1)[0]
        an = analyze(doc["text"], arch_full, deps, today, provider="rules")
        ids = [s["id"] for s in an["similar_cases"][:3]]
        deps3 = [d["department"] for d in an["departments_overall"][:3]]
        ok = own not in ids and (twin in ids if twin else True) and dep in deps3
        res.append((f"1. {fname}: podobne sprawy / wydział", ok, f"top3={ids}; wydziały={deps3} (oczek. {dep}); pytań={len(an['questions'])}"))
    # 2. Odpowiedź wydziału → projekt pisma (prawdziwa sprawa 543)
    c = umb / "przypadek_543"
    text, rep = build((c / "wniosek.txt").read_text(encoding="utf-8"),
                      [(f.name, f.read_text(encoding="utf-8")) for f in [c / "SCHRONISKO.txt", c / "WGK.txt"]],
                      "BKS.IV.1431.543.2026", date(2026, 8, 14), "udostepnienie", "template", "[podpis]", today)
    must = ["839 psom", "3.143.761,14", "Ad 5", "Łączę wyrazy szacunku", "Schronisko dla Zwierząt"]
    miss = [m for m in must if m not in text]
    ad3 = text.split("Ad 3", 1)[1].split("Ad 4", 1)[0] if "Ad 3" in text else ""
    placed = "839 psom" in ad3  # liczba zwierząt pod pytaniem 3 („ilu bezdomnym zwierzętom…”), jak w piśmie BKS
    res.append(("2. Projekt pisma z odpowiedzi wydziałów (543.2026)", not miss and not rep["gaps"] and not rep["number_check_template"] and placed,
                f"pytań={rep['questions']}, luki={rep['gaps']}, brakujące frazy={miss}, liczby spoza źródeł={rep['number_check_template']}, "
                f"pominięte liczby={rep['omitted_numbers_template']}, „839 psom” w Ad 3={placed}, niepewne przypisania={len(rep['uncertain_assignment'])}"))
    from udip.draft import check_numbers
    fake = check_numbers(["Budżet wyniósł 3.143 zł; opieka nad 560 psami i 839 kotami."], [(c / "SCHRONISKO.txt").read_text(encoding="utf-8")])
    res.append(("2b. Kontrola halucynacji liczb (zmyślona kwota, zamienione psy/koty)", len(fake) == 3, f"odrzucone: {fake}"))
    # 3. Anonimizacja: dokument z danymi osobowymi (lista UMB)
    pii = ("Bydgoszcz, 3 listopada 2026 r.\nAnna Nowak-Kowalska\nul. Słoneczna 7/12\n85-001 Bydgoszcz\ntel. 601 234 567\n"
           "anna.nowak@example.com\nPESEL 44051401359, dowód ABA300000, rachunek PL61 1090 1014 0000 0712 1981 2874\n"
           "Wnioskodawczyni, ur. 12.03.1980 r. w Toruniu, pyta o decyzję. Sprawę zgłosił J. Nowak.\nZ poważaniem\nAnna Nowak-Kowalska\n")
    spans = [s.__dict__ for s in detect(pii, provider="rules")]
    red = anon_apply(pii, spans, accept_all=True)
    leaks = [x for x in ["Nowak-Kowalska", "Słoneczna 7/12", "601 234 567", "anna.nowak@", "44051401359", "ABA300000", "1090 1014", "12.03.1980"] if x in red]
    review = [s["text"] for s in spans if s["status"] == "review"]
    res.append(("3. Anonimizacja pliku z danymi osobowymi", not leaks, f"wykryto {len(spans)}, wycieki po akceptacji: {leaks or 'brak'}; do decyzji urzędnika: {review}"))
    # 4. Stabilność: każdy plik próbki (w tym rękopis 16.2026) przechodzi przez analizę i anonimizację
    errs, warned = [], []
    for f in sorted((umb / "probki").iterdir()):
        try:
            d = read_any(f)
            analyze(d["text"], Archive(arch_recs), deps, today, provider="rules")
            detect(d["text"], provider="rules")
            if d.get("warning"):
                warned.append(f.name)
        except Exception as e:  # noqa: BLE001
            errs.append(f"{f.name}: {e}")
    for r in arch_recs:
        try:
            analyze(r["request_text"], Archive(arch_recs), deps, today, provider="rules")
            detect(r["request_text"] + r["response_text"], provider="rules")
        except Exception as e:  # noqa: BLE001
            errs.append(f"{r['id']}: {e}")
    res.append(("4. Stabilność na wszystkich próbkach UMB", not errs, f"{len(arch_recs)} spraw + {len(list((umb / 'probki').iterdir()))} plików, błędy: {errs or 'brak'}, czas {time.time() - t0:.1f} s"))
    # 5. Kalendarz: 10 wniosków UMB, od najstarszego, podświetlenia
    recs, issues = convert(umb / "kalendarium_umb.xlsx")
    real = rows([Request(**{k: v for k, v in r.items() if k in Request.__dataclass_fields__}) for r in recs], today, 2025)
    res.append(("5a. Kalendarz UMB bez zmian dat: filtr roku 2025", len(real) == 2 and all(r["urgency"] == "done" for r in real),
                f"{len(real)} sprawy z 2025 r., wszystkie zakończone (arkusz UMB ma same zamknięte sprawy)"))
    demo = demo_shift(recs, today)
    reqs = [Request(**{k: v for k, v in r.items() if k in Request.__dataclass_fields__}) for r in demo]
    rs = rows(reqs, today)
    order_ok = [r["received"] for r in rs] == sorted(r["received"] for r in rs)
    levels = {r["urgency"] for r in rs}
    ok = len(rs) == 10 and order_ok and "overdue" in levels and ("today" in levels or "tomorrow" in levels)
    res.append(("5b. Kalendarz 10 wniosków UMB w trybie demo (daty przesunięte): kolejność i podświetlenia", ok, f"poziomy={sorted(levels)}, kolejność od najstarszego={order_ok}"))
    # 6. Wgrywanie danych: import arkusza i archiwum
    res.append(("6. Import arkusza kalendarium UMB + kontrola niespójności", len(recs) == 10 and len(issues) >= 3, f"zaimportowano {len(recs)}, niespójności wykryte: {len(issues)}"))
    with tempfile.TemporaryDirectory() as td:
        from udip.ingest import import_archive
        (Path(td) / "a").mkdir()
        for f in (umb / "probki").iterdir():
            (Path(td) / "a" / f.name.replace("Wniosek - ", "").replace(" ", "_")).write_bytes(f.read_bytes())
        n = import_archive(Path(td) / "a", Path(td) / "x.jsonl")
    res.append(("6b. Import katalogu dokumentów do archiwum", n == 3, f"zaimportowano {n} spraw z katalogu"))

    lines = [f"# Testy akceptacyjne (scenariusz jury), {today}", "", "| Test | Wynik | Szczegóły |", "|---|---|---|"]
    lines += [f"| {n} | {'✅' if ok else '❌'} | {d} |" for n, ok, d in res]
    out = "\n".join(lines)
    print(out)
    if a.report:
        a.report.write_text(out + "\n", encoding="utf-8")
    return 0 if all(ok for _, ok, _ in res) else 1


if __name__ == "__main__":
    sys.exit(main())
