# Jak uruchomić Asystenta UDIP

Aplikacja działa **w całości lokalnie, bez internetu i bez klucza API** (model językowy jest opcjonalny). Po uruchomieniu otwórz **http://127.0.0.1:8000** — przy pierwszym starcie automatycznie wczytują się 10 spraw startowych UMB z przesuniętymi datami demo.

## Opcja 1: Docker (najszybciej — zawiera Python 3.12 + Tesseract OCR `pol`)

```bash
git clone https://github.com/raniszewski-robert/inteligentny-asystent-urzednika
cd inteligentny-asystent-urzednika
docker compose up --build
```

Albo bez Compose:

```bash
docker build -t asystent-udip .
docker run --rm -p 8000:8000 -v udip_data:/data asystent-udip
```

Aplikacja jest dostępna pod adresem **http://127.0.0.1:8000** (baza SQLite zapisuje się w wolumenie `udip_data`).

## Opcja 2: Windows (Python 3.11+ i Git)

```powershell
git clone https://github.com/raniszewski-robert/inteligentny-asystent-urzednika
cd inteligentny-asystent-urzednika
powershell -ExecutionPolicy Bypass -File .\setup.ps1
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

## Opcja 3: Linux / macOS (Python 3.11+)

```bash
git clone https://github.com/raniszewski-robert/inteligentny-asystent-urzednika
cd inteligentny-asystent-urzednika
bash run.sh
```

## Co przetestować w 3 minuty (gotowe pliki w repozytorium)

1. **Biurko i kalendarz** (`/biurko`, `/kalendarz`): 10 spraw UMB z kolorami pilności (po terminie / dziś / jutro / do 3 dni), tablica etapów i tabela rejestru, import arkusza `demo_assets/01_rejestr_umb.xlsx` (wykrywa 6 niespójności).
2. **Nowy wniosek** (`/wniosek/nowy`): wgraj `data-partner/umb/probki/Wniosek - BKS.IV.1431.599.2026.docx` → wyciąga 2 pytania, proponuje Wydział Edukacji i Sportu (`WE`) i znajduje podobną sprawę `BKS.IV.1431.307.2025` z zeszłego roku.
3. **Sprawa 543.2026 → Projekt pisma** (`/kalendarz` → kliknij `BKS.IV.1431.543.2026`): wgraj `data-partner/umb/przypadek_543/WGK.txt` i `SCHRONISKO.txt` (rozpoznanie wydziałów) → kliknij **Generuj projekt** → układ `Ad 1…Ad 5` z kontrolą liczb (`839 psów`, `560 kotów`, `3.143.761,14 zł`) i przypisaniem zdania do `Ad 2`.
4. **Anonimizacja i bezpieczeństwo** (`/anonimizacja`): wgraj `demo_assets/02_wniosek_atak_bezpieczenstwa.docx` (dane fikcyjne) → wykrywa ukryty biały tekst 1 pt, podpis i prompt injection; szare propozycje UMB, ramka „do decyzji” dla funkcjonariusza publicznego; po zatwierdzeniu eksport DOCX z audytem XML (0 trafień, metadane usunięte).
5. **Archiwum i akty prawne** (`/archiwum`): wgraj `demo_assets/04_nowelizacja_udip_2026_demo.pdf` → wyszukaj „termin 14 dni”.

## Opcjonalnie: lokalny model Bielik (Ollama)

Aplikacja działa w pełni bez LLM (reguły). Jeśli na komputerze działa lokalnie Ollama (`http://localhost:11434`, np. `SpeakLeash/bielik-4.5b-v3.0-instruct:Q8_0`), aplikacja automatycznie korzysta z niego w tle — także z wnętrza Dockera przez `host.docker.internal:11434`.

## Testy

```bash
bash scripts/smoke.sh
```

Rozwiązywanie problemów na Windows: `docs/INSTALL_WINDOWS.md`.
