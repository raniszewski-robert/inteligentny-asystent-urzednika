# Baseline'y: co robią i co dalej

Każdy baseline działa na CPU laptopa i kończy się w sekundach albo minutach. Jego rola to dać punkt odniesienia i wykryć wyciek, zanim zespół zainwestuje w coś cięższego.

| Zadanie | `--task` | Co robi baseline | Metryka domyślna | Następny krok, gdy baseline nie wystarcza |
|---|---|---|---|---|
| Klasyfikacja tabelaryczna | `tabular-clf` | Imputacja, kodowanie kategorii; regresja logistyczna i gradient boosting (HistGradientBoosting) z wagami klas; porównanie z „najczęstszą klasą" | F1 macro | Cechy domenowe (ilorazy, różnice dat, agregaty po grupach), próg decyzji pod metrykę, kalibracja |
| Regresja | `regression` | Regresja grzbietowa i gradient boosting; porównanie z medianą | MAE | Transformacja logarytmiczna skośnego celu, cechy z dat, sprawdzenie obserwacji odstających |
| Klasyfikacja tekstu | `text-clf` | TF-IDF słów (1–2) i n-gramów znakowych (2–5), regresja logistyczna i LinearSVC | F1 macro | Osadzenia z modelu językowego albo klasyfikacja przez LLM z kilkoma przykładami (`hn-llm-w-produkcie`); zawsze porównaj na tej samej walidacji |
| Klasyfikacja obrazów | `image-clf` | Piksele 32×32 i histogram barw; regresja logistyczna i las losowy | F1 macro | Cechy z wytrenowanego modelu wizyjnego plus regresja logistyczna; augmentacja. Sprawdź czas na CPU przed decyzją |
| Wykrywanie anomalii | `anomaly` | Isolation Forest; porównanie z największym odchyleniem (odporny z-score) | ROC-AUC, PR-AUC (gdy są etykiety) | Reguły domenowe od Partnera, cechy względem grupy (odchylenie od mediany podmiotu), przegląd ręczny pierwszych 50 wyników |
| Ekstrakcja informacji | `extract_fields.py` | Wzorce dla dat, kwot, NIP, PESEL, REGON, KRS, e-maili, telefonów, kodów pocztowych, rachunków; identyfikatory z sumą kontrolną | F1 na pole (dokładne dopasowanie po normalizacji) | LLM z wyjściem według schematu dla pól, których wzorce nie łapią (nazwy, strony umowy, przedmiot); wzorce zostają jako walidator wyniku LLM |

## Jak czytać wynik

- **Baseline tuż nad modelem naiwnym.** Albo cechy nie niosą informacji, albo etykiety są zaszumione. Sprawdź w profilu wiersz „identyczne cechy z różną etykietą" i zapytaj Partnera, jak powstały etykiety.
- **Baseline bliski 1,0.** Najpierw szukaj wycieku: duplikaty, kolumna wyliczona z celu, identyfikator kodujący klasę, ta sama jednostka po obu stronach. Dopiero potem się ciesz.
- **Duża różnica między walidacją a wynikiem u Partnera.** Podział nie odpowiada testowi. Wróć do `make_split.py` z `--time` albo `--group`.

## Złoty zbiór do ekstrakcji

`extract_fields.py eval` potrzebuje pliku JSONL z poprawnymi polami. Jeśli Partner go nie daje, niech jedna osoba ręcznie oznaczy 20–30 dokumentów w pierwszych dwóch godzinach. To jedyny sposób, żeby w README pojawiła się liczba, a nie przymiotnik.

```json
{"doc": "faktura_0.pdf", "fields": {"nip": ["1234563218"], "data": ["12.03.2026"], "kwota": ["1 250,00 zł"]}}
```

## Metryki w `metrics.py`

Klasyfikacja: accuracy, balanced accuracy, precision, recall i F1 w wariantach macro, micro i weighted, wyniki na klasę, macierz pomyłek, a dla dwóch klas z kolumną wyniku także ROC-AUC i PR-AUC. Regresja: MAE, RMSE, R², mediana błędu bezwzględnego, MAPE. Anomalie: ROC-AUC i PR-AUC z kolumny wyniku.

Klasa pozytywna dla ROC-AUC to domyślnie ostatnia etykieta alfabetycznie (dla 0/1 jest to „1"). Inną wskaż przez `--positive`.
