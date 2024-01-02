import json
from importlib.resources import files
from pathlib import Path


def split_kaikki_non_en_jsonl(jsonl_path: Path, gloss_code: str) -> None:
    """
    Split extracted jsonl file created by wiktextract to each language file.
    """
    with (files("proficiency") / "data" / "kaikki_languages.json").open(
        encoding="utf-8"
    ) as f:
        lang_codes = json.load(f)
        del lang_codes["hr"]  # Croatian
        # Wiktionary still uses the deprecated language code
        lang_codes["sh"] = "Serbo-Croatian"

    out_file_paths = {
        lemma_code: Path(f"build/{lemma_code}/{lemma_code}_{gloss_code}.jsonl")
        for lemma_code in lang_codes
    }
    for out_file_path in out_file_paths.values():
        out_file_path.parent.mkdir(parents=True, exist_ok=True)
    out_files = {
        lemma_code: out_file_path.open("w", encoding="utf-8")
        for lemma_code, out_file_path in zip(lang_codes.keys(), out_file_paths.values())
    }

    with jsonl_path.open(encoding="utf-8") as jsonl_f:
        for line in jsonl_f:
            data = json.loads(line)
            if "lang_code" in data:
                lang_code = data["lang_code"]
                if lang_code in lang_codes:
                    out_files[lang_code].write(line)
                elif lang_code == "mul":
                    for out_f in out_files.values():
                        out_f.write(line)

    for out_f in out_files.values():
        out_f.close()
