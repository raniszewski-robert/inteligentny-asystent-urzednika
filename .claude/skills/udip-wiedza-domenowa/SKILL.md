---
name: udip-wiedza-domenowa
description: Wiedza domenowa o obsłudze wniosków o dostęp do informacji publicznej w Urzędzie Miasta Bydgoszczy – słownik (AIP, BKS, kwerenda, informacja przetworzona, odesłanie, decyzja), podstawy prawne z numerami artykułów, role z Zarządzenia Prezydenta 2024, typy pism BKS, kluczowe liczby i typowe pomyłki. Użyj, gdy zespół pyta „co to jest kwerenda”, „kto podpisuje”, „jaki artykuł”, „czy to informacja przetworzona”, „jak UMB to robi dziś”, albo pisze teksty do UI, prezentacji lub README.
---

# udip-wiedza-domenowa

Jedna wersja prawdy to `research/01` (Partner, proces) i `research/05` (prawo); tu jest skrót do pracy w trakcie hackathonu. Słownik i pomyłki: `references/slownik.md`.

## Proces UMB w 6 zdaniach (Zarządzenie 2024, § 9–12)

1. Wniosek wpływa dowolnym kanałem i trafia do **AIP** w **Biurze Komunikacji Społecznej**, który go rejestruje (znak `BKS.IV.1431.<nr>.<rok>`; rejestracja w SIDAS).
2. AIP przekazuje zakres pytań **właściwym wydziałom** i wyznacza im termin.
3. Wydział przygotowuje **projekt odpowiedzi w swojej części**, sam anonimizuje i odsyła na bip@um.bydgoszcz.pl.
4. Przy informacji przetworzonej wydział dołącza uzasadnienie; przy odmowie przygotowuje projekt decyzji.
5. AIP składa pismo BKS („Ad 1…Ad N”, „Łączę wyrazy szacunku”) i wysyła; decyzje podpisuje Prezydent lub upoważnione osoby.
6. Informacji opublikowanej w BIP się nie udostępnia na wniosek, tylko wskazuje dokładny adres (§ 8).

## Liczby i terminy (źródła w research/05)

| Co | Wartość | Podstawa |
|---|---|---|
| Termin odpowiedzi | 14 dni od złożenia | art. 13 ust. 1 UDIP |
| Przedłużenie | do 2 miesięcy od złożenia, powiadomienie przed upływem 14 dni | art. 13 ust. 2 |
| Doprecyzowanie (praktyka UMB) | 7 dni na odpowiedź, potem bez rozpoznania | pismo 509.2026 |
| Opłata, forma | powiadomienie w 14 dni | art. 15 ust. 2, art. 14 ust. 2 |
| Odwołanie od decyzji | 14 dni na wniesienie; organ rozpatruje w 14 dni | art. 129 § 2 KPA, art. 16 ust. 2 UDIP |
| Organ odwoławczy | SKO w Bydgoszczy | BIP UMB [✔] |
| Inne tryby | ooś 1 mies., petycja 3 mies., skarga KPA 1 mies., interpelacja radnego 14 dni | research/05 |

## Słowa, których używa UMB (do UI i pitchu)

„wniosek o udostępnienie informacji publicznej”, „komórka merytoryczna”, „jednostka merytoryczna”, „kwerenda”, „doprecyzowanie zakresu wniosku”, „nie jest dysponentem wnioskowanych danych”, „Ad 1”, „AIP”, „Pracownik 1/2” (osoba odpowiedzialna), „data wpływu”, „termin odpowiedzi”, „pozostało dni”.

## Przykład wejście → wyjście

Pytanie zespołu: „Wniosek pyta o liczbę decyzji o wycince drzew za 10 lat w podziale na dzielnice. Co robimy?”
Odpowiedź skilla: to kandydat na **informację przetworzoną** (zestawienie, wiele lat, podział): flaga w `analyze.py`, decyzję podejmuje wydział z uzasadnieniem konkretów (liczba decyzji, nakład pracy; NSA III OSK 2073/22), szablon `przetworzona` w `udip-projekty-odpowiedzi`. Termin 14 dni biegnie dalej; przy braku wykazania interesu – decyzja odmowna (art. 16), przygotowuje wydział.

## Kiedy nie używać

Do rozstrzygania konkretnych spraw za urzędnika. To słownik i ściąga, nie porada prawna.

## Typowe pomyłki

Lista w `references/slownik.md` § „Pomyłki”, m.in. art. 127 vs 129 KPA, „przetworzona” vs „wymaga zebrania”, zaczernienie bez decyzji, liczenie terminu od rejestracji zamiast wpływu.
