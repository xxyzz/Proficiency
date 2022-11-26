#!/usr/bin/env python3

import pickle
import re
from itertools import chain, product
from pathlib import Path
from typing import Any

# https://lemminflect.readthedocs.io/en/latest/tags
POS_TYPE = {0: "NOUN", 1: "VERB", 2: "ADJ", 3: "ADV", 9: "PROPN"}


def get_inflections(lemma: str, pos: str) -> set[str]:
    from lemminflect import getAllInflections, getAllInflectionsOOV

    inflections = set(chain(*getAllInflections(lemma, pos).values()))
    if not inflections and pos:
        inflections = set(chain(*getAllInflectionsOOV(lemma, pos).values()))
    return inflections


def add_lemma(
    lemma: str, pos: str, data: tuple[int, int], keyword_processor: Any
) -> None:
    if " " in lemma:
        if "/" in lemma:  # "be/get togged up/out"
            words = [word.split("/") for word in lemma.split()]
            for phrase in map(" ".join, product(*words)):
                add_lemma(phrase, pos, data, keyword_processor)
        elif pos == "VERB":
            # inflect the first word of the phrase verb
            first_word, rest_words = lemma.split(maxsplit=1)
            for inflection in {first_word}.union(get_inflections(first_word, "VERB")):
                keyword_processor.add_keyword(f"{inflection} {rest_words}", data)
        else:
            keyword_processor.add_keyword(lemma, data)
    elif "-" in lemma:
        keyword_processor.add_keyword(lemma, data)
    else:
        for inflection in {lemma}.union(get_inflections(lemma, pos)):
            keyword_processor.add_keyword(inflection, data)


def dump_kindle_lemmas(
    lemmas: dict[str, tuple[int, int, int]], dump_path: Path | str
) -> None:
    from flashtext import KeywordProcessor

    keyword_processor = KeywordProcessor()
    for lemma, (difficulty, sense_id, pos) in lemmas.items():
        pos_str = POS_TYPE.get(pos, "")
        data = (difficulty, sense_id)
        if "(" in lemma:  # "(as) good as new"
            add_lemma(re.sub(r"[()]", "", lemma), pos_str, data, keyword_processor)
            add_lemma(
                " ".join(re.sub(r"\([^)]+\)", "", lemma).split()),
                pos_str,
                data,
                keyword_processor,
            )
        else:
            add_lemma(lemma, pos_str, data, keyword_processor)

    with open(dump_path, "wb") as f:
        pickle.dump(keyword_processor, f)
