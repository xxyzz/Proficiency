from unittest import TestCase

from proficiency.util import get_short_def


class TestUtil(TestCase):
    def test_nested_parentheses(self) -> None:
        # https://en.wiktionary.org/wiki/cadet_house
        self.assertEqual(
            get_short_def(
                "Synonym of cadet branch (“house (dynasty) descended from one of "
                "the patriarch's younger sons”)",
                "en",
            ),
            "Synonym of cadet branch",
        )

    def test_get_short_def_stop(self) -> None:
        # https://en.wiktionary.org/wiki/jack_jumper
        self.assertEqual(
            get_short_def(
                "Any of various small species of ant of the genus Myrmecia, "
                "often capable of jumping and having a painful sting; a jumper. "
                "(Also used attributively.)",
                "en",
            ),
            "a jumper",
        )

    def test_mastodonian(self) -> None:
        # https://en.wiktionary.org/wiki/mastodonian
        self.assertEqual(
            get_short_def(
                "Of, related to, or characteristic of a mastodon; large; powerful.",
                "en",
            ),
            "large",
        )
