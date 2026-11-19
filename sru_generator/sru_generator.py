"""
SRU Generator - Main module for generating Swedish SRU files.

This module provides all the core functionality for generating SRU files
according to Swedish tax authority specifications.
"""

import logging
import os
import re
from collections.abc import Mapping, Sequence
from datetime import datetime
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal
from pathlib import Path
from typing import Literal, TypedDict

from .amounts import to_decimal
from .exceptions import DataFormatError, FileOperationError, ValidationError
from .models import Amount, CharacterConverter, CryptoSRUGroup

# A library must not configure logging: handlers and levels belong to the application
# (the CLI sets them up). The package adds only a NullHandler, in __init__.py.
logger = logging.getLogger("sru_generator")

# SRU files are ISO-8859-1 (Latin-1), per Skatteverket's SRU specification (SKV 269).
# Swedish letters (å, ä, ö) are representable as they are; anything outside Latin-1
# (Greek, €, typographic quotes and dashes) is not and is rejected rather than replaced,
# because a silently substituted "?" in a name on a tax form is worse than an error.
SRU_ENCODING = "iso-8859-1"
_LATIN1_MAX = 0xFF  # highest code point ISO-8859-1 can represent


def encode_sru_text(content: str) -> bytes:
    """
    Encode SRU content as ISO-8859-1 bytes (`SRU_ENCODING`).

    Raises:
        DataFormatError: if the content has characters ISO-8859-1 cannot represent.
            Transliterate them first, e.g. with a ``character_converter``.
    """
    try:
        return content.encode(SRU_ENCODING)
    except UnicodeEncodeError:
        bad = sorted({char for char in content if ord(char) > _LATIN1_MAX})
        raise DataFormatError(
            "SRU content contains characters that ISO-8859-1 cannot represent: "
            + " ".join(f"{char!r} (U+{ord(char):04X})" for char in bad)
            + ". Transliterate them first, e.g. with a character_converter.",
            expected_format=SRU_ENCODING,
        ) from None


def decode_sru_bytes(data: bytes) -> str:
    """
    Decode an SRU file read from disk.

    Files from this package and from most other tools are ISO-8859-1, but some tools
    write UTF-8. Valid UTF-8 is tried first because ISO-8859-1 decodes any byte
    sequence and would turn UTF-8 "å" into "Ã¥" without complaint.
    """
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode(SRU_ENCODING)


# Define constants for SRU field identifiers
SRU_FIELD_BLANKETT_START = "#BLANKETT K4-{year}P4"
SRU_FIELD_IDENTITET = "#IDENTITET {personal_number} {datetime}"
SRU_FIELD_NAMN = "#NAMN {full_name}"
SRU_FIELD_UPPGIFT_GROUP_START = "#UPPGIFT 7014 {group_number}"

# --- CORRECTED CONSTANT DEFINITIONS FOR INDIVIDUAL ITEMS ---
SRU_LINE_START = "#UPPGIFT 31"
SRU_FIELD_QUANTITY_SUFFIX = "0"
SRU_FIELD_STOCK_NAME_SUFFIX = "1"
SRU_FIELD_SOLD_AMOUNT_SUFFIX = "2"
SRU_FIELD_COST_BASIS_SUFFIX = "3"
SRU_FIELD_PROFIT_SUFFIX = "4"
SRU_FIELD_LOSS_SUFFIX = "5"
# --- END CORRECTED CONSTANT DEFINITIONS ---

SRU_FIELD_GROUP_TOTAL_SOLD = "#UPPGIFT 3300 {amount}"  # Summa Försäljningspris
# Summa Omkostnadsbelopp
SRU_FIELD_GROUP_TOTAL_COST_BASIS = "#UPPGIFT 3301 {amount}"
SRU_FIELD_GROUP_TOTAL_PROFIT = "#UPPGIFT 3304 {amount}"  # Summa Vinst
SRU_FIELD_GROUP_TOTAL_LOSS = "#UPPGIFT 3305 {amount}"  # Summa Förlust
SRU_FIELD_BLANKETT_END = "#BLANKETTSLUT"
SRU_FIELD_FILE_END = "#FIL_SLUT"

