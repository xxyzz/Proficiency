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
        else:
            difficulty_data = None

    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.Connection(db_path)
    conn.executescript(
        """
    PRAGMA foreign_keys = ON;
    CREATE TABLE lemmas (id INTEGER PRIMARY KEY, lemma TEXT COLLATE NOCASE);
    CREATE TABLE forms (form TEXT COLLATE NOCASE, pos TEXT, lemma_id INTEGER, PRIMARY KEY(form, pos, lemma_id), FOREIGN KEY(lemma_id) REFERENCES lemmas(id));
    CREATE TABLE senses (id INTEGER PRIMARY KEY, enabled INTEGER, lemma_id INTEGER, pos TEXT, short_def TEXT DEFAULT '', full_def TEXT DEFAULT '', example TEXT DEFAULT '', difficulty INTEGER, FOREIGN KEY(lemma_id) REFERENCES lemmas(id));
    """
    )

    with open("en/kindle_all_lemmas.csv", newline="") as f:
        csv_reader = csv.reader(f)
        lemma_ids: dict[str, int] = {}
        inserted_lemma_pos: set[str] = set()
        for lemma, pos_type, sense_id_str, display_lemma_id_str in csv_reader:
            sense_id = int(sense_id_str)

            if lemma_lang == "en":
                enabled = 1 if sense_id in enabled_sense_ids else 0
                lemminflect_pos = kindle_to_lemminflect_pos(pos_type)
                difficulty = enabled_lemmas[lemma][0] if lemma in enabled_lemmas else 1
                en_data = (sense_id, enabled, pos_type, difficulty)
                insert_en_data(conn, lemma, en_data, lemminflect_pos, lemma_ids)
            else:
                non_en_data = (
                    sense_id,
                    lemma,
                    pos_type,
                    int(display_lemma_id_str),
                    lemma_lang,
                )
                insert_non_en_data(
                    conn,
                    non_en_data,
                    translations,
                    difficulty_data,
                    inserted_lemma_pos,
                    lemma_ids,
                )

    conn.executescript(
        """
    CREATE INDEX idx_lemmas ON lemmas (lemma);
    CREATE INDEX idx_senses ON senses (lemma_id, pos);
    """
    )
    conn.commit()
    conn.close()


def insert_lemma(
    conn: sqlite3.Connection, lemma: str, lemma_ids: dict[str, int]
) -> int:
    if lemma in lemma_ids:
        return lemma_ids[lemma]

    lemma_id = 0
    for (new_lemma_id,) in conn.execute(
        "INSERT INTO lemmas (lemma) VALUES(?) RETURNING id", (lemma,)
    ):
        lemma_id = new_lemma_id
    return lemma_id


def insert_en_data(
    conn: sqlite3.Connection,
    lemma: str,
    data: tuple[int, int, str, int],
    lemminflect_pos: str | None,
    lemma_ids: dict[str, int],
) -> None:
    lemma_id = insert_lemma(conn, lemma, lemma_ids)
    conn.execute(
        "INSERT INTO senses (id, enabled, pos, difficulty, lemma_id) VALUES(?, ?, ?, ?, ?)",
        data + (lemma_id,),
    )
    pos = data[2]
    if "(" in lemma:  # "(as) good as new"
        forms_with_words_in_parentheses = get_en_lemma_forms(
            re.sub(r"[()]", "", lemma), lemminflect_pos
        )
        forms_without_words_in_parentheses = get_en_lemma_forms(
            " ".join(re.sub(r"\([^)]+\)", "", lemma).split()),
            lemminflect_pos,
        )
        conn.executemany(
            "INSERT OR IGNORE INTO forms VALUES(?, ?, ?)",
            (
                (form, pos, lemma_id)
                for form in forms_with_words_in_parentheses
                | forms_without_words_in_parentheses
            ),
        )
    else:
        conn.executemany(
            "INSERT OR IGNORE INTO forms VALUES(?, ?, ?)",
            (
                (form, pos, lemma_id)
                for form in get_en_lemma_forms(lemma, lemminflect_pos)
            ),
        )


def insert_non_en_data(
    conn: sqlite3.Connection,
    data: tuple[int, str, str, int, str],
    translations: dict[str, list[list[str]]],
    difficulty_data: dict[str, int],
    inserted_lemmas_pos: set[str],
    lemma_ids: dict[str, int],
) -> None:
    sense_id, lemma, pos, display_lemma_id, lemma_lang = data
    tr_forms = translations.get(f"{lemma}_{pos}")
    if tr_forms is None and ("(" in lemma or "/" in lemma):
        for form in transform_lemma(lemma):
            for check_pos in [pos, "other"]:
                if f"{form}_{check_pos}" in translations:
                    tr_forms = translations.get(f"{form}_{check_pos}")
                    break
    if tr_forms is None and pos != "other":
        tr_forms = translations.get(f"{lemma}_other")
    if tr_forms is not None:
        tr_forms_dict = {forms[0]: forms[1:] for forms in tr_forms}
        tr_lemma = tr_forms[0][0]
        for test_lemma in tr_forms_dict.keys():
            if f"{test_lemma}_{pos}_{display_lemma_id}" not in inserted_lemmas_pos:
                tr_lemma = test_lemma
                break
        lemma_id = insert_lemma(conn, tr_lemma, lemma_ids)
        difficulty = (
            difficulty_data.get(tr_lemma, 1)
            if difficulty_data is not None
            else freq_to_difficulty(tr_lemma, lemma_lang)
        )
        tr_lemma_pos_en_id = f"{tr_lemma}_{pos}_{display_lemma_id}"
        if (tr_lemma_pos_en_id in inserted_lemmas_pos) or (
            difficulty_data is not None and tr_lemma not in difficulty_data
        ):
            enabled = 0
        else:
            enabled = 1

        conn.executemany(
            "INSERT OR IGNORE INTO forms VALUES(?, ?, ?)",
            ((form, pos, lemma_id) for form in tr_forms_dict[tr_lemma]),
        )
        conn.execute(
            "INSERT INTO senses (id, enabled, lemma_id, pos, difficulty) VALUES(?, ?, ?, ?, ?)",
            (sense_id, enabled, lemma_id, pos, difficulty),
        )
        inserted_lemmas_pos.add(tr_lemma_pos_en_id)
    else:
        # No translation
        lemma_id = insert_lemma(conn, lemma, lemma_ids)
        conn.execute(
            "INSERT INTO senses (id, enabled, lemma_id, pos, difficulty) VALUES(?, ?, ?, ?, ?)",
            (sense_id, 0, lemma_id, pos, 1),
        )


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
