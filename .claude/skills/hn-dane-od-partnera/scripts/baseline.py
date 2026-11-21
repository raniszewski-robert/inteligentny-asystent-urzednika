#!/usr/bin/env python3
"""Baseline bez GPU dla typowych zadan. Porownuje proste modele z modelem naiwnym i zapisuje predykcje.

  python3 baseline.py --task tabular-clf --train split/train.csv --valid split/valid.csv --target etykieta --id id
  python3 baseline.py --task regression  --train split/train.csv --valid split/valid.csv --target cena
  python3 baseline.py --task text-clf    --train split/train.csv --valid split/valid.csv --target kategoria --text-col tresc
  python3 baseline.py --task image-clf   --train obrazy/                      # klasa = podkatalog
  python3 baseline.py --task anomaly     --train dane.csv [--target czy_anomalia]   # etykieta tylko do oceny

Bez --valid skrypt sam odklada 20% danych. Z --predict test.csv zapisuje tez submission.csv.
Wyniki w --out-dir (domyslnie baseline_out/): valid_predictions.csv, metrics.json, model.joblib.

Zaleznosci: pandas, numpy, scikit-learn, joblib (BSD-3); Pillow (MIT-CMU) dla obrazow.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor, IsolationForest, RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.model_selection import train_test_split
from sklearn.pipeline import FeatureUnion, Pipeline, make_pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler
from sklearn.svm import LinearSVC

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import IMAGE_EXT, read_table, write_table  # noqa: E402
from metrics import classification, ranking, regression  # noqa: E402

SEED = 42


def pick_columns(df: pd.DataFrame, drop: list[str]) -> tuple[list[str], list[str], list[str]]:
    """Dzieli kolumny na liczbowe i kategoryczne; odrzuca stale, identyfikatory i tekst o wysokiej licznosci."""
    num, cat, skipped = [], [], []
    n = len(df)
    for col in df.columns:
        if col in drop:
            continue
        s = df[col]
        if s.nunique(dropna=True) <= 1:
            skipped.append(f"{col} (stala)")
        elif pd.api.types.is_bool_dtype(s) or pd.api.types.is_numeric_dtype(s):
            num.append(col)
        elif pd.api.types.is_datetime64_any_dtype(s):
            skipped.append(f"{col} (data: dodaj cechy recznie)")
        elif s.nunique() > max(50, 0.3 * n):
            skipped.append(f"{col} (tekst albo identyfikator, {s.nunique()} wartosci)")
        else:
            cat.append(col)
    return num, cat, skipped


def tabular_prep(num: list[str], cat: list[str], linear: bool) -> ColumnTransformer:
    num_steps = [SimpleImputer(strategy="median")] + ([StandardScaler()] if linear else [])
    encoder = (OneHotEncoder(handle_unknown="ignore", min_frequency=2) if linear
               else OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1))
    cat_pipe = make_pipeline(SimpleImputer(strategy="constant", fill_value="_brak_"), encoder)
    return ColumnTransformer([("num", make_pipeline(*num_steps), num), ("cat", cat_pipe, cat)])


def to_frame_types(df: pd.DataFrame, num: list[str], cat: list[str]) -> pd.DataFrame:
    out = df[num + cat].copy()
    for c in num:
        out[c] = pd.to_numeric(out[c], errors="coerce").astype(float)
    for c in cat:
        out[c] = out[c].astype(object).where(out[c].notna(), None).map(lambda v: None if v is None else str(v))
    return out


def scores_of(model, X) -> np.ndarray | None:
    """Wynik dla klasy pozytywnej (ostatniej alfabetycznie) w klasyfikacji binarnej."""
    if len(getattr(model, "classes_", [])) != 2:
        return None
    if hasattr(model, "predict_proba"):
        return model.predict_proba(X)[:, 1]
    if hasattr(model, "decision_function"):
        return model.decision_function(X)
    return None


def run_models(models: dict, Xtr, ytr, Xva, yva, clf: bool) -> tuple[str, dict, dict]:
    results, fitted = {}, {}
    for name, model in models.items():
        t0 = time.time()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model.fit(Xtr, ytr)
        pred = model.predict(Xva)
        if clf:
            sc = scores_of(model, Xva)
            res = classification(pd.Series(yva), pd.Series(pred), pd.Series(sc) if sc is not None else None)
            line = f"F1 macro {res['f1_macro']:.4f}  accuracy {res['accuracy']:.4f}" + (f"  ROC-AUC {res['roc_auc']:.4f}" if "roc_auc" in res else "")
        else:
            res = regression(pd.Series(yva), pd.Series(pred))
            line = f"MAE {res['mae']:.4f}  RMSE {res['rmse']:.4f}  R2 {res['r2']:.4f}"
        res["fit_seconds"] = round(time.time() - t0, 2)
        results[name], fitted[name] = res, model
        print(f"  {name:<22} {line}  ({res['fit_seconds']} s)")
    real = {k: v for k, v in results.items() if not k.startswith("naiwny")}
    best = max(real, key=lambda k: real[k]["f1_macro"]) if clf else min(real, key=lambda k: real[k]["mae"])
    return best, results, fitted


def load_images(root: Path, max_per_class: int) -> tuple[np.ndarray, np.ndarray, list[str]]:
    from PIL import Image

    X, y, names = [], [], []
    for cls_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        files = sorted(f for f in cls_dir.rglob("*") if f.suffix.lower() in IMAGE_EXT)[:max_per_class]
        for f in files:
            try:
                with Image.open(f) as im:
                    rgb = im.convert("RGB")
                    small = np.asarray(rgb.resize((32, 32)), dtype=np.float32) / 255.0
                    hist = np.concatenate([np.histogram(np.asarray(rgb)[..., ch], bins=16, range=(0, 255), density=True)[0] for ch in range(3)])
            except Exception:
                continue
            X.append(np.concatenate([small.ravel(), hist * 16]))
            y.append(cls_dir.name)
            names.append(str(f.relative_to(root)))
    return np.array(X), np.array(y), names


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--task", required=True, choices=["tabular-clf", "regression", "text-clf", "image-clf", "anomaly"])
    ap.add_argument("--train", required=True)
    ap.add_argument("--valid")
    ap.add_argument("--target")
    ap.add_argument("--id", dest="id_col")
    ap.add_argument("--text-col")
    ap.add_argument("--predict", help="plik (albo katalog obrazow) do predykcji koncowej")
    ap.add_argument("--max-per-class", type=int, default=500, help="limit obrazow na klase")
    ap.add_argument("--out-dir", default="baseline_out")
    args = ap.parse_args()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    clf = args.task in ("tabular-clf", "text-clf", "image-clf")

    # ---------- obrazy ----------
    if args.task == "image-clf":
        X, y, names = load_images(Path(args.train), args.max_per_class)
        if len(set(y)) < 2:
            print("BLAD: potrzebne co najmniej dwa podkatalogi klas z obrazami.", file=sys.stderr)
            return 2
        if args.valid:
            Xtr, ytr = X, y
            Xva, yva, keys = load_images(Path(args.valid), args.max_per_class)
        else:
            Xtr, Xva, ytr, yva, _, keys = train_test_split(X, y, names, test_size=0.2, random_state=SEED, stratify=y)
        print(f"Obrazy: train {len(Xtr)}, walidacja {len(Xva)}, klas {len(set(y))}, cech {X.shape[1]} (piksele 32x32 + histogram barw).")
        models = {"naiwny (najczestsza)": DummyClassifier(strategy="most_frequent"),
                  "regresja logistyczna": make_pipeline(StandardScaler(), LogisticRegression(max_iter=500, C=0.1)),
                  "las losowy": RandomForestClassifier(n_estimators=200, random_state=SEED, n_jobs=-1, class_weight="balanced")}
        best, results, fitted = run_models(models, Xtr, ytr, Xva, yva, True)
        preds = pd.DataFrame({"plik": keys, "y_true": yva, "y_pred": fitted[best].predict(Xva)})
        if args.predict:
            Xte, _, te_names = load_images(Path(args.predict), 10**9)
            write_table(pd.DataFrame({"plik": te_names, "y_pred": fitted[best].predict(Xte)}), out / "submission.csv")
    else:
        if not args.target and args.task != "anomaly":
            print("BLAD: podaj --target.", file=sys.stderr)
            return 2
        train, _ = read_table(args.train)
        if args.target and args.target not in train.columns:
            print(f"BLAD: brak kolumny `{args.target}`. Dostepne: {list(train.columns)}", file=sys.stderr)
            return 2
        if args.target and args.task != "anomaly":
            train = train.dropna(subset=[args.target])
        if args.valid:
            valid, _ = read_table(args.valid)
        elif args.task == "anomaly":
            valid = train
        else:
            y_all = train[args.target]
            strat = y_all if clf and y_all.value_counts().min() >= 2 else None
            train, valid = train_test_split(train, test_size=0.2, random_state=SEED, stratify=strat)
            print("Brak --valid: odlozono 20% danych na walidacje.")
        keys = valid[args.id_col].values if args.id_col and args.id_col in valid.columns else np.arange(len(valid))
        key_name = args.id_col or "wiersz"
        test = read_table(args.predict)[0] if args.predict else None

        # ---------- tekst ----------
        if args.task == "text-clf":
            if not args.text_col or args.text_col not in train.columns:
                print(f"BLAD: podaj --text-col. Dostepne kolumny: {list(train.columns)}", file=sys.stderr)
                return 2
            prep = lambda d: d[args.text_col].fillna("").astype(str)  # noqa: E731
            ytr, yva = train[args.target].astype(str), valid[args.target].astype(str)
            feats = lambda: FeatureUnion([  # noqa: E731
                ("slowa", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=2, max_features=200_000)),
                ("znaki", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True, min_df=2, max_features=300_000))])
            models = {"naiwny (najczestsza)": DummyClassifier(strategy="most_frequent"),
                      "tfidf + reg. logist.": Pipeline([("f", feats()), ("m", LogisticRegression(max_iter=2000, C=10, class_weight="balanced"))]),
                      "tfidf + LinearSVC": Pipeline([("f", feats()), ("m", LinearSVC(class_weight="balanced"))])}
            Xtr, Xva = prep(train), prep(valid)
            print(f"Tekst: train {len(Xtr)}, walidacja {len(Xva)}, klas {ytr.nunique()}. Cechy: TF-IDF slow (1-2) i znakow (2-5), dobre dla polskiej fleksji.")
            best, results, fitted = run_models(models, Xtr, ytr, Xva, yva, True)
            Xte = prep(test) if test is not None else None
        # ---------- tabela: klasyfikacja, regresja, anomalie ----------
        else:
            drop = [c for c in (args.target, args.id_col) if c]
            num, cat, skipped = pick_columns(train, drop)
            if not num and not cat:
                print("BLAD: po odrzuceniu identyfikatorow i tekstu nie zostala zadna cecha.", file=sys.stderr)
                return 2
            print(f"Cechy: {len(num)} liczbowych, {len(cat)} kategorycznych." + (f" Pominieto: {', '.join(skipped)}." if skipped else ""))
            Xtr, Xva = to_frame_types(train, num, cat), to_frame_types(valid, num, cat)
            Xte = to_frame_types(test, num, cat) if test is not None else None

            if args.task == "anomaly":
                model = make_pipeline(tabular_prep(num, cat, linear=False), IsolationForest(n_estimators=300, random_state=SEED))
                model.fit(Xtr)
                score = -model.score_samples(Xva)
                z = Xva[num].apply(lambda s: (s - s.median()).abs() / (1.4826 * (s - s.median()).abs().median() + 1e-9)).max(axis=1).fillna(0) if num else pd.Series(0, index=Xva.index)
                preds = pd.DataFrame({key_name: keys, "score": score, "score_naiwny_zscore": z.values})
                results = {"n": len(Xva)}
                if args.target:
                    preds["y_true"] = valid[args.target].values
                    results["isolation_forest"] = ranking(valid[args.target], pd.Series(score))
                    results["naiwny (max z-score)"] = ranking(valid[args.target], pd.Series(z.values))
                    for name in ("naiwny (max z-score)", "isolation_forest"):
                        r = results[name]
                        print(f"  {name:<22} " + (f"ROC-AUC {r['roc_auc']:.4f}  PR-AUC {r['pr_auc']:.4f}  (klasa pozytywna: {r['positive_class']})" if "roc_auc" in r else str(r)))
                else:
                    print("  Brak etykiet: nie da sie policzyc metryki. Przejrzyj recznie wiersze o najwyzszym wyniku.")
                print("Najbardziej podejrzane wiersze:")
                print(preds.sort_values("score", ascending=False).head(10).to_string(index=False))
                write_table(preds, out / "valid_predictions.csv")
                joblib.dump(model, out / "model.joblib")
                (out / "metrics.json").write_text(json.dumps(results, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
                print(f"Zapisano: {out}/valid_predictions.csv, metrics.json, model.joblib")
                return 0

            if clf:
                ytr, yva = train[args.target].astype(str), valid[args.target].astype(str)
                models = {"naiwny (najczestsza)": DummyClassifier(strategy="most_frequent"),
                          "regresja logistyczna": make_pipeline(tabular_prep(num, cat, True), LogisticRegression(max_iter=2000, class_weight="balanced")),
                          "gradient boosting": make_pipeline(tabular_prep(num, cat, False), HistGradientBoostingClassifier(random_state=SEED, class_weight="balanced"))}
            else:
                ytr, yva = train[args.target].astype(float), valid[args.target].astype(float)
                models = {"naiwny (mediana)": DummyRegressor(strategy="median"),
                          "regresja grzbietowa": make_pipeline(tabular_prep(num, cat, True), Ridge(alpha=1.0)),
                          "gradient boosting": make_pipeline(tabular_prep(num, cat, False), HistGradientBoostingRegressor(random_state=SEED))}
            print(f"Train {len(Xtr)}, walidacja {len(Xva)}.")
            best, results, fitted = run_models(models, Xtr, ytr, Xva, yva, clf)

        preds = pd.DataFrame({key_name: keys, "y_true": np.asarray(yva), "y_pred": fitted[best].predict(Xva)})
        if clf:
            sc = scores_of(fitted[best], Xva)
            if sc is not None:
                preds["score"] = sc
        if test is not None:
            sub_keys = test[args.id_col].values if args.id_col and args.id_col in test.columns else np.arange(len(test))
            write_table(pd.DataFrame({key_name: sub_keys, args.target: fitted[best].predict(Xte)}), out / "submission.csv")

    naive = next(k for k in results if k.startswith("naiwny"))
    metric = "f1_macro" if clf else "mae"
    print(f"Najlepszy: {best} ({metric} {results[best][metric]:.4f}; naiwny {results[naive][metric]:.4f}).")
    gain = results[best][metric] - results[naive][metric] if clf else results[naive][metric] - results[best][metric]
    if gain <= 0:
        print("UWAGA: model nie jest lepszy od naiwnego. Sprawdz cechy, etykiety i podzial, zanim zaczniesz stroic.")
    write_table(preds, out / "valid_predictions.csv")
    joblib.dump(fitted[best], out / "model.joblib")
    (out / "metrics.json").write_text(json.dumps({"best": best, "results": results}, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    print(f"Zapisano: {out}/valid_predictions.csv, metrics.json, model.joblib" + (", submission.csv" if args.predict else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
