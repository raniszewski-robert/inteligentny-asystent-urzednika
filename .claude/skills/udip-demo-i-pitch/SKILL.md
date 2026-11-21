---
name: udip-demo-i-pitch
description: Scenariusz demo, wideo do 3 minut i prezentacji do 10 slajdów dla zadania „Inteligentny asystent urzędnika” (UMB) – słownictwo BKS, kolejność pokazu na danych UMB (kalendarz, wniosek 293/543, pismo, anonimizacja, offline), wymagane elementy prezentacji z treści zadania, pytania jury z UMB z odpowiedziami i argumenty o wdrożeniu w Bydgoszczy. Użyj, gdy zespół mówi „demo”, „nagrajmy wideo”, „slajdy”, „pitch dla Bydgoszczy”, „co zapyta jury” albo „jak pokazać anonimizację”. Ogólne zasady pitchu: hn-pitch-final, zgłoszenia: hn-zgloszenie.
---

# udip-demo-i-pitch

Ogólne zasady (czas, technika nagrania, HackTribe) są w skillach wspólnych `hn-pitch-final` i `hn-zgloszenie`. Tu tylko to, co specyficzne dla UMB. Plan godzinowy, scenariusz wideo i 10 pytań jury: `research/07`.

## Wymogi z treści zadania (sekcja 4)

- Film **maks. 3 minuty**; celujemy w 2:00–2:30 (HackNation zaleca do 2 min).
- Prezentacja **maks. 10 slajdów**; obowiązkowe treści i nasz slajd:

| # | Treść wymagana przez UMB | Nasz dowód |
|---|---|---|
| 1 | nazwa projektu, zespół | — |
| 2 | problem: czas urzędnika, ochrona danych | arkusz UMB: 6 rozbieżności do sprawdzenia; 266 940 wniosków w 2025 r. w Polsce [~] |
| 3 | jak wyszukuje archiwalne sprawy | 599.2026 → 307.2025 (ten sam temat rok wcześniej) |
| 4 | jak anonimizuje | lista UMB (28 pozycji) → wzorce, słownik, „do decyzji”; szary → czarny; 0 wycieków na danych testowych |
| 5 | jak działa kalendarz | 10 spraw UMB, kolory, statusy a–e, dwie daty terminu |
| 6 | „jak to działa” (wgranie PDF/Word → projekt) | wideo/demo na 543.2026 |
| 7 | dla kogo: urzędnicy JST | AIP w BKS, wydziały |
| 8 | przyszłość w UMB | serwer w intranecie, import Excela, „uczenie się” przez archiwum |
| 9 | narzędzia (i rozwiązania zewnętrzne – Regulamin § 4 ust. 1) | lista bibliotek z licencjami; pakiet przygotowany przed wydarzeniem |
| 10 | **offline i konkretny model lokalny** | Bielik-11B-v3.1-Instruct (Apache-2.0); działa też bez modelu |

## Kolejność demo na żywo (4 min)

1. Kalendarz: „to są Wasze sprawy z arkusza, daty przesunięte na dziś” (czerwone, pomarańczowe, kwerenda).
2. Wgraj `Wniosek - BKS.IV.1431.599.2026.docx`: 2 pytania, podobna sprawa 307.2025 z zeszłego roku, wydział WE. (Zapas: 293.2025 → WGK i Schronisko.)
3. Wgraj odpowiedzi wydziałów (przypadek 543): pismo „Ad 1…Ad 5” w stylu BKS; pokaż kontrolę liczb i przeniesienie zdania między „Ad” (urzędnik poprawia projekt).
4. Anonimizacja: plik z PESEL, adresem, „ur. … w Toruniu” i podpisem → szary; akceptacja → czarny DOCX; ostrzeżenie o decyzji.
5. Wyłącz Wi-Fi: wszystko dalej działa. Slajd z modelem lokalnym.

Mów słowami UMB: „komórka merytoryczna”, „kwerenda”, „doprecyzowanie”, „AIP”, „Ad 1”, „nie jest dysponentem”.

## Przykład wejście → wyjście

Pytanie jury: „Co, jeśli model wymyśli kwotę?”
Odpowiedź: „Pokażę. [atrapa modelu `mock_llm.py bad` wpisuje 999 999 zł] Narzędzie odrzuca akapit, bo tej liczby nie ma w odpowiedzi wydziału, i wraca do szablonu. To samo, gdy model zamieni psy z kotami. Na prawdziwym Bieliku tego jeszcze nie mierzyliśmy.”

## Argumenty o wdrożeniu w Bydgoszczy

- Bez integracji z SIDAS (zgodnie z pkt 11), ale z importem obecnego arkusza XLSX: zero migracji.
- Jeden proces Python, licencje MIT/BSD/Apache: Miasto może przejąć prawa (Regulamin § 4) bez konfliktu licencji.
- Pasuje do Zarządzenia 2024: role AIP i wydziałów, anonimizacja w wydziale, decyzje poza narzędziem.
- Model lokalny opcjonalny: wdrożenie etapami (rejestr → archiwum → generator → LLM).

## Kiedy nie używać

Do ogólnych pytań o HackTribe, wideo i pitch (`hn-zgloszenie`, `hn-pitch-final`). Do faktów prawnych (`udip-wiedza-domenowa`).

## Pułapki

- Odpowiedzi wydziałów w przypadku 543 **odtworzyliśmy** z pisma BKS; powiedz to, gdy jury zapyta.
- Nie obiecuj odczytu rękopisów: pokaż ostrzeżenie dla 16.2026.
- Liczby syntetyczne (F1 0,99) podawaj z zastrzeżeniem; główne są wyniki na danych UMB.
- Materiały UMB w publicznym repo dopiero po zgodzie mentora.