# Define rounding template for whole numbers
WHOLE_NUMBER_ROUNDING = Decimal("1")

# Skatteverket states the whole-krona rule per K4 column, and it is not symmetric. From
# the Inkomstdeklaration 1 e-service's own help text for bilaga K4, avsnitt A
# ("Marknadsnoterade aktier, aktieindexobligationer, aktieoptioner m.m."); avsnitt D
# says the same:
#
#   Kolumnen "Forsaljningspris"  -- "Avrunda oren nedat till hela kronor."
#   Kolumnen "Omkostnadsbelopp"  -- "Avrunda oren uppat till hela kronor."
#   Kolumnen "Vinst/Forlust"     -- "raknas ut automatiskt genom att forsaljningspriset
#                                     minskas med det omkostnadsbelopp du fyllt i."
#
# https://www8.skatteverket.se/hjalptexter/EfInk1k4_aktie.html
#
# Three consequences, each easy to get wrong (rounding every amount independently, e.g.
# with ROUND_HALF_EVEN, gets all three wrong):
#
# - The two directions are opposite. Neither column is "truncated" and neither is
#   rounded to nearest, so no single rounding mode is right for both.
# - Vinst/forlust is *derived*, never rounded on its own. Rounding it independently is
#   what let a K4 row state a vinst that is not that row's own forsaljningspris minus
#   its own omkostnadsbelopp; measured on a real 2019-2025 archive, 104 of 450 rows did.
# - Because it is derived, the question of which way a negative amount truncates never
#   arises.
#
# This is Skatteverket's rule rather than a preference, so it is deliberately not routed
# through `SRUConfig.rounding_mode`.
K4_SALE_PRICE_ROUNDING = ROUND_FLOOR
K4_COST_BASIS_ROUNDING = ROUND_CEILING
NUMBER_OF_CHARACTERS_FOR_STOCK_NAME = 80

#: K4 section A has nine rows per page (fields 3100-3185); a tenth would write 3190,
#: which is not a K4 field.
K4_SECTION_A_ROWS = 9
#: K4 section D ("Övriga värdepapper, andra tillgångar", e.g. crypto): seven rows of six
#: fields (3410-3475) and the four totals. Merged crypto pages may hold only these.
K4_SECTION_D_FIELDS = frozenset(
    {3400 + 10 * row + column for row in range(1, 8) for column in range(6)}
    | {3500, 3501, 3503, 3504}
)
_UPPGIFT_LINE = re.compile(r"#UPPGIFT (\d{4}) (\S.*)")

#: The K4 block name carries the income year (K4-2025P4 is income year 2025).
MIN_INCOME_YEAR = 2000
MAX_INCOME_YEAR = 9999

# Define numeric limits for SRU fields
MAX_GROUP_NUMBER = 99999
MAX_MONETARY_VALUE = 999999999999


class GroupTotals(TypedDict):
    """One K4 page's section A totals in whole kronor (3300, 3301, 3304, 3305)."""

    total_sold: int
    total_cost_basis: int
    total_profit: int
    total_loss: int


def check_income_year(year: object) -> int:
    """``year`` if it can name a K4 block (``K4-{year}P4``); else ValidationError."""
    if (
        isinstance(year, bool)
        or not isinstance(year, int)
        or not MIN_INCOME_YEAR <= year <= MAX_INCOME_YEAR
    ):
        raise ValidationError(
            f"year must be a four-digit income year from {MIN_INCOME_YEAR}, "
            f"got {year!r}",
            field="year",
            value=year,
        )
    return year


def check_items_per_group(items_per_group: object) -> int:
    """Rows per page: 1 to ``K4_SECTION_A_ROWS``, else ``ValidationError``."""
    if (
        isinstance(items_per_group, bool)
        or not isinstance(items_per_group, int)
        or not 1 <= items_per_group <= K4_SECTION_A_ROWS
    ):
        raise ValidationError(
            f"items_per_group must be between 1 and {K4_SECTION_A_ROWS} "
            f"(the rows of K4 section A), got {items_per_group!r}",
            field="items_per_group",
            value=items_per_group,
        )
    return items_per_group


