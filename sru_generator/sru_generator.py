"""
SRU Generator - Main module for generating Swedish SRU files.

This module provides all the core functionality for generating SRU files
according to Swedish tax authority specifications.
"""

import os
from datetime import datetime
from decimal import ROUND_HALF_EVEN, Decimal
from typing import Any, Dict, List

from .utils import setup_logger

# Set up logger
logger = setup_logger()

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
NUMBER_OF_CHARACTERS_FOR_STOCK_NAME = 80

# Define numeric limits for SRU fields
MAX_GROUP_NUMBER = 99999
MAX_MONETARY_VALUE = 999999999999


def generate_sru_info_content(
    personal_number: str,
    full_name: str,
    postal_code: str,
    city_name: str,
) -> str:
    """Generates the content for an SRU-format info file."""
    current_datetime: str = datetime.now().strftime("%Y%m%d %H%M%S")
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
    current_datetime_str: str = datetime.now().strftime("%Y%m%d %H%M%S")
    form_year_suffix = str(year_of_report)

    return f"""{SRU_FIELD_BLANKETT_START.format(year=form_year_suffix)}
{SRU_FIELD_IDENTITET.format(personal_number=personal_number, datetime=current_datetime_str)}
{SRU_FIELD_NAMN.format(full_name=full_name)}
"""


def format_trade_item_sru(
    row_data: Dict[str, Any],
    item_index_in_group: int,
    group_index: int,  # Currently unused but kept for API compatibility
    character_converter: callable = None,
) -> str:
    """
    Formats the SRU lines for a single trade item (quantity, stock, sale, cost, profit/loss).
    Handles data conversion, rounding, and profit/loss split.
    Quantity must be an integer between 0 and MAX_MONETARY_VALUE.
    All monetary values (sale price, cost basis, profit, loss) must be integers between 0 and MAX_MONETARY_VALUE.

    Expected keys in row_data:
    - quantity: Number of shares/units sold
    - stock: Stock name/identifier
    - net value: Sale price
    - total net value of purchase: Cost basis
    - profit/loss: Profit or loss amount
    """
    content = ""

    try:
        # Validate quantity is within allowed range
        raw_quantity = int(row_data.get("quantity", 0))
        if raw_quantity < 0 or raw_quantity > MAX_MONETARY_VALUE:
            logger.error(
                "Invalid quantity %s for stock '%s'. "
                "Quantity must be between 0 and %s. Using 0.",
                raw_quantity,
                row_data.get("stock", "UNKNOWN_STOCK"),
                MAX_MONETARY_VALUE,
            )
            quantity = 0
        else:
            quantity = raw_quantity

        stock_name_raw: str = str(row_data.get("stock", "UNKNOWN_STOCK"))
        if character_converter:
            stock_name: str = character_converter(stock_name_raw)
        else:
            stock_name: str = stock_name_raw
        # Limit stock name length
        stock_name = stock_name[:NUMBER_OF_CHARACTERS_FOR_STOCK_NAME]

        try:
            amount_sold_for_decimal = Decimal(str(row_data.get("net value", 0)))
        except Exception:
            logger.warning("Invalid 'net value' for '%s'. Using 0.", stock_name)
            amount_sold_for_decimal = Decimal(0)

        try:
            cost_basis_decimal = Decimal(
                str(row_data.get("total net value of purchase", 0))
            )
        except Exception:
            logger.warning(
                "Invalid 'total net value of purchase' for '%s'. Using 0.", stock_name
            )
            cost_basis_decimal = Decimal(0)

        try:
            profit_loss_from_data_decimal = Decimal(str(row_data.get("profit/loss", 0)))
        except Exception:
            logger.warning("Invalid 'profit/loss' for '%s'. Using 0.", stock_name)
            profit_loss_from_data_decimal = Decimal(0)

        # Convert to integers and validate ranges
        amount_sold_for = int(
            amount_sold_for_decimal.quantize(
                WHOLE_NUMBER_ROUNDING, rounding=ROUND_HALF_EVEN
            )
        )
        cost_basis = int(
            cost_basis_decimal.quantize(WHOLE_NUMBER_ROUNDING, rounding=ROUND_HALF_EVEN)
        )
        profit_loss_from_data = int(
            profit_loss_from_data_decimal.quantize(
                WHOLE_NUMBER_ROUNDING, rounding=ROUND_HALF_EVEN
            )
        )

        # Validate monetary values are within allowed range
        if amount_sold_for < 0 or amount_sold_for > MAX_MONETARY_VALUE:
            logger.error(
                "Invalid sale price %s for '%s'. Must be between 0 and %s. Using 0.",
                amount_sold_for,
                stock_name,
                MAX_MONETARY_VALUE,
            )
            amount_sold_for = 0
        if cost_basis < 0 or cost_basis > MAX_MONETARY_VALUE:
            logger.error(
                "Invalid cost basis %s for '%s'. Must be between 0 and %s. Using 0.",
                cost_basis,
                stock_name,
                MAX_MONETARY_VALUE,
            )
            cost_basis = 0
        if abs(profit_loss_from_data) > MAX_MONETARY_VALUE:
            logger.error(
                "Invalid profit/loss %s for '%s'. Must be between -%s and %s. Using 0.",
                profit_loss_from_data,
                stock_name,
                MAX_MONETARY_VALUE,
                MAX_MONETARY_VALUE,
            )
            profit_loss_from_data = 0

        calculated_profit_loss = amount_sold_for - cost_basis
        difference = abs(calculated_profit_loss - profit_loss_from_data)
        if difference > 1:  # Using 1 since we're now working with integers
            logger.warning(
                "Calculated profit/loss mismatch for '%s': calculated=%s, data=%s. Using data value for SRU.",
                stock_name,
                calculated_profit_loss,
                profit_loss_from_data,
            )
        elif difference > 0:
            logger.info(
                "Small profit/loss difference for '%s': calculated=%s, data=%s. Difference=%s. Using data value for SRU.",
                stock_name,
                calculated_profit_loss,
                profit_loss_from_data,
                difference,
            )

        base_code = 3100 + (item_index_in_group * 10)
        content += f"#UPPGIFT {base_code} {quantity}\n"
        content += f"#UPPGIFT {base_code + 1} {stock_name}\n"
        content += f"#UPPGIFT {base_code + 2} {amount_sold_for}\n"
        content += f"#UPPGIFT {base_code + 3} {cost_basis}\n"

        if profit_loss_from_data >= 0:
            content += f"#UPPGIFT {base_code + 4} {profit_loss_from_data}\n"
        else:
            content += f"#UPPGIFT {base_code + 5} {abs(profit_loss_from_data)}\n"

    except Exception as e:
        logger.error(
            "Error formatting trade item '%s': %s. Skipping this item in output.",
            row_data.get("stock", "N/A"),
            e,
        )
        return ""

    return content


