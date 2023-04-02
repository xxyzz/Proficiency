import json
import re
from itertools import chain
from pathlib import Path


def get_shortest_lemma_length(lemma_lang: str) -> int:
    if lemma_lang in {"zh", "ja", "ko"}:
        return 2
    else:
        return 3


def remove_full_stop(text: str) -> str:
    return text.removesuffix(".").removesuffix("。")


def get_short_def(gloss: str, gloss_lang: str) -> str:
    gloss = remove_full_stop(gloss)
    gloss = re.sub(
        r"\([^)]+\)|（[^）]+）|〈[^〉]+〉|\[[^]]+\]|［[^］]+］|【[^】]+】|﹝[^﹞]+﹞|「[^」]+」",
        "",
        gloss,
    )
    gloss = min(re.split(";|；", gloss), key=len)
    gloss = min(gloss.split("/"), key=len)
    if gloss_lang == "zh":
        gloss = min(gloss.split("、"), key=len)
    if gloss_lang == "es" and "|" in gloss:
        gloss = gloss.split("|", 1)[1]
    return gloss.strip()


def load_difficulty_data(lemma_lang: str) -> dict[str, int]:
    difficulty_data = {}
    if lemma_lang == "en":
        with open("en/kindle_enabled_lemmas.json", encoding="utf-8") as f:
            difficulty_data = {
                lemma: values[0] for lemma, values in json.load(f).items()
            }
    else:
        difficulty_json_path = Path(f"{lemma_lang}/difficulty.json")
        if difficulty_json_path.exists():
            with difficulty_json_path.open(encoding="utf-8") as f:
                difficulty_data = json.load(f)

    return difficulty_data


def freq_to_difficulty(word: str, lang: str) -> int:
    from wordfreq import zipf_frequency

    freq = zipf_frequency(word, lang)
    if freq >= 7:
        return 5
    elif freq >= 5:
        return 4
    elif freq >= 3:
        return 3
    elif freq >= 1:
        return 2
    else:
        return 1


def get_en_inflections(lemma: str, pos: str | None) -> set[str]:
    from lemminflect import getAllInflections, getAllInflectionsOOV

    inflections = set(chain(*getAllInflections(lemma, pos).values()))
    if not inflections and pos:
        inflections = set(chain(*getAllInflectionsOOV(lemma, pos).values()))
    return inflections
