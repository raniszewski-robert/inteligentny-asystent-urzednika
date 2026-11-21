# Lane E – core: safety & learning

Owns: CONTRACTS §1 row E (`udip/security.py`, `udip/export.py`, `udip/learning.py` and their tests). The calls into these modules are pre-wired by T00; implement the functions behind them. Follow `_rules.md`.

## Phase E1 (after T00)

1. **T27** export hardening + XML leak audit + redaction footer. *Report early* (lane B2 needs it for T08).
2. **T26** security scanner + prompt-injection pre-filter (build `tests/fixtures/attack_bundle.docx` with python-docx + Pillow).
3. **T25** learning loops – needs T02 on `main` (tables); rebase first. *Report early.*
