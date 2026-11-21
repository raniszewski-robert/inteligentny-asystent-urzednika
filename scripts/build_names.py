"""T28: build the name lexicon in udip/data/names/ (run once; the output is committed).

Sources (all bundled data is MIT or BSD-2, see udip/data/names/README.md):
- Faker (MIT): pl_PL, uk_UA, ru_RU person providers – first names and surnames.
- Mimesis (MIT): pl, uk, ru person datasets – first names and surnames.
- Morfeusz 2 + SGJP (BSD-2), build time only: exact Polish inflected forms of first names and surnames.
Ukrainian and Russian names are transliterated twice: the passport Latin spelling (KMU 2010 / ICAO 9303, plus the
common y/yu/ya variant) and the Polish spelling (PWN), e.g. Олена Шевченко → Olena Shevchenko, Ołena Szewczenko.

    pip install faker mimesis morfeusz2   # build-time only, not in requirements.txt
    python scripts/build_names.py

Writes imiona.tsv and nazwiska.tsv ("form<TAB>base[<TAB>amb]", singular forms only).
"""
from __future__ import annotations

import ast
import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "udip" / "data" / "names"
CYR_VOWELS = set("аеєиіїоуюяёыэь'ъй")

# ---------------------------------------------------------------- sources


def _faker(locale: str) -> dict[str, list[str]]:
    spec = importlib.util.find_spec("faker")
    path = Path(spec.origin).parent / "providers" / "person" / locale / "__init__.py"
    out: dict[str, list[str]] = {}
    for n in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        target, value = None, None
        if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name):
            target, value = n.targets[0].id, n.value
        elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name):
            target, value = n.target.id, n.value
        if target and isinstance(value, (ast.Tuple, ast.List, ast.Dict)):
            try:
                v = ast.literal_eval(value)
            except ValueError:
                continue
            out[target] = list(v.keys()) if isinstance(v, dict) else list(v)
    return out


def _mimesis(locale: str) -> dict:
    spec = importlib.util.find_spec("mimesis")
    return json.loads((Path(spec.origin).parent / "datasets" / locale / "person.json").read_text(encoding="utf-8"))


def _clean(xs) -> set[str]:
    return {x.strip() for x in xs if isinstance(x, str) and re.fullmatch(r"[^\W\d_]+(?:-[^\W\d_]+)?", x.strip()) and len(x.strip()) >= 3}


def sources() -> dict[str, set[str]]:
    fpl, fua, fru = _faker("pl_PL"), _faker("uk_UA"), _faker("ru_RU")
    mpl, mua, mru = _mimesis("pl"), _mimesis("uk"), _mimesis("ru")
    hand = [x.strip() for x in (ROOT / "udip" / "data" / "imiona.txt").read_text(encoding="utf-8").splitlines()
            if x.strip() and not x.startswith("#")]
    pick = lambda d, *keys: [v for k in keys for v in d.get(k, [])]
    return {
        "pl_first": _clean(hand + pick(fpl, "first_names_male", "first_names_female") + mpl["names"]["male"] + mpl["names"]["female"]),
        "pl_last": _clean(pick(fpl, "unisex_last_names", "male_last_names") + mpl["surnames"]["male"] + mpl["surnames"]["female"]),
        "ua_first": _clean(pick(fua, "first_names_male", "first_names_female") + mua["names"]["male"] + mua["names"]["female"]),
        "ua_last": _clean(pick(fua, "last_names_common", "last_names_male_only", "last_names_female_only")
                          + mua["surnames"]["male"] + mua["surnames"]["female"]),
        "ru_first": _clean(pick(fru, "first_names_male", "first_names_female") + mru["names"]["male"] + mru["names"]["female"]),
        "ru_last": _clean(pick(fru, "last_names_male", "last_names_female") + mru["surnames"]["male"] + mru["surnames"]["female"]),
    }

# ---------------------------------------------------------------- transliteration


def _translit(word: str, table: dict, iotated: dict, popular: bool) -> str:
    w = word.lower().replace("’", "'").replace("ʼ", "'")
    out = []
    for i, ch in enumerate(w):
        prev = w[i - 1] if i else ""
        if ch in iotated:
            start = i == 0 and table is UA_LAT  # KMU: y-form only at the word start; ICAO: always the i-form
            out.append(iotated[ch][0] if (start or popular) else iotated[ch][1])
        elif ch == "г" and prev == "з" and table is UA_LAT:
            out.append("gh")  # KMU 2010: зг → zgh
        else:
            out.append(table.get(ch, ch))
    s = "".join(out)
    return s[:1].upper() + s[1:]


