# 03. Jakie dane są naprawdę dostępne

Stan: 21.11.2026. Status testu: ✅ próbka pobrana i sprawdzona skryptem, ⚠️ częściowo, ❌ niesprawdzone.

## Źródła

| Źródło | Dostęp | Format | Licencja / warunki | Aktualność | Pułapki jakości | Test |
|---|---|---|---|---|---|---|
| **Materiały UMB od mentorów** (folder „Hacknation 2026 - UMB”, kod QR) | Od mentorów 21.11; oryginały u zespołu, w repo tylko tekst i małe pliki (`data-partner/umb/`) | 10 wniosków (6 DOCX, 3 PDF, w tym 1 rękopis), 10 pism BKS (PDF, zanonimizowane), arkusz XLSX, Zarządzenie (PDF), 4 TXT (lista danych do anonimizacji, linki) | **Brak licencji; materiały konkursowe UMB.** Nie upubliczniać repo z `data-partner/` bez zgody mentora | 2025–2026 | Rękopis (16.2026) nieczytelny dla OCR; PDF-y z rozstrzelonymi literami (pdfplumber naprawia, pypdf nie); błędy dat w arkuszu; dane fikcyjne („Jerzy Dociekliwy”) | ✅ `ingest.py`, `build_archive.py`, `acceptance.py` |
| Lista komórek UMB (BIP) | https://bip.um.bydgoszcz.pl/artykuly/198/wydzialy, /artykuly/1158/biura | HTML | informacja publiczna | odczyt 21.11.2026 | Zakresy jednostek wywnioskowane z nazw [?]; słowa kluczowe układane ręcznie | ✅ → `departments.json` (29 komórek UMB + 17 jednostek miejskich) |
| Teksty ustaw (UDIP, KPA) | ISAP/ELI (`api.sejm.gov.pl/eli`) | HTML/PDF | domena publiczna (akty prawne) | UDIP tj. Dz.U. 2022 poz. 902 + 2025 poz. 1844; KPA tj. Dz.U. 2025 poz. 1691 | Z maszyny roboczej sesji ELI zablokowane (proxy), czytane przez przeglądarkę | ⚠️ treść streszczona w `notatki/prawo_szczegoly.md`; pobrania brak |
| Dni wolne | ustawa z 18.01.1951, tj. Dz.U. 2025 poz. 296; Wigilia: Dz.U. 2024 poz. 1965 | — | domena publiczna | od 1.02.2025 | Święto w sobotę daje urzędowi inny dzień wolny (nie „ustawowo wolny”) – konfigurować | ✅ kod `deadlines.py`, 18 testów |
| CBOSA (orzeczenia) | https://orzeczenia.nsa.gov.pl | RTF/HTML | informacja publiczna | 13 sygnatur sprawdzonych | Streszczenia narzędzia, nie pełne teksty | ⚠️ |
| Dane syntetyczne (nasze) | `gen_synthetic.py` | JSONL/TXT | MIT (nasze) | generowane | Testy to parafrazy naszych szablonów → wyniki optymistyczne | ✅ |

## Co mamy w repozytorium

| Plik | Zawartość | Pochodzenie |
|---|---|---|
| `data-partner/umb/archiwum_umb.jsonl` | 10 spraw UMB: wniosek + pisma BKS + wydziały + typ rozstrzygnięcia | tekst z próbek UMB (ingest + OCR), wydziały z treści pism, 2 uzupełnienia ręczne opisane w `note` |
| `data-partner/umb/kalendarium_umb.xlsx` | arkusz UMB bez zmian | UMB |
| `data-partner/umb/rejestr_umb.json`, `niespojnosci_arkusza.md` | import arkusza i raport | `import_xlsx.py` |
| `data-partner/umb/przypadek_543/` | wniosek 543.2026 + dwie odpowiedzi wydziałów **odtworzone z treści pisma BKS** (Schronisko, WGK) | test generatora |
| `data-partner/umb/probki/` | 3 oryginalne pliki wniosków (2 DOCX, 1 PDF, 0,3 MB) | UMB |
| `data-samples/syntetyczne/` | 90 spraw archiwum, 16 wniosków testowych ze złotymi wydziałami, 40 dokumentów ze złotymi spanami danych osobowych, 10 wniosków do kalendarza | `gen_synthetic.py --seed 2026` |
| `.claude/skills/udip-archiwum-i-wydzialy/data/departments.json` | 19 wydziałów, 10 biur UMB i 17 jednostek miejskich ze słowami kluczowymi | BIP UMB + praca własna |
| `.claude/skills/udip-anonimizacja/data/*` | imiona, stop-lista, adresy i domeny jawne, kategorie szczególne z listy UMB, funkcjonariusze | praca własna + lista UMB |

Oryginały UMB w pełnym rozmiarze (ok. 40 MB, skany 11–14 MB) zostają na dysku zespołu: `Hacknation 2026 - UMB/`. Odtworzenie: `python3 data-partner/umb/build_archive.py <katalog z JSON z ingest.py> <arkusz.xlsx>`.

## Plan B na danych syntetycznych

Gdy jury wgra własne pliki, a archiwum jest małe (10 spraw UMB), dołączamy archiwum syntetyczne (90 spraw, 16 tematów typowych dla JST, w tym schronisko, oświata, drogi, odpady). W demo oddzielamy je wyraźnie: „archiwum UMB” i „archiwum przykładowe”.

## Pytania do mentorów UMB (na miejscu)

1. Czy możemy wrzucić próbki UMB do publicznego repozytorium zgłoszenia, czy tylko teksty, czy nic? (Wpływa na README dla jury.)
2. Ile wniosków UDIP rocznie trafia do BKS? (Numeracja sugeruje ok. 800 [?].)
3. Czy art. 57 § 4 KPA (sobota → poniedziałek) stosujecie do 14 dni? Pokazujemy obie daty: ustawową i „bezpieczną”.
4. Czy zaczernienie danych osób trzecich w udostępnianym dokumencie robicie z decyzją o częściowej odmowie? (WSA Opole I SAB/Op 11/26 tego wymaga.)
5. Kto ma być widoczny w kolumnie „Osoba odpowiedzialna”: inicjały czy „Pracownik N”?
6. Czy dzień wolny za święto w sobotę (np. 26.12.2026) urząd ustala zarządzeniem? Kalendarz ma to w konfiguracji.
7. Lista osób pełniących funkcje publiczne do białej listy anonimizacji (prezydent, zastępcy, dyrektorzy).
