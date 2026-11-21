# Review brief: "Intelligent Clerk Assistant" for public-information requests (HackNation 2026, Bydgoszcz)

You are reviewing a hackathon project mid-build. Please read everything, then give (1) the weakest points of the approach, (2) novel ideas we have not considered, (3) concrete changes ranked by impact on the jury score per hour of work. We have roughly 20 hours left, one builder (an AI coding agent) and one human who runs the demo. Be specific: name the feature, the change and how to verify it. Do not repeat what we already do unless you think it is wrong.

## 1. The challenge

- **Hackathon:** HackNation 2026, Bydgoszcz, Poland, 21–22 November 2026. 24 hours. Submission deadline Sunday 22.11 at 11:00; our code freeze is 09:30.
- **Partner:** Urząd Miasta Bydgoszczy (Bydgoszcz City Hall, "UMB"). The team owning the process is Biuro Komunikacji Społecznej (BKS, Social Communication Office).
- **Prize:** 15,000 PLN. The winner transfers copyright to the city, so dependencies must be permissively licensed (MIT/BSD/Apache; no GPL/AGPL/LGPL).
- **Domain:** requests for access to public information under the Polish Act of 6 Sept 2001 ("UDIP"). Anyone can ask any public body for information. The body must answer "without undue delay, no later than 14 days" (art. 13(1)). It may extend to 2 months if it notifies the requester before the 14 days pass, giving reasons (art. 13(2)). Refusals are formal administrative decisions (art. 16). Privacy of private persons and business secrets limit disclosure (art. 5(2)), but data of public officials related to their function is public.

**What the city asked for** (the official task text, condensed):
1. A tool for clerks handling these requests: a **calendar/register of requests** with deadlines, a **response-draft generator** and an **anonymization module**.
2. AI is allowed during the hackathon (open/cloud models on test data), but **the target system must run on a closed model without Internet**, "able to learn from uploaded data" (laws, law updates, past requests and answers). The presentation must name a specific model that can run in a closed environment.
3. Inputs are uploaded manually by the clerk (PDF or Word).
4. The calendar lists requests from oldest to newest with days left. Requests due today and the day before are highlighted. Optional fields: response in preparation, "kwerenda" (extension), response sent, clerk initials, number, short subject, received date, due date, response date. Year selector.
5. Anonymization **suggests** which data should be hidden (highlighted grey), and after the clerk accepts it becomes black.
6. Search the archive of past answers for similar requests.
7. Suggest the best path: which city departments should provide the answer.
8. After the clerk uploads the departments' answers, generate a draft letter that the clerk checks for errors and hallucinations.
9. The tool never sends anything by itself. No integration with other systems (including their EZD "SIDAS"). It is a support tool; the clerk decides.

**The city's simplified flow:** upload laws, past answers and orders → upload a request → show similar requests from the last year → propose departments → the request goes into the register and the clerk confirms data → departments reply (outside the tool) and the clerk uploads the replies → draft with fields marked for anonymization → clerk accepts → export doc/txt → clerk edits → status updates at each step (a: no action, b: queries sent to departments, c: extension + days, d: response prepared, e: response sent).

**How the jury tests:**
1. Upload a sample request (PDF/Word) and check that similar cases are found.
2. Provide a department answer and check the draft letter.
3. Upload a file with personal data and check that it is hidden.
4. Check ease of use, stability and real-world feasibility.
5. Check the calendar ordering, how urgent requests are marked and how processing stages are shown.
6. Check how easily data, laws and past answers can be uploaded.

**Scoring:**
- fit with the challenge 30%
- security and effective anonymization 20%
- ease of use for the clerk 20%
- completeness and quality of the working prototype 30%

Deliverables: video ≤ 3 min, ≤ 10 slides, repo.

## 2. Partner data we have (real, from the city's mentors; approved for testing with cloud LLMs)

- 10 real cases (2025–2026): requests (DOCX, PDF, one **handwritten** scan), BKS final letters (PDF, already anonymized by the city), one extension letter, one "please clarify" letter.
- Their current register is an **Excel sheet** with 9 columns. Its deadlines use `=E11+14` with no weekend/holiday shift, and it has typos (a due date in the wrong year, a received date after the answer date).
- The city's internal order (Zarządzenie, 2024) on the procedure:
  - an "AIP" officer in BKS registers requests and forwards the questions to the relevant departments, setting each a deadline;
  - each department drafts its part of the answer **and anonymizes it itself**, then sends it back;
  - BKS assembles the final letter;
  - refusal decisions are drafted by the department and signed by the Mayor or authorized persons.
