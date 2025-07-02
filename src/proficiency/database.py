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

    CREATE TABLE sounds (
    id INTEGER PRIMARY KEY,
    ipa TEXT DEFAULT '',
    ga_ipa TEXT DEFAULT '',
    rp_ipa TEXT DEFAULT '',
    pinyin TEXT DEFAULT '',
    bopomofo TEXT DEFAULT '');

    CREATE TABLE form_groups (id INTEGER PRIMARY KEY);

    CREATE TABLE forms (
    form TEXT COLLATE NOCASE, form_group_id INTEGER REFERENCES form_groups(id),
    PRIMARY KEY(form, form_group_id));

    CREATE TABLE senses (
    id INTEGER PRIMARY KEY,
    enabled INTEGER,
    lemma TEXT COLLATE NOCASE,
    pos TEXT,
    short_def TEXT DEFAULT '',
    full_def TEXT DEFAULT '',
    example TEXT DEFAULT '',
    difficulty INTEGER,
    sound_id INTEGER REFERENCES sounds(id),
    embed_vector TEXT DEFAULT '',
    form_group_id INTEGER REFERENCES form_groups(id));

    CREATE TABLE examples (
    text TEXT, offsets TEXT, sense_id INTEGER REFERENCES senses(id));
    """)
    return conn


def create_indexes_then_close(
    conn: sqlite3.Connection, lemma_lang: str, close: bool = True
) -> None:
    create_indexes_sql = """
    CREATE INDEX idx_senses ON senses (lemma, pos);
    CREATE INDEX idx_senses_forms ON senses (form_group_id);
    PRAGMA optimize;
    """
    conn.executescript(create_indexes_sql)
    if lemma_lang != "":
        for (lemma_num,) in conn.execute("SELECT count(DISTINCT lemma) FROM senses"):
            print(f"{lemma_lang}: {lemma_num}")
    conn.commit()
    if close:
        conn.close()
