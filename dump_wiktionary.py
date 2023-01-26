import json
import pickle
import sqlite3
from pathlib import Path


def dump_wiktionary(lemma_lang: str, db_path: Path, dump_path: Path) -> None:
    is_cjk = lemma_lang in ["zh", "ja", "ko"]
    if is_cjk:
        import ahocorasick

        kw_processor = ahocorasick.Automaton()
    else:
        from flashtext import KeywordProcessor

        kw_processor = KeywordProcessor()

    try:
        from .config import prefs  # type: ignore

        prefered_en_ipa = prefs["en_ipa"]
        prefered_zh_ipa = prefs["zh_ipa"]
        difficulty_limit = prefs[f"{lemma_lang}_wiktionary_difficulty_limit"]
    except ImportError:
        prefered_en_ipa = "ga_ipa"
        prefered_zh_ipa = "pinyin"
        difficulty_limit = 5

    conn = sqlite3.connect(db_path)
    if lemma_lang == "en":
        query_sql = "SELECT enabled, lemma, short_def, full_def, forms, example, ga_ipa, rp_ipa FROM lemmas WHERE difficulty <= ?"
    elif lemma_lang == "zh":
        query_sql = "SELECT enabled, lemma, short_def, full_def, forms, example, pinyin, bopomofo FROM lemmas WHERE difficulty <= ?"
    else:
        query_sql = "SELECT enabled, lemma, short_def, full_def, forms, example, ipa FROM lemmas WHERE difficulty <= ?"
    for enabled, lemma, short_def, full_def, forms, example, *ipas in conn.execute(
        query_sql, (difficulty_limit,)
    ):
        if lemma_lang == "en":
            ga_ipa, rp_ipa = ipas
            ipa = ga_ipa if prefered_en_ipa == "ga_ipa" else rp_ipa
        elif lemma_lang == "zh":
            pinyin, bopomofo = ipas
            ipa = pinyin if prefered_zh_ipa == "pinyin" else bopomofo
        else:
            ipa = ipas[0]

        if is_cjk:
            kw_processor.add_word(lemma, (lemma, short_def, full_def, example, ipa))
        else:
            kw_processor.add_keyword(lemma, (short_def, full_def, example, ipa))
        for form in forms.split(","):
            if is_cjk:
                kw_processor.add_word(form, (form, short_def, full_def, example, ipa))
            else:
                kw_processor.add_keyword(form, (short_def, full_def, example, ipa))

    conn.close()
    if is_cjk:
        kw_processor.make_automaton()
        kw_processor.save(str(dump_path), pickle.dumps)
    else:
        with open(dump_path, "wb") as f:
            pickle.dump(kw_processor, f)
