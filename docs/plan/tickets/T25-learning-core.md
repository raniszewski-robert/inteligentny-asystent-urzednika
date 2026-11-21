# T25 – Learning from clerk corrections (3 feedback loops)

**Lane:** E – core: safety & learning · **Status:** done · **Estimate:** 1.5 h · **Blocked by:** T02

**Owns:** `udip/learning.py`, `tests/core/test_learning.py` (hooks in `anonymize.detect` / `analyze.route` are pre-wired by T00)

## Goal

Make „uczy się na podstawie wgrywanych danych” real, offline and auditable.

## Scope

- `learned_pii_rules`: `remember(phrase, action allow|redact, category, case, by)`; `detect` applies them first (allow beats patterns; redact adds `suggested` spans with reason „Wyuczone z korekty urzędnika”).
- `routing_feedback`: `log_routing(question, predicted, confirmed, case)`; `route` adds a boost from similar confirmed questions with reason „Wzmocnione przez N korekt urzędnika”.
- Laws/rulings: `add_law(file)` splits into `Art. / § / sygnatura` chunks into `legal_chunks`, searchable at once; `legal_hits(text)` for the case screen („Nowo dodany akt prawny”).
- `memory_stats()` and `reset(kind)` for the „Pamięć instytucjonalna” widget.

## Acceptance criteria

- [ ] Reject an official's name with „Zapamiętaj jako wyjątek” and mark „Projekt Kaskada” as business secret → next upload: official not flagged, „Projekt Kaskada” suggested with the badge.
- [ ] Override routing once → a similar question ranks the confirmed department first with the note.
- [ ] Uploaded mock amendment PDF → its article appears in `legal_hits`.
