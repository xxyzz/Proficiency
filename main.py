import argparse
import json
import logging
import tarfile
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from pathlib import Path

from create_klld import create_klld_db
from en.extract_kindle_lemmas import create_kindle_lemmas_db
from extract_wiktionary import create_wiktionary_lemmas_db, wiktionary_db_path

VERSION = "0.5.5dev"
MAJOR_VERSION = VERSION.split(".")[0]


def compress(tar_path: Path, files: list[Path]) -> None:
    if tar_path.exists():
        tar_path.unlink()
    with tarfile.open(tar_path, "x:gz") as tar:
        for wiktionary_file in files:
            tar.add(wiktionary_file)


def create_wiktionary_files(lemma_lang: str, gloss_lang: str = "en") -> None:
    db_paths = create_wiktionary_lemmas_db(lemma_lang, gloss_lang, MAJOR_VERSION)
    compress(
        Path(f"{lemma_lang}/wiktionary_{lemma_lang}_{gloss_lang}_v{VERSION}.tar.gz"),
        db_paths[:1],
    )
    if gloss_lang == "zh":
        compress(
            Path(f"{lemma_lang}/wiktionary_{lemma_lang}_zh_cn_v{VERSION}.tar.gz"),
            db_paths[1:],
        )


def create_kindle_files(lemma_lang: str, gloss_lang: str) -> None:
    if lemma_lang == "en" and gloss_lang == "en":
        db_path = Path(f"en/kindle_en_en_v{MAJOR_VERSION}.db")
        create_kindle_lemmas_db(db_path)
        compress(Path(f"en/kindle_en_en_v{VERSION}.tar.gz"), [db_path])

    klld_path = Path(
        f"{lemma_lang}/kll.{lemma_lang}.{gloss_lang}_v{MAJOR_VERSION}.klld"
    )
    create_klld_db(
        wiktionary_db_path(lemma_lang, gloss_lang, MAJOR_VERSION),
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
    with open("kaikki_languages.json", encoding="utf-8") as f:
        kaikki_languages = json.load(f)

    parser = argparse.ArgumentParser()
    parser.add_argument("gloss_lang", choices=["en", "zh"])
    parser.add_argument(
        "--lemma-lang-codes",
        nargs="*",
        default=kaikki_languages.keys(),
        choices=kaikki_languages.keys(),
    )
    args = parser.parse_args()

    with ProcessPoolExecutor() as executor:
        logging.info("Creating Wiktionary files")
        for _ in executor.map(
            partial(create_wiktionary_files, gloss_lang=args.gloss_lang),
            args.lemma_lang_codes,
        ):
            pass
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
