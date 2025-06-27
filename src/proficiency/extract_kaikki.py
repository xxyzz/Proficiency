import json
import re
import sqlite3
import subprocess
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from shutil import which
from typing import Any

from .database import create_indexes_then_close, init_db, wiktionary_db_path
from .languages import KAIKKI_TRANSLATED_GLOSS_LANGS, WSD_LANGS
from .util import (
    freq_to_difficulty,
    get_short_def,
    get_shortest_lemma_length,
    load_difficulty_data,
)

FILTER_SENSE_TAGS = frozenset(
    {
        "alternative",
        "obsolete",
        "abbreviation",
        "initialism",
        "form-of",
        "misspelling",
        "alt-of",
    }
)
FILTER_EN_FORM_TAGS = frozenset(
    ["table-tags", "auxiliary", "class", "inflection-template", "obsolete"]
)
USED_POS_TYPES = frozenset(["adj", "adv", "noun", "phrase", "proverb", "verb"])
# tatuylonen/wiktextract#1263
FILTER_EN_EXAMPLE_PREFIXES = (
    "Active-voice counterpart:",
    "Coordinate term:",
    "Alternative forms:",
    "Comeronyms:",
    "Holonym:",
    "Imperfective:",
    "See synonyms at",
    "Meronym:",
    "Near-synonym:",
    "Perfective:",
    "Troponym:",
)
FILTER_EN_CAT_SUFFIXES = (" obsolete terms",)


@dataclass
class Example:
    text: str = ""
    offsets: str = ""


@dataclass
class Sense:
    enabled: bool = False
    short_gloss: str = ""
    gloss: str = ""
    short_example: str = ""
    examples: list[Example] = field(default_factory=list)


def download_kaikki_json(lemma_lang: str, gloss_lang: str) -> None:
    from .split_jsonl import split_kaikki_jsonl

    url = "https://kaikki.org/"
    if gloss_lang == "en" or (
        gloss_lang in KAIKKI_TRANSLATED_GLOSS_LANGS and lemma_lang == "en"
    ):
        url += "dictionary/"
    else:
        url += f"{gloss_lang}wiktionary/"
    url += "raw-wiktextract-data.jsonl.gz"

    gz_path = Path(f"build/{gloss_lang}.jsonl.gz")
    if not gz_path.exists():
        gz_path.parent.mkdir(exist_ok=True)
        subprocess.run(
            ["wget", "-nv", "-O", str(gz_path), url],
            check=True,
            capture_output=True,
            text=True,
        )
    if gz_path.exists():
        if which("pigz") is None and which("gzip") is None:
            import gzip

            with gzip.open(gz_path, "rb") as gz_f:
                split_kaikki_jsonl(gz_f, lemma_lang, gloss_lang)
        else:
            command_args = ["pigz" if which("pigz") is not None else "gzip", "-d", "-c"]
            command_args.append(str(gz_path))
            sub_p = subprocess.Popen(command_args, stdout=subprocess.PIPE)
            if sub_p.stdout is not None:
                with sub_p.stdout as f:
                    split_kaikki_jsonl(f, lemma_lang, gloss_lang)
            sub_p.wait()


def load_data(lemma_lang: str, gloss_lang: str) -> tuple[Path, dict[str, int]]:
    kaikki_json_path = Path(f"build/{lemma_lang}/{lemma_lang}_{gloss_lang}.jsonl")
    if gloss_lang in KAIKKI_TRANSLATED_GLOSS_LANGS:
        kaikki_json_path = Path(f"build/{lemma_lang}/{lemma_lang}_{lemma_lang}.jsonl")

    difficulty_data = load_difficulty_data(lemma_lang)
    return kaikki_json_path, difficulty_data


