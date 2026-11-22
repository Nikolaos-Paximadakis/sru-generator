"""
SRU Generator - A Python package for generating Swedish SRU (Skatteverket) files.

This package provides functionality to generate SRU files for Swedish tax reporting,
including support for stock trades, crypto transactions, and proper formatting
according to Swedish tax authority specifications.
"""

import logging

from .amounts import to_decimal
from .builders import build_blanketter_sru, build_info_sru, encode_sru_content
from .character_converters import load_character_converter

# Enhanced features
from .config import DEFAULT_CONFIG, SRUConfig, create_config, get_default_config
from .currency import (
    CurrencyAmount,
    CurrencyConverter,
    convert_currency,
    convert_to_sek,
    get_currency_converter,
    set_exchange_rate,
)
from .exceptions import (
    BusinessRuleError,
    ConfigurationError,
    CurrencyError,
    DataFormatError,
    FileOperationError,
    SRUGeneratorError,
    ValidationError,
)
from .models import CryptoSRUGroup, PersonalInfo, SRUTradeRow
from .sru_generator import (
    K4_COST_BASIS_ROUNDING,
    K4_SALE_PRICE_ROUNDING,
    K4_SECTION_A_ROWS,
    MAX_GROUP_NUMBER,
    MAX_MONETARY_VALUE,  # Constants
    NUMBER_OF_CHARACTERS_FOR_STOCK_NAME,
    SRU_ENCODING,
    SRU_FIELD_BLANKETT_END,
    SRU_FIELD_BLANKETT_START,
    SRU_FIELD_COST_BASIS_SUFFIX,
    SRU_FIELD_FILE_END,
    SRU_FIELD_GROUP_TOTAL_COST_BASIS,
    SRU_FIELD_GROUP_TOTAL_LOSS,
    SRU_FIELD_GROUP_TOTAL_PROFIT,
    SRU_FIELD_GROUP_TOTAL_SOLD,
    SRU_FIELD_IDENTITET,
    SRU_FIELD_LOSS_SUFFIX,
    SRU_FIELD_NAMN,
    SRU_FIELD_PROFIT_SUFFIX,
    SRU_FIELD_QUANTITY_SUFFIX,
    SRU_FIELD_SOLD_AMOUNT_SUFFIX,
    SRU_FIELD_STOCK_NAME_SUFFIX,
    SRU_FIELD_UPPGIFT_GROUP_START,
    SRU_LINE_START,
    WHOLE_NUMBER_ROUNDING,
    calculate_group_totals,
    decode_sru_bytes,
    encode_sru_text,
    format_group_totals_sru,
    format_trade_item_sru,
    generate_sru_footer,
    generate_sru_header,
    generate_sru_info_content,
    generate_sru_trade_content,
    merge_sru_groups,
    read_crypto_sru_content,
    round_k4_cost_basis,
    round_k4_quantity,
    round_k4_sale_price,
    write_sru_file,
)
from .validators import TradeDataValidator, validate_personal_info, validate_trade_data

__version__ = "1.0.1"

# Library logging etiquette: stay silent unless the application configures logging.
logging.getLogger("sru_generator").addHandler(logging.NullHandler())

__all__ = [
    "DEFAULT_CONFIG",
    "K4_COST_BASIS_ROUNDING",
    "K4_SALE_PRICE_ROUNDING",
    "K4_SECTION_A_ROWS",
    "MAX_GROUP_NUMBER",
    "MAX_MONETARY_VALUE",
    "NUMBER_OF_CHARACTERS_FOR_STOCK_NAME",
    "SRU_ENCODING",
    "SRU_FIELD_BLANKETT_END",
    # Constants
    "SRU_FIELD_BLANKETT_START",
    "SRU_FIELD_COST_BASIS_SUFFIX",
    "SRU_FIELD_FILE_END",
    "SRU_FIELD_GROUP_TOTAL_COST_BASIS",
    "SRU_FIELD_GROUP_TOTAL_LOSS",
    "SRU_FIELD_GROUP_TOTAL_PROFIT",
    "SRU_FIELD_GROUP_TOTAL_SOLD",
    "SRU_FIELD_IDENTITET",
    "SRU_FIELD_LOSS_SUFFIX",
    "SRU_FIELD_NAMN",
    "SRU_FIELD_PROFIT_SUFFIX",
    "SRU_FIELD_QUANTITY_SUFFIX",
    "SRU_FIELD_SOLD_AMOUNT_SUFFIX",
    "SRU_FIELD_STOCK_NAME_SUFFIX",
    "SRU_FIELD_UPPGIFT_GROUP_START",
    "SRU_LINE_START",
    "WHOLE_NUMBER_ROUNDING",
    "BusinessRuleError",
    "ConfigurationError",
    "CryptoSRUGroup",
    "CurrencyAmount",
    "CurrencyConverter",
    "CurrencyError",
    "DataFormatError",
    "FileOperationError",
    "PersonalInfo",
    # Enhanced features
    "SRUConfig",
    # Exceptions
    "SRUGeneratorError",
    "SRUTradeRow",
    "TradeDataValidator",
    "ValidationError",
    "build_blanketter_sru",
    "build_info_sru",
    "calculate_group_totals",
    "convert_currency",
    "convert_to_sek",
    "create_config",
    "decode_sru_bytes",
    "encode_sru_content",
    "encode_sru_text",
    "format_group_totals_sru",
    "format_trade_item_sru",
    "generate_sru_footer",
    "generate_sru_header",
    # Main functions
    "generate_sru_info_content",
    "generate_sru_trade_content",
    "get_currency_converter",
    "get_default_config",
    "load_character_converter",
    "merge_sru_groups",
    "read_crypto_sru_content",
    "round_k4_cost_basis",
    "round_k4_quantity",
    "round_k4_sale_price",
    "set_exchange_rate",
    "to_decimal",
    "validate_personal_info",
    "validate_trade_data",
    "write_sru_file",
]
