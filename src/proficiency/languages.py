from typing import Any

KAIKKI_LEMMA_LANGS = {
    "ca",  # Catalan
    "cs",  # Czech
    "da",  # Danish
    "de",  # German
    "el",  # Greek
    "en",  # English
    "es",  # Spanish
    "fi",  # Finnish
    "fr",  # French
    "he",  # Hebrew
    "hr",  # Serbo-Croatian
    "it",  # Italian
    "ja",  # Japanese
    "ko",  # Korean
    "lt",  # Lithuanian
    "mk",  # Macedonian
    "nl",  # Dutch
    "no",  # Norwegian Bokmål
    "pl",  # Polish
    "pt",  # Portuguese
    "ro",  # Romanian
    "ru",  # Russian
    "sl",  # Slovene
    "sv",  # Swedish
    "uk",  # Ukrainian
    "zh",  # Chinese
}

KAIKKI_GLOSS_LANGS = {"en", "fr", "zh"}

# has_exolex: has lemmas in other languages
# has_morphology: has inflection forms data
DBNARY_LANGS: dict[str, Any] = {
    "bg": {"has_exolex": False, "has_morphology": False},
    "de": {"has_exolex": False, "has_morphology": True},
    "el": {
        "has_exolex": True,
        "has_morphology": False,
        "lemma_languages": {"el", "en", "fr"},
    },
    "en": {"has_exolex": True, "has_morphology": True},
    "es": {
        "has_exolex": True,
        "has_morphology": False,
        "lemma_languages": {"en", "es"},
    },
    "fi": {"has_exolex": False, "has_morphology": False},
    "fr": {"has_exolex": True, "has_morphology": True},
    "hr": {"has_exolex": False, "has_morphology": True},
    "id": {"has_exolex": False, "has_morphology": False},
    "it": {
        "has_exolex": True,
        "has_morphology": False,
        "lemma_languages": {"en", "it"},
    },
    "ja": {"has_exolex": False, "has_morphology": False},
    "ku": {"has_exolex": False, "has_morphology": False},
    "la": {"has_exolex": True, "has_morphology": False},
    "lt": {"has_exolex": False, "has_morphology": False},
    "mg": {"has_exolex": True, "has_morphology": False},
    "nl": {"has_exolex": False, "has_morphology": False},
    "no": {"has_exolex": False, "has_morphology": False},
    "pl": {"has_exolex": False, "has_morphology": False},
    "pt": {"has_exolex": False, "has_morphology": False},
    "ru": {"has_exolex": False, "has_morphology": False},
    "sv": {"has_exolex": False, "has_morphology": True},
    "tr": {"has_exolex": False, "has_morphology": False},
    "zh": {"has_exolex": False, "has_morphology": False},
}
