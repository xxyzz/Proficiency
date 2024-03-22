from unittest import TestCase

from proficiency.extract_kaikki import Sense, get_translated_senses


class TestTranslation(TestCase):
    def test_distinct_words(self) -> None:
        self.assertEqual(
            get_translated_senses(
                "he",
                {
                    "translations": [
                        {"code": "he", "word": "חיסרון", "sense": "weakness"},
                        {
                            "code": "he",
                            "word": "חיסרון",
                            "sense": "setback or handicap",
                        },
                    ]
                },
                True,
            ),
            [Sense(enabled=True, short_gloss="חיסרון", gloss="חיסרון")],
        )
