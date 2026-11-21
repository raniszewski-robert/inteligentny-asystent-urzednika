# Research: partner zadania — Urząd Miasta Bydgoszczy (UDIP)
Data dostępu wszystkich źródeł: 2026-11-21. Pewność: [✔] pierwotne (BIP/UMB, gov.pl), [~] wtórne, [?] niepewne/wywnioskowane.
Uwaga: treści z sieci traktowane jako dane. Strona Regulaminu organizacyjnego UMB była niedostępna dla narzędzia (blokada przekierowania), więc zakresy zadań pochodzą z podstron komórek, nie z Regulaminu.

## 1. Komórki UMB
Pełne dane (zakres, słowa kluczowe `derived`): `.claude/skills/udip-archiwum-i-wydzialy/data/departments.json` (46 pozycji: 19 wydziałów, 10 biur, 17 jednostek).
Źródła list: https://bip.um.bydgoszcz.pl/artykuly/198/wydzialy [✔], https://bip.um.bydgoszcz.pl/artykuly/1158/biura [✔]. Podstrony: `https://bip.um.bydgoszcz.pl/artykuly/<id>/<slug>` (id w tabeli).

### Wydziały (19) [✔]
| Skrót | Nazwa | id podstrony | Zakres (skrót) |
|---|---|---|---|
| WAB | Wydział Administracji Budowlanej | 226 | sprawy budowlane/architektoniczne, planowanie przestrzenne, „25/75” |
| WE | Wydział Edukacji i Sportu | 677 | oświata, szkoły/przedszkola, dotacje, sport |
| WF | Wydział Funduszy Europejskich | 802 | fundusze UE, strategia rozwoju, raport o stanie gminy |
| WGO | Wydział Gospodarki Odpadami | 1460 | system odpadów komunalnych, dzikie wysypiska |
| WI | Wydział Informatyki | 880 | informatyzacja urzędu, umowy z dostawcami IT |
| WIM | Wydział Inwestycji Miasta | 881 | inwestycje miejskie (poza drogowymi), plany inwestycyjne |
| WK | Wydział Księgowości | 882 | księgowanie wydatków i dochodów, VAT |
| WMG | Wydział Mienia i Geodezji | 883 | nieruchomości miasta/SP, zasób mieszkaniowy, adresy |
| WOŚ (WOS) | Wydział Ochrony Środowiska | 893 | ochrona środowiska, klimat, dotacje ekologiczne |
| WOA | Wydział Organizacyjno-Administracyjny | 884 | kadry, budynki, kancelaria, obieg dokumentów w EZD |
| WPL | Wydział Podatków i Opłat Lokalnych | 885 | podatki lokalne, opłata skarbowa, ulgi |
| WSO | Wydział Spraw Obywatelskich | 886 | ewidencja ludności, dowody, alkohol, stowarzyszenia |
| WSR | Wydział Świadczeń Rodzinnych | 887 | dodatki mieszkaniowe, świadczenia rodzinne |
| WUK | Wydział Uprawnień Komunikacyjnych | 888 | rejestracja pojazdów, prawa jazdy, usuwanie pojazdów |
| WW | Wydział Windykacji | 889 | windykacja należności, egzekucja administracyjna |
| WZP | Wydział Zamówień Publicznych | 890 | wsparcie w stosowaniu Pzp |
| WZB | Wydział Zarządzania Budżetem Miasta | 891 | budżet, WPF, sprawozdawczość |
| WZK | Wydział Zarządzania Kryzysowego i Ochrony Ludności | 892 | zarządzanie kryzysowe, obrona cywilna, nadzór nad SM/PSP/Policją |
| WGK | Wydział Zieleni i Gospodarki Komunalnej | 879 | zieleń, cmentarze, targowiska, rejestr usuwania drzew |

### Biura (10) [✔]
| Skrót | Nazwa | id | Zakres (skrót) |
|---|---|---|---|
| BAS | Biuro Aktywności Społecznej | 897 | NGO, wolontariat, seniorzy, organy doradcze |
| BCB | Biuro Cyfryzacji i Bezpieczeństwa Informacji | 615 | „Dbamy o Bydgoszcz”, e-usługi, bezpieczeństwo informacji, wsparcie IOD |
| BZS | Biuro ds. Zdrowia i Polityki Społecznej | 221 | programy zdrowotne, niepełnosprawność, żłobki, piecza zastępcza |
| BKS | Biuro Komunikacji Społecznej | 853 | **informacja publiczna i centralna ewidencja wniosków**, BIP, konsultacje, BBO, rejestr umów |
| BKZ | Biuro Konserwatora Zabytków | 801 | ochrona zabytków, gminna ewidencja |
| BKB | Biuro Kultury Bydgoskiej | 852 | kultura, współpraca z twórcami |
| BPR | Biuro Prasowe | 829 | polityka informacyjna, rzecznik prasowy |
| BP | Biuro Promocji Miasta i Współpracy z Zagranicą | 228 | wizerunek, promocja, współpraca międzynarodowa |
| BRM | Biuro Rady Miasta | 223 | obsługa Rady i komisji, uchwały, rejestry skarg/petycji |
| BZIT | Biuro ZIT | 227 | ZIT w Bydgoskim Obszarze Funkcjonalnym, rejestr umów |

