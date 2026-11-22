# Instalacja na Windows

Wszystko, co tworzy instalacja, zostaje w katalogu repozytorium (np. na D:): środowisko Pythona `.venv`, baza i pliki w `var`, pamięć podręczna pip w `var\pip-cache`, pliki tymczasowe w `var\tmp`. Na C: trafia tylko sam Python (i Git, jeśli go instalujesz).

## Wymagania

| Program | Sprawdzenie | Instalacja |
|---|---|---|
| Python 3.11 lub nowszy | `py -3.12 --version` albo `python --version` | `winget install -e --id Python.Python.3.12` |
| Git | `git --version` | `winget install -e --id Git.Git` |
| Tesseract OCR z językiem polskim (opcjonalnie, tylko skany PDF) | `tesseract --list-langs` | `winget install -e --id UB-Mannheim.TesseractOCR --location D:\Tools\Tesseract-OCR`, w instalatorze zaznacz język Polish |

Po instalacji Pythona albo Gita otwórz nowe okno PowerShell, żeby zobaczyć nowe polecenia.

## Pierwsze uruchomienie

```powershell
cd D:\
git clone <adres repozytorium> inteligentny-asystent-urzednika
cd inteligentny-asystent-urzednika
powershell -ExecutionPolicy Bypass -File .\setup.ps1
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

`setup.ps1` sprawdza Pythona i Gita, tworzy `.env`, instaluje paczki (raz, potrzebny internet) i wczytuje dane startowe UMB: 10 spraw z arkusza kalendarium i archiwum odpowiedzi. Sprawy z arkusza są już zamknięte, więc daty wpływu przesuwamy wokół dnia instalacji (tryb demo, sprawy oznaczone), żeby kalendarz pokazał wszystkie poziomy pilności. `run.ps1` uruchamia aplikację pod adresem http://127.0.0.1:8000 i otwiera przeglądarkę na ekranie Kalendarz. Od tej chwili internet nie jest potrzebny. Zatrzymanie: Ctrl+C w oknie PowerShell.

`-ExecutionPolicy Bypass` dotyczy tylko tego jednego polecenia i nie zmienia ustawień systemu.

## Plik .env

`setup.ps1` dopisuje do `.env` tylko brakujące klucze i niczego w nim nie nadpisuje. Klucz API (`ANTHROPIC_API_KEY=...`) wpisz ręcznie, jeśli chcesz użyć zewnętrznego modelu na danych testowych; aplikacja działa bez niego (`UDIP_PROVIDER=rules`).

| Klucz | Wartość po instalacji |
|---|---|
| `UDIP_ENV_FILE` | pełna ścieżka do tego pliku `.env` |
| `UDIP_VENV` | `<repo>\.venv` |
| `UDIP_DATA_DIR` | `<repo>\var` (baza, wgrane pliki, eksporty) |
| `LLM_BUDGET_USD` | `15` |
| `UDIP_PROVIDER` | `openai_compat:bielik` (reguły zawsze; Bielik dokłada swoje w tle, gdy Ollama działa; `rules` wyłącza model; `gemini` – pokaz w chmurze, wymaga `GEMINI_API_KEY`) |
| `TESSERACT_CMD` | `D:\Tools\Tesseract-OCR\tesseract.exe`, jeśli tam jest |

## Opcje

| Polecenie | Działanie |
|---|---|
| `.\run.ps1 -Port 8001` | inny port, gdy 8000 jest zajęty |
| `.\run.ps1 -NoBrowser` | bez otwierania przeglądarki |
| `.\run.ps1 -Reseed` albo `.\setup.ps1 -Reseed` | sprawy z arkusza UMB od nowa, z datami demo na dziś (kasuje historię statusów tych spraw) |
| `.\run.ps1 -Reseed -RealDates` | sprawy z prawdziwymi datami z arkusza (wszystkie są już zamknięte) |

## Gdy coś nie działa

| Komunikat | Co zrobić |
|---|---|
| „Nie znaleziono Pythona 3.11 lub nowszego” | zainstaluj Pythona (tabela wyżej), otwórz nowe okno, uruchom `setup.ps1` ponownie |
| „running scripts is disabled on this system” | uruchamiaj przez `powershell -ExecutionPolicy Bypass -File ...`, jak wyżej |
| „brak środowiska Pythona” | najpierw `setup.ps1` |
| „port 8000 jest zajęty” | aplikacja już działa w innym oknie albo użyj `-Port 8001` |
| „Środowisko ... nie działa” | usuń katalog `.venv` i uruchom `setup.ps1` ponownie |

## Linux i macOS

```bash
bash run.sh
```

Przy pierwszym starcie skrypt tworzy `.venv` i instaluje paczki, potem uruchamia aplikację na http://127.0.0.1:8000. Opcje: `--port 8001`, `--no-browser`, `--reseed`, `--real-dates`.
