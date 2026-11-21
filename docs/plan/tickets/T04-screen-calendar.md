# T04 – Kalendarz screen

**Lane:** B1 – UI: case flow · **Status:** done · **Estimate:** 2 h · **Blocked by:** T03, T02

**Owns:** `app/routes/kalendarz.py`, `app/templates/kalendarz*.html`

## Goal

Jury test 5: oldest → newest, urgent highlighted, stages visible.

## Scope

- Table (UMB columns + status, kwerenda, termin, termin bezpieczny, dni robocze, wydziały, terminy wydziałów); colours: po terminie, dziś, jutro, ≤3 dni, kwerenda, zakończone; counters; year filter.
- Toggle „Widok demo (daty bieżące)” vs „Dane historyczne UMB”, clearly labelled.
- Inline status a–e with history and initials; extension days for c.
- XLSX import with audit card „Zaimportowano N spraw · Wykryto M rozbieżności” listing each.
- Risk button when ≤3 working days left or a department sub-deadline passed with answers missing: „Ryzyko terminu – przygotuj przedłużenie (art. 13 ust. 2)” → opens Projekt pisma with type `przedluzenie`.
- Ustawienia section „Dni wolne urzędu” (add/remove dates; statutory holidays pre-seeded).
- CSV export (ICS deferred). unslop-ui pass.

## Acceptance criteria

- [ ] 10 UMB cases in demo view with ≥4 urgency colours; historic view shows them closed; year filter works.
- [ ] Import shows 6 discrepancies.
- [ ] Adding a day off moves an affected deadline.
