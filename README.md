![Asystent UDIP – baner](docs/screens/banner.png)

# Asystent UDIP: kalendarz wniosków, projekty pism i anonimizacja dla Urzędu Miasta Bydgoszczy

Aplikacja dla urzędników Biura Komunikacji Społecznej (BKS) UMB, którzy prowadzą wnioski o udostępnienie informacji publicznej. Prowadzi wniosek przez proces z Zarządzenia UMB: wgranie pliku → podobne sprawy i wydział → kalendarz z terminami → odpowiedzi wydziałów → projekt pisma „Ad 1…Ad N” w stylu BKS → anonimizacja z decyzją urzędnika → DOCX do wysyłki i do archiwum. Działa w całości lokalnie, bez internetu. Model językowy jest opcją (lokalny Bielik), a jego wyniki zawsze sprawdzają reguły.

- **Instrukcja uruchomienia dla Jurorów:** [JAK_URUCHOMIC.md](JAK_URUCHOMIC.md)
- **Prezentacja (10 slajdów):** [docs/deck/deck.pdf](docs/deck/deck.pdf) · [docs/deck/deck.pptx](docs/deck/deck.pptx)
- **Opis techniczny, wyniki i ograniczenia:** [docs/opis_techniczny.md](docs/opis_techniczny.md) · [docs/eval/RESULTS.md](docs/eval/RESULTS.md)

## Jak to działa w skrócie

![Asystent UDIP – proces od wniosku do gotowego pisma](docs/screens/idea_800x600.png)

## Ekrany aplikacji

| Kalendarz wniosków (`/kalendarz`) | Wniosek `599.2026` → wydział WE i archiwum (`/wniosek/nowy`) |
|---|---|
| ![Kalendarz wniosków](docs/screens/kalendarz.png) | ![Analiza wniosku 599.2026](docs/screens/wniosek_nowy_599.png) |
| **Projekt pisma „Ad 1…Ad 5” (`543.2026`)** | **Anonimizacja, skaner bezpieczeństwa i audyt XML** |
| ![Projekt pisma 543.2026](docs/screens/projekt_543.png) | ![Anonimizacja i kontrola danych](docs/screens/anonimizacja_dane_osobowe.png) |

## Dla kogo

- **Pracownik BKS:** rejestr i terminy, pakiety pytań dla wydziałów, projekt pisma, anonimizacja, archiwum.
- **Wydziały merytoryczne:** jasny podział pytań, formularz odpowiedzi, mniej pracy z anonimizacją.
- **Kierownik BKS:** zaległości i terminy na jednym ekranie, historia statusów.

Ten sam proces mają inne jednostki samorządu: zmienia się lista komórek (`udip/data/departments.json`) i szablony pism (`udip/data/letter_types.json`).

## Uruchomienie

