# Typowe awarie zgłoszenia i poprawki

| Awaria | Jak ją wykryć | Poprawka | Ile trwa |
|---|---|---|---|
| Repozytorium prywatne | `preflight.py` (widoczność przez `gh`), okno incognito | Settings → General → Change visibility → Public. Sprawdź, czy w historii nie ma sekretów **przed** upublicznieniem | 2 min |
| Wideo prywatne albo „tylko dla mnie" | link w incognito daje „film niedostępny" albo prośbę o logowanie | YouTube: Niepubliczny. Dysk: „każdy, kto ma link" | 2 min |
| Link w README prowadzi do localhost | `preflight.py` | Usuń albo zamień na działającą wersję; opisz uruchomienie lokalne w bloku kodu | 5 min |
| Demo wymaga klucza API | uruchom z `.env` skopiowanym z `.env.example` | `LLM_MODE=replay` z `.llm_cache/` w repozytorium (`hn-llm-w-produkcie`) | 15 min, jeśli scenariusz był przejrzany w trybie `cache` |
| Demo wymaga danych Partnera, których nie ma w repozytorium | świeży klon i uruchomienie | Mały plik przykładowy w `examples/` (bez danych osobowych, za zgodą Partnera) albo dane syntetyczne o tym samym schemacie | 20 min |
| Działająca wersja nie wstaje (darmowy hosting usypia, limit) | otwórz link z telefonu | Zaznacz w README, że pierwsze otwarcie trwa do minuty; wideo jest planem B | 5 min |
| Klucz API w repozytorium | `preflight.py --history` | Unieważnij klucz u dostawcy, wygeneruj nowy, usuń z plików. Przepisanie historii jest drugorzędne, bo klucz i tak mógł wyciec | 10 min |
| Zależność GPL/AGPL albo niekomercyjna, a Partner przejmuje prawa | `preflight.py`, `LICENSES-THIRD-PARTY.md` | Zamień na permisywną albo opisz w README i zapytaj Partnera | 15–60 min |
| `pip install` nie działa na czystym komputerze | świeży klon w nowym katalogu, nowe `venv` | `pip freeze > requirements.txt` z działającego środowiska; podaj wersję Pythona | 10 min |
| Plik większy niż 100 MB (model, dane) | `preflight.py`, `git push` odrzucony | Usuń z repozytorium, link do pobrania w README; skrypt `download_model.sh` | 15 min |
| Ostatni push nie doszedł | `git status`, GitHub w przeglądarce | `git push`; jeśli konflikt, nie rób rebase pod presją: wypchnij gałąź i wskaż ją w README | 5 min |
| Platforma zgłoszeń przeciążona przed 11:00 | strona się nie ładuje | Zgłoszenie było gotowe o 10:30 i zapisane. Jeśli nie było: zrzut ekranu z godziną, wiadomość na Discord `#zapytaj-organizatora`, Info Point | — |
| Wybrano złe zadanie w HackTribe | kontrola o 19:30 | Przed 20:00: popraw. Po 20:00: nie da się; od razu napisz do organizatorów | — |
| W zgłoszeniu brak ujawnienia materiałów sprzed wydarzenia i narzędzi AI | `preflight.py` (README) | Sekcja „Ujawnienie" z szablonu | 5 min |
