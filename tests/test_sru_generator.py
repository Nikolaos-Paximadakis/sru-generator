"""
Tests for SRU Generator package.
"""

import unittest
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from sru_generator import build_blanketter_sru, build_info_sru
from sru_generator.exceptions import ValidationError
from sru_generator.sru_generator import (
    MAX_GROUP_NUMBER,
    MAX_MONETARY_VALUE,
    calculate_group_totals,
    format_group_totals_sru,
    format_trade_item_sru,
    generate_sru_footer,
    generate_sru_header,
    generate_sru_info_content,
    generate_sru_trade_content,
    round_k4_cost_basis,
    round_k4_sale_price,
    write_sru_file,
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

    def test_build_info_sru(self):
        content = build_info_sru(
            {
                "personal_number": "1234567890",
                "full_name": "John Doe",
                "postal_code": "12345",
                "city_name": "Stockholm",
            }
        )

        self.assertIn("#ORGNR 1234567890", content)
        self.assertIn("#NAMN John Doe", content)

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

    def test_build_blanketter_sru(self):
        content = build_blanketter_sru(
            trade_rows=[
                {
                    "quantity": 100,
                    "stock": "Apple Inc",
                    "net value": 15000.00,
                    "total net value of purchase": 14000.00,
                    "profit/loss": 1000.00,
                }
            ],
            personal_info={
                "personal_number": "1234567890",
                "full_name": "John Doe",
                "postal_code": "12345",
                "city_name": "Stockholm",
            },
            year=2024,
        )

        self.assertIn("#BLANKETT K4-2024P4", content)
        self.assertIn("#UPPGIFT 3100 100", content)
        self.assertTrue(content.endswith("#FIL_SLUT\n"))

    PERSONAL_INFO = {
        "personal_number": "1234567890",
        "full_name": "John Doe",
        "postal_code": "12345",
        "city_name": "Stockholm",
    }

    def test_build_blanketter_sru_crypto_only(self):
        """No trade rows but crypto groups: only the crypto pages, numbered 1..n."""
        crypto_groups = [
            {"group_number": 1, "uppgifter": ["#UPPGIFT 3410 2", "#UPPGIFT 3411 BTC"]},
            {"group_number": 2, "uppgifter": ["#UPPGIFT 3410 5", "#UPPGIFT 3411 ETH"]},
        ]

        content = build_blanketter_sru(
            trade_rows=[],
            personal_info=self.PERSONAL_INFO,
            year=2024,
            crypto_groups=crypto_groups,
        )

        pages = content.split("#BLANKETT K4-2024P4\n")[1:]
        self.assertEqual(len(pages), 2)
        self.assertIn("#UPPGIFT 7014 1\n#UPPGIFT 3410 2\n#UPPGIFT 3411 BTC\n", pages[0])
        self.assertIn("#UPPGIFT 7014 2\n#UPPGIFT 3410 5\n#UPPGIFT 3411 ETH\n", pages[1])
        self.assertNotIn("#UPPGIFT 31", content)
        self.assertNotIn("#UPPGIFT 33", content)
        self.assertTrue(content.endswith("#BLANKETTSLUT\n#FIL_SLUT\n"))

    def test_build_blanketter_sru_refuses_no_trades_and_no_crypto(self):
        for crypto_groups in (None, []):
            with self.subTest(crypto_groups=crypto_groups):
                with self.assertRaisesRegex(
                    ValidationError, "Trade data cannot be empty"
                ):
                    build_blanketter_sru(
                        trade_rows=[],
                        personal_info=self.PERSONAL_INFO,
                        year=2024,
                        crypto_groups=crypto_groups,
                    )

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


class TestK4WholeKronaRounding(unittest.TestCase):
    """Skatteverket's whole-krona rule for a K4 row, which is not one rule but three.

    From the Inkomstdeklaration 1 e-service's help text for bilaga K4 avsnitt A
    (https://www8.skatteverket.se/hjalptexter/EfInk1k4_aktie.html): forsaljningspris rounds
    "oren nedat", omkostnadsbelopp rounds "oren uppat", and vinst/forlust "raknas ut
    automatiskt" from those two. Until 2026-09-16 all three were rounded independently with
    ROUND_HALF_EVEN, which is right for none of them.
    """

    def test_the_sale_price_drops_its_ore_and_the_cost_basis_gains_one(self):
        content = format_trade_item_sru(
            {
                "quantity": 100,
                "stock": "Apple Inc",
                "net value": "15000.99",
                "total net value of purchase": "14000.01",
                "profit/loss": "1000.98",
            },
            0,
            0,
        )

        # Half-even would have written 15001 and 14000, overstating the gain by 2 kr.
        self.assertIn("#UPPGIFT 3102 15000", content)
        self.assertIn("#UPPGIFT 3103 14001", content)

    def test_the_row_states_its_own_difference_not_the_supplied_profit(self):
        content = format_trade_item_sru(
            {
                "quantity": 100,
                "stock": "Apple Inc",
                "net value": "15000.99",
                "total net value of purchase": "14000.01",
                "profit/loss": "1000.98",  # half-even: 1001. The row says 999.
            },
            0,
            0,
        )

        self.assertIn("#UPPGIFT 3104 999", content)
        self.assertNotIn("#UPPGIFT 3104 1001", content)

    def test_a_loss_row_rounds_the_same_way_round(self):
        content = format_trade_item_sru(
            {
                "quantity": 50,
                "stock": "Microsoft Corp",
                "net value": "12000.01",
                "total net value of purchase": "13000.99",
                "profit/loss": "-1000.98",
            },
            0,
            0,
        )

        self.assertIn("#UPPGIFT 3102 12000", content)
        self.assertIn("#UPPGIFT 3103 13001", content)
        self.assertIn("#UPPGIFT 3105 1001", content)  # losses are written positive

    def test_a_sub_krona_result_needs_no_rule_about_truncating_negatives(self):
        """The old open question -- does -0.40 round to a 0 vinst or a 1 kr forlust? -- does
        not survive deriving the figure: the answer follows from the two columns."""
        gain = format_trade_item_sru(
            {
                "quantity": 1,
                "stock": "A",
                "net value": "100.40",
                "total net value of purchase": "100.00",
            },
            0,
            0,
        )
        self.assertIn("#UPPGIFT 3104 0", gain)

        loss = format_trade_item_sru(
            {
                "quantity": 1,
                "stock": "B",
                "net value": "100.00",
                "total net value of purchase": "100.60",
            },
            0,
            0,
        )
        self.assertIn("#UPPGIFT 3105 1", loss)

    def test_every_row_in_a_generated_file_states_its_own_difference(self):
        rows = [
            {
                "quantity": 1,
                "stock": f"S{index}",
                "net value": f"{1000 + index}.{ore:02d}",
                "total net value of purchase": f"{900 + index}.{(99 - ore):02d}",
            }
            for index, ore in enumerate((0, 1, 49, 50, 51, 99))
        ]

        content = generate_sru_trade_content(rows, "John Doe", "1234567890", year=2025)
        fields = {}
        for line in content.splitlines():
            if line.startswith("#UPPGIFT "):
                _, code, value = line.split(" ", 2)
                fields.setdefault(code, []).append(value)

        for index in range(len(rows)):
            base = 3100 + index * 10
            sale = int(fields[str(base + 2)][0])
            cost = int(fields[str(base + 3)][0])
            profit = int(fields.get(str(base + 4), [0])[0])
            loss = int(fields.get(str(base + 5), [0])[0])
            self.assertEqual(sale - cost, profit - loss, f"row {index} does not add up")

    def test_the_group_totals_are_the_sums_of_the_rows_printed_above_them(self):
        rows = [
            {
                "quantity": 1,
                "stock": f"S{index}",
                "net value": f"{1000 + index}.{ore:02d}",
                "total net value of purchase": f"{900 + index}.{(99 - ore):02d}",
            }
            for index, ore in enumerate((0, 1, 49, 50, 51, 99))
        ]

        content = generate_sru_trade_content(rows, "John Doe", "1234567890", year=2025)
        fields = {}
        for line in content.splitlines():
            if line.startswith("#UPPGIFT "):
                _, code, value = line.split(" ", 2)
                fields.setdefault(code, []).append(value)

        sold = sum(int(fields[str(3100 + i * 10 + 2)][0]) for i in range(len(rows)))
        cost = sum(int(fields[str(3100 + i * 10 + 3)][0]) for i in range(len(rows)))
        profit = sum(
            int(fields.get(str(3100 + i * 10 + 4), [0])[0]) for i in range(len(rows))
        )
        loss = sum(
            int(fields.get(str(3100 + i * 10 + 5), [0])[0]) for i in range(len(rows))
        )

        # A zero total is omitted rather than written as 0, which is pre-existing behaviour.
        self.assertEqual(int(fields["3300"][0]), sold)
        self.assertEqual(int(fields["3301"][0]), cost)
        self.assertEqual(int(fields.get("3304", [0])[0]), profit)
        self.assertEqual(int(fields.get("3305", [0])[0]), loss)
        # And the block as a whole adds up, which independent rounding did not guarantee.
        self.assertEqual(sold - cost, profit - loss)

    def test_the_totals_round_each_row_before_summing(self):
        """Sum-then-round is not round-then-sum, and the gap grows with the row count."""
        totals = calculate_group_totals(
            [{"net value": "100.60", "total net value of purchase": "0.10"}] * 3
        )

        self.assertEqual(totals["total_sold"], 300)  # not 301.80 -> 302
        self.assertEqual(totals["total_cost_basis"], 3)  # not 0.30 -> 0
        self.assertEqual(totals["total_profit"], 297)
        self.assertEqual(totals["total_loss"], 0)

    def test_an_unusable_supplied_profit_does_not_remove_the_row_from_the_file(self):
        """The figure is diagnostic, so a bad one must not cost the row its lines.

        `calculate_group_totals` no longer reads the key at all, so a row that formatting
        throws away still lands in the group totals -- a summa with nothing above it.
        `Decimal("NaN")` is the case that gets there: it parses, and only `int()` fails.
        """
        row = {
            "quantity": 1,
            "stock": "X",
            "net value": "100.99",
            "total net value of purchase": "50.01",
            "profit/loss": "NaN",
        }

        content = format_trade_item_sru(row, 0, 0)
        totals = calculate_group_totals([row])

        self.assertIn("#UPPGIFT 3102 100", content)
        self.assertIn("#UPPGIFT 3103 51", content)
        self.assertIn("#UPPGIFT 3104 49", content)
        self.assertEqual(totals["total_sold"], 100)
        self.assertEqual(totals["total_cost_basis"], 51)
        self.assertEqual(totals["total_profit"], 49)

    def test_an_unreadable_supplied_profit_is_not_cross_checked_either(self):
        content = format_trade_item_sru(
            {
                "quantity": 1,
                "stock": "X",
                "net value": "100.99",
                "total net value of purchase": "50.01",
                "profit/loss": "not a number",
            },
            0,
            0,
        )

        self.assertIn("#UPPGIFT 3104 49", content)

    def test_a_self_consistent_row_is_never_accused_of_not_adding_up(self):
        """The two directions can move the derived figure a full 2 away from the caller's own.

        `floor(sale) - ceil(cost)` lies in `(sale - cost - 2, sale - cost]`, so asking the
        question of the *rounded* amounts accuses correct input -- measured at 12% of random
        self-consistent rows. It is asked of the unrounded ones instead.
        """
        with self.assertNoLogs("sru_generator", level="WARNING"):
            format_trade_item_sru(
                {
                    "quantity": 1,
                    "stock": "X",
                    "net value": "10.99",
                    "total net value of purchase": "10.01",
                    "profit/loss": "0.98",  # exactly sale - cost; derived is -1
                },
                0,
                0,
            )

    def test_a_row_that_does_not_add_up_still_is(self):
        with self.assertLogs("sru_generator", level="WARNING") as captured:
            format_trade_item_sru(
                {
                    "quantity": 1,
                    "stock": "X",
                    "net value": "100.00",
                    "total net value of purchase": "10.00",
                    "profit/loss": "5.00",  # sale - cost is 90
                },
                0,
                0,
            )

        self.assertIn(
            "does not match its own sale price minus cost basis", captured.output[0]
        )

    def test_the_helpers_state_the_two_directions(self):
        self.assertEqual(round_k4_sale_price("10.99"), 10)
        self.assertEqual(round_k4_sale_price("10.00"), 10)
        self.assertEqual(round_k4_cost_basis("10.01"), 11)
        self.assertEqual(round_k4_cost_basis("10.00"), 10)


GOLDEN_DIR = Path(__file__).parent / "golden"
FIXED_NOW = datetime(2024, 3, 1, 12, 0, 0)

# Ten rows, so the stock side spans two pages, and three crypto groups, so the crypto side
# runs past the last stock page: both of the merge's page-count branches are in the file.
GOLDEN_TRADE_ROWS = [
    {
        "quantity": 10 + i,
        "stock": f"Stock {i}",
        "net value": Decimal("1000.55") + i * Decimal("101.25"),
        "total net value of purchase": Decimal("900.10") + i * Decimal("123.40"),
        "profit/loss": (Decimal("1000.55") + i * Decimal("101.25"))
        - (Decimal("900.10") + i * Decimal("123.40")),
    }
    for i in range(10)
]
GOLDEN_CRYPTO_GROUPS = [
    {
        "group_number": n,
        "uppgifter": [
            f"#UPPGIFT 3410 {n}",
            f"#UPPGIFT 3411 C{n}",
            "#UPPGIFT 3412 100",
            "#UPPGIFT 3413 60",
            "#UPPGIFT 3414 40",
            "#UPPGIFT 3500 100",
            "#UPPGIFT 3501 60",
            "#UPPGIFT 3503 40",
        ],
    }
    for n in (1, 2, 3)
]
GOLDEN_PERSONAL_INFO = {
    "personal_number": "1234567890",
    "full_name": "John Doe",
    "postal_code": "12345",
    "city_name": "Stockholm",
}


def build_golden_outputs():
    """The stock-only and mixed files, with the clock the header stamps held still."""
    with patch("sru_generator.sru_generator.datetime") as mock_datetime:
        mock_datetime.now.return_value = FIXED_NOW
        stock_only = build_blanketter_sru(GOLDEN_TRADE_ROWS, GOLDEN_PERSONAL_INFO, 2024)
        mixed = build_blanketter_sru(
            GOLDEN_TRADE_ROWS,
            GOLDEN_PERSONAL_INFO,
            2024,
            crypto_groups=GOLDEN_CRYPTO_GROUPS,
        )
    return {"blanketter_stock_only.sru": stock_only, "blanketter_mixed.sru": mixed}


class TestBlanketterOutputUnchanged(unittest.TestCase):
    """Stock-only and mixed files are byte-identical to the ones 1.3.1 wrote before #8.

    #8 let an empty trade list through when crypto groups are given; the golden files in
    ``tests/golden/`` were generated at 1ab25e1, the commit before it, so any change the
    crypto-only path makes to the other two shapes shows up here as a diff.
    """

    def test_stock_only_and_mixed_files_are_unchanged(self):
        for name, content in build_golden_outputs().items():
            with self.subTest(name=name):
                expected = (GOLDEN_DIR / name).read_text(encoding="utf-8")
                self.assertEqual(content, expected)
