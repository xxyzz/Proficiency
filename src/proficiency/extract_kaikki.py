import json
import re
import sqlite3
import subprocess
from pathlib import Path
from shutil import which
from typing import Any

from .database import create_indexes_then_close, init_db, wiktionary_db_path
from .util import (
    freq_to_difficulty,
    get_short_def,
    get_shortest_lemma_length,
    load_difficulty_data,
)

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
USED_POS_TYPES = frozenset(["adj", "adv", "noun", "phrase", "proverb", "verb"])


def download_kaikki_json(gloss_lang: str) -> None:
    from .split_jsonl import split_kaikki_jsonl

    url = "https://kaikki.org/"
    if gloss_lang == "en":
        url += "dictionary/"
    else:
        url += f"{gloss_lang}wiktionary/"
    url += "raw-wiktextract-data.json.gz"

    gz_path = Path(f"build/{url.rsplit('/', 1)[1]}")
    if not gz_path.exists():
        subprocess.run(
            ["wget", "-nv", "-P", "build", url],
            check=True,
            capture_output=True,
            text=True,
        )
    if gz_path.exists():
        if which("pigz") is None and which("gzip") is None:
            import gzip

            with gzip.open(gz_path, "rb") as f:
                split_kaikki_jsonl(f, gloss_lang)
        else:
            sub_p = subprocess.Popen(
                [
                    "pigz" if which("pigz") is not None else "gzip",
                    "-d",
                    "-c",
                    str(gz_path),
                ],
                stdout=subprocess.PIPE,
            )
            if sub_p.stdout is not None:
                with sub_p.stdout as f:
                    split_kaikki_jsonl(f, gloss_lang)
            sub_p.wait()
        gz_path.unlink()


def load_data(lemma_lang: str, gloss_lang: str) -> tuple[Path, dict[str, int]]:
    if lemma_lang == "hr":
        lemma_lang = "sh"
    kaikki_json_path = Path(f"build/{lemma_lang}/{lemma_lang}_{gloss_lang}.jsonl")

    difficulty_data = load_difficulty_data(lemma_lang)
    return kaikki_json_path, difficulty_data


def create_lemmas_db_from_kaikki(lemma_lang: str, gloss_lang: str) -> list[Path]:
    kaikki_json_path, difficulty_data = load_data(lemma_lang, gloss_lang)

    db_path = wiktionary_db_path(lemma_lang, gloss_lang)
    conn = init_db(db_path, lemma_lang, False, True)
    if gloss_lang == "zh":
        zh_cn_db_path = wiktionary_db_path(lemma_lang, "zh_cn")
        zh_cn_conn = init_db(zh_cn_db_path, lemma_lang, False, True)

    enabled_words_pos: set[str] = set()
    len_limit = get_shortest_lemma_length(lemma_lang)
    if lemma_lang == "zh" or gloss_lang == "zh":
        import opencc

        converter = opencc.OpenCC("t2s.json")

    lemma_ids: dict[str, int] = {}

    with open(kaikki_json_path, encoding="utf-8") as f:
        for line in f:
            data = json.loads(line)
            word = data.get("word")
            pos = data.get("pos")
            if (
                pos not in USED_POS_TYPES
                or len(word) < len_limit
                or re.match(r"\W|\d", word)
                or is_form_entry(gloss_lang, data)
            ):
                continue

            word_pos = f"{word} {pos}"
            enabled = False if word_pos in enabled_words_pos else True
            difficulty = 1
            if difficulty_data:
                if word in difficulty_data:
                    difficulty = difficulty_data[word]
                else:
                    enabled = False
            else:
                disabled_by_freq, difficulty = freq_to_difficulty(word, lemma_lang)
                if disabled_by_freq:
                    enabled = False

            if enabled:
                enabled_words_pos.add(word_pos)

            forms = get_forms(
                word, lemma_lang, gloss_lang, data.get("forms", []), pos, len_limit
            )
            if lemma_lang == "zh":
                simplified_form = converter.convert(word)
                if simplified_form != word:
                    forms.add(simplified_form)

            sense_data = []
            zh_cn_sense_data = []

            for sense in data.get("senses", []):
                examples = sense.get("examples", [])
                glosses = sense.get("glosses")
                example_sent = None
                if not glosses or is_form_entry(gloss_lang, sense):
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

                for example_data in examples:
                    # Use the first example
                    example_text = example_data.get("text", "")
                    if len(example_text) > 0 and example_text != "(obsolete)":
                        example_sent = example_text
                        break
                    # Chinese Wiktionary
                    example_texts = example_data.get("texts", [])
                    if len(example_texts) > 0:
                        example_sent = example_texts[0]
                        break

                short_gloss = get_short_def(gloss, gloss_lang)
                if not short_gloss:
                    continue
                sense_data.append((enabled, short_gloss, gloss, example_sent))
                if gloss_lang == "zh":
                    zh_cn_sense_data.append(
                        (
                            enabled,
                            converter.convert(short_gloss),
                            converter.convert(gloss),
                            (
                                converter.convert(example_sent)
                                if example_sent is not None
                                else None
                            ),
                        )
                    )
                enabled = False

            if sense_data:
                ipas = get_ipas(lemma_lang, data.get("sounds", []))
                lemma_id = insert_lemma(
                    word,
                    lemma_lang,
                    ipas,
                    lemma_ids,
                    [conn, zh_cn_conn] if gloss_lang == "zh" else [conn],
                )
                insert_forms(conn, forms, pos, lemma_id)
                insert_senses(conn, sense_data, lemma_id, pos, difficulty)
                if gloss_lang == "zh":
                    insert_forms(zh_cn_conn, forms, pos, lemma_id)
                    insert_senses(
                        zh_cn_conn, zh_cn_sense_data, lemma_id, pos, difficulty
                    )

    create_indexes_then_close(conn)
    if gloss_lang == "zh":
        create_indexes_then_close(zh_cn_conn)
    kaikki_json_path.unlink()
    return [db_path, zh_cn_db_path] if gloss_lang == "zh" else [db_path]


