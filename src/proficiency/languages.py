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
