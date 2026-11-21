# T06 – Sprawa screen

**Lane:** B1 – UI: case flow · **Status:** done · **Estimate:** 2 h · **Blocked by:** T05, T24

**Owns:** `app/routes/sprawa.py`, `app/templates/sprawa.html`

## Goal

One place for a case, including the BKS → department workflow.

## Scope

- Header: deadlines (statutory + safe), status, days left, department sub-deadlines.
- Questions with chosen departments; confirming/overriding logs `routing_feedback` (shows learned boosts).
- Per department: „Przygotuj przekazanie do wydziału” → copy message + download reply form; „Oznacz jako przekazane” → status b + sub-deadlines.
- Upload department answers (filled forms or free text; per-question dropzone optional).
- Similar cases: „Porównaj z zeszłym rokiem” (letters side by side) and „Użyj tej samej ścieżki wydziałów”; BIP banner when ≥2 similar in 12 months (art. 10 ust. 1 u.d.i.p.).
- History list. unslop-ui pass.

## Acceptance criteria

- [ ] Case 543: packets for WGK and Schronisko, filled forms uploaded, status b → history.
- [ ] BIP banner appears for a repeated topic.
