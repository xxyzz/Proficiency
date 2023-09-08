import json
import re
from pathlib import Path


def main() -> None:
    """
    Convert the Wikitext of pages in https://en.wiktionary.org/wiki/Appendix:JLPT
    to difficulty value
    """
    words = {}
    for txt_path in Path(".").glob("*.txt"):
        filename = txt_path.name
        difficulty = int(re.search(r"(\d)", filename).group(0))  # type: ignore
        with txt_path.open(encoding="utf-8") as f:
            for line in f:
                for match in re.finditer(r"{{([^}]+)}}", line):
                    word = match.group(1).split("|")[-1]
                    words[word] = difficulty

    with open("difficulty.json", "w", encoding="utf-8") as f:
        json.dump(words, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
