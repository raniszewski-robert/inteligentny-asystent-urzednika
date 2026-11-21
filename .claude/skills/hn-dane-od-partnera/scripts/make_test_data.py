#!/usr/bin/env python3
"""Tworzy male zbiory testowe do proby generalnej skryptow (smoke_test.sh).

Zrodla:
  - wine, diabetes, breast_cancer, digits: zbiory dolaczone do scikit-learn (BSD-3; dane z UCI, publiczne),
  - pisma_pl.csv, osoby_pii.csv, PDF-y: dane syntetyczne generowane tutaj (zmyslone, bez prawdziwych osob),
  - sms.tsv (opcjonalnie, --with-sms): SMS Spam Collection z UCI (CC BY 4.0), pobierany z GitHuba.

  python3 make_test_data.py /tmp/hn-test-data [--with-sms]

Zaleznosci: scikit-learn, pandas, numpy, Pillow, pyarrow, openpyxl; reportlab (BSD) tylko do PDF-ow testowych.
"""
from __future__ import annotations

import json
import random
import sys
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn import datasets

SMS_URL = "https://raw.githubusercontent.com/justmarkham/pycon-2016-tutorial/master/data/sms.tsv"
rnd = random.Random(7)


def gen_pesel() -> str:
    y, m, d = rnd.randint(1950, 1999), rnd.randint(1, 12), rnd.randint(1, 28)
    base = f"{y % 100:02d}{m:02d}{d:02d}{rnd.randint(0, 9999):04d}"
    c = (10 - sum(int(a) * w for a, w in zip(base, (1, 3, 7, 9, 1, 3, 7, 9, 1, 3))) % 10) % 10
    return base + str(c)


def gen_nip() -> str:
    while True:
        base = "".join(str(rnd.randint(0, 9)) for _ in range(9))
        c = sum(int(a) * w for a, w in zip(base, (6, 5, 7, 2, 3, 4, 5, 6, 7))) % 11
        if c != 10:
            return base + str(c)


def tabular(out: Path) -> None:
    wine = datasets.load_wine(as_frame=True).frame.rename(columns={"target": "klasa"})
    wine["klasa"] = wine["klasa"].map({0: "A", 1: "B", 2: "C"})
    wine.insert(0, "id", [f"W{i:04d}" for i in range(len(wine))])
    wine["region"] = [rnd.choice(["północ", "południe", "wschód"]) for _ in range(len(wine))]
    wine["producent"] = [f"P{rnd.randint(1, 30):02d}" for _ in range(len(wine))]
    wine["stala"] = 1
    wine.loc[wine.sample(12, random_state=1).index, "magnesium"] = np.nan
    dirty = pd.concat([wine, wine.iloc[:4]], ignore_index=True)           # 4 pelne duplikaty
    dirty.to_csv(out / "wine.csv", index=False, sep=";", encoding="cp1250")  # typowy polski eksport
    wine.to_excel(out / "wine.xlsx", index=False)
    wine.to_parquet(out / "wine.parquet", index=False)
    wine.to_json(out / "wine.jsonl", orient="records", lines=True, force_ascii=False)
    (out / "wine_nested.json").write_text(json.dumps({"meta": {"zrodlo": "test"}, "rekordy": wine.head(20).to_dict("records")}), encoding="utf-8")
    tr, te = wine.iloc[:140], pd.concat([wine.iloc[140:], wine.iloc[:5]])   # 5 wierszy przecieka do testu
    tr.to_csv(out / "wine_train.csv", index=False)
    te.drop(columns="klasa").to_csv(out / "wine_test.csv", index=False)
    te[["id"]].assign(klasa="A").to_csv(out / "sample_submission.csv", index=False)
    te[["id"]].assign(klasa="Z").iloc[:-2].to_csv(out / "bad_submission.csv", index=False)

    diab = datasets.load_diabetes(as_frame=True).frame.rename(columns={"target": "wynik"})
    diab.insert(0, "id", range(len(diab)))
    diab.to_csv(out / "diabetes.csv", index=False)

    bc = datasets.load_breast_cancer(as_frame=True).frame
    bc["anomalia"] = (bc.pop("target") == 0).astype(int)                   # zlosliwe = 1
    bc = pd.concat([bc[bc.anomalia == 0], bc[bc.anomalia == 1].sample(25, random_state=0)]).sample(frac=1, random_state=0)
    bc.insert(0, "id", range(len(bc)))
    bc.to_csv(out / "anomalie.csv", index=False)


def images(out: Path) -> None:
    from PIL import Image

    digits = datasets.load_digits()
    root = out / "obrazy"
    counts = {}
    for img, label in zip(digits.images, digits.target):
        if label > 3 or counts.get(label, 0) >= 60:
            continue
        counts[label] = counts.get(label, 0) + 1
        d = root / f"cyfra_{label}"
        d.mkdir(parents=True, exist_ok=True)
        Image.fromarray((img / 16 * 255).astype(np.uint8)).resize((32, 32)).save(d / f"{counts[label]:03d}.png")
    (root / "cyfra_1" / "duplikat.png").write_bytes((root / "cyfra_0" / "001.png").read_bytes())
    (root / "cyfra_2" / "zepsuty.png").write_bytes(b"to nie jest obraz")


