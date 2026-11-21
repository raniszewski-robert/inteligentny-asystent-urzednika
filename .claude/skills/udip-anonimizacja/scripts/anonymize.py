#!/usr/bin/env python3
"""CLI: anonimizacja odpowiedzi UDIP (propozycja → akceptacja urzędnika → redakcja). Logika: udip/anonymize.py.

  python3 anonymize.py detect plik.txt --out spans.json [--keep "Jan Nowak"] [--html podglad.html]
  python3 anonymize.py apply plik.txt spans.json --out zanonimizowany.txt [--accept-all]
  python3 anonymize.py --selftest
Domyślnie same reguły; detect --provider anthropic:sonnet (itp.) dokłada propozycje modelu przez udip.llm.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from udip.anonymize import *  # noqa: E402,F401,F403  (import tego pliku daje to samo co udip.anonymize)
from udip.anonymize import apply, detect, iban_ok, idcard_ok, nip_ok, pesel_ok, preview_html, regon_ok  # noqa: E402

SAMPLE = Path(__file__).resolve().parent.parent / "data" / "przyklad_wniosek.txt"




def _selftest() -> int:
    sample = SAMPLE.read_text(encoding="utf-8")
    spans = [asdict(s) for s in detect(sample, keep=["Rafał Bruski"], provider="rules")]
    found = {(s["type"], s["text"]) for s in spans}
    expected = {
        ("OSOBA", "Anna Kowalska-Wiśniewska"), ("ADRES", "ul. Długa 15/4"), ("KOD_MIEJSC", "85-034 Bydgoszcz"),
        ("EMAIL", "anna.kw@example.com"), ("TELEFON", "+48 601 234 567"), ("PESEL", "44051401359"),
        ("IBAN", "PL61 1090 1014 0000 0712 1981 2874"), ("DOWOD", "ABA300000"), ("NIP", "526-104-08-28"),
        ("OSOBA", "Janem Nowakiem"), ("OSOBA", "Kowalska-Wiśniewska"),
    }
    must_not = {"Bydgoszczy", "Urząd Miasta", "Prezydent", "Wydział"}
    fails = 0
    for e in sorted(expected):
        ok = e in found
        fails += not ok
        print(("OK  " if ok else "BRAK") + f" {e[0]:<10} {e[1]}")
    for s in spans:
        if any(m in s["text"] for m in must_not):
            fails += 1
            print("FAŁSZYWY ALARM:", s["type"], s["text"])
    rb = [s for s in spans if "Bruski" in s["text"]]
    if not rb or rb[0]["status"] != "review":
        fails += 1
        print("BŁĄD: funkcjonariusz publiczny powinien mieć status review")
    else:
        print("OK   Rafał Bruski → review (art. 5 ust. 2)")
    assert pesel_ok("44051401359") and not pesel_ok("44051401358")
    assert nip_ok("5261040828") and not nip_ok("5261040829")
    assert idcard_ok("ABA300000") and not idcard_ok("ABA300001")
    assert iban_ok("PL61109010140000071219812874")
    assert regon_ok("123456785") and not regon_ok("123456786")
    red = apply(sample, spans, accept_all=True)
    leaks = [x for x in ["44051401359", "anna.kw@example.com", "Długa 15/4", "601 234 567"] if x in red]
    fails += bool(leaks)
    print("Wycieki po redakcji:", leaks or "brak")
    print(f"Spanów: {len(spans)}; wynik: {'OK' if not fails else f'{fails} błędów'}")
    return 1 if fails else 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Anonimizacja UDIP")
    p.add_argument("--selftest", action="store_true")
    sub = p.add_subparsers(dest="cmd")
    d = sub.add_parser("detect")
    d.add_argument("input", type=Path)
    d.add_argument("--out", type=Path)
    d.add_argument("--keep", action="append", default=[], help="osoba pełniąca funkcję publiczną (status review)")
    d.add_argument("--keep-file", type=Path)
    d.add_argument("--html", type=Path)
    d.add_argument("--min-conf", type=float, default=0.5)
    d.add_argument("--provider", default="rules", help="rules (domyślnie) albo dostawca LLM z udip.llm (propozycje do decyzji)")
    ap = sub.add_parser("apply")
    ap.add_argument("input", type=Path)
    ap.add_argument("spans", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--mode", choices=["label", "block"], default="label")
    ap.add_argument("--accept-all", action="store_true", help="przyjmij wszystkie 'suggested' (tylko testy!)")
    ap.add_argument("--html", type=Path)
    a = p.parse_args(argv)
    if a.selftest:
        return _selftest()
    if a.cmd == "detect":
        text = a.input.read_text(encoding="utf-8")
        keep = a.keep + (_load_keep(a.keep_file) if a.keep_file else [])
        spans = [asdict(s) for s in detect(text, keep, a.min_conf, provider=a.provider)]
        js = json.dumps({"source": str(a.input), "spans": spans}, ensure_ascii=False, indent=2)
        (a.out.write_text(js, encoding="utf-8") if a.out else print(js))
        if a.html:
            a.html.write_text(preview_html(text, spans), encoding="utf-8")
        print(f"Wykryto {len(spans)} fragmentów: " + ", ".join(f"{t}×{sum(1 for s in spans if s['type']==t)}" for t in sorted({s['type'] for s in spans})), file=sys.stderr)
        return 0
    if a.cmd == "apply":
        text = a.input.read_text(encoding="utf-8")
        spans = json.loads(a.spans.read_text(encoding="utf-8"))["spans"]
        a.out.write_text(apply(text, spans, a.mode, a.accept_all), encoding="utf-8")
        if a.html:
            for s in spans:
                if a.accept_all and s["status"] == "suggested":
                    s["status"] = "accepted"
            a.html.write_text(preview_html(text, spans, "Po akceptacji"), encoding="utf-8")
        return 0
    p.print_help()
    return 2


def _load_keep(p: Path) -> list[str]:
    return [x.strip() for x in p.read_text(encoding="utf-8").splitlines() if x.strip() and not x.startswith("#")]


if __name__ == "__main__":
    sys.exit(main())