Aplikacja działa **lokalnie bez internetu i bez klucza API** (otwiera **http://127.0.0.1:8000**). Szczegółowa instrukcja krok po kroku: [JAK_URUCHOMIC.md](JAK_URUCHOMIC.md).

**Docker (najprościej – Python 3.12 + Tesseract OCR `pol` w obrazie):**

```bash
git clone https://github.com/raniszewski-robert/inteligentny-asystent-urzednika
cd inteligentny-asystent-urzednika
docker compose up --build
```

**Windows** (wymagany Python 3.11+ i Git; Tesseract tylko do skanów; szczegóły: [docs/INSTALL_WINDOWS.md](docs/INSTALL_WINDOWS.md)):

```powershell
git clone https://github.com/raniszewski-robert/inteligentny-asystent-urzednika
cd inteligentny-asystent-urzednika
powershell -ExecutionPolicy Bypass -File .\setup.ps1
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

**Linux / macOS:** `bash run.sh` (tworzy `.venv`, wczytuje dane UMB, otwiera http://127.0.0.1:8000).

Przy pierwszym starcie aplikacja wczytuje 10 spraw z arkusza UMB z datami przesuniętymi wokół dnia instalacji (tryb demo), żeby kalendarz pokazał wszystkie poziomy pilności. Testy: `bash scripts/smoke.sh` (281 testów jednostkowych i integracyjnych, pełna ścieżka end-to-end).

## Szybki przegląd (3 minuty)

1. **Biurko i Kalendarz** (`/biurko`, `/kalendarz`): sprawy od najstarszej, tablica etapów `a–e` i tabela rejestru, kolory pilności, import arkusza XLSX z raportem niespójności.
2. **Nowy wniosek** (`/wniosek/nowy`): wgraj `data-partner/umb/probki/Wniosek - BKS.IV.1431.599.2026.docx` → 2 pytania, podobna sprawa `307.2025` (`starsza niż rok`), Wydział Edukacji i Sportu (`WE`).
3. **Sprawa `543.2026`**: pakiety dla wydziałów, potem odpowiedzi z `data-partner/umb/przypadek_543/`.
4. **Projekt pisma**: „Ad 1…Ad 5” z kontrolą liczb (`839 psom`, `560 kotom`, `3.143.761,14 zł`); zdania niepewne czekają na przypisanie jednym kliknięciem.
5. **Anonimizacja** (`/anonimizacja`): wgraj `demo_assets/02_wniosek_atak_bezpieczenstwa.docx` (ukryty tekst `1 pt`, podpis, wstrzyknięte polecenie, PESEL, IBAN, nazwisko ukraińskie). Funkcjonariusz publiczny (`Rafał Bruski`) trafia do decyzji (art. 5 ust. 2 UDIP); eksport dopiero po decyzji o każdym fragmencie, z audytem XML (`0 trafień`).
6. **Archiwum** (`/archiwum`): wysłane pismo w wersji zanonimizowanej trafia do wyszukiwania BM25; panel „Pamięć instytucjonalna” pokazuje, czego aplikacja nauczyła się z poprawek.

Pliki przykładowe i opis pułapek: [demo_assets/README.md](demo_assets/README.md).

## Najważniejsze cechy i wyniki

- **Proces UMB:** kroki z Zarządzenia UMB, statusy `a–e`, znak `BKS.IV.1431`, styl pism „Ad 1…Ad N”, lista 28 kategorii danych UMB, import obecnego arkusza kalendarium.
- **Cała ścieżka w jednej aplikacji:** od wgrania pliku do archiwum, z testem end-to-end; uruchomienie jednym poleceniem (Docker lub skrypt).
- **Bezpieczeństwo i anonimizacja:** czułość 100%, precyzja 99%, 0 wycieków na danych testowych; skaner ukrytego tekstu i wstrzykniętych poleceń; eksport zablokowany bez decyzji urzędnika, kontrola XML i metadanych DOCX; praca offline (`UDIP_OFFLINE=1`), dane nie opuszczają urzędu.
- **Lokalny model językowy:** opcjonalny **Bielik-11B-v3.1-Instruct** (`Apache-2.0`, Ollama/vLLM na serwerze Miasta) oraz zmierzony na laptopie **Bielik-4.5B-v3.0-Instruct** (`Q8_0`, offline, `$0.00`): [docs/eval/RESULTS.md](docs/eval/RESULTS.md).

## Dane

Próbki w `data-partner/umb/` pochodzą z Urzędu Miasta Bydgoszczy. Dane osobowe w plikach przykładowych (`demo_assets/`, `data-samples/`) są fikcyjne.

## Licencja

Zależności i dane wyłącznie na licencjach MIT, BSD, Apache-2.0 i 0BSD; fonty IBM Plex Sans, Source Serif 4 i Caveat na SIL OFL 1.1, dołączone lokalnie, żeby działały bez internetu: [LICENSES-THIRD-PARTY.md](LICENSES-THIRD-PARTY.md). Celowo bez PyMuPDF (AGPL), docxtpl (LGPL) i modeli spaCy pl (GPL).
