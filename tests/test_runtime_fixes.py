"""Bugs found while hardening the package for strict typing (one test class per fix)."""

import unittest
import warnings
from collections import UserDict
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from sru_generator import (
    ConfigurationError,
    DataFormatError,
    FileOperationError,
    SRUConfig,
    ValidationError,
    build_blanketter_sru,
    create_config,
    format_trade_item_sru,
    generate_sru_header,
    generate_sru_trade_content,
    read_crypto_sru_content,
    round_k4_cost_basis,
    round_k4_quantity,
    round_k4_sale_price,
    to_decimal,
    validate_personal_info,
    validate_trade_data,
)
from sru_generator.models import CryptoSRUGroup, PersonalInfo, SRUTradeRow

ME: PersonalInfo = {
    "personal_number": "198112189876",
    "full_name": "Test Person",
    "postal_code": "11122",
    "city_name": "Stockholm",
}


class TestFloatNoiseDoesNotMoveAKrona(unittest.TestCase):
    """A float that is a whole krona plus binary noise must round as that krona."""

    def test_cost_basis(self) -> None:
        noisy = 0.1 * 3 * 1000  # 300.00000000000006
        self.assertEqual(round_k4_cost_basis(noisy), 300)
        self.assertEqual(round_k4_cost_basis(Decimal("300.01")), 301)  # real öre: up

    def test_sale_price(self) -> None:
        noisy = 0.7 * 3 * 100  # 209.99999999999997
        self.assertEqual(round_k4_sale_price(noisy), 210)
        self.assertEqual(round_k4_sale_price(Decimal("209.99")), 209)  # real öre: down

    def test_quantity(self) -> None:
        self.assertEqual(round_k4_quantity(2.0000000000000004), 2)
        self.assertEqual(round_k4_quantity("0.001"), 1)

    def test_noise_is_removed_at_any_magnitude(self) -> None:
        noisy = 123456789.1 * 3  # 370370367.30000001
        self.assertEqual(to_decimal(noisy), Decimal("370370367.3"))

    def test_a_whole_file(self) -> None:
        row: SRUTradeRow = {
            "quantity": 1,
            "stock": "A",
            "net value": 0.7 * 3 * 100,
            "total net value of purchase": 0.1 * 3 * 1000,
        }
        content = build_blanketter_sru([row], ME, 2025)
        self.assertIn("#UPPGIFT 3102 210\n", content)
        self.assertIn("#UPPGIFT 3103 300\n", content)
        self.assertIn("#UPPGIFT 3105 90\n", content)  # förlust, row 1

    def test_validation_keeps_the_noise_out_too(self) -> None:
        (row,) = validate_trade_data(
            [_row(**{"total net value of purchase": 0.1 * 3e3})]
        )
        self.assertEqual(row["total net value of purchase"], Decimal("300"))


class TestExactInputFollowsTheRuleToTheLetter(unittest.TestCase):
    """Only floats are cleaned. Exact input below an öre still rounds down/up."""

    def test_sub_ore_decimals(self) -> None:
        self.assertEqual(round_k4_sale_price(Decimal("1.999")), 1)
        self.assertEqual(round_k4_cost_basis(Decimal("100.001")), 101)
        self.assertEqual(round_k4_cost_basis("300.004"), 301)

    def test_tiny_quantities_still_count(self) -> None:
        self.assertEqual(round_k4_quantity(Decimal("0.000000001")), 1)
        self.assertEqual(round_k4_quantity(1e-9), 1)

    def test_a_genuine_float_with_sub_ore_digits(self) -> None:
        self.assertEqual(round_k4_sale_price(1.999), 1)
        self.assertEqual(round_k4_cost_basis(100.001), 101)


def _row(**changes: object) -> dict[str, object]:
    row: dict[str, object] = {
        "quantity": 1,
        "stock": "A",
        "net value": 100,
        "total net value of purchase": 50,
    }
    row.update(changes)
    return row


def _valid_row(stock: str = "A") -> SRUTradeRow:
    return {
        "quantity": 1,
        "stock": stock,
        "net value": 100,
        "total net value of purchase": 50,
    }