- The city's list of **28 categories of data to anonymize**: names of private persons, PESEL (national ID number), ID card, private NIP (tax number), date and place of birth, address, private phone and e-mail, bank account, handwritten signature, image, family status, health, finances, welfare, political or religious views, union or party membership, ethnicity, sexual orientation, criminal record, land-register number, plot number (when it identifies an owner), private vehicle plate, business secret, tax secret, bank secret, professional secret, classified information.
- BKS letters follow a fixed style: header with case number `BKS.IV.1431.<n>.<year>`, "Szanowny Panie/Szanowna Pani/Szanowni Państwo", "na podstawie materiału przygotowanego przez komórkę merytoryczną, tj. Wydział X… informuję, co następuje.", then "Ad 1 … Ad N", closing "Łączę wyrazy szacunku". Five letter types appear in the samples:
  - full answer;
  - "we don't hold this data, ask body X" (art. 4(3));
  - "we don't keep such statistics";
  - extension notice;
  - request for clarification (7 days to reply).

## 3. What is already built and tested (Python, offline, standard library + pdfplumber/pypdf/python-docx/openpyxl/pypdfium2, Tesseract for OCR)

| Module | What it does | Measured |
|---|---|---|
| Deadlines | 14 days from receipt (receipt day not counted), weekend/holiday shift per art. 57 §4 of the Administrative Procedure Code (KPA), Polish holidays incl. Christmas Eve (a holiday since 2025), extension capped at 2 months. Shows a second, cautious "safe" date because courts have not settled whether the KPA shift applies to UDIP | 19 edge-case tests pass |
| Register/calendar | Sort oldest→newest; urgency levels overdue/today/tomorrow (= last working day before due)/≤3 working days/ok/done; statuses a–e; HTML/CSV/ICS export; import of the city's Excel with a discrepancy report | 10 UMB cases imported, 6 discrepancies flagged |
| Ingest | PDF (pdfplumber), DOCX, ODT, TXT (cp1250); OCR for scans; text-quality score that flags handwriting ("type it in manually") instead of passing OCR garbage | handwriting 0.36 vs letters 0.78–0.90 |
| Request analysis | Splits questions (numbered list or "?" sentences, ignores forwarded-email headers); detects other procedures (petition, environmental info with a 1-month deadline, re-use of public data, councillor requests, case-file access); flags "processed information", "already in BIP", personal-data questions | rule-based |
| Archive search | BM25 (own implementation, Polish suffix stripping + 6-character truncation), excludes the case itself, last-365-days window with fallback to older cases | real UMB data, leave-one-out: sibling case in top 3 for 5/6; 5,000 synthetic cases: 10 ms per query, hit@5 0.75 |
| Department routing | 29 UMB departments/offices + 17 city units with keywords from the city's public bulletin (BIP); per question; keyword score + votes from similar archived cases; excludes BKS (the coordinator) | real UMB: correct department top-1 6/9, top-3 8/9 |
| Draft generator | 7 letter types (5 copied from BKS's samples); assigns department-answer sentences to "Ad N" by IDF-weighted word overlap; flags gaps and questions that look like another department's competence; deadline warnings (extension sent too late, date in the past); internal notes never go into the letter; DOCX export with grey/black highlighting; two output versions (to the requester with the addressee visible, and anonymized for archive/BIP) | on real case 543: facts correct, but 2 sentences land in the wrong "Ad" without a flag |
| Number check (anti-hallucination) | Normalizes numbers ("3.143.761,14" = "3 143 761,14"), checks every number in the draft exists in the department answers **next to the same word** ("839 psom" ≠ "839 kotów"), reports omitted numbers. Used to reject LLM output | catches invented amounts and swapped figures |
| Anonymization | Validated patterns (PESEL with checksum and date, NIP, REGON, IBAN mod 97, ID card checksum, passport, phone, e-mail, postal code + city, street address, land register, plate); Polish first-name dictionary with generated declensions; "Pan/Pani X"; signatures; initial + surname; CAPS names; surname suffixes (-ski/-cka/-wicz) as "review"; birth data; plot numbers; sentences with sensitive categories (health, welfare, criminal record…) as "review"; whitelists for institutional addresses and e-mail domains, street/patron names ("św. Maksymiliana Kolbego"), public officials. Statuses: suggested (grey) / review (needs a decision) / accepted (black) / rejected | synthetic: precision 0.99, recall 1.00, 0 leaks; real UMB requests: correct hits, no false alarms on the city's own address |
| Legal guard | When accepting redactions of third-party data in disclosed content, warns that this is a partial refusal and needs a decision (a 2026 administrative court ruling, WSA Opole I SAB/Op 11/26) | — |
| Acceptance tests | The jury's 6 steps scripted on real UMB files | 11/11 pass |

## 4. Decisions for the remaining build

- **App:** FastAPI + Jinja2 + htmx + small vanilla JS; SQLite (no ORM); runs locally on the demo person's Windows laptop from D:\ (native venv, `setup.ps1`/`run.ps1`); no login (a "clerk" dropdown).
- **Screens:**
  1. Calendar (import Excel, status changes, colors, year filter);
  2. New request (upload → analysis → confirm into calendar);
  3. Case (questions, routing per question, similar cases, upload department answers, history);
  4. Draft letter (letter type, move sentences between "Ad", warnings);
  5. Anonymization editor (grey/black, exports);
  6. Archive / knowledge base (search, upload laws and past cases).
- **LLM layer (required by the team):**
  - Claude Sonnet via API during the hackathon (cached, hard budget $15);
  - rules remain as fallback and validators;
  - LLM tasks: draft paragraphs per "Ad" (guarded by the number check), request analysis as JSON, an anonymization second pass (review status only), routing with a one-line justification;
  - "ask the archive" chat as a stretch goal.
- **Local model for the pitch:** Bielik (Polish open model by SpeakLeash, Apache-2.0). Bielik-11B-v3.1-Instruct is recommended for a city server with a GPU. Bielik-4.5B-v3.0-Instruct will be **measured** on CPU in a sandbox on a ~20-item subset; it is not shipped in the demo.
- **Evaluation for slides:** rules vs Claude Sonnet vs Claude Haiku vs Bielik on the same items, covering:
  - question extraction;
  - routing top-1/top-3;
  - draft facts in the right "Ad", invented/swapped/omitted numbers;
  - anonymization P/R/leaks;
  - latency and cost per request.

  Items: 10 real UMB cases + ~40 synthetic cases generated by Claude in the style and topics of the real ones, with gold labels.

## 5. Known weaknesses (please attack these)

1. Assigning department-answer sentences to "Ad N" is lexical and sometimes wrong without flagging it.
2. Only 10 real cases: similarity search and routing are thin, and synthetic data may flatter our numbers.
3. The anonymization name dictionary is small (157 first names); surnames without first names rely on suffix heuristics; no handling of images, signatures or scans.
4. "Learning from uploaded data" is currently just "uploaded documents feed BM25 search", with no learning from clerk corrections.
5. Deadlines: legally ambiguous weekend shift; days off granted for holidays falling on Saturday are not "statutory holidays" and need config.
6. Handwritten requests cannot be read (Tesseract fails).
7. The demo runs on a single laptop; the "deploy in the city for years" story is a slide, not something shown.
8. Calendar colors on real data only appear in a demo mode that shifts dates (the city's sheet has only closed cases).

## 6. Questions for you

1. What would make a jury of city clerks say "we want this on Monday"? What are we missing that saves them the most time?
2. Is there a better way to assign department answers to questions than word overlap or an LLM? For example, asking departments to answer in a structured form, or a per-question upload.
3. How would you make "learns from uploaded data" real and demonstrable in 20 hours, offline-compatible? For example, learning from clerk corrections to anonymization and routing, a few-shot store, or a template library mined from past letters.
4. Any better anonymization approach under permissive licenses that runs on CPU (Polish NER, GLiNER-PII, a small LLM), and how to measure it convincingly in front of the jury?
5. How to demonstrate safety (prompt injection inside a citizen's request, data leaks, hallucinations) in under 30 seconds of video?
6. Anything novel in UX: e.g. a deadline risk forecast, auto-generated department query emails (not sent), a "what did we answer last year" diff, a public-BIP suggestion for repeated questions.
7. Which of our planned features would you cut to make time for your best idea?

Answer in English or Polish, ranked by impact per hour.
