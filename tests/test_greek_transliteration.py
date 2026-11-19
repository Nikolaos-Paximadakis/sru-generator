"""The built-in greek converter: η as "i" and digraphs capitalised by context."""

import unittest

from sru_generator.character_converters import (
    convert_greek_characters_to_english as greek,
)


class TestGreekTransliteration(unittest.TestCase):
    def test_place_names(self) -> None:
        cases = {
            "Θεσσαλονίκη": "Thessaloniki",
            "Χανιά": "Chania",
            "Ηράκλειο": "Irakleio",
            "Ψυχικό": "Psychiko",
            "Αθήνα": "Athina",
        }
        for greek_text, latin in cases.items():
            with self.subTest(greek_text):
                self.assertEqual(greek(greek_text), latin)

    def test_capitals_stay_capitals(self) -> None:
        self.assertEqual(greek("ΘΕΣΣΑΛΟΝΙΚΗ"), "THESSALONIKI")
        self.assertEqual(greek("ΑΘΗΝΑ"), "ATHINA")
        self.assertEqual(greek("ΧΑΝΙΑ ΨΥΧΗ"), "CHANIA PSYCHI")
        self.assertEqual(greek("ΤΡΑΠΕΖΑ ΠΕΙΡΑΙΩΣ"), "TRAPEZA PEIRAIOS")

    def test_digraph_at_the_end_of_a_capital_word(self) -> None:
        self.assertEqual(greek("ΚΑΛΥΨ"), "KALYPS")

    def test_a_lone_capital_digraph_is_title_case(self) -> None:
        self.assertEqual(greek("Θ"), "Th")
        self.assertEqual(greek("Χ. Παπαδόπουλος"), "Ch. Papadopoulos")

    def test_omicron_upsilon_is_ou(self) -> None:
        self.assertEqual(greek("Παπαδόπουλος"), "Papadopoulos")
        self.assertEqual(greek("ΟΥΡΑΝΟΥΠΟΛΗ"), "OURANOUPOLI")
        self.assertEqual(greek("Ούζο"), "Ouzo")
        self.assertEqual(greek("Υδρα κύμα"), "Ydra kyma")  # υ alone stays y

    def test_eta_with_and_without_tonos(self) -> None:
        self.assertEqual(greek("ήη ΉΗ"), "ii II")

    def test_text_that_is_not_greek_is_unchanged(self) -> None:
        self.assertEqual(greek("Åsa Öberg 123 ABB"), "Åsa Öberg 123 ABB")

    def test_existing_examples_still_hold(self) -> None:
        self.assertEqual(greek("Ελλάδα"), "Ellada")
        self.assertEqual(greek("Άλφα Ώρα"), "Alfa Ora")
        self.assertEqual(greek("Τράπεζα Πειραιώς"), "Trapeza Peiraios")


if __name__ == "__main__":
    unittest.main()
