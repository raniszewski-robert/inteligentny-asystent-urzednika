# Contracts (T00): the interfaces every lane codes against

Frozen at the start of parallel work (v2, after the external review). Changing a contract = a small commit to `main` by the coordinator that touches only this file + the stub it describes, announced to all lanes. Everything not listed here is private to the lane that owns it.

## 1. Repository layout and ownership

| Path | Owner lane | Others may |
|---|---|---|
| `udip/` core modules (`deadlines, register, importer, ingest, textpl, search, analyze, anonymize, draft, letters, dispatch, db`), `udip/data/` (incl. `names/`), `scripts/seed.py`, `scripts/build_names.py`, `.claude/skills/udip-*/scripts/` (wrappers), `tests/core/` (except files below), `tests/e2e/`, `scripts/smoke.sh` | **A – core** | read, call public functions |
| `udip/security.py`, `udip/export.py`, `udip/learning.py`, `tests/core/test_security.py`, `tests/core/test_export.py`, `tests/core/test_learning.py`, `tests/fixtures/attack_bundle.docx` | **E – core: safety & learning** | read, call |
| `app/main.py`, `app/templates/base.html`, `app/static/app.css`, `app/static/htmx.min.js`, `app/static/scan_viewer.js`, screens Kalendarz, Nowy wniosek, Sprawa, Archiwum (`app/routes/{kalendarz,wniosek,sprawa,archiwum}.py` + templates) | **B1 – UI: case flow** | read |
| Screens Projekt pisma, Anonimizacja, Ustawienia (`app/routes/{projekt,anonimizacja,ustawienia}.py` + templates), `app/static/{ad_editor,redaction}.js`, `.unslop-ui/`, `docs/plan/unslop-report.md` | **B2 – UI: letters & redaction** | read |
| `udip/llm.py`, `udip/llm_tasks/`, `scripts/eval_llm.py`, `scripts/gen_synthetic_umb.py`, `scripts/bielik_server.sh`, `data-samples/syntetyczne_umb/`, `docs/eval/`, `tests/llm/`, `tests/fixtures/pii_torture_test.docx` | **C – LLM & eval** | read, call |
| `setup.ps1`, `run.ps1`, `run.sh`, `docs/INSTALL_WINDOWS.md`, `demo_assets/`, `docs/deck/`, `docs/video_script.md`, `README.md`, `LICENSES-THIRD-PARTY.md` | **D – delivery** | propose changes in reports |
| `requirements.txt` | shared, **append-only**, one line per package with licence comment | append |
| `docs/plan/` | each lane edits only the status line of its own tickets; `PLAN.md`, `CONTRACTS.md` by the coordinator | — |
| `research/`, `data-partner/`, `data-samples/syntetyczne/` | frozen (read-only) | — |

## 2. Core API

### Lane A provides (T00 creates delegating stubs)

```python
# udip/ingest.py
read_any(path: Path, ocr: str = "auto") -> dict
    # {file, text, chars, pages?, ocr?, quality, warning, security}   security = udip.security.scan(path)
render_pages(path: Path, scale: float = 1.5) -> list[bytes]          # PNG per page (pypdfium2), for the scan viewer

# udip/analyze.py
analyze(text, archive, deps, today, since_days=365, exclude_id=None, provider=None) -> dict
    # {mode, flags[], requested_form, questions[{no,text,routing[{department,name,score,share,reasons}]}],
    #  similar_cases[{id,date,title,score,departments,matched_terms,response_excerpt,older_than_window?}],
    #  departments_overall[], routing_plan[], bip_candidate: {count, ids[]} | None, legal_hits[], llm_used: bool}
route(question, deps, similar, k=3) -> list[dict]       # applies learning.boost(question, scores)
load_departments(path=None) -> list[dict]

# udip/search.py
class Archive: __init__(records); search(query, k=5, since=None) -> list[dict]

# udip/register.py
STATUSES, URGENCY_LABEL, URGENCY_COLOR
rows(requests, today, year=None) -> list[dict]   # lp, number, received, summary, initials, status, status_label, extension,
                                                 # due, due_safe, answered, working_days_left, urgency, urgency_label,
                                                 # departments, dept_deadlines[], risk: bool, warnings
# udip/deadlines.py – holidays come from office_days_off when the DB exists (statutory + configured)

# udip/importer.py
convert(xlsx) -> (records, issues); demo_shift(records, today) -> records

# udip/dispatch.py
sub_deadline(received: date, today: date) -> date
packet(case: dict, department: str, questions: list[dict]) -> {"message_text": str, "reply_form_docx": bytes}
parse_reply(text: str) -> dict[int, str] | None          # tier 1: [Ad N] / Ad N. / Ad. N markers

# udip/draft.py
make_draft(request, answers, received, ltype="udostepnienie", *, number, today=None, mode="template", sign,
           extension_until=None, reason="", dept_ids=None, scope="", entity="", entity_contact="", bip_url="",
           keep=None, assignments: dict | None = None) -> dict
    # {text, spans, report, html}; report adds: unassigned[{sentence, source, index}],
    # provenance[{para, sentence, source, index}], number_check{checked, ok, bad[]}, mode_used
finalize(text, spans, accept=set(), reject=set(), accept_all_suggested=False, edited_text=None, initials="") -> dict
    # {text, spans, warnings, anonymized, to_send, body_spans, categories[]}
write_docx(text, spans, path, final=False, version="bip"|"send", initials="") -> {"path", "audit"}
LETTER_TYPES

# udip/anonymize.py
detect(text, keep=None, min_conf=0.5, provider=None) -> list[Span]   # learned rules first, then patterns/lexicon, then LLM review spans
apply(text, spans, mode="label"|"block"); preview_html(text, spans, title)
```

