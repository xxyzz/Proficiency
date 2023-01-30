import csv
import json
import re
import sqlite3
import sys
from itertools import chain, product
from pathlib import Path


def kindle_to_lemminflect_pos(pos: str) -> str | None:
    # https://lemminflect.readthedocs.io/en/latest/tags
    match pos:
        case "noun":
            return "NOUN"
        case "verb":
            return "VERB"
        case "adjective":
            return "ADJ"
        case "adverb":
            return "ADV"
        case "pronoun":
            return "PROPN"
        case _:
            return None


def get_inflections(lemma: str, pos: str | None) -> set[str]:
    from lemminflect import getAllInflections, getAllInflectionsOOV

    inflections = set(chain(*getAllInflections(lemma, pos).values()))
    if not inflections and pos:
        inflections = set(chain(*getAllInflectionsOOV(lemma, pos).values()))
    return inflections


def get_en_lemma_forms(lemma: str, pos: str | None) -> set[str]:
    if " " in lemma:
        if "/" in lemma:  # "be/get togged up/out"
            words = [word.split("/") for word in lemma.split()]
            forms: set[str] = set()
            for phrase in map(" ".join, product(*words)):
                forms |= get_en_lemma_forms(phrase, pos)
            return forms
        elif pos == "VERB":
            # inflect the first word of the phrase verb
            first_word, rest_words = lemma.split(maxsplit=1)
            return {
                f"{inflection} {rest_words}"
                for inflection in {first_word}.union(
                    get_inflections(first_word, "VERB")
                )
            }
        else:
            return {lemma}
    elif "-" in lemma:  # A-bomb
        return {lemma}
    else:
        return {lemma}.union(get_inflections(lemma, pos))


def transform_lemma(lemma: str) -> set[str]:
    if "(" in lemma:
        return transform_lemma(re.sub(r"[()]", "", lemma)) | transform_lemma(
            " ".join(re.sub(r"\([^)]+\)", "", lemma).split())
        )
    elif "/" in lemma:
        words = [word.split("/") for word in lemma.split()]
        return set(map(" ".join, product(*words)))
    else:
        return {lemma}


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


