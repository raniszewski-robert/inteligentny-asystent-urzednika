# Film: scenariusz i ścieżka kliknięć (T21, limit 2:45)

> Linie zaczynające się od „>” to obraz i kliknięcia; zwykły tekst to lektor. Czas: `python3 .claude/skills/hn-pitch-final/scripts/pitch_timing.py docs/video_script.md --limit 2:45` (130 słów na minutę). Plan scen razem 2:32; sam lektor 2:03 przy 130 słowach na minutę, 2:19 przy 115. Trasy według CONTRACTS §5; etykiety przycisków sprawdzić w gotowym UI przed nagraniem.
>
> Przygotowanie: `bash run.sh --reseed` (albo `.\run.ps1 -Reseed`), kalendarz w trybie demo (daty przesunięte na dzień nagrania), urzędnik w nagłówku wybrany, `UDIP_PROVIDER=rules`. Przeglądarka 125%, 1280×720, bez innych kart i powiadomień. Pliki pod ręką: `data-partner/umb/kalendarium_umb.xlsx`, `data-partner/umb/probki/Wniosek - BKS.IV.1431.599.2026.docx`, `data-partner/umb/przypadek_543/WGK.txt` i `SCHRONISKO.txt`, `docs/deck/demo_dane_osobowe.docx` (dane fikcyjne), Zarządzenie UMB 2024 w PDF (materiały UMB, poza repozytorium). Nagrywanie i konwersja: `.claude/skills/hn-zgloszenie/assets/wideo-scenariusz.md`.

## 1. Otwarcie (0:08)

> Obraz: `/kalendarz`, nagłówek „Urząd Miasta Bydgoszczy · Biuro Komunikacji Społecznej”.

Asystent UDIP dla Urzędu Miasta Bydgoszczy. Pokazujemy drogę wniosku o informację publiczną na prawdziwych sprawach UMB.

## 2. Kalendarz (0:22)

> Obraz: `/kalendarz`, 10 spraw UMB od najstarszej, liczniki „po terminie / dziś / jutro”.
> Klik: najechanie na podświetlony wiersz po terminie, potem na wiersz z terminem jutro; kolumny „termin” i „termin bezpieczny”.
> Klik: zmiana statusu jednej sprawy na „b) zapytania wysłane do wydziałów” (`POST /sprawy/{id}/status`); w historii pojawiają się inicjały.
> Klik: import arkusza (`POST /kalendarz/import`), plik `kalendarium_umb.xlsx`; raport pokazuje 6 niespójności.

Dziesięć spraw z arkusza BKS, od najstarszej. Podświetlone są te po terminie i z terminem dziś albo jutro. Termin uwzględnia soboty i święta, obok jest termin bezpieczny. Status zmieniam jednym kliknięciem, z inicjałami w historii. Import obecnego arkusza od razu wskazuje sześć miejsc do sprawdzenia.

## 3. Nowy wniosek z pliku Word (0:26)

> Klik: „Nowy wniosek” (`/wniosek/nowy`), wgranie `Wniosek - BKS.IV.1431.599.2026.docx`.
> Obraz: 2 pytania, flaga „informacja przetworzona?”, podobna sprawa BKS.IV.1431.307.2025 z etykietą „starsza niż rok”, propozycja „Wydział Edukacji i Sportu” przy obu pytaniach.
> Klik: potwierdzenie numeru, daty wpływu i inicjałów; powrót do `/kalendarz`, nowa sprawa ze statusem „a) brak działań”.

[PAUZA 2s]
Wgrywam wniosek w formacie Word. Narzędzie wyciąga dwa pytania, o uczniów i o cudzoziemców w szkołach, i znajduje sprawę 307 z 2025 roku o tym samym. Proponuje Wydział Edukacji i Sportu. Potwierdzam numer, datę i inicjały: wniosek jest w kalendarzu.

## 4. Odpowiedzi wydziałów (0:14)

> Klik: sprawa BKS.IV.1431.543.2026 w kalendarzu (`/sprawy/{id}`); wgranie `WGK.txt` i `SCHRONISKO.txt` (`POST /sprawy/{id}/odpowiedzi`).
> Obraz: oba pliki z rozpoznanym wydziałem: Wydział Zieleni i Gospodarki Komunalnej, Schronisko dla Zwierząt.
> Napis na ekranie: „Odpowiedzi wydziałów odtworzone z pisma BKS”.

Sprawa o bezdomne zwierzęta. Wgrywam odpowiedzi Wydziału Zieleni i Gospodarki Komunalnej oraz Schroniska; narzędzie rozpoznaje, kto je przysłał.

## 5. Projekt pisma (0:28)