### Lane E provides (T00 creates neutral stubs; the hooks above already call them)

```python
# udip/security.py
scan(path: Path) -> {"hidden_text": [...], "images": [{"page", "kind"}], "injection": [...], "notes": [...]}
sanitize_for_llm(text: str) -> tuple[str, list[dict]]        # (clean text, quarantined spans) – logs security_events

# udip/export.py
harden_docx(docx_bytes: bytes) -> bytes                       # scrub core/app/custom props, comments, revisions
audit_docx(docx_bytes: bytes, secrets: list[str]) -> {"ok": bool, "hits": [...], "xml_preview": str}
metryczka(categories: list[str], initials: str, on: date) -> str
BLOCK = "██████"                                              # fixed-length replacement for accepted spans

# udip/learning.py
apply_rules(text: str) -> list[dict]                          # learned_pii_rules: allow → suppress, redact → suggested span
remember(phrase, action, category, case_id, by) -> int
boost(question: str, scores: dict[str, float]) -> dict[str, tuple[float, str]]   # department → (extra score, reason)
log_routing(question, predicted, confirmed, case_id) -> None
add_law(path_or_text, title) -> int; legal_hits(text, k=3) -> list[dict]
memory_stats() -> dict; reset(kind: str) -> None
```

## 3. LLM API (lane C provides; stubs return `None` = "use rules")

```python
# udip/llm.py
mode() -> {"id": "offline_rules"|"offline_bielik"|"cloud_claude", "label": str, "network": "blocked"|"api.anthropic.com"}
available() -> bool
complete_json(task, system, user, schema, *, provider=None, images=None) -> dict | None
usage() -> {calls, cached, input_tokens, output_tokens, usd, budget_usd}

# udip/llm_tasks/
analyze_route.call1(text, deps, similar) -> dict | None
    # {questions[], other_procedure_flags[], routing_per_question[{question_no, department, reason}], summary}
draft_pii.call2(ltype, questions, sentences, legal_hits) -> dict | None
    # {ad_map{"1": ["S1"], …, "unassigned": [...]}, connective_text{}, semantic_pii[{text, category}]}
vision.transcribe(page_pngs: list[bytes]) -> dict | None        # cloud mode only
```
Untrusted text always passes `security.sanitize_for_llm` and sits inside `<untrusted_citizen_request>` / `<untrusted_department_reply>`. `UDIP_OFFLINE=1` (offline modes) makes `udip.llm` refuse every non-localhost connection. Hook points in `analyze`, `draft`, `anonymize` (written in T00) call these and treat `None` as "keep the rule result".

## 4. Database (lane A owns `udip/db.py`; the schema is the contract)

