# 01. Partner i problem: kto, czego potrzebuje, co uzna za sukces

Stan: 21.11.2026, po publikacji pełnej treści (11:00) i po otrzymaniu materiałów UMB od mentorów. Oznaczenia: [✔] źródło pierwotne, [~] wtórne, [?] hipoteza. Szczegóły i URL: `notatki/partner_szczegoly.md`, `zrodla.md`.

## Partner

| Pole | Ustalenie | Pewność |
|---|---|---|
| Partner | Urząd Miasta Bydgoszczy (UMB); przyrzekający nagrodę: Miasto Bydgoszcz (Regulamin zadania § 1 ust. 3) | [✔] `docs/zadanie/` |
| Nagroda | 15 000 zł brutto, jedna nagroda główna (Regulamin § 3) | [✔] |
| Opiekunowie zadania | pracownik Biura Komunikacji Społecznej i pracownik Biura Rady Miasta (pełna treść, pkt 10) | [✔] |
| Kto prowadzi UDIP w UMB | **Biuro Komunikacji Społecznej (BKS)**, referat IV: „centralna ewidencja wniosków”, BIP. Znak spraw: `BKS.IV.1431.<nr>.<rok>` [✔] próbki UMB; 1431 to symbol JRWA dla udostępniania informacji publicznej [?] z pamięci, DO WERYFIKACJI | [✔]/[?] |
| Procedura wewnętrzna | Zarządzenie Prezydenta Miasta Bydgoszczy z 2024 r. „w sprawie zasad i trybu udostępniania informacji publicznej” (plik UMB „Zarządzenie Informacja Publiczna 535-2024”; OCR nagłówka czyta „Nr 536”, DO WERYFIKACJI) | [✔] dokument UMB |
| EZD | UMB rejestruje korespondencję w **SIDAS** (e-mail w próbce 543.2026: „Prośba o rejestrację w SIDAS”); SIDAS to produkt MADKOM SA. Zadanie wyklucza integrację (pkt 11) | [✔] próbka UMB, [~] producent |
| Prawa autorskie | Zwycięzca przenosi autorskie prawa majątkowe na Miasto (Regulamin § 4) → zależności z licencjami permisywnymi | [✔] |

## Proces według Zarządzenia (jak to działa dziś)

1. Wniosek wpływa (e-mail, e-Doręczenia, ePUAP, papier, kancelaria) i trafia do **AIP** (Administrator Informacji Publicznej, BKS), który go rejestruje (§ 9).
2. AIP „niezwłocznie” przekazuje zakres wniosku **właściwym merytorycznie wydziałom** (§ 10).
3. Wydział przygotowuje **projekt odpowiedzi w swojej części** i przesyła na bip@um.bydgoszcz.pl w terminie wyznaczonym przez AIP (§ 11 ust. 1); sam robi **anonimizację** (§ 11 ust. 8); przy informacji przetworzonej przesyła uzasadnienie (ust. 7); przy odmowie – projekt decyzji (ust. 9); gdy nie ma informacji – wskazuje podmiot właściwy (ust. 3).
4. AIP składa odpowiedź (pismo BKS, „Łączę wyrazy szacunku”, podpis Biura) i wysyła; decyzje podpisuje Prezydent lub upoważnione osoby (§ 12).

Wniosek: użytkownikiem głównym jest **AIP w BKS** (kilka osób; w arkuszu „Pracownik 1”, „Pracownik 2”), a wydziały są dostawcami treści. Narzędzie musi pasować do tego podziału: AIP rejestruje, rozsyła, zbiera, składa, anonimizuje i pilnuje terminów.

## Problem w liczbach i dowodach

