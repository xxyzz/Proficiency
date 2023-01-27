import argparse
import json
import tarfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from dump_wiktionary import dump_wiktionary
from en.dump_kindle_lemmas import dump_kindle_lemmas
from en.extract_kindle_lemmas import create_kindle_lemmas_db
from en.translate import translate_english_lemmas
from extract_wiktionary import create_wiktionary_lemmas_db

VERSION = "0.5.0"
MAJOR_VERSION = VERSION.split(".")[0]


def compress(tar_path: Path, files: list[Path]) -> None:
    if tar_path.exists():
        tar_path.unlink()
    with tarfile.open(tar_path, "x:gz") as tar:
        for wiktionary_file in files:
            tar.add(wiktionary_file)


def create_wiktionary_files(lemma_lang: str, gloss_lang: str) -> None:
    db_paths = create_wiktionary_lemmas_db(lemma_lang, gloss_lang, MAJOR_VERSION)
    dump_path = Path(
        f"{lemma_lang}/wiktionary_{lemma_lang}_{gloss_lang}_dump_v{MAJOR_VERSION}"
    )
    dump_wiktionary(lemma_lang, db_paths[0], dump_path)
    compress(
        Path(f"{lemma_lang}/wiktionary_{lemma_lang}_{gloss_lang}_v{VERSION}.tar.gz"),
        [db_paths[0], dump_path],
    )
    if gloss_lang == "zh":
        zh_cn_dump_path = Path(
            f"{lemma_lang}/wiktionary_{lemma_lang}_zh_cn_dump_v{MAJOR_VERSION}"
        )
        dump_wiktionary(lemma_lang, db_paths[1], zh_cn_dump_path)
        compress(
            Path(f"{lemma_lang}/wiktionary_{lemma_lang}_zh_cn_v{VERSION}.tar.gz"),
            [db_paths[1], zh_cn_dump_path],
        )


def create_kindle_files(lemma_lang: str, kaikki_json_path: Path) -> None:
    db_path = Path(f"{lemma_lang}/kindle_{lemma_lang}_en_v{MAJOR_VERSION}.db")
    dump_path = Path(f"{lemma_lang}/kindle_{lemma_lang}_en_dump_v{MAJOR_VERSION}")
    create_kindle_lemmas_db(lemma_lang, kaikki_json_path, db_path)
    dump_kindle_lemmas(lemma_lang in ["zh", "ja", "ko"], db_path, dump_path)
    compress(
        Path(f"{lemma_lang}/kindle_{lemma_lang}_en_v{VERSION}.tar.gz"),
        [db_path, dump_path],
    )


def main() -> None:
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
        results = [
            executor.submit(create_wiktionary_files, lemma_lang, args.gloss_lang)
            for lemma_lang in args.lemma_lang_codes
        ]

        for result in results:
            result.result()

    if args.gloss_lang == "en":
        kaikki_json_path = Path("en/kaikki.org-dictionary-English.json")
        translate_english_lemmas(kaikki_json_path, set(args.lemma_lang_codes) - {"en"})
        with ProcessPoolExecutor() as executor:
            results = [
                executor.submit(create_kindle_files, lemma_lang, kaikki_json_path)
                for lemma_lang in args.lemma_lang_codes
            ]

            for result in results:
                result.result()


if __name__ == "__main__":
    main()
