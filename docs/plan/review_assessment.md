# Assessment of the external review (`external_review.md`), 21.11.2026

Verdict per item and what changed in the plan (v2). Checked against our code and data the same day.

| Item | Verdict | Evidence / reason | Plan v2 |
|---|---|---|---|
| P1 irreversible redaction | **premise false, polish adopted** | Unzipped our `odpowiedz_zanonimizowana.docx`: 0 accepted spans in any XML (we replace characters). Real gaps: block length = text length; `docProps/core.xml` says `python-docx` | T27, T08 |
| P2 name lexicon + GLiNER | adopt with changes | Licence of dane.gov.pl lists and Polish support of `urchade/gliner_multi_pii-v1` unverified; HF and dane.gov.pl unreachable from our machines today; GLiNER pulls torch onto the laptop | T28 (lexicon first, NER optional) |
| P3 learning loops | adopt | Makes requirement 1 („uczenie się”) demonstrable; style 1-shot retrieval skipped (templates already copy BKS formulas) | T25, T17, T08, T06 |
| P4 dispatch packet + Ad tiers + tray | adopt (top value) | Mirrors Zarządzenie § 10–11; fixes the silent misplacement in case 543 | T24, T06, T07, T12 |
| P5 security scanner + injection shield | adopt | 20 % criterion; UMB list includes signatures and images | T26, T05, T10 |
| P6 modes + 2 calls | adopt, wording changed | „0 B ruchu” only as „połączenia zewnętrzne zablokowane”, enforced in code (`UDIP_OFFLINE`); Bielik-11B tag corrected to v3.1 (verified on Ollama) | T10, T11, T12, T23 |
| P7 calendar polish, days off, sub-deadlines, extension button | adopt | Closes the Saturday-holiday gap; most of the rest already built | T04 |
| P8 scan viewer, provenance, BIP banner, legal wording | adopt | Legal advisory wording is more precise than ours | T05, T07, T06, T08 |
| P9 canvas redactor | skip | Low value per hour | — |
| Cuts: chat, 50-case suite, 4 calls, ICS | adopt (synthetic set kept small at ~20 cases for archive breadth, by team decision) | | T20 dropped, T14/T15 reshaped |
| Qwen2.5-VL-7B as offline VLM | verify before use | Licence not checked by us | T13, T21 |