def calculate_group_totals(group_data: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Calculates the total sales, cost basis, profit, and loss for a group of trade items.
    All monetary values must be integers between 0 and MAX_MONETARY_VALUE.
    Profits and losses are tracked separately, with losses stored as positive numbers.

    Expected keys in each item of group_data:
    - net value: Sale price
    - total net value of purchase: Cost basis
    - profit/loss: Profit or loss amount
    """
    group_total_amount_sold = 0
    group_total_cost_basis = 0
    current_group_total_profit = 0
    current_group_total_loss = 0

    for row in group_data:
        try:
            # Convert to integers and validate ranges
            amount_sold_for = int(
                Decimal(str(row.get("net value", 0))).quantize(
                    WHOLE_NUMBER_ROUNDING, rounding=ROUND_HALF_EVEN
                )
            )
            cost_basis = int(
                Decimal(str(row.get("total net value of purchase", 0))).quantize(
                    WHOLE_NUMBER_ROUNDING, rounding=ROUND_HALF_EVEN
                )
            )
            item_pl_from_data = int(
                Decimal(str(row.get("profit/loss", 0))).quantize(
                    WHOLE_NUMBER_ROUNDING, rounding=ROUND_HALF_EVEN
                )
            )

            # Validate monetary values are within allowed range
            if amount_sold_for < 0 or amount_sold_for > MAX_MONETARY_VALUE:
                logger.error(
                    "Invalid sale price %s in group totals. Must be between 0 and %s. Using 0.",
                    amount_sold_for,
                    MAX_MONETARY_VALUE,
                )
                amount_sold_for = 0
            if cost_basis < 0 or cost_basis > MAX_MONETARY_VALUE:
                logger.error(
                    "Invalid cost basis %s in group totals. Must be between 0 and %s. Using 0.",
                    cost_basis,
                    MAX_MONETARY_VALUE,
                )
                cost_basis = 0
            if abs(item_pl_from_data) > MAX_MONETARY_VALUE:
                logger.error(
                    "Invalid profit/loss %s in group totals. Must be between -%s and %s. Using 0.",
                    item_pl_from_data,
                    MAX_MONETARY_VALUE,
                    MAX_MONETARY_VALUE,
                )
                item_pl_from_data = 0

            # Add to totals with validation
            if group_total_amount_sold + amount_sold_for > MAX_MONETARY_VALUE:
                logger.error(
                    "Group total sale price would exceed maximum allowed value (%s). Truncating to maximum.",
                    MAX_MONETARY_VALUE,
                )
                group_total_amount_sold = MAX_MONETARY_VALUE
            else:
                group_total_amount_sold += amount_sold_for

            if group_total_cost_basis + cost_basis > MAX_MONETARY_VALUE:
                logger.error(
                    "Group total cost basis would exceed maximum allowed value (%s). Truncating to maximum.",
                    MAX_MONETARY_VALUE,
                )
                group_total_cost_basis = MAX_MONETARY_VALUE
            else:
                group_total_cost_basis += cost_basis

            # Handle profit/loss separately
            if item_pl_from_data >= 0:
                if current_group_total_profit + item_pl_from_data > MAX_MONETARY_VALUE:
                    logger.error(
                        "Group total profit would exceed maximum allowed value (%s). Truncating to maximum.",
                        MAX_MONETARY_VALUE,
                    )
                    current_group_total_profit = MAX_MONETARY_VALUE
                else:
                    current_group_total_profit += item_pl_from_data
            else:
                loss_amount = abs(item_pl_from_data)
                if current_group_total_loss + loss_amount > MAX_MONETARY_VALUE:
                    logger.error(
                        "Group total loss would exceed maximum allowed value (%s). Truncating to maximum.",
                        MAX_MONETARY_VALUE,
                    )
                    current_group_total_loss = MAX_MONETARY_VALUE
                else:
                    current_group_total_loss += loss_amount

        except Exception as e:
            logger.warning(
                "Could not sum values for a row in the current group: %s. Skipping this row for totals calculation.",
                e,
            )
            continue

    logger.info(
        f"Group totals - Sales: {group_total_amount_sold}, Cost: {group_total_cost_basis}, "
        f"Profit: {current_group_total_profit}, Loss: {current_group_total_loss}"
    )

    return {
        "total_sold": group_total_amount_sold,
        "total_cost_basis": group_total_cost_basis,
        "total_profit": current_group_total_profit,
        "total_loss": current_group_total_loss,
    }


def format_group_totals_sru(totals: Dict[str, int]) -> str:
    """Formats the SRU lines for group totals (Summa Försäljningspris, etc.)."""
    content = ""
    content += f"{SRU_FIELD_GROUP_TOTAL_SOLD.format(amount=totals['total_sold'])}\n"
    content += f"{SRU_FIELD_GROUP_TOTAL_COST_BASIS.format(amount=totals['total_cost_basis'])}\n"

    if totals["total_profit"] > 0:
        content += (
            f"{SRU_FIELD_GROUP_TOTAL_PROFIT.format(amount=totals['total_profit'])}\n"
        )
    if totals["total_loss"] > 0:
        content += f"{SRU_FIELD_GROUP_TOTAL_LOSS.format(amount=totals['total_loss'])}\n"
    return content


def generate_sru_trade_content(
    trade_data: List[Dict[str, Any]],
    full_name: str,
    personal_number: str,
    year: int = 2024,
    items_per_group: int = 9,
    character_converter: callable = None,
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
    current_datetime_str = datetime.now().strftime("%Y%m%d %H%M%S")

    content_trades = ""
    group_start_index = 0
    group_counter = 0

    for i, row_data in enumerate(trade_data):
        if i % items_per_group == 0:
            group_start_index = i
            group_counter += 1
            # Ensure group number is within valid range
            if group_counter > MAX_GROUP_NUMBER:
                logger.error(
                    "Maximum number of groups (%s) exceeded. Cannot generate more groups.",
                    MAX_GROUP_NUMBER,
                )
                break

            # Add new BLANKETT section for each group
            content_trades += f"{SRU_FIELD_BLANKETT_START.format(year=str(year))}\n"
            content_trades += f"{SRU_FIELD_IDENTITET.format(personal_number=personal_number, datetime=current_datetime_str)}\n"
            content_trades += f"{SRU_FIELD_NAMN.format(full_name=full_name)}\n"
            content_trades += (
                f"{SRU_FIELD_UPPGIFT_GROUP_START.format(group_number=group_counter)}\n"
            )

        item_index_in_group = i % items_per_group
        group_index = group_counter - 1  # Zero-based index for group
        content_trades += format_trade_item_sru(
            row_data, item_index_in_group, group_index, character_converter
        )

        if (i + 1) % items_per_group == 0 or i == len(trade_data) - 1:
            current_group_end_index = i + 1
            current_group_data = trade_data[group_start_index:current_group_end_index]
            group_totals = calculate_group_totals(current_group_data)
            content_trades += format_group_totals_sru(group_totals)
            # Add BLANKETTSLUT at the end of each group
            content_trades += f"{SRU_FIELD_BLANKETT_END}\n"

    return content_trades


def generate_sru_footer() -> str:
    """Generates the footer section of the SRU file."""
    return f"{SRU_FIELD_FILE_END}\n"


def merge_sru_groups(
    stock_content: str,
    crypto_groups: List[Dict[str, List[str]]],
    full_name: str,
    personal_number: str,
    year: int = 2024,
) -> str:
    """
    Merges stock and crypto groups, ensuring stocks come first followed by crypto UPPGIFTER.
    Returns the merged content as a string.

    Args:
        stock_content: SRU content for stock trades
        crypto_groups: List of crypto group dictionaries
        full_name: Full name for SRU file
        personal_number: Personal number for SRU file
        year: Year for the SRU file
    """
    # Calculate datetime once at the start
    current_datetime_str = datetime.now().strftime("%Y%m%d %H%M%S")

    # Split stock content into groups
    stock_groups = stock_content.split("#BLANKETT K4-")
    # Remove empty groups
    stock_groups = [g for g in stock_groups if g.strip()]

    # Get the maximum number of groups
    max_stock_groups = len(stock_groups)
    max_crypto_groups = len(crypto_groups)
    max_groups = max(max_stock_groups, max_crypto_groups)

    logger.info("Group Analysis:")
    logger.info("Stock groups: %s", max_stock_groups)
    logger.info("Crypto groups: %s", max_crypto_groups)

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
        crypto_group = next(
            (g for g in crypto_groups if g["group_number"] == group_num), None
        )
        if crypto_group:
            merged_content += "\n".join(crypto_group["uppgifter"]) + "\n"

        # Add group footer
        merged_content += "#BLANKETTSLUT\n"

    # Add file footer
    merged_content += "#FIL_SLUT\n"

    return merged_content


def write_sru_file(file_path: str, content: str) -> bool:
    """
    Writes the given content string to a file, creating directories if needed.
    Returns True on success, False on failure.
    """
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(content)
        logger.info("SRU file '%s' has been successfully created.", file_path)
        return True
    except IOError as e:
        logger.error("Failed to write SRU file '%s': %s", file_path, e)
        return False
    except Exception as e:
        logger.error(
            "An unexpected error occurred while writing SRU file '%s': %s", file_path, e
        )
        return False


def read_crypto_sru_content(crypto_file_path: str) -> List[Dict[str, List[str]]]:
    """
    Reads the crypto SRU content from the specified file path.
    Returns a list of dictionaries, where each dictionary represents a group and contains:
    - 'group_number': The group number (from UPPGIFT 7014)
    - 'uppgifter': List of UPPGIFT lines for that group
    """
    if not os.path.exists(crypto_file_path):
        logger.warning(
            f"Crypto SRU file not found at {crypto_file_path}. Continuing without crypto data."
        )
        return []

    logger.info("Starting to read crypto SRU file from: %s", crypto_file_path)

    try:
        with open(crypto_file_path, "r", encoding="utf-8") as file:
            content = file.read()

        # Split content into groups
        groups = content.split("#BLANKETT K4-")
        parsed_groups = []

        for group in groups[1:]:  # Skip the first empty split
            group_data = {"group_number": None, "uppgifter": []}

            # Process each line in the group
            lines = group.split("\n")
            found_7014 = False

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                if "#UPPGIFT 7014" in line:
                    # Extract group number
                    try:
                        group_number = int(line.split()[-1])
                        group_data["group_number"] = group_number
                        found_7014 = True
                    except (ValueError, IndexError):
                        logger.error("Could not parse group number from line: %s", line)
                    continue

                if found_7014 and line.startswith("#UPPGIFT"):
                    if not line.startswith("#BLANKETTSLUT"):
                        group_data["uppgifter"].append(line)

            if group_data["group_number"] is not None and group_data["uppgifter"]:
                parsed_groups.append(group_data)

        logger.info(
            f"Successfully read {len(parsed_groups)} groups from crypto SRU file"
        )
        return parsed_groups

    except Exception as e:
        logger.error("Error reading crypto SRU file: %s", e)
        return []