def insert_lemma(
    lemma: str,
    lemma_lang: str,
    ipas: dict[str, str] | str,
    lemma_ids: dict[str, int],
    conn_list: list[sqlite3.Connection],
) -> int:
    if lemma in lemma_ids:
        return lemma_ids[lemma]

    if lemma_lang == "en":
        sql = "INSERT INTO lemmas (lemma, ga_ipa, rp_ipa) VALUES(?, ?, ?) RETURNING id"
    elif lemma_lang == "zh":
        sql = (
            "INSERT INTO lemmas (lemma, pinyin, bopomofo) VALUES(?, ?, ?) RETURNING id"
        )
    else:
        sql = "INSERT INTO lemmas (lemma, ipa) VALUES(?, ?) RETURNING id"

    if lemma_lang == "en":
        ipas_data = (
            (ipas.get("ga_ipa", ""), ipas.get("rp_ipa", ""))
            if isinstance(ipas, dict)
            else (ipas, "")
        )
        data = (lemma,) + ipas_data
    elif lemma_lang == "zh":
        ipas_data = (
            (ipas.get("pinyin", ""), ipas.get("bopomofo", ""))
            if isinstance(ipas, dict)
            else (ipas, "")
        )
        data = (lemma,) + ipas_data
    else:
        data = (lemma, ipas)  # type: ignore

    lemma_id = 0
    for conn in conn_list:
        for (new_lemma_id,) in conn.execute(sql, data):
            lemma_id = new_lemma_id
    lemma_ids[lemma] = lemma_id
    return lemma_id


def insert_forms(
    conn: sqlite3.Connection, forms: set[str], pos: str, lemma_id: int
) -> None:
    conn.executemany(
        "INSERT OR IGNORE INTO forms VALUES(?, ?, ?)",
        ((form, pos, lemma_id) for form in forms),
    )


def insert_senses(
    conn: sqlite3.Connection, data_list: Any, lemma_id: int, pos: str, difficulty: int
) -> None:
    conn.executemany(
        """
        INSERT INTO senses
        (enabled, short_def, full_def, example, lemma_id, pos, difficulty)
        VALUES(?, ?, ?, ?, ?, ?, ?)
        """,
        (data + (lemma_id, pos, difficulty) for data in data_list),
    )


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
            if ("US" in tags or "General-American" in tags) and "ga_ipa" not in ipas:
                ipas["ga_ipa"] = ipa
            if (
                "UK" in tags or "Received-Pronunciation" in tags
            ) and "rp_ipa" not in ipas:
                ipas["rp_ipa"] = ipa
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
                    ipas["pinyin"] = pron
                elif (
                    "bopomofo" in tags or "Zhuyin" in tags
                ) and "bopomofo" not in ipas:
                    ipas["bopomofo"] = pron
    else:
        for sound in sounds:
            if "ipa" in sound:
                return sound["ipa"]

    return ipas if ipas else ""


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
    from wiktextract_lemmatization.utils import FORM_TAGS_TO_IGNORE, remove_accents

    forms: set[str] = set()
    if lemma_lang in ["de", "da"]:  # German, Danish
        forms_data = [
            data
            for data in forms_data
            if "tags" not in data
            or (
                "tags" in data
                and not any(tag in FORM_TAGS_TO_IGNORE for tag in data["tags"])
            )
        ]

    for form in map(lambda x: x.get("form", ""), forms_data):
        if form and form != word and len(form) >= len_limit:
            forms.add(form)

    if lemma_lang == "cs":
        if (
            pos in ["adj", "verb", "adv"]
            and not word.startswith("ne")
            and " " not in word
        ):
            # Negative form: https://en.wikipedia.org/wiki/Czech_language#Grammar
            forms |= {f"ne{form}" for form in forms}
        if pos == "adj":
            # Wiktionary doesn't have the dual instrumental form in declension tables
            # https://linguistics.stackexchange.com/questions/48502/what-is-the-behind-the-declension-obrovskýma-in-the-phrase-obrovskýma-očima/48507#48507
            forms |= {form[:-3] + "ýma" for form in forms if form.endswith("ými")}

    if lemma_lang in ["ru", "uk"]:  # Russian, Ukrainian
        forms |= {remove_accents(form) for form in forms}
    return forms


ZH_FORMS_CAT_SUFFIXES = ("變格形", "變位形式", "複數形式")
FR_FORMS_CAT_PREFIXES = ("Formes",)


def is_form_entry(gloss_lang: str, sense_data: dict[str, list[str]]) -> bool:
    for category in sense_data.get("categories", []):
        if gloss_lang == "zh" and category.endswith(ZH_FORMS_CAT_SUFFIXES):
            return True
        if gloss_lang == "fr" and category.startswith(FR_FORMS_CAT_PREFIXES):
            return True
    return False
