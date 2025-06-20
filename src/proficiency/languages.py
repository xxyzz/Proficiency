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
    "hi",  # Hindi
    "hr",  # Serbo-Croatian
    "id",  # Indonesian
    "it",  # Italian
    "ja",  # Japanese
    "ko",  # Korean
    "lt",  # Lithuanian
    "mk",  # Macedonian
    "ms",  # Malay
    "nl",  # Dutch
    "nb",  # Norwegian Bokmål
    "pl",  # Polish
    "pt",  # Portuguese
    "ro",  # Romanian
    "ru",  # Russian
    "sl",  # Slovene
    "sv",  # Swedish
    "th",  # Thai
    "uk",  # Ukrainian
    "zh",  # Chinese
}

KAIKKI_GLOSS_LANGS = {
    "en",
    "fr",
    "zh",
    "ru",
    "de",
    "es",
    "ja",
    "pl",
    "nl",
    "ko",
    "pt",
    "it",
    "el",
    "th",
}

# key is translated word language code, value is source Wiktionary edition codes
KAIKKI_TRANSLATED_GLOSS_LANGS: dict[str, list[str]] = {
    "he": ["en"],  # English to Hebrew
}

WSD_LANGS = {
    "en-en",
    "de-en",
    "es-en",
    "fr-en",
    "zh-en",
    "ja-en",
    "ko-en",
    "ru-en",
    "fr-fr",
    "en-fr",
    "de-de",
    "en-de",
}

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
    "nb": {"has_exolex": False, "has_morphology": False},
    "pl": {"has_exolex": False, "has_morphology": False},
    "pt": {"has_exolex": False, "has_morphology": False},
    "ru": {"has_exolex": False, "has_morphology": False},
    "sv": {"has_exolex": False, "has_morphology": True},
    "tr": {"has_exolex": False, "has_morphology": False},
    "zh": {"has_exolex": False, "has_morphology": False},
}