def create_lemmas_db_from_kaikki(lemma_lang: str, gloss_lang: str) -> list[Path]:
    kaikki_json_path, difficulty_data = load_data(lemma_lang, gloss_lang)

    db_path = wiktionary_db_path(lemma_lang, gloss_lang)
    conn = init_db(db_path)
    if gloss_lang == "zh":
        zh_cn_db_path = wiktionary_db_path(lemma_lang, "zh_cn")
        zh_cn_conn = init_db(zh_cn_db_path)

    len_limit = get_shortest_lemma_length(lemma_lang)
    if lemma_lang == "zh" or gloss_lang == "zh":
        import opencc

        converter = opencc.OpenCC("t2s.json")

    last_word = ""
    form_group_ids: dict[str, int] = {}
    sound_ids: dict[str, int] = {}
    with open(kaikki_json_path, encoding="utf-8") as f:
        for line in f:
            data = json.loads(line)
            word = data.get("word", "")
            pos = data.get("pos", "")
            if (
                pos not in USED_POS_TYPES
                or len(word) < len_limit
                or re.match(r"\W|\d", word)
                or (
                    gloss_lang in KAIKKI_TRANSLATED_GLOSS_LANGS
                    and len(data.get("translations", [])) == 0
                )
                or (
                    gloss_lang == "en"
                    and any(
                        cat.endswith(FILTER_EN_CAT_SUFFIXES)
                        for cat in data.get("categories", [])
                    )
                )
            ):
                continue
            if last_word != word:
                form_group_ids.clear()
                sound_ids.clear()

            enabled = True
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

            forms = get_forms(
                word, lemma_lang, gloss_lang, data.get("forms", []), pos, len_limit
            )
            if lemma_lang == "zh":
                simplified_form = converter.convert(word)
                if simplified_form != word:
                    forms.add(simplified_form)

            sense_data = (
                get_translated_senses(gloss_lang, data, enabled)
                if gloss_lang in KAIKKI_TRANSLATED_GLOSS_LANGS
                else get_senses(lemma_lang, gloss_lang, data, enabled)
            )
            if len(sense_data) > 0:
                ipas = get_ipas(lemma_lang, data.get("sounds", []))
                form_group_id = insert_forms(
                    [conn, zh_cn_conn] if gloss_lang == "zh" else [conn],
                    forms,
                    form_group_ids,
                )
                sound_id = insert_sound(
                    [conn, zh_cn_conn] if gloss_lang == "zh" else [conn],
                    ipas,
                    sound_ids,
                )
                insert_senses(
                    conn, sense_data, word, pos, difficulty, sound_id, form_group_id
                )
                if gloss_lang == "zh":
                    zh_cn_senses = [
                        Sense(
                            enabled=sense.enabled,
                            short_gloss=converter.convert(sense.short_gloss),
                            gloss=converter.convert(sense.gloss),
                            short_example=converter.convert(sense.short_example),
                        )
                        for sense in sense_data
                    ]
                    insert_senses(
                        zh_cn_conn,
                        zh_cn_senses,
                        word,
                        pos,
                        difficulty,
                        sound_id,
                        form_group_id,
                    )
                last_word = word

    create_indexes_then_close(conn, lemma_lang, close=False)
    save_wsd_db(db_path, conn, lemma_lang, gloss_lang)
    if gloss_lang == "zh":
        create_indexes_then_close(zh_cn_conn, "", close=False)
        save_wsd_db(zh_cn_db_path, zh_cn_conn, lemma_lang, gloss_lang)
    kaikki_json_path.unlink()
    return [db_path, zh_cn_db_path] if gloss_lang == "zh" else [db_path]


def insert_forms(
    conn_list: list[sqlite3.Connection], forms: set[str], form_group_ids: dict[str, int]
) -> int | None:
    if len(forms) == 0:
        return None
    form_key = "_".join(sorted(forms))
    if form_key in form_group_ids:
        return form_group_ids[form_key]
    form_group_id = 0
    for conn in conn_list:
        for (form_group_id,) in conn.execute(
            "INSERT INTO form_groups VALUES (NULL) RETURNING id"
        ):
            conn.executemany(
                "INSERT OR IGNORE INTO forms (form, form_group_id) VALUES(?, ?)",
                ((form, form_group_id) for form in forms),
            )
            form_group_ids[form_key] = form_group_id
    return form_group_id


def insert_senses(
    conn: sqlite3.Connection,
    senses: list[Sense],
    lemma: str,
    pos: str,
    difficulty: int,
    sound_id: int | None,
    form_group_id: int | None,
) -> None:
    for sense in senses:
        for (sense_id,) in conn.execute(
            """
                INSERT INTO senses
                (enabled, short_def, full_def, example, lemma, pos,
                difficulty, sound_id, form_group_id)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING id
                """,
            (
                sense.enabled,
                sense.short_gloss,
                sense.gloss,
                sense.short_example,
                lemma,
                pos,
                difficulty,
                sound_id,
                form_group_id,
            ),
        ):
            insert_examples(conn, sense, sense_id)


