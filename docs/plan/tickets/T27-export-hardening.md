# T27 – Irreversible export hardening + XML leak audit + redaction footer

**Lane:** E – core: safety & learning · **Status:** done · **Estimate:** 45 min · **Blocked by:** T00

**Owns:** `udip/export.py`, `tests/core/test_export.py` (the call from `draft.write_docx`/`finalize` is pre-wired by T00)

## Goal

Make the existing zero-leak export provable on screen and in the file.

## Scope

- Accepted spans become fixed-length blocks (`██████`) so lengths don't leak (PESEL = 11).
- Scrub `docProps/core.xml` (creator, lastModifiedBy, title, subject, keywords, description) and drop comments/revisions/custom props.
- `audit_docx(bytes, secrets) -> {ok, hits[], xml_preview}`: unzip, scan every `.xml` (case-, whitespace- and diacritic-normalised).
- `metryczka(categories, initials, date)`: footer „Wyłączenie jawności” citing art. 5 ust. 2 u.d.i.p. (prywatność osoby fizycznej / tajemnica przedsiębiorcy) and other statutory secrets by category.
- Implement the functions the T00 hook in `draft.write_docx`/`finalize` already calls (two versions: do wysyłki / BIP-archiwum).

## Acceptance criteria

- [ ] Automated: export with PESEL, name, address, e-mail, IBAN → audit 0 hits, core.xml has no personal or tool metadata.
- [ ] Footer lists only categories actually redacted.
