import json
import pickle
from pathlib import Path


def get_ipa(lang: str, ipas: dict[str, str] | str) -> str:
    if not ipas:
        return ""
    elif lang in ["en", "zh"]:
        try:
            from .config import prefs  # type: ignore
        except ImportError:
            prefs = {"en_ipa": "US", "zh_ipa": "Pinyin"}

        ipa_tag = prefs["en_ipa"] if lang == "en" else prefs["zh_ipa"]
        if isinstance(ipas, str):
            return ipas
        elif ipa_tag in ipas:
            return ipas[ipa_tag]
        elif lang == "en":
            for ipa in ipas.values():
                return ipa

    return ipas  # type: ignore


def dump_wiktionary(json_path: Path, dump_path: Path, lang: str) -> None:
    with open(json_path, encoding="utf-8") as f:
        words = json.load(f)

    if lang in ["zh", "ja", "ko"]:
        import ahocorasick

        automaton = ahocorasick.Automaton()
        for _, word, _, short_gloss, gloss, example, forms, ipas, _ in filter(
            lambda x: x[0] and not automaton.exists(x[1]), words
        ):
            ipa = get_ipa(lang, ipas)
            automaton.add_word(word, (word, short_gloss, gloss, example, ipa))
            for form in filter(lambda x: not automaton.exists(x), forms.split(",")):
                automaton.add_word(form, (form, short_gloss, gloss, example, ipa))

        automaton.make_automaton()
        automaton.save(str(dump_path), pickle.dumps)
    else:
        from flashtext import KeywordProcessor

        keyword_processor = KeywordProcessor()
        for _, word, _, short_gloss, gloss, example, forms, ipas, _ in filter(
            lambda x: x[0] and x[1] not in keyword_processor, words
        ):
            ipa = get_ipa(lang, ipas)
            keyword_processor.add_keyword(word, (short_gloss, gloss, example, ipa))
            for form in filter(lambda x: x not in keyword_processor, forms.split(",")):
                keyword_processor.add_keyword(form, (short_gloss, gloss, example, ipa))

        with open(dump_path, "wb") as f:
            pickle.dump(keyword_processor, f)
