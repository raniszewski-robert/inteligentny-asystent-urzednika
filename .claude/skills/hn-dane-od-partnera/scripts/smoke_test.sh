#!/usr/bin/env bash
# Proba generalna skryptow hn-dane-od-partnera na malych zbiorach publicznych i syntetycznych.
# Uruchom przed wyjazdem na laptopie, ktory pojedzie na hackathon:
#   bash smoke_test.sh            # dane w katalogu tymczasowym
#   bash smoke_test.sh --with-sms # dodatkowo pobiera publiczny zbior SMS (wymaga sieci)
# Kod wyjscia: 0 = wszystkie kroki przeszly.
set -u
S="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
D="$(mktemp -d "${TMPDIR:-/tmp}/hn-dane-XXXXXX")"
PASS=0; FAIL=0
LOG="$D/log.txt"

step() { # step "nazwa" oczekiwany_kod polecenie...
  local name="$1" want="$2"; shift 2
  "$@" >"$D/out.txt" 2>&1; local got=$?
  { echo "=== $name (kod $got, oczekiwany $want)"; cat "$D/out.txt"; echo; } >>"$LOG"
  if [ "$got" -eq "$want" ]; then PASS=$((PASS+1)); echo "PASS  $name"; else FAIL=$((FAIL+1)); echo "FAIL  $name (kod $got, oczekiwany $want)"; tail -5 "$D/out.txt" | sed 's/^/      /'; fi
}

echo "Dane testowe: $D"
step "make_test_data" 0 python3 "$S/make_test_data.py" "$D/data" "$@"
cd "$D" || exit 1

step "profil CSV (cp1250, srednik)"   0 python3 "$S/profile_dataset.py" data/wine.csv --target klasa --id id --out profil_wine.md
step "profil Excel"                   0 python3 "$S/profile_dataset.py" data/wine.xlsx --target klasa
step "profil Parquet"                 0 python3 "$S/profile_dataset.py" data/wine.parquet --target klasa
step "profil JSONL"                   0 python3 "$S/profile_dataset.py" data/wine.jsonl --target klasa
step "profil JSON zagniezdzony"       0 python3 "$S/profile_dataset.py" data/wine_nested.json
step "profil regresja"                0 python3 "$S/profile_dataset.py" data/diabetes.csv --target wynik --id id
step "profil dane osobowe"            0 python3 "$S/profile_dataset.py" data/osoby_pii.csv --out profil_pii.md
step "profil wyciek train/test"       0 python3 "$S/profile_dataset.py" data/wine_train.csv --compare data/wine_test.csv --id id --target klasa --out profil_leak.md
step "profil katalog obrazow"         0 python3 "$S/profile_dataset.py" data/obrazy --out profil_obrazy.md
step "profil katalog PDF"             0 python3 "$S/profile_dataset.py" data/pdf --out profil_pdf.md
step "profil brak pliku"              2 python3 "$S/profile_dataset.py" data/nie_ma.csv

step "podzial stratyfikowany"         0 python3 "$S/make_split.py" data/wine.csv --target klasa --out-dir split_wine
step "podzial grupowy (30 grup)"      0 python3 "$S/make_split.py" data/wine.csv --target klasa --group producent --out-dir split_group
step "podzial grupowy (3 grupy)"      0 python3 "$S/make_split.py" data/wine.csv --target klasa --group region --out-dir split_group3
step "podzial czasowy: zla data"      2 python3 "$S/make_split.py" data/wine.csv --target klasa --time region
step "podzial losowy (regresja)"      0 python3 "$S/make_split.py" data/diabetes.csv --target wynik --out-dir split_diab
step "podzial zla kolumna"            2 python3 "$S/make_split.py" data/wine.csv --target nie_ma

step "baseline klasyfikacja tabel."   0 python3 "$S/baseline.py" --task tabular-clf --train split_wine/train.csv --valid split_wine/valid.csv --target klasa --id id --predict data/wine_test.csv --out-dir bl_wine
step "baseline regresja"              0 python3 "$S/baseline.py" --task regression --train split_diab/train.csv --valid split_diab/valid.csv --target wynik --id id --out-dir bl_diab
step "baseline tekst (PL, syntet.)"   0 python3 "$S/baseline.py" --task text-clf --train data/pisma_pl.csv --target kategoria --text-col tresc --id id --out-dir bl_pisma
step "baseline obrazy"                0 python3 "$S/baseline.py" --task image-clf --train data/obrazy --out-dir bl_obrazy
step "baseline anomalie"              0 python3 "$S/baseline.py" --task anomaly --train data/anomalie.csv --target anomalia --id id --out-dir bl_anom
if [ -f data/sms.csv ]; then
  step "baseline tekst (SMS, publ.)"  0 python3 "$S/baseline.py" --task text-clf --train data/sms.csv --target etykieta --text-col tresc --id id --out-dir bl_sms
fi

step "metryki klasyfikacja"           0 python3 "$S/metrics.py" --task clf --truth split_wine/valid.csv --pred bl_wine/valid_predictions.csv --key id --truth-col klasa --pred-col y_pred --out m_wine.json
step "metryki regresja"               0 python3 "$S/metrics.py" --task reg --truth split_diab/valid.csv --pred bl_diab/valid_predictions.csv --key id --truth-col wynik --pred-col y_pred
step "metryki anomalie (ROC-AUC)"     0 python3 "$S/metrics.py" --task anomaly --truth data/anomalie.csv --pred bl_anom/valid_predictions.csv --key id --truth-col anomalia --score-col score
step "metryki brak klucza"            2 python3 "$S/metrics.py" --task clf --truth split_wine/valid.csv --pred bl_wine/valid_predictions.csv --key nie_ma --truth-col klasa

step "walidator: poprawny plik"       0 python3 "$S/validate_submission.py" bl_wine/submission.csv --sample data/sample_submission.csv --key id --labels A,B,C
step "walidator: zly plik"            1 python3 "$S/validate_submission.py" data/bad_submission.csv --sample data/sample_submission.csv --key id --labels A,B,C

step "ekstrakcja z PDF"               0 python3 "$S/extract_fields.py" run data/pdf --out ext.jsonl
step "ekstrakcja: ocena"              0 python3 "$S/extract_fields.py" eval --pred ext.jsonl --gold data/gold_pdf.jsonl

echo
echo "Wynik: $PASS PASS, $FAIL FAIL. Pelny log: $LOG"
[ "$FAIL" -eq 0 ]
