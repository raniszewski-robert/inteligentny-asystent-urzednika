# Research technologiczny: narzędzie UDIP dla UM Bydgoszcz (HackNation 2026)
Data dostępu wszystkich źródeł: 2026-11-21. Pewność: [✔] źródło pierwotne, [~] wtórne, [?] niesprawdzone/szacunek.
Uwaga: treści z sieci traktowane jako dane. To nie jest porada prawna; licencje do potwierdzenia przez prawnika miasta.

## 1. Lokalne LLM (polskie i wielojęzyczne)

### 1.1 Bielik (SpeakLeash + ACK Cyfronet AGH)
| Model | Licencja | Szczegóły | URL | Pewn. |
|---|---|---|---|---|
| Bielik-11B-v3.1-Instruct | Apache-2.0 | Premiera 10.11.2026; 11B, 56 języków, 500B tokenów pretrain, SFT 26M, RL (GRPO); kontekst 32K (Ollama); function calling, `reasoning_effort`; vLLM >=0.24 | https://huggingface.co/speakleash/Bielik-11B-v3.1-Instruct ; https://www.instalki.pl/news/software/bielik-ai-nowa-wersja-polskiego-modelu-ai/ | [✔] HF, [~] data |
| Bielik-11B-v3.0-Instruct | Apache-2.0 | baza Bielik-11B-v3-Base-20250730; GGUF: Q4_K_M 6,72 GB, Q5_K_M 7,91, Q6_K 9,16, Q8_0 11,9, BF16 22,3 GB | https://huggingface.co/speakleash/Bielik-11B-v3.0-Instruct ; https://huggingface.co/speakleash/Bielik-11B-v3.0-Instruct-GGUF | [✔] |
| Bielik-4.5B-v3.0-Instruct | Apache-2.0 | ~4,6B; GGUF Q8_0 5,06 GB, FP16 9,5 GB; w Ollama kontekst 8K | https://huggingface.co/speakleash/Bielik-4.5B-v3.0-Instruct ; https://huggingface.co/speakleash/Bielik-4.5B-v3.0-Instruct-GGUF | [✔] |
| Bielik-1.5B-v3.0-Instruct | Apache-2.0 (niezweryfikowano na karcie) | istnieje (AWQ, NVFP4, MLX) | https://huggingface.co/speakleash | [?] licencja |
| Bielik-Minitron-7B-v3.0-Instruct | nieustalona | istnieje w katalogu Ollama/HF; licencja pochodna NVIDIA Minitron niesprawdzona | https://huggingface.co/speakleash | [?] |
| Bielik-11B-v3.0-DFlash | Apache-2.0 | tylko draft do speculative decoding (nie samodzielny); wymaga SGLang >0.5.6 lub vLLM >0.20.0 | https://huggingface.co/speakleash/Bielik-11B-v3.0-DFlash | [✔] |

- Ollama (oficjalne konto SpeakLeash): `ollama pull SpeakLeash/bielik-11b-v3.1-instruct:Q4_K_M` (6,7 GB; Q5_K_M 7,9; Q6_K 9,2; Q8_0 ~12; kontekst 32K). https://ollama.com/SpeakLeash/bielik-11b-v3.1-instruct [✔]
- `ollama pull SpeakLeash/bielik-4.5b-v3.0-instruct:Q8_0` (5,1 GB, kontekst 8K). https://ollama.com/SpeakLeash/bielik-4.5b-v3.0-instruct [✔]
- Alternatywnie z HF: `ollama run hf.co/speakleash/Bielik-11B-v3.0-Instruct-GGUF:Q4_K_M`. [✔]
- Karta modelu ostrzega: kwantyzacja obniża jakość i zwiększa halucynacje; brak mechanizmów moderacji. [✔]
- Wymagania (wyliczone z rozmiarów plików, nie z pomiarów): 11B Q4_K_M ~7 GB + KV cache -> GPU 12 GB VRAM wystarczy, komfortowo 16-24 GB; BF16 22 GB -> GPU 24-48 GB. 4,5B Q8_0 ~5 GB -> CPU z 8-16 GB RAM. [?]
- Szybkość na CPU: nie znalazłem wiarygodnego benchmarku Bielika. Szacunek (reguła kciuka dla modeli 4-5B Q8 na laptopie 8-16 rdzeni): kilka do ~10 tok/s; 11B Q4 na CPU: ~2-5 tok/s. Zmierzyć samemu przed prezentacją. [?]

