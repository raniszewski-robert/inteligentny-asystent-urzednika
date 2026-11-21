# Zapis uruchomień testowych: hn-godzina-zero

Data: 2026-11-17, Python 3.13.18, Linux. Pakiety zadań `prep/<slug>/` jeszcze nie istniały, więc test użył atrapy pakietu w katalogu tymczasowym (`prep/atrapa_zadania/` z README z sekcją „Karta zadania", `research/06_warianty_i_rekomendacja.md`, jednym skillem i jedną próbką danych).

## new_decision.py

| Przypadek | Polecenie | Wynik |
|---|---|---|
| Jedno zadanie z pakietem | `--slug atrapa_zadania --nazwa "ATRAPA ZADANIA" --now 2026-11-21T11:20` | Zapisano `godzina-zero/decyzja_atrapa_zadania.md`; nagłówek pokazuje „8 h 40 min" do 20:00 i „23 h 40 min" do zgłoszenia; blok „Z pakietu" zawiera Kartę zadania, warianty A i B, rekomendację, skill i liczbę próbek |
| Porównanie: zadanie z pakietem i bez | `--slug atrapa_zadania --slug nowe_zadanie` | Istniejący plik pominięty (bez `--force`), zapisano `decyzja_nowe_zadanie.md` z blokiem „BRAK PAKIETU" i `porownanie.md` z kolumnami obu zadań |
| Brak katalogu `prep/` | `--slug cos --now 2026-11-22T12:00` w pustym katalogu | Ostrzeżenie, plik w trybie bez pakietu, czas: „termin minal" |
| Cztery slugi | `--slug a --slug b --slug c --slug d` | Błąd z komunikatem o limicie, kod wyjścia 2 |

Fragment wyjścia:

```
ZAPISANO   godzina-zero/decyzja_atrapa_zadania.md
Czas: do wyboru zadania 8 h 40 min, do zgloszenia 23 h 40 min.
```

## criteria_check.py

| Przypadek | Wynik |
|---|---|
| Świeży szablon (pusta tabela) | „tabela kryteriow jest pusta", kod 2 |
| Tabela z 4 kryteriami (40%, 30%, 20%, 10%), jedno bez funkcji, dowodu i osoby, jedno ze statusem „gotowe" | Suma 100%, 80% wagi z zaplanowanym dowodem, 30% z gotowym, trzy ostrzeżenia, kod 1 |
| Plik bez tabeli kryteriów | Komunikat o braku tabeli, kod 2 |

Fragment wyjścia:

```
Kryteriow: 4   suma wag: 100%
Waga z zaplanowanym dowodem: 80 (80%)
Waga z gotowym dowodem (Status = gotowe): 30 (30%)
      20  Innowacyjność            BRAK FUNKCJI BRAK DOWODU BRAK OSOBY
OSTRZEZENIA:
  - 1 kryteriow bez dowodu (20% wagi): juror nie da punktow za cos, czego nie zobaczy
```

## Błędy znalezione i poprawione w trakcie testu

- Polskie cudzysłowy w napisach Pythona kończyły napis znakiem `"` i powodowały błąd składni. Komunikaty skryptów są teraz w ASCII.
- Nagłówek „Warianty" był liczony jako wariant. Skrypt szuka teraz słowa „wariant" jako osobnego wyrazu.

## Czego nie testowano

Prawdziwych pakietów zadań. Jeśli pakiet nazwie sekcję inaczej niż „Karta zadania" albo plik inaczej niż `research/06*.md`, skrypt zgłosi brak w pakiecie i trzeba przeczytać pakiet ręcznie.

## Poprawki po przeglądzie świeżego subagenta (2026-11-17) i ponowne testy

| Problem z przeglądu | Poprawka | Test |
|---|---|---|
| Z repozytorium rozwiązania (obok repozytorium przygotowawczego) skrypt nie widział pakietu | `install.sh` kopiuje README i `research/` pakietów do `.claude/hn-prep/`; skrypt szuka kolejno: `HN_PREP`, `.claude/hn-prep/`, `prep/` tu i wyżej; wypisuje, gdzie znalazł | Repozytorium rozwiązania obok `setup/`: „Pakiety: …/rozwiazanie/.claude/hn-prep”, Karta zadania i skill `kw-demo-i-pitch` w pliku decyzji; z `setup/` dalej działa `prep/` |
| `--prep` nieistniejący przechodził po cichu | Błąd z komunikatem, kod 2 | `--prep /nie/ma` → kod 2 |
| Lista skilli po instalacji zawierała `hn-*` | Przy `.claude/hn-prep/` lista pomija `hn-*` | tylko `kw-demo-i-pitch` |
| `--now` z przesunięciem UTC był czytany jak czas warszawski | Przeliczenie do Europe/Warsaw | `2026-11-21T10:30:00+00:00` → „11:30”, 8 h 30 min do 20:00 |
| Wagi w punktach („0–10 pkt”) dawały 0 | Waga = największa liczba w komórce | „0–10 pkt” → 10, „max 20 pkt” → 20 |
| Statusy „jest w planie”, „okazjonalnie” liczone jako gotowe | Tylko całe słowa: gotowe, gotowy, zrobione, done, ok | Waga gotowa 10 z 35 (tylko „gotowe”) |
| Ścieżki względne w szablonie i SKILL.md | Pełne ścieżki `.claude/skills/hn-godzina-zero/...` i `.claude/hn-prep/...` | przegląd tekstu |
| Plan w szablonie: wideo „gotowe” o 9:30, a wgranie o 9:45 | 09:00 README, wideo, prezentacja w wersji roboczej; 09:30 zamrożenie kodu, materiały do 10:30 | przegląd tekstu |
| Limit dwóch zadań podany jako pewny | „według przewodnika; potwierdź na Discordzie” | przegląd tekstu |

Ponowne uruchomienie przypadków z pierwszej tabeli: wyniki bez zmian (plik decyzji, porównanie dwóch zadań, kod 2 przy pustej tabeli i przy czterech slugach).
