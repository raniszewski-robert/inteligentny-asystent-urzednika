---
name: hn-zgloszenie
description: 'Prowadzi zgłoszenie HackNation od projektu w HackTribe (wybór zadania do soboty 20:00) do wysłania w niedzielę przed 11:00. Daje README dla jurora z kilkoma minutami, scenariusz wideo do 2 minut, ujawnienie materiałów i narzędzi AI, kontrolę sekretów, licencji copyleft, linków i widoczności repozytorium oraz plan zamrożenia. Użyj, gdy zespół mówi „zgłoszenie”, „HackTribe”, „README”, „nagrajmy demo”, „wideo”, „czy możemy wysyłać”, „sprawdź repo przed wysłaniem” albo „zamrażamy kod”.'
---

# hn-zgloszenie

## Po co

W etapie 1 juror ma na projekt kilka minut i ocenia wyłącznie to, co jest w zgłoszeniu. Do finału przechodzi pięć zespołów z zadania; w 2025 r. przypadało średnio około 27 zgłoszeń na zadanie (437 rozwiązań na 16 zadań). Zgłoszenie z niedziałającym linkiem, prywatnym repozytorium albo demo wymagającym klucza API przegrywa, zanim ktoś obejrzy kod. Ten skill prowadzi przez dwa terminy i automatycznie sprawdza to, co najczęściej się psuje.

Zasady i źródła: `.claude/hn-prep/_wspolne/research/01_zasady_hacknation_2026.md` (kopiuje je `install.sh`). Przebieg w HackTribe: `.claude/skills/hn-zgloszenie/references/hacktribe.md`. Polecenia niżej uruchamiaj z katalogu głównego repozytorium rozwiązania.

## Terminy, których nie da się przesunąć

| Kiedy | Co | Co się dzieje po terminie |
|---|---|---|
| **sob. 20:00** | Projekt w HackTribe założony, zadanie wybrane | Nie da się zmienić zadania ani założyć nowego projektu |
| **niedz. 11:00** | Zgłoszenie kompletne | Zmiany po czasie nie są uwzględniane |

Jeśli regulamin zadania wskazuje inną platformę zgłoszeń, obowiązuje regulamin zadania. Sprawdź to w sobotę.

## Kroki

### Sobota, do 13:00: projekt w HackTribe (15 min)

1. Załóż projekt z polami: nazwa projektu, nazwa zespołu, link do repozytorium, numer stolika, wstępny opis (2–3 zdania z `godzina-zero/decyzja_<slug>.md`, sekcja 1). Wybierz zadanie.
2. Utwórz **publiczne** repozytorium od razu, z `.gitignore` (`.env`, `data/`, `.venv/`, `node_modules/`; `install.sh --gitignore` je dopisze) i `README.md` z szablonu: `cp .claude/skills/hn-zgloszenie/assets/README-szablon.md README.md`. Pola `{{...}}` wypełniasz w trakcie; niewypełnione pole to dla `preflight.py` bloker.
3. Zapisz w README sekcję „Ujawnienie" już teraz: materiały przygotowane przed wydarzeniem (np. skrypty z tego pakietu) i narzędzia AI. Zespół ma wyjaśnić z organizatorem kwestię gotowego kodu i narzędzi AI **przed zgłoszeniem**; zapytaj na Discordzie `#zapytaj-organizatora` i zapisz odpowiedź.
4. O 19:30 jedna osoba sprawdza w HackTribe, że projekt istnieje i ma właściwe zadanie.

### Sobota wieczór: pierwsza kontrola (10 min)

```bash
source .venv/bin/activate      # albo inne środowisko projektu: licencje są czytane z zainstalowanych paczek
python3 .claude/skills/hn-zgloszenie/scripts/preflight.py . --decision godzina-zero/decyzja_<slug>.md --history
```

Skrypt sprawdza README (siedem elementów dla jurora i kryteria z pliku decyzji), sekrety w plikach i historii gita, licencje zależności Python i npm (także przechodnich), stan gita i widoczność repozytorium. Zapisuje `LICENSES-THIRD-PARTY.md`. Blokery napraw od razu. Klucz znaleziony w historii gita to uwaga, nie bloker: jeśli jest prawdziwy, **unieważnij go u dostawcy** (usunięcie pliku nie wystarczy), a potem uwaga może zostać.

### Niedziela: plan zamrożenia

| Godzina | Co | Kto |
|---|---|---|
| 07:00 | Koniec nowych funkcji. Liczby z ewaluacji wpisane do README | wszyscy |
| 08:00 | Nagranie wideo według `assets/wideo-scenariusz.md` (dwa podejścia, wybierz lepsze) | osoba od demo |
| 09:00 | README skończone: tabela kryteriów, wyniki, uruchomienie, ujawnienie | osoba od README |
| 09:00 | Prezentacja PDF (wymagana w zgłoszeniu): 4–6 slajdów według `.claude/skills/hn-pitch-final/assets/pitch-3min.md` (problem, rozwiązanie, zrzuty demo, liczby, wdrożenie); link albo plik w README | mówca |
| **09:30** | **Zamrożenie kodu.** Od teraz tylko poprawki błędów blokujących demo, każda przez jedną osobę. README, wideo, prezentację i linki można poprawiać do 10:30 | wszyscy |
| 09:45 | `video_check.sh`, wgranie wideo, link w README | osoba od demo |
| 10:00 | `preflight.py . --check-links --history`: zero blokerów | osoba od README |
| 10:15 | Test z obcego komputera albo telefonu, w oknie incognito: repozytorium, wideo, działająca wersja, instrukcja uruchomienia | ktoś spoza pisania README |
| **10:30** | **Zgłoszenie w HackTribe kompletne**, zapisane, sprawdzone z innego urządzenia | lider |
| 10:30–11:00 | Zapas na awarie. Nie zmieniaj kodu | |