```sql
CREATE TABLE cases (id INTEGER PRIMARY KEY, number TEXT UNIQUE, received TEXT, summary TEXT, applicant_label TEXT,
  initials TEXT, status TEXT DEFAULT 'a_brak_dzialan', extension_days INTEGER, extension_until TEXT, answered TEXT,
  departments TEXT DEFAULT '[]', analysis TEXT, is_demo INTEGER DEFAULT 0, created_at TEXT);
CREATE TABLE status_history (id INTEGER PRIMARY KEY, case_id INTEGER, from_status TEXT, to_status TEXT, at TEXT, by TEXT, note TEXT);
CREATE TABLE documents (id INTEGER PRIMARY KEY, case_id INTEGER, kind TEXT CHECK(kind IN ('request','dept_answer','letter','law','archive','other')),
  filename TEXT, department TEXT, text TEXT, quality REAL, security TEXT, path TEXT, created_at TEXT);
CREATE TABLE drafts (id INTEGER PRIMARY KEY, case_id INTEGER, version INTEGER, ltype TEXT, text TEXT, spans TEXT, report TEXT,
  assignments TEXT, final_to_send TEXT, final_anonymized TEXT, audit TEXT, created_at TEXT);
CREATE TABLE department_dispatches (id INTEGER PRIMARY KEY, case_id INTEGER, department TEXT, questions TEXT,
  sub_deadline TEXT, sent_at TEXT, answered_at TEXT);
CREATE TABLE archive (id TEXT PRIMARY KEY, date TEXT, title TEXT, request_text TEXT, response_text TEXT, departments TEXT, source TEXT);
CREATE TABLE legal_chunks (id INTEGER PRIMARY KEY, law_title TEXT, ref TEXT, text TEXT, source_file TEXT, created_at TEXT);
CREATE TABLE learned_pii_rules (id INTEGER PRIMARY KEY, phrase TEXT, normalized_phrase TEXT, action TEXT CHECK(action IN ('allow','redact')),
  category TEXT, source_case_id INTEGER, created_by TEXT, created_at TEXT);
CREATE TABLE routing_feedback (id INTEGER PRIMARY KEY, question_text TEXT, tokens_json TEXT, predicted_dept TEXT, confirmed_dept TEXT,
  case_id INTEGER, created_at TEXT);
CREATE TABLE security_events (id INTEGER PRIMARY KEY, case_id INTEGER, kind TEXT, detail TEXT, raw TEXT, created_at TEXT);
CREATE TABLE office_days_off (day TEXT PRIMARY KEY, label TEXT, statutory INTEGER);
```
Helpers in `udip/db.py`: `connect, init, list_cases, get_case, create_case, set_status, add_document, save_draft, add_dispatch, archive_records, add_archive, days_off, set_day_off`. Lane E reads and writes its own tables through `db.connect()`.

## 5. Routes and templates

| Route | Template | Ticket |
|---|---|---|
| `GET /` → `/kalendarz`, `POST /kalendarz/import`, `POST /sprawy/{id}/status`, `GET /kalendarz.csv` | `kalendarz.html` | T04 |
| `GET/POST /wniosek/nowy`, `GET /wniosek/{doc_id}/strona/{n}.png`, `POST /wniosek/{doc_id}/odczyt-ai` | `wniosek_nowy.html` | T05 |
| `GET /sprawy/{id}`, `POST /sprawy/{id}/odpowiedzi`, `POST /sprawy/{id}/trasowanie`, `GET /sprawy/{id}/przekazanie/{dept}` (+ `.docx`), `POST /sprawy/{id}/przekazane` | `sprawa.html` | T06 |
| `GET/POST /sprawy/{id}/projekt`, `POST /sprawy/{id}/projekt/przypisz` | `projekt.html` | T07 |
| `GET/POST /sprawy/{id}/anonimizacja`, `GET /sprawy/{id}/eksport/{send\|bip}.{docx\|txt}`, `GET/POST /anonimizacja`, `POST /pamiec` | `anonimizacja.html` | T08 |
| `GET /archiwum`, `POST /archiwum/import`, `POST /archiwum/przepisy`, `POST /archiwum/pamiec/reset` | `archiwum.html` | T17 |
| `GET/POST /ustawienia` (mode, usage; days off section from T04) | `ustawienia.html` | T23 |

## 6. Environment and shared resources

