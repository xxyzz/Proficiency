import json
import re
import sqlite3
import subprocess
import tarfile
from collections import defaultdict
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.request import urlopen

from en.extract_kindle_lemmas import freq_to_difficulty, get_inflections
from en.translate import kaikki_to_kindle_pos

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


def download_kaikki_json(lang: str) -> Path:
    with open("kaikki_languages.json", encoding="utf-8") as f:
        kaikki_languages = json.load(f)

    filename_lang = re.sub(r"[\s-]", "", kaikki_languages[lang])
    filename = f"kaikki.org-dictionary-{filename_lang}.json"
    filepath = Path(f"{lang}/{filename}")
    if not filepath.exists():
        subprocess.run(
            [
                "wget",
                "-nv",
                "-P",
                lang,
                f"https://kaikki.org/dictionary/{kaikki_languages[lang]}/{filename}",
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


def load_data(lemma_lang: str, gloss_lang: str) -> tuple[Path, dict[str, int]]:
    if gloss_lang == "en":
        kaikki_json_path = download_kaikki_json(lemma_lang)
    else:
        kaikki_json_path = download_zh_json("sh" if lemma_lang == "hr" else lemma_lang)

    difficulty_data = {}
    if lemma_lang != "en":
        difficulty_json_path = Path(f"{lemma_lang}/difficulty.json")
        if difficulty_json_path.exists():
            with difficulty_json_path.open(encoding="utf-8") as f:
                difficulty_data = json.load(f)
    else:
        with open("en/kindle_enabled_lemmas.json", encoding="utf-8") as f:
            difficulty_data = {
                lemma: values[0] for lemma, values in json.load(f).items()
            }
    return kaikki_json_path, difficulty_data


def create_wiktionary_lemmas_db(
    lemma_lang: str, gloss_lang: str, major_version: str
) -> list[Path]:
    kaikki_json_path, difficulty_data = load_data(lemma_lang, gloss_lang)

    db_path = Path(
        f"{lemma_lang}/wiktionary_{lemma_lang}_{gloss_lang}_v{major_version}.db"
    )
    if not db_path.parent.is_dir():
        db_path.parent.mkdir()
    if db_path.exists():
        db_path.unlink()
    if lemma_lang == "en":
        create_table_sql = "CREATE TABLE lemmas (id INTEGER PRIMARY KEY, enabled INTEGER, lemma TEXT, pos_type TEXT, short_def TEXT, full_def TEXT, difficulty INTEGER, forms TEXT, example TEXT, ga_ipa TEXT, rp_ipa TEXT)"
    elif lemma_lang == "zh":
        create_table_sql = "CREATE TABLE lemmas (id INTEGER PRIMARY KEY, enabled INTEGER, lemma TEXT, pos_type TEXT, short_def TEXT, full_def TEXT, difficulty INTEGER, forms TEXT, example TEXT, pinyin TEXT, bopomofo TEXT)"
    else:
        create_table_sql = "CREATE TABLE lemmas (id INTEGER PRIMARY KEY, enabled INTEGER, lemma TEXT, pos_type TEXT, short_def TEXT, full_def TEXT, difficulty INTEGER, forms TEXT, example TEXT, ipa TEXT)"
    conn = sqlite3.connect(db_path)
    conn.execute(create_table_sql)
    if gloss_lang == "zh":
        zh_cn_db_path = Path(
            f"{lemma_lang}/wiktionary_{lemma_lang}_zh_cn_v{major_version}.db"
        )
        if zh_cn_db_path.exists():
            zh_cn_db_path.unlink()
        zh_cn_conn = sqlite3.connect(zh_cn_db_path)
        zh_cn_conn.execute(create_table_sql)

    enabled_words_pos = set()
    len_limit = 2 if lemma_lang in ["zh", "ja", "ko"] else 3
    if lemma_lang == "zh" or gloss_lang == "zh":
        import opencc

        converter = opencc.OpenCC("t2s.json")

    all_forms_data: dict[str, list[str]] | None = (
        defaultdict(list) if lemma_lang != "en" and gloss_lang == "en" else None
    )

    with open(kaikki_json_path, encoding="utf-8") as f:
        for line in f:
            data = json.loads(line)
            word = data.get("word")
            pos = data.get("pos")
            if (
                pos not in USED_POS_TYPES
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
            if all_forms_data is not None:
                all_forms_data[f"{word}_{kaikki_to_kindle_pos(pos)}"].extend(
                    list(forms)
                )

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
                short_gloss = short_def(gloss, gloss_lang)
                if not short_gloss:
                    continue
                ipas = get_ipas(lemma_lang, data.get("sounds", []))
                insert_lemma(
                    lemma_lang,
                    conn,
                    (
                        enabled,
                        word,
                        pos,
                        short_gloss,
                        gloss,
                        difficulty,
                        ",".join(forms),
                        example_sent,
                    ),
                    ipas,
                )
                if gloss_lang == "zh":
                    insert_lemma(
                        lemma_lang,
                        zh_cn_conn,
                        (
                            enabled,
                            word,
                            pos,
                            converter.convert(short_gloss),
                            converter.convert(gloss),
                            difficulty,
                            ",".join(forms),
                            converter.convert(example_sent) if example_sent else "",
                        ),
                        ipas,
                    )
                enabled = False

    lemma_index_sql = (
        "CREATE INDEX idx_lemmas ON lemmas (lemma, pos_type)"
        if lemma_lang != "zh"
        else "CREATE INDEX idx_lemmas ON lemmas (lemma, pos_type, forms)"
    )
    conn.execute(lemma_index_sql)
    conn.commit()
    conn.close()
    if gloss_lang == "zh":
        zh_cn_conn.execute(lemma_index_sql)
        zh_cn_conn.commit()
        zh_cn_conn.close()
    if all_forms_data is not None:
        with open(f"{lemma_lang}/forms.json", "w", encoding="utf-8") as f:
            json.dump(all_forms_data, f, ensure_ascii=False)
    return [db_path, zh_cn_db_path] if gloss_lang == "zh" else [db_path]


def insert_lemma(
    lemma_lang: str, conn: sqlite3.Connection, data: Any, ipas: dict[str, str] | str
) -> None:
    if lemma_lang == "en":
        ipas_data = (
            (ipas.get("ga_ipa", ""), ipas.get("rp_ipa", ""))
            if type(ipas) == dict
            else (ipas, "")
        )
        conn.execute(
            "INSERT INTO lemmas (enabled, lemma, pos_type, short_def, full_def, difficulty, forms, example, ga_ipa, rp_ipa) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            data + ipas_data,
        )
    elif lemma_lang == "zh":
        ipas_data = (
            (ipas.get("pinyin", ""), ipas.get("bopomofo", ""))
            if type(ipas) == dict
            else (ipas, "")
        )
        conn.execute(
            "INSERT INTO lemmas (enabled, lemma, pos_type, short_def, full_def, difficulty, forms, example, pinyin, bopomofo) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            data + ipas_data,
        )
    else:
        conn.execute(
            "INSERT INTO lemmas (enabled, lemma, pos_type, short_def, full_def, difficulty, forms, example, ipa) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)",
            data + (ipas,),
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
                elif "bopomofo" in tags and "bopomofo" not in ipas:
                    ipas["bopomofo"] = pron
    else:
        for sound in sounds:
            if "ipa" in sound:
                return sound["ipa"]

    return ipas if ipas else ""


def short_def(gloss: str, gloss_lang: str) -> str:
    gloss = gloss.removesuffix(".").removesuffix("。")
    gloss = re.sub(
        r"\([^)]+\)|（[^）]+）|〈[^〉]+〉|\[[^]]+\]|［[^］]+］|【[^】]+】|﹝[^﹞]+﹞|「[^」]+」",
        "",
        gloss,
    )
    gloss = min(re.split(";|；", gloss), key=len)
    gloss = min(gloss.split("/"), key=len)
    if gloss_lang == "zh":
        gloss = min(gloss.split("、"), key=len)
    return gloss.strip()


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
