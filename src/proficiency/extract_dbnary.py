import json
import sqlite3
import subprocess
from importlib.resources import files
from pathlib import Path
from shutil import which

from pyoxigraph import Store

from .database import create_indexes_then_close, init_db, wiktionary_db_path
from .util import (
    freq_to_difficulty,
    get_short_def,
    get_shortest_lemma_length,
    load_difficulty_data,
)


def download_dbnary_files(gloss_lang: str) -> None:
    with (files("proficiency") / "data" / "dbnary_languages.json").open(
        encoding="utf-8"
    ) as f:
        dbnary_languages = json.load(f)

    base_url = "https://kaiko.getalp.org/static/ontolex/latest"
    lang_key = gloss_lang
    if gloss_lang == "hr":
        gloss_lang = "sh"
    download_dbnary_file(f"{base_url}/{gloss_lang}_dbnary_ontolex.ttl.bz2")
    if dbnary_languages[lang_key]["has_exolex"]:
        download_dbnary_file(f"{base_url}/{gloss_lang}_dbnary_exolex_ontolex.ttl.bz2")
    if dbnary_languages[lang_key]["has_morphology"]:
        download_dbnary_file(f"{base_url}/{gloss_lang}_dbnary_morphology.ttl.bz2")


def download_dbnary_file(url: str) -> None:
    bz2_path = Path(f"build/ttl/{url.rsplit('/', 1)[-1]}")
    ttl_path = bz2_path.with_suffix("")
    ttl_exists = ttl_path.exists()
    if not bz2_path.exists() and not ttl_path.exists():
        subprocess.run(
            ["wget", "-nv", "-P", "build/ttl", url],
            check=True,
            text=True,
            capture_output=True,
        )
    if bz2_path.exists() and not ttl_path.exists():
        subprocess.run(
            ["lbunzip2" if which("lbunzip2") is not None else "bunzip2", str(bz2_path)],
            check=True,
            text=True,
            capture_output=True,
        )
    if not ttl_exists:
        # remove private use area characters that cause invalid IRI error
        # https://www.unicode.org/charts/PDF/UE000.pdf
        subprocess.run(
            ["perl", "-C", "-pi", "-e", r"s/[\x{E000}-\x{F8FF}]//g", str(ttl_path)],
            check=True,
            text=True,
            capture_output=True,
        )
        if ttl_path.name == "es_dbnary_ontolex.ttl":
            # Fix parse subtag error
            subprocess.run(
                ["perl", "-C", "-pi", "-e", "s/es-.+-ipa/es-fonipa/g", str(ttl_path)],
                check=True,
                text=True,
                capture_output=True,
            )


def insert_lemmas(
    store: Store, conn: sqlite3.Connection, lemma_lang: str
) -> dict[str, int]:
    lemma_ids: dict[str, int] = {}
    lemma_length_limit = get_shortest_lemma_length(lemma_lang)
    query = rf"""
    PREFIX lexinfo:  <http://www.lexinfo.net/ontology/2.0/lexinfo#>
    PREFIX lime:     <http://www.w3.org/ns/lemon/lime#>
    PREFIX ontolex:  <http://www.w3.org/ns/lemon/ontolex#>
    PREFIX rdf:      <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

    SELECT DISTINCT (GROUP_CONCAT(DISTINCT ?form_rep; SEPARATOR="|") AS ?word)
    ?pos (SAMPLE(?ipas) AS ?ipa)
    WHERE {{
      ?entry rdf:type ontolex:LexicalEntry ;
             ontolex:canonicalForm ?form ;
             lexinfo:partOfSpeech ?pos ;
             ontolex:sense ?sense ;
             lime:language '{lemma_lang}' .
      ?form ontolex:writtenRep ?form_rep .
      OPTIONAL {{ ?form ontolex:phoneticRep ?ipas . }}
      FILTER (?pos in (lexinfo:adjective, lexinfo:adverb, lexinfo:noun,
                       lexinfo:properNoun, lexinfo:verb)) .
      FILTER (STRLEN(STR(?form_rep)) >= {lemma_length_limit}) .
      FILTER (!REGEX(STR(?form_rep), "^\\d|'|&|\\(|\\.|-"))
    }}
    GROUP BY ?entry ?pos
    ORDER BY ?word ?pos
    """

    for query_result in store.query(query):  # type: ignore
        lemmas = query_result["word"].value.split("|")
        lemma = lemmas[0]
        if lemma not in lemma_ids:
            for (lemma_id,) in conn.execute(
                "INSERT INTO lemmas (lemma, ipa) VALUES(?, ?) RETURNING id",
                (lemma, query_result["ipa"].value if query_result["ipa"] else None),
            ):
                lemma_ids[lemma] = lemma_id
        else:
            lemma_id = lemma_ids[lemma]
        pos = dbnary_to_kaikki_pos(query_result["pos"].value)
        for other_form in lemmas[1:]:
            conn.execute(
                "INSERT OR IGNORE INTO forms VALUES(?, ?, ?)",
                (other_form, pos, lemma_id),
            )

    return lemma_ids


