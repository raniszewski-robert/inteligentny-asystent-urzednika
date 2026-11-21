# Zapis uruchomień testowych: hn-dane-od-partnera

Data: 2026-11-17, Python 3.13.18, Linux, bez GPU. Polecenie: `bash scripts/smoke_test.sh --with-sms`.

**Wynik: 32 PASS, 0 FAIL.** Test obejmuje też przypadki błędne (brak pliku, zła kolumna, zły plik wynikowy) i sprawdza ich kody wyjścia.

Który skrypt uruchamia który krok `smoke_test.sh`:

| Skrypt | Kroki testu |
|---|---|
| `make_test_data.py` | „make_test_data” (tworzy wszystkie zbiory testowe) |
| `_common.py` | pośrednio we wszystkich krokach (wczytywanie formatów, wzorce PESEL, NIP, REGON i innych) |
| `profile_dataset.py` | 11 kroków „profil …” |
| `make_split.py` | 6 kroków „podzial …” |
| `baseline.py` | 6 kroków „baseline …” (z SMS) |
| `metrics.py` | 4 kroki „metryki …” |
| `validate_submission.py` | 2 kroki „walidator …” |
| `extract_fields.py` | „ekstrakcja z PDF”, „ekstrakcja: ocena” |

## Kroki i wyniki

| Krok | Dane | Wynik |
|---|---|---|
| Profil CSV | wine z brudem: średnik, cp1250, 4 duplikaty, braki, stała kolumna | Wykryto `cp1250` i separator `;`, 182 wiersze, 4 duplikaty, stałą kolumnę, 3 klasy |
| Profil Excel, Parquet, JSONL, JSON zagnieżdżony | wine | Wczytane poprawnie; w JSON-ie wybrano listę rekordów spod klucza |
| Profil regresji | diabetes | Cel rozpoznany jako regresja |
| Profil danych osobowych | 40 syntetycznych osób | PESEL: 40 trafień (z sumą kontrolną), e-mail: 40, telefon: 40; kolumna `imie_nazwisko` oznaczona po nazwie |
| Wyciek train/test | wine_train i wine_test z 5 wspólnymi wierszami | 5 wierszy o identycznych cechach, 5 wspólnych identyfikatorów, 9 kolumn o innym rozkładzie |
| Profil obrazów | 242 PNG 32×32 z digits (4 klasy) | 1 grupa duplikatów między klasami, 1 uszkodzony plik |
| Profil PDF | 3 faktury tekstowe i 1 skan | Skan oznaczony jako brak warstwy tekstowej |
| Podział stratyfikowany | wine | 142 / 36 po usunięciu duplikatów |
| Podział grupowy, 30 grup | wine, `producent` | 140 / 38, żadna grupa po obu stronach |
| Podział grupowy, 3 grupy | wine, `region` | 119 / 59 z ostrzeżeniem o małej liczbie grup |
| Podział czasowy na kolumnie bez dat | wine, `region` | Błąd z komunikatem, kod 2 |
| Baseline klasyfikacji tabelarycznej | wine | Naiwny F1 macro 0,187; regresja logistyczna 0,941; gradient boosting 1,000 |
| Baseline regresji | diabetes | Naiwny MAE 62,7; regresja grzbietowa 42,8; gradient boosting 45,0 |
| Baseline tekstu, polski syntetyczny | 240 pism, 4 klasy | Naiwny 0,100; TF-IDF z regresją logistyczną 1,000 (zbiór jest celowo łatwy, sprawdza tylko potok) |
| Baseline tekstu, zbiór publiczny | SMS Spam Collection, 5572 wiersze | Naiwny F1 macro 0,464; TF-IDF z regresją logistyczną 0,984, ROC-AUC 0,997; około 1 s |
| Baseline obrazów | digits, 4 klasy | Naiwny 0,098; regresja logistyczna 1,000; las losowy 0,979 |
| Baseline anomalii | breast_cancer, 25 przypadków złośliwych na 382 | Odporny z-score: ROC-AUC 0,946, PR-AUC 0,497; Isolation Forest: ROC-AUC 0,952, PR-AUC 0,619 |
| Metryki z plików | predykcje z baseline'ów | Klasyfikacja, regresja i ROC-AUC policzone; ROC-AUC zgodny z baseline'em (0,9518) |
| Walidator, poprawny plik | `submission.csv` z baseline'u i wzorzec | OK, kod 0 |
| Walidator, zły plik | brak 2 wierszy, etykieta spoza zbioru | 3 błędy, kod 1 |
| Ekstrakcja z PDF | 3 faktury i skan | Daty, kwoty, e-maile, kody pocztowe, NIP: F1 1,0 na dokumentach tekstowych; NIP czułość 0,75, bo skan nie ma tekstu; 11-cyfrowy numer zamówienia nie został uznany za PESEL |

Fragment wyjścia baseline'u:

```
Cechy: 13 liczbowych, 2 kategorycznych. Pominieto: stala (stala).
  naiwny (najczestsza)   F1 macro 0.1867  accuracy 0.3889  (0.03 s)
  regresja logistyczna   F1 macro 0.9407  accuracy 0.9444  (0.04 s)
  gradient boosting      F1 macro 1.0000  accuracy 1.0000  (0.14 s)
Najlepszy: gradient boosting (f1_macro 1.0000; naiwny 0.1867).
```

## Błędy znalezione i poprawione w trakcie testu

- Podział grupowy wywracał się, gdy grup było mniej niż części podziału. Liczba części jest teraz ograniczona liczbą grup, a przy mniej niż 10 grupach skrypt ostrzega.
- Porównanie plików zgłaszało osobne ostrzeżenie dla każdej kolumny o innym rozkładzie. Teraz jest jedno ostrzeżenie z pięcioma największymi przesunięciami.

## Czego nie testowano

- Dużych zbiorów (powyżej kilkuset MB) i czasu działania na nich. `profile_dataset.py` wczytuje cały plik do pamięci.
- Starego formatu `.xls` (nieobsługiwany; zapisz jako `.xlsx` albo CSV).
- OCR skanów i modeli wizyjnych: skrypty tylko wykrywają, że są potrzebne.
- Prawdziwych danych Partnerów.
