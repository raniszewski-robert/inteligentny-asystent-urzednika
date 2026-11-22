![Asystent UDIP – baner](docs/screens/banner.png)

# Asystent UDIP: kalendarz wniosków, projekty pism i anonimizacja dla Urzędu Miasta Bydgoszczy

Aplikacja dla urzędników Biura Komunikacji Społecznej (BKS) UMB, którzy prowadzą wnioski o udostępnienie informacji publicznej. Prowadzi wniosek przez proces z Zarządzenia UMB: wgranie pliku → podobne sprawy i wydział → kalendarz z terminami → odpowiedzi wydziałów → projekt pisma „Ad 1…Ad N” w stylu BKS → anonimizacja z decyzją urzędnika → DOCX do wysyłki i do archiwum. Działa w całości lokalnie, bez internetu. Model językowy jest opcją (lokalny Bielik), a jego wyniki zawsze sprawdzają reguły.

Opis techniczny, wyniki i ograniczenia: [docs/opis_techniczny.md](docs/opis_techniczny.md).

![Kalendarz wniosków](docs/screens/kalendarz.png)

## Dla kogo

- **Pracownik BKS:** rejestr i terminy, pakiety pytań dla wydziałów, projekt pisma, anonimizacja, archiwum.
- **Wydziały merytoryczne:** jasny podział pytań, formularz odpowiedzi, mniej pracy z anonimizacją.
- **Kierownik BKS:** zaległości i terminy na jednym ekranie, historia statusów.

Ten sam proces mają inne jednostki samorządu: zmienia się lista komórek (`udip/data/departments.json`) i szablony pism (`udip/data/letter_types.json`).

## Uruchomienie

**Windows** (wymagany Python 3.11+ i Git; Tesseract tylko do skanów; szczegóły: [docs/INSTALL_WINDOWS.md](docs/INSTALL_WINDOWS.md)):

```powershell
git clone https://github.com/hacknation-2026-solutions/inteligentny-asystent-urzednika
cd inteligentny-asystent-urzednika
powershell -ExecutionPolicy Bypass -File .\setup.ps1
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

**Linux / macOS:** `bash run.sh` (tworzy `.venv`, wczytuje dane UMB, otwiera http://127.0.0.1:8000).

Przy pierwszym starcie aplikacja wczytuje 10 spraw z arkusza UMB z datami przesuniętymi wokół dnia instalacji (tryb demo), żeby kalendarz pokazał wszystkie poziomy pilności. Testy: `bash scripts/smoke.sh` (256 testów, ścieżka end-to-end, testy akceptacyjne 11/11).

## Szybki przegląd

1. **Kalendarz** (`/kalendarz`): sprawy od najstarszej, kolory pilności, statusy a–e, import arkusza XLSX z raportem niespójności.
2. **Nowy wniosek** (`/wniosek/nowy`): wgraj `data-partner/umb/probki/Wniosek - BKS.IV.1431.599.2026.docx` → 2 pytania, podobna sprawa 307.2025, Wydział Edukacji i Sportu.
3. **Sprawa 543.2026**: pakiety dla wydziałów, potem odpowiedzi z `data-partner/umb/przypadek_543/`.
4. **Projekt pisma**: „Ad 1…Ad 5” z kontrolą liczb („839 psom”, „3.143.761,14 zł”); zdania niepewne czekają na przypisanie.
5. **Anonimizacja**: dowolny plik, np. `demo_assets/02_wniosek_atak_bezpieczenstwa.docx` (ukryty tekst, wstrzyknięte polecenie, PESEL, IBAN, nazwisko ukraińskie). Eksport dopiero po decyzji o każdym fragmencie.
6. **Archiwum**: wysłane pismo w wersji zanonimizowanej trafia do wyszukiwania; panel „Pamięć instytucjonalna” pokazuje, czego aplikacja nauczyła się z poprawek.

Pliki przykładowe i opis pułapek: [demo_assets/README.md](demo_assets/README.md).

## Najważniejsze cechy

- **Proces UMB:** kroki z Zarządzenia UMB, statusy a–e, znak BKS.IV.1431, styl pism „Ad 1…Ad N”, lista danych do anonimizacji UMB, import obecnego arkusza kalendarium.
- **Cała ścieżka w jednej aplikacji:** od wgrania pliku do archiwum, z testem end-to-end; instalacja jednym poleceniem.
- **Bezpieczeństwo i anonimizacja:** czułość 100%, precyzja 99%, 0 wycieków na danych testowych; skaner ukrytego tekstu i wstrzykniętych poleceń; eksport zablokowany bez decyzji urzędnika, kontrola XML i metadanych DOCX; praca offline, dane nie opuszczają urzędu.
- **Łatwość obsługi:** ekrany w języku urzędu, kolory pilności, jeden przycisk na krok, „szary → czarny” jak na papierze.

Porównanie reguł i lokalnego modelu Bielik 4.5B na danych UMB (offline, bez kosztów): [docs/eval/RESULTS.md](docs/eval/RESULTS.md).

## Dane

Próbki w `data-partner/umb/` pochodzą z Urzędu Miasta Bydgoszczy. Dane osobowe w plikach przykładowych (`demo_assets/`, `data-samples/`) są fikcyjne.

## Licencja

Zależności i dane tylko na licencjach MIT, BSD, Apache-2.0 i 0BSD; fonty IBM Plex Sans i Source Serif 4 na SIL OFL 1.1, dołączone, żeby działały bez internetu: [LICENSES-THIRD-PARTY.md](LICENSES-THIRD-PARTY.md). Celowo bez PyMuPDF (AGPL), docxtpl (LGPL) i modeli spaCy pl (GPL).
