---
name: udip-ewaluacja
description: Mierzy jakość asystenta UDIP i odtwarza test jury – testy akceptacyjne 6 kroków z treści zadania na danych UMB, ewaluacja leave-one-out na 10 sprawach UMB (podobne sprawy, wydział), metryki na danych syntetycznych (hit@5, MRR, top-1/3 wydziału, P/R/F1 anonimizacji, wycieki) i generator danych syntetycznych ze złotymi etykietami. Użyj, gdy zespół mówi „czy działa”, „przetestuj jak jury”, „jaki mamy wynik”, „sprawdź anonimizację”, „wygeneruj dane testowe” albo „smoke test przed demo”.
---

# udip-ewaluacja

Jury nie zapowiada metryki liczbowej; sprawdza 6 rzeczy z sekcji 6 treści. Ten skill daje (1) zielone/czerwone dla każdej z nich, (2) liczby do pitchu i do pilnowania regresji.

## Skrypty

| Skrypt | Dane | Wynik 21.11.2026 |
|---|---|---|
| `scripts/acceptance.py --repo <repo> [--today]` | `data-partner/umb/` | 11/11 testów na prawdziwej ścieżce (pełne archiwum, okno 365 dni), w tym kontrola halucynacji liczb (kod wyjścia 0) |
| `scripts/evaluate_partner.py <archiwum_umb.jsonl>` | 10 spraw UMB, leave-one-out | bliźniak w top 3: 5/6; wydział top-1 6/9, top-3 8/9 |
| `scripts/evaluate.py --data <katalog> --today 2026-11-22` | `data-samples/syntetyczne/` | hit@5 0,88, MRR 0,76; wydział 0,90/1,00; anonimizacja P 0,99, R 1,00, F1 0,99, 0 wycieków; zbiór odłożony (seed 7): hit@5 0,88, wydział 0,75/1,00, P 0,99; skala 5000 spraw: hit@5 0,75, zapytanie 10 ms |
| `scripts/gen_synthetic.py --out <katalog> --today <data> --n 90 --seed 2026` | generuje archiwum, testy, PII ze złotymi spanami, 10 wniosków kalendarza | deterministyczny |

## Kroki

1. Przed każdym demo i po każdej większej zmianie: `bash scripts/smoke.sh` w katalogu głównym repo (wszystkie selftesty + akceptacja).
2. Gdy UMB da nowe sprawy: odtwórz archiwum (`udip-dane-i-zrodla`), uruchom `evaluate_partner.py`, dopisz pary „bliźniaków” do `TWINS`.
3. Gdy jury lub mentor da plik z danymi osobowymi: dopisz złote spany do `pii/gold.json` w formacie `{file, spans:[{start,end,type,text}]}` i uruchom `evaluate.py`.

## Przykład wejście → wyjście

Wejście: `python3 scripts/acceptance.py --repo ../../..`
Wyjście (skrót): `| 2. Projekt pisma z odpowiedzi wydziałów (543.2026) | ✅ | pytań=5, luki=[], … „839 psom” w Ad 3=True, niepewne przypisania=2 |` … `| 2b. Kontrola halucynacji liczb | ✅ | odrzucone: ['3143', '560 (psa… zamiast kot…)', '839 (kot… zamiast pso…)'] |`.

## Kiedy nie używać

Do udowadniania jakości przed jury samymi liczbami syntetycznymi: testy syntetyczne to parafrazy naszych szablonów, a wagi tras strojone na nich. W pitchu podawaj wyniki UMB (5/6, 8/9) jako główne.

## Pułapki

- `--today` zmienia wynik kalendarza i filtrów roku; w niedzielę 22.11 poziom „today” jest niemożliwy (termin nie wypada w niedzielę), stąd w teście wystarczy „today” albo „tomorrow”.
- Test 2 sprawdza frazy i miejsce „839 psom”, a nie zgodność wszystkich „Ad” z pismem BKS (2 zdania są gdzie indziej niż u BKS – znane ograniczenie, `udip-projekty-odpowiedzi`).
- Bliźniak 509↔590 w arkuszu UMB nazywa się „Astoria”, ale wniosek 509 dotyczy terenu po budynku Astrum: to różne tematy, pudło jest uzasadnione.
- Generator nadpisuje `data-samples/syntetyczne/`; zmiana seeda zmienia złote etykiety.

Wyniki uruchomień: `references/test-run.md`.
