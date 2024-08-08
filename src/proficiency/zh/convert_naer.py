import argparse
import csv
import json
import re


def convert_difficulty(level_str: str) -> int:
    match int(level_str[1]):
        case 1 | 2 | 3:
            return 5
        case 4:
            return 4
        case 5:
            return 3
        case 6:
            return 2
        case _:
            return 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert COCT data")
    parser.add_argument(
        "csv_path", help="CSV file exported from Excel file's main table"
    )
    args = parser.parse_args()

    words = {}
    with open(args.csv_path, newline="", encoding="utf-8") as csvfile:
        first_row = True
        for row in csv.reader(csvfile):
            if first_row:
                first_row = False
                continue
            word = row[1]
            last_character = word[-1]
            if last_character.isdigit():
                word = word[:-1]
                if int(last_character) > 1:
                    continue
            if len(word) < 2:
                continue
            level = row[3]
            difficulty = convert_difficulty(level)
            if "/" in word:
                for split_word in word.split("/"):
                    if len(split_word) >= 2:
                        words[split_word] = difficulty
            elif "(" in word:
                words[re.sub(r"[()]", "", word)] = difficulty
                words[re.sub(r"\([^)]+\)", "", word)] = difficulty
            else:
                words[word] = difficulty

    with open("difficulty.json", "w") as f:
        json.dump(words, f, indent=2, ensure_ascii=False, sort_keys=True)


if __name__ == "__main__":
    main()
