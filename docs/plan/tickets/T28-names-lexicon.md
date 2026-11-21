# T28 – Bigger name lexicon + optional local NER

**Lane:** A – core · **Status:** done · **Estimate:** 1.5 h · **Blocked by:** T01

**Owns:** `udip/data/names/`, lexicon loading in `udip/anonymize.py`, `scripts/build_names.py`

## Goal

Catch common Polish and Ukrainian names the 157-name list misses (jury test 3 uses its own file).

## Scope

- Needs the team: name lists from dane.gov.pl (first names and surnames from the PESEL register) downloaded into the UMB folder, or dane.gov.pl allowed. **Verify and record the licence** before bundling.
- Compact local file (top ~5 000 first names, ~30 000 surnames) + common Ukrainian/Belarusian transliterations; surname detection beyond -ski/-cka/-wicz.
- Optional NER behind `UDIP_NER=gliner`: try `flowxai/cee-pii` and `urchade/gliner_multi_pii-v1` (both Apache-2.0 per model cards; Polish support to be measured), `local_files_only`; absent weights → silent fallback. Only if weights can be fetched and install stays reasonable on Windows.

## Acceptance criteria

- [x] `pii_torture_test.docx` (Bogumił Krawczyk, Bożena Zając, Olena Shevchenko, PESEL, KW, plot with owner, IBAN, business-secret sentence + Rafał Bruski as Prezydent, ul. Jezuicka 1, ul. św. Maksymiliana Kolbego) → 0 leaks on private data, 0 false positives on official/address/patron, with network disabled.
- [x] Licence of every bundled list or model recorded in `udip/data/names/README.md`.

> Dropped to 'lexicon only' if the name lists can't be obtained; GLiNER is the first thing to cut in this ticket.


## As built (21.11, coordinator)

dane.gov.pl was unreachable from both the cloud workspace and the laptop shell, so the lexicon is built from Faker and Mimesis (MIT) name lists, with Polish inflected forms and ambiguity flags from SGJP via Morfeusz 2 (BSD-2, build time only). Ukrainian and Russian names are added in passport and Polish transliteration. The torture document is built in `tests/core/test_names_lexicon.py` (not a committed fixture). A business-secret sentence rule (`TAJEMNICA`, review) was added for the acceptance criteria. GLiNER dropped.
