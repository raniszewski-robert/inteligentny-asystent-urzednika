# T17 – Archiwum / Baza wiedzy screen

**Lane:** B1 – UI: case flow · **Status:** done · **Estimate:** 1.5 h · **Blocked by:** T03, T25

**Owns:** `app/routes/archiwum.py`, `app/templates/archiwum.html`

## Goal

Jury test 6 and the visible learning story.

## Scope

- Search past cases (filters year, department); open a letter.
- Upload: past-case folder, laws/rulings (→ `learning.add_law`).
- Widget „Pamięć instytucjonalna”: learned PII rules, routing corrections, legal acts, archived cases, with list/delete/reset.
- unslop-ui pass.

## Acceptance criteria

- [ ] Uploading the UMB order PDF makes § 12 findable.
- [ ] Widget counts change after a correction in another screen.