> Klik: „Generuj projekt”, typ „udostępnienie” (`/sprawy/{id}/projekt`).
> Obraz: pismo „Ad 1…Ad 5”, w Ad 3 „839 psom oraz 560 kotom”, w Ad 4 „3.143.761,14 zł”; raport obok: kontrola liczb bez błędów, 2 niepewne przypisania.
> Klik: zdanie „Opiekę nad domowymi zwierzętami bezdomnymi sprawuje Schronisko…” przeniesione z Ad 2 do Ad 1 (tak jak w piśmie BKS); zapis, „wersja 2”.

[PAUZA 2s]
Projekt w układzie BKS, od Ad 1 do Ad 5. Liczby psów, kotów i budżet schroniska pochodzą z odpowiedzi wydziałów. Narzędzie sprawdza każdą liczbę ze źródłem i odrzuca zmyśloną kwotę albo zamienione psy z kotami. Zdanie z niepewnym przypisaniem przenoszę do Ad 1 i zapisuję drugą wersję.

## 6. Anonimizacja (0:24)

> Klik: „Anonimizacja” (`/anonimizacja`), wgranie `docs/deck/demo_dane_osobowe.docx`.
> Obraz: szare propozycje (imię i nazwisko, adres, telefon, e-mail, PESEL, dowód, rachunek, „ur. 12.03.1980 r. w Toruniu”), „J. Nowak” w ramce „do decyzji”.
> Klik: „Zaczernij wszystkie propozycje” → czarne; „J. Nowak” → „zaczernij”; „Zatwierdź anonimizację”; eksport DOCX wersji zanonimizowanej (`/anonimizacja/{token}/eksport/zanonimizowana.docx`). Eksport jest zablokowany, dopóki choć jeden fragment nie ma decyzji.

Plik z PESEL-em, dowodem, rachunkiem, adresem i datą urodzenia. Szare to propozycje według listy UMB, w ramce to, o czym decyduje urzędnik. Po akceptacji dane są czarne. Plik pobiorę dopiero, gdy każdy fragment ma decyzję. W sprawie powstają dwie wersje: do wysyłki i zanonimizowana do archiwum.

## 7. Baza wiedzy (0:14)

> Klik: „Archiwum” (`/archiwum`), wgranie Zarządzenia UMB 2024 jako przepisu (`POST /archiwum/przepisy`); licznik dokumentów rośnie.
> Klik: wyszukanie „kto podpisuje decyzje”; wynik: § 12 Zarządzenia.

Narzędzie uczy się z tego, co wgra urzędnik. Dodaję zarządzenie o informacji publicznej i od razu znajduję, kto podpisuje decyzje: paragraf 12.

## 8. Bez internetu i zamknięcie (0:16)

> Klik: wyłączenie Wi-Fi (ikona systemowa w kadrze); odświeżenie `/biurko` i `/kalendarz`: wszystko działa na regułach, bez internetu.
> Plansza: „Bielik-11B-v3.1-Instruct, Apache-2.0, lokalnie w urzędzie” i „pomiar: nie zmierzono w czasie hackathonu”; adres repozytorium.

Bez internetu wszystko działa dalej. Docelowo akapity redaguje lokalny model Bielik na serwerze urzędu. Pismo powstaje w kilka minut, a decyzja zawsze należy do urzędnika.

> ## Ścieżka kliknięć w skrócie
>
> | Scena | Trasa | Plik / działanie |
> |---|---|---|
> | 1–2 | `GET /kalendarz`, `POST /sprawy/{id}/status`, `POST /kalendarz/import` | `kalendarium_umb.xlsx` |
> | 3 | `GET/POST /wniosek/nowy` | `Wniosek - BKS.IV.1431.599.2026.docx` |
> | 4 | `GET /sprawy/{id}`, `POST /sprawy/{id}/odpowiedzi` | `WGK.txt`, `SCHRONISKO.txt` (sprawa 543.2026) |
> | 5 | `GET/POST /sprawy/{id}/projekt` | przeniesienie zdania z Ad 2 do Ad 1, wersja 2 |
> | 6 | `GET/POST /anonimizacja` | `docs/deck/demo_dane_osobowe.docx`, eksport DOCX |
> | 7 | `GET /archiwum`, `POST /archiwum/przepisy` | Zarządzenie UMB 2024 (PDF) |
> | 8 | `GET /biurko`, `GET /kalendarz` | Wi-Fi wyłączone |
>
> Wymagania sekcji 4 pkt 4 treści zadania w filmie: wgranie pliku Word (scena 3, 6), przetwarzanie (3–5), projekt odpowiedzi (5). Testy jury z sekcji 6: 1 → scena 3, 2 → 5, 3 → 6, 5 → 2, 6 → 2 i 7.
