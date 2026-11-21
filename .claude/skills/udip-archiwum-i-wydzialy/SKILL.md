---
name: udip-archiwum-i-wydzialy
description: Analizuje wniosek UDIP – wyciąga pytania, rozpoznaje tryb (UDIP, petycja, ooś, ponowne wykorzystanie, radny, akta KPA), flaguje informację przetworzoną, BIP i dane osobowe – szuka podobnych spraw w archiwum odpowiedzi (BM25, offline, filtr ostatniego roku) i proponuje ścieżkę do wydziałów UMB per pytanie (46 komórek z BIP). Użyj, gdy zespół mówi „znajdź podobne wnioski”, „przeszukaj archiwum”, „który wydział”, „ścieżka do wydziału”, „rozbij wniosek na pytania” albo „czy to w ogóle UDIP”.
---

# udip-archiwum-i-wydzialy

Wymagania 5 (przeszukiwanie archiwum) i 6 (wskazywanie ścieżki) oraz test jury nr 1. Tylko biblioteka standardowa.

## Skrypty i dane

| Plik | Co robi |
|---|---|
| `scripts/textpl.py` | tokenizacja PL, stop-lista (z formułami wniosków), stemming: obcięcie końcówki + 6 znaków |
| `scripts/search.py` | `Archive(records).search(tekst, k, since)` – BM25 po tytule, pytaniach i odpowiedzi; nagłówki wniosków pomijane |
| `scripts/analyze.py` | `analyze(tekst, archive, deps, today, since_days=365, exclude_id=None)` → JSON (pomija samą sprawę: ten sam numer albo identyczny tekst; gdy w oknie roku pusto, zwraca starsze z `older_than_window`; BKS nie jest proponowany, bo to koordynator): `mode, flags, requested_form, questions[{no,text,routing}], similar_cases, departments_overall, routing_plan` |
| `udip/data/departments.json` | 29 komórek UMB (19 wydziałów, 10 biur) i 17 jednostek miejskich: `id, name, type, url, scope, keywords` (BIP UMB 21.11.2026; słowa kluczowe ułożone ręcznie) |

Archiwum: JSONL z polami `id, date, title, request_text, response_text, departments`. Archiwum UMB: `data-partner/umb/archiwum_umb.jsonl`; przykładowe: `data-samples/syntetyczne/archiwum.jsonl`. Z katalogu plików: `udip-dane-i-zrodla/scripts/ingest.py --archive`.

## Kroki

```bash
python3 scripts/analyze.py wniosek.txt --archive ../../../data-partner/umb/archiwum_umb.jsonl --today 2026-11-22 --since-days 365
python3 scripts/search.py ../../../data-partner/umb/archiwum_umb.jsonl --query "liczba uczniów cudzoziemców szkoły podstawowe"
```

## Przykład wejście → wyjście

Wejście: wniosek UMB 599.2026 („edytowalne zestawienie liczby uczniów… zestawienie osób-obcokrajowców”).
Wyjście (skrót, pełne archiwum UMB, okno 365 dni, 22.11.2026): `questions: 2`, `similar_cases: [BKS.IV.1431.307.2025 (older_than_window)]`, `departments_overall: WE, WOA, WUK`.

Wyniki na danych UMB (leave-one-out): bliźniacza sprawa w top 3 w 5/6 przypadków, prawdziwy wydział top-1 6/9, top-3 8/9 (`udip-ewaluacja/scripts/evaluate_partner.py`).

## Kiedy nie używać

- Do ostatecznej kwalifikacji trybu i informacji przetworzonej: to flagi do decyzji urzędnika i radcy (NSA III OSK 2073/22 wymaga konkretnego uzasadnienia).
- Gdy archiwum ma tysiące spraw z różnym słownictwem (synonimy): dodaj embeddingi `sdadas/mmlw-retrieval-e5-base` (Apache-2.0) w hybrydzie z BM25 (research/04, wariant C).

## Pułapki

- Biuro Komunikacji Społecznej (BKS) jest koordynatorem, więc `route()` go nie proponuje (`COORDINATOR`).
- Plan wysyłki (`routing_plan`) bierze tylko pierwszy wydział każdego pytania: dla 543.2026 wszystkie 5 pytań idzie do WGK, a Schronisko jest dopiero drugie. W UI pokaż top 3 per pytanie i pozwól zaznaczyć kilka.
- Sprawy kierowane poza UMB (np. Wojewódzki Konserwator Zabytków, ZDMiKP z własnym BIP) wymagają pisma „odesłanie art. 4 ust. 3”; w archiwum UMB oznaczone `ZEWN-*`.
- Wagi tras (słowo kluczowe 1,5, podobna sprawa 1,0) i słowa kluczowe WOS/WOA dostroiliśmy na danych syntetycznych (zbiór odłożony: top-1 0,75), a WGK uzupełniliśmy na podstawie pism UMB 293/543 (`keywords_evidence`). Dalej stroić tylko pod nowe sprawy UMB.
- Skala: 5000 spraw – zapytanie 10 ms, ale hit@5 spada do 0,75; wniosek z dwoma tematami dostaje podobne sprawy głównie dla jednego (patrz podobne per pytanie w `questions[].routing`).
- `--since-days 365` odpowiada „wnioskom z ostatniego roku” z instrukcji Partnera; dla małego archiwum UMB użyj `0` (bez filtra).

Wyniki uruchomień: `references/test-run.md`.
