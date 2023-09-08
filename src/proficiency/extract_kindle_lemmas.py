import csv
import json
import re
import sqlite3
import sys
from itertools import product
from pathlib import Path

from .database import create_indexes_then_close, init_db
from .util import get_en_inflections


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
                    get_en_inflections(first_word, "VERB")
                )
            }
        else:
            return {lemma}
    elif "-" in lemma:  # A-bomb
        return {lemma}
    else:
        return {lemma}.union(get_en_inflections(lemma, pos))


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


def create_kindle_lemmas_db(db_path: Path) -> None:
    with open("en/kindle_enabled_lemmas.json", encoding="utf-8") as f:
        enabled_lemmas = json.load(f)
    enabled_sense_ids: set[int] = {data[1] for data in enabled_lemmas.values()}
    conn = init_db(db_path, "en", True, False)

    with open("en/kindle_all_lemmas.csv", newline="") as f:
        csv_reader = csv.reader(f)
        lemma_ids: dict[str, int] = {}
        for lemma, pos_type, sense_id_str, _ in csv_reader:
            sense_id = int(sense_id_str)
            enabled = 1 if sense_id in enabled_sense_ids else 0
            lemminflect_pos = kindle_to_lemminflect_pos(pos_type)
            difficulty = enabled_lemmas[lemma][0] if lemma in enabled_lemmas else 1
            en_data = (sense_id, enabled, pos_type, difficulty)
            insert_en_data(conn, lemma, en_data, lemminflect_pos, lemma_ids)

    create_indexes_then_close(conn)


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
        """
        INSERT INTO senses (id, enabled, pos, difficulty, lemma_id)
        VALUES(?, ?, ?, ?, ?)
        """,
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


def extract_kindle_lemmas(klld_path: str) -> None:
    conn = sqlite3.connect(klld_path)
    with open("en/kindle_all_lemmas.csv", "w", encoding="utf-8", newline="") as f:
        csv_writer = csv.writer(f)
        for data in conn.execute(
            """
            SELECT lemma, pos_types.label, senses.id, display_lemma_id
            FROM lemmas
            JOIN senses ON lemmas.id = display_lemma_id
            JOIN pos_types ON pos_types.id = senses.pos_type
            WHERE (full_def IS NOT NULL OR short_def IS NOT NULL)
            AND lemma NOT like '-%'
            ORDER BY lemma, pos_type, senses.id
            """
        ):
            csv_writer.writerow(data)


if __name__ == "__main__":
    extract_kindle_lemmas(sys.argv[1])
