import json
import sys
import tarfile


def main() -> None:
    """
    Split extracted Chinese Wiktionary json file to each language file.
    """

    all_jsonl = sys.argv[1]
    kaikki_json_path = sys.argv[2]

    with open(kaikki_json_path) as f:
        lang_codes = json.load(f)

    files = {lang: open(f"{lang}_zh.json", "w") for lang in lang_codes}

    with open(all_jsonl) as f:
        for line in f:
            data = json.loads(line)
            if "lang_code" in data:
                lang_code = data["lang_code"]
                if lang_code in lang_codes:
                    files[lang_code].write(line)
                elif lang_code == "mul":
                    for f in files.values():
                        f.write(line)

    for lang, f in files.items():
        f.close()

        with tarfile.open(f"{lang}_zh.bz2", "w:bz2") as tar:
            tar.add(f"{lang}_zh.json")


if __name__ == "__main__":
    main()