UA_LAT = dict(zip("абвгґдежзиіклмнопрстуфхцчшщь'", ["a", "b", "v", "h", "g", "d", "e", "zh", "z", "y", "i", "k", "l", "m", "n", "o",
                                                   "p", "r", "s", "t", "u", "f", "kh", "ts", "ch", "sh", "shch", "", ""]))
UA_LAT_IOT = {"є": ("ye", "ie"), "ї": ("yi", "i"), "й": ("y", "i"), "ю": ("yu", "iu"), "я": ("ya", "ia")}
RU_LAT = dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэ", ["a", "b", "v", "g", "d", "e", "e", "zh", "z", "i", "i", "k", "l", "m", "n", "o",
                                                     "p", "r", "s", "t", "u", "f", "kh", "ts", "ch", "sh", "shch", "ie", "y", "", "e"]))
RU_LAT_IOT = {"ю": ("yu", "iu"), "я": ("ya", "ia")}
RU_LAT.update({"і": "i", "ї": "i", "є": "e"})  # Ukrainian letters that slip into the Russian lists


def lat(word: str, lang: str) -> set[str]:
    """Passport spelling (KMU 2010 for Ukrainian, ICAO 9303 for Russian) and the common y-variant."""
    if lang == "ua":
        return {_translit(word, UA_LAT, UA_LAT_IOT, False), _translit(word, UA_LAT, UA_LAT_IOT, True)}
    pop = dict(RU_LAT, **{"й": "y", "ъ": ""})
    return {_translit(word, RU_LAT, RU_LAT_IOT, False), _translit(word, pop, RU_LAT_IOT, True)}


PL_BASE = dict(zip("абвгґдежзиіклмнопрстуфхцчшщыэ", ["a", "b", "w", "h", "g", "d", "e", "ż", "z", "y", "i", "k", "ł", "m", "n", "o",
                                                  "p", "r", "s", "t", "u", "f", "ch", "c", "cz", "sz", "szcz", "y", "e"]))
SOFT = {"н": "ń", "с": "ś", "з": "ź", "ц": "ć", "л": "l"}


def pl(word: str, lang: str) -> str:
    """Polish transliteration (PWN rules, simplified): Олена → Ołena, Шевченко → Szewczenko, Ольга → Olha."""
    w = word.lower().replace("’", "'").replace("ʼ", "'")
    base = dict(PL_BASE)
    if lang == "ru":
        base["г"] = "g"
        base["и"] = "i"
    out = []
    for i, ch in enumerate(w):
        prev = w[i - 1] if i else "#"
        nxt = w[i + 1] if i + 1 < len(w) else "#"
        start = i == 0 or prev in CYR_VOWELS
        if ch == "л":
            out.append("l" if nxt in "іїєюяеёиь" and not (lang == "ua" and nxt in "еи") else "ł")
        elif ch == "ь":
            if prev in SOFT and prev != "л" and nxt not in "аеєиіїоуюяё":
                out[-1] = SOFT[prev]
            elif prev in SOFT and prev != "л":
                out[-1] = SOFT[prev]
        elif ch in "'ъ":
            continue
        elif ch in "єюяёї" or (ch == "е" and lang == "ru"):
            v = {"є": "e", "ю": "u", "я": "a", "ё": "o", "ї": "i", "е": "e"}[ch]
            if ch == "ї":
                out.append("ji" if start or prev == "'" else "i")
            elif start or prev in "'ъь":
                out.append(("j" + v) if not (ch == "е" and lang == "ru" and i > 0 and prev not in CYR_VOWELS | {"ъ", "ь"}) else v)
            elif prev == "л":
                out.append(v)
            elif ch == "е":
                out.append("e")
            elif prev in "жчшщ":
                out.append(v)
            else:
                out.append("i" + v)
        elif ch == "и" and lang == "ru" and prev in "жшц":
            out.append("y")
        elif ch == "й":
            out.append("j")
        else:
            out.append(base.get(ch, ch))
    s = "".join(out)
    return s[:1].upper() + s[1:]

# ---------------------------------------------------------------- inflection


def first_forms_heuristic(base: str) -> set[str]:
    import sys
    sys.path.insert(0, str(ROOT))
    from udip.anonymize import name_forms
    return name_forms(base)


