import json
import sys
import tarfile
import subprocess


def main() -> None:
    """
    Split extracted data to each language file.
    """

    all_jsonl = sys.argv[1]

    lang_codes = {
        "ca",
        "da",
        "de",
        "el",
        "en",
        "es",
        "fi",
        "fr",
        "it",
        "ja",
        "ko",
        "lt",
        "mk",
        "nl",
        "no",
        "pl",
        "pt",
        "ro",
        "ru",
        "sh",
        "sv",
        "uk",
        "zh",
    }

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

        with tarfile.open(f"{lang}_zh.tar.gz", "w:gz") as tar:
            tar.add(f"{lang}_zh.json")


if __name__ == "__main__":
    main()