Godziny to rekomendacja tego pakietu. 30 minut zapasu bierze się stąd, że platformy zgłoszeń przed terminem bywają przeciążone.

### Wideo do 2 minut

Scenariusz i technika: `assets/wideo-scenariusz.md`. Zasada: pierwsze 10 sekund mówi, dla kogo to jest i jaki problem rozwiązuje, potem pokazujesz działanie na jednym realnym przypadku, a na końcu liczbę z ewaluacji. Sprawdzenie i konwersja:

```bash
bash .claude/skills/hn-zgloszenie/scripts/video_check.sh nagranie.mov --fix demo.mp4
```

Wynik: H.264 i AAC, najwyżej 1920 px szerokości, przycięte do 1:58. Wgraj jako film niepubliczny (dostępny dla każdego z linkiem) i sprawdź link w oknie incognito.

### README dla jurora

Szablon: `assets/README-szablon.md`. Kolejność odpowiada temu, co juror sprawdza w pierwszych minutach: co to jest i dla kogo (2 zdania), link do wideo, tabela „kryterium → co zrobiliśmy → gdzie to zobaczyć", wyniki z punktem odniesienia, uruchomienie jedną komendą **bez klucza API** (tryb `replay` z `hn-llm-w-produkcie`), ujawnienie, licencja. Pozostałe szczegóły przenieś do `docs/`. Najwyżej około 1500 słów.

## Przykład

Wejście: „Jest 9:50, sprawdź, czy możemy wysyłać."

Wyjście (skrót):

```
preflight: 2 blokery, 3 uwagi.
BLOKER [git] 3 commity niewypchnięte → git push.
BLOKER [git] widoczność repozytorium: PRIVATE → Settings → Change visibility → Public, potem incognito.
UWAGA [licencje] certifi MPL-2.0 (słaby copyleft): zwykle w porządku, jest w LICENSES-THIRD-PARTY.md.
UWAGA [README] kryteria 3/4: brak „Skalowalność 15%" → dodaj wiersz z odpowiedzią z sekcji „Wdrożenie".
Po poprawkach: 0 blokerów. Następny krok: test z telefonu w incognito, 10:15.
```

## Kiedy nie używać

- Wybór zadania i plan: `hn-godzina-zero`.
- Liczby z ewaluacji: `hn-dane-od-partnera` (one trafiają do README, tutaj tylko je wstawiasz).
- Pitch w finale: `hn-pitch-final`.

## Pułapki

Pełna lista awarii z poprawkami: `references/awarie.md`. Najczęstsze:

- **Prywatne repozytorium albo wideo.** Juror zobaczy 404 albo „film niedostępny". `preflight.py` sprawdzi widoczność repozytorium (przez `gh`), ale nie wideo: serwisy wideo często zwracają stronę także dla filmu prywatnego. Sprawdzaj w oknie incognito z innego urządzenia.
- **Demo wymaga klucza API, GPU albo danych Partnera.** Juror tego nie uruchomi. Tryb `replay`, małe dane przykładowe w repozytorium, wersja działająca pod linkiem.
- **Klucz w historii gita.** Repozytorium jest publiczne; boty skanują GitHub w minutach. Unieważnij klucz.
- **Licencja copyleft albo niekomercyjna** w zależności, gdy Partner przejmuje prawa. Sprawdź regulamin zadania i `LICENSES-THIRD-PARTY.md`.
- **Edycja kodu o 10:55.** Ostatni commit może nie dojść albo zepsuć demo. Zamrożenie o 9:30.
- **README bez liczb i bez kryteriów.** Juror nie znajdzie dowodu i nie da punktów.

## Pliki

- `scripts/preflight.py`: kontrola README, sekretów (także w historii), licencji Python i npm, gita i widoczności, linków; biblioteka standardowa, git, opcjonalnie gh.
- `scripts/video_check.sh`: długość, kodek, rozdzielczość, dźwięk; konwersja do H.264 z cięciem; wymaga ffmpeg.
- `scripts/selftest.py`: test `preflight.py` na dwóch tymczasowych repozytoriach.
- `assets/README-szablon.md`: README dla jurora.
- `assets/wideo-scenariusz.md`: scenariusz wideo do 2 minut z techniką nagrania.
- `references/hacktribe.md`: przebieg w HackTribe i co wiadomo o platformie.
- `references/awarie.md`: typowe awarie i poprawki.
- `references/test-run.md`: zapis uruchomień testowych.
