# T05 – Nowy wniosek screen (upload → security → analysis → calendar)

**Lane:** B1 – UI: case flow · **Status:** done · **Estimate:** 2 h · **Blocked by:** T04, T01

**Owns:** `app/routes/wniosek.py`, `app/templates/wniosek_nowy.html`, `app/static/scan_viewer.js`

## Goal

Jury tests 1 and 6.

## Scope

- Upload PDF/DOCX/ODT/TXT → `ingest` + `security.scan`; banners: injection neutralised (orange), hidden text, images/possible signature (amber).
- Quality < 0.5 → two panes: page images (pypdfium2) left, editable transcript right; Cloud mode button „Odczytaj pismo ręczne (AI)” (T13) with „Zweryfikuj odczyt” banner; Offline mode text pointing to manual entry.
- Analysis panel: questions, mode/flags, similar cases (older-than-a-year label), departments per question (top 3, selectable), new legal hits.
- Confirm form: number (next BKS.IV.1431.N.YYYY), received date, initials, summary → case.
- unslop-ui pass.

## Acceptance criteria

- [ ] 599.2026 DOCX → 2 questions, 307.2025, WE.
- [ ] Handwritten 16.2026 → dual pane; Cloud mode fills the transcript.
- [ ] attack_bundle.docx → 3 banners, clean analysis.
