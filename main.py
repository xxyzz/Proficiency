import argparse
import json
import sys
import tarfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from dump_wiktionary import dump_wiktionary
from en.dump_kindle_lemmas import dump_kindle_lemmas
from extract_wiktionary import download_kaikki_json, extract_wiktionary

VERSION = "0.1.0"
MAJOR_VERSION = "0"


def compress(lemma_lang: str, gloss_lang: str, files: list[Path]) -> None:
    with tarfile.open(
        f"{lemma_lang}/wiktionary_{lemma_lang}_{gloss_lang}_v{VERSION}.tar.gz", "x:gz"
    ) as tar:
        for wiktionary_file in files:
            tar.add(wiktionary_file)


def create_file(lemma_lang: str, languages: dict[str, str], gloss_lang: str) -> None:
    if gloss_lang == "en":
        kaikki_path = download_kaikki_json(lemma_lang, languages[lemma_lang])
    else:
        kaikki_path = Path(f"{lemma_lang}-{gloss_lang}.json")

    if lemma_lang != "en":
        difficulty_json_path = Path(f"{lemma_lang}/difficulty.json")
        difficulty_data = {}
        if difficulty_json_path.exists():
            with open(f"{lemma_lang}/difficulty.json", encoding="utf-8") as f:
                difficulty_data = json.load(f)
    else:
        with open("en/kindle_lemmas.json", encoding="utf-8") as f:
            difficulty_data = {
                lemma: values[0] for lemma, values in json.load(f).items()
            }

    wiktionary_json_path, tst_path = extract_wiktionary(
        lemma_lang, gloss_lang, kaikki_path, difficulty_data
    )
    wiktioanry_dump_path = Path(
        f"{lemma_lang}/wiktionary_{lemma_lang}_{gloss_lang}_dump_v{MAJOR_VERSION}"
    )
    dump_wiktionary(wiktionary_json_path, wiktioanry_dump_path, lemma_lang)
    compress(
        lemma_lang, gloss_lang, [wiktionary_json_path, tst_path, wiktioanry_dump_path]
    )

    if lemma_lang == "en" and gloss_lang == "en":
        with open("en/kindle_lemmas.json", encoding="utf-8") as f:
            lemmas = json.load(f)
            dump_kindle_lemmas(lemmas, f"en/kindle_lemmas_dump_v{MAJOR_VERSION}")


def main():
    with open("kaikki_languages.json", encoding="utf-8") as f:
        languages = json.load(f)

    parser = argparse.ArgumentParser()
    parser.add_argument("gloss_lang", choices=["en", "zh"])
    parser.add_argument(
        "--lemma-lang-codes",
        nargs="*",
        default=languages.keys(),
        choices=languages.keys(),
    )
    args = parser.parse_args()

    with ProcessPoolExecutor() as executor:
        for lemma_lang in args.lemma_lang_codes:
            executor.submit(create_file, lemma_lang, languages, args.gloss_lang)


if __name__ == "__main__":
    sys.exit(main())
