# T08 – Anonimizacja screen + verified exports

**Lane:** B2 – UI: letters & redaction · **Status:** done · **Estimate:** 2.5 h · **Blocked by:** T07, T27, T25

**Owns:** `app/routes/anonimizacja.py`, `app/templates/anonimizacja.html`, `app/static/redaction.js`

## Goal

Jury test 3 and the 20 % security criterion, shown live.

## Scope

- Editor: grey suggested, yellow review, black accepted; reason tooltip; badge „Wyuczone” for learned rules; select any text → „Zaznacz jako dane do ukrycia” + „Zapamiętaj na przyszłość”; on reject → „Zapamiętaj jako wyjątek (dane publiczne)”.
- Two buttons: „Eksportuj dla wnioskodawcy (.docx)” and „Eksportuj do BIP / archiwum (.docx)”, plus TXT.
- After export: badge from `export.audit_docx` („Zweryfikowano plik wyjściowy: 0 śladów…”) or blocked download listing hits; expandable XML preview showing `<w:t>██████</w:t>`; redaction footer.
- Legal advisory (non-blocking): redaction of incidental third-party data is technical; if it removes the requested information itself, a refusal decision (art. 16) may be required.
- Standalone mode for any uploaded file (what the jury will do). Status e → letter into archive.
- unslop-ui pass.

## Acceptance criteria

- [ ] `pii_torture_test.docx` and the UMB samples: 0 hits in the audit; official/address/patron untouched.
- [ ] Learning round-trip visible in this screen.

> Checkpoint 2 after this ticket and T06 are merged
