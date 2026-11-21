---
name: hn-pitch-final
description: 'Przygotowuje pitch finałowy HackNation (niedziela, finaliści 14.45, pitching od 15.15) w wariantach 3 i 5 minut, bo czasu nie podano. Daje scenariusz z demo na żywo, pomiar czasu wypowiedzi, plan awaryjny demo i odpowiedzi na pytania jury z administracji o wdrożenie, RODO, koszty, utrzymanie, integrację z systemami państwowymi, skalę i AI Act. Użyj, gdy zespół mówi „weszliśmy do finału”, „pitch”, „prezentacja dla jury”, „co jury zapyta”, „prezentacja do zgłoszenia” albo „demo się wywali”.'
---

# hn-pitch-final

## Po co

W finale wyniki etapu 1 się nie liczą: pięć zespołów z zadania zaczyna od zera, pokazuje działanie i odpowiada na pytania. W 2025 r. finalista z drugim wynikiem po etapie 1 przegrał, bo przygotował slajdy, a jury poprosiło o demo konkretnego przypadku na żywo. Zwycięzcy innego zadania wygrali rozwiązaniem wpiętym w narzędzie, którego urzędnik już używa. Ten skill buduje pitch wokół demo i przygotowuje odpowiedzi na pytania, które padają przy rozwiązaniach dla administracji.

Wnioski z 2025 r. ze źródłami: `prep/_wspolne/research/02_wnioski_z_2025.md`.

## Treści dla konkretnego Partnera

Pakiet zadania ma skill `<prefix>-demo-i-pitch` (np. w `prep/<slug>/.claude/skills/`) z językiem Partnera, jego systemami i przewidywanymi pytaniami. Załaduj go **razem** z tym skillem: ten daje strukturę i pytania ogólne, tamten treść. Jeśli pakietu nie ma, zbierz brakujące informacje od mentora Partnera w niedzielę przed 14:45 (lista w kroku 1).

## Prezentacja do zgłoszenia (niedziela, do 09:00)

Zgłoszenie wymaga prezentacji, zanim wiadomo, kto jest w finale. Zrób 4–6 slajdów według sekcji `assets/pitch-3min.md` (problem, rozwiązanie, zrzuty z demo w miejsce demo na żywo, liczby, wdrożenie) i zapisz jako PDF. W finale użyjesz tego samego szkieletu.

## Kroki

1. **Zbierz materiał (niedziela rano, 20 min).** Z pliku decyzji `godzina-zero/decyzja_<slug>.md`: kryteria z wagami i dowody. Z README: liczby z ewaluacji. Od mentora Partnera, jeśli można: jak nazywają użytkownika i problem, z jakich systemów korzystają, kto podejmie decyzję o wdrożeniu, czego się boją. Zapytaj też organizatorów o czas pitchu i sprzęt (rzutnik, złącze, internet dla finalistów).
2. **Napisz dwa warianty** z szablonów `assets/pitch-3min.md` i `assets/pitch-5min.md`. Wersja 5-minutowa to wersja 3-minutowa plus trzy bloki „+", więc ćwiczysz jedną historię. Kolejność sekcji odpowiada kryteriom o najwyższej wadze.
3. **Zmierz czas.** Przeczytaj minutę tekstu na głos, policz słowa i podaj tempo:
   ```bash
   python3 .claude/skills/hn-pitch-final/scripts/pitch_timing.py pitch-3min.md --limit 180 --wpm <twoje tempo>
   python3 .claude/skills/hn-pitch-final/scripts/pitch_timing.py pitch-5min.md --limit 300 --wpm <twoje tempo>
   ```
   Cel: co najmniej 10% zapasu. Na scenie mówi się wolniej niż na próbie, a demo trwa dłużej.