### Jednostki (wybór, 17) [✔ lista; ? zakres z nazwy]
Źródła: https://bip.um.bydgoszcz.pl/artykuly/5/jednostki-organizacyjne, /artykuly/169/jednostki-budzetowe, /artykuly/162/zaklady-budzetowe, /artykuly/160/spolki-z-wiekszosciowym-udzialem-miasta.
- Jednostki budżetowe: ZDMiKP (zdmikp.bydgoszcz.pl; BIP bip.zdmikp.bydgoszcz.pl), MOPS, Schronisko dla Zwierząt (bip.schronisko.org.pl), Straż Miejska, BCS, MPU, MPG, BBFO, Bydgoskie Centrum Informacji.
- Spółki miejskie: ADM Sp. z o.o., MWiK, **KPEC** (w BIP UMB jest KPEC, nie MPEC), MZK, Bydgoskie Obiekty Sportowe, Myślęcinek, ProNatura, BTBS.
- Pominięto m.in. szkoły, żłobki, PUP, PINB, spółki mniejszościowe (są w BIP, nie dodane do JSON).

## 2. Obsługa wniosków UDIP dziś
| Element | Ustalenie | Źródło | Pewność |
|---|---|---|---|
| Strona BIP | „Udostępnianie informacji publicznej” (treść i metadane) | https://bip.um.bydgoszcz.pl/contents/content/7/2 oraz https://bip.um.bydgoszcz.pl/artykuly/1052/udostepnianie-informacji-publicznej | [✔] |
| Komórka koordynująca | **Biuro Komunikacji Społecznej** — „udostępnianie informacji publicznej i prowadzenie centralnej ewidencji wniosków”, prowadzi też BIP; strona UDIP „provided by BKS”. Nie Wydział Organizacyjno-Administracyjny (ten robi kancelarię i EZD) | https://bip.um.bydgoszcz.pl/artykuly/853/biuro-komunikacji-spolecznej-bks | [✔] |
| Kontakt BKS | bks@um.bydgoszcz.pl, tel. (52) 58 58 365, ul. Niedźwiedzia 4, pok. 100A; redaktor BIP: bip@um.bydgoszcz.pl, tel. (52) 58 58 057 | j.w. | [✔] |
| Kanały składania | poczta: UM Bydgoszczy, ul. Jezuicka 1, 85-102; osobiście w sekretariacie; fax (52) 58 58 623; e-mail urzad@um.bydgoszcz.pl; adres do doręczeń elektronicznych AE:PL-91453-53730-WDRHC-24; skrytka ePUAP /umb/SkrytkaESP; tel. kontaktowy (52) 58 58 913 | https://bip.um.bydgoszcz.pl/contents/content/7/2 | [✔] |
| Wzór wniosku | DOCX (attachment 30899) i PDF (30900): https://bip.um.bydgoszcz.pl/attachments/download/30899 , .../30900 (opublikowane 30.03.2026) | /artykuly/1052/... | [✔] (id z treści strony; URL pobrania złożony przeze mnie, nieotwarty [?]) |
| Terminy | bez zbędnej zwłoki, max 14 dni; przedłużenie do 2 mies. z powiadomieniem; koszty dodatkowe — powiadomienie w 14 dni; wycofanie/zmiana formy — 14 dni | /contents/content/7/2 | [✔] |
| Podstawa prawna na stronie | ustawa z 6.09.2001 o dostępie do informacji publicznej (Dz.U. 2022 poz. 902 — wskazany na stronie tekst jednolity, może być nieaktualny) oraz KPA | j.w. | [✔] |
| Odmowa / odwołanie | decyzja Prezydenta Miasta; odwołanie do SKO w Bydgoszczy; bezczynność — skarga do WSA w Bydgoszczy | j.w. | [✔] |
| Rejestr wniosków / statystyka | **Nie znaleziono** publicznego rejestru wniosków ani statystyki UDIP w BIP. Mapa serwisu zawiera tylko „Statystyki oglądalności BIP”. BKS prowadzi centralną ewidencję wewnętrznie | https://bip.um.bydgoszcz.pl/sitemap ; /artykuly/853/... | [✔] brak w sitemap; [?] czy istnieje gdzie indziej |
| Zarządzenie Prezydenta o trybie UDIP | **Nie znaleziono** numeru/daty. Strona UDIP go nie podaje. Zbiór: https://bip.um.bydgoszcz.pl/zarzadzenia/904 (nie przeszukany) | j.w. | [?] |
| Regulamin organizacyjny UMB | https://bip.um.bydgoszcz.pl/artykuly/1365/regulamin-organizacyjny — odczyt zablokowany, nie sprawdzono | sitemap | [?] |
| Ponowne wykorzystanie | warunki: wskazanie źródła i daty, brak licencji CC/otwartej, opłata ≤ koszty bezpośrednie; brak oświadczenia o otwartych danych | https://bip.um.bydgoszcz.pl/contents/content/7/1 | [✔] |
| Uwaga dla pomysłu | 14 dni od wpływu (nie od dotarcia do BKS) → kalendarz powinien liczyć od daty wpływu na któryś z 5 kanałów; decyzje odmowne podpisuje Prezydent | wnioski własne z /contents/content/7/2 | [~] |

