import json
import math
import re
from importlib.resources import files
from itertools import chain


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
        with (files("proficiency") / "en" / "kindle_enabled_lemmas.json").open(
            encoding="utf-8"
        ) as f:
            difficulty_data = {
                lemma: values[0] for lemma, values in json.load(f).items()
            }
    else:
        difficulty_json_path = files("proficiency") / lemma_lang / "difficulty.json"
        if difficulty_json_path.is_file():
            with difficulty_json_path.open(encoding="utf-8") as f:
                difficulty_data = json.load(f)

    return difficulty_data


def freq_to_difficulty(word: str, lang: str) -> tuple[bool, int]:
    """
    Zipf values are between 0 and 8, `zipf_frequency()` returns 0 if word is not in the
    wordlist and the word is disabled. Zipf value greater or equal to 7 means the word
    is too common, also disable it.

    Return difficulty value between 1 to 5, value 1 for the most obscure words and value
    5 for the most common words. Over half words in Wiktioanry have 0 zipf value and
    they are rare, enable them would take a long time to create spaCy Doc file.

    Also return `True` if the word should be disabled either too common or too rare.
    """
    from wordfreq import zipf_frequency

    freq = math.floor(zipf_frequency(word, lang))
    if freq == 0:
        return True, 1
    if freq >= 7:
        return True, 5
    if freq >= 5:
        return False, 5
    return False, freq


def get_en_inflections(lemma: str, pos: str | None) -> set[str]:
    from lemminflect import getAllInflections, getAllInflectionsOOV

    inflections = set(chain(*getAllInflections(lemma, pos).values()))
    if not inflections and pos:
        inflections = set(chain(*getAllInflectionsOOV(lemma, pos).values()))
    return inflections


if __name__ == "__main__":
    import sqlite3
    import sys
    from pathlib import Path

    from wordfreq import zipf_frequency

    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE words (word TEXT, freq REAL, PRIMARY KEY(word, freq))")

    jsonl_path = Path(sys.argv[1])
    lang_code = sys.argv[2]
    with jsonl_path.open(encoding="utf-8") as f:
        for line in f:
            data = json.loads(line)
            word = data.get("word")
            if word is not None:
                freq = zipf_frequency(word, lang_code)
                conn.execute("INSERT OR IGNORE INTO words VALUES(?, ?)", (word, freq))

    for (r,) in conn.execute("SELECT count(DISTINCT word) FROM words"):
        all_words = r

    print(f"{all_words=}")

    for lower_freq in range(9, -1, -1):
        for (r,) in conn.execute(
            "SELECT count(DISTINCT word) FROM words WHERE freq >= ? AND freq < ?",
            (lower_freq, lower_freq + 1),
        ):
            print(
                f"{lower_freq} <= freq < {lower_freq + 1}: {r}, {r / all_words * 100}"
            )