def _is_row_index(value: object) -> bool:
    """0 to K4_SECTION_A_ROWS - 1, as a real int: untyped callers may pass 0.5 or "1",
    and 0.5 used to produce the field code '3105.0'."""
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and 0 <= value < K4_SECTION_A_ROWS
    )


def check_crypto_groups(groups: Sequence[CryptoSRUGroup]) -> list[CryptoSRUGroup]:
    """Crypto pages fit to merge, else ``ValidationError``.

    Every line must be ``#UPPGIFT <code> <value>`` with a K4 section D code (anything
    else would collide with the share rows on the same page, or is not a field), and
    pages must be numbered 1..n: a duplicate number used to drop a page and add an
    empty one, and a gap used to drop the pages after it.
    """
    numbers = sorted(group["group_number"] for group in groups)
    if numbers != list(range(1, len(numbers) + 1)):
        raise ValidationError(
            f"crypto pages must be numbered 1..{len(numbers)}, got {numbers}",
            field="crypto_groups",
        )
    for group in groups:
        for line in group["uppgifter"]:
            match = _UPPGIFT_LINE.fullmatch(line)
            if match is None or int(match.group(1)) not in K4_SECTION_D_FIELDS:
                raise ValidationError(
                    f"crypto page {group['group_number']}: {line!r} is not a "
                    "K4 section D line (#UPPGIFT 3410-3475 or 3500/3501/3503/3504)",
                    field="crypto_groups",
                )
    return sorted(groups, key=lambda group: group["group_number"])


def _timestamp() -> str:
    """Local date and time for #SKAPAD and #IDENTITET, as ``YYYYMMDD HHMMSS``."""
    return datetime.now().astimezone().strftime("%Y%m%d %H%M%S")


def _amount_or_zero(
    row: Mapping[str, object], key: str, stock_name: str, *, log: bool
) -> Decimal:
    """An amount from an unvalidated row; 0 if it is unreadable or not finite.

    format_trade_item_sru and calculate_group_totals both read amounts through this,
    so a row and the totals below it always agree. They used to differ: the row was
    written with 0 while the totals dropped the whole row, cost included.
    """
    try:
        amount = _as_decimal(row.get(key, 0))
        if amount.is_finite():
            return amount
    except Exception:  # noqa: S110 -- any unreadable value means "use 0", logged below
        pass
    if log:
        logger.warning("Invalid '%s' for '%s'. Using 0.", key, stock_name)
    return Decimal(0)


def _as_decimal(value: object) -> Decimal:
    """How every amount in this module is read (see ``to_decimal``)."""
    return to_decimal(value)


def round_k4_sale_price(value: Amount) -> int:
    """Forsaljningspris in whole kronor: oren nedat (`K4_SALE_PRICE_ROUNDING`)."""
    return int(
        to_decimal(value).quantize(
            WHOLE_NUMBER_ROUNDING, rounding=K4_SALE_PRICE_ROUNDING
        )
    )


def round_k4_quantity(value: Amount) -> int:
    """Antal in whole units, rounded **up**.

    Fractional shares and crypto amounts are common, but the K4 antal field is a whole
    number. Rounding up means a sale of 0.25 units is reported as 1 rather than 0; antal
    is informational and does not enter the vinst/förlust calculation.
    """
    return int(
        to_decimal(value).quantize(WHOLE_NUMBER_ROUNDING, rounding=ROUND_CEILING)
    )


def round_k4_cost_basis(value: Amount) -> int:
    """Omkostnadsbelopp in whole kronor: oren uppat (`K4_COST_BASIS_ROUNDING`)."""
    return int(
        to_decimal(value).quantize(
            WHOLE_NUMBER_ROUNDING, rounding=K4_COST_BASIS_ROUNDING
        )
    )


