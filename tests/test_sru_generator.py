"""
Tests for SRU Generator package.
"""

import unittest
from decimal import Decimal
from sru_generator.sru_generator import (
    generate_sru_info_content,
    generate_sru_header,
    format_trade_item_sru,
    calculate_group_totals,
    format_group_totals_sru,
    generate_sru_trade_content,
    generate_sru_footer,
    write_sru_file,
    MAX_GROUP_NUMBER,
    MAX_MONETARY_VALUE,
)


class TestSRUGenerator(unittest.TestCase):
    """Test cases for SRU Generator functions."""

    def test_generate_sru_info_content(self):
        """Test SRU info content generation."""
        content = generate_sru_info_content(
            personal_number="1234567890",
            full_name="John Doe",
            postal_code="12345",
            city_name="Stockholm",
        )

        self.assertIn("#DATABESKRIVNING_START", content)
        self.assertIn("#PRODUKT SRU", content)
        self.assertIn("1234567890", content)
        self.assertIn("John Doe", content)
        self.assertIn("12345", content)
        self.assertIn("Stockholm", content)
        self.assertIn("#MEDIELEV_SLUT", content)

    def test_generate_sru_header(self):
        """Test SRU header generation."""
        content = generate_sru_header(
            year_of_report=2024, personal_number="1234567890", full_name="John Doe"
        )

        self.assertIn("#BLANKETT K4-2024P4", content)
        self.assertIn("#IDENTITET 1234567890", content)
        self.assertIn("#NAMN John Doe", content)

    def test_format_trade_item_sru(self):
        """Test trade item formatting."""
        row_data = {
            "quantity": 100,
            "stock": "Apple Inc",
            "net value": 15000.00,
            "total net value of purchase": 14000.00,
            "profit/loss": 1000.00,
        }

        content = format_trade_item_sru(row_data, 0, 0)

        self.assertIn("#UPPGIFT 3100 100", content)  # Quantity
        self.assertIn("#UPPGIFT 3101 Apple Inc", content)  # Stock name
        self.assertIn("#UPPGIFT 3102 15000", content)  # Sale price
        self.assertIn("#UPPGIFT 3103 14000", content)  # Cost basis
        self.assertIn("#UPPGIFT 3104 1000", content)  # Profit

    def test_format_trade_item_sru_with_loss(self):
        """Test trade item formatting with loss."""
        row_data = {
            "quantity": 50,
            "stock": "Microsoft Corp",
            "net value": 12000.00,
            "total net value of purchase": 13000.00,
            "profit/loss": -1000.00,
        }

        content = format_trade_item_sru(row_data, 0, 0)

        self.assertIn("#UPPGIFT 3100 50", content)  # Quantity
        self.assertIn("#UPPGIFT 3101 Microsoft Corp", content)  # Stock name
        self.assertIn("#UPPGIFT 3102 12000", content)  # Sale price
        self.assertIn("#UPPGIFT 3103 13000", content)  # Cost basis
        self.assertIn("#UPPGIFT 3105 1000", content)  # Loss (positive value)

    def test_calculate_group_totals(self):
        """Test group totals calculation."""
        group_data = [
            {
                "net value": 15000.00,
                "total net value of purchase": 14000.00,
                "profit/loss": 1000.00,
            },
            {
                "net value": 12000.00,
                "total net value of purchase": 13000.00,
                "profit/loss": -1000.00,
            },
        ]

        totals = calculate_group_totals(group_data)

        self.assertEqual(totals["total_sold"], 27000)
        self.assertEqual(totals["total_cost_basis"], 27000)
        self.assertEqual(totals["total_profit"], 1000)
        self.assertEqual(totals["total_loss"], 1000)

    def test_format_group_totals_sru(self):
        """Test group totals SRU formatting."""
        totals = {
            "total_sold": 27000,
            "total_cost_basis": 27000,
            "total_profit": 1000,
            "total_loss": 1000,
        }

        content = format_group_totals_sru(totals)

        self.assertIn("#UPPGIFT 3300 27000", content)  # Total sold
        self.assertIn("#UPPGIFT 3301 27000", content)  # Total cost basis
        self.assertIn("#UPPGIFT 3304 1000", content)  # Total profit
        self.assertIn("#UPPGIFT 3305 1000", content)  # Total loss

    def test_generate_sru_trade_content(self):
        """Test SRU trade content generation."""
        trade_data = [
            {
                "quantity": 100,
                "stock": "Apple Inc",
                "net value": 15000.00,
                "total net value of purchase": 14000.00,
                "profit/loss": 1000.00,
            }
        ]

        content = generate_sru_trade_content(
            trade_data=trade_data,
            full_name="John Doe",
            personal_number="1234567890",
            year=2024,
        )

        self.assertIn("#BLANKETT K4-2024P4", content)
        self.assertIn("#IDENTITET 1234567890", content)
        self.assertIn("#NAMN John Doe", content)
        self.assertIn("#UPPGIFT 7014 1", content)  # Group number
        self.assertIn("#BLANKETTSLUT", content)

    def test_generate_sru_footer(self):
        """Test SRU footer generation."""
        content = generate_sru_footer()
        self.assertEqual(content, "#FIL_SLUT\n")

    def test_validation_limits(self):
        """Test validation of quantity and monetary limits."""
        # Test quantity limit
        row_data = {
            "quantity": MAX_MONETARY_VALUE + 1,
            "stock": "Test Stock",
            "net value": 1000.00,
            "total net value of purchase": 1000.00,
            "profit/loss": 0.00,
        }

        content = format_trade_item_sru(row_data, 0, 0)
        self.assertIn("#UPPGIFT 3100 0", content)  # Should be clamped to 0

        # Test monetary value limit
        row_data = {
            "quantity": 100,
            "stock": "Test Stock",
            "net value": MAX_MONETARY_VALUE + 1,
            "total net value of purchase": 1000.00,
            "profit/loss": 0.00,
        }

        content = format_trade_item_sru(row_data, 0, 0)
        self.assertIn("#UPPGIFT 3102 0", content)  # Should be clamped to 0


if __name__ == "__main__":
    unittest.main()
