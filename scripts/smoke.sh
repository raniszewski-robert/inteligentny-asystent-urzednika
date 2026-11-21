#!/usr/bin/env bash
# Smoke test całego pakietu: wszystkie selftesty, ewaluacje i testy akceptacyjne (scenariusz jury).
# Użycie: bash scripts/smoke.sh [RRRR-MM-DD]   (domyślnie 2026-11-22)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
S="$ROOT/.claude/skills"
TODAY="${1:-2026-11-22}"
step() { echo; echo "=== $*"; }
step "Terminy";            python3 "$S/udip-kalendarz-terminy/scripts/deadlines.py" --selftest | tail -1
step "Anonimizacja";       python3 "$S/udip-anonimizacja/scripts/anonymize.py" --selftest | tail -1
step "Wczytywanie + OCR";  python3 "$S/udip-dane-i-zrodla/scripts/ingest.py" --selftest 2>/dev/null | grep -E "^(OK|BŁĄD|POMINIĘTO|Wynik)"
step "Ewaluacja (syntetyczne)"; python3 "$S/udip-ewaluacja/scripts/evaluate.py" --data "$ROOT/data-samples/syntetyczne" --today "$TODAY" | sed -n '5,10p'
step "Ewaluacja (UMB)";    python3 "$S/udip-ewaluacja/scripts/evaluate_partner.py" "$ROOT/data-partner/umb/archiwum_umb.jsonl" | tail -1
step "Pakiet udip + testy (pytest)"; python3 -c "import udip.analyze, udip.draft, udip.register, udip.llm" && python3 -m pytest -q "$ROOT/tests" 2>&1 | tail -3
step "E2E (ścieżka jury przez aplikację)"; python3 -m pytest -q "$ROOT/tests/e2e" 2>&1 | tail -1
step "Akceptacja (scenariusz jury)"; python3 "$S/udip-ewaluacja/scripts/acceptance.py" --repo "$ROOT" --today "$TODAY" 2>/dev/null | tail -n +3
echo; echo "SMOKE OK"
