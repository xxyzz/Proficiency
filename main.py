import argparse
import json
import logging
import tarfile
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from pathlib import Path

from create_klld import create_klld_db
from database import wiktionary_db_path
from extract_dbnary import (
    create_lemmas_db_from_dbnary,
    download_dbnary_files,
    init_oxigraph_store,
)
from extract_kaikki import create_lemmas_db_from_kaikki
from extract_kindle_lemmas import create_kindle_lemmas_db

VERSION = "0.5.6"
MAJOR_VERSION = VERSION.split(".")[0]


def compress(tar_path: Path, files: list[Path]) -> None:
    if tar_path.exists():
        tar_path.unlink()
    with tarfile.open(tar_path, "x:gz") as tar:
        for wiktionary_file in files:
            tar.add(wiktionary_file)


def compress_wiktionary_files(
    db_paths: list[Path], lemma_lang: str, gloss_lang: str
) -> None:
    compress(
        Path(f"{lemma_lang}/wiktionary_{lemma_lang}_{gloss_lang}_v{VERSION}.tar.gz"),
        db_paths[:1],
    )
    if gloss_lang == "zh":
        compress(
            Path(f"{lemma_lang}/wiktionary_{lemma_lang}_zh_cn_v{VERSION}.tar.gz"),
            db_paths[1:],
        )


def create_wiktionary_files_from_kaikki(
    lemma_lang: str, gloss_lang: str = "en"
) -> None:
    db_paths = create_lemmas_db_from_kaikki(lemma_lang, gloss_lang)
    compress_wiktionary_files(db_paths, lemma_lang, gloss_lang)


def create_wiktionary_files_from_dbnary(
    lemma_langs: list[str], gloss_lang: str
) -> None:
    download_dbnary_files(gloss_lang)
    store, has_morphology = init_oxigraph_store(gloss_lang)
    for lemma_lang in lemma_langs:
        db_paths = create_lemmas_db_from_dbnary(
            store, lemma_lang, gloss_lang, has_morphology
        )
        compress_wiktionary_files(db_paths, lemma_lang, gloss_lang)


def create_kindle_files(lemma_lang: str, gloss_lang: str) -> None:
    if lemma_lang == "en" and gloss_lang == "en":
        db_path = Path(f"en/kindle_en_en_v{MAJOR_VERSION}.db")
        create_kindle_lemmas_db(db_path)
        compress(Path(f"en/kindle_en_en_v{VERSION}.tar.gz"), [db_path])

    klld_path = Path(
        f"{lemma_lang}/kll.{lemma_lang}.{gloss_lang}_v{MAJOR_VERSION}.klld"
    )
    create_klld_db(
        wiktionary_db_path(lemma_lang, gloss_lang),
        klld_path,
        lemma_lang,
        gloss_lang,
    )
    compress(
        Path(f"{lemma_lang}/kll.{lemma_lang}.{gloss_lang}_v{VERSION}.klld.tar.gz"),
        [klld_path],
    )


def main() -> None:
    logging.basicConfig(
        format="%(asctime)s %(levelname)s: %(message)s", level=logging.INFO
    )
    with open("data/kaikki_languages.json", encoding="utf-8") as f:
        kaikki_languages = json.load(f)
    with open("data/dbnary_languages.json") as f:
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
    if args.gloss_lang not in ["en", "zh"]:
        avaliable_lemma_languages: set[str] = set()
        if dbnary_languages[args.gloss_lang]["has_exolex"]:
            if "lemma_languages" in dbnary_languages[args.gloss_lang]:
                avaliable_lemma_languages = set(
                    dbnary_languages[args.gloss_lang]["lemma_languages"]
                )
            else:
                avaliable_lemma_languages = set(kaikki_languages.keys())
        else:
            avaliable_lemma_languages = {args.gloss_lang}
        lemma_languages = set(args.lemma_lang_codes) & avaliable_lemma_languages
        if len(lemma_languages) == 0:
            logging.error(
                f"Invalid lemma language code, avaliable codes: {avaliable_lemma_languages}"
            )
            raise ValueError
        args.lemma_lang_codes = list(lemma_languages)

    with ProcessPoolExecutor() as executor:
        logging.info("Creating Wiktionary files")
        if args.gloss_lang in ["en", "zh"]:
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
