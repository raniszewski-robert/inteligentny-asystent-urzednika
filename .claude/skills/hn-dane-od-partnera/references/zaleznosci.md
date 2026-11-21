# Zależności i licencje: hn-dane-od-partnera

Wersje, na których skrypty były uruchomione 2026-11-17 (Python 3.13.18). Licencje odczytane z metadanych zainstalowanych paczek (`importlib.metadata`).

| Paczka | Wersja | Licencja | Do czego |
|---|---|---|---|
| pandas | 3.0.5 | BSD-3-Clause | wczytywanie i profil tabel |
| numpy | 2.5.3 | BSD-3-Clause (z dodatkami 0BSD, MIT, Zlib, CC0) | obliczenia |
| scikit-learn | 1.9.1 | BSD-3-Clause | podział, modele, metryki |
| joblib | 1.6.0 | BSD-3-Clause | zapis modelu |
| Pillow | 12.3.0 | MIT-CMU | obrazy |
| pypdf | 6.17.0 | BSD-3-Clause | tekst z PDF-ów |
| pyarrow | 26.0.1 | Apache-2.0 | Parquet |
| openpyxl | 3.1.5 | MIT | Excel (.xlsx) |
| reportlab | 5.0.1 | BSD | tylko generowanie PDF-ów testowych w `make_test_data.py` |

Wszystkie licencje są permisywne. Żadna zależność nie jest copyleft, więc skrypty można włączyć do rozwiązania, do którego Partner nabywa prawa (po potwierdzeniu u organizatora, że wcześniej przygotowany kod jest dozwolony, i po ujawnieniu go w zgłoszeniu).

## Instalacja

```bash
python3 -m pip install "pandas>=2.2" numpy scikit-learn joblib Pillow pypdf pyarrow openpyxl
python3 -m pip install reportlab     # tylko do smoke_test.sh
```

Zainstaluj i uruchom `bash scripts/smoke_test.sh` **przed wyjazdem**: paczki ważą łącznie kilkaset MB, a Wi-Fi na sali może być przeciążone. Skrypty nie potrzebują sieci (poza opcją `--with-sms` w teście).

## Dane testowe

| Zbiór | Pochodzenie | Licencja |
|---|---|---|
| wine, diabetes, breast_cancer, digits | dołączone do scikit-learn (`sklearn.datasets.load_*`), pierwotnie UCI | dane publiczne, dystrybuowane z scikit-learn (BSD-3) |
| SMS Spam Collection (opcjonalnie) | UCI Machine Learning Repository, pobierany z kopii na GitHubie | CC BY 4.0 |
| pisma_pl.csv, osoby_pii.csv, PDF-y | generowane w `make_test_data.py` | syntetyczne, zmyślone; numery PESEL i NIP są losowe z poprawną sumą kontrolną i nie należą do nikogo celowo |

Dane testowe nie są częścią pakietu. Powstają w katalogu tymczasowym przy każdym uruchomieniu testu.
