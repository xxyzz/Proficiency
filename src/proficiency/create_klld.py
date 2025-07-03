import base64
import sqlite3
from datetime import date
from pathlib import Path

from .util import remove_full_stop


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


def copy_data_from_wiktionary_db(
    klld_path: Path, wiktionary_path: Path, gloss_lang: str, lemma_lang: str
) -> None:
    if klld_path.exists():
        klld_path.unlink()
    klld_conn = sqlite3.connect(klld_path)
    wiktionary_conn = sqlite3.connect(wiktionary_path)
    create_klld_tables(klld_conn, lemma_lang, gloss_lang)

    lemma_ids = {}
    for (lemma,) in wiktionary_conn.execute("SELECT lemma FROM senses"):
        if lemma in lemma_ids:
            continue
        for (lemma_id,) in klld_conn.execute(
            "INSERT INTO lemmas (lemma) VALUES(?) RETURNING id", (lemma,)
        ):
            lemma_ids[lemma] = lemma_id

    for lemma, pos, short_def, full_def, example in wiktionary_conn.execute(
        "SELECT lemma, pos, short_def, full_def, example FROM senses"
    ):
        if gloss_lang == "he":
            short_def = remove_rtl_pdi(short_def)
            full_def = remove_rtl_pdi(full_def)
        lemma_id = lemma_ids[lemma]
        klld_conn.execute(
            """
            INSERT INTO senses
            (display_lemma_id, term_id, term_lemma_id, pos_type, source_id,
            sense_number, corpus_count , short_def, full_def, example_sentence)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
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
                if example is not None and len(example) > 0
                else None,
            ),
        )

    klld_conn.executescript(
        """
        CREATE INDEX senses_synset_id_index ON senses(synset_id);
        CREATE INDEX senses_term_lemma_id_index ON senses(term_lemma_id);
        PRAGMA optimize;
        """
    )
    klld_conn.commit()
    klld_conn.close()
    wiktionary_conn.close()


def create_klld_db(gloss_lang: str, lemma_lang: str) -> Path:
    from .database import wiktionary_db_path

    klld_path = Path(f"build/{lemma_lang}/{get_klld_filename(lemma_lang, gloss_lang)}")
    copy_data_from_wiktionary_db(
        klld_path, wiktionary_db_path(lemma_lang, gloss_lang), gloss_lang, lemma_lang
    )
    return klld_path


def remove_rtl_pdi(text: str) -> str:
    # https://en.wikipedia.org/wiki/Bidirectional_text
    return text.replace("\u2067", "").replace("\u2069", "")


def get_klld_filename(lemma_lang: str, gloss_lang: str) -> str:
    from .main import MAJOR_VERSION

    return f"kll.{lemma_lang}.{gloss_lang}_v{MAJOR_VERSION}.klld"


def main():
    import sys

    from .main import archive_files

    wiktionary_path = Path(sys.argv[1])
    _, lemma_lang, gloss_lang, _ = wiktionary_path.stem.split("_", maxsplit=3)
    klld_path = wiktionary_path.with_name(get_klld_filename(lemma_lang, gloss_lang))
    klld_path = klld_path.with_stem(klld_path.stem + "_wsd")
    copy_data_from_wiktionary_db(klld_path, wiktionary_path, gloss_lang, lemma_lang)
    archive_files([wiktionary_path, klld_path], Path())
