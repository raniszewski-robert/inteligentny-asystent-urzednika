# Zapis uruchomień testowych: hn-zgloszenie

Data: 2026-11-17, Python 3.13.18, git 2.43.0, ffmpeg 6.1.1, Linux.

## preflight.py (przez `python3 scripts/selftest.py`)

**Wynik: 24 PASS, 0 FAIL** (po poprawkach z przeglądu; pierwszy przebieg: 22 testy).

Test buduje dwa tymczasowe repozytoria z lokalnym zdalnym repozytorium (`git init --bare`). Fałszywe klucze są składane w czasie testu, więc w plikach pakietu nie ma niczego, co wygląda na klucz.

**Repozytorium źle przygotowane:** README z TODO i samym localhost; `.env` z kluczem w repozytorium; token GitHub i hasło w adresie bazy w `config.py`, usunięte w drugim commicie (zostają w historii); `requirements.txt` z `python-apt` (GPL) i `img2pdf` (LGPL); `node_modules` z paczkami GPL-3.0, CC-BY-NC-4.0, WTFPL i bez licencji.

Wynik: kod 1, 8 blokerów, 11 uwag. Wykryte: klucz Anthropic w `.env` (raz, bez duplikatu jako klucz OpenAI), `.env` w repozytorium, 3 podejrzane wartości w historii gita, brak polecenia uruchomienia i linku do demo (blokery), pięć brakujących elementów README (uwagi), TODO, tylko localhost, GPL z `python-apt` i z npm, CC-BY-NC jako niekomercyjna, LGPL z `img2pdf` i MPL z `pikepdf` (zależność przechodnia) jako słaby copyleft, paczka npm bez licencji jako nieznana, gałąź bez śledzenia zdalnej.

**Repozytorium gotowe:** README z `assets/README-szablon.md` (linki podmienione na lokalny serwer HTTP), `.env` z kluczem lokalnie, ale w `.gitignore`, `.env.example` z pustymi wartościami, `requirements.txt` z `requests`, wypchnięte.

Wynik: kod 0, 0 blokerów. Siedem elementów README obecnych; kryteria z pliku decyzji 3/3; linki 200; `certifi` (MPL-2.0, przechodnia zależność `requests`) jako uwaga; niewypełnione pola `{{...}}` szablonu jako uwaga; lokalny `.env` niezgłoszony; brak sekretów także w historii.

Fragment:

```
BLOKER  [sekrety] .env:1: klucz Anthropic (sk-ant...3d4)
BLOKER  [sekrety] w historii gita sa 3 podejrzane wartosci (np. haslo w URL). Usuniecie pliku nie wystarczy: uniewaznij klucz u dostawcy i wygeneruj nowy
UWAGA   [licencje] python certifi 2026.10.18: MPL-2.0 [Mozilla Public License 2.0 (MPL 2.0)] (slaby copyleft). Zwykle dopuszczalne jako niemodyfikowana zaleznosc; wymien w README
```

### Błędy znalezione i poprawione

- Puste przypisanie `KLUCZ=` w `.env.example` łączyło się z następną linią i dawało fałszywy alarm. Wzorzec nie przechodzi już przez koniec linii.
- Klucz Anthropic był zgłaszany także jako klucz OpenAI. Wzorzec OpenAI wyklucza `sk-ant-`, a jedna linia daje jedno trafienie.
- Plik `LICENSES-THIRD-PARTY.md` zapisywany przez skrypt był potem zgłaszany jako niezacommitowany. Kontrola gita działa teraz przed kontrolą licencji.
- Niewypełnione pola szablonu `{{...}}` nie były wykrywane; są teraz uwagą.

### Czego nie testowano

- Sprawdzania widoczności przez `gh` na prawdziwym repozytorium GitHub (w teście zdalne repozytorium jest lokalne, więc ta kontrola jest pomijana).
- Linków do zewnętrznych serwisów (test używa lokalnego serwera HTTP).
- Projektów z Poetry lub pnpm bez `node_modules`.

## video_check.sh

Wideo testowe wygenerowane przez ffmpeg (`testsrc`, `sine`).

| Przypadek | Wynik |
|---|---|
| 130 s, MPEG-4 i MP3, 1920×1080 | BŁĄD: dłuższe niż 2:00; UWAGA: kodek mpeg4; kod 1 |
| To samo z `--fix demo.mp4` | Wynik 118,0 s, H.264 i AAC, 8 MB; OK; kod 0; około 33 s na CPU |
| 40 s, H.264, 1280×720, bez dźwięku | UWAGA: brak ścieżki dźwiękowej; kod 0 |
| Brak pliku | Komunikat o użyciu, kod 2 |

## Poprawki po przeglądzie świeżego subagenta (2026-11-17)

| Problem z przeglądu | Poprawka | Test |
|---|---|---|
| Niewypełniony szablon README przechodził z 0 blokerów | Pole `{{...}}` to bloker | README prosto z szablonu: kod 1, „niewypelnionych pol szablonu” |
| Klucz w historii gita był blokerem na zawsze, nawet po unieważnieniu | Historia to uwaga z instrukcją unieważnienia; klucz w bieżących plikach nadal blokerem | „UWAGA [sekrety] w historii gita” |
| Literówka w `--decision` pomijała kontrolę kryteriów po cichu | Uwaga „nie ma pliku decyzji” | `--decision literowka.md` → uwaga |
| Brak linii OK przy czystym gicie | „OK [git] wszystko zacommitowane i wypchniete” | gotowe repozytorium |
| Licencje czytane z dowolnego Pythona | Uwaga, gdy większość zależności nie jest zainstalowana; SKILL.md każe aktywować środowisko projektu | przegląd tekstu |
| Brak prezentacji w planie zgłoszenia | Wiersz 09:00 „Prezentacja PDF” w planie zamrożenia, link w szablonie README, sekcja w `hn-pitch-final` | przegląd tekstu |
| Przykład z YouTube 404 (serwisy wideo zwykle zwracają stronę także dla filmów prywatnych) | Przykład zmieniony na widoczność repozytorium; ostrzeżenie, że wideo sprawdza się w incognito | przegląd tekstu |
| Szablon README bez ograniczeń, przykładowych danych i podziału „co powstało na hackathonie” | Sekcja „Ograniczenia”, linia o `examples/`, punkt „Co powstało podczas hackathonu”, komentarz o usuwaniu zdań niepasujących do stacku | gotowe repozytorium z wypełnionym szablonem: 7/7 elementów README |
| Brakujące lokalne pliki z README (np. `docs/screenshot.png`) | Uwaga dla linków i obrazów markdown wskazujących nieistniejące pliki | gotowe repozytorium ma `docs/screenshot.png`, brak uwagi |

Błąd znaleziony przy tych testach: kontrola „dla kogo” była wrażliwa na wielkość liter i przechodziła tylko dzięki słowu „urzędnik” w polu szablonu. Jest teraz niewrażliwa.

`video_check.sh`: `--fix` bez nazwy pliku → „BLAD: --fix wymaga nazwy pliku wynikowego”, kod 2. Nagranie 125 s z `--fix` → „UWAGA: --fix utnie ostatnie 7.0 s nagrania”, wynik 118,0 s, kod 0.

Nie poprawione: preflight nie sprawdza plików wymienionych w README tylko w kodzie (np. `scripts/evaluate.py` w bloku kodu), jedynie linki i obrazy markdown.
