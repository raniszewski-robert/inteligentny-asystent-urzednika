# Wnioski z HackNation 2025

Pytanie: **co wygrywało w 2025 r. i na czym zespoły traciły?** Publicznych relacji uczestników jest mało, a większość tekstów to komunikaty prasowe. Dlatego każdy wniosek ma oznaczenie pewności ([✔] relacja pierwotna uczestnika lub uczelni, [~] źródło wtórne lub fragment, [?] nasza interpretacja). Numery źródeł: `zrodla.md`. Dostęp: 2026-11-17.

## Fakty o edycji 2025

| Fakt | Pewność | Źródło |
|---|---|---|
| 6–7.12.2025, BCTW Bydgoszcz, około 1500 uczestników, 16 zadań, 437 zgłoszonych rozwiązań | [✔] / [~] | Z1, Z9 |
| Jury wybrało po trzy najlepsze rozwiązania na zadanie; finaliści prezentowali prototypy, założenia, sposób działania i ścieżki rozwoju | [~] | Z10, Z11 |
| Zwycięzcę wskazywano według „największego potencjału do wdrożenia w administracji publicznej" | [~] | Z10, Z11 |
| Nagroda 25 000 zł za zadanie i możliwość dalszej pracy z instytucją; brak nagród za 2. i 3. miejsce (uczestnicy to krytykowali) | [~] | Z9, Z13 |
| Ponad 250 mentorów, w tym przedstawiciele instytucji, które zgłosiły zadania | [~] | Z9 |
| W jednym zadaniu MC („Zgrany budżet") złożono ponad 20 projektów; finalista miał ocenę 4,85 na 5 | [✔] | Z13 |
| Średnio 437 / 16 ≈ 27 zgłoszeń na zadanie (nasz rachunek) | [?] | Z1 |

## Wnioski dla zespołu

1. **Etap 1 jest wąskim gardłem.** Przy 20–30 zgłoszeniach na zadanie i pięciu miejscach w finale odpada około 80% zespołów, a juror ma na projekt kilka minut. Ocena 4,85/5 u finalisty pokazuje, że w finale lądują projekty niemal bez strat punktów. Dlatego `hn-zgloszenie` pilnuje, żeby każde kryterium miało w zgłoszeniu widoczny dowód. [?] na podstawie Z13 i Z2.
2. **Jury w finale chce zobaczyć działanie na konkretnym przypadku, a nie slajdy.** Zespół Solvro (zadanie KAS, drugi wynik po etapie 1) przygotował prezentację w Figmie i liczył na umiejętności wystąpień, ale jury poprosiło o demo na żywo konkretnego przypadku użycia. Zespół musiał improwizować i przegrał z konkurentem. [✔ Z12] Stąd `hn-pitch-final` zaczyna od demo, a slajdy traktuje jako zapas.
3. **Wygrywa rozwiązanie wpięte w to, czego urzędnik już używa.** Zwycięzcy zadania MSiT (White Hats, PWr) uznali interfejs za najważniejszą część i zrobili go jako dodatek do Microsoft Word, tak żeby urzędnik prowadził sprawę od wpływu do decyzji bez wychodzenia z Worda. [✔ Z11] W 2026 r. przewodnik też mówi o pokazaniu działania i pytaniach jury. [✔ Z2]
4. **Trafienie w realny ból Partnera wyróżnia projekt.** Solvro zbudował orkiestrator, który sprawdza strony bukmacherskie co 15 minut, bo kontrola ręczna kończy się po godzinach pracy urzędu. Dashboard zaprojektowali tak, by nieprawidłowości było widać w 3 sekundy, szczegóły w 30, a pełny obraz w 300. [✔ Z12]
5. **Wiedza domenowa waży tyle co kod.** KAS dał uczestnikom notatnik NotebookLM ze zweryfikowanymi przepisami. Zespół opisał naukę kontekstu prawnego jako dużą część zadania. [✔ Z12] Na miejscu warto od razu zapytać Partnera, czy udostępnia materiały domenowe, i iść do jego mentorów.
6. **Jury mogło oceniać szerzej, niż wynikało z opisu zadania, a platforma zgłoszeń miała problemy.** To relacja uczestnika z LinkedIna, znana tylko z fragmentu w wynikach wyszukiwania (strona blokuje odczyt); nie mamy pewności, że dotyczy HackNation. [~ Z14] Wniosek praktyczny i tak jest tani: zgłoszenie wstępne wypełnić w sobotę, finalne wysłać z zapasem i mieć te same materiały w README repozytorium.
7. **Prawa autorskie.** Przed edycją 2025 organizatorzy mówili, że prawa będą przekazywane tylko przy zwycięskich projektach, które tego wymagają do wdrożenia. [~ Z15, materiał prasowy] W 2026 r. decyduje regulamin zadania (Z4 §6.3), więc trzeba go przeczytać w sobotę.
8. **Szkielet przed wydarzeniem.** Sponsorowany tekst chip.pl przed edycją 2025 radził przygotować wcześniej repozytorium z pipeline'em danych, automatyzacją wdrożeń i komponentami UI. [~ Z16] To nie jest stanowisko organizatora. Kwestię gotowego kodu trzeba potwierdzić na Discordzie.

## Czego nie udało się ustalić

- Kryteriów i wag z 2025 r. oraz uzasadnień jury dla zwycięzców.
- Czasu pitchu w finale 2025.
- Tego, ile zwycięskich rozwiązań faktycznie wdrożono.
