import json
from pathlib import Path
from typing import BinaryIO


def split_kaikki_jsonl(jsonl_f: BinaryIO, gloss_code: str) -> None:
    """
    Split extracted jsonl file created by wiktextract to each language file.
    """
    from .languages import KAIKKI_LEMMA_LANGS

    lemma_codes = KAIKKI_LEMMA_LANGS
    lemma_codes.remove("hr")  # Croatian
    # Wiktionary still uses the deprecated language code
    lemma_codes.add("sh")

    out_file_paths = {
        lemma_code: Path(f"build/{lemma_code}/{lemma_code}_{gloss_code}.jsonl")
        for lemma_code in lemma_codes
    }
    for out_file_path in out_file_paths.values():
        out_file_path.parent.mkdir(parents=True, exist_ok=True)
    out_files = {
        lemma_code: out_file_path.open("w", encoding="utf-8")
        for lemma_code, out_file_path in zip(lemma_codes, out_file_paths.values())
    }

    for line in jsonl_f:
        data = json.loads(line)
        if "lang_code" in data:
            lang_code = data["lang_code"]
            if lang_code in lemma_codes:
                out_files[lang_code].write(line.decode("utf-8"))
            elif lang_code == "mul":
                for out_f in out_files.values():
                    out_f.write(line.decode("utf-8"))

    for out_f in out_files.values():
        out_f.close()