### 1.2 PLLuM (konsorcjum, MC / NASK / PWr / IPI PAN i in.)
Generacja "2512" (grudzień 2025; artykuł arXiv 5.11.2025). Starsze: 2412, 2507, 2508 (v2.0 lip 2025, v2.1 sie 2025, v2.2 gru 2025 wg kolekcji).
| Model | Licencja (karta) | Baza | URL | Pewn. |
|---|---|---|---|---|
| PLLuM-12B-instruct/chat-2512 | Apache-2.0 | Mistral-Nemo-Base-2407 | https://huggingface.co/CYFRAGOVPL/PLLuM-12B-instruct-2512 | [✔] |
| PLLuM-4B-instruct/chat-2512 | Apache-2.0 (deklaracja) | gemma-3-4b-pt (warunki Gemma!) | https://huggingface.co/CYFRAGOVPL/PLLuM-4B-instruct-2512 | [✔] baza; [?] ważność Apache |
| Llama-PLLuM-8B-instruct/chat-2512 | Llama 3.1 (community) | Llama-3.1-8B | https://huggingface.co/CYFRAGOVPL/Llama-PLLuM-8B-instruct-2512 | [✔] |
| Llama-PLLuM-70B-*-2512 | Llama (community) | Llama 3.1 70B | https://huggingface.co/CYFRAGOVPL/Llama-PLLuM-70B-chat-2508 | [~] |
| PLLuM-12b-nc-*, PLLuM-8x7B-nc-* | pllum-1.2, tylko badania, bramkowane (instytucje naukowe) | - | https://huggingface.co/CYFRAGOVPL/PLLuM-12b-nc-base-2507 | [✔] NIEUŻYWAĆ |
- Karta 12B wskazuje na zastosowanie w administracji publicznej; w danych m.in. 15k instrukcji w stylu RAG; część instrukcji syntetyczna (Mixtral 8x22, DeepSeek V3). Karta nie porównuje z Bielikiem; deklaracje "SOTA" niezweryfikowane. https://huggingface.co/CYFRAGOVPL/PLLuM-12B-instruct-2512 [✔]/[?]
- Gemma Terms of Use to NIE Apache-2.0: ograniczenia użycia, obowiązek przekazania ich dalej, możliwość zakończenia umowy i obowiązek usunięcia modelu. https://ai.google.dev/gemma/terms [✔]. Wniosek: 4B PLLuM i Gemma traktować jako ryzyko.
- Dostępność w Ollama: oficjalnej biblioteki PLLuM nie potwierdziłem; GGUF społecznościowe / własna konwersja. [?]

### 1.3 Alternatywy
| Model | Licencja | Uwagi | URL | Pewn. |
|---|---|---|---|---|
| Qwen3-8B | Apache-2.0 | 8,2B, 100+ języków, 32K (128K YaRN); polski słabszy niż Bielik (brak pomiaru) | https://huggingface.co/Qwen/Qwen3-8B | [✔] |
| Mistral-Nemo-Instruct-2407 | Apache-2.0 | 12B, 128K | https://huggingface.co/mistralai/Mistral-Nemo-Instruct-2407 | [✔] |
| Gemma 3 | Gemma Terms (nie permisywna) | unikać | https://ai.google.dev/gemma/terms | [✔] |
| Llama 3.x | Llama community | unikać | - | [~] |