class TestValidatorHoles(unittest.TestCase):
    def test_whitespace_only_text_is_refused(self) -> None:
        for field in ("full_name", "city_name"):
            with self.subTest(field=field):
                with self.assertRaises(ValidationError):
                    validate_personal_info({**ME, field: "   "})
        with self.assertRaises(ValidationError):
            validate_trade_data([_row(stock="  ")])

    def test_surrounding_whitespace_is_still_stripped(self) -> None:
        result = validate_personal_info({**ME, "full_name": "  Test Person  "})
        self.assertEqual(result["full_name"], "Test Person")

    def test_non_finite_and_boolean_numbers_raise_validation_error(self) -> None:
        cases = {
            "NaN sale": _row(**{"net value": "NaN"}),
            "Infinity cost": _row(**{"total net value of purchase": "Infinity"}),
            "float nan profit/loss": _row(**{"profit/loss": float("nan")}),
            "sNaN profit/loss": _row(**{"profit/loss": "sNaN"}),
            "True quantity": _row(quantity=True),
            "False sale": _row(**{"net value": False}),
        }
        for label, row in cases.items():
            with self.subTest(label):
                with self.assertRaises(ValidationError):
                    validate_trade_data([row])


class TestPageParameters(unittest.TestCase):
    def test_year_must_be_a_four_digit_income_year(self) -> None:
        for year in (25, -1, 20251, 1999, True):
            with self.subTest(year=year):
                with self.assertRaises(ValidationError):
                    build_blanketter_sru([_valid_row()], ME, year)
        self.assertIn(
            "#BLANKETT K4-2025P4\n", build_blanketter_sru([_valid_row()], ME, 2025)
        )

    def test_items_per_group_cannot_exceed_the_nine_rows_of_section_a(self) -> None:
        rows = [_valid_row(f"S{i}") for i in range(12)]
        for size in (0, 10, 12):
            with self.subTest(items_per_group=size):
                with self.assertRaises(ValidationError):
                    build_blanketter_sru(rows, ME, 2025, items_per_group=size)
        content = build_blanketter_sru(rows, ME, 2025, items_per_group=5)
        self.assertEqual(content.count("#BLANKETT "), 3)
        self.assertNotIn("#UPPGIFT 3150", content)


def _page(number: int, *lines: str) -> CryptoSRUGroup:
    return {"group_number": number, "uppgifter": list(lines) or ["#UPPGIFT 3410 1"]}


class TestCryptoPagesAreChecked(unittest.TestCase):
    def test_section_d_lines_are_merged(self) -> None:
        content = build_blanketter_sru(
            [_valid_row()],
            ME,
            2025,
            crypto_groups=[_page(1, "#UPPGIFT 3410 0.5", "#UPPGIFT 3411 Bitcoin")],
        )
        self.assertIn("#UPPGIFT 3410 0.5\n#UPPGIFT 3411 Bitcoin\n", content)

    def test_lines_that_are_not_section_d_are_refused(self) -> None:
        bad = ("#UPPGIFT 3100 999", "#UPPGIFT 7014 2", "garbage", "#UPPGIFT 3411")
        for line in bad:
            with self.subTest(line=line):
                with self.assertRaises(ValidationError):
                    build_blanketter_sru(
                        [_valid_row()], ME, 2025, crypto_groups=[_page(1, line)]
                    )

    def test_pages_must_be_numbered_one_to_n(self) -> None:
        for numbers in ((1, 1), (1, 3), (0,), (2,)):
            with self.subTest(numbers=numbers):
                with self.assertRaises(ValidationError):
                    build_blanketter_sru(
                        [], ME, 2025, crypto_groups=[_page(n) for n in numbers]
                    )

    def test_an_unreadable_crypto_file_is_an_error_not_an_empty_list(self) -> None:
        with TemporaryDirectory() as tmp:
            with self.assertRaises(FileOperationError):
                read_crypto_sru_content(str(Path(tmp)))  # a directory, not a file
            self.assertEqual(read_crypto_sru_content(str(Path(tmp) / "absent.sru")), [])


class TestTotalsOnlyCountWrittenRows(unittest.TestCase):
    def test_a_row_that_cannot_be_formatted_is_not_in_the_totals(self) -> None:
        rows = [_row(), _row(quantity="not a number", **{"net value": 1000})]
        content = generate_sru_trade_content(rows, "Test Person", "198112189876", 2025)
        self.assertNotIn("#UPPGIFT 3110", content)  # second row skipped...
        self.assertIn("#UPPGIFT 3300 100\n", content)  # ...and not in the total


_PAGE_HEAD = "#BLANKETT K4-2025P4\n#IDENTITET 198112189876 20260101 120000\n"


