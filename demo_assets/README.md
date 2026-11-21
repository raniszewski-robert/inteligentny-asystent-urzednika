# Pliki przykładowe

Wszystkie dane osobowe w tych plikach są fikcyjne. Rafał Bruski (Prezydent Miasta Bydgoszczy) występuje wyłącznie w roli funkcjonariusza publicznego, żeby pokazać, że takich osób narzędzie nie anonimizuje automatycznie (art. 5 ust. 2 UDIP). Pliki odtwarza `python scripts/make_demo_assets.py`.

| Plik | Gdzie wgrać | Co pokazuje |
|---|---|---|
| `01_rejestr_umb.xlsx` | Kalendarz → Import arkusza | Kopia arkusza kalendarium UMB: 10 spraw i raport 6 niespójności (termin w sobotę, rok 2025 przy wniosku z 2026 itd.). |
| `02_wniosek_atak_bezpieczenstwa.docx` | Nowy wniosek, potem Anonimizacja | Wniosek o wydatki na zieleń z pułapkami: polecenie „zignoruj poprzednie instrukcje”, ukryty biały tekst 1 pt, obraz podpisu, PESEL, IBAN, e-mail, telefon. Reguły proponują zaczernienie danych wnioskodawcy, Prezydenta zostawiają do decyzji, adres urzędu (ul. Jezuicka 1) zostawiają jawny. „Olena Shevchenko” wykrywa słownik imion i nazwisk, który zna też nazwiska ukraińskie i rosyjskie w zapisie paszportowym i polskim (Olena Shevchenko, Ołena Szewczenko). |
| `03_odpowiedz_wydzialu.docx` | Sprawa 543 → Odpowiedzi wydziałów | Odpowiedź Schroniska: 839 psom, 560 kotom, 3 143 761,14 zł. Projekt pisma przenosi te liczby do Ad 3 i Ad 4. |
| `03b_odpowiedz_wydzialu_zamienione_liczby.docx` | do kontroli liczb | Ta sama odpowiedź z zamienionymi psami i kotami. Wklej zdanie z tego pliku do treści pisma (Projekt pisma → edycja): kontrola liczb oznaczy „839 kot… zamiast pso…”. |
| `04_nowelizacja_udip_2026_demo.pdf` | Archiwum → Dodaj akt prawny | Jednostronicowy dokument wyraźnie oznaczony jako demonstracyjny (nie jest aktem prawnym). Po wgraniu wyszukiwanie „termin 14 dni” zwraca § 1. |