def texts(out: Path, with_sms: bool) -> None:
    parts = {
        "skarga": (["Składam skargę na", "Zgłaszam zastrzeżenia do", "Protestuję przeciwko"], ["opieszałość urzędu", "błędną decyzję", "brak odpowiedzi"], ["Żądam wyjaśnień.", "Proszę o interwencję.", "Sprawa trwa zbyt długo."]),
        "wniosek": (["Wnoszę o", "Zwracam się z wnioskiem o", "Proszę o wydanie"], ["zaświadczenia o niezaleganiu", "odpisu aktu", "pozwolenia na budowę"], ["Załączam wymagane dokumenty.", "Opłatę uiściłem.", "Proszę o pilne rozpatrzenie."]),
        "zapytanie": (["Czy mogę", "Kiedy można", "Gdzie należy"], ["złożyć deklarację", "odebrać dowód osobisty", "zarejestrować pojazd"], ["Dziękuję za informację.", "Proszę o odpowiedź mailową.", "Nie znalazłem tego na stronie."]),
        "podziekowanie": (["Dziękuję za", "Chciałbym podziękować za", "Serdecznie dziękuję za"], ["sprawną obsługę", "życzliwą pomoc", "szybkie załatwienie sprawy"], ["Pozdrawiam.", "Tak trzymać.", "Miła niespodzianka."]),
    }
    rows = []
    for label, (a, b, c) in parts.items():
        for i in range(60):
            rows.append({"id": f"{label[:2]}{i:03d}", "tresc": f"{rnd.choice(a)} {rnd.choice(b)} nr {rnd.randint(1, 999)}/2026. {rnd.choice(c)}", "kategoria": label})
    pd.DataFrame(rows).sample(frac=1, random_state=3).to_csv(out / "pisma_pl.csv", index=False)

    names = ["Jan Testowy", "Anna Przykladowa", "Piotr Zmyslony", "Ewa Fikcyjna"]
    pii = pd.DataFrame({"id": range(40), "imie_nazwisko": [rnd.choice(names) for _ in range(40)], "pesel": [gen_pesel() for _ in range(40)],
                        "kontakt": [f"tel. {rnd.randint(500, 799)} {rnd.randint(100, 999)} {rnd.randint(100, 999)}, osoba{i}@example.com" for i in range(40)],
                        "kwota": [rnd.randint(100, 9000) for _ in range(40)]})
    pii.to_csv(out / "osoby_pii.csv", index=False)

    if with_sms:
        try:
            urllib.request.urlretrieve(SMS_URL, out / "sms.tsv")
            df = pd.read_csv(out / "sms.tsv", sep="\t", header=None, names=["etykieta", "tresc"])
            df.insert(0, "id", range(len(df)))
            df.to_csv(out / "sms.csv", index=False)
            (out / "sms.tsv").unlink()
            print(f"  sms.csv: {len(df)} wierszy (SMS Spam Collection, CC BY 4.0)")
        except Exception as exc:  # brak sieci nie przerywa testu
            print(f"  sms.csv pominiety: {type(exc).__name__}: {exc}")


def pdfs(out: Path) -> None:
    from PIL import Image
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    root = out / "pdf"
    root.mkdir(exist_ok=True)
    gold = []
    for i in range(3):
        nip, date, amount = gen_nip(), f"{rnd.randint(1, 28):02d}.{rnd.randint(1, 12):02d}.2026", f"{rnd.randint(1, 9)} {rnd.randint(100, 999)},50 zl"
        mail = f"biuro{i}@example.com"
        c = canvas.Canvas(str(root / f"faktura_{i}.pdf"), pagesize=A4)
        lines = [f"Faktura VAT nr {i + 1}/2026", f"Data wystawienia: {date}", f"Sprzedawca: Firma Testowa {i} sp. z o.o., NIP: {nip[:3]}-{nip[3:6]}-{nip[6:8]}-{nip[8:]}",
                 f"Kontakt: {mail}, 85-001 Bydgoszcz", f"Do zaplaty: {amount}", "Numer zamowienia 12345678901 nie jest numerem PESEL."]
        for j, line in enumerate(lines):
            c.drawString(60, 780 - 22 * j, line)
        c.save()
        gold.append({"doc": f"faktura_{i}.pdf", "fields": {"nip": [nip], "data": [date], "kwota": [amount], "email": [mail], "kod_pocztowy": ["85-001"]}})
    img = Image.fromarray((np.random.default_rng(0).random((200, 300)) * 255).astype(np.uint8))
    c = canvas.Canvas(str(root / "skan.pdf"), pagesize=A4)
    c.drawImage(ImageReader(img), 60, 500, width=300, height=200)
    c.save()
    gold.append({"doc": "skan.pdf", "fields": {"nip": ["0000000000"]}})
    (out / "gold_pdf.jsonl").write_text("\n".join(json.dumps(g, ensure_ascii=False) for g in gold) + "\n", encoding="utf-8")


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    tabular(out)
    images(out)
    texts(out, "--with-sms" in sys.argv)
    pdfs(out)
    print(f"Dane testowe w {out}: {len(list(out.rglob('*')))} plikow i katalogow.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
