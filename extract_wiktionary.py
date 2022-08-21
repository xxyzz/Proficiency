import json
import pickle
import re
import subprocess
from pathlib import Path

import opencc

from tst import TST

FILTER_TAGS = frozenset(
    {
        "plural",
        "alternative",
        "obsolete",
        "abbreviation",
        "initialism",
        "form-of",
        "misspelling",
        "alt-of",
        "compound-of",  # Spanish
    }
)
SPANISH_INFLECTED_GLOSS = (
    r"(?:first|second|third)-person|only used in|gerund combined with"
)
CJK_LANGS = ["zh", "ja", "ko"]
POS_TYPES = frozenset(["adj", "adv", "noun", "phrase", "proverb", "verb"])


def download_kaikki_json(lang: str, kaikki_lang: str) -> Path:
    filename_lang = re.sub(r"[\s-]", "", kaikki_lang)
    filename = f"kaikki.org-dictionary-{filename_lang}.json"
    filepath = Path(f"{lang}/{filename}")
    if not filepath.exists():
        subprocess.run(
            ["wget", f"https://kaikki.org/dictionary/{kaikki_lang}/{filename}"],
            check=True,
            capture_output=True,
            text=True,
        )
    return filepath


def extract_wiktionary(
    lang: str, kaikki_path: Path, difficulty_data: dict[str, int]
) -> list[Path]:
    from main import VERSION

    print(f"Extracting {lang} Wiktionary JSON file")
    words = []
    enabled_words_pos = set()
    len_limit = 2 if lang in CJK_LANGS else 3
    if lang == "zh":
        converter = opencc.OpenCC("t2s.json")

    with open(kaikki_path, encoding="utf-8") as f:
        for line in f:
            data = json.loads(line)
            word = data.get("word")
            pos = data.get("pos")
            if (
                pos not in POS_TYPES
                or len(word) < len_limit
                or re.match(r"\W|\d", word)
            ):
                continue
            if lang in CJK_LANGS and re.fullmatch(r"[a-zA-Z\d]+", word):
                continue

            word_pos = f"{word} {pos}"
            enabled = False if word_pos in enabled_words_pos else True
            difficulty = 1
            if difficulty_data:
                if enabled and word in difficulty_data:
                    enabled = True
                    difficulty = difficulty_data[word]
                else:
                    enabled = False
            if enabled:
                enabled_words_pos.add(word_pos)

            forms = set()
            for form in map(lambda x: x.get("form"), data.get("forms", [])):
                if form and form != word and len(form) >= len_limit:
                    forms.add(form)
            if lang == "zh":
                simplified_form = converter.convert(word)
                if simplified_form != word:
                    forms.add(simplified_form)

            for sense in data.get("senses", []):
                examples = sense.get("examples", [])
                glosses = sense.get("glosses")
                example_sent = None
                if not glosses:
                    continue
                if len(glosses) > 1:
                    gloss = glosses[1]
                else:
                    gloss = glosses[0]
                if lang == "es" and re.match(SPANISH_INFLECTED_GLOSS, gloss):
                    continue
                tags = set(sense.get("tags", []))
                if tags.intersection(FILTER_TAGS):
                    continue
                for example in examples:
                    example = example.get("text")
                    if example and example != "(obsolete)":
                        example_sent = example
                        break
                short_gloss = short_def(gloss)
                if short_gloss == "of":
                    continue
                words.append(
                    (
                        enabled,
                        word,
                        pos,
                        short_gloss,
                        gloss,
                        example_sent,
                        ",".join(forms),
                        get_ipas(lang, data.get("sounds", [])),
                        difficulty,
                    )
                )
                enabled = False

    words.sort(key=lambda x: x[1])
    lemmas_tst = TST()
    lemmas_row = []
    added_lemmas = set()
    for row, data in enumerate(words):
        lemma = data[1]
        if lemma not in added_lemmas:
            lemmas_row.append((lemma, row))
            added_lemmas.add(lemma)
    lemmas_tst.put_values(lemmas_row)
    tst_filename = f"{lang}/wiktionary_{lang}_tst_v{VERSION}"
    with open(tst_filename, "wb") as f:
        pickle.dump(lemmas_tst, f)

    wiktionary_json_filename = f"{lang}/wiktionary_{lang}_v{VERSION}.json"
    with open(wiktionary_json_filename, "w", encoding="utf-8") as f:
        json.dump(words, f)
    return [Path(wiktionary_json_filename), Path(tst_filename)]


def get_ipas(lang, sounds):
    ipas = {}
    if lang == "en":
        for sound in sounds:
            ipa = sound.get("ipa")
            if not ipa:
                continue
            tags = sound.get("tags")
            if not tags:
                return ipa
            if ("US" in tags or "General-American" in tags) and "US" not in ipas:
                ipas["US"] = ipa
            if ("UK" in tags or "Received-Pronunciation" in tags) and "UK" not in ipas:
                ipas["UK"] = ipa
    elif lang == "zh":
        for sound in sounds:
            pron = sound.get("zh-pron")
            if not pron:
                continue
            tags = sound.get("tags")
            if not tags:
                return pron
            if "Mandarin" in tags:
                if "Pinyin" in tags and "Pinyin" not in ipas:
                    ipas["Pinyin"] = pron
                elif "bopomofo" in tags and "bopomofo" not in ipas:
                    ipas["bopomofo"] = pron
    else:
        for sound in sounds:
            if "ipa" in sound:
                return sound["ipa"]

    return ipas if ipas else ""


def short_def(gloss: str) -> str:
    gloss = gloss.removesuffix(".")
    gloss = re.sub(r"\([^)]+\) ?", "", gloss)
    gloss = min(gloss.split(";"), key=len)
    gloss = gloss.split(",", 1)[0]
    return gloss.strip()
