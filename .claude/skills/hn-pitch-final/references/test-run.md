# Zapis uruchomień testowych: hn-pitch-final

Data: 2026-11-17, Python 3.13.18, Linux.

## pitch_timing.py

| Przypadek | Polecenie | Wynik |
|---|---|---|
| Szablon 3 min | `pitch_timing.py assets/pitch-3min.md --limit 3:00` | 6 sekcji, demo 70 s ze wstawki; razem 2:01, zapas 0:59; kod 0 |
| Szablon 5 min | `pitch_timing.py assets/pitch-5min.md --limit 300` | 9 sekcji, wstawki 80 s i 30 s; razem 2:56, zapas 2:04; kod 0 |
| Szablon 5 min przy limicie 3 min | `--limit 180` | Zapas 0:04, poniżej 10%: „wytnij około 32 słów"; kod 1 |
| Sekcja 260 słów przy planie 0:20, tempo 120 | `--limit 180 --wpm 120` | Sekcja oznaczona „ZA DLUGO", razem 3:10, limit przekroczony; notatka `>` pominięta; kod 1 |

Szablony dają krótkie czasy, bo pola `{{...}}` zastępują prawdziwy tekst. Po wypełnieniu każda sekcja powinna zbliżyć się do czasu w nawiasie.

Fragment:

```
Sekcja                              slowa  wstawki   czas   plan
Problem                               260       0s   2:10   0:20  ZA DLUGO
Demo                                    0      60s   1:00   1:00

Razem: 3:10 przy 120 slowach/min; limit 3:00; zapas 0:10 (PRZEKROCZONY).
```

## Czego nie testowano

Tempo domyślne 130 słów na minutę to założenie [?]. Zmierz własne tempo na próbie.
