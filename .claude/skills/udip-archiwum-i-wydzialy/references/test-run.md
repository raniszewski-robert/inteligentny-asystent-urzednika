# test-run: udip-archiwum-i-wydzialy

Uruchomione 2026-11-21, Python 3.13.18, w katalogu głównym repozytorium (`bash scripts/smoke.sh` uruchamia skrót tych testów).

```
$ python3 .claude/skills/udip-archiwum-i-wydzialy/scripts/search.py data-partner/umb/archiwum_umb.jsonl --query 'liczba uczniów cudzoziemców w szkołach podstawowych' --k 3
[
  {
    "id": "BKS.IV.1431.599.2026",
    "date": "2026-09-08",
    "title": "Edytowalne zestawienie liczby uczniów oraz uczniów cudzoziemców w poszczególnych szkołach podstawowych w Bydgoszczy - stan na koniec czerwca 2026 oraz stan na wrzesień 2026.",
    "score": 12.07,
    "departments": [
      "WE"
    ],
    "matched_terms": [
      "cudzoz",
      "szkoł",
      "uczni",
      "podsta"
    ],
    "response_excerpt": ""
  },
  {
    "id": "BKS.IV.1431.307.2025",
    "date": "2025-06-25",
    "title": "Aktualne zestawienie liczby uczniów w szkołach podstawowych. Proszę też o podanie liczby obcokrajowców w poszczególnych szkołach.",
    "score": 8.38,
    "departments": [
      "WE"
    ],
    "matched_terms": [
      "szkoł",
      "uczni",
      "podsta"
    ],
    "response_excerpt": "[Odpowiedź]\nURZĄD MIASTA BYDGOSZCZY\nBiuro Komunikacji Społecznej\nBydgoszcz, dnia 8 lipca 2025 r.\nBKS.IV.1431.307.2025\nW odpowiedzi na wystosowany przez Pana wniosek o udostępnienie informacji publicznej\nw zakresie aktualnego zestawienia liczby uczniów w szkołach podstawowych, w tym podanie\nliczby ob"
  }
]
```

```
$ python3 .claude/skills/udip-dane-i-zrodla/scripts/ingest.py 'data-partner/umb/probki/Wniosek - BKS.IV.1431.599.2026.docx' --out /tmp/w599.txt && python3 .claude/skills/udip-archiwum-i-wydzialy/scripts/analyze.py /tmp/w599.txt --archive data-partner/umb/archiwum_umb.jsonl --since-days 0 --today 2026-11-22 | python3 -c "import json,sys;d=json.load(sys.stdin);print('mode',d['mode']);print('flags',[f['type'] for f in d['flags']]);print('form',d['requested_form']);[print('Q',q['no'],q['text'][:80],'->',[r['department'] for r in q['routing']]) for q in d['questions']];print('similar',[s['id'] for s in d['similar_cases']]);print('plan',d['routing_plan'])"
mode udip
flags ['informacja_przetworzona?']
form nie wskazano (art. 14 UDIP: forma zgodna z wnioskiem, gdy możliwa)
Q 1 proszę o edytowalne zestawienie liczby uczniów w poszczególnych szkołach podstaw -> ['WE', 'WOA', 'WUK']
Q 2 Proszę też przesłanie zestawienia osób-obcokrajowców w poszczególnych szkołach w -> ['WE', 'WUK', 'BBFO']
similar ['BKS.IV.1431.307.2025']
plan [{'department': 'WE', 'name': 'Wydział Edukacji i Sportu', 'questions': [1, 2]}]
```

```
$ printf 'Petycja do Rady Miasta w sprawie zmiany uchwały o parkowaniu.\n' > /tmp/pet.txt && python3 .claude/skills/udip-archiwum-i-wydzialy/scripts/analyze.py /tmp/pet.txt | python3 -c "import json,sys;d=json.load(sys.stdin);print(d['mode'],d['flags'])"
petycja [{'type': 'tryb', 'message': 'Petycja (ustawa o petycjach) – inny tryb; przekaż do Biura Rady Miasta lub właściwej komórki.'}]
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