### 1.4 Rekomendacja
- Serwer urzędu (GPU 16-24 GB): **Bielik-11B-v3.1-Instruct** (Apache-2.0, 32K, Ollama Q5_K_M/Q8_0 lub vLLM BF16). Ryzyko: wydany 11 dni temu, mało testów; zapas: Bielik-11B-v3.0-Instruct (sprawdzony, GGUF) lub PLLuM-12B-instruct-2512 (Apache-2.0, argument "model dla administracji" w prezentacji).
- Laptop bez GPU: **Bielik-4.5B-v3.0-Instruct Q8_0** (~5 GB, Ollama, kontekst 8K - przy długich pismach wymusza chunking).
- "Uczenie się na wgrywanych danych": realistycznie RAG (indeks ustaw i archiwalnych odpowiedzi) + few-shot z podobnymi wnioskami; dostrajanie LoRA to opcja na etap docelowy, nie na 22 h. [?] (ocena własna)

## 2. Serwowanie lokalne
| Narzędzie | Licencja | Wersja/uwagi | URL | Pewn. |
|---|---|---|---|---|
| Ollama | MIT | OpenAI-compat: `http://localhost:11434/v1/` (`/chat/completions`, `/embeddings`); klient PyPI `ollama` 0.6.3 MIT | https://github.com/ollama/ollama ; https://docs.ollama.com/api/openai-compatibility | [✔] |
| llama.cpp | MIT | "Copyright 2023-2026 The ggml authors"; `llama-server` ma API OpenAI | https://github.com/ggml-org/llama.cpp | [✔] licencja; [~] API |
| llama-cpp-python | MIT | 0.3.37 (2026-11-15) | https://pypi.org/project/llama-cpp-python/ | [✔] |
| vLLM | Apache-2.0 | serwer OpenAI-compat; wymaga GPU; Bielik 3.1 wymaga >=0.24 | https://github.com/vllm-project/vllm | [✔] licencja; [~] API |
| openai (klient) | Apache-2.0 | 3.57.0 | https://pypi.org/project/openai/ | [✔] |
- Prototyp: Ollama (prosto), produkcja GPU: vLLM. Cały kod aplikacji pisać przeciw API OpenAI, by zmiana backendu była konfiguracją.