def create_kindle_lemmas_db(lemma_lang: str, klld_path: Path, db_path: Path) -> None:
    is_cjk = lemma_lang in ["zh", "ja", "ko"]
    with open("en/kindle_enabled_lemmas.json", encoding="utf-8") as f:
        enabled_lemmas = json.load(f)
    enabled_sense_ids: set[int] = {data[1] for data in enabled_lemmas.values()}
    if lemma_lang != "en":
        with open(f"{lemma_lang}/translations.json", encoding="utf-8") as f:
            translations = json.load(f)

        difficulty_json_path = Path(f"{lemma_lang}/difficulty.json")
        if difficulty_json_path.exists():
            with difficulty_json_path.open(encoding="utf-8") as f:
                difficulty_data = json.load(f)

    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.Connection(db_path)
    if lemma_lang == "en":
        conn.execute(
            "CREATE TABLE lemmas (sense_id INTEGER PRIMARY KEY, enabled INTEGER, lemma TEXT, pos_type TEXT, short_def TEXT DEFAULT '', full_def TEXT DEFAULT '', difficulty INTEGER, example TEXT DEFAULT '', forms TEXT)"
        )
    else:
        conn.execute(
            "CREATE TABLE lemmas (sense_id INTEGER PRIMARY KEY, enabled INTEGER, lemma TEXT, pos_type TEXT, short_def TEXT DEFAULT '', full_def TEXT DEFAULT '', difficulty INTEGER, example TEXT DEFAULT '', forms TEXT DEFAULT '', display_lemma_id INTEGER)"
        )

    with open("en/kindle_all_lemmas.csv", newline="") as f:
        csv_reader = csv.reader(f)
        for lemma, pos_type, sense_id_str, display_lemma_id_str in csv_reader:
            lemminflect_pos = kindle_to_lemminflect_pos(pos_type)
            sense_id = int(sense_id_str)
            display_lemma_id = int(display_lemma_id_str)
            enabled = 1 if sense_id in enabled_sense_ids else 0

            if lemma_lang == "en":
                difficulty = enabled_lemmas[lemma][0] if lemma in enabled_lemmas else 1
                data = (sense_id, enabled, lemma, pos_type, difficulty)
                if "(" in lemma:  # "(as) good as new"
                    forms_with_words_in_parentheses = get_en_lemma_forms(
                        re.sub(r"[()]", "", lemma), lemminflect_pos
                    )
                    forms_without_words_in_parentheses = get_en_lemma_forms(
                        " ".join(re.sub(r"\([^)]+\)", "", lemma).split()),
                        lemminflect_pos,
                    )
                    conn.execute(
                        "INSERT INTO lemmas (sense_id, enabled, lemma, pos_type, difficulty, forms) VALUES(?, ?, ?, ?, ?, ?)",
                        data
                        + (
                            ",".join(
                                forms_with_words_in_parentheses
                                | forms_without_words_in_parentheses
                            ),
                        ),
                    )
                else:
                    conn.execute(
                        "INSERT INTO lemmas (sense_id, enabled, lemma, pos_type, difficulty, forms) VALUES(?, ?, ?, ?, ?, ?)",
                        data + (",".join(get_en_lemma_forms(lemma, lemminflect_pos)),),
                    )
            else:
                tr_forms = translations.get(f"{lemma}_{pos_type}")
                if tr_forms is None and ("(" in lemma or "/" in lemma):
                    for form in transform_lemma(lemma):
                        for check_pos in [pos_type, "other"]:
                            if f"{form}_{check_pos}" in translations:
                                tr_forms = translations.get(f"{form}_{check_pos}")
                                break
                if tr_forms is None and pos_type != "other":
                    tr_forms = translations.get(f"{lemma}_other")
                if tr_forms is not None:
                    unused_indexes = list(range(len(tr_forms)))
                    for index in range(len(tr_forms)):
                        for ignore in conn.execute(
                            "SELECT * FROM lemmas WHERE lemma = ? AND pos_type = ? AND display_lemma_id = ? LIMIT 1",
                            (tr_forms[index][0], pos_type, display_lemma_id),
                        ):
                            unused_indexes.remove(index)
                    unused_index = unused_indexes[0] if len(unused_indexes) > 0 else 0
                    tr_lemma, *forms = tr_forms[unused_index]
                    difficulty = (
                        difficulty_data.get(tr_lemma, 1)
                        if difficulty_json_path.exists()
                        else freq_to_difficulty(tr_lemma, lemma_lang)
                    )
                    conn.execute(
                        "INSERT INTO lemmas (sense_id, enabled, lemma, pos_type, difficulty, forms, display_lemma_id) VALUES(?, ?, ?, ?, ?, ?, ?)",
                        (
                            sense_id,
                            enabled,
                            tr_lemma,
                            pos_type,
                            difficulty,
                            ",".join(forms),
                            display_lemma_id,
                        ),
                    )
                else:
                    conn.execute(
                        "INSERT INTO lemmas (sense_id, enabled, lemma, pos_type, difficulty, display_lemma_id) VALUES(?, ?, ?, ?, ?, ?)",
                        (
                            sense_id,
                            enabled,
                            lemma,
                            pos_type,
                            1,
                            display_lemma_id,
                        ),
                    )

    conn.execute(
        "CREATE INDEX idx_lemmas ON lemmas (lemma, pos_type)"
        if lemma_lang != "zh"
        else "CREATE INDEX idx_lemmas ON lemmas (lemma, pos_type, forms)"
    )
    conn.commit()
    conn.close()


def extract_kindle_lemmas(klld_path: str) -> None:
    conn = sqlite3.connect(klld_path)
    with open("kindle_all_lemmas.csv", "w", encoding="utf-8", newline="") as f:
        csv_writer = csv.writer(f)
        for data in conn.execute(
            "SELECT lemma, pos_types.label, senses.id, display_lemma_id FROM lemmas JOIN senses ON lemmas.id = display_lemma_id JOIN pos_types ON pos_types.id = senses.pos_type WHERE (full_def IS NOT NULL OR short_def IS NOT NULL) AND lemma NOT like '-%' ORDER BY lemma, pos_type, senses.id"
        ):
            csv_writer.writerow(data)


if __name__ == "__main__":
    extract_kindle_lemmas(sys.argv[1])
