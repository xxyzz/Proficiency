import argparse
import csv
import json
import re
import sys


def convert_difficulty(level: str) -> int:
    match level:
        case "第P1級" | "第1級" | "第1+級" | "第2級" | "第2+級" | "第3級" | "第3+級":
            return 5
        case "第4級":
            return 4
        case "第5級":
            return 3
        case "第6級":
            return 2
        case "第7級":
            return 1


def main():
    parser = argparse.ArgumentParser(description="Convert COCT data")
    parser.add_argument(
        "csv_path", help="CSV file exported from Excel file's main table"
    )
    args = parser.parse_args()

    words = {}
    with open(args.csv_path, newline="") as csvfile:
        first_row = True
        for row in csv.reader(csvfile):
            if first_row:
                first_row = False
                continue
            word = row[1]
            last_chracter = word[-1]
            if last_chracter.isdigit():
                word = word[:-1]
                if int(last_chracter) > 1:
                    continue
            if len(word) < 2:
                continue
            level = row[3]
            difficulty = convert_difficulty(level)
            if "/" in word:
                for splited_word in word.split("/"):
                    if len(splited_word) >= 2:
                        words[splited_word] = difficulty
            elif "(" in word:
                words[re.sub(r"[()]", "", word)] = difficulty
                words[re.sub(r"\([^)]+\)", "", word)] = difficulty
            else:
                words[word] = difficulty

    with open("difficulty.json", "w") as f:
        json.dump(words, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    sys.exit(main())
