# Implementation plan v2: Inteligentny asystent urzędnika (UMB), parallel

Agreed on 21.11.2026; v2 folds in the external review (`docs/plan/review_assessment.md`). Up to **six agents** work at once in separate git worktrees, each in a **lane** that owns its files (CONTRACTS.md §1). Demo runs locally on the team's Windows laptop from D:. Deadline: Sunday 22.11, 11:00; code freeze 09:30.

**Run it in one session:** paste `docs/plan/ORCHESTRATOR_PROMPT.md` into Claude Code opened in the repo root. Standing rules for every agent: `CLAUDE.md`; lane briefs: `docs/plan/lanes/`.

## Decisions

| Area | Decision |
|---|---|
| Stack | FastAPI, Jinja2 + htmx (vendored) + small vanilla JS, SQLite (`sqlite3`), Python 3.11+ |
| Look | plain official, text header „Urząd Miasta Bydgoszczy · Biuro Komunikacji Społecznej”, no city logo; unslop-ui `--surface` on every screen + audit T18 |
| Data | real UMB data (mentors approved, also with Claude); ~20 synthetic cases for archive breadth + 5 adversarial cases |
| BKS → department workflow | dispatch packet per department (copyable message + DOCX reply form with `[Ad N]` blocks), sub-deadlines, never sent by the tool (T24, T06) |
| Ad mapping | deterministic from reply forms; otherwise rules with a margin or LLM index mapping; anything uncertain goes to a visible tray, never silently placed (T24, T07, T12) |
| Learning | 3 feedback loops in SQLite: learned PII rules, routing corrections, laws/rulings as searchable chunks; visible „Pamięć instytucjonalna” (T25, T17) |
| Security | ingest scanner (hidden text, images/signatures, prompt-injection pre-filter), tagged untrusted text, number check on every LLM output (T26, T10–T12) |
| Exports | two versions (wnioskodawca / BIP-archiwum), fixed-length blocks, metadata scrub, XML leak audit badge, redaction footer citing art. 5 ust. 2 (T27, T08) |
| Anonymization coverage | bigger name lexicon from dane.gov.pl lists (licence verified before bundling), optional local NER behind a flag (T28) |
| LLM | modes Offline – reguły / Offline – lokalny Bielik / Cloud demo – Claude Sonnet; offline enforced in code; 2 cached calls (analyze+route, draft+semantic PII) + vision for handwriting in cloud mode; disk cache; global budget $15 |
| Evaluation | 10 real UMB + 5 adversarial cases: rules vs Bielik-4.5B (CPU) vs Sonnet; one slide (T15) |
| Local model in the deck | Bielik-11B-v3.1-Instruct (Apache-2.0) for a city GPU server; Bielik-4.5B measured on CPU; offline VLM named only if its licence is verified |
| Cut | „Zapytaj archiwum” chat, Haiku comparison, 50-case suite, ICS export, canvas redactor for scans |
| Run | `setup.ps1` + `run.ps1` on D:; Tesseract optional |
| UI font (21.11, team) | Lato, vendored in `app/static/fonts/` (SIL OFL 1.1 – accepted for fonts alongside MIT/BSD/Apache for code); letter text stays Times New Roman like the DOCX |

## Lanes

| Lane | Phases and tickets | Starts after |
|---|---|---|
| **0 – coordinator** | T00, merges, checkpoints | — |
| **A – core** | A1: T01 → T02 → T24 → T28 · A2: T19 | T00 · A2 after T06 + T08 |
| **E – core: safety & learning** | E1: T27 → T26 → T25 | T00 (T25 needs T02) |
| **B1 – UI: case flow** | T03 → T04 → T05 → T06 → T17 | T00 |
| **B2 – UI: letters & redaction** | B2a: T07 → T08 · B2b: T23 → T18 | B2a after T03 · B2b after T11, T12, T13, T17 |
| **C – LLM & eval** | T10 → T16 (background) → T11 → T12 → T13 → T14 → T15 | T00 |
| **D – delivery** | D1: T09 → T29 → T21 draft · D2: T21 final → T22 | T00 · D2 after T15 + T18 |

```
T00 ─┬─ A:  T01 ─ T02 ─ T24 ─ T28 ··························· T19 ─┐
     ├─ E:  T27 ─ T26 ─ T25 (needs T02) ─────────────────────────────┤
     ├─ B1: T03 ─ T04 ─ T05 ─ T06 (T24) ─ T17 (T25) ─────────────────┤
     │         └─ B2: T07 (T02,T24) ─ T08 (T27,T25) ─ T23 ─ T18 ──────┤
     ├─ C:  T10 ─ T11 ─ T12 (T24) ─ T13 ─ T14 ─ T15   (T16 bg) ──────┤
     └─ D:  T09 ─ T29 ─ T21 draft ················· T21 final ──────┴─ T22
```