## 3. Embeddingi, wyszukiwanie, baza wektorowa
| Model | Licencja | Parametry | PIRB NDCG@10 | URL | Pewn. |
|---|---|---|---|---|---|
| sdadas/mmlw-retrieval-e5-base | Apache-2.0 | 0,3B | 56,09 | https://huggingface.co/sdadas/mmlw-retrieval-e5-base | [✔] |
| sdadas/mmlw-retrieval-e5-large | Apache-2.0 | 0,6B | 58,30 | https://huggingface.co/sdadas/mmlw-retrieval-e5-large | [✔] |
| sdadas/mmlw-e5-base | Apache-2.0 | 0,3B | 53,56 (MTEB-PL 59,71) | https://huggingface.co/sdadas/mmlw-e5-base | [✔] |
| sdadas/mmlw-retrieval-roberta-large-v2 | **Gemma** | 0,4B | 60,71 | https://huggingface.co/sdadas/mmlw-retrieval-roberta-large-v2 | [✔] NIE |
| sdadas/stella-pl-retrieval-mini-8k | **Gemma** | 0,4B | 61,29 | https://huggingface.co/sdadas/stella-pl-retrieval-mini-8k | [✔] NIE |
| BAAI/bge-m3 | MIT | ~0,6B (dim 1024), 8192 tokenów, 100+ języków | brak w paperze PIRB | https://huggingface.co/BAAI/bge-m3 | [✔] |
| intfloat/multilingual-e5-large | MIT | 0,6B | PIRB 57,29 (paper) | https://huggingface.co/intfloat/multilingual-e5-large ; https://arxiv.org/pdf/2402.13350 | [✔] |
| Qwen3-Embedding-0.6B | Apache-2.0 | 0,6B, 32K | brak danych | https://huggingface.co/Qwen/Qwen3-Embedding-0.6B | [✔] |
- Pułapka: najlepsze nowe modele sdadas (roberta-large-v2, stella-pl) mają licencję Gemma, nie Apache; starsze mmlw-retrieval-e5-* są Apache-2.0. BM25 w PIRB: 41,85 vs e5-base 53,12 -> hybryda ma sens. [✔]
- Rekomendacja: **sdadas/mmlw-retrieval-e5-large** (Apache, 58,30, polski-specyficzny); zapas: bge-m3 (MIT, długie dokumenty 8K). Na laptopie bez GPU: mmlw-retrieval-e5-base.
- Rerankery sdadas (polish-reranker-*) istnieją; licencji nie sprawdzałem. [?] https://huggingface.co/sdadas
| Biblioteka | Licencja | Wersja (data) | Pewn. |
|---|---|---|---|
| rank_bm25 | Apache-2.0 | 0.2.2 (2022, niepielęgnowana) | [✔] PyPI |
| bm25s | MIT | 0.3.16 (2026-10-28) | [✔] PyPI |
| sentence-transformers | Apache-2.0 | 6.3.0 (2026-11-11) | [✔] |
| sqlite-vec | MIT + Apache-2.0 (dual) | 0.1.9 (2026-03-31) | [✔] |
| chromadb | Apache-2.0 | 1.5.9 (2026-05-05) | [✔] |
| lancedb | Apache-2.0 | 0.41.0 (2026-10-29) | [✔] |
| faiss-cpu | MIT | 1.16.0 (2026-11-10) | [✔] |
Źródła: https://pypi.org/project/<nazwa>/ (JSON API PyPI). Polski w BM25: brak stemmera, rozważyć prostą normalizację/lematyzację (np. prefiksowe n-gramy) [?].
- Rekomendacja: SQLite (FTS5 + sqlite-vec) lub Chroma; jedna baza plikowa, proste wdrożenie offline.

