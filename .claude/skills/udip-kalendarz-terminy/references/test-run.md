# test-run: udip-kalendarz-terminy

Uruchomione 2026-11-21, Python 3.13.18, w katalogu głównym repozytorium (`bash scripts/smoke.sh` uruchamia skrót tych testów).

```
$ python3 .claude/skills/udip-kalendarz-terminy/scripts/deadlines.py --selftest
OK  wpływ 2026-11-02 → 2026-11-16 (oczek. 2026-11-16) – zwykły poniedziałek → poniedziałek
OK  wpływ 2026-11-07 → 2026-11-23 (oczek. 2026-11-23) – 21.11 to sobota → poniedziałek 23.11
OK  wpływ 2026-10-18 → 2026-11-02 (oczek. 2026-11-02) – 1.11 niedziela (Wszystkich Świętych) → 2.11
OK  wpływ 2026-10-28 → 2026-11-12 (oczek. 2026-11-12) – 11.11 środa (święto) → 12.11
OK  wpływ 2026-12-10 → 2026-12-28 (oczek. 2026-12-28) – 24.12 czw. Wigilia; 14 dni = 24.12 → 28.12 (25, 26 wolne, 27 niedz.)
OK  wpływ 2026-12-18 → 2027-01-04 (oczek. 2027-01-04) – 1.01.2027 piątek → 4.01 (2–3 weekend)
OK  wpływ 2026-03-22 → 2026-04-07 (oczek. 2026-04-07) – 5.04.2026 Wielkanoc, 6.04 poniedziałek → 7.04
OK  wpływ 2026-05-20 → 2026-06-03 (oczek. 2026-06-03) – 3.06 środa, nie święto
OK  wpływ 2026-05-21 → 2026-06-05 (oczek. 2026-06-05) – 4.06.2026 Boże Ciało → 5.06
OK  wpływ 2024-12-10 → 2024-12-24 (oczek. 2024-12-24) – 2024: Wigilia nie była wolna
OK  2 mies. od 31.12.2026 → 2027-03-01 (oczek. 2027-03-01)
OK  kwerenda +90 dni ucięta do 2 mies. → 2027-01-04; ostrzeżeń: 2
OK  pilność termin 2026-11-23, dziś 2026-11-20 → tomorrow (oczek. tomorrow)
OK  pilność termin 2026-11-23, dziś 2026-11-23 → today (oczek. today)
OK  pilność termin 2026-11-23, dziś 2026-11-24 → overdue (oczek. overdue)
OK  pilność termin 2026-11-26, dziś 2026-11-23 → soon (oczek. soon)
OK  pilność termin 2026-12-15, dziś 2026-11-23 → ok (oczek. ok)
OK  termin bezpieczny dla wpływu 10.12.2026 → 2026-12-23 (oczek. 2026-12-23)

Wynik: wszystkie testy OK
```

```
$ python3 .claude/skills/udip-kalendarz-terminy/scripts/deadlines.py 2026-12-10 --extend-months 2
Termin podstawowy (art. 13 UDIP + art. 57 § 4 KPA): 2026-12-28
Termin bezpieczny (bez przesunięcia na dzień roboczy): 2026-12-23
Termin po przedłużeniu: 2027-02-10
  ! Przed upływem 14 dni wyślij wnioskodawcy powiadomienie o przedłużeniu z podaniem powodów (art. 13 ust. 2 UDIP).
```

```
$ python3 .claude/skills/udip-kalendarz-terminy/scripts/import_xlsx.py data-partner/umb/kalendarium_umb.xlsx --out /tmp/r.json
# Niespójności w arkuszu

- BKS.IV.1431.15.2026: termin w arkuszu 2026-09-26 ≠ wyliczony 2026-09-28 (art. 13 UDIP + art. 57 § 4 KPA)
- BKS.IV.1431.15.2026: odpowiedź 2026-01-14 przed wpływem 2026-09-12 – sprawdź datę wpływu
- BKS.IV.1431.18.2026: termin 2025-01-29 wcześniejszy niż wpływ 2026-01-15 (literówka w roku?); wyliczono 2026-01-29
- BKS.IV.1431.509.2026: tekst w kolumnie terminu ('19.08.2026/18.09.2026 - doprecyzowanie wniosku') → przedłużenie do 2026-09-18
- BKS.IV.1431.543.2026: odpowiedź 2026-09-22 po terminie 2026-08-28 bez odnotowanego przedłużenia
- BKS.IV.1431.590.2026: odpowiedź 2026-09-29 po terminie 2026-09-21 bez odnotowanego przedłużenia

Zaimportowano 10 wniosków.

```

