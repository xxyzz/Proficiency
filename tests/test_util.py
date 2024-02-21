from unittest import TestCase


class TestUtil(TestCase):
    def test_nested_parentheses(self) -> None:
        from proficiency.util import remove_parentheses

        self.assertEqual(remove_parentheses("a (b (c)) d"), "a d")