## 4. Anonimizacja / NER po polsku
| Narzędzie / model | Licencja | Uwagi | URL | Pewn. |
|---|---|---|---|---|
| Microsoft Presidio (analyzer/anonymizer 2.2.366, 2026-10-27) | MIT | Polska: tylko `PlPeselRecognizer` (wzorzec + suma kontrolna wag 1,3,7,9); NIP/REGON/dowód/IBAN-PL trzeba dopisać; NER-owy silnik dla pl trzeba podłączyć samemu | https://github.com/microsoft/presidio ; https://pypi.org/project/presidio-analyzer/ | [✔] |
| spaCy (biblioteka 3.8.18) | MIT | tylko biblioteka | https://pypi.org/project/spacy/ | [✔] |
| **spaCy pl_core_news_sm/md/lg 3.8.0** | **GNU GPL 3.0** | potwierdzone w meta JSON: źródła UD Polish PDB i NKJP, obie GPL-3.0; NER F=0,80/0,83/0,84; rozmiary 19/47/547 MB | https://raw.githubusercontent.com/explosion/spacy-models/master/meta/pl_core_news_md-3.8.0.json | [✔] RYZYKO |
| pczarnik/herbert-base-ner | CC-BY-4.0 | PER/LOC/ORG, WikiANN-pl, F1 0,896 (deklarowane); baza HerBERT CC-BY-4.0 | https://huggingface.co/pczarnik/herbert-base-ner | [✔] |
| lexedit/herbert-polish-legal-ner | CC-BY-4.0 | 29 etykiet BIO: PER, ORG, LOC, LOC_PUB, DATE, MONEY, EMAIL, PHONE, ID, IBAN, DIAGNOSIS...; trenowany na dokumentach prawnych/administracyjnych (dane syntetyczne + rzeczywiste); brak raportu F1 w kartach, które odczytałem | https://huggingface.co/lexedit/herbert-polish-legal-ner | [✔] licencja; [?] jakość |
| NASK-PIB/BANonymizer-PL | Apache-2.0 | HerBERT-large; tylko pseudonimy i nazwiska (internet, BAN-PL) | https://huggingface.co/NASK-PIB/BANonymizer-PL | [✔] |
| flowxai/cee-pii (GLiNER) | Apache-2.0 | polski F1 0,94 exact (autorzy); 34 typy (pesel, nip, iban, phone, email, person_name, address); ~300M par., 1,15 GB; baza gliner_multi-v2.1 (mDeBERTa) | https://huggingface.co/flowxai/cee-pii | [✔] licencja; [?] wynik z własnego benchmarku |
| urchade/gliner_multi_pii-v1 | Apache-2.0 | karta nie potwierdza polskiego | https://huggingface.co/urchade/gliner_multi_pii-v1 | [✔]/[?] |
| knowledgator/gliner-pii-base-v1.0 | Apache-2.0 | polski niepotwierdzony | https://huggingface.co/knowledgator/gliner-pii-base-v1.0 | [✔]/[?] |
| Stanza pl (1.15.1, 2026-11-14) | kod Apache-2.0; modele na HF: Apache-2.0 | NER NKJP, F1 88,73: date, geogName, orgName, persName, placeName, time; dane NKJP/PDB są GPL -> status modeli niejasny | https://stanfordnlp.github.io/stanza/ner_models.html ; https://huggingface.co/stanfordnlp/stanza-pl | [✔] F1; [?] czystość licencyjna |
| CodeNLP/pdn2_v08_nkjp_large (PolDeepNer2, CLARIN) | MIT (karta HF) | NKJP, 12 kategorii; repo clarin-pl/poldeepner2 bez pliku licencji; dane NKJP GPL | https://huggingface.co/CodeNLP/pdn2_v08_nkjp_large ; https://github.com/clarin-pl/poldeepner2 | [✔] karta; [?] łańcuch |
| flair 0.15.1 | MIT | biblioteka; modele PL nieweryfikowane | https://pypi.org/project/flair/ | [✔]/[?] |
| llm-safe-pl | MIT | wycofany (DEPRECATED, następca pii-veil + pii-core); nie oceniałem | https://pypi.org/project/llm-safe-pl/ | [✔]/[?] |
- Liner2: licencji nie sprawdzałem. [?]
- Regexy z walidacją (własny kod, brak zależności): PESEL (wagi 1,3,7,9,1,3,7,9,1,3; cyfra kontrolna = (10 - suma mod 10) mod 10), NIP (wagi 6,5,7,2,3,4,5,6,7; mod 11), REGON 9/14 cyfr (wagi 8,9,2,3,4,5,6,7 / 2,4,8,5,0,9,7,3,6,1,2,4,8), IBAN PL (26 cyfr, mod 97), dowód osobisty (3 litery + 6 cyfr, suma kontrolna), telefon, e-mail, kod pocztowy `\d{2}-\d{3}`. Wzory sum kontrolnych z wiedzy własnej, zweryfikować testami na znanych numerach. [?]
- Realistycznie w 22 h bez GPU i z licencją permisywną: (a) regexy + sumy kontrolne dla identyfikatorów (deterministyczne, najpewniejsze), (b) imiona/nazwiska/adresy: **GLiNER cee-pii** (Apache-2.0, ~300M, działa na CPU) lub **herbert-polish-legal-ner** (CC-BY: wymaga wzmianki o atrybucji; dopuszcza użycie komercyjne), (c) rezerwowo słownik imion/nazwisk. Całość jako PROPOZYCJE do akceptacji urzędnika (zgodnie z wymogiem). Obowiązkowo zmierzyć jakość na własnych 20-30 przykładach, nie wierzyć F1 z kart.
- Uwaga: CC-BY-4.0 jest permisywna, ale wymaga atrybucji; pasuje do przeniesienia praw tylko jako zależność z zachowaną licencją (przenosi się autorskie prawa do własnego kodu, nie do cudzych komponentów).

