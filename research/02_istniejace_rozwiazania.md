# 02. Co już istnieje i gdzie jest luka

Stan: 21.11.2026. Szczegóły i URL: `notatki/technologia_szczegoly.md` § 6, `notatki/partner_szczegoly.md` § 3–5.

## Co ma Partner

| Element | Stan | Pewność |
|---|---|---|
| EZD | SIDAS (MADKOM SA) – rejestracja korespondencji; brak integracji w zakresie zadania (pkt 11) | [✔] próbka 543.2026 |
| Rejestr UDIP | Arkusz Excel „WNIOSKI O UDOSTĘPNIANIE INFORMACJI PUBLICZNEJ” (9 kolumn: Lp., numer, wnioskodawca, przedmiot, data wpływu, termin, data odpowiedzi, osoba, pozostało dni) | [✔] `data-partner/umb/kalendarium_umb.xlsx` |
| Wzory pism | Utrwalone formuły BKS (5 typów), pisane ręcznie | [✔] próbki UMB |
| Anonimizacja | Ręczna, w wydziałach (Zarządzenie § 11 ust. 8); w próbce 509.2026 wydział pisze o „skomplikowanym procesie anonimizacji” opóźniającym dostęp do akt o miesiąc | [✔] |
| AI w UMB | Brak komunikatu o AI w UDIP; wiceprezydent Ł. Krupa mówił o AI w urzędach (Atos Smart City, 19–20.11.2026) | [✔]/[~] |

## Co istnieje w Polsce

| Rozwiązanie | Co robi | Czego brakuje względem zadania | Pewność |
|---|---|---|---|
| EZD RP (NASK/MC) | Elektroniczne zarządzanie dokumentacją | Opis funkcji nie wspomina o rejestrze UDIP, AI ani anonimizacji | [~] |
| PLLuM w samorządach (Gdynia, Łódź, Częstochowa) | Chatbot dla mieszkańców, wyszukiwarka BIP | Narzędzie dla mieszkańca, nie dla AIP; brak kalendarza i anonimizacji | [~] |
| Asystent AI w mObywatelu (PLLuM) | Odpowiedzi dla obywateli | j.w. | [~] |
| Anonimizatory (Typly, eAuditor Bluur AI, Praetor WK, „Anonymizer for Polish Language” PŁ) | Anonimizacja dokumentów | Komercyjne lub akademickie, nie znają listy UMB, brak kalendarza i archiwum | [~] nie testowane |
| Kalkulatory terminów (np. gotowybip.pl) | Liczą 14 dni | Brak rejestru i statusów | [~] |
| Microsoft Presidio | Silnik anonimizacji (MIT) | Dla PL tylko PESEL; NIP/REGON/dowód/IBAN trzeba dopisać | [✔] |

HackNation 2025: zadanie miasta „Bydgoszcz – Ścieżki Pamięci 2.0” wygrał Adrian Michalski (25 000 zł). Losu projektu po hackathonie nie ustaliliśmy [?]. Dla nas to sygnał, że miasto pyta o wdrażalność, więc pokazujemy instalację w jednym kroku i brak zależności od chmury.

## Luka, którą da się zająć w 22 h

Nie znaleźliśmy narzędzia, które w jednym przepływie offline łączy pięć rzeczy [?, przegląd niepełny]:
1. rejestr UDIP z terminami według art. 13 UDIP i art. 57 KPA;
2. archiwum odpowiedzi z wyszukiwaniem podobnych spraw;
3. podpowiedź wydziału na podstawie struktury UMB i historii;
4. składanie pisma BKS z części przygotowanych przez wydziały;
5. anonimizację według listy UMB z akceptacją człowieka.

Każdy z tych klocków osobno istnieje. Wyróżnikiem jest dopasowanie do procesu UMB: znak BKS.IV.1431, formuły pism, Zarządzenie, import ich arkusza. Rdzeń jest już w pakiecie (`.claude/skills/udip-*`, testy 21.11).

## Czego nie budujemy (i mówimy to jury)

- Integracji z SIDAS i wysyłki (pkt 9 i 11 treści).
- Automatycznej decyzji odmownej: projekt decyzji przygotowuje wydział (§ 11 ust. 9), a decyzję podpisuje Prezydent (§ 12).
- Rozpoznawania rękopisów: wniosek 16.2026 wymaga ręcznego przepisania albo modelu obrazowego. Pokazujemy ostrzeżenie zamiast śmieci z OCR.
