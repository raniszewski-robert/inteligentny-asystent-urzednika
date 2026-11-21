# data-partner/umb – materiały Urzędu Miasta Bydgoszczy

**Pochodzenie:** folder „Hacknation 2026 - UMB” przekazany uczestnikom przez mentorów UMB 21.11.2026 (kod QR z treści zadania, sekcja 6). Pisma odpowiedzi są przez UMB zanonimizowane („.anonymised.pdf”); dane wnioskodawców w próbkach są fikcyjne („Jerzy Dociekliwy”, „Stowarzyszenie Obrony Zwierzątek”).

**Licencja: brak.** Materiały konkursowe UMB. **Przed upublicznieniem repozytorium zapytaj mentora UMB**, czy mogą być publiczne; w razie wątpliwości usuń ten katalog z publicznej kopii (kod działa na `data-samples/`).

| Plik | Zawartość | Jak powstał |
|---|---|---|
| `kalendarium_umb.xlsx` | arkusz UMB „WNIOSKI O UDOSTĘPNIANIE INFORMACJI PUBLICZNEJ” (10 spraw), bez zmian | kopia |
| `archiwum_umb.jsonl` | 10 spraw: tekst wniosku, tekst pism BKS, wydziały, typ rozstrzygnięcia | `build_archive.py` z tekstów wyciągniętych `ingest.py` (pdfplumber + OCR); rękopis 16.2026 przepisany ręcznie z obrazu; 2 uzupełnienia w `MANUAL` |
| `rejestr_umb.json`, `niespojnosci_arkusza.md` | import arkusza do rejestru i raport 6 niespójności | `import_xlsx.py` |
| `przypadek_543/` | `wniosek.txt` (UMB) + `SCHRONISKO.txt`, `WGK.txt` – **odpowiedzi wydziałów odtworzone przez nas z treści pisma BKS 543.2026** (UMB nie dał plików wydziałów); nazwisko i telefon „Sprawę prowadzi” fikcyjne | ręcznie |
| `probki/` | 3 oryginalne pliki wniosków (2 DOCX, 1 PDF; 0,3 MB) do testów wgrywania | kopia |
| `build_archive.py` | skrypt odtwarzający archiwum | nasz (MIT) |

Poza repozytorium (u zespołu): pełny folder UMB (ok. 40 MB, skany 11–14 MB): 10 wniosków, 10 pism BKS, Zarządzenie Prezydenta 2024 o UDIP, plik „Dane podlegające anonimizacji.txt” (jego treść przenieśliśmy do kategorii w `udip-anonimizacja/data/`), linki do ustaw i BIP.
