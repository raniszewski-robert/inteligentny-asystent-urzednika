---
name: udip-kalendarz-terminy
description: Liczy terminy odpowiedzi na wnioski UDIP (14 dni, przedłużenie do 2 miesięcy, soboty i święta wg art. 57 KPA, termin bezpieczny) i prowadzi kalendarz wniosków BKS UMB – statusy a–e, kolory pilności, eksport HTML/CSV/ICS, import arkusza kalendarium UMB z wykrywaniem błędów. Użyj, gdy zespół mówi „policz termin”, „kalendarz wniosków”, „kwerenda”, „przedłużenie”, „podświetl pilne”, „zaimportuj Excel UMB” albo „10 wniosków testowych”.
---

# udip-kalendarz-terminy

Rdzeń wymagania nr 3 treści zadania („tabela zintegrowana z kalendarzem”) i testu jury nr 5. Tylko biblioteka standardowa (+ `openpyxl`, MIT, do importu XLSX).

## Skrypty

| Skrypt | Co robi |
|---|---|
| `scripts/deadlines.py` | dni wolne PL (z Wigilią od 2025), `deadline_days`, `deadline_safe`, `deadline_extended`, `urgency`; `--selftest` (18 przypadków) |
| `scripts/register.py` | model `Request`, statusy a–e, `rows()` (sortowanie od najstarszego, pilność, dni robocze), eksport `--html/--csv/--ics/--json-out`, filtr `--year` |
| `scripts/import_xlsx.py` | arkusz UMB „WNIOSKI O UDOSTĘPNIANIE INFORMACJI PUBLICZNEJ.xlsx” → JSON rejestru + raport rozbieżności; `--archive` uzupełnia wydziały z archiwum; `--demo-today` przesuwa daty, by pokazać kolory na dzień demo |

## Kroki

1. Termin pojedynczy: `python3 scripts/deadlines.py 2026-12-10` → termin ustawowy 2026-12-28, bezpieczny 2026-12-23.
2. Kalendarz demo z danymi UMB:
   ```bash
   python3 scripts/import_xlsx.py ../../../data-partner/umb/kalendarium_umb.xlsx --out /tmp/r.json --demo-today 2026-11-22
   python3 scripts/register.py /tmp/r.json --today 2026-11-22 --html kalendarz.html --ics terminy.ics
   ```
3. W aplikacji: `from register import Request, rows` → `rows(lista, today, year)` daje wiersze z polami `lp, number, received, summary, initials, status_label, extension, due, due_safe, answered, working_days_left, urgency, urgency_label, departments`. Kolory: `URGENCY_COLOR`.
4. Zmiana statusu: `req.set_status("c_kwerenda", who="AK")` dopisuje historię; status `e_odpowiedz_wyslana` ustawia datę odpowiedzi.

## Przykład wejście → wyjście

Wejście (wiersz arkusza UMB): `BKS.IV.1431.590.2026 | 2026-09-07 | termin "=E11+14" | odpowiedź 2026-09-29`
Wyjście importu: `BKS.IV.1431.590.2026: odpowiedź 2026-09-29 po terminie 2026-09-21 bez odnotowanego przedłużenia`.
Wyjście `register.py --print` (demo 22.11.2026): `1 BKS.IV.1431.293.2025 wpł. 2026-11-06 termin 2026-11-20 [overdue] b) zapytania wysłane do wydziałów`.

## Reguły (źródła: research/05)

- 14 dni od dnia złożenia, dzień wpływu się nie liczy; koniec w sobotę lub dzień ustawowo wolny przesuwa się na następny dzień roboczy (art. 57 § 4 KPA). Orzecznictwo nie przesądza tego dla UDIP, więc `due_safe` = ostatni dzień roboczy przed 14. dniem. **Planuj wysyłkę według `due_safe`.**
- Przedłużenie (kwerenda): maks. 2 miesiące od złożenia (art. 13 ust. 2), z powiadomieniem przed upływem 14 dni; dłuższe jest obcinane z ostrzeżeniem.
- Pilność: `overdue`, `today`, `tomorrow` (dziś = ostatni dzień roboczy przed terminem; to „dzień poprzedzający” z treści), `soon` (≤3 dni robocze), `ok`, `done`.

## Kiedy nie używać

- Do terminów innych trybów (ooś: 1 miesiąc, petycje: 3 miesiące, skargi KPA: 1 miesiąc) – `deadline_extended(months=…)` policzy datę, ale tryb rozpoznaje `udip-archiwum-i-wydzialy`.
- Dzień wolny za święto w sobotę (np. 26.12.2026) nie jest „ustawowo wolny”: jeśli UMB go ustala, dopisz datę do `polish_holidays` w konfiguracji (pytanie do mentora w research/03).

## Pułapki

- Excel UMB liczy `=E+14` bez przesunięcia; nie kopiuj tej logiki.
- Arkusz UMB ma **same zamknięte sprawy**: bez `--demo-today` kalendarz pokazuje 10× „zakończony” (filtr roku działa: 2025 → 2 sprawy). `--demo-today` zmienia daty wpływu (także spraw z 2025) – w demo mów, że to dane UMB z przesuniętymi datami (`notes` ma `[DEMO]`).
- Część „rozbieżności” importu wynika z naszej interpretacji art. 57 § 4 KPA; przy BKS nie nazywaj ich błędami.
- Kolumna „Osoba odpowiedzialna” w UMB to „Pracownik 1/2”, nie inicjały; import przepisuje wartość, gdy nie da się zrobić inicjałów.

Wyniki uruchomień: `references/test-run.md`.
