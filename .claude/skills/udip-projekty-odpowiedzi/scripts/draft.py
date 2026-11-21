#!/usr/bin/env python3
"""CLI: projekt odpowiedzi na wniosek UDIP z odpowiedzi wydziałów → TXT/DOCX z zaznaczoną anonimizacją. Logika: udip/draft.py.

  python3 draft.py --request wniosek.txt --answer odp1.txt [--answer odp2.txt] --number BKS.1431.12.2026 \\
      --received 2026-11-02 --type udostepnienie --out-dir wynik/ [--mode llm]
Wyniki: projekt.txt, projekt.docx (szare = propozycja anonimizacji), spans.json, podglad.html, raport.json.
Finalizacja po akceptacji: python3 draft.py --finalize wynik/ [--accept s1,s2 | --accept-all-suggested]
  → odpowiedz_do_wysylki.* (adresat jawny) i odpowiedz_zanonimizowana.* (archiwum/BIP).
--mode llm idzie przez udip.llm (dostawca: UDIP_PROVIDER w .env); bez dostępnego LLM zostaje szablon (raport: llm_error).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from udip.draft import *  # noqa: E402,F401,F403  (import tego pliku daje to samo co udip.draft)
from udip.draft import TEMPLATES, finalize, make_draft, preview_html, write_docx  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Projekt odpowiedzi UDIP")
    p.add_argument("--request", type=Path)
    p.add_argument("--answer", type=Path, action="append", default=[])
    p.add_argument("--number", default="BKS.IV.1431.___.2026")
    p.add_argument("--received")
    p.add_argument("--type", default="udostepnienie", choices=[k for k in TEMPLATES if not k.startswith("_")])
    p.add_argument("--mode", default="template", choices=["template", "llm"])
    p.add_argument("--sign", default="[podpis AIP]")
    p.add_argument("--today", default=date.today().isoformat())
    p.add_argument("--reason", default="")
    p.add_argument("--keep", action="append", default=[], help="osoba pełniąca funkcję publiczną → do decyzji")
    p.add_argument("--dept", action="append", default=[], help="id komórki z departments.json (domyślnie: z odpowiedzi)")
    p.add_argument("--scope", default="", help="zakres wniosku do formuły „w zakresie …” (domyślnie: z wniosku)")
    p.add_argument("--entity", default="", help="właściwy podmiot (odesłanie art. 4 ust. 3)")
    p.add_argument("--entity-contact", default="")
    p.add_argument("--bip-url", default="")
    p.add_argument("--until", help="nowy termin (RRRR-MM-DD) dla przedłużenia/doprecyzowania")
    p.add_argument("--out-dir", type=Path)
    p.add_argument("--finalize", type=Path, help="katalog z poprzedniego uruchomienia")
    p.add_argument("--edited", type=Path, help="przy --finalize: tekst pisma po poprawkach urzędnika")
    p.add_argument("--accept", default="", help="id spanów do zaczernienia, np. s1,s3")
    p.add_argument("--reject", default="", help="id spanów do pozostawienia jawnymi")
    p.add_argument("--accept-all-suggested", action="store_true")
    a = p.parse_args(argv)

    if a.finalize:
        d = a.finalize
        text = (d / "projekt.txt").read_text(encoding="utf-8")
        spans = json.loads((d / "spans.json").read_text(encoding="utf-8"))["spans"]
        edited = a.edited.read_text(encoding="utf-8") if a.edited else None
        r = finalize(text, spans, set(filter(None, a.accept.split(","))), set(filter(None, a.reject.split(","))),
                     a.accept_all_suggested, edited)
        for w in r["warnings"]:
            print(w, file=sys.stderr)
        (d / "spans.json").write_text(json.dumps({"spans": r["spans"]}, ensure_ascii=False, indent=2), encoding="utf-8")
        (d / "odpowiedz_zanonimizowana.txt").write_text(r["anonymized"], encoding="utf-8")
        write_docx(r["text"], r["spans"], d / "odpowiedz_zanonimizowana.docx", final=True)
        (d / "odpowiedz_do_wysylki.txt").write_text(r["to_send"], encoding="utf-8")
        write_docx(r["text"], r["body_spans"], d / "odpowiedz_do_wysylki.docx", final=True)
        (d / "podglad_final.html").write_text(preview_html(r["text"], r["spans"], "Po akceptacji urzędnika"), encoding="utf-8")
        print(f"Zapisano odpowiedz_zanonimizowana.* i odpowiedz_do_wysylki.*; zaczernione: {sum(s['status'] == 'accepted' for s in r['spans'])}")
        return 0

    if not (a.request and a.out_dir and a.received):
        p.error("wymagane: --request, --received, --out-dir (albo --finalize)")
    a.out_dir.mkdir(parents=True, exist_ok=True)
    res = make_draft(a.request.read_text(encoding="utf-8"), [(f.name, f.read_text(encoding="utf-8")) for f in a.answer],
                     date.fromisoformat(a.received), a.type, number=a.number, today=date.fromisoformat(a.today), mode=a.mode,
                     sign=a.sign, extension_until=date.fromisoformat(a.until) if a.until else None, reason=a.reason,
                     dept_ids=a.dept, scope=a.scope, entity=a.entity, entity_contact=a.entity_contact, bip_url=a.bip_url, keep=a.keep)
    (a.out_dir / "projekt.txt").write_text(res["text"], encoding="utf-8")
    (a.out_dir / "spans.json").write_text(json.dumps({"spans": res["spans"]}, ensure_ascii=False, indent=2), encoding="utf-8")
    (a.out_dir / "podglad.html").write_text(res["html"], encoding="utf-8")
    write_docx(res["text"], res["spans"], a.out_dir / "projekt.docx")
    (a.out_dir / "raport.json").write_text(json.dumps(res["report"], ensure_ascii=False, indent=2), encoding="utf-8")
    for w in res["report"]["warnings"]:
        print("UWAGA:", w, file=sys.stderr)
    print(json.dumps(res["report"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
