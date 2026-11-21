---
name: udip-anonimizacja
description: Wykrywa i redaguje dane osobowe w wnioskach i odpowiedziach UDIP według listy UMB „Dane podlegające anonimizacji” – PESEL, NIP, REGON, IBAN, dowód (z sumami kontrolnymi), e-mail, telefon, adres, imię i nazwisko z odmianą, data i miejsce urodzenia, nr działki, dane szczególne. Daje propozycje (szary), decyzje (ramka) i redakcję po akceptacji (czarny). Użyj, gdy zespół mówi „zanonimizuj”, „ukryj dane osobowe”, „zaczernij”, „test anonimizacji”, „szary na czarny” albo „czy coś wycieka”.
---

# udip-anonimizacja

Wymaganie nr 4 treści i test jury nr 3; kryterium „Bezpieczeństwo i skuteczna anonimizacja” (20%). Tylko biblioteka standardowa.

## Jak działa

`scripts/anonymize.py` łączy cztery detektory i zwraca spany `{id, start, end, text, type, confidence, reason, status}`:
1. **Wzorce z walidacją**: PESEL (suma i data), NIP, REGON 9/14, IBAN PL (mod 97), dowód osobisty (suma), paszport, e-mail, telefon, kod pocztowy z miejscowością, adres (ul./al./os./pl. + numer), księga wieczysta, nr rejestracyjny.
2. **Osoby**: słownik imion (`udip/data/imiona.txt`) z generowaną odmianą (Jan/Janem, Anna/Annę) i słownik T28 (`udip/data/names/`: 3 807 imion, 12 596 nazwisk polskich, ukraińskich i rosyjskich z odmianą; nieznane imię + nazwisko ze słownika; formy wieloznaczne, np. „Mieszka”, tylko w parze), „Pan/Pani X”, podpis po „Z poważaniem”, inicjał + nazwisko („E. Góra”), imiona WIELKIMI LITERAMI, końcówki nazwisk (-ski, -cka, -wicz) jako „review”.
3. **Lista UMB**: data i miejsce urodzenia, nr działki, zdania o zdrowiu, pomocy społecznej, karalności, poglądach, sytuacji rodzinnej i majątkowej (`udip/data/kategorie_szczegolne.txt`) → „review”.
4. **Wyjątki jawne**: adresy i domeny instytucji (`jawne_adresy.txt`, `jawne_domeny.txt`), patroni i ulice („św. Maksymiliana Kolbego”, „ulicy Fordońska”), osoby pełniące funkcje publiczne (`funkcjonariusze.txt`, z odmianą: Bruskiego) → „review”, nie automat (art. 5 ust. 2 UDIP).

Statusy: `suggested` (szary), `review` (ramka, decyduje urzędnik), `accepted` (czarny), `rejected` (jawne).

## Kroki

```bash
python3 scripts/anonymize.py detect plik.txt --out spans.json --html podglad.html [--keep "Jan Nowak"]
python3 scripts/anonymize.py apply plik.txt spans.json --out wynik.txt --mode label|block [--accept-all]
python3 scripts/anonymize.py --selftest
```
W aplikacji: `from anonymize import detect, apply, preview_html`. Edytor: kliknięcie w `<mark data-id>` zmienia status, potem `apply`. Dokument DOCX z szarym/czarnym tworzy `udip-projekty-odpowiedzi/scripts/draft.py`.

## Przykład wejście → wyjście

Wejście: `Pan Jan Kowalski, ur. 12.03.1980 r. w Toruniu, korzysta z zasiłku z MOPS. Właściciel działki nr 123/4 jest chory. Sprawę zgłosił J. Nowak.`
Wyjście (typ, tekst, status): `OSOBA „Jan Kowalski” suggested`; `URODZENIE „ur. 12.03.1980 r. w Toruniu” suggested`; `SZCZEGOLNE_POMOC_SPOLECZNA (całe zdanie) review`; `SZCZEGOLNE_ZDROWIE (zdanie) review`; `DZIALKA „123/4” review`; `OSOBA „J. Nowak” review`.

## Pokrycie listy UMB (28 pozycji, `data-partner/umb/dane_podlegajace_anonimizacji_UMB.txt`)

| Pozycje listy | Jak |
|---|---|
| imię i nazwisko, PESEL, dowód/paszport, NIP, data i miejsce urodzenia, adres, telefon, e-mail, rachunek, nr KW, nr działki, nr rejestracyjny | wzorce i słowniki → `suggested` (działka → `review`) |
| stan cywilny i rodzina, zdrowie, majątek i dochody, pomoc społeczna, poglądy, przynależność, karalność | zdania ze słowami kluczowymi → `review` (`kategorie_szczegolne.txt`) |
| pochodzenie rasowe/etniczne, orientacja seksualna | **brak** reguł – dopisać słowa do `kategorie_szczegolne.txt` po konsultacji z IOD |
| podpis (parafka), wizerunek | **nie dotyczy tekstu** – tylko skany/obrazy, poza zakresem |
| tajemnica przedsiębiorstwa, skarbowa, bankowa, zawodowa, informacje niejawne | **nie do wykrycia wzorcem** – ocena wydziału (Zarządzenie § 11 ust. 8) |

## Jakość (21.11.2026, `udip-ewaluacja`)

Syntetyczne 40 dok., 144 spany: P 0,99, R 1,00, F1 0,99, 0 wycieków (zbiór odłożony, seed 7: P 0,99, R 1,00). Na 10 prawdziwych wnioskach UMB: wykrywa „Ewa Góra”, „E. Góra”, „JERZY” (rękopis), „abcxyz@jahu.komm”; nie oznacza „św. Maksymiliana Kolbego” ani bip@um.bydgoszcz.pl. Zbiór syntetyczny pisaliśmy sami, więc to górna granica; jury sprawdzi własnym plikiem.

## Kiedy nie używać

- Do decyzji, czy dane są jawne (funkcjonariusz publiczny, kontrahent gminy): to ocena prawna. Narzędzie daje „review”.
- Do skanów bez warstwy tekstu: najpierw `udip-dane-i-zrodla/scripts/ingest.py` (OCR). Zaczernianie w PDF-obrazie nie jest zaimplementowane.
- Do tajemnicy przedsiębiorstwa i informacji niejawnych z listy UMB: nie da się ich wykryć wzorcem; zostają w ocenie wydziału (Zarządzenie § 11 ust. 8).

## Pułapki

- **Zaczernienie danych osób trzecich w udostępnianej informacji to częściowa odmowa i wymaga decyzji** (WSA Opole I SAB/Op 11/26; research/05). `draft.py --finalize` drukuje ostrzeżenie.
- Pismo do wysyłki zachowuje dane adresata; wersja do archiwum/BIP je redaguje. Nie myl wersji.
- Słownik nie zna wszystkich nazwisk (12 596). Rzadkie nazwisko z rzadkim imieniem bez „Pan/Pani” zostanie pominięte. Rozszerzenie: lista PESEL z dane.gov.pl w `scripts/build_names.py` albo GLiNER `flowxai/cee-pii` (Apache-2.0; research/04).
- Nie dodawaj modeli spaCy `pl_core_news_*`: licencja GPL-3.0 koliduje z przeniesieniem praw.

Wyniki uruchomień: `references/test-run.md`.
