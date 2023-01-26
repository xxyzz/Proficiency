import pickle
import sqlite3
from pathlib import Path


def dump_kindle_lemmas(is_cjk: bool, db_path: Path, dump_path: Path) -> None:
    if is_cjk:
        import ahocorasick

        kw_processor = ahocorasick.Automaton()
    else:
        from flashtext import KeywordProcessor

        kw_processor = KeywordProcessor()

    conn = sqlite3.connect(db_path)
    for lemma, difficulty, sense_id, forms_str in conn.execute(
        "SELECT lemma, difficulty, sense_id, forms FROM lemmas WHERE enabled = 1"
    ):
        if is_cjk:
            kw_processor.add_word(lemma, (lemma, difficulty, sense_id))
        else:
            kw_processor.add_keyword(lemma, (difficulty, sense_id))
        for form in forms_str.split(","):
            if is_cjk:
                kw_processor.add_word(lemma, (lemma, difficulty, sense_id))
            else:
                kw_processor.add_keyword(lemma, (difficulty, sense_id))

    conn.close()
    if is_cjk:
        kw_processor.make_automaton()
        kw_processor.save(str(dump_path), pickle.dumps)
    else:
        with open(dump_path, "wb") as f:
            pickle.dump(kw_processor, f)
