#!/usr/bin/env python3
"""Harness metryk: liczy wynik z pliku prawdy i pliku predykcji, laczac je po kluczu.

  python3 metrics.py --task clf --truth valid.csv --pred pred.csv --key id --truth-col etykieta --pred-col y_pred
  python3 metrics.py --task clf ... --score-col proba        # dodatkowo ROC-AUC i PR-AUC (klasyfikacja binarna)
  python3 metrics.py --task reg --truth valid.csv --pred pred.csv --key id --truth-col cena --pred-col y_pred
  python3 metrics.py --task anomaly --truth valid.csv --pred pred.csv --key id --truth-col czy_anomalia --score-col score

Bez --key pliki sa laczone po kolejnosci wierszy (musza miec te sama dlugosc).
Wynik: tekst na ekranie i JSON (--out).
Zaleznosci: pandas, numpy, scikit-learn (BSD-3).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn import metrics as M

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import read_table  # noqa: E402


def classification(y_true: pd.Series, y_pred: pd.Series, score: pd.Series | None) -> dict:
    y_true, y_pred = y_true.astype(str), y_pred.astype(str)
    labels = sorted(set(y_true) | set(y_pred))
    res = {"n": int(len(y_true)), "accuracy": M.accuracy_score(y_true, y_pred),
           "balanced_accuracy": M.balanced_accuracy_score(y_true, y_pred)}
    for avg in ("macro", "micro", "weighted"):
        p, r, f, _ = M.precision_recall_fscore_support(y_true, y_pred, average=avg, zero_division=0)
        res[f"precision_{avg}"], res[f"recall_{avg}"], res[f"f1_{avg}"] = p, r, f
    p, r, f, s = M.precision_recall_fscore_support(y_true, y_pred, labels=labels, zero_division=0)
    res["per_class"] = {lab: {"precision": float(p[i]), "recall": float(r[i]), "f1": float(f[i]), "support": int(s[i])} for i, lab in enumerate(labels)}
    res["labels"] = labels
    res["confusion_matrix"] = M.confusion_matrix(y_true, y_pred, labels=labels).tolist()
    unseen = sorted(set(y_pred) - set(y_true))
    if unseen:
        res["warning"] = f"predykcje zawieraja etykiety nieobecne w prawdzie: {unseen}"
    if score is not None and len(set(y_true)) == 2:
        res.update(ranking(y_true, score))
    return res


def ranking(y_true: pd.Series, score: pd.Series, positive: str | None = None) -> dict:
    y_true = y_true.astype(str)
    classes = sorted(set(y_true))
    if len(classes) != 2:
        return {"warning_auc": f"ROC-AUC wymaga dwoch klas, sa: {classes}"}
    pos = positive if positive is not None else classes[-1]
    y_bin = (y_true == pos).astype(int)
    return {"positive_class": pos, "roc_auc": M.roc_auc_score(y_bin, score), "pr_auc": M.average_precision_score(y_bin, score)}


def regression(y_true: pd.Series, y_pred: pd.Series) -> dict:
    y_true, y_pred = y_true.astype(float), y_pred.astype(float)
    res = {"n": int(len(y_true)), "mae": M.mean_absolute_error(y_true, y_pred),
           "rmse": float(np.sqrt(M.mean_squared_error(y_true, y_pred))), "r2": M.r2_score(y_true, y_pred),
           "median_ae": M.median_absolute_error(y_true, y_pred)}
    nonzero = y_true != 0
    if nonzero.any():
        res["mape"] = float(np.mean(np.abs((y_true[nonzero] - y_pred[nonzero]) / y_true[nonzero])))
    return res


def show(res: dict) -> None:
    for k, v in res.items():
        if k in ("per_class", "confusion_matrix", "labels"):
            continue
        print(f"  {k:<20} {v:.4f}" if isinstance(v, float) else f"  {k:<20} {v}")
    if "per_class" in res:
        print("  Na klase:")
        for lab, d in res["per_class"].items():
            print(f"    {lab[:28]:<28} P {d['precision']:.3f}  R {d['recall']:.3f}  F1 {d['f1']:.3f}  n={d['support']}")
        if len(res["labels"]) <= 12:
            print("  Macierz pomylek (wiersze = prawda, kolumny = predykcja):")
            print(pd.DataFrame(res["confusion_matrix"], index=res["labels"], columns=res["labels"]).to_string(max_colwidth=12))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--task", required=True, choices=["clf", "reg", "anomaly"])
    ap.add_argument("--truth", required=True)
    ap.add_argument("--pred", required=True)
    ap.add_argument("--key")
    ap.add_argument("--truth-col", required=True)
    ap.add_argument("--pred-col", default="y_pred")
    ap.add_argument("--score-col")
    ap.add_argument("--positive", help="etykieta klasy pozytywnej dla ROC-AUC (domyslnie ostatnia alfabetycznie)")
    ap.add_argument("--out")
    args = ap.parse_args()

    truth, _ = read_table(args.truth)
    pred, _ = read_table(args.pred)
    if args.key:
        for name, df in (("prawda", truth), ("predykcje", pred)):
            if args.key not in df.columns:
                print(f"BLAD: brak klucza `{args.key}` w pliku: {name}", file=sys.stderr)
                return 2
        if pred[args.key].duplicated().any():
            print(f"BLAD: klucz `{args.key}` powtarza sie w predykcjach", file=sys.stderr)
            return 2
        merged = truth[[args.key, args.truth_col]].merge(pred, on=args.key, how="left", suffixes=("_true", ""))
        truth_col = args.truth_col + "_true" if args.truth_col in pred.columns else args.truth_col
        check_col = args.pred_col if args.task != "anomaly" else args.score_col
        missing = int(merged[check_col].isna().sum())
        if missing:
            print(f"BLAD: {missing} wierszy prawdy nie ma predykcji (brak klucza albo pusta wartosc)", file=sys.stderr)
            return 2
    else:
        if len(truth) != len(pred):
            print(f"BLAD: rozna liczba wierszy ({len(truth)} i {len(pred)}); podaj --key", file=sys.stderr)
            return 2
        merged = pred.copy()
        truth_col = "_truth"
        merged[truth_col] = truth[args.truth_col].values

    score = merged[args.score_col].astype(float) if args.score_col else None
    if args.task == "clf":
        res = classification(merged[truth_col], merged[args.pred_col], score)
        if score is not None and args.positive:
            res.update(ranking(merged[truth_col], score, args.positive))
    elif args.task == "reg":
        res = regression(merged[truth_col], merged[args.pred_col])
    else:
        if score is None:
            print("BLAD: --task anomaly wymaga --score-col (wyzszy wynik = bardziej podejrzane)", file=sys.stderr)
            return 2
        res = {"n": int(len(merged)), **ranking(merged[truth_col], score, args.positive)}
    print(f"Metryki ({args.task}):")
    show(res)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(res, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
