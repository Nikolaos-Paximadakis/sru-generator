"""
Tests for enhanced SRU Generator features.
"""

import sys
import unittest
import warnings
from decimal import Decimal
from unittest.mock import patch

from sru_generator import (
    ConfigurationError,
    CurrencyError,
    SRUConfig,
    ValidationError,
    convert_currency,
    convert_to_sek,
    create_config,
    get_default_config,
    set_exchange_rate,
    validate_personal_info,
    validate_trade_data,
)
from sru_generator.config import ValidationLevel


class TestSRUConfig(unittest.TestCase):
    """Test SRUConfig functionality."""

    def test_default_config(self) -> None:
        """Test default configuration creation."""
        config = SRUConfig()
        self.assertEqual(config.character_converter, "none")
        self.assertEqual(config.default_currency, "SEK")
        self.assertFalse(config.auto_convert_currency)  # nothing converts automatically

    def test_custom_config(self) -> None:
        """Test custom configuration creation."""
        config = create_config(character_converter="greek", default_currency="USD")
        self.assertEqual(config.character_converter, "greek")
        self.assertEqual(config.default_currency, "USD")

    def test_fields_without_effect_warn_but_still_work(self) -> None:
        """validation_level is read by nothing: setting it warns (removal in 2.0)."""
        with self.assertWarnsRegex(DeprecationWarning, "validation_level"):
            config = create_config(validation_level="strict")
        self.assertEqual(config.validation_level, ValidationLevel.STRICT)

    def test_defaults_and_copies_do_not_warn(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            create_config(character_converter="greek").copy()
            get_default_config()

    def test_from_dict_leaves_the_callers_dict_alone(self) -> None:
        options: dict[str, object] = {"character_converter": "greek"}
        before = dict(options)
        SRUConfig.from_dict(options)
        self.assertEqual(options, before)

    def test_invalid_character_converter(self) -> None:
        """Test invalid character converter raises error."""
        with self.assertRaises(ConfigurationError):
            create_config(character_converter="invalid")

    def test_exchange_rates(self) -> None:
        """Test exchange rate management."""
        config = create_config()
        config.set_exchange_rate("USD", "SEK", 10.5)

        self.assertEqual(config.get_exchange_rate("USD", "SEK"), 10.5)
        self.assertEqual(config.get_exchange_rate("SEK", "USD"), 1 / 10.5)

    def test_invalid_exchange_rate(self) -> None:
        """Test invalid exchange rate raises error."""
        config = create_config()
        with self.assertRaises(ConfigurationError):
            config.set_exchange_rate("USD", "SEK", -1.0)

    def test_config_to_dict(self) -> None:
        """Test configuration serialization."""
        config = create_config(character_converter="greek")
        config_dict = config.to_dict()

        self.assertIn("character_converter", config_dict)
        self.assertEqual(config_dict["character_converter"], "greek")

    def test_config_from_dict(self) -> None:
        """Test configuration deserialization."""
        config_dict = {
            "character_converter": "greek",
            "default_currency": "USD",
            "validation_level": "strict",
        }
        with self.assertWarns(DeprecationWarning):
            config = SRUConfig.from_dict(config_dict)
        self.assertEqual(config_dict["validation_level"], "strict")  # not mutated

        self.assertEqual(config.character_converter, "greek")
        self.assertEqual(config.default_currency, "USD")


class TestValidation(unittest.TestCase):
    """Test validation functionality."""

    def test_valid_trade_data(self) -> None:
        """Test validation of valid trade data."""
        trade_data = [
            {
                "quantity": 100,
                "stock": "Apple Inc",
                "net value": 15000.00,
                "total net value of purchase": 14000.00,
                "profit/loss": 1000.00,
            }
        ]

        validated = validate_trade_data(trade_data)
        self.assertEqual(len(validated), 1)
        self.assertEqual(validated[0]["quantity"], 100)

    def test_invalid_quantity(self) -> None:
        """Test validation fails for negative quantity."""
        trade_data = [
            {
                "quantity": -10,
                "stock": "Apple Inc",
                "net value": 15000.00,
                "total net value of purchase": 14000.00,
            }
        ]

        with self.assertRaises(ValidationError):
            validate_trade_data(trade_data)

    def test_empty_stock_name(self) -> None:
        """Test validation fails for empty stock name."""
        trade_data = [
            {
                "quantity": 100,
                "stock": "",
                "net value": 15000.00,
                "total net value of purchase": 14000.00,
            }
        ]

        with self.assertRaises(ValidationError):
            validate_trade_data(trade_data)

    def test_profit_loss_calculation(self) -> None:
        """Test automatic profit/loss calculation."""
        trade_data = [
            {
                "quantity": 100,
                "stock": "Apple Inc",
                "net value": 15000.00,
                "total net value of purchase": 14000.00,
                # profit/loss not provided
            }
        ]

        validated = validate_trade_data(trade_data)
        self.assertEqual(validated[0]["profit/loss"], Decimal("1000.00"))

    def test_profit_loss_mismatch(self) -> None:
        """Test validation fails for profit/loss mismatch."""
        trade_data = [
            {
                "quantity": 100,
                "stock": "Apple Inc",
                "net value": 15000.00,
                "total net value of purchase": 14000.00,
                "profit/loss": 2000.00,  # Should be 1000.00
            }
        ]

        with self.assertRaises(ValidationError):
            validate_trade_data(trade_data)

    def test_valid_personal_info(self) -> None:
        """Test validation of valid personal info."""
        personal_info = {
            "personal_number": "198112189876",
            "full_name": "John Doe",
            "postal_code": "12345",
            "city_name": "Stockholm",
        }

        validated = validate_personal_info(personal_info)
        self.assertEqual(validated["full_name"], "John Doe")

    def test_invalid_personal_number(self) -> None:
        """Test validation fails for invalid personal number."""
        personal_info = {
            "personal_number": "123",  # Too short
            "full_name": "John Doe",
            "postal_code": "12345",
            "city_name": "Stockholm",
        }

        with self.assertRaises(ValidationError):
            validate_personal_info(personal_info)

    def test_invalid_postal_code(self) -> None:
        """Test validation fails for invalid postal code."""
        personal_info = {
            "personal_number": "198112189876",
            "full_name": "John Doe",
            "postal_code": "1234",  # Wrong format
            "city_name": "Stockholm",
        }

        with self.assertRaises(ValidationError):
            validate_personal_info(personal_info)


class TestCurrencyConversion(unittest.TestCase):
    """Test currency conversion functionality."""

    def setUp(self) -> None:
        """Set up test exchange rates."""
        set_exchange_rate("USD", "SEK", 10.5)
        set_exchange_rate("EUR", "SEK", 11.2)

    def test_convert_to_sek(self) -> None:
        """Test conversion to SEK."""
        usd_amount = 1000.00
        sek_amount = convert_to_sek(usd_amount, "USD")
        expected = Decimal("10500.00")

        self.assertEqual(sek_amount, expected)

    def test_convert_currency(self) -> None:
        """Test direct currency conversion."""
        usd_amount = 1000.00
        eur_amount = convert_currency(usd_amount, "USD", "EUR")

        # 1000 USD = 10500 SEK = 937.5 EUR (10500 / 11.2)
        expected = Decimal("937.50")
        self.assertEqual(eur_amount, expected)

    def test_unsupported_currency(self) -> None:
        """Test error for unsupported currency."""
        with self.assertRaises(CurrencyError):
            convert_to_sek(1000.00, "XYZ")

    def test_negative_amount(self) -> None:
        """Test error for negative amount."""
        with self.assertRaises(ValidationError):
            convert_to_sek(-1000.00, "USD")

    def test_same_currency(self) -> None:
        """Test conversion to same currency returns same amount."""
        amount = Decimal("1000.00")
        result = convert_currency(amount, "SEK", "SEK")
        self.assertEqual(result, amount)


class TestIntegration(unittest.TestCase):
    """Test integration of enhanced features."""

    def test_full_workflow(self) -> None:
        """Test complete workflow with enhanced features."""
        # Create configuration
        config = create_config(character_converter="greek")

        # Set exchange rates
        config.set_exchange_rate("USD", "SEK", 10.5)

        # Multi-currency trade data
        trade_data = [
            {
                "quantity": 100,
                "stock": "Apple Inc",
                "net value": 1500.00,
                "total net value of purchase": 1400.00,
                "currency": "USD",
            }
        ]

        # Validate data
        validated_data = validate_trade_data(trade_data)
        self.assertEqual(len(validated_data), 1)

        # Convert currency
        trade = validated_data[0]
        currency = trade["currency"]
        assert currency is not None
        sale_sek = convert_to_sek(trade["net value"], currency)
        cost_sek = convert_to_sek(trade["total net value of purchase"], currency)

        # Verify conversion
        self.assertEqual(sale_sek, Decimal("15750.00"))
        self.assertEqual(sale_sek - cost_sek, Decimal("1050.00"))

        # Test character converter. Without text-converters installed this is the
        # bundled copy, which warns; force that case so the test does not depend on
        # what is installed.
        with (
            patch.dict(sys.modules, {"text_converters": None}),
            self.assertWarns(DeprecationWarning),
        ):
            converter = config.get_character_converter()
        self.assertEqual(converter("Ελλάδα"), "Ellada")


if __name__ == "__main__":
    unittest.main()
