import base64
import sqlite3
from datetime import date
from pathlib import Path

from util import remove_full_stop


def kaikki_to_kindle_pos_id(pos: str) -> int:
    match pos:
        case "adj":
            return 1
        case "adv":
            return 3
        case "noun":
            return 0
        case "verb":
            return 1
        case _:
            return 7  # other


def create_klld_tables(
    conn: sqlite3.Connection, lemma_lang: str, gloss_lang: str
) -> None:
    conn.executescript(
        """
    CREATE TABLE `pos_types` (
    `id` integer NOT NULL DEFAULT '0',
    `label` varchar(100) DEFAULT NULL,
    PRIMARY KEY (`id`)
    );

    CREATE TABLE `sources` (
    `id` integer NOT NULL DEFAULT '0',
    `label` varchar(200) DEFAULT NULL,
    PRIMARY KEY (`id`)
    );

    CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT);
    CREATE TABLE lemmas (id INTEGER PRIMARY KEY, lemma TEXT);

    CREATE TABLE senses (
    id INTEGER PRIMARY KEY,
    display_lemma_id INTEGER,
    term_id INTEGER,
    term_lemma_id INTEGER,
    pos_type INTEGER,
    source_id INTEGER,
    sense_number REAL,
    synset_id INTEGER,
    corpus_count INTEGER,
    full_def TEXT,
    short_def TEXT,
    example_sentence TEXT);
    """
    )

    pos_types = [
        "noun",
        "verb",
        "adjective",
        "adverb",
        "article",
        "number",
        "conjunction",
        "other",
        "preposition",
        "pronoun",
        "particle",
        "punctuation",
    ]
    conn.executemany("INSERT INTO pos_types VALUES(?, ?)", enumerate(pos_types))

    sources = [None, "Merriam-Webster", None, "Wiktionary", None, None]
    conn.executemany("INSERT INTO sources VALUES(?, ?)", enumerate(sources))

    metadata = {
        "maxTermLength": "3",
        "termTerminatorList": ",    ;       .       \"       '       !       ?",
        "definitionLanguage": gloss_lang,
        "id": "kll.en.zh",
        "lemmaLanguage": lemma_lang,
        "version": date.today().isoformat(),
        "revision": "57",
        "tokenSeparator": None,
        "encoding": "1",
    }
    conn.executemany("INSERT INTO metadata VALUES(?, ?)", metadata.items())


def create_klld_db(
    wiktionary_db_path: Path, klld_path: Path, lemma_lang: str, gloss_lang: str
) -> None:
    if klld_path.exists():
        klld_path.unlink()

    klld_conn = sqlite3.connect(klld_path)
    wiktionary_conn = sqlite3.connect(wiktionary_db_path)
    create_klld_tables(klld_conn, lemma_lang, gloss_lang)

    for data in wiktionary_conn.execute("SELECT id, lemma FROM lemmas"):
        klld_conn.execute("INSERT INTO lemmas VALUES(?, ?)", data)

    for (
        sense_id,
        lemma_id,
        pos,
        short_def,
        full_def,
        example,
    ) in wiktionary_conn.execute(
        "SELECT id, lemma_id, pos, short_def, full_def, example FROM senses"
    ):
        klld_conn.execute(
            "INSERT INTO senses (id, display_lemma_id, term_id, term_lemma_id, pos_type, source_id, sense_number, corpus_count , short_def, full_def, example_sentence) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                sense_id,
                lemma_id,
                lemma_id,
                lemma_id,
                kaikki_to_kindle_pos_id(pos),
                3,
                1.0,
                0,
                base64.b64encode(short_def.encode("utf-8")).decode("utf-8"),
                base64.b64encode(remove_full_stop(full_def).encode("utf-8")).decode(
                    "utf-8"
                ),
                base64.b64encode(remove_full_stop(example).encode("utf-8")).decode(
                    "utf-8"
                )
                if example is not None
                else None,
            ),
        )

    klld_conn.executescript(
        """
    CREATE INDEX senses_synset_id_index ON senses(synset_id);
    CREATE INDEX senses_term_lemma_id_index ON senses(term_lemma_id);
    """
    )
    klld_conn.commit()
    klld_conn.close()
    wiktionary_conn.close()
