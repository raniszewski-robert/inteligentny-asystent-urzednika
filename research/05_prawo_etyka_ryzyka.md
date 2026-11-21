# 05. Prawo, czerwone linie, ryzyka

Stan prawny na 21.11.2026. Pełne tabele, cytaty i sygnatury: `notatki/prawo_szczegoly.md`. To nie jest porada prawna; przepisy w kodzie zatwierdza radca prawny UMB.

## Akty, które stosujemy

| Akt | Wersja | Co z niego bierzemy | Pewność |
|---|---|---|---|
| Ustawa o dostępie do informacji publicznej (UDIP) | tj. Dz.U. 2022 poz. 902, zm. Dz.U. 2025 poz. 1844 (od 1.01.2026; UMB cytuje tę parę w piśmie 509.2026) | art. 2 (bez wykazywania interesu), 3 ust. 1 pkt 1 (przetworzona), 4 ust. 3 (posiadacz informacji), 5 ust. 2 (prywatność, wyjątek funkcjonariuszy), 10 (BIP), 13 (14 dni / 2 miesiące), 14 (forma), 15 (opłata), 16 (decyzja) | [✔] ELI; zakres zmiany 2025/1844 DO WERYFIKACJI |
| KPA | tj. Dz.U. 2025 poz. 1691 | art. 57 § 1, 3, 4 (liczenie terminów), 107 (decyzja), 129 § 2 (odwołanie 14 dni) | [✔] |
| Ustawa o dniach wolnych od pracy | tj. Dz.U. 2025 poz. 296; Wigilia: Dz.U. 2024 poz. 1965, od 1.02.2025 | lista świąt w `deadlines.py` | [✔] ELI |
| Zarządzenie Prezydenta Miasta Bydgoszczy (2024) o zasadach i trybie UDIP | plik UMB „535-2024” (OCR: „Nr 536”) | role AIP i wydziałów, § 8 (BIP), § 11 (projekt odpowiedzi, anonimizacja w wydziale, przetworzona, decyzja), § 12 (kto podpisuje decyzje) | [✔] dokument UMB |
| RODO | art. 6, 86 | podstawa i minimalizacja; anonimizacja w odpowiedziach | [✔] |
| AI Act 2024/1689 + omnibus 2026/1744 | zał. III od 2.12.2027 (wg źródeł wtórnych), art. 50 od 2.08.2026 | asystent z człowiekiem w pętli najpewniej nie jest systemem wysokiego ryzyka | [~] / [?] ocena własna |
| Ustawa o systemach sztucznej inteligencji | Dz.U. 2026 poz. 1003, w życie 11.08.2026 | obowiązków dla JST nie znaleziono | [✔] akt, [?] obowiązki |

## Reguły zakodowane (i gdzie są testy)

| Reguła | Implementacja | Uwaga prawna |
|---|---|---|
| Termin 14 dni od dnia złożenia; dzień wpływu się nie liczy | `deadline_days` | sądy liczą „od dnia złożenia” (II SAB/Ol 107/23) [✔] |
| Koniec w sobotę / dzień ustawowo wolny → następny dzień roboczy | `shift_to_working_day` (art. 57 § 4 KPA) | **Orzecznictwo nie przesądza** stosowania art. 57 KPA do art. 13 UDIP (NSA III OSK 754/25: postępowanie o informację nie jest postępowaniem administracyjnym) → pokazujemy także `due_safe` (ostatni dzień roboczy przed 14. dniem) i planujemy według niego |
| Przedłużenie do 2 miesięcy, powiadomienie z powodami przed upływem 14 dni | `deadline_extended` (art. 57 § 3), ostrzeżenie | lakoniczne powody = bezczynność (II SAB/Ol 107/23) [✔] |
| Doprecyzowanie: 7 dni, potem pozostawienie bez rozpoznania | szablon `doprecyzowanie` | praktyka UMB (509.2026), nie przepis UDIP [✔ próbka] |
| Wysyłka: liczy się wysłanie w sposób umożliwiający odbiór, kanał zgodny z wnioskiem | `requested_form` w analizie | WSA Kraków II SAB/Kr 34/26 [✔] |
| Inne tryby (petycja, ooś 1 mies., ponowne wykorzystanie, radny 14 dni, akta KPA, prasa) | `MODES` w `analyze.py` → flaga „tryb” | rozróżnienie: tabela w `notatki/prawo_szczegoly.md` § 4 |

