import argparse
import json
import subprocess
from importlib.resources import files
from pathlib import Path
from shutil import which


def main() -> None:
    """
    Split extracted jsonl file created by wiktextract to each language file.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("jsonl_path", type=Path)
    parser.add_argument("gloss_code")
    args = parser.parse_args()

    with (files("proficiency") / "data" / "kaikki_languages.json").open(
        encoding="utf-8"
    ) as f:
        lang_codes = json.load(f)
        del lang_codes["hr"]  # Croatian
        # Wiktionary still uses the deprecated language code
        lang_codes["sh"] = "Serbo-Croatian"

    out_file_paths = {
        lemma_code: Path(f"build/{lemma_code}/{lemma_code}_{args.gloss_code}.jsonl")
        for lemma_code in lang_codes
    }
    for out_file_path in out_file_paths.values():
        out_file_path.parent.mkdir(parents=True, exist_ok=True)
    out_files = {
        lemma_code: out_file_path.open("w", encoding="utf-8")
        for lemma_code, out_file_path in zip(lang_codes.keys(), out_file_paths.values())
    }

    with args.jsonl_path.open(encoding="utf-8") as jsonl_f:
        for line in jsonl_f:
            data = json.loads(line)
            if "lang_code" in data:
                lang_code = data["lang_code"]
                if lang_code in lang_codes:
                    out_files[lang_code].write(line)
                elif lang_code == "mul":
                    for out_f in out_files.values():
                        out_f.write(line)

    for lemma_code, out_f in out_files.items():
        out_f.close()
        jsonl_path = out_file_paths[lemma_code]
        jsonl_bz2_path = jsonl_path.with_suffix(".jsonl.bz2")
        jsonl_bz2_path.unlink(missing_ok=True)
        subprocess.run(
            ["lbzip2" if which("lbzip2") is not None else "bzip2", str(jsonl_path)],
            check=True,
            capture_output=True,
            text=True,
        )


if __name__ == "__main__":
    main()