Critical path ≈ 11 h of work: T00 → T01 → T02 → T24 → T07 → T08 → T23 → T18 → T22.

## How parallel work stays safe

1. **Contracts first.** T00 freezes module APIs, schema, routes, env vars, hook points and fixtures; stubs delegate to today's tested code.
2. **File ownership** per CONTRACTS §1; `requirements.txt` append-only; cross-lane needs go through the coordinator.
3. **Branches and worktrees**, one per lane phase; rebase on `origin/main` before each ticket; only the coordinator merges (order A → E → B1 → B2 → C → D) after `smoke.sh` passes on the merged result.
4. **Waiting:** a lane whose next ticket is blocked builds against stubs where allowed, or moves to its next unblocked ticket, or reports `blocked` (`docs/plan/lanes/_rules.md`).
5. **Shared LLM budget and cache** via one absolute `UDIP_DATA_DIR`; allocation: C $9, B2/T23 $1, D (vision demo) $1, reserve $4.
6. **Git server limit:** 2 concurrent transfers per repo; push one at a time, retry once after 5 s on HTTP 429.

## Fewer agents

| Agents | Assignment |
|---|---|
| 6 | 0+D, A, E, B1, B2, C |
| 5 | 0+D, A+E, B1, B2, C |
| 4 | 0+D, A+E, B1+B2 (B1 first up to T03, then interleave), C |
| 3 | 0+A+E+D, B1+B2, C |
| 2 | 0+A+E+B1+B2+D, C |

## Checkpoints with the team (progress-based)

1. **T05 + T09 merged:** Kalendarz and Nowy wniosek run on your Windows machine.
2. **T06 + T08 merged:** full jury path works offline with rules (dispatch → reply form → draft → verified export).
3. **T15 + T21 final merged:** benchmark, deck and video script ready for review.

## If time runs short, drop in this order

GLiNER in T28 → T13 vision (manual transcription stays) → live Bielik mode in T23 (deck still shows the CPU measurement) → T16 („nie zmierzono”) → legal chunks in T25 → „Porównaj z zeszłym rokiem” in T06.

## Needed from the team