def _comparable_profit_loss(value: object, stock_name: str) -> Decimal | None:
    """The caller's own profit/loss, or `None` when there is nothing to compare.

    Diagnostic only -- the written figure is derived (see `K4_SALE_PRICE_ROUNDING`). An
    absent key, an explicit `None`, an unparseable string and a non-finite `Decimal` all
    mean the same thing here: the caller made no claim this row can be checked against.
    A stated 0 is not one of them.

    Every one of those must be swallowed rather than raised. `format_trade_item_sru`
    skips a row whose formatting throws, while `calculate_group_totals` no longer reads
    this key at all and would still count the row -- so letting a bad diagnostic value
    escape produces a group total with no row above it. NaN is the case that reached
    this docstring: `Decimal("NaN")` parses happily and only fails at `int()`.
    """
    if value is None:
        return None
    try:
        supplied = Decimal(str(value))
        if not supplied.is_finite():
            raise ValueError("not a finite amount")
        return supplied
    except Exception:
        logger.warning(
            "Invalid 'profit/loss' for '%s'. Not cross-checking this row.", stock_name
        )
        return None


def generate_sru_info_content(
    personal_number: str,
    full_name: str,
    postal_code: str,
    city_name: str,
) -> str:
    """Generates the content for an SRU-format info file."""
    current_datetime = _timestamp()
    return f"""#DATABESKRIVNING_START
#PRODUKT SRU
#SKAPAD {current_datetime}
#FILNAMN BLANKETTER.SRU
#DATABESKRIVNING_SLUT
#MEDIELEV_START
#ORGNR {personal_number}
#NAMN {full_name}
#POSTNR {postal_code}
#POSTORT {city_name}
#MEDIELEV_SLUT
"""


def generate_sru_header(
    year_of_report: int, personal_number: str, full_name: str
) -> str:
    """Generates the header section of the SRU K4 file."""
    check_income_year(year_of_report)
    current_datetime_str = _timestamp()
    form_year_suffix = str(year_of_report)

    return f"""{SRU_FIELD_BLANKETT_START.format(year=form_year_suffix)}
{
        SRU_FIELD_IDENTITET.format(
            personal_number=personal_number, datetime=current_datetime_str
        )
    } {SRU_FIELD_NAMN.format(full_name=full_name)}
"""