class TestCryptoFilesFromOtherTools(unittest.TestCase):
    def read(self, text: str) -> list[CryptoSRUGroup]:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "crypto.sru"
            path.write_text(text, encoding="iso-8859-1")
            return read_crypto_sru_content(str(path))

    def test_7014_at_the_end_of_the_page(self) -> None:
        """K4Skatt, k4sru and csv_to_sru write 7014 last; this used to read as []."""
        text = (
            _PAGE_HEAD + "#UPPGIFT 3410 1\n#UPPGIFT 3411 Bitcoin\n#UPPGIFT 7014 1\n"
            "#BLANKETTSLUT\n#FIL_SLUT\n"
        )
        self.assertEqual(
            self.read(text),
            [
                {
                    "group_number": 1,
                    "uppgifter": ["#UPPGIFT 3410 1", "#UPPGIFT 3411 Bitcoin"],
                }
            ],
        )

    def test_an_unreadable_page_number_is_an_error(self) -> None:
        """Page 2 with '7014 BAD' used to vanish while page 1 passed every check."""
        text = (
            _PAGE_HEAD
            + "#UPPGIFT 7014 1\n#UPPGIFT 3410 1\n#BLANKETTSLUT\n"
            + _PAGE_HEAD
            + "#UPPGIFT 7014 BAD\n#UPPGIFT 3410 2\n#BLANKETTSLUT\n#FIL_SLUT\n"
        )
        with self.assertRaises(DataFormatError):
            self.read(text)

    def test_pages_without_7014_are_numbered_in_file_order(self) -> None:
        text = (
            _PAGE_HEAD
            + "#UPPGIFT 3410 1\n#BLANKETTSLUT\n"
            + _PAGE_HEAD
            + "#UPPGIFT 3410 2\n#BLANKETTSLUT\n#FIL_SLUT\n"
        )
        self.assertEqual([g["group_number"] for g in self.read(text)], [1, 2])


class TestLowerLevelWritersAreCheckedToo(unittest.TestCase):
    def test_header_year(self) -> None:
        with self.assertRaises(ValidationError):
            generate_sru_header(25, "198112189876", "Test Person")
        self.assertTrue(
            generate_sru_header(2025, "198112189876", "A").startswith(
                "#BLANKETT K4-2025P4"
            )
        )

    def test_row_index(self) -> None:
        for index in (-1, 9, 12, 0.5, "1", True):
            with self.subTest(index=index):
                with self.assertRaises(ValidationError):
                    format_trade_item_sru(_valid_row(), index, 0)  # type: ignore[arg-type]  # untyped callers
        self.assertIn("#UPPGIFT 3180 1\n", format_trade_item_sru(_valid_row(), 8, 0))


class TestSRUConfigReviewFixes(unittest.TestCase):
    def test_copy_does_not_repeat_the_warning(self) -> None:
        with self.assertWarns(DeprecationWarning):
            config = create_config(validation_level="strict")
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            copied = config.copy()
        self.assertEqual(copied.validation_level, config.validation_level)

    def test_bad_values_are_configuration_errors(self) -> None:
        cases: list[dict[str, object]] = [
            {"exchange_rates": []},
            {"exchange_rates": {"USD_SEK": -1}},
            {"exchange_rates": {"USD_SEK": "10"}},
            {"character_converter": ["greek"]},
            {"default_currency": 3},
            {"no_such_option": True},
            {"log_level": []},
            {"batch_size": "9"},
            {"exchange_rates": {"USD_SEK": float("inf")}},
        ]
        for options in cases:
            with self.subTest(options=options):
                with self.assertRaises(ConfigurationError):
                    SRUConfig.from_dict(dict(options))
        with self.assertRaises(ConfigurationError):
            create_config(validation_level="bogus")


class TestAnnotatedInputTypesAreAccepted(unittest.TestCase):
    """The signatures say Sequence/Mapping; the runtime used to demand list/dict."""

    def test_a_tuple_of_rows_and_a_user_dict(self) -> None:
        (row,) = validate_trade_data((_row(),))
        self.assertEqual(row["net value"], Decimal("100"))
        info = validate_personal_info(UserDict(ME))
        self.assertEqual(info["full_name"], "Test Person")

    def test_a_string_is_still_not_a_list_of_rows(self) -> None:
        with self.assertRaises(DataFormatError):
            validate_trade_data("not rows")  # type: ignore[arg-type]  # the point of the test


if __name__ == "__main__":
    unittest.main()