```
$ python3 .claude/skills/udip-kalendarz-terminy/scripts/import_xlsx.py data-partner/umb/kalendarium_umb.xlsx --out /tmp/demo.json --demo-today 2026-11-23 >/dev/null && python3 .claude/skills/udip-kalendarz-terminy/scripts/register.py /tmp/demo.json --today 2026-11-23 --print --html /tmp/k.html --csv /tmp/k.csv --ics /tmp/k.ics && wc -c /tmp/k.html /tmp/k.csv /tmp/k.ics && head -4 /tmp/k.ics
.claude/skills/udip-kalendarz-terminy/scripts/register.py:156: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
  stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
 1 BKS.IV.1431.293.2025   wpł. 2026-11-06 termin 2026-11-20 [overdue ] b) zapytania wysłane do wydziałów      Opieka i odławianie bezdomnych zwierzat.
 2 BKS.IV.1431.307.2025   wpł. 2026-11-09 termin 2026-11-23 [today   ] d) przygotowana odpowiedź              Aktualne zestawienie liczby uczniów w szkołach pod
 3 BKS.IV.1431.16.2026    wpł. 2026-11-10 termin 2026-11-24 [tomorrow] b) zapytania wysłane do wydziałów      Pytanie o liczbę punktów sprzedaży alkoholu powsta
 4 BKS.IV.1431.17.2026    wpł. 2026-11-12 termin 2026-11-26 [soon    ] b) zapytania wysłane do wydziałów      Proszę o udostępnienie informacji publicznej dot.r
 5 BKS.IV.1431.15.2026    wpł. 2026-11-13 termin 2026-11-27 [done    ] e) odpowiedź wysłana                   Zapytanie o rzeźbę Ludmiły Stehnovej która została
 6 BKS.IV.1431.599.2026   wpł. 2026-11-16 termin 2026-11-30 [ok      ] a) brak działań                        Edytowalne zestawienie liczby uczniów oraz uczniów
 7 BKS.IV.1431.590.2026   wpł. 2026-11-17 termin 2026-12-01 [ok      ] a) brak działań                        Kompleks Astoria.
 8 BKS.IV.1431.543.2026   wpł. 2026-11-18 termin 2027-01-04 [ok      ] c) kwerenda (przedłużenie)             Opieka nad bezdomnymi zwierzętami i ich wyłapywani
 9 BKS.IV.1431.509.2026   wpł. 2026-11-19 termin 2026-12-03 [ok      ] a) brak działań                        Dokumentacja dotycząca basenu Astorii: projekt zag
10 BKS.IV.1431.18.2026    wpł. 2026-11-20 termin 2026-12-04 [ok      ] a) brak działań                        Liczba mieszkańców wskazanych ulic według opłat za
 5599 /tmp/k.html
 2360 /tmp/k.csv
 3307 /tmp/k.ics
11266 total
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//asystent-udip//PL
CALSCALE:GREGORIAN
```

```
$ python3 .claude/skills/udip-kalendarz-terminy/scripts/register.py data-samples/syntetyczne/kalendarz_demo.json --today 2026-11-22 --year 2026 --print
 1 BKS.IV.1431.109.2026   wpł. 2026-10-29 termin 2026-12-14 [ok      ] c) kwerenda (przedłużenie)             Straż miejska interwencje
 2 BKS.IV.1431.108.2026   wpł. 2026-10-30 termin 2026-11-13 [done    ] e) odpowiedź wysłana                   Schronisko dla zwierząt
 3 BKS.IV.1431.100.2026   wpł. 2026-11-06 termin 2026-11-20 [overdue ] b) zapytania wysłane do wydziałów      Remont ulicy
 4 BKS.IV.1431.102.2026   wpł. 2026-11-09 termin 2026-11-23 [tomorrow] b) zapytania wysłane do wydziałów      Wycinka drzew
 5 BKS.IV.1431.103.2026   wpł. 2026-11-10 termin 2026-11-24 [soon    ] a) brak działań                        Liczba uczniów i nauczycieli
 6 BKS.IV.1431.107.2026   wpł. 2026-11-16 termin 2026-11-30 [ok      ] a) brak działań                        Pozwolenie na budowę
 7 BKS.IV.1431.104.2026   wpł. 2026-11-17 termin 2026-12-01 [ok      ] a) brak działań                        Wydatki na promocję i sponsoring
 8 BKS.IV.1431.106.2026   wpł. 2026-11-18 termin 2026-12-02 [ok      ] a) brak działań                        Odpady komunalne
 9 BKS.IV.1431.105.2026   wpł. 2026-11-19 termin 2026-12-03 [ok      ] a) brak działań                        Przetarg i umowa
10 BKS.IV.1431.101.2026   wpł. 2026-11-20 termin 2026-12-04 [ok      ] d) przygotowana odpowiedź              Oświetlenie uliczne
```