def insert_forms(
    store: Store, conn: sqlite3.Connection, lemma_lang: str, lemma_ids: dict[str, int]
) -> None:
    query = f"""
    PREFIX lexinfo:  <http://www.lexinfo.net/ontology/2.0/lexinfo#>
    PREFIX lime:     <http://www.w3.org/ns/lemon/lime#>
    PREFIX ontolex:  <http://www.w3.org/ns/lemon/ontolex#>
    PREFIX rdf:      <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

    SELECT DISTINCT ?form ?pos ?lemma
    WHERE {{
      ?entry rdf:type ontolex:LexicalEntry ;
             lexinfo:partOfSpeech ?pos ;
             ontolex:canonicalForm/ontolex:writtenRep ?lemma ;
             ontolex:otherForm/ontolex:writtenRep ?form ;
             ontolex:sense ?sense ;
             lime:language "{lemma_lang}" .
      FILTER (?pos in (lexinfo:adjective, lexinfo:adverb, lexinfo:noun,
                       lexinfo:properNoun, lexinfo:verb)) .
      FILTER (STR(?form) != STR(?lemma))
    }}
    ORDER BY ?lemma ?pos ?form
    """
    for query_result in store.query(query):  # type: ignore
        lemma = query_result["lemma"].value
        if lemma in lemma_ids:
            lemma_id = lemma_ids[lemma]
            conn.execute(
                "INSERT OR IGNORE INTO forms VALUES(?, ?, ?)",
                (
                    query_result["form"].value,
                    dbnary_to_kaikki_pos(query_result["pos"].value),
                    lemma_id,
                ),
            )


def insert_senses(
    store: Store,
    conn: sqlite3.Connection,
    lemma_lang: str,
    gloss_lang: str,
    lemma_ids: dict[str, int],
) -> None:
    enabled_lemma_pos: set[str] = set()
    difficulty_data = load_difficulty_data(lemma_lang)
    query = f"""
    PREFIX lexinfo:  <http://www.lexinfo.net/ontology/2.0/lexinfo#>
    PREFIX lime:     <http://www.w3.org/ns/lemon/lime#>
    PREFIX ontolex:  <http://www.w3.org/ns/lemon/ontolex#>
    PREFIX rdf:      <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX skos:     <http://www.w3.org/2004/02/skos/core#>
    PREFIX dbnary:   <http://kaiko.getalp.org/dbnary#>
    PREFIX xsd:      <http://www.w3.org/2001/XMLSchema#>

    SELECT DISTINCT ?lemma ?pos ?definition (SAMPLE(?example_sentence) AS ?example)
    WHERE {{
      ?entry rdf:type ontolex:LexicalEntry ;
             ontolex:canonicalForm/ontolex:writtenRep ?lemma ;
             lexinfo:partOfSpeech ?pos ;
             ontolex:sense ?sense ;
             lime:language '{lemma_lang}' .
      ?sense skos:definition/rdf:value ?definition ;
             dbnary:senseNumber ?sense_number .
      OPTIONAL {{ ?sense skos:example/rdf:value ?example_sentence }} .
      FILTER (?pos in (lexinfo:adjective, lexinfo:adverb, lexinfo:noun,
                       lexinfo:properNoun, lexinfo:verb))
    }}
    GROUP BY ?lemma ?pos ?definition ?sense_number
    ORDER BY ?lemma ?pos xsd:decimal(?sense_number)
    """

    for query_result in store.query(query):  # type: ignore
        lemma = query_result["lemma"].value
        if lemma in lemma_ids:
            lemma_id = lemma_ids[lemma]
            pos = dbnary_to_kaikki_pos(query_result["pos"].value)
            full_def = query_result["definition"].value

            lemma_pos = f"{lemma}_{pos}"
            enabled = False if lemma_pos in enabled_lemma_pos else True
            difficulty = 1
            if difficulty_data:
                if lemma in difficulty_data:
                    difficulty = difficulty_data[lemma]
                else:
                    enabled = False
            else:
                disabled_by_freq, difficulty = freq_to_difficulty(lemma, lemma_lang)
                if disabled_by_freq:
                    enabled = False

            if enabled:
                enabled_lemma_pos.add(lemma_pos)

            if not (full_def.startswith("(") and full_def.endswith(")")):
                short_def = get_short_def(full_def, gloss_lang)
                if len(short_def) == 0:
                    short_def = full_def
                conn.execute(
                    """
             INSERT INTO senses
             (enabled, lemma_id, pos, short_def, full_def, example, difficulty)
             VALUES(?, ?, ?, ?, ?, ?, ?)
             """,
                    (
                        enabled,
                        lemma_id,
                        pos,
                        short_def,
                        full_def,
                        query_result["example"].value
                        if query_result["example"]
                        else None,
                        difficulty,
                    ),
                )


