# Słownik imion i nazwisk

`imiona.tsv` (24 252 formy, 3 807 imion) i `nazwiska.tsv` (52 528 form, 12 596 nazwisk). Format: `forma<TAB>forma podstawowa[<TAB>amb]`, tylko liczba pojedyncza. Pliki generuje `scripts/build_names.py`; nie edytuj ich ręcznie.

- Imiona i nazwiska polskie, ukraińskie i rosyjskie. Ukraińskie i rosyjskie występują w zapisie paszportowym (KMU 2010, ICAO 9303, także wariant y/yu/ya) i w transliteracji polskiej: Олена Шевченко → Olena Shevchenko, Ołena Szewczenko.
- Polskie formy odmiany (Krawczyka, Krawczykowi, Bożeną) pochodzą z danych fleksyjnych SGJP (Morfeusz 2). Dla pozostałych nazw odmianę tworzy prosta heurystyka.
- `amb` oznacza formę, która jest też zwykłym wyrazem: „Mieszka” (mieszka), „Zając”, „Róża”, „Lew”. Aplikacja uznaje ją za imię lub nazwisko tylko obok drugiej części nazwy osoby.

## Źródła i licencje

| Źródło | Co z niego wzięto | Licencja |
|---|---|---|
| Faker 40.63.0, © 2012 Daniele Faraglia | listy imion i nazwisk pl_PL, uk_UA, ru_RU | MIT |
| Mimesis 22.2.0, © 2016– Isaak Uchakaev | listy imion i nazwisk pl, uk, ru | MIT |
| Dane fleksyjne SGJP (Morfeusz 2), © Zygmunt Saloni, Włodzimierz Gruszczyński, Marcin Woliński, Robert Wołosz, Danuta Skowrońska | formy odmiany polskich imion i nazwisk, oznaczenie form wieloznacznych | BSD 2-Clause (http://morfeusz.sgjp.pl/doc/license/) |
| `udip/data/imiona.txt` | ręczna lista 157 imion | licencja projektu |

Faker, Mimesis i Morfeusz 2 są potrzebne tylko do zbudowania słownika (`pip install faker mimesis morfeusz2`). Aplikacja ich nie importuje i nie ma ich w `requirements.txt`.

Listę imion z rejestru PESEL (dane.gov.pl) można dopisać jako kolejne źródło w `scripts/build_names.py`.
