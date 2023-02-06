import csv
import json
from collections import defaultdict
from pathlib import Path


def kaikki_to_kindle_pos(pos: str) -> str:
    # https://github.com/tatuylonen/wiktextract/blob/master/wiktextract/data/en/pos_subtitles.json
    # https://github.com/xxyzz/WordDumb/blob/master/docs/word_wise_db.md#pos_types
    match pos:
        case "noun":
            return "noun"
        case "verb":
            return "verb"
        case "adj":
            return "adjective"
        case "adv":
            return "adverb"
        case "article":
            return "article"
        case "num":
            return "number"
        case "conj":
            return "conjunction"
        case "prep":
            return "preposition"
        case "pron":
            return "pronoun"
        case "particle":
            return "particle"
        case "punct":
            return "punctuation"
        case _:
            return "other"


def translate_english_lemmas(kaikki_path: Path, target_languages: set[str]) -> None:
    from en.extract_kindle_lemmas import transform_lemma

    with open("en/kindle_all_lemmas.csv", newline="") as f:
        csv_reader = csv.reader(f)
        kindle_lemmas: set[str] = set()
        for lemma, *_ in csv_reader:
            kindle_lemmas.add(lemma)
            if "(" in lemma or "/" in lemma:
                kindle_lemmas |= transform_lemma(lemma)

    lang_forms: dict[str, dict[str, list[str]]] = {}
    for target_lang in target_languages:
        with open(f"{target_lang}/forms.json", encoding="utf-8") as f:
            lang_forms[target_lang] = json.load(f)

    translations: dict[str, dict[str, list[list[str]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    with open(kaikki_path, encoding="utf-8") as f:
        for line in f:
            data = json.loads(line)
            word = data.get("word")
            pos = data.get("pos")
            kindle_pos = kaikki_to_kindle_pos(pos)

            if word not in kindle_lemmas:
                continue

            for sense in data.get("senses", []):
                translated_forms: dict[str, list[str]] = defaultdict(list)
                for trans_data in sense.get("translations", []):
                    target_lang = trans_data["code"]
                    if target_lang == "cmn":
                        target_lang = "zh"
                    elif target_lang == "sh":
                        target_lang = "hr"
                    if target_lang not in target_languages or "word" not in trans_data:
                        continue

                    translated_forms[f"{target_lang}_{word}_{kindle_pos}"].extend(
                        [trans_data["word"]]
                        + lang_forms[target_lang].get(
                            f"{trans_data['word']}_{kindle_pos}", []
                        )
                    )

                for lang_word_pos, forms in translated_forms.items():
                    lang, word_pos = lang_word_pos.split("_", 1)
                    translations[lang][word_pos].append(forms)

        for lang, data in translations.items():
            with open(f"{lang}/translations.json", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
