# Scenariusz wideo demo (do 2:00)

Juror ogląda wideo po to, żeby w dwie minuty zobaczyć, że rozwiązanie działa na prawdziwym przypadku. Organizator zaleca do 2 minut. Plan na 1:50, żeby został zapas.

## Scenariusz

| Czas | Obraz | Co mówisz (przykład do podmiany) |
|---|---|---|
| 0:00–0:12 | Ekran startowy aplikacji z nazwą | „{{Kto}} dziś {{robi co}} ręcznie, co zajmuje {{ile}}. {{Nazwa}} robi to w {{ile}}." |
| 0:12–0:20 | Dane wejściowe: prawdziwe pismo, plik, zbiór | „Weźmy {{konkretny przypadek z danych Partnera}}." |
| 0:20–1:05 | Główny przepływ, jeden przypadek od wejścia do wyniku | Opisujesz, co widać, i dlaczego to ważne dla użytkownika. Bez opowiadania o kodzie |
| 1:05–1:25 | Wyróżnik: cytat ze źródła, uzasadnienie, odporność na próbę manipulacji, tryb offline, zgodność z WCAG | „Każda decyzja ma źródło: kliknięcie podświetla fragment przepisu." |
| 1:25–1:40 | Liczba z ewaluacji na planszy | „Na {{N}} przypadkach od Partnera: {{metryka}} {{wynik}} wobec {{punkt odniesienia}}." |
| 1:40–1:50 | Plansza: wdrożenie i link do repozytorium | „Działa {{gdzie}}, kosztuje {{ile}} na dokument. Kod i instrukcja w repozytorium." |

Odpowiedz na kryteria o najwyższej wadze w kolejności wag. Tabela kryteriów w README może podawać czasy scen („wideo 0:20–1:05").

## Technika

- **Nagrywanie ekranu:** OBS Studio (GPL-2.0; narzędzie, nie wchodzi do rozwiązania) albo wbudowane nagrywanie systemu (macOS: Cmd+Shift+5; Windows: Win+Alt+R w Xbox Game Bar).
- **Rozdzielczość:** 1920×1080 albo 1280×720. Powiększ czcionkę w przeglądarce do 125–150%, zamknij zbędne karty i powiadomienia.
- **Dźwięk:** słuchawki z mikrofonem w cichym kącie (strefa odpoczynku). Bez dźwięku dodaj napisy.
- **Dane:** tylko takie, które można pokazać publicznie. Żadnych danych osobowych, kluczy API ani zakładek z kontem.
- **Tryb demo:** `LLM_MODE=replay`, żeby wideo nie zależało od sieci i nie było przerw na czekanie. Długie oczekiwanie wytnij i powiedz, ile trwało naprawdę.
- **Dwa podejścia.** Pierwsze zwykle jest za długie. Nie montuj dłużej niż 20 minut; lepiej nagrać od nowa.
- **Konwersja i sprawdzenie:** `bash .claude/skills/hn-zgloszenie/scripts/video_check.sh nagranie.mov --fix demo.mp4`. Skrypt tnie koniec powyżej 1:58 i mówi, ile utnie; jeśli to zakończenie, skróć środek i nagraj ponownie.
- **Publikacja:** YouTube jako film niepubliczny albo dysk z dostępem „każdy z linkiem". Link sprawdź w oknie incognito na telefonie.
