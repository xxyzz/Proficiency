import json
import logging
from gzip import GzipFile
from pathlib import Path
from typing import IO


def split_kaikki_jsonl(
    jsonl_f: IO[bytes] | GzipFile, lemma_code: str, gloss_code: str
) -> None:
    """
    Split extracted jsonl file created by wiktextract to each language file.
    """
    from .languages import KAIKKI_LEMMA_LANGS, KAIKKI_TRANSLATED_GLOSS_LANGS

    logging.info("Start splitting JSONL file")
    if gloss_code in KAIKKI_TRANSLATED_GLOSS_LANGS:
        lemma_codes = {lemma_code}
        gloss_code = lemma_code
    else:
        lemma_codes = KAIKKI_LEMMA_LANGS

    out_file_paths = {
        l_code: Path(f"build/{l_code}/{l_code}_{gloss_code}.jsonl")
        for l_code in lemma_codes
    }
    for out_file_path in out_file_paths.values():
        out_file_path.parent.mkdir(parents=True, exist_ok=True)
    out_files = {
        l_code: out_file_path.open("w", encoding="utf-8")
        for l_code, out_file_path in zip(lemma_codes, out_file_paths.values())
    }

    for line in iter(jsonl_f.readline, b""):
        data = json.loads(line)
        if "lang_code" in data:
            lang_code = data["lang_code"]
            if lang_code in lemma_codes:
                out_files[lang_code].write(line.decode("utf-8"))
            else:
                new_lang_code = convert_lang_code(lang_code)
                if new_lang_code in lemma_codes:
                    out_files[new_lang_code].write(line.decode("utf-8"))

    for out_f in out_files.values():
        out_f.close()
    logging.info("Split JSONL file completed")


def convert_lang_code(code: str) -> str:
    codes = {
        "sh": "hr",  # Serbo-Croatian -> Croatian
        "no": "nb",  # Norwegian -> Norwegian Bokmål
        "cmn": "zh",  # used in Russian Wiktionary for Mandarin Chinese
    }
    return codes.get(code, "")
