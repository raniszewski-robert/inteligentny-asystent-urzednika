# T24 – Department dispatch packet + deterministic Ad mapping

**Lane:** A – core · **Status:** done · **Estimate:** 1.5 h · **Blocked by:** T01

**Owns:** `udip/dispatch.py`, Ad-mapping tiers in `udip/draft.py`, `tests/core/test_dispatch.py`

## Goal

Mirror the UMB order (BKS forwards questions with a deadline) and end silent Ad misplacement.

## Scope

- `sub_deadline(received, today)` = max(today + 2 working days, legal due − 3 working days), using office days off.
- `packet(case, department, questions) -> {message_text, reply_form_docx}`: copy-ready message (case number, only that department's questions, sub-deadline, reminder to return anonymised material per Zarządzenie § 11 ust. 8) and a DOCX form with `[Ad N] Pytanie: … / Odpowiedź wydziału:` blocks.
- Ad mapping tier 1: `[Ad N]`, `Ad N.`, `Ad. N` markers or per-question upload → confidence 1.0.
- Tier 2 (rules): IDF overlap with margin; below threshold → `unassigned` (never placed silently). Report lists `unassigned` sentences with source file and index (provenance).

## Acceptance criteria

- [ ] Case 543: filled reply form uploaded back → 100 % deterministic mapping.
- [x] Raw 543 replies in rules mode → none silently wrong; ambiguous ones land in `unassigned` (reworded by the coordinator 21.11: „Miasto nie zawierało umów…” → unassigned, „Umowa 1/2022/SZ” → Ad 5 as in the BKS letter, else Ad 5 would be a gap).
- [ ] Every draft sentence carries `(source_file, sentence_index)`.
