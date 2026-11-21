#!/usr/bin/env python3
"""CLI: PDF/DOCX/ODT/TXT → tekst (+ OCR dla skanów). Logika: udip/ingest.py.

  python3 ingest.py plik.pdf [--out plik.txt]          # jeden plik
  python3 ingest.py --archive katalog/ --out archiwum.jsonl   # import archiwum odpowiedzi
  python3 ingest.py --selftest
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from udip.ingest import *  # noqa: E402,F401,F403  (import tego pliku daje to samo co udip.ingest)
from udip.ingest import IngestError, import_archive, read_any  # noqa: E402


def _selftest() -> int:
    import docx
    from reportlab.lib.pagesizes import A4  # tylko do wygenerowania próbki PDF w teście (BSD)
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas
    fails = 0
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        txt = "Bydgoszcz, 3 listopada 2026 r.\nWniosek o udostępnienie informacji publicznej: wydatki na oświetlenie ulic w Fordonie."
        dx = docx.Document()
        for line in txt.split("\n"):
            dx.add_paragraph(line)
        dx.save(td / "a_wniosek.docx")
        font = next((p for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/dejavu/DejaVuSans.ttf"] if Path(p).exists()), None)
        c = canvas.Canvas(str(td / "a_odpowiedz.pdf"), pagesize=A4)
        if font:
            pdfmetrics.registerFont(TTFont("DV", font))
            c.setFont("DV", 11)
        c.drawString(72, 760, "Odpowiedź: wydatki na oświetlenie w 2025 r. wyniosły 1 234 567 zł.")
        c.drawString(72, 740, "Wydział Gospodarki Komunalnej, Urząd Miasta Bydgoszczy, ul. Jezuicka 1.")
        c.save()
        (td / "b.txt").write_bytes("Prośba o kopię umowy na zieleń miejską – Śródmieście.".encode("cp1250"))
        for f, must in [("a_wniosek.docx", "oświetlenie"), ("a_odpowiedz.pdf", "1 234 567"), ("b.txt", "Śródmieście")]:
            d = read_any(td / f)
            ok = must in d["text"]
            fails += not ok
            print(f"{'OK ' if ok else 'BŁĄD'} {f}: {d['chars']} znaków, meta={ {k: v for k, v in d.items() if k not in ('text', 'file', 'sha256', 'chars')} }")
        n = import_archive(td, td / "arch.jsonl")
        rec = [json.loads(x) for x in (td / "arch.jsonl").read_text(encoding="utf-8").splitlines()]
        a = next(r for r in rec if r["id"] == "a")
        ok = n == 2 and "response_text" in a and a["date"] == "2026-11-03"
        fails += not ok
        print(f"{'OK ' if ok else 'BŁĄD'} archiwum: {n} sprawy, para wniosek+odpowiedź połączona, data {a.get('date')}")
        # OCR: PDF z obrazem tekstu (render strony → obraz → nowy PDF bez warstwy tekstu)
        from udip.ingest import ocr_unavailable
        why = ocr_unavailable()
        if why is None:
            import pypdfium2 as pdfium
            img = pdfium.PdfDocument(str(td / "a_odpowiedz.pdf"))[0].render(scale=3).to_pil().convert("RGB")
            img.save(td / "skan.pdf")
            d = read_any(td / "skan.pdf")
            ok = d["ocr"] and "oświetlenie" in d["text"]
            fails += not ok
            print(f"{'OK ' if ok else 'BŁĄD'} skan.pdf przez OCR: {d['text'][:70]!r}")
        else:
            print(f"POMINIĘTO test OCR: {why}")
        try:
            read_any(td / "b.doc") if (td / "b.doc").write_text("x") else None
        except IngestError as e:
            print("OK  .doc → czytelny komunikat:", e)
    print("Wynik:", "OK" if not fails else f"{fails} błędów")
    return 1 if fails else 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="PDF/DOCX/ODT/TXT → tekst")
    p.add_argument("input", nargs="?", type=Path)
    p.add_argument("--out", type=Path)
    p.add_argument("--ocr", choices=["auto", "always", "never"], default="auto")
    p.add_argument("--archive", type=Path, help="katalog archiwum spraw → JSONL")
    p.add_argument("--json", action="store_true", help="wypisz JSON z metadanymi")
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args(argv)
    if a.selftest:
        return _selftest()
    if a.archive:
        import_archive(a.archive, a.out or Path("archiwum.jsonl"))
        return 0
    if not a.input:
        p.error("podaj plik")
    try:
        d = read_any(a.input, a.ocr)
    except IngestError as e:
        print("BŁĄD:", e, file=sys.stderr)
        return 1
    if d.get("warning"):
        print("UWAGA:", d["warning"], file=sys.stderr)
    out = json.dumps(d, ensure_ascii=False, indent=2) if a.json else d["text"]
    (a.out.write_text(out, encoding="utf-8") if a.out else print(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
