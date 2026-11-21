# Implementation Handoff — Intelligent Clerk Assistant (HackNation 2026, UMB / BKS)

This document is an actionable execution spec for the implementation team. Execute tasks strictly in priority order (`P1` → `P8`; `P9` only if ahead of schedule). Do **not** rebuild already-tested deterministic modules unless explicitly specified below.

---

## 0. Hard Constraints & Ground Rules

- **Timeline:** Code freeze **Sunday 22.11.2026 at 09:30 CET**; submission at **11:00 CET**. Total implementation budget below: **~13.75h** (leaves buffer for Windows testing, 3-min video, and ≤10 slides).
- **Runtime target:** Demo runs on a Windows laptop from `D:\` via native Python venv (`setup.ps1` / `run.ps1`). Stack: **FastAPI + Jinja2 + htmx + minimal vanilla JS + SQLite (no ORM)**. No login (clerk dropdown only).
- **Never auto-send / never integrate:** The tool never sends emails, never integrates with SIDAS/EZD, and never finalizes legal actions without clerk confirmation.
- **License compliance (MANDATORY — copyright transfers to Bydgoszcz City Hall):**
  - **Allowed only:** MIT, Apache-2.0, BSD-2/3-Clause, ISC, CC0 / Public Domain, PSF.
  - **FORBIDDEN (do NOT install or import):**
    - `spaCy` Polish models (`pl_core_news_sm/md/lg` — **GPL-3.0**)
    - `PyMuPDF` / `fitz` (**AGPL-3.0**)
    - `iiiorg/piiranha-v1-detect-personal-information` / `wikineural` (**CC-BY-NC**)
    - Gemma models (non-OSI custom license)
    - Any GPL / AGPL / LGPL / CC-BY-NC package or weights.
- **Jury scoring weights:** Fit with challenge **30%** · Prototype completeness/quality **30%** · Security & anonymization **20%** · Ease of use **20%**.

---

## 1. Immediate Scope Cuts (Stop / Do Not Build)

1. **CUT "Ask the archive" chat.** High hallucination risk, redundant with similar-case search + side-by-side comparison.
2. **CUT the 4-model × 50-case synthetic evaluation suite.** Replace with a fast benchmark on the **10 real UMB cases + 5 adversarial test cases** comparing `Reguły Offline` vs `Bielik-4.5B Offline (CPU)` vs `Claude Sonnet` (~1h total, 1 slide).
3. **CUT 4 separate LLM calls per request.** Consolidate into **at most 2 cached JSON calls** (Call 1: Request Analysis + Department Routing; Call 2: Draft Paragraph Assembly + Semantic-PII Review). Deterministic rules remain fallback and post-validator on every call.
4. **DEFER extra register exports (e.g., ICS) and cosmetic polish** until `P1`–`P6` pass all 6 jury acceptance tests on Windows.

---

## 2. Prioritized Implementation Plan

### P1 — True Irreversible DOCX/TXT Redaction + Post-Export XML Leak Audit + Polish BIP Clause (~1.5h)
**Why:** Black highlight/shading in DOCX leaves raw PII readable in `word/document.xml` via `Ctrl+A` → `Ctrl+C` or unzip. This is a critical failure under the 20% Security rubric.

**Build:**
1. **Irreversible redaction on export:**
   - Preview/editor keeps grey (`suggested`) / yellow (`review`) / black (`accepted`) visual states in HTML.
   - On final anonymized `.docx` and `.txt` export, **physically replace** every accepted span's text with solid block runs (`██████` — fixed or length-bucketed so exact character length does not leak PESEL/short names). Never emit original characters underneath black formatting.
2. **Metadata & hidden-artifact scrubbing in exported DOCX:**
   - Clear `docProps/core.xml` (`creator`, `lastModifiedBy`, `title`, `subject`, `keywords`, `description`, `comments`).
   - Strip comments (`word/comments.xml`), tracked changes/revisions (`w:ins`, `w:del`), and custom properties if present.
3. **Dual 1-click export buttons:**
   - `Eksportuj dla wnioskodawcy (.docx)` — addressee block intact; third-party / body PII irreversibly redacted.
   - `Eksportuj do BIP / archiwum (.docx)` — addressee + all accepted PII irreversibly redacted.
   - Keep `.txt` export alongside `.docx`.
4. **Auto-generated `Metryczka wyłączenia jawności` footer:**
   - Append a structured Polish redaction clause at the bottom of exported anonymized documents based on the accepted PII categories present:
     - Private person data (names, PESEL, address, phone, email, IBAN, health, etc.) → `art. 5 ust. 2 ustawy z dnia 6 września 2001 r. o dostępie do informacji publicznej (prywatność osoby fizycznej)`
     - Business secret → `art. 5 ust. 2 u.d.i.p. (tajemnica przedsiębiorcy)`
     - Tax / bank / classified / professional secret → cite corresponding statutory confidentiality category.
     - Include clerk initials (from active clerk dropdown) and export date.
5. **Post-export byte-level leak verifier (`Audyt pliku wyjściowego`):**
   - Immediately after generating the `.docx` bytes, open the archive with `zipfile`, scan every `.xml` member (`word/*.xml`, `docProps/*.xml`) case-insensitively (and whitespace/diacritic-normalized) for every accepted PII string.
   - Return structured audit result to UI and display a verifiable green badge:
     `Zweryfikowano plik wyjściowy: 0 śladów PII w XML i metadanych` (or block download and list offenders if >0).
   - Provide an expandable "Podgląd XML po anonimizacji" snippet in the UI showing `<w:t>██████</w:t>` for the live demo.

**Verify:**
- Automated test: export `Do_BIP.docx` containing PESEL, full name, address, email, IBAN → unzip all XML entries → assert `0` matches for every accepted PII value and `0` personal metadata in `docProps/core.xml`.
- Manual test: open exported `.docx` in Word/LibreOffice, `Ctrl+A` → `Ctrl+C` → paste into Notepad → only `██████` blocks appear, plus the `Metryczka wyłączenia jawności` footer.

---

### P2 — Offline Polish PII Upgrade: Expanded `dane.gov.pl` Lexicon + Permissive CPU NER (~2.0h)
**Why:** Current 157-first-name dictionary will miss common Polish/Ukrainian names on Jury Test #3 (live file upload).

**Build:**
1. **Static Polish/regional name lexicon (CC0 / Public Domain):**
   - Bundle top ~5,000 Polish first names + ~30,000 Polish surnames from `dane.gov.pl` (PESEL public open-data lists, CC0) as a compact local data file (~300–500 KB gzip/json), plus common Ukrainian/Belarusian transliterated first/last names and Polish case declension stem matching.
   - Keep capitalized multi-token person-name detection (First + Surname, Surname + First, Initial + Surname) without relying solely on `-ski/-cka/-wicz`.
2. **Layer 2 CPU NER (permissive license, offline):**
   - Integrate **`urchade/gliner_multi_pii-v1`** (Apache-2.0) running via **`onnxruntime`** (MIT) in quantized ONNX on CPU (or `gliner` Apache-2.0 wrapper configured to load local cached weights with `local_files_only=True`).
   - Map GLiNER labels onto UMB's 28 categories (person, address, phone, email, ID/tax numbers, bank account, date of birth, health/medical, organization/business secret hints).
   - Mark high-confidence structured matches as `suggested` (grey) and ambiguous NER-only spans as `review` (yellow).
   - Ensure graceful fallback: if ONNX model weights are absent, Layer 1 (regex + expanded `dane.gov.pl` lexicon) still runs cleanly without crashing.
3. **Strict whitelist precedence (prevent false alarms on public data):**
   - Always exempt (unless explicitly overridden by clerk): UMB institutional addresses (`ul. Jezuicka 1`, etc.), `@um.bydgoszcz.pl` / `.bip.pl` domains, street/patron names (`ul. św. Maksymiliana Kolbego`, `al. Jana Pawła II`, etc.), and public officials acting in their official capacity (Mayor, Deputy Mayors, department directors, councillors).

**Verify:**
- Create an adversarial fixture `tests/fixtures/pii_torture_test.docx` containing: *Bogumił Krawczyk*, *Bożena Zając*, *Olena Shevchenko*, valid PESEL, land-register number (KW), plot number with owner, IBAN, business secret sentence, alongside *Rafał Bruski (Prezydent Miasta Bydgoszczy)*, *ul. Jezuicka 1, 85-102 Bydgoszcz*, and *ul. św. Maksymiliana Kolbego*.
- Run with network disabled → assert **0 PII leaks** on private data and **0 false positives** on the public official, UMB address, and street patron.

---

### P3 — Real, Auditable Offline Continuous Learning (3 SQLite Feedback Loops) (~2.0h)
**Why:** Requirement #2 asks for a system "able to learn from uploaded data" offline. BM25 indexing alone is retrieval, not learning.

**Build:**
Add 3 SQLite tables that persist across restarts and immediately influence behavior:

1. **`learned_pii_rules`**
   - Columns: `id, phrase, normalized_phrase, action ('allow'|'redact'), category, source_case_id, created_by, created_at`.
   - UI in Anonymization Editor:
     - When clerk rejects a suggested span → show 1-click button: `Zapamiętaj jako wyjątek (dane publiczne)`.
     - Allow clerk to select any unflagged text and click `Zaznacz jako PII` + checkbox `Zapamiętaj na przyszłość`.
   - Next ingest/anonymization pass applies `learned_pii_rules` automatically and badges matches with `Wyuczone z korekty urzędnika`.

2. **`routing_feedback`**
   - Columns: `id, question_text, tokens_json, predicted_dept, confirmed_dept, case_id, created_at`.
   - When clerk confirms or overrides department routing on the Case screen, log the decision.
   - Routing scorer adds a weighted boost from matching `routing_feedback` entries (BM25/token similarity) and surfaces the reason in UI: `Wzmocnione przez X korekt urzędnika`.

3. **Live Legal Knowledge Base → Legal Guard & Style Retrieval**
   - When clerk uploads a law, amendment, or court ruling in Screen 6 (Archive / Knowledge Base):
     - Split into structured `Art. / § / sygnatura` chunks stored in SQLite (`legal_chunks`), indexed immediately in BM25.
     - Surface relevant chunks automatically in Case Analysis / Legal Guard with a `Nowo dodany akt prawny` badge.
   - **Dynamic 1-shot style retrieval:** When drafting a letter of type `T`, fetch the most similar approved past BKS letter of type `T` from the archive, pass it as style reference (or template), and display `Wzór stylu: BKS.IV.1431.X.2025`.
   - Show a compact **"Pamięć instytucjonalna"** summary widget in Screen 6 listing counts of learned PII rules, routing corrections, indexed legal acts, and archived cases (with delete/reset controls for easy demo resets).

**Verify:**
- End-to-end automated + manual test:
  1. Reject a false-positive official name with `Zapamiętaj jako wyjątek`, and manually mark `"Projekt Kaskada"` as `tajemnica przedsiębiorcy` with `Zapamiętaj na przyszłość`.
  2. Upload a fresh document containing both terms → verify the official is NOT flagged and `"Projekt Kaskada"` IS auto-highlighted grey with badge `Wyuczone`.
  3. Change a department routing for a test question and confirm → re-upload a similar question → verify the newly learned department ranks #1 with the feedback note.
  4. Upload a mock 2026 UDIP amendment PDF → verify its article chunk immediately appears in search and Legal Guard.

---

### P4 — 1-Click Department Dispatch Packet + Deterministic / Safe `Ad N` Mapping (~2.0h)
**Why:** Directly matches UMB's 2024 *Zarządzenie* (BKS forwards questions with deadlines; departments reply) and eliminates the silent `Ad N` misplacement bug observed on real case 543.

**Build:**
1. **Department Dispatch Packet (Case screen, never auto-sent):**
   - Per routed department, add button `Przygotuj przekazanie do wydziału`.
   - Calculates internal sub-deadline automatically: `max(today + 2 working days, legal_due_date - 3 working days)` (respecting Polish holidays).
   - Generates two clerk-ready artifacts:
     - **Copy-ready email/EZD message** (1-click Copy): case number `BKS.IV.1431.X.2026`, only the questions assigned to that department, internal sub-deadline, and reminder to return anonymized material per UMB Zarządzenie.
     - **Downloadable structured `.docx` reply form**: pre-populated header (`Sprawa: BKS.IV.1431.X.2026`, `Wydział: ...`, `Termin: ...`) and explicit question blocks (`[Ad 1] Pytanie: ... / Odpowiedź wydziału: ...`, `[Ad 2] ...`).
   - Clicking `Oznacz jako przekazane do wydziałów` updates case status to `b` and records per-department sub-deadlines in SQLite (`department_dispatches` table).
2. **Improved Department Answer → `Ad N` Mapping:**
   - **Tier 1 (Deterministic):** If uploaded reply contains `[Ad N]` / `Ad N.` / `Ad. N` markers (including returned Dispatch Packet DOCX) OR was uploaded via a per-question dropzone, map directly to `Ad N` with confidence `1.0`.
   - **Tier 2 (Unstructured replies):** Never silently place low-confidence sentences into the wrong `Ad`.
     - In LLM mode: send numbered questions `[Q1..Qm]` + numbered reply sentences `[S1..Sk]` and request strict JSON index mapping `{"ad_1": ["S1", "S2"], "unassigned": ["S5"]}` (never rewrite numbers).
     - In Rules/Offline mode: use IDF overlap (or optional MIT `intfloat/multilingual-e5-small` ONNX embeddings if quick) with a confidence margin threshold (`top1 - top2 < threshold` → send to `unassigned`).
   - **UI `Wymaga przypisania` tray** on the Draft screen: any unassigned/low-confidence sentence appears in a visible yellow box with 1-click `[→ Ad 1] [→ Ad 2] [Notatka wewnętrzna / Pomiń]` buttons.

**Verify:**
- Test A: Export Dispatch DOCX for case 543, fill answers under `[Ad 1]`..`[Ad N]`, upload → assert 100% deterministic assignment.
- Test B: Upload raw unstructured UMB case 543 reply → assert the 2 previously misplaced sentences either map accurately (LLM mode) or surface in the `Wymaga przypisania` tray (Rules mode) with zero silent misplacement; verify 1-click reassignment updates draft and export.

---

### P5 — Prompt-Injection Shield + Hidden-Text & Embedded-Image Security Scanner (~1.5h)
**Why:** Untrusted citizen uploads are fed to analysis/routing/drafting/LLM layers; UMB's 28-item list explicitly requires handling signatures and images.

**Build:**
1. **Ingest Security Scanner (PDF & DOCX):**
   - **Hidden text detection:**
     - PDF (`pdfplumber`): flag characters/words with font size `< 3pt`, text color matching page background (e.g., white-on-white RGB ≥ `(0.95, 0.95, 0.95)`), or off-page coordinates.
     - DOCX (`python-docx` XML): flag runs with `w:vanish` (hidden text), tiny font (`< 3pt`), white font color (`#FFFFFF`), comments, and tracked deletions.
   - **Embedded image / signature detection:**
     - Detect images in PDF pages (`pdfplumber` `page.images`) and DOCX (`inline_shapes` / `word/media/*`).
     - Emit an explicit amber security notice: `Wykryto X obraz(ów) (np. str. 2) — zweryfikuj pod kątem podpisu odręcznego lub wizerunku (kategoria z listy UMB)`.
2. **Prompt-Injection Defense:**
   - Deterministic pre-filter scanning extracted citizen text for injection patterns (PL & EN: `"zignoruj poprzednie instrukcje"`, `"ignore previous instructions"`, `"system prompt"`, `"jako model AI"`, `"odpowiedz że urząd ukrywa"`, XML/role spoofing tags).
   - Quarantine matched spans (log in `security_events` table, strip from LLM instruction path, preserve original raw text in read-only audit log) and display a prominent orange banner: `Wykryto i zneutralizowano próbę wstrzyknięcia instrukcji (Prompt Injection)`.
   - Wrap all untrusted citizen and department text in explicit structural delimiters (`<untrusted_citizen_request>...</untrusted_citizen_request>`) with system instructions forbidding execution of embedded commands.
   - Keep strict JSON schema validation + your existing **contextual number-checker** on every LLM draft output; on validation failure, auto-retry once with error feedback, then fall back to deterministic rules and display the caught discrepancy.

**Verify:**
- Create `tests/fixtures/attack_bundle.docx` containing: (a) a real public-info question, (b) an explicit Polish prompt-injection line, (c) white-on-white 1pt hidden text, and (d) 1 embedded PNG signature image.
- Upload → assert all 3 security alerts fire in UI, injection text does not corrupt routing or draft output, and draft passes the number-checker.

---

### P6 — Live Air-Gapped Mode Toggle (Real Local Bielik + Instant Rules + 2-Call LLM Consolidation) (~2.0h)
**Why:** Requirement #2 demands a closed offline model. Showing a real live toggle working in Windows Airplane Mode beats a benchmark slide.

**Build:**
1. **Unified LLM Provider Layer (`app/llm.py`):**
   - Header mode selector persisted in session/settings:
     - `Offline: Tylko reguły (natychmiastowy)` — 0 network, <50ms, pure deterministic + local GLiNER ONNX.
     - `Offline: Lokalny Bielik (Ollama / llama.cpp)` — OpenAI-compatible `http://127.0.0.1:11434/v1` (or `llama-cpp-python` MIT) pointing to **`Bielik-4.5B-v3.0-Instruct`** Q4_K_M (Apache-2.0, ~2.8 GB RAM).
     - `Cloud Demo: Claude Sonnet (API)` — disk-cached in SQLite (`llm_cache`) with hard `$15` budget tracker.
   - Display a persistent top-bar status pill: `Tryb: OFFLINE · Ruch zewnętrzny: 0 B` (green) vs `Tryb: CLOUD DEMO (Claude Sonnet · Cache)` (blue).
   - If Local Bielik is selected but the local server isn't running, display a clean non-blocking status message and fall back automatically to `Offline: Tylko reguły`.
2. **Consolidate to 2 Cached Structured Calls:**
   - **Call 1 (`analyze_and_route`):** Input = sanitized request + department catalog + top-3 similar archive cases → Output = strict JSON (`questions[]`, `other_procedure_flags[]`, `routing_per_question[]` with 1-line Polish justification).
   - **Call 2 (`draft_and_semantic_pii`):** Input = letter type + questions + department answers + 1-shot style letter + legal chunks → Output = strict JSON (`ad_paragraphs[]` + `semantic_pii_candidates[]` in `review` status only). Post-validate every number with the existing number-checker before accepting.
3. **Target Architecture Slide Accuracy Check:**
   - Verify the exact published HuggingFace tag of Bielik-11B (Apache-2.0) before putting it on slides (e.g., `speakleash/Bielik-11B-v2.6-Instruct` or `v3.0`). For offline handwritten scan OCR in the target city server spec, cite an Apache-2.0 VLM such as **`Qwen2.5-VL-7B-Instruct`**.

**Verify:**
- Put laptop into Airplane Mode (Wi-Fi off).
- Run a complete case end-to-end in `Offline: Tylko reguły` and in `Offline: Lokalny Bielik` (if Ollama/GGUF is loaded on demo laptop). Verify zero errors, zero timeouts, and `Ruch zewnętrzny: 0 B`.

---

### P7 — Demo-Ready Calendar Polish + Excel Audit Modal + Dual-Clock SLA Alerts (~1.25h)
**Why:** UMB's real Excel sheet contains only closed historical cases, so without a clean date-shift toggle, Jury Test #5 (urgent highlighting & processing stages) will look flat.

**Build:**
1. **Calendar Mode Toggle (header of Screen 1):**
   - `Widok demo (daty bieżące)` vs `Dane historyczne UMB (2025–2026)`.
   - Demo view shifts the imported real UMB cases cleanly relative to "today" so the jury immediately sees: overdue (red), due today (red/bold), due tomorrow / last working day before due (amber), ≤3 working days (yellow), kwerenda/extension (purple), and done (grey/green) — sorted oldest → newest with days left and stages `a–e`.
2. **Excel Import Audit Modal:**
   - Importing UMB's original 9-column Excel sheet immediately displays a crisp summary card: `Zaimportowano 10 spraw · Wykryto 6 rozbieżności w arkuszu Excel` listing each exact anomaly (wrong year, response before receipt, weekend deadline without KPA art. 57 §4 shift).
3. **Dual-Clock SLA Risk & 1-Click Extension:**
   - Track department sub-deadlines alongside the legal 14-day clock.
   - If a case has ≤3 working days left (or a department sub-deadline passed) and not all department answers are uploaded, show a prominent action button: `Ryzyko terminu — przygotuj przedłużenie (art. 13 ust. 2 u.d.i.p.)` that opens Screen 4 pre-selected to the Extension Notice letter type.
4. **Configurable Extra Days Off:**
   - Add a small `Dni wolne urzędu` config list in Settings/SQLite (pre-seeded with Polish statutory holidays incl. Christmas Eve, plus editable dates for Saturday-holiday days off granted by the Mayor).

**Verify:**
- Import UMB's real Excel file → confirm all 6 discrepancies render cleanly.
- Toggle `Widok demo` → verify oldest→newest ordering, today/tomorrow highlights, stage badges `a–e`, and 1-click extension generation.

---

### P8 — Handwritten Scan Side-by-Side Viewer + Clickable Provenance + BIP Candidate Banner + Legal Guard Polish (~1.5h)
**Why:** Turns the handwritten real UMB scan from a dead-end error into a smooth clerk workflow, builds trust in AI drafts, and adds a BKS-specific BIP workflow insight.

**Build:**
1. **Handwritten / Low-Quality Scan Dual-Pane Viewer (Screen 2):**
   - Whenever OCR quality score `< 0.50` (as on the real UMB handwritten case, 0.36):
     - Render page PNGs via `pypdfium2` in the **left pane** (zoomable) and an editable transcript `<textarea>` in the **right pane**.
     - In `Cloud Demo` mode: offer 1-click `Odczytaj pismo ręczne (AI Vision)` (Claude Vision, cached) that populates the right pane with a yellow banner `Zweryfikuj odczyt pisma ręcznego przed zatwierdzeniem`.
     - In `Offline` mode: clearly show `Wykryto pismo ręczne (jakość OCR 0.36) — przepisz treść po prawej stronie (w wersji docelowej: lokalny model VLM Qwen2.5-VL)`.
2. **Clickable Draft Provenance (`Pokaż źródło`) + Side-by-Side Past Letter Comparison:**
   - Store `(source_file, sentence_index)` metadata for every sentence in the generated draft. Clicking any draft sentence highlights the exact source passage from the department's uploaded reply in a side panel, alongside the green `Zweryfikowano liczby: X/X zgodne ze źródłem` badge.
   - On Screen 3 (Case), when a similar archived case is found, add `Porównaj z zeszłym rokiem` (shows last year's letter beside the current case) and 1-click `Użyj tej samej ścieżki wydziałów`.
3. **BIP Publication Candidate Banner:**
   - When BM25 finds ≥2 similar requests within the last 365 days, display an info banner on Screen 3:
     `Powtarzający się temat (X podobne wnioski w 12 mies.) — rozważ publikację odpowiedzi w BIP (art. 10 ust. 1 u.d.i.p. zwalnia z ponownego udostępniania).`
4. **Legal Guard Wording Calibration:**
   - Frame the WSA Opole (`I SAB/Op 11/26`) alert as a **non-blocking legal advisory** ("Uwaga prawna: anonimizacja techniczna dotyczy danych ubocznych osób trzecich; jeśli usunięcie danych narusza istotę żądanej informacji, może być wymagana decyzja odmowna z art. 16 u.d.i.p."), so it helps clerks without falsely blocking routine technical redactions.

**Verify:**
- Upload the real handwritten UMB scan → left pane displays crisp rendered scan, right pane holds editable text (auto-transcribed in Cloud mode, clean manual entry in Offline mode).
- Open Draft screen → click a draft sentence → matching department source line highlights.
- Upload a request similar to 2 archived cases → BIP suggestion banner appears.

---

### P9 — Stretch Goal ONLY if P1–P8 Complete Early: Canvas Box Redactor for Scanned Images/Signatures (~1.5h)
- If an uploaded PDF/DOCX contains embedded images or scanned pages, render page PNG onto an HTML5 `<canvas>` on Screen 5, allow dragging black rectangles over handwritten signatures/faces, burn solid `#000000` boxes via `Pillow` (MIT-CMU), and export a flattened image-only PDF (`Pillow` `save_all=True`, zero hidden text layer).

---

## 3. Demo Assets & Verification Checklist Before 09:30 Freeze

### 3.1 Pre-Baked Demo Fixtures (put in `demo_assets/`)
1. `01_rejestr_umb.xlsx` — real UMB Excel sheet (demonstrates 6-discrepancy audit + calendar demo shift).
2. `02_wniosek_atak_bezpieczenstwa.docx` — synthetic request containing real-style Bydgoszcz question + explicit prompt-injection instruction + hidden white 1pt text + embedded signature image + tricky Polish/Ukrainian PII (*Bogumił Krawczyk*, *Olena Shevchenko*, PESEL, IBAN) + public official (*Rafał Bruski*) + *ul. Jezuicka 1*.
3. `03_odpowiedz_wydzialu_halucynacja_test.docx` — sample department answer (with numbers like `839 psom` / `3 143 761,14 zł`) plus a toggleable demo hook or unit test showing the number-checker catching a swapped number (`839 kotów`) in <5 seconds.
4. `04_nowelizacja_udip_2026_demo.pdf` — short 1-page mock legal update to prove live Knowledge Base upload → immediate Legal Guard citation.

### 3.2 25-Second Video Sequence ("3 Attacks, 3 Shields")
- **0:00–0:08 (Prompt Injection + Hidden Content):** Upload `02_wniosek_atak_bezpieczenstwa.docx` → orange Prompt Injection banner + hidden-text + embedded-signature alerts fire → clean analysis produced.
- **0:08–0:17 (Anti-Hallucination):** Show caught numeric mismatch (`839 kotów` vs `839 psów`) blocked by deterministic number-checker + clickable source provenance.
- **0:17–0:25 (Zero Leak + Offline):** Show `Tryb: OFFLINE · 0 B`, accept redactions (grey → black), export `Do_BIP.docx`, display `Audyt pliku wyjściowego: 0 śladów PII w XML i metadanych` + `<w:t>██████</w:t>` proof + auto-generated `Metryczka wyłączenia jawności`.

### 3.3 Final Pre-Freeze Gates (Must All Pass on Demo Windows Laptop `D:\`)
- [ ] **Jury Test 1:** Upload PDF/DOCX request → similar cases from last 365 days shown + BIP banner if repeated.
- [ ] **Jury Test 2:** Generate Dispatch Packet + upload department reply → draft letter generated with provenance, `Ad N` review tray (no silent misplacement), and 0 numeric errors.
- [ ] **Jury Test 3:** Upload file with tricky Polish/Ukrainian PII + public official → grey suggestions → accept → black → export `Do_BIP.docx` → XML audit = `0` leaks, copy-paste shows only `██████`, public official untouched.
- [ ] **Jury Test 4:** Run in Windows Airplane Mode (`Offline` mode) with 0 crashes; verify clean restart from `run.ps1`.
- [ ] **Jury Test 5:** Calendar sorted oldest→newest, urgency colors (overdue/today/tomorrow) visible via `Widok demo`, stages `a–e` update cleanly, year filter works.
- [ ] **Jury Test 6:** Upload law PDF + past case + teach 1 PII exception & 1 new PII term → verify immediate effect on next upload.
- [ ] **License Audit:** Inspect `requirements.txt` / installed packages and model cards → confirm **zero** GPL/AGPL/LGPL/CC-BY-NC dependencies.
- [ ] **Compact Benchmark Table (for 1 slide):** Run 10 real UMB cases + 5 adversarial cases across `Reguły Offline`, `Bielik-4.5B Offline (CPU)`, and `Claude Sonnet` (report PII Leak Rate, False Alarms on Public Data, Routing Top-1/Top-3, Numeric Accuracy, Latency).