def format_trade_item_sru(
    row_data: Mapping[str, object],
    item_index_in_group: int,
    group_index: int,  # Currently unused but kept for API compatibility
    character_converter: CharacterConverter | None = None,
) -> str:
    """
    Formats the SRU lines for a single trade item (quantity, stock, sale, cost,
    profit/loss). Handles data conversion, rounding, and profit/loss split. Quantity
    must be an integer between 0 and MAX_MONETARY_VALUE. All monetary values (sale
    price, cost basis, profit, loss) must be integers between 0 and MAX_MONETARY_VALUE.

    Expected keys in row_data:
    - quantity: Number of shares/units sold
    - stock: Stock name/identifier
    - net value: Sale price
    - total net value of purchase: Cost basis
    - profit/loss: optional. Only cross-checked against the derived vinst/forlust, never
      written -- see `K4_SALE_PRICE_ROUNDING` for why the row derives its own.
    """
    # Before the try below, which turns errors into a skipped row: a row index past
    # section A's ninth row would write field codes K4 does not have (3190+).
    if not _is_row_index(item_index_in_group):
        raise ValidationError(
            f"item_index_in_group must be 0-{K4_SECTION_A_ROWS - 1} "
            f"(K4 section A rows), got {item_index_in_group!r}",
            field="item_index_in_group",
            value=item_index_in_group,
        )
    content = ""

    try:
        # Validate quantity is within allowed range
        quantity = _within_monetary_range(
            round_k4_quantity(_as_decimal(row_data.get("quantity", 0))),
            "Invalid quantity %s for stock '%s'. "
            "Quantity must be between 0 and %s. Using 0.",
            row_data.get("stock", "UNKNOWN_STOCK"),
        )

        stock_name_raw: str = str(row_data.get("stock", "UNKNOWN_STOCK"))
        if character_converter:
            stock_name = character_converter(stock_name_raw)
        else:
            stock_name = stock_name_raw
        # Limit stock name length
        stock_name = stock_name[:NUMBER_OF_CHARACTERS_FOR_STOCK_NAME]

        amount_sold_for_decimal = _amount_or_zero(
            row_data, "net value", stock_name, log=True
        )
        cost_basis_decimal = _amount_or_zero(
            row_data, "total net value of purchase", stock_name, log=True
        )

        # Convert to integers and validate ranges. Each column has its own direction --
        # see `K4_SALE_PRICE_ROUNDING`.
        amount_sold_for = round_k4_sale_price(amount_sold_for_decimal)
        cost_basis = round_k4_cost_basis(cost_basis_decimal)
        profit_loss_from_data = _comparable_profit_loss(
            row_data.get("profit/loss"), stock_name
        )

        # Validate monetary values are within allowed range
        amount_sold_for = _within_monetary_range(
            amount_sold_for,
            "Invalid sale price %s for '%s'. Must be between 0 and %s. Using 0.",
            stock_name,
        )
        cost_basis = _within_monetary_range(
            cost_basis,
            "Invalid cost basis %s for '%s'. Must be between 0 and %s. Using 0.",
            stock_name,
        )
        # The written profit/loss needs no range check of its own: it is the difference
        # of two values both already clamped to [0, MAX_MONETARY_VALUE], so it cannot
        # leave [-MAX_MONETARY_VALUE, MAX_MONETARY_VALUE]. An out-of-range `profit/loss`
        # in the input is reported by the mismatch warning below rather than silently
        # zeroed, which would have turned a wild input into a clean-looking row.

        # Skatteverket derives vinst/forlust from the two rounded columns, so this is
        # the value written -- not the caller's own `profit/loss`, which cannot be
        # reconciled with the row printed above it.
        profit_loss = amount_sold_for - cost_basis

        # The question this asks is whether the *caller's* row adds up, which is a fact
        # about the input, so it is asked of the unrounded amounts. Comparing the
        # rounded ones instead accuses correct input: `floor(sale) - ceil(cost)` sits
        # anywhere in `(sale - cost - 2, sale - cost]`, so a self-consistent row can
        # differ from its own rounded profit by a full 2 -- 10.99 / 10.01 / 0.98 is one,
        # and 12% of rows are. The tolerance is the one the validator layer already
        # documents for this comparison.
        if profit_loss_from_data is not None:
            difference = abs(
                (amount_sold_for_decimal - cost_basis_decimal) - profit_loss_from_data
            )
            if difference > Decimal("1"):
                logger.warning(
                    "Supplied profit/loss for '%s' does not match its own sale price "
                    "minus cost basis: data=%s, sale-cost=%s. Writing the derived %s.",
                    stock_name,
                    profit_loss_from_data,
                    amount_sold_for_decimal - cost_basis_decimal,
                    profit_loss,
                )

        base_code = 3100 + (item_index_in_group * 10)
        content += f"#UPPGIFT {base_code} {quantity}\n"
        content += f"#UPPGIFT {base_code + 1} {stock_name}\n"
        content += f"#UPPGIFT {base_code + 2} {amount_sold_for}\n"
        content += f"#UPPGIFT {base_code + 3} {cost_basis}\n"

        if profit_loss >= 0:
            content += f"#UPPGIFT {base_code + 4} {profit_loss}\n"
        else:
            content += f"#UPPGIFT {base_code + 5} {abs(profit_loss)}\n"

    except Exception as e:
        logger.error(
            "Error formatting trade item '%s': %s. Skipping this item in output.",
            row_data.get("stock", "N/A"),
            e,
        )
        return ""

    return content


def _within_monetary_range(amount: int, message: str, *context: object) -> int:
    """``amount`` if within [0, MAX_MONETARY_VALUE]; otherwise log and return 0.

    ``message`` gets ``amount``, then ``context``, then the maximum.
    """
    if 0 <= amount <= MAX_MONETARY_VALUE:
        return amount
    logger.error(message, amount, *context, MAX_MONETARY_VALUE)
    return 0


_TotalKey = Literal["total_sold", "total_cost_basis", "total_profit", "total_loss"]


def _add_capped(totals: GroupTotals, key: _TotalKey, amount: int, label: str) -> None:
    """Add ``amount`` to ``totals[key]``, capping the total at MAX_MONETARY_VALUE."""
    if totals[key] + amount > MAX_MONETARY_VALUE:
        logger.error(
            "Group total %s would exceed maximum allowed value (%s). "
            "Truncating to maximum.",
            label,
            MAX_MONETARY_VALUE,
        )
        totals[key] = MAX_MONETARY_VALUE
    else:
        totals[key] += amount


