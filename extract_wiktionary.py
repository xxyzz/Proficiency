import json
import operator
import pickle
import re
import subprocess
import tarfile
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.request import urlopen

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
            [
                "wget",
                "-nv",
                "-P",
                lang,
                f"https://kaikki.org/dictionary/{kaikki_lang}/{filename}",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

    return filepath


def download_zh_json(lang: str) -> Path:
    filepath = Path(f"{lang}/{lang}_zh.json")
    if not filepath.exists():
        with urlopen(
            f"https://github.com/xxyzz/wiktextract/releases/latest/download/{lang}_zh.tar.gz"
        ) as r:
            with tarfile.open(fileobj=BytesIO(r.read())) as tar:
                tar.extractall(lang)
    return filepath


def extract_wiktionary(
    lemma_lang: str, gloss_lang: str, kaikki_path: Path, difficulty_data: dict[str, int]
) -> list[Path]:
    words = []
    zh_cn_words = []
    enabled_words_pos = set()
    len_limit = 2 if lemma_lang in CJK_LANGS else 3
    if lemma_lang == "zh" or gloss_lang == "zh":
        import opencc

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

            word_pos = f"{word} {pos}"
            enabled = False if word_pos in enabled_words_pos else True
            difficulty = 1
            if difficulty_data:
                if enabled and word in difficulty_data:
                    difficulty = difficulty_data[word]
                else:
                    enabled = False
            else:
                difficulty = freq_to_difficulty(word, lemma_lang)

            if enabled:
                enabled_words_pos.add(word_pos)

            forms = get_forms(
                word, lemma_lang, gloss_lang, data.get("forms", []), pos, len_limit
            )
            if lemma_lang == "zh":
                simplified_form = converter.convert(word)
                if simplified_form != word:
                    forms.add(simplified_form)

            for sense in data.get("senses", []):
                examples = sense.get("examples", [])
                glosses = sense.get("glosses")
                example_sent = None
                if not glosses:
                    continue
                gloss = glosses[1] if len(glosses) > 1 else glosses[0]
                if (
                    lemma_lang == "es"
                    and gloss_lang == "en"
                    and re.match(SPANISH_INFLECTED_GLOSS, gloss)
                ):
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
                if not short_gloss:
                    short_gloss = gloss
                if short_gloss == "of":
                    continue
                ipas = get_ipas(lemma_lang, data.get("sounds", []))
                words.append(
                    (
                        enabled,
                        word,
                        pos,
                        short_gloss,
                        gloss,
                        example_sent,
                        ",".join(forms),
                        ipas,
                        difficulty,
                    )
                )
                if gloss_lang == "zh":
                    zh_cn_words.append(
                        (
                            enabled,
                            word,
                            pos,
                            converter.convert(short_gloss),
                            converter.convert(gloss),
                            converter.convert(example_sent) if example_sent else None,
                            ",".join(forms),
                            ipas,
                            difficulty,
                        )
                    )
                enabled = False

    return save_files(words, lemma_lang, gloss_lang, zh_cn_words)


def save_files(
    words: list[Any], lemma_lang: str, gloss_lang: str, zh_cn_words: list[Any]
) -> list[Path]:
    from main import MAJOR_VERSION

    words.sort(key=operator.itemgetter(1))
    lemmas_tst = TST()
    lemmas_row = []
    added_lemmas = set()
    for row, data in enumerate(words):
        lemma = data[1]
        if lemma not in added_lemmas:
            lemmas_row.append((lemma, row))
            added_lemmas.add(lemma)
    lemmas_tst.put_values(lemmas_row)
    tst_path = Path(
        f"{lemma_lang}/wiktionary_{lemma_lang}_{gloss_lang}_tst_v{MAJOR_VERSION}"
    )
    if not tst_path.parent.exists():
        tst_path.parent.mkdir()
    with tst_path.open("wb") as f:
        pickle.dump(lemmas_tst, f)

    wiktionary_json_path = Path(
        f"{lemma_lang}/wiktionary_{lemma_lang}_{gloss_lang}_v{MAJOR_VERSION}.json"
    )
    with wiktionary_json_path.open("w", encoding="utf-8") as f:
        json.dump(words, f)

    if gloss_lang == "zh":
        zh_cn_words.sort(key=operator.itemgetter(1))
        with open(
            f"{lemma_lang}/wiktionary_{lemma_lang}_zh_cn_v{MAJOR_VERSION}.json",
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(zh_cn_words, f)

    return [wiktionary_json_path, tst_path]


def get_ipas(lang: str, sounds: list[dict[str, str]]) -> dict[str, str] | str:
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
    gloss = gloss.removesuffix(".").removesuffix("。")
    gloss = re.sub(
        r"\([^)]+\)|（[^）]+）|〈[^〉]+〉|\[[^]]+\]|［[^］]+］|【[^】]+】|﹝[^﹞]+﹞|「[^」]+」",
        "",
        gloss,
    )
    gloss = min(re.split(";|；", gloss), key=len)
    gloss = min(re.split(",|，", gloss), key=len)
    gloss = min(re.split("、|/", gloss), key=len)
    return gloss.strip()


def freq_to_difficulty(word: str, lang: str) -> int:
    from wordfreq import zipf_frequency

    freq = zipf_frequency(word, lang)
    if freq >= 7:
        return 5
    elif freq >= 5:
        return 4
    elif freq >= 3:
        return 3
    elif freq >= 1:
        return 2
    else:
        return 1


# https://lemminflect.readthedocs.io/en/latest/tags/
LEMMINFLECT_POS_TAGS = {
    "adj": "ADJ",
    "adv": "ADV",
    "noun": "NOUN",
    "name": "PROPN",
    "verb": "VERB",
}


def get_forms(
    word: str,
    lemma_lang: str,
    gloss_lang: str,
    forms_data: list[dict[str, str]],
    pos: str,
    len_limit: int,
) -> set[str]:
    forms: set[str] = set()
    if lemma_lang == "en" and gloss_lang == "zh":
        from en.dump_kindle_lemmas import get_inflections

        # Extracted Chinese Wiktionary forms data are not usable yet
        find_forms = get_inflections(word, LEMMINFLECT_POS_TAGS.get(pos))
        if find_forms:
            if word in find_forms:
                find_forms.remove(word)
            if find_forms:
                forms = find_forms
    else:
        for form in map(lambda x: x.get("form", ""), forms_data):
            if gloss_lang == "zh" and (
                form.startswith("Category:") or len(form) / len(word) > 2
            ):
                # temporarily filter garbage data
                continue
            if form and form != word and len(form) >= len_limit:
                forms.add(form)

    return forms
