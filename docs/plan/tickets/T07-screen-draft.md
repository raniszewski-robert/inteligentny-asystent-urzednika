# T07 – Projekt pisma screen

**Lane:** B2 – UI: letters & redaction · **Status:** done · **Estimate:** 2.5 h · **Blocked by:** T03, T02, T24

**Owns:** `app/routes/projekt.py`, `app/templates/projekt.html`, `app/static/ad_editor.js`

## Goal

Jury test 2: department answers → correct, checkable draft.

## Scope

- Render `make_draft()`: letter, report panel (gaps, warnings, number check, omitted numbers, internal notes).
- Tray „Wymaga przypisania”: unassigned sentences with buttons [→ Ad 1] … [Notatka wewnętrzna / Pomiń]; reassignment updates draft and export.
- Click any sentence → source passage highlighted in a side panel; badge „Zweryfikowano liczby: X/X zgodne ze źródłem” bound to the real check.
- Letter type switch with its fields; free edit; versions.
- Build against `tests/fixtures/draft_543.json` first. unslop-ui pass.

## Acceptance criteria

- [ ] 543 with filled forms: Ad 1–5 like BKS's letter, tray empty.
- [ ] 543 raw replies: 2 sentences in the tray, 1-click fix.
- [ ] Clicking a sentence shows its source.
