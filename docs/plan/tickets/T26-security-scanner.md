# T26 – Ingest security scanner + prompt-injection pre-filter

**Lane:** E – core: safety & learning · **Status:** done · **Estimate:** 1.5 h · **Blocked by:** T00

**Owns:** `udip/security.py`, `tests/core/test_security.py`, `tests/fixtures/attack_bundle.docx`

## Goal

Untrusted uploads cannot steer the tool or hide content (20% security criterion; signatures and images are on UMB's list).

## Scope

- `scan(path) -> {hidden_text[], images[], injection[], notes[]}`: PDF via pdfplumber (chars < 3 pt, near-white fill ≥ 0.95, off-page); DOCX via XML (`w:vanish`, size < 6 half-points, white colour, comments, `w:del`); images in PDF pages and `word/media/*`.
- `sanitize_for_llm(text) -> (clean_text, quarantined_spans)`: PL/EN injection patterns ("zignoruj poprzednie instrukcje", "ignore previous instructions", "system prompt", role/XML spoofing tags…), logged to `security_events`.
- `ingest.read_any` already calls `security.scan` through the T00 hook (`security` key); lane C calls `sanitize_for_llm`.

## Acceptance criteria

- [ ] `attack_bundle.docx` (question + Polish injection line + white 1 pt text + embedded PNG) → 3 findings; analysis of the cleaned text keeps the real question.
- [ ] Clean UMB samples → 0 false findings except real images.