## 5. Parsowanie dokumentów i generowanie
| Biblioteka | Licencja | Wersja (data) | Pewn. |
|---|---|---|---|
| pypdf | BSD-3-Clause | 7.1.1 (2026-11-18) | [✔] |
| pdfplumber | MIT | 0.11.11 (2026-11-21) | [✔] |
| pdfminer.six | MIT | 20260107 | [✔] |
| **PyMuPDF** | **AGPL-3.0 lub komercyjna Artifex** | 2.1 (2026-11-02) | [✔] UNIKAĆ |
| python-docx | MIT | 1.2.0 | [✔] |
| docx2python | MIT | 3.7.2 | [✔] |
| mammoth | BSD-2-Clause | 1.13.0 | [✔] |
| **docxtpl** | **LGPL-2.1-only** | 0.20.2 | [✔] ryzyko słabszego copyleftu |
| pytesseract | Apache-2.0 | 0.3.13 | [✔] |
| Tesseract + tessdata/tessdata_fast (pol.traineddata) | Apache-2.0 | - | [✔] https://github.com/tesseract-ocr/tessdata_fast |
| ocrmypdf | MPL-2.0 | 17.14.2 (2026-11-16) | [✔] (słaby copyleft na poziomie plików; używać jako narzędzie CLI) |
| pdf2image | MIT | 1.17.0 | [✔] (wymaga poppler, GPL - jako zewnętrzny program) [?] |
- Rekomendacja: pdfplumber/pdfminer + pypdf, python-docx, Tesseract pol (OCR skanów) przez wywołanie procesu. Szablony odpowiedzi: python-docx z własnymi placeholderami zamiast docxtpl. Źródło wszystkich: https://pypi.org/project/<nazwa>/.

## 6. Istniejące rozwiązania i luka
- EZD RP (NASK/MC): strona funkcji opisuje rejestrację korespondencji i bezpieczeństwo, nie wspomina o rejestrze UDIP ani AI/anonimizacji. https://www.gov.pl/web/ezd-rp/funkcje-systemu [✔] (brak wzmianki ≠ brak funkcji; sprawdzić podręcznik użytkownika) [?]
- Komercyjne systemy rejestru UDIP: wyniki wyszukiwania to głównie SWZ/BIP gmin; konkretnego produktu nie zidentyfikowałem. [?]
- Gdynia: umowa z konsorcjum HIVE AI na PLLuM (2.10.2025), chatbot dla mieszkańców i wyszukiwarka BIP; nie jest to narzędzie dla urzędników; brak info o on-premise. https://www.telepolis.pl/wiadomosci/ministerstwo-cyfryzacji-polska-sztuczna-inteligencja-pllum-pomoc-w-urzedzie-gdynia [~]
- Łódź i Częstochowa: PLLuM w samorządzie (komunikaty MC). https://www.gov.pl/web/cyfryzacja/polski-model-jezykowy-pllum-trafia-do-samorzadu [~] (stronę Łodzi nie udało się pobrać)
- mObywatel: asystent AI na PLLuM (zapowiedź 25.10.2025); COI planuje PLLuM dla urzędników (przetwarzanie dokumentów, wsparcie odpowiedzi). https://spidersweb.pl/2025/10/mobywatel-chatbot-pllum.html [~]
- Sądy: "Nowy Portal Orzeczeń" (publikacja, anonimizacja, wyszukiwanie) w planie 2026; brak informacji o AI w anonimizacji. https://www.gov.pl/attachment/4d0d6beb-5e87-4ff1-ad1b-672036d63769 [✔]/[?]
- Anonimizatory komercyjne/akademickie: Typly Anonimizator, eAuditor Bluur AI, Wolters Kluwer Praetor, "Anonymizer for Polish Language" (Politechnika Łódzka). Nie testowane. https://typly-marketing-page.pages.dev/anonimizator/ ; https://repozytorium.p.lodz.pl/items/fccad6ee-8e32-468f-a254-2359eec1365c [~]
- Watchdog Polska (Sieć Obywatelska): publikacje o stanie jawności, raport AI i opracowanie "Nadużywanie prawa do informacji" (lipiec 2026); narzędzia dla urzędników nie ustaliłem. https://siecobywatelska.pl/wp-content/uploads/2026/07/Naduzywanie-prawa-do-informacji.pdf [~]
- Luka (wniosek własny): brak ustalonego narzędzia łączącego w jednym przepływie rejestr UDIP, wyszukiwanie podobnych archiwalnych wniosków, podpowiedź komórki, szkic odpowiedzi z odpowiedzi wydziałów, anonimizację z akceptacją i kalendarz terminów, działającego offline. [?]

