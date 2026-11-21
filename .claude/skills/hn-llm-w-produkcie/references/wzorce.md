# Wzorce LLM dla rozwiązań w administracji

## 1. Człowiek decyduje, model przygotowuje

Model klasyfikuje, wyciąga pola, streszcza i proponuje odpowiedź; urzędnik zatwierdza. W interfejsie pokaż propozycję, uzasadnienie, cytat ze źródła i przycisk „popraw". To odpowiada na pytania jury o odpowiedzialność i błędy modelu, a poprawki urzędnika są gotowym zbiorem do oceny jakości. Pole `pewnosc` w schemacie kieruje niepewne przypadki prosto do człowieka.

## 2. Wynik według schematu, sprawdzany w kodzie

- Kategorie zawsze jako `enum` z listy Partnera; model nie wymyśli nowej.
- Identyfikatory (NIP, PESEL, numer sprawy) sprawdzaj sumą kontrolną albo wzorcem (`hn-dane-od-partnera/scripts/_common.py`). Model, który „poprawi" cyfrę, zostanie złapany.
- Daty i kwoty normalizuj w kodzie, nie w modelu.
- Błąd walidacji po ponowieniu: pokaż „nie udało się przetworzyć, przekazano do ręcznej obsługi", nie zgaduj.

## 3. Treść niezaufana (prompt injection)

Pisma, e-maile, załączniki i strony internetowe mogą zawierać polecenia dla modelu. Warstwy obrony, od najtańszej:

1. Treść w znacznikach (`wrap_untrusted`) i zasada w prompcie systemowym (`UNTRUSTED_SYSTEM_RULE`).
2. Wynik tylko według schematu z `enum`: nawet przejęty model nie wpisze dowolnego tekstu w pole decyzji.
3. Model nie ma narzędzi wykonujących akcje (wysyłka, zapis, płatność) bez zatwierdzenia przez człowieka.
4. Test kanarków (`injection_suite.py`) w każdym przebiegu przed demo.
5. Opcjonalnie pole `podejrzana_tresc: bool` w schemacie: model sam zgłasza próbę manipulacji, a interfejs to pokazuje. Dobry moment na demo.

Żadna z warstw nie daje pewności. Na pitchu mów „ograniczamy skutki", nie „jesteśmy odporni".

## 4. Cytowanie źródeł

Odpowiedź o przepisach, procedurach albo danych Partnera bez źródła jest bezużyteczna dla urzędnika. Dwa sposoby:

- API Claude z cytowaniami (`references/claude-api.md`): fragmenty źródła wskazuje API.
- Pole `cytat` w schemacie i kontrola w kodzie: `cytat in tekst_zrodla` po normalizacji spacji. Brak dosłownego wystąpienia → oznacz odpowiedź jako niepotwierdzoną.

W interfejsie podświetl cytat w dokumencie. Juror zobaczy to w kilka sekund.

## 5. Koszt i opóźnienie

- Stały prefiks (instrukcje, przykłady, dokument referencyjny) na początku zapytania i cache promptu po stronie API.
- Najtańszy model, który przechodzi zestaw testowy; większy tylko dla przypadków o niskiej pewności (kaskada).
- Przetwarzanie wsadowe nocą tam, gdzie urząd nie potrzebuje wyniku od razu.
- Mierz z dziennika (`llm_client.py stats`), przeliczaj na skalę Partnera (`cost_estimate.py`). Na pitchu podaj koszt na dokument w złotych i porównaj z czasem pracy urzędnika.

## 6. Demo, które nie zależy od sieci

- Sobota wieczór: przejdź scenariusz z `LLM_MODE=cache`, sprawdź, że `.llm_cache/` ma wszystkie odpowiedzi.
- Scena: `LLM_MODE=replay`. Wynik pojawia się natychmiast, nie ma klucza na ekranie.
- Jedno pytanie „na żywo" od jury zaplanuj jako tryb `cache` z modelem lokalnym, jeśli laptop go udźwignie; w przeciwnym razie powiedz wprost, że demo działa na nagranych odpowiedziach i pokaż dziennik prawdziwych wywołań.
- Dane w cache nie mogą zawierać danych osobowych, jeśli katalog trafia do publicznego repozytorium.
