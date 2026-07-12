from pathlib import Path
from sqlite3 import Connection

X_RAY_EDITIONS = {
    "ca",
    "da",
    "de",
    "el",
    "en",
    "es",
    "fi",
    "fr",
    "hr",
    "it",
    "ja",
    "ko",
    "lt",
    "nb",
    "nl",
    "pl",
    "pt",
    "ro",
    "ru",
    "sl",
    "sv",
    "uk",
    "zh",
}


def download_title_sql_dump(url: str) -> Path:
    import gzip
    import shutil

    import requests

    from .main import VERSION, logger

    filename = url.rsplit("/", maxsplit=1)[-1]
    sql_gz_path = Path("build") / filename
    sql_path = sql_gz_path.with_name(sql_gz_path.stem)
    if not sql_path.exists() and not sql_gz_path.exists():
        logger.info(f"Downloading {filename}")
        r = requests.get(
            url,
            headers={
                "user-agent": f"Proficiency/{VERSION} (https://github.com/xxyzz/Proficiency)"
            },
            stream=True,
        )
        with sql_gz_path.open("wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        logger.info(f"{filename} downloaded")
    if not sql_path.exists():
        with gzip.open(sql_gz_path, "rb") as f_in, sql_path.open("wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
        sql_gz_path.unlink()
    return sql_path


def init_db(edition: str) -> tuple[Connection, Path]:
    import sqlite3

    from .main import MAJOR_VERSION

    db_path = Path(f"build/{edition}.wikipedia.org_v{MAJOR_VERSION}.db")
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(db_path)
    conn.execute("""
    CREATE TABLE pages (
    title TEXT PRIMARY KEY COLLATE NOCASE,
    description TEXT,
    wikidata_item TEXT,
    redirect_to TEXT,
    redirect_fragment TEXT,
    id INTEGER)
    """)
    return conn, db_path


def create_temp_index(conn: Connection):
    conn.executescript("""
    CREATE INDEX id_idx ON pages (id);
    PRAGMA optimize;
    """)
    conn.commit()


def drop_temp_index(conn: Connection):
    conn.executescript("""
    DROP INDEX id_idx;
    ALTER TABLE pages DROP COLUMN id;
    VACUUM;
    """)
    conn.commit()
    conn.close()


def parse_sql_line(line: str):
    import csv
    import io
    import re

    line = re.sub(r"^INSERT INTO `.+` VALUES \(", "", line)
    line = line.strip("(); \n").replace("),(", "\n")
    return csv.reader(
        io.StringIO(line),
        delimiter=",",
        quotechar="'",
        escapechar="\\",
        doublequote=False,
    )


def parse_page_sql(conn: Connection, input_path: Path):
    # https://www.mediawiki.org/wiki/Manual:Page_table
    from .main import logger

    with input_path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("INSERT INTO "):
                for row in parse_sql_line(line):
                    page_id, namespace, title, *_ = row
                    if namespace == "0":
                        # MediaWiki titles could be case insensitive
                        conn.execute(
                            "INSERT OR IGNORE INTO pages (title, id) VALUES(?, ?)",
                            (title.replace("_", " "), page_id),
                        )
    create_temp_index(conn)
    logger.info("page.sql done")


def parse_page_props_sql(conn: Connection, input_path: Path):
    # https://www.mediawiki.org/wiki/Manual:Page_props_table
    from .main import logger

    # ignore "UnicodeDecodeError" in glob type column
    with input_path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("INSERT INTO "):
                for row in parse_sql_line(line):
                    page_id, propname, value, *_ = row
                    if propname == "disambiguation":
                        conn.execute("DELETE FROM pages WHERE id = ?", (page_id,))
    conn.commit()
    logger.info("page_props.sql done")


def parse_redirect_sql(conn: Connection, input_path: Path):
    # https://www.mediawiki.org/wiki/Manual:Redirect_table
    from .main import logger

    with input_path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("INSERT INTO "):
                for row in parse_sql_line(line):
                    from_id, namespace, to_title, interwiki, fragment = row
                    if namespace == "0" and interwiki == "":
                        to_title = to_title.replace("_", " ")
                        if fragment == "":
                            fragment = None
                        else:
                            fragment = fragment.replace(" ", "_")
                        has_target_page = False
                        for _ in conn.execute(
                            "SELECT * FROM pages WHERE title = ?", (to_title,)
                        ):
                            conn.execute(
                                """
                                UPDATE pages SET redirect_to = ?, redirect_fragment = ?
                                WHERE id = ?
                                """,
                                (to_title, fragment, from_id),
                            )
                            has_target_page = True
                        if not has_target_page:
                            conn.execute("DELETE FROM pages WHERE id = ?", (from_id,))
    drop_temp_index(conn)
    logger.info("redirect.sql done")


def create_wiki_db(edition: str):
    import bz2
    import shutil

    conn, db_path = init_db(edition)
    for file in ("-page.sql.gz", "-page_props.sql.gz", "-redirect.sql.gz"):
        input_path = download_title_sql_dump(
            f"https://dumps.wikimedia.org/{edition}wiki/latest/{edition}wiki-latest{file}"
        )
        match file:
            case "-page.sql.gz":
                parse_page_sql(conn, input_path)
            case "-page_props.sql.gz":
                parse_page_props_sql(conn, input_path)
            case "-redirect.sql.gz":
                parse_redirect_sql(conn, input_path)
        input_path.unlink()
    bz2_path = db_path.with_name(db_path.name + ".bz2")
    if bz2_path.exists():
        bz2_path.unlink()
    with db_path.open("rb") as in_f, bz2.open(bz2_path, mode="wb") as out_f:
        shutil.copyfileobj(in_f, out_f)
    db_path.unlink()
