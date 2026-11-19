"""ISO-8859-1 output, working character converters, and fractional quantities."""

import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from sru_generator import (
    DataFormatError,
    ValidationError,
    build_blanketter_sru,
    decode_sru_bytes,
    encode_sru_content,
    encode_sru_text,
    read_crypto_sru_content,
    round_k4_quantity,
    validate_personal_info,
    validate_trade_data,
    write_sru_file,
)
from sru_generator.character_converters import get_character_converter
from sru_generator.models import Amount, PersonalInfo, SRUTradeRow

PERSONAL_INFO: PersonalInfo = {
    "personal_number": "198112189876",
    "full_name": "Åsa Öberg",
    "postal_code": "11122",
    "city_name": "Göteborg",
}


def trade(quantity: Amount, stock: str = "ABB") -> SRUTradeRow:
    return {
        "quantity": quantity,
        "stock": stock,
        "net value": "1000.50",
        "total net value of purchase": "400.10",
    }


class TestEncoding(unittest.TestCase):
    def test_swedish_letters_are_written_as_single_latin1_bytes(self) -> None:
        self.assertEqual(encode_sru_text("Åäö"), b"\xc5\xe4\xf6")
        self.assertEqual(encode_sru_content("Åäö"), b"\xc5\xe4\xf6")

    def test_characters_outside_latin1_are_refused_and_named(self) -> None:
        with self.assertRaises(DataFormatError) as caught:
            encode_sru_text("Ελλάδα €")
        message = str(caught.exception)
        self.assertIn("U+20AC", message)
        self.assertIn("character_converter", message)

    def test_write_sru_file_writes_latin1(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "out" / "INFO.SRU"
            self.assertTrue(write_sru_file(str(path), "#NAMN Åsa Öberg\n"))
            self.assertEqual(path.read_bytes(), b"#NAMN \xc5sa \xd6berg\n")

    @unittest.skipIf(sys.platform == "win32", "POSIX permissions")
    def test_write_sru_file_is_private_to_its_owner(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "BLANKETTER.SRU"
            path.write_text("old")
            path.chmod(0o644)
            self.assertTrue(write_sru_file(str(path), "#FIL_SLUT\n"))
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(path.read_bytes(), b"#FIL_SLUT\n")

    def test_write_sru_file_accepts_a_bare_file_name(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "INFO.SRU"
            self.assertTrue(write_sru_file(str(path), "#FIL_SLUT\n"))

    def test_write_sru_file_refuses_unencodable_content(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "INFO.SRU"
            self.assertFalse(write_sru_file(str(path), "#NAMN Ελλάδα\n"))
            self.assertFalse(path.exists())

    def test_decode_prefers_utf8_and_falls_back_to_latin1(self) -> None:
        self.assertEqual(decode_sru_bytes("Åsa".encode()), "Åsa")
        self.assertEqual(decode_sru_bytes("Åsa".encode("iso-8859-1")), "Åsa")

    def test_crypto_file_is_read_in_either_encoding_and_with_crlf(self) -> None:
        text = (
            "#BLANKETT K4-2024P4\r\n#IDENTITET 198112189876 20250101 120000\r\n"
            "#NAMN Åsa\r\n#UPPGIFT 7014 1\r\n#UPPGIFT 3410 1\r\n"
            "#UPPGIFT 3411 Bitcoin\r\n#BLANKETTSLUT\r\n#FIL_SLUT\r\n"
        )
        for encoding in ("utf-8", "iso-8859-1"):
            with self.subTest(encoding=encoding), TemporaryDirectory() as tmp:
                path = Path(tmp) / "crypto.sru"
                path.write_bytes(text.encode(encoding))
                groups = read_crypto_sru_content(str(path))
                self.assertEqual(
                    groups,
                    [
                        {
                            "group_number": 1,
                            "uppgifter": ["#UPPGIFT 3410 1", "#UPPGIFT 3411 Bitcoin"],
                        }
                    ],
                )


class TestCharacterConverters(unittest.TestCase):
    def test_converters_really_convert(self) -> None:
        self.assertEqual(get_character_converter("swedish")("Åäö"), "Aao")
        self.assertEqual(get_character_converter("german")("Größe"), "Groesse")
        self.assertEqual(
            get_character_converter("french")("cœur Œuvre æ Æ"), "coeur Oeuvre ae Ae"
        )
        self.assertEqual(get_character_converter("greek")("Ελλάδα"), "Ellada")
        self.assertEqual(get_character_converter("greek")("Άλφα Ώρα"), "Alfa Ora")

    def test_unknown_converter_is_an_error(self) -> None:
        with self.assertRaises(ValueError):
            get_character_converter("klingon")

    def test_greek_stock_name_becomes_encodable(self) -> None:
        content = build_blanketter_sru(
            [trade(1, stock="Τράπεζα Πειραιώς")],
            PERSONAL_INFO,
            2024,
            character_converter=get_character_converter("greek"),
        )
        self.assertIn("#UPPGIFT 3101 Trapeza Peiraios", content)
        encode_sru_text(content)  # does not raise

    def test_importing_the_package_leaves_sys_path_alone(self) -> None:
        code = (
            "import sys; before = list(sys.path); import sru_generator; "
            "assert sys.path == before, set(sys.path) ^ set(before)"
        )
        # Fixed argv: this interpreter and a literal snippet, no outside input.
        subprocess.run([sys.executable, "-c", code], check=True)  # noqa: S603


class TestFractionalQuantity(unittest.TestCase):
    def test_round_k4_quantity_rounds_up(self) -> None:
        self.assertEqual(round_k4_quantity("0.25"), 1)
        self.assertEqual(round_k4_quantity(1.5), 2)
        self.assertEqual(round_k4_quantity(3), 3)
        self.assertEqual(round_k4_quantity("3.000"), 3)
        self.assertEqual(round_k4_quantity(0), 0)

    def test_fractional_quantities_are_accepted_and_written_rounded_up(self) -> None:
        for quantity, written in ((1.5, 2), ("1.5", 2), (0.25, 1), ("100", 100)):
            with self.subTest(quantity=quantity):
                content = build_blanketter_sru([trade(quantity)], PERSONAL_INFO, 2024)
                self.assertIn(f"#UPPGIFT 3100 {written}\n", content)

    def test_negative_quantity_is_still_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            validate_trade_data([trade(-1)])


class TestPersonalNumberAndText(unittest.TestCase):
    def info(self, **changes: str) -> dict[str, object]:
        return {**PERSONAL_INFO, **changes}

    def test_twelve_digits_with_a_correct_check_digit_pass(self) -> None:
        for number in ("198112189876", "19811218-9876", " 198112189876 "):
            with self.subTest(number=number):
                result = validate_personal_info(self.info(personal_number=number))
                self.assertEqual(result["personal_number"], "198112189876")

    def test_refused_numbers_say_why(self) -> None:
        cases = {
            "1212121212": "12 digits",
            "121212-1212": "12 digits",
            "198112189875": "check digit",
            "19811218+9876": "digits only",
            "1981 1218 9876": "digits only",
        }
        for number, reason in cases.items():
            with self.subTest(number=number):
                with self.assertRaises(ValidationError) as caught:
                    validate_personal_info(self.info(personal_number=number))
                self.assertIn(reason, str(caught.exception))
                self.assertNotIn(number.strip(), str(caught.exception))

    def test_hash_and_line_breaks_are_refused_in_text_values(self) -> None:
        for field, value in (
            ("full_name", "Test #1"),
            ("full_name", "Test\nPerson"),
            ("city_name", "Stock\rholm"),
        ):
            with self.subTest(field=field, value=value):
                with self.assertRaises(ValidationError):
                    validate_personal_info(self.info(**{field: value}))
        for stock in ("Class #2", "ABB\n#UPPGIFT 3102 1"):
            with self.subTest(stock=stock):
                with self.assertRaises(ValidationError):
                    validate_trade_data([trade(1, stock=stock)])


if __name__ == "__main__":
    unittest.main()