def calculate_group_totals(group_data: Sequence[Mapping[str, object]]) -> GroupTotals:
    """
    Calculates the total sales, cost basis, profit, and loss for a group of trade items.
    All monetary values must be integers between 0 and MAX_MONETARY_VALUE.
    Profits and losses are tracked separately, with losses stored as positive numbers.

    Each row is rounded to whole kronor exactly as `format_trade_item_sru` rounds it --
    see `K4_SALE_PRICE_ROUNDING` -- and only then summed, so every total is the sum of
    the column printed above it. A row's `profit/loss` is not read here: vinst/forlust
    is derived from the two rounded amounts, the way Skatteverket's own K4 does it.

    Expected keys in each item of group_data:
    - net value: Sale price
    - total net value of purchase: Cost basis
    """
    totals: GroupTotals = {
        "total_sold": 0,
        "total_cost_basis": 0,
        "total_profit": 0,
        "total_loss": 0,
    }

    for row in group_data:
        try:
            # Rounded exactly as `format_trade_item_sru` rounds the rows above these
            # totals -- each column its own direction, vinst/forlust derived. A total
            # that rounded differently from its own rows would not be the column's sum.
            amount_sold_for = _within_monetary_range(
                round_k4_sale_price(_amount_or_zero(row, "net value", "", log=False)),
                "Invalid sale price %s in group totals. "
                "Must be between 0 and %s. Using 0.",
            )
            cost_basis = _within_monetary_range(
                round_k4_cost_basis(
                    _amount_or_zero(row, "total net value of purchase", "", log=False)
                ),
                "Invalid cost basis %s in group totals. "
                "Must be between 0 and %s. Using 0.",
            )
            item_profit_loss = amount_sold_for - cost_basis

            _add_capped(totals, "total_sold", amount_sold_for, "sale price")
            _add_capped(totals, "total_cost_basis", cost_basis, "cost basis")
            if item_profit_loss >= 0:
                _add_capped(totals, "total_profit", item_profit_loss, "profit")
            else:
                _add_capped(totals, "total_loss", abs(item_profit_loss), "loss")

        except Exception as e:
            logger.warning(
                "Could not sum values for a row in the current group: %s. "
                "Skipping this row for totals calculation.",
                e,
            )
            continue

    logger.debug(
        "Group totals - Sales: %s, Cost: %s, Profit: %s, Loss: %s",
        totals["total_sold"],
        totals["total_cost_basis"],
        totals["total_profit"],
        totals["total_loss"],
    )

    return totals


def format_group_totals_sru(totals: GroupTotals) -> str:
    """Formats the SRU lines for group totals (Summa Försäljningspris, etc.)."""
    content = ""
    content += f"{SRU_FIELD_GROUP_TOTAL_SOLD.format(amount=totals['total_sold'])}\n"
    cost_basis_line = SRU_FIELD_GROUP_TOTAL_COST_BASIS.format(
        amount=totals["total_cost_basis"]
    )
    content += f"{cost_basis_line}\n"

    if totals["total_profit"] > 0:
        content += (
            f"{SRU_FIELD_GROUP_TOTAL_PROFIT.format(amount=totals['total_profit'])}\n"
        )
    if totals["total_loss"] > 0:
        content += f"{SRU_FIELD_GROUP_TOTAL_LOSS.format(amount=totals['total_loss'])}\n"
    return content