- [ ] `.env` with `ANTHROPIC_API_KEY=…` in `Hacknation 2026 - UMB\_dla_claude\` (T10).
- [ ] Confirm Python 3.11+ and Git on Windows (T09).
- [ ] For T28: download from dane.gov.pl the lists of first names and surnames from the PESEL register (CSV) into `_dla_claude\`, or allow `dane.gov.pl`.
- [ ] For T16: allow `huggingface.co`, `hf.co`, `cdn-lfs.huggingface.co`, `cdn-lfs.hf.co`, `cas-bridge.xethub.hf.co`, or install Ollama on the laptop with `OLLAMA_MODELS` on D:.

## Tickets

Status 21.11, 15:40: the v1 build (T00–T23) is merged and green; v2 arrived on `origin/main` during the build and is merged as the plan of record. Rows below say what v1 already covers and what v2 adds.

| Ticket | Lane | Title | Blocked by | Estimate | Status |
|---|---|---|---|---|---|
| [T00](tickets/T00-contracts.md) | 0 – coordinator | Freeze contracts and scaffold stubs | — | 40 min | done (v1 contracts); v2 stubs come with each v2 ticket |
| [T01](tickets/T01-core-package.md) | A – core | Move the core into a `udip/` package | T00 | 45 min | done |
| [T02](tickets/T02-database-seed.md) | A – core | SQLite schema + seed from UMB data | T01 | 1 h | done (v2 tables arrive with T24–T26) |
| [T03](tickets/T03-app-skeleton.md) | B1 – UI: case flow | FastAPI + Jinja2 + htmx skeleton and visual base | T00 | 45 min | done |
| [T04](tickets/T04-screen-calendar.md) | B1 – UI: case flow | Kalendarz screen | T03, T02 | 2 h | done; v2 extras (days off, dept sub-deadlines, risk) open |
| [T05](tickets/T05-screen-new-request.md) | B1 – UI: case flow | Nowy wniosek screen (upload → security → analysis → calendar) | T04, T01 | 2 h | done; security note from T26; scan viewer open |
| [T06](tickets/T06-screen-case.md) | B1 – UI: case flow | Sprawa screen | T05, T24 | 2 h | done incl. T24 dispatch packets |
| [T07](tickets/T07-screen-draft.md) | B2 – UI: letters & redaction | Projekt pisma screen | T03, T02, T24 | 2.5 h | done incl. T24 unassigned list + provenance |
| [T08](tickets/T08-screen-anonymization.md) | B2 – UI: letters & redaction | Anonimizacja screen + verified exports | T07, T27, T25 | 2.5 h | done incl. T27 hardening (blocks, metadata scrub, XML audit badge, footer) |
| [T09](tickets/T09-windows-setup.md) | D – delivery | Windows setup on D: + checkpoint 1 | T00 | 45 min | done (app ran on the team's Windows laptop: var/udip.sqlite, uploads) |
| [T10](tickets/T10-llm-client.md) | C – LLM & eval | LLM client: modes, offline enforcement, cache, budget | T00 | 1 h | done incl. v2 mode() + UDIP_OFFLINE enforcement |
| [T11](tickets/T11-llm-call1-analyze-route.md) | C – LLM & eval | Call 1: analyze_and_route | T10, T01 | 1 h | dropped: team decision 21.11 21:40 – local Bielik only, no cloud API |
| [T12](tickets/T12-llm-call2-draft-pii.md) | C – LLM & eval | Call 2: draft_and_semantic_pii | T10, T01, T24 | 1.5 h | dropped: team decision 21.11 21:40 – local Bielik only, no cloud API |
| [T13](tickets/T13-llm-vision-handwriting.md) | C – LLM & eval | Handwriting transcription (Claude Vision, cloud demo only) | T10 | 45 min | dropped: team decision 21.11 21:40 – local Bielik only, no cloud API |
| [T14](tickets/T14-synthetic-adversarial.md) | C – LLM & eval | Small synthetic set + adversarial cases | T10 | 45 min | dropped: team decision 21.11 21:40 – local Bielik only, no cloud API |
| [T15](tickets/T15-benchmark.md) | C – LLM & eval | Benchmark: rules vs Bielik (offline) vs Sonnet | T11, T12, T14 | 1 h | dropped: team decision 21.11 21:40 – local Bielik only, no cloud API |
| [T16](tickets/T16-bielik.md) | C – LLM & eval | Bielik-4.5B offline: benchmark row and live mode | T10 | background | done (team laptop, 19:28): Bielik 4.5B measured offline, 80 calls, $0; 165.6 s per request |
| [T17](tickets/T17-archive-knowledge.md) | B1 – UI: case flow | Archiwum / Baza wiedzy screen | T03, T25 | 1.5 h | done incl. „Pamięć instytucjonalna” panel (T25) |
| [T18](tickets/T18-unslop-audit.md) | B2 – UI: letters & redaction | unslop-ui audit of all templates | T08, T17, T23 | 45 min | done |
| [T19](tickets/T19-e2e-tests.md) | A – core | End-to-end tests of the app | T06, T08 | 45 min | done |
| [T20](tickets/T20-ask-archive.md) | C – LLM & eval | Cut: „Zapytaj archiwum” chat | — | — | dropped |
| [T21](tickets/T21-deck-video.md) | D – delivery | Slides (≤10) + video script, checkpoint 3 | T00 | 1.5 h | done (v1 content; refresh after v2 deltas) |
| [T22](tickets/T22-readme-freeze.md) | D – delivery | README for the jury, disclosure, freeze | T19, T21, T18 | 45 min | done (video link + git push: team) |
| [T23](tickets/T23-ui-llm-wiring.md) | B2 – UI: letters & redaction | Wire LLM modes into the UI | T08, T11, T12, T13 | 1 h | done (provider select, mode label, offline note) |
| [T24](tickets/T24-dispatch-core.md) | A – core | Department dispatch packet + deterministic Ad mapping | T01 | 1.5 h | done (lane A) |
| [T25](tickets/T25-learning-core.md) | E – core: safety & learning | Learning from clerk corrections (3 feedback loops) | T02 | 1.5 h | done (merged 21.11 20:45; routing log on Sprawa not done) |
| [T26](tickets/T26-security-scanner.md) | E – core: safety & learning | Ingest security scanner + prompt-injection pre-filter | T00 | 1.5 h | done (lane E) |
| [T27](tickets/T27-export-hardening.md) | E – core: safety & learning | Irreversible export hardening + XML leak audit + redaction footer | T00 | 45 min | done (coordinator) |
| [T28](tickets/T28-names-lexicon.md) | A – core | Bigger name lexicon + optional local NER | T01 | 1.5 h | done (lexicon from Faker/Mimesis + SGJP forms; dane.gov.pl unreachable, GLiNER dropped) |
| [T29](tickets/T29-demo-assets.md) | D – delivery | Demo assets | T00 | 45 min | done (coordinator): 5 files + README; rules miss 'Olena Shevchenko' (→ T28 / model pass), documented |
