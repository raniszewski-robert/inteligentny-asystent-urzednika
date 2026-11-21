# data-partner/umb – materiały Urzędu Miasta Bydgoszczy

**Pochodzenie:** materiały przekazane przez Urząd Miasta Bydgoszczy 21.11.2026. Pisma odpowiedzi są przez UMB zanonimizowane („.anonymised.pdf”); dane wnioskodawców w próbkach są fikcyjne („Jerzy Dociekliwy”, „Stowarzyszenie Obrony Zwierzątek”).

**Licencja: brak.** Materiały UMB; publikacja wymaga zgody Urzędu. Aplikacja działa także bez tego katalogu (na `data-samples/`).

| Plik | Zawartość | Jak powstał |
|---|---|---|
| `kalendarium_umb.xlsx` | arkusz UMB „WNIOSKI O UDOSTĘPNIANIE INFORMACJI PUBLICZNEJ” (10 spraw), bez zmian | kopia |
| `archiwum_umb.jsonl` | 10 spraw: tekst wniosku, tekst pism BKS, wydziały, typ rozstrzygnięcia | `build_archive.py` z tekstów wyciągniętych `ingest.py` (pdfplumber + OCR); rękopis 16.2026 przepisany ręcznie z obrazu; 2 uzupełnienia w `MANUAL` |
| `rejestr_umb.json`, `niespojnosci_arkusza.md` | import arkusza do rejestru i raport 6 niespójności | `import_xlsx.py` |
| `przypadek_543/` | `wniosek.txt` (UMB) + `SCHRONISKO.txt`, `WGK.txt` – **odpowiedzi wydziałów odtworzone z treści pisma BKS 543.2026** (oryginalne pliki wydziałów nie są dołączone); nazwisko i telefon „Sprawę prowadzi” fikcyjne | ręcznie |
| `probki/` | 3 oryginalne pliki wniosków (2 DOCX, 1 PDF; 0,3 MB) do testów wgrywania | kopia |
| `build_archive.py` | skrypt odtwarzający archiwum | MIT |

Poza repozytorium: pełny folder UMB (ok. 40 MB, skany 11–14 MB): 10 wniosków, 10 pism BKS, Zarządzenie Prezydenta 2024 o UDIP, plik „Dane podlegające anonimizacji.txt” (jego treść jest odwzorowana w kategoriach w `udip-anonimizacja/data/`), linki do ustaw i BIP.
