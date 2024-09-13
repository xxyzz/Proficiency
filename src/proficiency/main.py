import argparse
import logging
import multiprocessing
import re
import tarfile
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from importlib.metadata import version
from pathlib import Path

from .create_klld import create_klld_db
from .extract_dbnary import (
    create_lemmas_db_from_dbnary,
    download_dbnary_files,
    init_oxigraph_store,
)
from .extract_kaikki import create_lemmas_db_from_kaikki, download_kaikki_json
from .extract_kindle_lemmas import create_kindle_lemmas_db
from .languages import (
    DBNARY_LANGS,
    KAIKKI_GLOSS_LANGS,
    KAIKKI_LEMMA_LANGS,
    KAIKKI_TRANSLATED_GLOSS_LANGS,
)

VERSION = version("proficiency")
MAJOR_VERSION = VERSION.split(".")[0]


def create_wiktionary_files_from_kaikki(
    lemma_lang: str, gloss_lang: str = "en"
) -> list[Path]:
    if gloss_lang in KAIKKI_TRANSLATED_GLOSS_LANGS:
        download_kaikki_json(lemma_lang, gloss_lang)

    return create_lemmas_db_from_kaikki(lemma_lang, gloss_lang)


def create_wiktionary_files_from_dbnary(
    lemma_langs: list[str], gloss_lang: str
) -> list[Path]:
    download_dbnary_files(gloss_lang)
    store, has_morphology = init_oxigraph_store(gloss_lang)
    db_paths: list[Path] = []
    for lemma_lang in lemma_langs:
        db_paths.extend(
            create_lemmas_db_from_dbnary(store, lemma_lang, gloss_lang, has_morphology)
        )
    return db_paths


def main() -> None:
    logging.basicConfig(
        format="%(asctime)s %(levelname)s: %(message)s", level=logging.INFO
    )
    gloss_languages = (
        KAIKKI_GLOSS_LANGS | KAIKKI_TRANSLATED_GLOSS_LANGS.keys() | DBNARY_LANGS.keys()
    )
    parser = argparse.ArgumentParser()
    parser.add_argument("gloss_lang", choices=gloss_languages)
    parser.add_argument(
        "--lemma-lang-codes",
        nargs="*",
        default=KAIKKI_LEMMA_LANGS,
        choices=KAIKKI_LEMMA_LANGS,
    )
    args = parser.parse_args()
    if args.gloss_lang not in KAIKKI_GLOSS_LANGS | KAIKKI_TRANSLATED_GLOSS_LANGS.keys():
        available_lemma_languages: set[str] = set()
        if DBNARY_LANGS[args.gloss_lang]["has_exolex"]:
            if "lemma_languages" in DBNARY_LANGS[args.gloss_lang]:
                available_lemma_languages = DBNARY_LANGS[args.gloss_lang][
                    "lemma_languages"
                ]
            else:
                available_lemma_languages = KAIKKI_GLOSS_LANGS
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
    if args.gloss_lang in KAIKKI_TRANSLATED_GLOSS_LANGS:
        args.lemma_lang_codes = KAIKKI_TRANSLATED_GLOSS_LANGS[args.gloss_lang]

    with ProcessPoolExecutor(
        mp_context=multiprocessing.get_context("spawn")
    ) as executor:
        logging.info("Creating Wiktionary files")
        file_paths = []
        if args.gloss_lang in KAIKKI_GLOSS_LANGS | KAIKKI_TRANSLATED_GLOSS_LANGS.keys():
            if args.gloss_lang in KAIKKI_GLOSS_LANGS:
                download_kaikki_json("", args.gloss_lang)
            for db_paths in executor.map(
                partial(
                    create_wiktionary_files_from_kaikki, gloss_lang=args.gloss_lang
                ),
                args.lemma_lang_codes,
            ):
                file_paths.extend(db_paths)
        else:
            file_paths = create_wiktionary_files_from_dbnary(
                args.lemma_lang_codes, args.gloss_lang
            )
        logging.info("Wiktionary files created")

        logging.info("Creating Kindle files")
        kindle_db_path = Path()
        if "en" in args.lemma_lang_codes and args.gloss_lang in ["en", "zh"]:
            kindle_db_path = Path(f"build/en/kindle_en_en_v{MAJOR_VERSION}.db")
            create_kindle_lemmas_db(kindle_db_path)

        no_zh_cn_paths = file_paths.copy()
        for db_path in executor.map(
            partial(create_klld_db, args.gloss_lang),
            args.lemma_lang_codes,
        ):
            no_zh_cn_paths.append(db_path)
        archive_files(no_zh_cn_paths, kindle_db_path)
        if args.gloss_lang == "zh":
            for db_path in executor.map(
                partial(create_klld_db, "zh_cn"),
                args.lemma_lang_codes,
            ):
                file_paths.append(db_path)
            archive_files(file_paths, kindle_db_path, True)
        logging.info("Kindle files created")


def archive_files(
    file_paths: list[Path], kindle_db_path: Path, is_zh_cn: bool = False
) -> None:
    grouped_paths = defaultdict(list)
    lemma_code = ""
    gloss_code = ""
    for path in file_paths:
        if (is_zh_cn and "zh_cn" not in path.name) or (
            not is_zh_cn and "zh_cn" in path.name
        ):
            continue
        _, lemma_code, gloss_code, _ = re.split(r"\.|_", path.name, 3)
        tar_name = f"{lemma_code}_{gloss_code}"
        if is_zh_cn:
            tar_name += "_cn"
        grouped_paths[tar_name].append(path)
    for tar_name, paths in grouped_paths.items():
        tar_path = Path(f"build/{tar_name}.tar.bz2")
        with tarfile.open(name=tar_path, mode="x:bz2") as tar_f:
            for path in paths:
                tar_f.add(path, path.name)
            if tar_name.startswith(("en_en", "en_zh")):
                tar_f.add(kindle_db_path, kindle_db_path.name)


if __name__ == "__main__":
    main()
