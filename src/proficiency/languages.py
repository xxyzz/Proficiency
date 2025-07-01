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

# enabled lemma language should have at least 1000 lemmas
KAIKKI_GLOSS_LANGS = {
    "en": KAIKKI_LEMMA_LANGS,
    "fr": KAIKKI_LEMMA_LANGS - {"he", "hi", "mk", "th"},
    "zh": KAIKKI_LEMMA_LANGS,
    "ru": KAIKKI_LEMMA_LANGS,
    "de": KAIKKI_LEMMA_LANGS
    - {"th", "da", "id", "nb", "ja", "zh", "ko", "el", "he", "ms", "hi"},
    "es": {
        "ja",
        "pl",
        "es",
        "en",
        "fr",
        "it",
        "ca",
        "nl",
        "sv",
        "he",
        "pt",
        "ro",
        "de",
    },
    "ja": KAIKKI_LEMMA_LANGS - {"ms", "hi", "sl", "el", "id"},
    "pl": KAIKKI_LEMMA_LANGS - {"ms"},
    "nl": {
        "pt",
        "it",
        "sv",
        "ru",
        "de",
        "en",
        "da",
        "id",
        "es",
        "ja",
        "pl",
        "nl",
        "fr",
        "ca",
        "nb",
        "cs",
    },
    "ko": {"hr", "da", "ko", "de", "ja", "zh", "fr", "sl", "en"},
    "pt": {
        "sv",
        "nb",
        "cs",
        "de",
        "ro",
        "en",
        "it",
        "da",
        "nl",
        "ca",
        "fi",
        "pl",
        "fr",
        "pt",
        "ru",
        "zh",
        "el",
        "ja",
        "es",
    },
    "it": {
        "it",
        "fi",
        "sv",
        "fr",
        "ja",
        "de",
        "pt",
        "pl",
        "ru",
        "nl",
        "en",
        "ko",
        "es",
    },
    "el": {
        "de",
        "nl",
        "en",
        "pl",
        "it",
        "fi",
        "pt",
        "ro",
        "fr",
        "ru",
        "sv",
        "es",
        "el",
    },
    "th": {"ja", "de", "en", "es", "it", "hi", "zh", "th", "fr", "fi"},
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