4. **Przygotuj demo z planem awaryjnym** według `references/demo-plan-b.md`: tryb `replay`, wideo z dysku, zrzuty ekranu, drugi laptop, adaptery. Każdy poziom awaryjny sprawdź raz przed 14:45.
5. **Przećwicz pytania.** Z `references/pytania-jury.md` wybierz 10 najbardziej prawdopodobnych dla tego Partnera (plus te z `<prefix>-demo-i-pitch`). Każda odpowiedź: pierwsze zdanie odpowiada wprost, drugie daje dowód albo liczbę, trzecie mówi, co zrobicie dalej. Jedna osoba zadaje pytania, druga odpowiada, trzecia mierzy czas (najwyżej 30 sekund).
6. **Dwie próby generalne** z zegarem, na sprzęcie, na którym będzie demo. Po pierwszej wytnij to, co się nie zmieściło; nie przyspieszaj mowy.
7. **Podział ról:** mówca (jedna, najwyżej dwie osoby), operator demo (nie mówi, klika), osoba od pytań technicznych, osoba pilnująca czasu, która daje znak na 30 sekund przed końcem.

## Przykład

Wejście: „Weszliśmy do finału RISK MINER. Nie wiemy, ile mamy czasu."

Wyjście (skrót odpowiedzi):

```
Organizatorzy: zapytaj na Info Point o czas i złącze; do tego czasu ćwiczymy 3 i 5 minut.
Wersja 3 min (2:38 przy Twoim tempie 125 słów/min, zapas 0:22):
  0:00 problem MFiPR: kontrolerzy ręcznie przeglądają N projektów → 0:20 rozwiązanie → 0:30 demo:
  projekt z danych Partnera, ranking ryzyka i uzasadnienie z cytatem → 1:50 F1 0,78 wobec 0,61 →
  2:10 wdrożenie: model lokalny, dane nie wychodzą z ministerstwa → 2:30 zamknięcie.
Wersja 5 min: + przypadek trudny (projekt z nietypowym budżetem), + architektura, + pilotaż.
Pytania do przećwiczenia (top 5): skąd etykiety ryzyka; co przy błędnej klasyfikacji; RODO a dane
beneficjentów; koszt utrzymania; integracja z systemem, którego używa Partner.
Plan B: replay → wideo z dysku → 4 zrzuty ekranu.
```

(Przykład ilustracyjny; liczby są zmyślone.)

## Kiedy nie używać

- Wideo do zgłoszenia (etap 1): `hn-zgloszenie` (`.claude/skills/hn-zgloszenie/assets/wideo-scenariusz.md`).
- Treść o konkretnym Partnerze: `<prefix>-demo-i-pitch` z pakietu zadania.

## Pułapki

- **Slajdy zamiast demo.** Jury z administracji chce zobaczyć działanie na przypadku Partnera. Slajdy najwyżej trzy: problem, liczby, wdrożenie.
- **Demo zależne od sieci na sali.** Tryb `replay` jako domyślny; tryb na żywo tylko, jeśli jury poprosi.
- **Odpowiedź „to tylko prototyp".** Jury ocenia potencjał wdrożenia. Mów, co jest gotowe, czego brakuje i ile to zajmie.
- **Obietnice bez pokrycia.** „Zgodne z RODO" bez wyjaśnienia jest gorsze niż „dane osobowe nie opuszczają serwera urzędu, bo model działa lokalnie".
- **Przekroczenie czasu.** Jury przerywa. Ostatnie 30 sekund to zamknięcie, nie dokończenie demo.
- **Technologia zamiast korzyści.** Nazwy bibliotek i modeli tylko w odpowiedzi na pytanie.

## Pliki

- `assets/pitch-3min.md`, `assets/pitch-5min.md`: szablony scenariusza z czasami sekcji.
- `scripts/pitch_timing.py`: czas wypowiedzi według tempa mowy i wstawek `[DEMO 60s]`, porównanie z limitem.
- `references/pytania-jury.md`: pytania jury z administracji i wzorce odpowiedzi.
- `references/demo-plan-b.md`: poziomy awaryjne demo i lista sprzętu.
- `references/test-run.md`: zapis uruchomień testowych.