def insert_examples(conn: sqlite3.Connection, sense: Sense, sense_id: int) -> None:
    conn.executemany(
        "INSERT INTO examples (sense_id, text, offsets) VALUES(?, ?, ?)",
        (
            (sense_id, example.text, example.offsets)
            for example in sense.examples
            if example.offsets != ""
        ),
    )


def insert_sound(
    conn_list: list[sqlite3.Connection],
    sound_data: dict[str, str],
    sound_ids: dict[str, int],
) -> int | None:
    sound_key = "_".join(sound_data.values())
    if sound_key == "":
        return None
    elif sound_key in sound_ids:
        return sound_ids[sound_key]

    sound_id = 0
    for conn in conn_list:
        for (sound_id,) in conn.execute(
            """
            INSERT INTO sounds
            (ipa, ga_ipa, rp_ipa, pinyin, bopomofo)
            VALUES (?, ?, ?, ?, ?)
            RETURNING id
            """,
            tuple(
                sound_data.get(key, "")
                for key in ["ipa", "ga_ipa", "rp_ipa", "pinyin", "bopomofo"]
            ),
        ):
            sound_ids[sound_key] = sound_id
    return sound_id


def get_ipas(lang: str, sounds: list[dict[str, Any]]) -> dict[str, str]:
    ipas = {}
    if lang == "en":
        for sound in sounds:
            ipa = sound.get("ipa", "")
            if ipa == "":
                continue
            tags: list[str] = sound.get("tags", [])
            if len(tags) == 0:
                return {"ipa": ipa}
            if ("US" in tags or "General-American" in tags) and "ga_ipa" not in ipas:
                ipas["ga_ipa"] = ipa
            if (
                "UK" in tags or "Received-Pronunciation" in tags
            ) and "rp_ipa" not in ipas:
                ipas["rp_ipa"] = ipa
    elif lang == "zh":
        for sound in sounds:
            pron = sound.get("zh-pron", "")
            if pron == "":
                continue
            lower_tags: list[str] = [t.lower() for t in sound.get("tags", [])]
            if len(lower_tags) == 0:
                return {"ipa": pron}
            if "mandarin" in lower_tags:
                if "pinyin" in lower_tags and "pinyin" not in lower_tags:
                    ipas["pinyin"] = pron
                elif (
                    "bopomofo" in lower_tags or "zhuyin" in lower_tags
                ) and "bopomofo" not in ipas:
                    ipas["bopomofo"] = pron
    else:
        for sound in sounds:
            ipa = sound.get("ipa", "")
            if ipa != "":
                ipas["ipa"] = ipa
                break

    return ipas


# https://lemminflect.readthedocs.io/en/latest/tags/
LEMMINFLECT_POS_TAGS = {
    "adj": "ADJ",
    "adv": "ADV",
    "noun": "NOUN",
    "name": "PROPN",
    "verb": "VERB",
}


def czech_adjective_to_adverb(word: str) -> str | None:
    if word.endswith("lý") or word.endswith("sý"):
        return word[:-1] + "e"
    elif word.endswith("rý"):
        return word[:-2] + "ře"
    elif word.endswith("cí"):
        return word[:-1] + "e"
    elif word.endswith("í"):
        return word[:-1] + "ě"
    elif word.endswith("chý"):
        return word[:-3] + "še"
    elif word.endswith("cký") or word.endswith("ský"):
        return word[:-2] + "ky"
    elif word.endswith("hý"):
        return word[:-2] + "ze"
    elif word.endswith("ký"):
        return word[:-2] + "ce"
    elif word.endswith("ý"):
        return word[:-1] + "ě"
    else:
        return None


def get_czech_derived_adverb_forms(adj: str) -> set[str]:
    adverb = czech_adjective_to_adverb(adj)
    if adverb is None:
        return set()
    else:
        derived_base_forms = {adverb}
        if not adverb.startswith("ne"):  # Negated form
            derived_base_forms.add("ne" + adverb)
        final_derived_forms: set[str] = set()
        for adv in derived_base_forms:  # Comparative and superlative forms
            if adv.endswith("ě") or adv.endswith("e"):
                final_derived_forms.add(adv + "ji")
                final_derived_forms.add("nej" + adv + "ji")
        final_derived_forms |= derived_base_forms
        return final_derived_forms


