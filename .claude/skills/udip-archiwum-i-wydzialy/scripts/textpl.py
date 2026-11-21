"""Wspólne narzędzia tekstowe dla polskiego: tokenizacja, stopwords, lekki stemmer (bez zależności).

Stemmer obcina typowe końcówki fleksyjne. To nie jest lematyzator (Morfeusz2 ma licencję BSD-2 dla
programu i słownika SGJP na CC BY-SA – sprawdź przed użyciem), ale dla BM25 na krótkich wnioskach wystarcza.
"""
from __future__ import annotations

import re
import unicodedata

STOP = set("""a aby albo ale ani aż bardzo bez bo być był była było były będzie będą by byłoby cała cały ci cię co czy czyli dla do
dlaczego dnia dni dzień gdy gdzie go i ich ile im in innych jak jaka jaki jakie jako je jego jej jest jestem jeszcze jeśli już ją
każdy kiedy kto która które którego której który których którym którzy lub ma mają mam mi między mnie mną moje mój może można mu
my na nad nam nas nasz nie niego niej nim nią o od oraz po pod podać podanie proszę przez przy r roku sa się są ta tak takie także
tam te tego tej ten to tu tych tym u w we wg więc wraz wszystkie wszystkich z za ze że żeby oraz itp itd tj.
wniosek wnoszę wniosku informacji informacja informację publicznej publiczną udostępnienie udostępnienia uprzejmie zwracam
dostępie ustawy ustawa art ust pkt podstawie dotyczące dotyczy prośba proszę udzielenie odpowiedzi odpowiedź szanowni państwo
mieszkaniec mieszkańca mieszkańców mieszkańcy mieszkańcom ilu ile ilość liczba liczby koniec roku rok latach miasto miasta miasta urząd urzędu""".split())

SUFFIXES = sorted("""owego owej owym owych owie owi ami ach ego emu ymi imi ów om ach ach iej ej ym im ych ich ą ę y i a e o u
ości ość ością ościami ościach anie aniu ania aniem enie eniu enia eniem acji acja acją acje cji cja cją cje
owy owa owe ową owych""".split(), key=len, reverse=True)
MAXLEN = 6  # obcięcie do 6 znaków: prosta, skuteczna „stemizacja” dla polskiego w IR (mieszkań/mieszkanie → mieszk)

TOKEN = re.compile(r"[a-ząćęłńóśźż0-9]+", re.I)


def norm(s: str) -> str:
    return unicodedata.normalize("NFC", s).lower()


def stem(w: str) -> str:
    if len(w) <= 4 or w.isdigit():
        return w
    for suf in SUFFIXES:
        if w.endswith(suf) and len(w) - len(suf) >= 4:
            w = w[: -len(suf)]
            break
    return w[:MAXLEN]


def tokens(text: str, keep_stop: bool = False, keep_numbers: bool = False) -> list[str]:
    out = []
    for t in TOKEN.findall(norm(text)):
        if t.isdigit() and not keep_numbers:
            continue  # lata i kwoty zaszumiają podobieństwo tematów
        if not keep_stop and (t in STOP or len(t) < 3):
            continue
        out.append(stem(t))
    return out