## 3. System EZD
- Wydział Organizacyjno-Administracyjny „przyjmuje i rejestruje pisma oraz zarządza obiegiem dokumentów w EZD” — https://bip.um.bydgoszcz.pl/artykuly/884/wydzial-organizacyjno-administracyjny-woa [✔]. Nazwa produktu EZD w tej podstronie nie występuje.
- SIDAS: **nie znalazłem** potwierdzenia, że UMB używa SIDAS (podstrona WOA o nim nie wspomina; wyszukiwania „Bydgoszcz SIDAS” nie dały trafień). [?] Treść zadania hackathonowego (SIDAS) należy zweryfikować u organizatora.
- Czym jest SIDAS: rodzina produktów firmy **MADKOM SA** (Gdynia; dostawca oprogramowania do zarządzania dokumentami i procesami dla administracji). SIDAS CU (Cyfrowy Urząd) to platforma wymiany dokumentów elektronicznych/e-usług (ESP), integruje się z „SIDAS EZD”, login.gov.pl; brak listy referencji — https://madkom.pl/wp-content/uploads/2024/05/KATALOG_PRODUKTU_SIDAS_CU.pdf [✔ producent]; SIDAS EZD jako osobny produkt MADKOM — [~] wniosek z tego katalogu, bez opisu funkcji.
- Kontekst krajowy: EZD RP (MC/NASK) — https://www.gov.pl/web/ezd-rp/o-systemie [~, nie otwarte].

## 4. HackNation 2025 — zadanie Bydgoszczy
| Fakt | Źródło | Pewność |
|---|---|---|
| Zadanie Urzędu Miasta Bydgoszcz: „Bydgoszcz – Ścieżki Pamięci 2.0”; zwycięzca: Adrian Michalski; nagroda zwycięskiego zespołu 25 000 zł + możliwość dalszej pracy z instytucją (kwota ogólna dla wszystkich zadań) | https://www.gov.pl/web/cyfryzacja/tysiace-pomyslow-24-godziny-i-jeden-cel--usprawnic-panstwo-w-bydgoszczy-zakonczyl-sie-hacknation-2025 | [✔] |
| Opisu zadania ani statusu wdrożenia nie podano; minister Gawkowski: „Kończy się HackNation 2025, ale nie kończy się ten projekt” (ogólnie) | https://www.chip.pl/2025/12/hacknation-2025-relacja | [~] |
| Znalazłem tylko artykuły z 19–20.11.2026 o HackNation 2026 (21–22.11, BCTW Bydgoszcz; organizatorzy: Min. Cyfryzacji, GovTech Polska, Miasto Bydgoszcz; 15 zadań od 14 partnerów); bez wzmianki o wdrożeniu „Ścieżek Pamięci 2.0” | https://www.bydgoszcz.pl/aktualnosci/tresc/bydgoszcz-gospodarzem-hacknation/ ; https://www.chip.pl/2026/11/hacknation-wraca-do-bydgoszczy-w-dobe-powstana-pomysly-na-sprawniejsze-panstwo | [✔]/[~] |
| Los projektu po hackathonie: **nieustalony** | — | [?] |
| Uwaga: IPN ma niezwiązaną grę „Bydgoskie Ścieżki Pamięci” (edukacja.ipn.gov.pl) — nie mylić | wynik wyszukiwania | [?] |