## Czerwone linie produktu (i jak je pokazujemy w interfejsie)

| Czerwona linia | Dlaczego | W interfejsie |
|---|---|---|
| Narzędzie niczego nie wysyła | treść zadania pkt 9; OWASP LLM06 | brak przycisku „Wyślij”; eksport do DOCX/TXT; status „e) wysłana” ustawia człowiek |
| Każde pismo to projekt | pkt 12 treści; ryzyko halucynacji | stopka „[PROJEKT … sprawdź przed podpisaniem]”, raport `raport.json` z lukami i kontrolą liczb |
| Anonimizacja to propozycja | lista UMB zawiera kategorie wymagające oceny (nr działki, sytuacja majątkowa) | szary = propozycja, ramka = do decyzji, czarny = po akceptacji |
| **Zaczernienie danych osób trzecich w udostępnianej informacji = częściowa odmowa → decyzja** | WSA Opole I SAB/Op 11/26; III OSK 1768/25 | przy finalizacji ostrzeżenie „UWAGA PRAWNA … rozważ decyzję (art. 16 UDIP)” [✔ wdrożone] |
| Funkcjonariusze publiczni nie są anonimizowani automatycznie | art. 5 ust. 2 UDIP; NSA III OSK 1855/24 | status „review” dla osób z listy `funkcjonariusze.txt` (np. Prezydent) |
| Kwalifikacja „informacja przetworzona” i odmowa nie są automatyczne | NSA III OSK 2073/22: uzasadnienie musi mieć konkrety | flaga „informacja_przetworzona?” + szablon wezwania z polem na uzasadnienie wydziału; notatka „skonsultuj z radcą” |
| Treść wniosku nie steruje modelem | OWASP LLM01 | znaczniki `<pytanie>`, `<odpowiedz_wydzialu>`, JSON, kontrola liczb, brak narzędzi |
| Dane nie wychodzą poza urząd | pkt 1 i 5 treści; RODO | tryb domyślny bez LLM; LLM tylko lokalny (`LLM_BASE_URL=localhost`) |

## Macierz ryzyk

| Ryzyko | P-stwo | Skutek | Mitygacja |
|---|---|---|---|
| Przekroczenie terminu przez błąd liczenia | niskie | skarga na bezczynność | 18 testów, dwie daty (ustawowa i bezpieczna), import wykrywa błędy arkusza |
| Wyciek danych w odpowiedzi | średnie | naruszenie RODO, upomnienie UODO (por. III OSK 8/22) | wzorce z sumami kontrolnymi, słownik imion z odmianą, lista UMB, 0 wycieków w testach; człowiek akceptuje |
| Nadmierna anonimizacja (np. nazwa ulicy, patron) | średnie | zarzut częściowej odmowy bez decyzji | reguły „św./ul./parafia”, adresy i domeny instytucji jawne, status „review” zamiast automatu |
| Halucynacja LLM w piśmie | średnie przy LLM | błędna informacja publiczna | kontrola liczb, szablon jako fallback, stopka „projekt” |
| Błędna kwalifikacja trybu | niskie | inny termin (ooś: 1 mies., petycja: 3 mies.) | flaga, nie decyzja; tabela trybów |
| Licencja zależności sprzeczna z przeniesieniem praw | niskie | problem przy umowie z Miastem | lista licencji w każdym SKILL.md, brak GPL/AGPL/LGPL |
| Upublicznienie materiałów UMB w repo zgłoszenia | średnie | naruszenie zaufania Partnera | `data-partner/` – pytanie do mentora przed upublicznieniem (README, checklista) |