def generate_sru_trade_content(  # noqa: PLR0917 -- positional public API
    trade_data: Sequence[Mapping[str, object]],
    full_name: str,
    personal_number: str,
    year: int = 2024,
    items_per_group: int = 9,
    character_converter: CharacterConverter | None = None,
) -> str:
    """
    Generates the main trade content section of the SRU file, including
    individual items and group totals. Handles the grouping logic.
    Group numbers must be integers between 1 and MAX_GROUP_NUMBER.
    Each group starts with a new BLANKETT and ends with BLANKETTSLUT.

    Args:
        trade_data: List of trade dictionaries with required keys
        full_name: Full name for SRU file
        personal_number: Personal number for SRU file
        year: Year for the SRU file
        items_per_group: Number of items per group (default 9)
    """
    # Calculate datetime once at the start
    check_income_year(year)
    check_items_per_group(items_per_group)
    identity_line = SRU_FIELD_IDENTITET.format(
        personal_number=personal_number, datetime=_timestamp()
    )

    content_trades = ""
    group_counter = 0
    # Totals cover the rows actually written: format_trade_item_sru skips a row it
    # cannot format, and summing the raw page used to count that row anyway.
    written_rows: list[Mapping[str, object]] = []

    for i, row_data in enumerate(trade_data):
        if i % items_per_group == 0:
            written_rows = []
            group_counter += 1
            # Ensure group number is within valid range
            if group_counter > MAX_GROUP_NUMBER:
                logger.error(
                    "Maximum number of groups (%s) exceeded. "
                    "Cannot generate more groups.",
                    MAX_GROUP_NUMBER,
                )
                break

            # Add new BLANKETT section for each group
            content_trades += f"{SRU_FIELD_BLANKETT_START.format(year=str(year))}\n"
            content_trades += f"{identity_line}\n"
            content_trades += f"{SRU_FIELD_NAMN.format(full_name=full_name)}\n"
            content_trades += (
                f"{SRU_FIELD_UPPGIFT_GROUP_START.format(group_number=group_counter)}\n"
            )

        item_index_in_group = i % items_per_group
        group_index = group_counter - 1  # Zero-based index for group
        row_lines = format_trade_item_sru(
            row_data, item_index_in_group, group_index, character_converter
        )
        if row_lines:
            written_rows.append(row_data)
        content_trades += row_lines

        if (i + 1) % items_per_group == 0 or i == len(trade_data) - 1:
            group_totals = calculate_group_totals(written_rows)
            content_trades += format_group_totals_sru(group_totals)
            # Add BLANKETTSLUT at the end of each group
            content_trades += f"{SRU_FIELD_BLANKETT_END}\n"

    return content_trades


def generate_sru_footer() -> str:
    """Generates the footer section of the SRU file."""
    return f"{SRU_FIELD_FILE_END}\n"


def merge_sru_groups(
    stock_content: str,
    crypto_groups: Sequence[CryptoSRUGroup],
    full_name: str,
    personal_number: str,
    year: int = 2024,
) -> str:
    """
    Merges stock and crypto groups, ensuring stocks come first followed by crypto
    UPPGIFTER. Returns the merged content as a string.

    Args:
        stock_content: SRU content for stock trades
        crypto_groups: List of crypto group dictionaries
        full_name: Full name for SRU file
        personal_number: Personal number for SRU file
        year: Year for the SRU file
    """
    check_income_year(year)
    crypto_by_number = {
        group["group_number"]: group for group in check_crypto_groups(crypto_groups)
    }
    # Calculate datetime once at the start
    current_datetime_str = _timestamp()

    # Split stock content into groups
    stock_groups = stock_content.split("#BLANKETT K4-")
    # Remove empty groups
    stock_groups = [g for g in stock_groups if g.strip()]

    # Get the maximum number of groups
    max_stock_groups = len(stock_groups)
    max_crypto_groups = len(crypto_groups)
    max_groups = max(max_stock_groups, max_crypto_groups)

    logger.debug(
        "Merging %s stock page(s) and %s crypto page(s)",
        max_stock_groups,
        max_crypto_groups,
    )

    merged_content = ""

    # Process each group number
    for group_num in range(1, max_groups + 1):
        # Add group header
        merged_content += f"#BLANKETT K4-{year}P4\n"
        merged_content += f"#IDENTITET {personal_number} {current_datetime_str}\n"
        merged_content += f"#NAMN {full_name}\n"
        merged_content += f"#UPPGIFT 7014 {group_num}\n"

        # Add stock content if available
        if group_num <= max_stock_groups:
            stock_group = stock_groups[group_num - 1]
            # Extract only UPPGIFT lines
            stock_uppgifter = [
                line
                for line in stock_group.split("\n")
                if line.startswith("#UPPGIFT 31") or line.startswith("#UPPGIFT 33")
            ]
            merged_content += "\n".join(stock_uppgifter) + "\n"

        # Add crypto content if available
        crypto_group = crypto_by_number.get(group_num)
        if crypto_group:
            merged_content += "\n".join(crypto_group["uppgifter"]) + "\n"

        # Add group footer
        merged_content += "#BLANKETTSLUT\n"

    # Add file footer
    merged_content += "#FIL_SLUT\n"

    return merged_content


