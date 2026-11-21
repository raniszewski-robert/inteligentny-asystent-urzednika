# test-run: udip-ewaluacja

Uruchomione 2026-11-21, Python 3.13.18, w katalogu głównym repozytorium (`bash scripts/smoke.sh` uruchamia skrót tych testów).

```
$ python3 .claude/skills/udip-ewaluacja/scripts/gen_synthetic.py --out data-samples/syntetyczne --today 2026-11-22 --n 90
archiwum: 90 spraw; testy: 16 wniosków; PII: 40 dokumentów; kalendarz: 10 wniosków → data-samples/syntetyczne
```

```
$ python3 .claude/skills/udip-ewaluacja/scripts/evaluate.py --data data-samples/syntetyczne --today 2026-11-22
# Wynik ewaluacji

Dane: `data-samples/syntetyczne`, dzień odniesienia 2026-11-22.

| Moduł | Metryka | Wynik |
|---|---|---|
| Podobne sprawy (ostatni rok) | hit@5 / MRR na 16 wnioskach | 0.875 / 0.76 |
| Wskazanie wydziału | top-1 / top-3 na 20 pytaniach | 0.9 / 1.0 |
| Anonimizacja | P / R / F1 na 144 spanach w 40 dok. | 0.986 / 1.0 / 0.993 |
| Anonimizacja | wycieki (≥3 jawne znaki złotego spanu) | 0 |

Per typ (tp/fp/fn): ADRES 24/1/0; EMAIL 10/0/0; KOD_MIEJSC 16/0/0; OSOBA 64/1/0; PESEL 12/0/0; TELEFON 18/0/0

Błędy wydziału (plik, pytanie, oczekiwany, top-3): wniosek_03.txt q1 WGK → ['ZDMiKP', 'WGK', 'WMG']; wniosek_15.txt q1 WOS → ['WF', 'WOS', 'BZIT']

Pominięte spany: brak
```

Zbiór odłożony (inny seed, nieużywany przy strojeniu):

```
$ python3 .claude/skills/udip-ewaluacja/scripts/gen_synthetic.py --out /tmp/held --today 2026-11-22 --n 90 --seed 7 && python3 .claude/skills/udip-ewaluacja/scripts/evaluate.py --data /tmp/held --today 2026-11-22 | sed -n 5,12p
archiwum: 90 spraw; testy: 16 wniosków; PII: 40 dokumentów; kalendarz: 10 wniosków → /tmp/held
| Moduł | Metryka | Wynik |
|---|---|---|
| Podobne sprawy (ostatni rok) | hit@5 / MRR na 16 wnioskach | 0.875 / 0.797 |
| Wskazanie wydziału | top-1 / top-3 na 20 pytaniach | 0.75 / 1.0 |
| Anonimizacja | P / R / F1 na 145 spanach w 40 dok. | 0.986 / 1.0 / 0.993 |
| Anonimizacja | wycieki (≥3 jawne znaki złotego spanu) | 0 |

Per typ (tp/fp/fn): ADRES 24/1/0; EMAIL 13/0/0; KOD_MIEJSC 16/0/0; OSOBA 64/1/0; PESEL 14/0/0; TELEFON 14/0/0
```

```
$ python3 .claude/skills/udip-ewaluacja/scripts/evaluate_partner.py data-partner/umb/archiwum_umb.jsonl
| Sprawa | Oczekiwany wydział | Propozycja (top 3) | Podobne (top 3) | Bliźniak w top 3 |
|---|---|---|---|---|
| 293.2025 | WGK, SCHRONISKO | WGK, SCHRONISKO, WIM | 543.2026 | tak |
| 307.2025 | WE | WE, WI, WUK | 599.2026, 509.2026 | tak |
| 15.2026 | ZEWN-WKZ | WAB, WF, WIM | 509.2026, 307.2025 |  |
| 16.2026 | WSO | WMG, WOA, WSO | 590.2026 |  |
| 17.2026 | ZDMiKP | WF, WK, WZP | 509.2026, 590.2026, 543.2026 |  |
| 18.2026 | WGO | WGO, ZDMiKP, WAB | 293.2025, 543.2026, 590.2026 |  |
| 509.2026 | WAB | WAB, WF, WIM | 17.2026, 599.2026, 307.2025 | NIE |
| 543.2026 | WGK, SCHRONISKO | WGK, SCHRONISKO, WIM | 293.2025 | tak |
| 590.2026 | WIM | WAB, WIM, BZIT | 509.2026, 16.2026, 18.2026 | tak |
| 599.2026 | WE | WE, WOA, WUK | 307.2025, 509.2026 | tak |

Bliźniak w top 3: 5/6. Wydział: top-1 6/9, top-3 8/9 (sprawy z wydziałem UMB).
```

```
$ python3 .claude/skills/udip-ewaluacja/scripts/acceptance.py --repo . --today 2026-11-22; echo exit=$?
Zaimportowano 3 spraw do /tmp/tmpla10wrqp/x.jsonl (błędów: 0)
# Testy akceptacyjne (scenariusz jury), 2026-11-22

| Test | Wynik | Szczegóły |
|---|---|---|
| 1. Wniosek - BKS.IV.1431.599.2026.docx: podobne sprawy / wydział | ✅ | top3=['BKS.IV.1431.307.2025']; wydziały=['WE', 'WOA', 'WUK'] (oczek. WE); pytań=2 |
| 1. Wniosek - BKS.IV.1431.293.2025.docx: podobne sprawy / wydział | ✅ | top3=['BKS.IV.1431.543.2026']; wydziały=['WGK', 'SCHRONISKO', 'WIM'] (oczek. WGK); pytań=5 |
| 1. Wniosek - BKS.IV.1431.590.2026.pdf: podobne sprawy / wydział | ✅ | top3=[]; wydziały=['WAB', 'WIM', 'BZIT'] (oczek. WIM); pytań=1 |
| 2. Projekt pisma z odpowiedzi wydziałów (543.2026) | ✅ | pytań=5, luki=[], brakujące frazy=[], liczby spoza źródeł=[], pominięte liczby=[], „839 psom” w Ad 3=True, niepewne przypisania=2 |
| 2b. Kontrola halucynacji liczb (zmyślona kwota, zamienione psy/koty) | ✅ | odrzucone: ['3143', '560 (psa… zamiast kot…)', '839 (kot… zamiast pso…)'] |
| 3. Anonimizacja pliku z danymi osobowymi | ✅ | wykryto 11, wycieki po akceptacji: brak; do decyzji urzędnika: ['J. Nowak'] |
| 4. Stabilność na wszystkich próbkach UMB | ✅ | 10 spraw + 3 plików, błędy: brak, czas 0.4 s |
| 5a. Kalendarz UMB bez zmian dat: filtr roku 2025 | ✅ | 2 sprawy z 2025 r., wszystkie zakończone (arkusz UMB ma same zamknięte sprawy) |
| 5b. Kalendarz 10 wniosków UMB w trybie demo (daty przesunięte): kolejność i podświetlenia | ✅ | poziomy=['done', 'ok', 'overdue', 'soon', 'tomorrow'], kolejność od najstarszego=True |
| 6. Import arkusza kalendarium UMB + kontrola niespójności | ✅ | zaimportowano 10, niespójności wykryte: 6 |
| 6b. Import katalogu dokumentów do archiwum | ✅ | zaimportowano 3 spraw z katalogu |
exit=0
```

