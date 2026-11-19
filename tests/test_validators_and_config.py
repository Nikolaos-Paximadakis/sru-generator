"""Validator classes and SRUConfig paths not exercised by the main suites."""

import unittest
from decimal import Decimal
from typing import ClassVar

from sru_generator import (
    ConfigurationError,
    DataFormatError,
    SRUConfig,
    TradeDataValidator,
    ValidationError,
    create_config,
)
from sru_generator.validators import (
    CurrencyValidator,
    DecimalValidator,
    IntegerValidator,
    PersonalNumberValidator,
    StringValidator,
    Validator,
    create_custom_validator,
    validate_personal_info,
)


class TestBaseValidator(unittest.TestCase):
    def test_required_and_optional_missing_values(self) -> None:
        with self.assertRaises(ValidationError):
            StringValidator("name").validate(None)
        self.assertIsNone(StringValidator("name", required=False).validate(None))

    def test_the_base_class_has_no_check_of_its_own(self) -> None:
        with self.assertRaises(NotImplementedError):
            Validator[str]("name").validate("x")


class TestStringValidator(unittest.TestCase):
    def test_type_length_and_pattern(self) -> None:
        validator = StringValidator("code", max_length=3, pattern=r"^\d+$")
        self.assertEqual(validator.validate(" 12 "), "12")
        for bad in (12, "1234", "ab"):
            with self.subTest(bad=bad), self.assertRaises(ValidationError):
                validator.validate(bad)

    def test_personal_number_must_be_a_string(self) -> None:
        with self.assertRaises(ValidationError):
            PersonalNumberValidator("personal_number").validate(198112189876)


class TestIntegerValidator(unittest.TestCase):
    def test_accepts_ints_and_digit_strings_within_bounds(self) -> None:
        validator = IntegerValidator("n", min_value=1, max_value=9)
        self.assertEqual(validator.validate(5), 5)
        self.assertEqual(validator.validate("7"), 7)

    def test_refuses_everything_else(self) -> None:
        validator = IntegerValidator("n", min_value=1, max_value=9)
        for bad in (True, "seven", 2.5, 0, 10):
            with self.subTest(bad=bad), self.assertRaises(ValidationError):
                validator.validate(bad)


class TestDecimalAndCurrencyValidators(unittest.TestCase):
    def test_decimal_validator(self) -> None:
        validator = DecimalValidator("x", max_value=Decimal("10"))
        self.assertEqual(validator.validate("1.5"), Decimal("1.5"))
        for bad in ("abc", [1], Decimal("11")):
            with self.subTest(bad=bad), self.assertRaises(ValidationError):
                validator.validate(bad)

    def test_currency_validator(self) -> None:
        validator = CurrencyValidator("currency")
        self.assertEqual(validator.validate("usd"), "USD")
        for bad in (978, "XYZ"):
            with self.subTest(bad=bad), self.assertRaises(ValidationError):
                validator.validate(bad)


class TestTradeAndPersonalShapes(unittest.TestCase):
    ROW: ClassVar[dict[str, object]] = {
        "quantity": 1,
        "stock": "A",
        "net value": 100,
        "total net value of purchase": 50,
    }

    def test_non_mapping_inputs(self) -> None:
        with self.assertRaises(DataFormatError):
            TradeDataValidator().validate_trade_item("row")  # type: ignore[arg-type]  # deliberate
        with self.assertRaises(DataFormatError):
            validate_personal_info(["not", "a", "dict"])  # type: ignore[arg-type]  # deliberate

    def test_a_replaced_validator_returning_the_wrong_type_is_caught(self) -> None:
        validator = TradeDataValidator()
        validator.validators["stock"] = create_custom_validator(
            "stock", lambda v, c: 42
        )
        with self.assertRaises(ValidationError):
            validator.validate_trade_item(self.ROW)

    def test_a_lenient_currency_validator_still_meets_the_business_rule(self) -> None:
        validator = TradeDataValidator()
        validator.validators["currency"] = create_custom_validator(
            "currency", lambda value, context: str(value)
        )
        with self.assertRaises(ValidationError):  # BusinessRuleError, wrapped
            validator.validate_trade_data([{**self.ROW, "currency": "XYZ"}])

    def test_create_custom_validator(self) -> None:
        doubled = create_custom_validator(
            "n", lambda value, context: 2 * int(str(value))
        )
        self.assertEqual(doubled.validate("21"), 42)


class TestSRUConfigPaths(unittest.TestCase):
    def test_limits_of_fields_without_effect(self) -> None:
        for options in (
            {"decimal_places": 11},
            {"batch_size": 0},
            {"cache_size": 0},
            {"log_level": "LOUD"},
        ):
            with self.subTest(options=options), self.assertRaises(ConfigurationError):
                SRUConfig.from_dict(options)

    def test_exchange_rate_lookups(self) -> None:
        config = create_config(exchange_rates={"USD_SEK": 10.0, "EUR_SEK": 11.0})
        self.assertEqual(config.get_exchange_rate("SEK", "sek"), 1.0)
        self.assertEqual(config.get_exchange_rate("SEK", "USD"), 0.1)
        self.assertAlmostEqual(config.get_exchange_rate("USD", "EUR"), 10 / 11)
        with self.assertRaises(ConfigurationError):
            config.get_exchange_rate("NOK", "USD")
        with self.assertRaises(ConfigurationError):
            config.set_exchange_rate("USD", "usd", 1.0)


if __name__ == "__main__":
    unittest.main()
