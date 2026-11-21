---
name: udip-dane-i-zrodla
description: Wczytuje dokumenty urzędnika i Partnera – PDF (pdfplumber, OCR Tesseract pol dla skanów), DOCX, ODT, TXT w cp1250 – ocenia jakość tekstu (rękopis → „wpisz ręcznie”), importuje katalog wniosków i odpowiedzi do archiwum JSONL i odtwarza archiwum UMB z materiałów mentorów. Użyj, gdy zespół mówi „wgraj plik”, „wczytaj PDF/Word”, „OCR”, „skan”, „zaimportuj archiwum”, „mamy nowe próbki od UMB” albo „wgraj ustawę”.
---

# udip-dane-i-zrodla

Wymaganie nr 2 treści (wgrywanie PDF/Word) i test jury nr 6 (łatwość wgrywania danych). Źródła i ich status: `research/03`.

## Skrypty

| Skrypt | Co robi |
|---|---|
| `scripts/ingest.py plik [--json] [--ocr auto\|always\|never]` | tekst + metadane (`pages`, `ocr`, `quality`, `warning`); PDF: pdfplumber → pypdf; skan (>50% stron bez tekstu) → pypdfium2 + `tesseract -l pol`; `.doc` → czytelny komunikat |
| `scripts/ingest.py --archive katalog/ --out archiwum.jsonl` | pary `<id>_wniosek.*` + `<id>_odpowiedz.*` → JSONL; opcjonalny `meta.json` z wydziałami |
| `scripts/ingest.py --selftest` | DOCX, PDF, TXT cp1250, archiwum, OCR na zeskanowanym PDF |
| `../../../data-partner/umb/build_archive.py <katalog_json> <arkusz.xlsx>` | archiwum UMB: łączy wniosek, pisma BKS (odpowiedź, kwerenda, doprecyzowanie), wydziały z treści, typ rozstrzygnięcia |

## Zależności i zmienne

`pdfplumber` (MIT), `pypdf` (BSD-3), `python-docx` (MIT), `pypdfium2` (Apache-2.0/BSD-3), `openpyxl` (MIT), Tesseract ≥ 5 z `tesseract-ocr-pol` (Apache-2.0). Nie używamy PyMuPDF (AGPL) ani pdftoppm (Poppler, GPL). Zmienne środowiskowe: brak (wszystko lokalnie).

## Kroki: nowe próbki od UMB

1. `for f in katalog/*; do python3 scripts/ingest.py "$f" --json --out "txt/$(basename "${f%.*}").json"; done`
2. Sprawdź pliki z `"warning"` (rękopisy): przepisz treść ręcznie i dopisz do `MANUAL` w `build_archive.py`.
3. `python3 ../../../data-partner/umb/build_archive.py txt/ arkusz.xlsx` → `archiwum_umb.jsonl`.
4. `python3 ../udip-ewaluacja/scripts/evaluate_partner.py archiwum_umb.jsonl`.

## Przykład wejście → wyjście

Wejście: `Wniosek - BKS.IV.1431.16.2026.pdf` (rękopis drukowanymi literami na kratce, 14 MB).
Wyjście: `quality: 0.36`, `ocr: true`, `warning: "Niska jakość tekstu (prawdopodobnie rękopis lub słaby skan): wpisz treść wniosku ręcznie…"`. Dla pism BKS jakość wynosi 0,78–0,90 (próg 0,5).

## Kiedy nie używać

- Do pobierania ustaw z ISAP/ELI w trakcie demo: wymaga sieci. Ustawy wgrywa urzędnik jako PDF (to jest „uczenie się” z treści zadania).
- Do rękopisów: Tesseract ich nie czyta. Docelowo lokalny model obrazowy (do oceny), teraz ręczne wpisanie.

## Pułapki

- pypdf rozstrzela litery w PDF-ach UMB („Komunik acji”); dlatego pdfplumber z `x_tolerance=1.5` jest pierwszy.
- OCR skanu 2 stron trwa kilka–kilkanaście sekund na CPU; w UI pokaż postęp.
- Nazwy folderów UMB kończą się spacją („Dokumenty i podstawy prawne ”) – narzędzia kopiujące mogą je odrzucać; pakuj tarem.
- Materiały UMB nie mają licencji: przed upublicznieniem repozytorium zapytaj mentora (research/03).

Wyniki uruchomień: `references/test-run.md`.
