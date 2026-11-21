# data-samples

| Katalog | Zawartość | Pochodzenie | Licencja |
|---|---|---|---|
| `syntetyczne/archiwum.jsonl` | 90 fikcyjnych spraw UDIP (16 tematów typowych dla JST, daty z 2 lat) | `udip-ewaluacja/scripts/gen_synthetic.py --today 2026-11-22 --n 90 --seed 2026` | MIT (nasze) |
| `syntetyczne/testy/` | 16 wniosków testowych (parafrazy innych słów niż archiwum, co 4. z drugim pytaniem z innego wydziału), 16 odpowiedzi wydziałów, `gold.json` (wydziały, trafne sprawy z ostatniego roku) | j.w. | MIT |
| `syntetyczne/pii/` | 8 „trudnych” dokumentów z danymi osobowymi + `gold.json` ze złotymi spanami dla 40 dokumentów (także testy/) | j.w. | MIT |
| `syntetyczne/kalendarz_demo.json` | 10 wniosków do kalendarza z rozkładem pilności względem 22.11.2026 | j.w. | MIT |

Wszystkie dane osobowe są fikcyjne: imiona i nazwiska z list częstych nazwisk w losowych kombinacjach, e-maile w domenie example.com (RFC 2606), PESEL-e losowe z poprawną sumą kontrolną. Rozmiar: < 1 MB.

Dane Partnera (prawdziwe próbki UMB) są osobno w `data-partner/umb/` (inne warunki, patrz tamtejszy README).