def surname_forms_heuristic(s: str) -> set[str]:
    f = {s}
    if re.search(r"(sk|ck|dzk)i$", s):
        st = s[:-1]
        f |= {st + "iego", st + "iemu", st + "im", s[:-1] + "a", s[:-1] + "iej", s[:-1] + "ą"}
    elif re.search(r"(sk|ck|dzk)a$", s):
        f |= {s[:-1] + "iej", s[:-1] + "ą"}
    elif re.search(r"(sky|skyi|skyy|skij|skiy|skii)$", s, re.I):
        pass
    elif s.endswith("a"):
        f |= {s[:-1] + "y", s[:-1] + "ą", s[:-1] + "ej"} if re.search(r"(ow|ew|in|yn)a$", s) else {s[:-1] + "y", s[:-1] + "ą", s[:-1] + "ę"}
    elif s.endswith(("o", "e", "i", "u", "y", "ij", "yj", "iy", "yi")):
        pass
    else:
        st = s[:-2] + s[-1] if re.search(r"[^aeiouyąęó]ek$", s) else s
        f |= {st + "a", st + "owi", st + "em", st + "u"}
    return f


def morfeusz_forms(lemmas: set[str], qualifier: str) -> tuple[dict[str, str], set[str]]:
    import morfeusz2
    m = morfeusz2.Morfeusz()
    forms: dict[str, str] = {}
    unknown = set()
    for lem in sorted(lemmas):
        todo = [lem]
        if re.search(r"(sk|ck|dzk)i$", lem):
            todo.append(lem[:-1] + "a")
        hit = False
        for l in todo:
            try:
                gen = m.generate(l)
            except Exception:
                gen = []
            for form, _lemma, tag, quals, _ in gen:
                if qualifier in quals and (":sg:" in tag or "sg.pl" in tag) and form[:1].isupper():
                    forms.setdefault(form, lem)
                    hit = True
        if not hit:
            unknown.add(lem)
    return forms, unknown


def build() -> dict[str, dict[str, str]]:
    src = sources()
    first: dict[str, str] = {}
    last: dict[str, str] = {}
    f_pl, unk = morfeusz_forms(src["pl_first"], "imię")
    first.update(f_pl)
    for b in unk:
        for f in first_forms_heuristic(b):
            first.setdefault(f, b)
    s_pl, unk = morfeusz_forms(src["pl_last"], "nazwisko")
    last.update(s_pl)
    for b in unk:
        for f in surname_forms_heuristic(b):
            last.setdefault(f, b)
    for lang in ("ua", "ru"):
        for cyr in src[f"{lang}_first"]:
            for b in lat(cyr, lang) | {pl(cyr, lang)}:
                for f in first_forms_heuristic(b):
                    first.setdefault(f, b)
        for cyr in src[f"{lang}_last"]:
            for b in lat(cyr, lang) | {pl(cyr, lang)}:
                for f in surname_forms_heuristic(b):
                    last.setdefault(f, b)
    stop = {x.strip() for x in (ROOT / "udip" / "data" / "nie_nazwiska.txt").read_text(encoding="utf-8").splitlines()
            if x.strip() and not x.startswith("#")}
    ok = re.compile(r"[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+(?:-[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)?")
    clean = lambda d: {k: v for k, v in d.items() if len(k) >= 3 and ok.fullmatch(k) and k not in stop}
    return {"imiona": clean(first), "nazwiska": clean(last)}


def ambiguous(forms: dict[str, str]) -> set[str]:
    """Forms that are also ordinary Polish words in lower case (Mieszka 'lives', Zając 'hare', Lew 'lion').
    The app treats these as a name only next to another name part."""
    import morfeusz2
    m = morfeusz2.Morfeusz()
    out = set()
    for f, base in forms.items():
        low = f.lower()
        adj_ok = re.search(r"(sk|ck|dzk)[ia]$", base) is not None  # Kowalska is also an adjective; the surname reading wins
        for _s, _e, (_orth, lemma, tag, _q, _l) in m.analyse(low):
            if adj_ok and tag.startswith("adj"):
                continue
            if tag != "ign" and lemma[:1].islower():
                out.add(f)
                break
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    res = build()
    for name, d in res.items():
        amb = ambiguous(d)
        lines = [f"{k}\t{v}" + ("\tamb" if k in amb else "") for k, v in sorted(d.items())]
        (OUT / f"{name}.tsv").write_text("# form<TAB>base[<TAB>amb] – generated by scripts/build_names.py, see README.md;"
                                         " amb = also an ordinary word, used only next to another name part\n"
                                         + "\n".join(lines) + "\n", encoding="utf-8")
        print(name, len(d), "forms,", len(set(d.values())), "bases,", len(amb), "ambiguous")


if __name__ == "__main__":
    main()