def get_forms(
    word: str,
    lemma_lang: str,
    gloss_lang: str,
    forms_data: list[dict[str, Any]],
    pos: str,
    len_limit: int,
) -> set[str]:
    from wiktextract_lemmatization.utils import remove_accents

    forms: set[str] = set()
    for form in forms_data:
        form_str = form.get("form", "")
        if form_str in ["", word] or len(form_str) < len_limit:
            continue
        if gloss_lang == "en" and any(
            tag in FILTER_EN_FORM_TAGS for tag in form.get("tags", [])
        ):
            continue
        forms.add(form_str)

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
            forms |= get_czech_derived_adverb_forms(word)

    if lemma_lang in ["ru", "uk"]:  # Russian, Ukrainian
        forms |= {remove_accents(form) for form in forms}
    return forms


def get_translated_senses(
    gloss_lang: str, word_data: dict[str, Any], enabled: bool
) -> list[Sense]:
    # group translated word by sense
    translations = defaultdict(list)
    words = set()
    for translation in word_data.get("translations", []):
        if (
            translation.get("code", translation.get("lang_code")) == gloss_lang
            and len(translation.get("word", "")) > 0
        ):
            word = translation.get("word")
            if word in words:
                continue
            words.add(word)
            sense = translation.get("sense", "")
            translations[sense].append(word)

    return [
        Sense(
            enabled=index == 0 and enabled,
            short_gloss=min(words, key=len),
            gloss=", ".join(words),
        )
        for index, words in enumerate(translations.values())
    ]


def get_senses(
    lemma_lang: str, gloss_lang: str, word_data: dict[str, Any], enabled: bool
) -> list[Sense]:
    senses = []
    first_glosses: dict[str, Sense] = {}
    for sense in word_data.get("senses", []):
        examples = sense.get("examples", [])
        glosses = sense.get("glosses", [])
        if len(glosses) == 0:
            continue
        elif len(glosses) > 1 and glosses[0] in first_glosses:
            parent_sense = first_glosses[glosses[0]]
            short_example, e_with_offsets = get_examples(examples, gloss_lang)
            if short_example != "" and len(short_example) < len(
                parent_sense.short_example
            ):
                parent_sense.short_example = short_example
            parent_sense.examples.extend(e_with_offsets)
            continue
        gloss = glosses[0]
        if gloss == "":
            continue
        tags = set(sense.get("tags", []))
        if len(tags.intersection(FILTER_SENSE_TAGS)) > 0:
            continue
        short_gloss = get_short_def(gloss, gloss_lang)
        if len(short_gloss) == 0:
            short_gloss = gloss
        short_example, e_with_offsets = get_examples(examples, gloss_lang)
        sense = Sense(
            enabled=enabled,
            short_gloss=short_gloss,
            gloss=gloss,
            short_example=short_example,
            examples=e_with_offsets,
        )
        senses.append(sense)
        first_glosses[gloss] = sense

    return senses


def get_examples(examples: dict, gloss_lang: str) -> tuple[str, list[Example]]:
    short_example = ""
    e_with_offsets = []
    for example in examples:
        example_text = example.get("text", "")
        # en Template:...
        if example_text in ["", "[…"] or (
            gloss_lang == "en" and example_text.startswith(FILTER_EN_EXAMPLE_PREFIXES)
        ):
            continue
        if short_example == "" or len(example_text) < len(short_example):
            short_example = example_text
        offsets = example.get(
            "bold_text_offsets",
            example.get("italic_text_offsets", ""),
        )
        if offsets != "":
            e_with_offsets.append(
                Example(text=example_text, offsets=json.dumps(offsets))
            )
    return short_example, e_with_offsets


def save_wsd_db(
    db_path: Path, conn: sqlite3.Connection, lemma_lang: str, gloss_lang: str
) -> None:
    if f"{lemma_lang}-{gloss_lang}" in WSD_LANGS:
        split_stem = db_path.stem.rsplit("_", maxsplit=1)
        new_stem = f"{split_stem[0]}_wsd_{split_stem[1]}"
        wsd_path = db_path.with_stem(new_stem)
        wsd_conn = sqlite3.connect(wsd_path)
        with wsd_conn:
            conn.backup(wsd_conn)
            wsd_conn.execute("CREATE INDEX idx_examples ON examples (sense_id)")
        wsd_conn.close()
        subprocess.run(
            ["zstd", "-z", "-19", str(wsd_path)],
            check=True,
            capture_output=True,
            text=True,
        )

    conn.execute("DROP TABLE examples")
    conn.commit()
    conn.close()