| Dowód | Co pokazuje | Źródło |
|---|---|---|
| Arkusz kalendarium UMB (10 spraw) | Rejestr prowadzony ręcznie w Excelu: formuły `=E11+14` bez przesunięcia z soboty, termin w złym roku (18.2026: 29.01.2025), data wpływu późniejsza niż odpowiedź (15.2026), przedłużenie wpisane tekstem w kolumnie dat (509.2026). Nasz import znajduje 6 niespójności | [✔] `data-partner/umb/niespojnosci_arkusza.md` |
| Próbki odpowiedzi UMB | 5 powtarzalnych typów pism: udostępnienie „Ad 1…Ad N”, odesłanie (art. 4 ust. 3), „nie prowadzimy statystyk”, kwerenda (art. 13 ust. 2), wezwanie do doprecyzowania (7 dni) | [✔] `data-partner/umb/archiwum_umb.jsonl` |
| Powtarzalne tematy | Te same pytania co rok: bezdomne zwierzęta 2024 (293.2025) i 2025 (543.2026), liczba uczniów i cudzoziemców (307.2025, 599.2026), Astoria (509, 590) | [✔] arkusz UMB |
| Opóźnienia | 543.2026 i 590.2026: odpowiedź po 14 dniach bez przedłużenia w arkuszu (kwerenda była, ale tylko w piśmie) | [✔] arkusz + pisma |
| Skala w Polsce | 266 940 wniosków w 2025 r. w badanych urzędach, średnio 112 na urząd (Watchdog Polska, 2026) | [~] `notatki/prawo_szczegoly.md` § 8 |
| Skala w UMB | Numeracja próbek dochodzi do 599 we wrześniu 2026 → rzędu 800 wniosków rocznie [?] (wniosek z numerów, nie statystyka UMB) | [?] |
| Rękopisy | Wniosek 16.2026 to rękopis drukowanymi literami na kratce; OCR (Tesseract) zwraca śmieci | [✔] test `udip-dane-i-zrodla` |

## Hipotezy: czego Partner naprawdę potrzebuje

| # | Hipoteza | Dowód | Pewność |
|---|---|---|---|
| H1 | Najważniejszy jest **kalendarz/rejestr** zastępujący Excel: kolejność od najstarszych, kolory na dziś/jutro, statusy a–e, inicjały, kwerenda, wybór roku | Treść pkt 3 i pkt 5 (jury sprawdzi „10 wniosków testowych”), arkusz UMB jako „robocza wizualizacja” | [✔] |
| H2 | **Wydziały odpowiadają częściami**, a BKS skleja je w „Ad 1…Ad N”: generator ma składać pismo z kilku plików wydziałów, nie pisać od zera | Zarządzenie § 11 ust. 1; odpowiedzi 293.2025 i 543.2026 łączą WGK i Schronisko | [✔] |
| H3 | **Anonimizacja = szary → czarny po akceptacji**, według listy UMB (28 pozycji w `data-partner/umb/dane_podlegajace_anonimizacji_UMB.txt`, m.in. PESEL, adres, podpis, zdrowie, karalność, nr działki) | Treść pkt 4; plik „Dane podlegające anonimizacji.txt” | [✔] |
| H4 | **„Uczenie się”** oznacza wgrywanie ustaw, zarządzeń i archiwalnych odpowiedzi przez urzędnika i korzystanie z nich (wyszukiwanie, wzory), nie trening modelu | Treść pkt 1 i „uproszczona instrukcja” pkt 1 | [~] interpretacja |
| H5 | Model docelowy **lokalny, bez internetu**; trzeba wskazać konkretny model w prezentacji | Treść pkt 1, sekcja 4 pkt 8 i sekcja 5 | [✔] |
| H6 | Wartość „ścieżki do wydziału” rośnie dzięki archiwum: „w zeszłym roku to pytanie poszło do WGK i Schroniska” | „Uproszczona instrukcja” pkt 3–4 | [~] |

## Użytkownicy i decydenci

| Rola | Potrzeba | Gdzie w produkcie |
|---|---|---|
| AIP (BKS, „Pracownik 1/2”) | Nie przegapić terminu; szybko znaleźć poprzednią odpowiedź; skleić pismo | Kalendarz, archiwum, generator |
| Wydział merytoryczny | Dostać jasny zakres pytań; mniej pracy z anonimizacją | Lista pytań per wydział, propozycje anonimizacji |
| Kierownik BKS / Sekretarz | Widok zaległości, statystyka | Liczniki „po terminie/dziś/jutro” |
| Radca prawny | Przypadki graniczne: informacja przetworzona, odmowa (decyzja), anonimizacja jako częściowa odmowa | Flagi w analizie i ostrzeżenie przy finalizacji |
| Decydent wdrożenia | Biuro Cyfryzacji i Bezpieczeństwa Informacji (BCB) + IOD; Wydział Informatyki (WI) | Argumenty: offline, licencje, brak integracji |

## Co Partner uzna za sukces

Kryteria z pełnej treści (sekcja 8): zgodność z założeniami 30%, bezpieczeństwo i skuteczna anonimizacja 20%, łatwość obsługi 20%, kompletność i jakość prototypu 30%. Test jury (sekcja 6) to sześć kroków; `udip-ewaluacja/scripts/acceptance.py` odtwarza je na danych UMB (9/9 testów przechodzi, 21.11.2026).

Mierzalny sukces dla UMB: czas od wgrania odpowiedzi wydziałów do projektu pisma liczony w minutach, zero przekroczeń terminu w kalendarzu, zero wycieków danych w wersji zanonimizowanej.
