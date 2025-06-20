import sqlite3
from pathlib import Path


def wiktionary_db_path(lemma_lang: str, gloss_lang: str) -> Path:
    from .main import MAJOR_VERSION

    return Path(
        f"build/{lemma_lang}/wiktionary_{lemma_lang}_{gloss_lang}_v{MAJOR_VERSION}.db"
    )


def init_db(db_path: Path) -> sqlite3.Connection:
    if not db_path.parent.is_dir():
        db_path.parent.mkdir()
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(db_path)
    conn.executescript("""
    PRAGMA foreign_keys = ON;

    CREATE TABLE lemmas (id INTEGER PRIMARY KEY, lemma TEXT COLLATE NOCASE);

    CREATE TABLE forms (
    form TEXT COLLATE NOCASE, pos TEXT, lemma_id INTEGER,
    PRIMARY KEY(form, pos, lemma_id),
    FOREIGN KEY(lemma_id) REFERENCES lemmas(id));

    CREATE TABLE sounds (
    id INTEGER PRIMARY KEY,
    ipa TEXT DEFAULT '',
    ga_ipa TEXT DEFAULT '',
    rp_ipa TEXT DEFAULT '',
    pinyin TEXT DEFAULT '',
    bopomofo TEXT DEFAULT '');

    CREATE TABLE senses (
    id INTEGER PRIMARY KEY,
    enabled INTEGER,
    lemma_id INTEGER,
    pos TEXT,
    short_def TEXT DEFAULT '',
    full_def TEXT DEFAULT '',
    example TEXT DEFAULT '',
    difficulty INTEGER,
    sound_id INTEGER,
    embed_vector TEXT DEFAULT '',
    FOREIGN KEY(lemma_id) REFERENCES lemmas(id),
    FOREIGN KEY(sound_id) REFERENCES sounds(id));

    CREATE TABLE examples (
    text TEXT, offsets TEXT, sense_id INTEGER,
    FOREIGN KEY(sense_id) REFERENCES senses(id));
    """)
    return conn


def create_indexes_then_close(
    conn: sqlite3.Connection, lemma_lang: str, close: bool = True
) -> None:
    create_indexes_sql = """
    CREATE INDEX idx_lemmas ON lemmas (lemma);
    CREATE INDEX idx_senses ON senses (lemma_id, pos, sound_id);
    """
    conn.executescript(create_indexes_sql)
    if lemma_lang != "":
        for (lemma_num,) in conn.execute("SELECT count(*) FROM lemmas"):
            print(f"{lemma_lang}: {lemma_num}")
    conn.commit()
    if close:
        conn.close()