| Variable | Default | Note |
|---|---|---|
| `UDIP_ENV_FILE` | `<repo>/.env` | absolute path of the one `.env` all worktrees read (worktrees don't copy untracked files) |
| `UDIP_VENV` | `<repo>/.venv` | one shared virtualenv |
| `UDIP_DATA_DIR` | `<repo>/var` | SQLite, uploads, exports, `llm_cache/`, `llm_usage.json`; one shared absolute path for all worktrees |
| `ANTHROPIC_API_KEY` | – | `.env` only |
| `LLM_BUDGET_USD` | `15` | global |
| `UDIP_PROVIDER` | `rules` until T10, then `anthropic:sonnet` if available | `rules`, `anthropic:sonnet`, `openai_compat:bielik` |
| `UDIP_OFFLINE` | `0` | `1` blocks all non-localhost connections in `udip.llm` |
| `LLM_BASE_URL`, `LLM_MODEL`, `LLM_TIMEOUT` | Ollama defaults | Bielik |
| `UDIP_NER` | `off` | `gliner` enables optional local NER (T28) |
| `TESSERACT_CMD` | `tesseract` | Windows: `D:\Tools\Tesseract-OCR\tesseract.exe` |

## 7. Fixtures available before lanes merge

`data-partner/umb/*`, `data-samples/syntetyczne/*`, and from T00: `tests/fixtures/analysis_599.json`, `draft_543.json`, `rows_demo.json`, `security_findings_demo.json`, `dispatch_543.json`.

## 8. As built in v1 (21.11, before v2 was merged)

The v1 build follows the v1 contract; where v2 differs, v2 is the target and the v2 ticket closes the gap. Built and tested today:

- LLM tasks as v1 split functions: `llm_tasks.analysis.analyze_llm`, `routing.route_llm`, `drafting.paragraphs_llm`, `anonymization.spans_llm` (each `provider=`), `udip.llm.provider_for()`, `usage()`, `set_transport()` (tests). v2 `call1`/`call2`/`vision`/`mode()` wrap or replace them (T10–T13).
- `analyze()` result has `llm_used`, `provider`; per-question `llm_routing`. `make_draft(..., provider=None)`; `draft.check_numbers`/`omitted_numbers` ignore `Ad N` headings.
- `udip.db` v1 schema + `seed(demo_today=None)`, `case_by_number`, `update_case`, `history`, `documents`, `get_draft`, `set_draft_finals`, `delete_case`, `set_status(..., at=None)`. `anonymize.flatten`, `analyze_rules`, `detect_rules`, `config.today()`.
- Routes as listed in v1 §5 plus: `/anonimizacja/{token}` standalone session with `/anonimizacja/{token}/eksport/zanonimizowana.{docx,txt}`, `POST /sprawy/{id}/analiza`, export names `do_wysylki`/`zanonimizowana` (v2 names `send`/`bip`), `/ustawienia` provider choice stored in `UDIP_DATA_DIR/settings.json`.
- Exports fail closed (409 while any span is undecided) and every DOCX/TXT is checked for accepted span text before download.
- T26 (lane E, merged 21.11 16:48): `udip.security.scan(path, text=None)`, `sanitize_for_llm(text, *, case_id=None, log=True)`, `find_injection`, `count`, `empty`, `log_scan`, `MARKER`; `read_any()` returns `security`; every `llm_tasks` prompt passes through `sanitize_for_llm`; `db.log_security_event(case_id, kind, detail, raw)`, `db.security_events(case_id=None)`, table `security_events`. The scanner only reports; the clerk's text is never altered. Not done: v2 `documents.security` column.
- T27 (coordinator): `udip.export` (`BLOCK`, `harden_docx`, `audit_docx`, `metryczka`), `write_docx(..., footer="")`, app export audit badge + export gate.
- T10/T23 v2 (coordinator): `llm.offline()`, `llm.mode(provider=None)`; `UDIP_OFFLINE=1` refuses non-localhost calls.
- T24 (lane A, merged 21.11 20:30): `make_draft(..., assignments=None)` ({"file#idx": n, 0 = skip; "file": n}); report adds `unassigned[{sentence, source, index, candidates, reason}]`, `provenance[{para, sentence, source, index, tier, confidence, rule}]`, `assignment_tiers`, `assignments`; `uncertain_assignment` keeps only department-competence notes. `udip.dispatch.packet(..., today=, due=)` (+ subject, sub_deadline, legal_due, filename, questions), `message_text()`, `dispatch_questions(case)`, `parse_reply()`; `db.add_dispatch`, `db.dispatches(case_id)`, `db.set_dispatch_answered()`. Routes: `GET /sprawy/{id}/przekazanie/{dept}[.docx]`, `POST /sprawy/{id}/przekazane` (a → b), `POST /sprawy/{id}/projekt/przypisz`. Office days off: statutory holidays only (no `office_days_off` table).
- T25 (lane E, merged 21.11 20:45): `udip.learning` – `remember(phrase, action, category="", case_id=None, by="")` (action `allow`|`redact`), `rules()`, `apply_rules(text)` (spans with `REASON_PII`), `log_routing()`, `boost(question, scores)` (used by `route()`), `korekty(n)`, `split_law(text)`, `add_law(path_or_text, title, source_file="")`, `legal_hits(text, k=3)`, `memory_stats()`, `reset(kind)`. Tables `learned_pii_rules`, `routing_feedback`, `legal_chunks`. New category `TAJEMNICA` in `anonymize`/`export`. Routes: `POST /pamiec` (Zapamiętaj on Anonimizacja), `POST /archiwum/pamiec/reset`; panel „Pamięć instytucjonalna” in Archiwum. Not done: routing-correction log on the Sprawa screen.
- T28 (coordinator, 21.11 22:30): `udip/data/names/{imiona,nazwiska}.tsv` built by `scripts/build_names.py`; `anonymize.SURNAME_FORMS`, `SURNAME_AMB`, `AMBIG_FIRST` (lexicon forms also loaded into `NAME_FORMS`); new rule: capitalised word + unambiguous lexicon surname → OSOBA 0.8; ambiguous first names only in a pair; 3-letter capital words need a surname. Sentence span type `TAJEMNICA` (review) for business-secret claims.
