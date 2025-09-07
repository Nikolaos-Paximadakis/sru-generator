"""
Tests for enhanced SRU Generator features.
"""

import unittest
from decimal import Decimal

from sru_generator import (BusinessRuleError, ConfigurationError,
                           CurrencyError, SRUConfig, ValidationError,
                           convert_currency, convert_to_sek, create_config,
                           set_exchange_rate, validate_personal_info,
                           validate_trade_data)


class TestSRUConfig(unittest.TestCase):
    """Test SRUConfig functionality."""

    def test_default_config(self):
        """Test default configuration creation."""
        config = SRUConfig()
        self.assertEqual(config.character_converter, "none")
        self.assertEqual(config.default_currency, "SEK")
        self.assertTrue(config.auto_convert_currency)

    def test_custom_config(self):
        """Test custom configuration creation."""
        config = create_config(
            character_converter="greek",
            validation_level="strict",
            default_currency="USD",
        )
        self.assertEqual(config.character_converter, "greek")
        self.assertEqual(config.default_currency, "USD")

    def test_invalid_character_converter(self):
        """Test invalid character converter raises error."""
        with self.assertRaises(ConfigurationError):
            create_config(character_converter="invalid")

    def test_exchange_rates(self):
        """Test exchange rate management."""
        config = create_config()
        config.set_exchange_rate("USD", "SEK", 10.5)

        self.assertEqual(config.get_exchange_rate("USD", "SEK"), 10.5)
        self.assertEqual(config.get_exchange_rate("SEK", "USD"), 1 / 10.5)

    def test_invalid_exchange_rate(self):
        """Test invalid exchange rate raises error."""
        config = create_config()
        with self.assertRaises(ConfigurationError):
            config.set_exchange_rate("USD", "SEK", -1.0)

    def test_config_to_dict(self):
        """Test configuration serialization."""
        config = create_config(character_converter="greek")
        config_dict = config.to_dict()

        self.assertIn("character_converter", config_dict)
        self.assertEqual(config_dict["character_converter"], "greek")

    def test_config_from_dict(self):
        """Test configuration deserialization."""
        config_dict = {
            "character_converter": "greek",
            "default_currency": "USD",
            "validation_level": "strict",
        }
        config = SRUConfig.from_dict(config_dict)

        self.assertEqual(config.character_converter, "greek")
        self.assertEqual(config.default_currency, "USD")


class TestValidation(unittest.TestCase):
    """Test validation functionality."""

    def test_valid_trade_data(self):
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

    def test_invalid_quantity(self):
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

    def test_empty_stock_name(self):
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

    def test_profit_loss_calculation(self):
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

    def test_profit_loss_mismatch(self):
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

    def test_valid_personal_info(self):
        """Test validation of valid personal info."""
        personal_info = {
            "personal_number": "1234567890",
            "full_name": "John Doe",
            "postal_code": "12345",
            "city_name": "Stockholm",
        }

        validated = validate_personal_info(personal_info)
        self.assertEqual(validated["full_name"], "John Doe")

    def test_invalid_personal_number(self):
        """Test validation fails for invalid personal number."""
        personal_info = {
            "personal_number": "123",  # Too short
            "full_name": "John Doe",
            "postal_code": "12345",
            "city_name": "Stockholm",
        }

        with self.assertRaises(ValidationError):
            validate_personal_info(personal_info)

    def test_invalid_postal_code(self):
        """Test validation fails for invalid postal code."""
        personal_info = {
            "personal_number": "1234567890",
            "full_name": "John Doe",
            "postal_code": "1234",  # Wrong format
            "city_name": "Stockholm",
        }

        with self.assertRaises(ValidationError):
            validate_personal_info(personal_info)


class TestCurrencyConversion(unittest.TestCase):
    """Test currency conversion functionality."""

    def setUp(self):
        """Set up test exchange rates."""
        set_exchange_rate("USD", "SEK", 10.5)
        set_exchange_rate("EUR", "SEK", 11.2)

    def test_convert_to_sek(self):
        """Test conversion to SEK."""
        usd_amount = 1000.00
        sek_amount = convert_to_sek(usd_amount, "USD")
        expected = Decimal("10500.00")

        self.assertEqual(sek_amount, expected)

    def test_convert_currency(self):
        """Test direct currency conversion."""
        usd_amount = 1000.00
        eur_amount = convert_currency(usd_amount, "USD", "EUR")

        # 1000 USD = 10500 SEK = 937.5 EUR (10500 / 11.2)
        expected = Decimal("937.50")
        self.assertEqual(eur_amount, expected)

    def test_unsupported_currency(self):
        """Test error for unsupported currency."""
        with self.assertRaises(CurrencyError):
            convert_to_sek(1000.00, "XYZ")

    def test_negative_amount(self):
        """Test error for negative amount."""
        with self.assertRaises(ValidationError):
            convert_to_sek(-1000.00, "USD")

    def test_same_currency(self):
        """Test conversion to same currency returns same amount."""
        amount = Decimal("1000.00")
        result = convert_currency(amount, "SEK", "SEK")
        self.assertEqual(result, amount)


class TestIntegration(unittest.TestCase):
    """Test integration of enhanced features."""

    def test_full_workflow(self):
        """Test complete workflow with enhanced features."""
        # Create configuration
        config = create_config(character_converter="greek", validation_level="strict")

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
        trade["net value"] = float(
            convert_to_sek(trade["net value"], trade["currency"])
        )
        trade["total net value of purchase"] = float(
            convert_to_sek(trade["total net value of purchase"], trade["currency"])
        )
        trade["profit/loss"] = trade["net value"] - trade["total net value of purchase"]

        # Verify conversion
        self.assertAlmostEqual(trade["net value"], 15750.0, places=2)
        self.assertAlmostEqual(trade["profit/loss"], 1050.0, places=2)

        # Test character converter
        converter = config.get_character_converter()
        self.assertIsNotNone(converter)


if __name__ == "__main__":
    unittest.main()
