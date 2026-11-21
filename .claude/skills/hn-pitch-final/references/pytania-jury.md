# Pytania jury z administracji i jak odpowiadać

Wzorzec odpowiedzi (najwyżej 30 sekund): **odpowiedź wprost → dowód lub liczba → następny krok**. Jeśli nie wiesz: „Nie sprawdziliśmy tego; zrobilibyśmy to tak: ...". Nie zgaduj liczb.

Przepisy wymienione niżej to punkty wyjścia do rozmowy, nie porada prawna. Oznaczenia: [✔] fakt pewny, [~] do potwierdzenia u Partnera, [?] hipoteza.

## Wdrożenie

| Pytanie | Co powinno być w odpowiedzi |
|---|---|
| Co trzeba zrobić, żeby to działało u nas za trzy miesiące? | Konkretny pilotaż: jeden wydział, liczba użytkowników, miara sukcesu, czas. Czego brakuje (dostęp do danych, integracja, testy z użytkownikami) |
| Kto to utrzyma po hackathonie? | Kod w repozytorium z licencją pozwalającą przejęcie; dokumentacja uruchomienia; technologie, które zespół IT Partnera zna; brak zależności od konta zespołu |
| Czy to działa na naszych prawdziwych danych? | Na czym testowaliście (dane Partnera, próbka, dane syntetyczne o tym samym schemacie) i jaki wynik |
| Co, jeśli model się pomyli? | Człowiek zatwierdza decyzje; niepewne przypadki trafiają do niego; każda odpowiedź ma źródło do sprawdzenia; poprawki urzędnika służą do oceny jakości |

## RODO i bezpieczeństwo danych

| Pytanie | Co powinno być w odpowiedzi |
|---|---|
| Gdzie trafiają dane obywateli? | Konkretnie: model lokalny na serwerze urzędu albo zewnętrzne API (które, w jakim regionie, na jakiej umowie [~]). Co wychodzi poza urząd, a co nie |
| Czy przetwarzacie dane osobowe? | Jakie kategorie; czy dane są pseudonimizowane przed przetwarzaniem; czy logi zawierają dane osobowe; czas przechowywania |
| Co z ocena skutków (DPIA)? | Przy nowej technologii i danych na dużą skalę ocena skutków dla ochrony danych może być wymagana (art. 35 RODO) [✔ istnienie przepisu; [~] czy dotyczy tego przypadku]. Deklaracja: przygotujemy materiał do oceny z inspektorem ochrony danych Partnera |
| Czy da się was zhakować promptem? | Treść obywatela traktowana jako dane; wynik tylko według schematu; brak akcji bez człowieka; test zestawem pism z wstrzykniętymi poleceniami (wynik, np. 8/8 odpornych) |

## AI Act

| Pytanie | Co powinno być w odpowiedzi |
|---|---|
| Czy to system wysokiego ryzyka według AI Act? | Rozporządzenie UE 2024/1689 (AI Act) [✔] klasyfikuje m.in. niektóre systemy używane przez władze publiczne do oceny uprawnień do świadczeń jako wysokiego ryzyka [~]. Odpowiedź: system wspiera urzędnika, nie podejmuje decyzji; jeśli wpada w kategorię wysokiego ryzyka, wdrożenie wymaga dokumentacji, nadzoru człowieka i rejestrowania zdarzeń, które już częściowo mamy (logi, uzasadnienia) |
| Czy obywatel dowie się, że rozmawia z AI? | Tak, interfejs to mówi (obowiązek przejrzystości dla systemów wchodzących w interakcję z ludźmi [~]) |

## Koszty i skala

| Pytanie | Co powinno być w odpowiedzi |
|---|---|
| Ile to kosztuje? | Koszt na dokument i rocznie przy skali Partnera (`hn-llm-w-produkcie/scripts/cost_estimate.py`), plus serwer i utrzymanie. Porównanie z czasem pracy urzędnika |
| Czy wytrzyma całą Polskę / wszystkie urzędy? | Zmierzone opóźnienie i przepustowość na jednym laptopie; jak się skaluje (więcej instancji, przetwarzanie wsadowe); co jest wąskim gardłem |
| Dlaczego nie kupić gotowego produktu? | Co jest specyficzne dla Partnera (jego kategorie, dane, przepisy); otwarty kod bez uzależnienia od dostawcy; model polski (PLLuM) rozwijany dla administracji |

## Integracja z systemami państwowymi

Jakich systemów używa Partner, ustal z mentorem; nie zakładaj. Przykłady systemów, o które jury może zapytać: EZD RP (elektroniczne zarządzanie dokumentacją), e-Doręczenia, login.gov.pl (Węzeł Krajowy), mObywatel, ePUAP [~ sprawdź, które dotyczą Partnera].

| Pytanie | Co powinno być w odpowiedzi |
|---|---|
| Jak to się połączy z naszym systemem? | Interfejs wejścia i wyjścia (plik, API, dodatek do narzędzia, którego urzędnik już używa); co zrobiliśmy w prototypie, co trzeba dopisać |
| Czy urzędnik musi uczyć się nowego narzędzia? | Najlepiej nie: rozwiązanie wpięte w istniejący proces (w 2025 r. wygrał dodatek do Worda [~ research/02]) |

## Dostępność i użytkownicy

| Pytanie | Co powinno być w odpowiedzi |
|---|---|
| Czy jest dostępne dla osób z niepełnosprawnościami? | Podmioty publiczne mają obowiązki z ustawy o dostępności cyfrowej, opartej na WCAG 2.1 [~]. Co sprawdziliście (kontrast, klawiatura, czytnik ekranu, prosty język) |
| Czy rozmawialiście z użytkownikami? | Z mentorem Partnera, z czego wynikła zmiana w rozwiązaniu (konkret) |

## Technika i jakość

| Pytanie | Co powinno być w odpowiedzi |
|---|---|
| Skąd wiecie, że to działa dobrze? | Metryka, zbiór, sposób podziału, punkt odniesienia; najsłabsze miejsce i co z nim zrobić |
| Co było przygotowane przed hackathonem? | Zgodnie z ujawnieniem w README: narzędzia i notatki, nie gotowe rozwiązanie; co powstało w ciągu 24 godzin |
| Czego nie zdążyliście zrobić? | Szczerze, dwie rzeczy, i ile czasu by zajęły |