def write_sru_file(file_path: str, content: str) -> bool:
    """
    Writes the given content string to a file in ISO-8859-1 (`SRU_ENCODING`), creating
    directories if needed. The file is readable and writable by its owner only (0600).
    Returns True on success, False on failure, including when the content has characters
    ISO-8859-1 cannot represent (see `encode_sru_text`).
    """
    try:
        data = encode_sru_text(content)
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        # SRU files hold a personnummer and financial data: create them readable by the
        # owner only. chmod as well, because O_CREAT's mode does not apply to a file
        # that already exists. (On Windows only the read-only bit is affected.)
        fd = os.open(file_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "wb") as file:
            file.write(data)
        path.chmod(0o600)
        logger.info("SRU file '%s' has been successfully created.", file_path)
        return True
    except DataFormatError as e:
        logger.error("Failed to write SRU file '%s': %s", file_path, e)
        return False
    except OSError as e:
        logger.error("Failed to write SRU file '%s': %s", file_path, e)
        return False
    except Exception as e:
        logger.error(
            "An unexpected error occurred while writing SRU file '%s': %s", file_path, e
        )
        return False


def read_crypto_sru_content(crypto_file_path: str) -> list[CryptoSRUGroup]:
    """
    Reads the crypto SRU content from the specified file path. Returns a list of
    dictionaries, where each dictionary represents a group and contains:
    - 'group_number': The group number (from UPPGIFT 7014)
    - 'uppgifter': List of UPPGIFT lines for that group
    """
    if not Path(crypto_file_path).exists():
        logger.warning(
            "Crypto SRU file not found at %s. Continuing without crypto data.",
            crypto_file_path,
        )
        return []

    logger.debug("Reading crypto SRU file: %s", crypto_file_path)

    try:
        raw = Path(crypto_file_path).read_bytes()
    except OSError as e:
        # Not swallowed: an unreadable crypto file used to give [] and a K4 file that
        # silently lacked the crypto pages.
        raise FileOperationError(
            f"Cannot read crypto SRU file {crypto_file_path}: {e}",
            file_path=crypto_file_path,
            operation="read",
        ) from e

    content = decode_sru_bytes(raw).replace("\r\n", "\n")

    # Split content into pages. 7014 (the page number) may come anywhere on a page:
    # several K4 tools write it last, and collecting only the lines after it read such
    # files as empty. It is optional in Skatteverket's description, so a page without
    # it is numbered by its position in the file.
    pages = content.split("#BLANKETT K4-")[1:]
    parsed_groups: list[CryptoSRUGroup] = []

    for position, page in enumerate(pages, start=1):
        group_number: int | None = None
        uppgifter: list[str] = []
        for raw_line in page.split("\n"):
            line = raw_line.strip()
            if not line.startswith("#UPPGIFT"):
                continue  # #IDENTITET, #NAMN, #BLANKETTSLUT, #FIL_SLUT, blank lines
            if line.split()[1:2] == ["7014"]:
                try:
                    group_number = int(line.split()[2])
                except (ValueError, IndexError):
                    raise DataFormatError(
                        f"Crypto SRU file {crypto_file_path}, page {position}: "
                        f"cannot read the page number in {line!r}",
                        expected_format="#UPPGIFT 7014 <number>",
                    ) from None
                continue
            uppgifter.append(line)

        if uppgifter:
            parsed_groups.append(
                {
                    "group_number": position if group_number is None else group_number,
                    "uppgifter": uppgifter,
                }
            )

    logger.info("Read %s page(s) from crypto SRU file", len(parsed_groups))
    return parsed_groups
