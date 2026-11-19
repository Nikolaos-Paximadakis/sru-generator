"""Currency helpers: amounts, rates (direct, inverse, via SEK) and conversion."""

import unittest
from decimal import Decimal

from sru_generator import (
    CurrencyAmount,
    CurrencyConverter,
    CurrencyError,
    ValidationError,
)
from sru_generator.currency import (
    get_currency_converter,
    get_currency_name,
    is_supported_currency,
)


class TestCurrencyAmount(unittest.TestCase):
    def test_to_sek_rounds_to_ore_half_even(self) -> None:
        self.assertEqual(
            CurrencyAmount(Decimal("10.005"), "USD").to_sek(1), Decimal("10.00")
        )
        self.assertEqual(
            CurrencyAmount(Decimal("10.015"), "USD").to_sek(1), Decimal("10.02")
        )
        self.assertEqual(
            CurrencyAmount(Decimal("100"), "USD").to_sek(10.5), Decimal("1050.00")
        )

    def test_invalid_amounts_codes_and_rates(self) -> None:
        with self.assertRaises(ValidationError):
            CurrencyAmount(Decimal("-1"), "USD")
        for code in ("", "US", "USDX"):
            with self.subTest(code=code), self.assertRaises(ValidationError):
                CurrencyAmount(Decimal("1"), code)
        for rate in (0, -2.5):
            with self.subTest(rate=rate), self.assertRaises(CurrencyError):
                CurrencyAmount(Decimal("1"), "USD").to_sek(rate)

    def test_str(self) -> None:
        self.assertEqual(str(CurrencyAmount(Decimal("12.50"), "EUR")), "12.50 EUR")


class TestCurrencyConverter(unittest.TestCase):
    def setUp(self) -> None:
        self.converter = CurrencyConverter()  # a fresh one, not the global

    def test_same_currency_direct_and_inverse(self) -> None:
        self.converter.set_exchange_rate("usd", "sek", 10.0)
        self.assertEqual(self.converter.get_exchange_rate("SEK", "sek"), 1.0)
        self.assertEqual(self.converter.get_exchange_rate("USD", "SEK"), 10.0)
        self.assertEqual(self.converter.get_exchange_rate("SEK", "USD"), 0.1)

    def test_rate_through_the_default_currency(self) -> None:
        self.converter.set_exchange_rate("USD", "SEK", 10.0)
        self.converter.set_exchange_rate("EUR", "SEK", 11.0)
        self.assertAlmostEqual(self.converter.get_exchange_rate("USD", "EUR"), 10 / 11)

    def test_missing_rate_is_an_error_even_via_the_default(self) -> None:
        self.converter.set_exchange_rate("USD", "SEK", 10.0)
        with self.assertRaises(CurrencyError):
            self.converter.get_exchange_rate("USD", "EUR")  # no EUR rate at all
        with self.assertRaises(CurrencyError):
            self.converter.get_exchange_rate("NOK", "SEK")

    def test_non_positive_rates_are_refused(self) -> None:
        for rate in (0, -1.0):
            with self.subTest(rate=rate), self.assertRaises(CurrencyError):
                self.converter.set_exchange_rate("USD", "SEK", rate)

    def test_convert(self) -> None:
        self.converter.set_exchange_rate("USD", "SEK", 10.5)
        self.assertEqual(self.converter.convert(100, "USD", "SEK"), Decimal("1050.00"))
        self.assertEqual(
            self.converter.convert(Decimal("1.234"), "USD", "SEK"), Decimal("12.96")
        )
        self.assertEqual(self.converter.convert_to_sek(2.5, "USD"), Decimal("26.25"))
        with self.assertRaises(ValidationError):
            self.converter.convert(-1, "USD", "SEK")

    def test_load_exchange_rates_skips_the_default_currency(self) -> None:
        self.converter.load_exchange_rates({"USD": 10.0, "sek": 1.0, "EUR": 11.0})
        self.assertEqual(
            self.converter.exchange_rates, {"USD_SEK": 10.0, "EUR_SEK": 11.0}
        )


class TestCurrencyLookups(unittest.TestCase):
    def test_global_converter_and_names(self) -> None:
        self.assertIs(get_currency_converter(), get_currency_converter())
        self.assertEqual(get_currency_name("usd"), "US Dollar")
        self.assertIsNone(get_currency_name("XYZ"))
        self.assertTrue(is_supported_currency("sek"))
        self.assertFalse(is_supported_currency("XYZ"))


if __name__ == "__main__":
    unittest.main()