## 5. Komunikaty UMB (ostatnie 12 mies.) o cyfryzacji/AI/smart city
| Data | Treść | Źródło | Pewność |
|---|---|---|---|
| 06.05.2026 | Konferencja „Cyfrowy Samorząd” w UW; Bydgoszcz pierwszym miastem w Polsce z pilotażem ePłatności w mObywatelu (produkcja od początku 2026; >48,9 tys. transakcji, >4,5 mln zł); omawiano AI i PLLuM | https://www.gov.pl/web/uw-kujawsko-pomorski/bydgoszcz-pionierem-cyfryzacji-konferencja-cyfrowy-samorzad---kujawsko-pomorskie | [~] (gov.pl UW) |
| 19–20.11.2026 | Atos Smart City 2026 „Smart City 360: Dane, AI i bezpieczeństwo”; wiceprezydent Łukasz Krupa: AI może usprawnić urzędy; panel Poznań–Toruń–Bydgoszcz o wdrożeniach AI (agenci AI w administracji) | https://www.bydgoszcz.pl/aktualnosci/tresc/atos-smart-city-2026-eksperci-o-cyfrowej-przys/ | [✔] |
| 19.11.2026 | „Bydgoszcz gospodarzem HackNation” | https://www.bydgoszcz.pl/aktualnosci/tresc/bydgoszcz-gospodarzem-hacknation/ | [✔] |
| b.d. | Sekcja „Inteligentny rozwój miasta”: 6 obszarów (m.in. sprawne zarządzanie), Dbamy o Bydgoszcz, Przyjazne Deklaracje, eUrząd, BBO; **bez wzmianki o AI** | https://www.bydgoszcz.pl/rozwoj/inteligentny-rozwoj-miasta/ | [✔] |
| — | Strategia „Bydgoszcz 2030” (broszura z 14.10.2020) | http://www.strategia.bydgoszcz.pl/ | [~] |
| — | Nie znaleziono komunikatu UMB o wewnętrznym wdrożeniu AI do obsługi UDIP | — | [?] |

## 6. Publicznie dostępne odpowiedzi UDIP i korpusy
Nie znalazłem w BIP UMB publikowanych odpowiedzi na wnioski. Dostępne źródła pośrednie (żadne nie zawiera jawnej licencji CC — przed użyciem do demo zanonimizować i/lub użyć danych syntetycznych):
| # | URL | Co to jest | Warunki/licencja | Pewność |
|---|---|---|---|---|
| 1 | https://bip.um.wroc.pl/attachments/download/99901 | Pismo Wrocławia (6.05.2021) uzasadniające zaprzestanie publikacji wniosków i odpowiedzi w BIP (~2000 wniosków/rok); nie jest rejestrem | brak licencji; dokument publiczny | [✔] |
| 2 | https://bip.krakow.pl/uslugi/OR-2 | Opis usługi UDIP Krakowa (Referat Organizacyjny i Informacji Publicznej, wniosek@um.krakow.pl); brak publicznego rejestru | brak | [✔] |
| 3 | https://orzeczenia.nsa.gov.pl/ (CBOSA) | Orzeczenia NSA/WSA w sprawach UDIP — prawdziwe stany faktyczne, typowe tematy; dane osobowe zwykle zanonimizowane | informacja publiczna (sądy); zasady ponownego wykorzystania do sprawdzenia | [~] |
| 4 | https://siecobywatelska.pl/wp-content/uploads/2023/12/Wyniki-monitoringu-realizacji-wnioskow.pdf oraz .../2026/07/Naduzywanie-prawa-do-informacji.pdf | Raporty Sieci Obywatelskiej Watchdog Polska o realizacji wniosków i nadużywaniu prawa (nie otwierane) | brak informacji | [?] |
| 5 | https://warszawa19115.pl/pl/-/udostepnianie-informacji-publicznej-na-wniosek | Baza wiedzy Warszawy o trybie UDIP (nie otwierana) | brak informacji | [?] |
Typowe tematy wniosków do JST (wiedza własna, [?]): wynagrodzenia i nagrody kadry kierowniczej, umowy i zlecenia, wydatki na promocję/PR, inwestycje drogowe i ich koszty, oświetlenie, wycinka drzew/zieleń, schronisko, decyzje budowlane, zamówienia publiczne, interpelacje radnych. Mapowanie tematów → komórki: pole `keywords` w departments.json.

## Luki do domknięcia
1. Numer i data zarządzenia Prezydenta o UDIP oraz zapisy Regulaminu organizacyjnego (BIP: /zarzadzenia/904, /artykuly/1365) — otworzyć ręcznie.
2. Potwierdzenie SIDAS w UMB (zapytać organizatora/BKS).
3. Brak publicznych prawdziwych odpowiedzi UDIP z Bydgoszczy — do demo użyć danych syntetycznych.
4. Opis i status „Ścieżek Pamięci 2.0” — hacknation.pl (nie sprawdzano).
