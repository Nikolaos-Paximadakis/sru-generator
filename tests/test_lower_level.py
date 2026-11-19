"""Lower-level writers called with unvalidated rows: rows and totals must agree."""

import logging
import os
import unittest
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from sru_generator import sru_generator as core
from sru_generator.sru_generator import (
    MAX_MONETARY_VALUE,
    calculate_group_totals,
    generate_sru_trade_content,
    write_sru_file,
)
from sru_generator.utils import setup_logger


def _fields(content: str) -> dict[str, list[str]]:
    fields: dict[str, list[str]] = {}
    for line in content.splitlines():
        if line.startswith("#UPPGIFT "):
            _, code, value = line.split(" ", 2)
            fields.setdefault(code, []).append(value)
    return fields


class TestUnreadableAmounts(unittest.TestCase):
    def test_an_unreadable_sale_price_is_0_in_the_row_and_in_the_totals(self) -> None:
        """The row used to be written with 0 but left out of the totals entirely."""
        row = {
            "quantity": 1,
            "stock": "A",
            "net value": "abc",
            "total net value of purchase": 50,
        }
        with self.assertLogs("sru_generator", level="WARNING"):
            content = generate_sru_trade_content([row], "Test", "198112189876", 2025)
        fields = _fields(content)
        self.assertEqual(fields["3102"], ["0"])
        self.assertEqual(fields["3103"], ["50"])
        self.assertEqual(fields["3300"], ["0"])
        self.assertEqual(fields["3301"], ["50"])  # was 0: the row's cost was dropped
        self.assertEqual(fields["3305"], ["50"])

    def test_a_non_finite_amount_counts_as_unreadable(self) -> None:
        row = {
            "quantity": 1,
            "stock": "A",
            "net value": 100,
            "total net value of purchase": Decimal("NaN"),
        }
        with self.assertLogs("sru_generator", level="WARNING"):
            content = generate_sru_trade_content([row], "Test", "198112189876", 2025)
        fields = _fields(content)
        self.assertEqual((fields["3103"], fields["3301"]), (["0"], ["0"]))
        self.assertEqual((fields["3104"], fields["3304"]), (["100"], ["100"]))


class TestLimits(unittest.TestCase):
    def test_page_totals_are_capped_at_the_field_maximum(self) -> None:
        rows = [{"net value": MAX_MONETARY_VALUE, "total net value of purchase": 0}] * 2
        with self.assertLogs("sru_generator", level="ERROR") as logs:
            totals = calculate_group_totals(rows)
        self.assertEqual(totals["total_sold"], MAX_MONETARY_VALUE)
        self.assertEqual(totals["total_profit"], MAX_MONETARY_VALUE)
        self.assertIn("would exceed maximum", logs.output[0])

    def test_a_row_too_large_to_round_is_skipped_in_row_and_totals(self) -> None:
        """1E+40 overflows Decimal's 28-digit precision when rounded: the row is not
        written, and the totals skip it too, so they still match the rows."""
        rows = [
            {
                "quantity": 1,
                "stock": "Huge",
                "net value": Decimal("1E+40"),
                "total net value of purchase": 0,
            },
            {
                "quantity": 1,
                "stock": "B",
                "net value": 10,
                "total net value of purchase": 4,
            },
        ]
        with self.assertLogs("sru_generator", level="WARNING"):
            totals = calculate_group_totals(rows)
        self.assertEqual((totals["total_sold"], totals["total_profit"]), (10, 6))
        with self.assertLogs("sru_generator", level="ERROR"):
            content = generate_sru_trade_content(rows, "Test", "198112189876", 2025)
        self.assertNotIn("Huge", content)
        self.assertIn("#UPPGIFT 3300 10\n", content)

    def test_the_page_count_stops_at_the_maximum(self) -> None:
        rows = [
            {
                "quantity": 1,
                "stock": f"S{i}",
                "net value": 1,
                "total net value of purchase": 1,
            }
            for i in range(5)
        ]
        with (
            patch.object(core, "MAX_GROUP_NUMBER", 2),
            self.assertLogs("sru_generator", level="ERROR"),
        ):
            content = generate_sru_trade_content(
                rows, "Test", "198112189876", 2025, items_per_group=2
            )
        self.assertEqual(content.count("#BLANKETT "), 2)


class TestWriteErrors(unittest.TestCase):
    def test_an_os_error_returns_false(self) -> None:
        with TemporaryDirectory() as tmp, self.assertLogs("sru_generator", "ERROR"):
            self.assertFalse(write_sru_file(tmp, "#FIL_SLUT\n"))  # a directory

    def test_an_unexpected_error_returns_false(self) -> None:
        with TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "x.sru")
            with (
                patch.object(os, "open", side_effect=RuntimeError("boom")),
                self.assertLogs("sru_generator", "ERROR") as logs,
            ):
                self.assertFalse(write_sru_file(path, "#FIL_SLUT\n"))
        self.assertIn("unexpected error", logs.output[0])


class TestSetupLogger(unittest.TestCase):
    def test_replaces_handlers_with_one_console_handler(self) -> None:
        name = "sru_generator.tests.setup_logger"
        setup_logger(name, logging.DEBUG)
        logger = setup_logger(name, logging.WARNING)  # a second call must not stack
        try:
            self.assertEqual(logger.level, logging.WARNING)
            self.assertEqual(len(logger.handlers), 1)
            self.assertIsInstance(logger.handlers[0], logging.StreamHandler)
        finally:
            logger.handlers.clear()


if __name__ == "__main__":
    unittest.main()
