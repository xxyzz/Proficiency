import argparse
import json
import logging
import subprocess
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from importlib.metadata import version
from importlib.resources import files
from pathlib import Path
from shutil import which

from .create_klld import create_klld_db
from .database import wiktionary_db_path
from .extract_dbnary import (
    create_lemmas_db_from_dbnary,
    download_dbnary_files,
    init_oxigraph_store,
)
from .extract_kaikki import create_lemmas_db_from_kaikki
from .extract_kindle_lemmas import create_kindle_lemmas_db

VERSION = version("proficiency")
MAJOR_VERSION = VERSION.split(".")[0]
WIKITEXTRACT_LANGUAGES = frozenset(["en", "zh", "fr"])


def compress(file_path: Path) -> None:
    compressed_path = file_path.with_suffix(file_path.suffix + ".bz2")
    compressed_path.unlink(missing_ok=True)
    subprocess.run(
        ["lbzip2" if which("lbzip2") is not None else "bzip2", "-k", str(file_path)],
        check=True,
        capture_output=True,
        text=True,
    )


def create_wiktionary_files_from_kaikki(
    lemma_lang: str, gloss_lang: str = "en"
) -> None:
    for db_path in create_lemmas_db_from_kaikki(lemma_lang, gloss_lang):
        compress(db_path)


def create_wiktionary_files_from_dbnary(
    lemma_langs: list[str], gloss_lang: str
) -> None:
    download_dbnary_files(gloss_lang)
    store, has_morphology = init_oxigraph_store(gloss_lang)
    for lemma_lang in lemma_langs:
        for db_path in create_lemmas_db_from_dbnary(
            store, lemma_lang, gloss_lang, has_morphology
        ):
            compress(db_path)


def create_kindle_files(lemma_lang: str, gloss_lang: str) -> None:
    if lemma_lang == "en" and gloss_lang == "en":
        db_path = Path(f"build/en/kindle_en_en_v{MAJOR_VERSION}.db")
        create_kindle_lemmas_db(db_path)
        compress(db_path)

    klld_path = Path(
        f"build/{lemma_lang}/kll.{lemma_lang}.{gloss_lang}_v{MAJOR_VERSION}.klld"
    )
    create_klld_db(
        wiktionary_db_path(lemma_lang, gloss_lang),
        klld_path,
        lemma_lang,
        gloss_lang,
    )
    compress(klld_path)


def main() -> None:
    logging.basicConfig(
        format="%(asctime)s %(levelname)s: %(message)s", level=logging.INFO
    )
    with (files("proficiency") / "data" / "kaikki_languages.json").open(
        encoding="utf-8"
    ) as f:
        kaikki_languages = json.load(f)
    with (files("proficiency") / "data" / "dbnary_languages.json").open(
        encoding="utf-8"
    ) as f:
        dbnary_languages = json.load(f)
    gloss_languages = kaikki_languages.keys() & dbnary_languages.keys()

    parser = argparse.ArgumentParser()
    parser.add_argument("gloss_lang", choices=gloss_languages)
    parser.add_argument(
        "--lemma-lang-codes",
        nargs="*",
        default=kaikki_languages.keys(),
        choices=kaikki_languages.keys(),
    )
    args = parser.parse_args()
    if args.gloss_lang not in WIKITEXTRACT_LANGUAGES:
        available_lemma_languages: set[str] = set()
        if dbnary_languages[args.gloss_lang]["has_exolex"]:
            if "lemma_languages" in dbnary_languages[args.gloss_lang]:
                available_lemma_languages = set(
                    dbnary_languages[args.gloss_lang]["lemma_languages"]
                )
            else:
                available_lemma_languages = set(kaikki_languages.keys())
        else:
            available_lemma_languages = {args.gloss_lang}
        lemma_languages = set(args.lemma_lang_codes) & available_lemma_languages
        if len(lemma_languages) == 0:
            logging.error(
                "Invalid lemma language code, available codes: "
                + str(available_lemma_languages)
            )
            raise ValueError
        args.lemma_lang_codes = list(lemma_languages)

    with ProcessPoolExecutor() as executor:
        logging.info("Creating Wiktionary files")
        if args.gloss_lang in WIKITEXTRACT_LANGUAGES:
            for _ in executor.map(
                partial(
                    create_wiktionary_files_from_kaikki, gloss_lang=args.gloss_lang
                ),
                args.lemma_lang_codes,
            ):
                pass
        else:
            create_wiktionary_files_from_dbnary(args.lemma_lang_codes, args.gloss_lang)
        logging.info("Wiktionary files created")

        logging.info("Creating Kindle files")
        for _ in executor.map(
            partial(create_kindle_files, gloss_lang=args.gloss_lang),
            args.lemma_lang_codes,
        ):
            pass
        if args.gloss_lang == "zh":
            for _ in executor.map(
                partial(create_kindle_files, gloss_lang="zh_cn"),
                args.lemma_lang_codes,
            ):
                pass
        logging.info("Kindle files created")


if __name__ == "__main__":
    main()
