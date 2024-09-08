import sqlite3
from pathlib import Path


def wiktionary_db_path(lemma_lang: str, gloss_lang: str) -> Path:
    from .main import MAJOR_VERSION

    return Path(
        f"build/{lemma_lang}/wiktionary_{lemma_lang}_{gloss_lang}_v{MAJOR_VERSION}.db"
    )


def init_db(
    db_path: Path, lemma_lang: str, for_kindle: bool, from_kaikki: bool
) -> sqlite3.Connection:
    if not db_path.parent.is_dir():
        db_path.parent.mkdir()
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    if for_kindle:
        create_lemmas_table_sql = (
            "CREATE TABLE lemmas (id INTEGER PRIMARY KEY, lemma TEXT COLLATE NOCASE)"
        )
    elif lemma_lang == "en" and from_kaikki:
        create_lemmas_table_sql = """
        CREATE TABLE lemmas
        (id INTEGER PRIMARY KEY, lemma TEXT COLLATE NOCASE, ga_ipa TEXT, rp_ipa TEXT)
        """
    elif lemma_lang == "zh" and from_kaikki:
        create_lemmas_table_sql = """
        CREATE TABLE lemmas
        (id INTEGER PRIMARY KEY, lemma TEXT COLLATE NOCASE, pinyin TEXT, bopomofo TEXT)
        """
    else:
        create_lemmas_table_sql = """
        CREATE TABLE lemmas
        (id INTEGER PRIMARY KEY, lemma TEXT COLLATE NOCASE, ipa TEXT)
        """

    conn.execute(create_lemmas_table_sql)
    create_other_tables_sql = """
    CREATE TABLE forms (form TEXT COLLATE NOCASE, pos TEXT, lemma_id INTEGER,
    PRIMARY KEY(form, pos, lemma_id), FOREIGN KEY(lemma_id) REFERENCES lemmas(id));

    CREATE TABLE senses (id INTEGER PRIMARY KEY, enabled INTEGER, lemma_id INTEGER,
    pos TEXT, short_def TEXT TEXT DEFAULT '', full_def TEXT TEXT DEFAULT '',
    example TEXT TEXT DEFAULT '', difficulty INTEGER,
    FOREIGN KEY(lemma_id) REFERENCES lemmas(id));
    """
    conn.executescript(create_other_tables_sql)
    return conn


def create_indexes_then_close(conn: sqlite3.Connection, lemma_lang: str) -> None:
    create_indexes_sql = """
    CREATE INDEX idx_lemmas ON lemmas (lemma);
    CREATE INDEX idx_senses ON senses (lemma_id, pos);
    """
    conn.executescript(create_indexes_sql)
    if lemma_lang != "":
        for (lemma_num,) in conn.execute("SELECT count(*) FROM lemmas"):
            print(f"{lemma_lang}: {lemma_num}")
    conn.commit()
    conn.close()