def init_oxigraph_store(gloss_lang: str) -> tuple[Store, bool]:
    if gloss_lang == "hr":
        gloss_lang = "sh"
    store = Store(f"build/ttl/{gloss_lang}_store")
    store.bulk_load(f"build/ttl/{gloss_lang}_dbnary_ontolex.ttl", "text/turtle")
    exolex_path = Path(f"build/ttl/{gloss_lang}_dbnary_exolex_ontolex.ttl")
    if exolex_path.exists():
        store.bulk_load(str(exolex_path), "text/turtle")
    morphology_path = Path(f"build/ttl/{gloss_lang}_dbnary_morphology.ttl")
    if morphology_path.exists():
        store.bulk_load(str(morphology_path), "text/turtle")
    store.optimize()

    return store, morphology_path.exists()


def create_lemmas_db_from_dbnary(
    store: Store, lemma_lang: str, gloss_lang: str, has_morphology: bool
) -> list[Path]:
    db_path = wiktionary_db_path(lemma_lang, gloss_lang)
    if lemma_lang == "hr":
        lemma_lang = "sh"
    if gloss_lang == "hr":
        gloss_lang = "sh"
    conn = init_db(db_path, lemma_lang, False, False)
    lemma_ids = insert_lemmas(store, conn, lemma_lang)
    if has_morphology and lemma_lang == gloss_lang:
        insert_forms(store, conn, lemma_lang, lemma_ids)
    insert_senses(store, conn, lemma_lang, gloss_lang, lemma_ids)
    create_indexes_then_close(conn)
    return [db_path]


def dbnary_to_kaikki_pos(pos: str) -> str:
    pos = pos.rsplit("#", 1)[-1]
    match pos:
        case "adjective":
            return "adj"
        case "adverb":
            return "adv"
        case "noun" | "properNoun":
            return "noun"
        case "verb":
            return "verb"
        case _:
            return "other"


if __name__ == "__main__":
    gloss_lang = "fr"
    store = Store()
    # store.bulk_load(f"ttl/test.ttl", "text/turtle")
    store.bulk_load(f"build/ttl/{gloss_lang}_dbnary_ontolex.ttl", "text/turtle")
    # store.bulk_load(f"ttl/{gloss_lang}_dbnary_morphology.ttl", "text/turtle")
    # store.bulk_load(f"ttl/{gloss_lang}_dbnary_exolex_ontolex.ttl", "text/turtle")
    store.optimize()

    lang_query = """
    prefix lexinfo:  <http://www.lexinfo.net/ontology/2.0/lexinfo#>
    prefix lime:     <http://www.w3.org/ns/lemon/lime#>
    prefix ontolex:  <http://www.w3.org/ns/lemon/ontolex#>
    prefix rdf:      <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    prefix rdfs:     <http://www.w3.org/2000/01/rdf-schema#>
    prefix skos:     <http://www.w3.org/2004/02/skos/core#>
    prefix dcterms:  <http://purl.org/dc/terms/>

    SELECT ?lang (COUNT(DISTINCT ?entry) AS ?count)
    WHERE {
      ?entry rdf:type ontolex:LexicalEntry ;
             lexinfo:partOfSpeech ?pos ;
             ontolex:sense ?sense ;
             lime:language ?lang.
      FILTER(STRLEN(STR(?lang)) = 2)
    }
    GROUP BY ?lang
    """

    # query_data = list(store.query(lang_query))
    # languages = {x["lang"].value: x["count"].value for x in query_data}
    # print(f"{gloss_lang} languages:")
    # with open("data/kaikki_languages.json", encoding="utf-8") as f:
    #     kaikki_languages = json.load(f)
    #     for lang in kaikki_languages.keys():
    #         print(f"{lang}: {languages.get(lang, 0)}")