## 7. OWASP Top 10 for LLM Applications (wersja 2025)
Lista: LLM01 Prompt Injection, LLM02 Sensitive Information Disclosure, LLM03 Supply Chain, LLM04 Data and Model Poisoning, LLM05 Improper Output Handling, LLM06 Excessive Agency, LLM07 System Prompt Leakage, LLM08 Vector and Embedding Weaknesses, LLM09 Misinformation, LLM10 Unbounded Consumption. https://genai.owasp.org/llm-top-10/ [✔]
| Pozycja | Istotność | Środek | URL |
|---|---|---|---|
| LLM01 Prompt Injection | wgrywane pisma obywateli to niezaufana treść (mogą zawierać instrukcje) | oddzielać i oznaczać treść zewnętrzną, walidować format wyjścia kodem, najmniejsze uprawnienia, akceptacja człowieka | https://genai.owasp.org/llmrisk/llm01-prompt-injection/ |
| LLM02 Sensitive Info Disclosure | dane osobowe we wnioskach i archiwum | maskowanie przed użyciem, minimalny dostęp, nie polegać wyłącznie na promptcie | https://genai.owasp.org/llmrisk/llm022025-sensitive-information-disclosure/ |
| LLM06 Excessive Agency | wysyłka odpowiedzi/zmiana terminów | model tylko proponuje, urzędnik zatwierdza; brak narzędzi poza odczytem; autoryzacja poza LLM | https://genai.owasp.org/llmrisk/llm062025-excessive-agency/ |
| LLM03 Supply Chain / LLM08 Vector | modele z HF, indeks wektorowy | weryfikować sumy, licencje, izolować indeks per uprawnienia | https://genai.owasp.org/llm-top-10/ |
| LLM09 Misinformation | halucynacje w szkicu odpowiedzi | cytować źródła (ustawa, archiwum), oznaczać szkic jako projekt | jw. |
Wszystkie środki [✔] z OWASP (streszczone przeze mnie).

## Lista źródeł (dostęp 2026-11-21)
HF: speakleash (Bielik), CYFRAGOVPL (PLLuM), sdadas, BAAI/bge-m3, intfloat, Qwen, mistralai, pczarnik, lexedit, NASK-PIB, flowxai, urchade, knowledgator, CodeNLP, stanfordnlp. Ollama: ollama.com/SpeakLeash/*. GitHub: ollama, ggml-org/llama.cpp, vllm-project/vllm, microsoft/presidio, explosion/spacy-models, tesseract-ocr, clarin-pl/poldeepner2. PyPI JSON API dla wszystkich bibliotek. https://ai.google.dev/gemma/terms ; https://arxiv.org/pdf/2402.13350 (PIRB) ; https://genai.owasp.org/ ; https://www.gov.pl/web/ezd-rp/ ; https://www.instalki.pl/ ; https://www.telepolis.pl/ ; https://spidersweb.pl/ ; https://stanfordnlp.github.io/stanza/ner_models.html
Nieudane/niepewne: benchmark CPU Bielika; licencja Bielik-1.5B/Minitron; Ollama dla PLLuM; Liner2; licencje rerankerów sdadas; konkretny produkt UDIP w JST.
