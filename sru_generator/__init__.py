"""
SRU Generator - A Python package for generating Swedish SRU (Skatteverket) files.

This package provides functionality to generate SRU files for Swedish tax reporting,
including support for stock trades, crypto transactions, and proper formatting
according to Swedish tax authority specifications.
"""

from .sru_generator import (
    generate_sru_info_content,
    generate_sru_header,
    format_trade_item_sru,
    calculate_group_totals,
    format_group_totals_sru,
    generate_sru_trade_content,
    generate_sru_footer,
    merge_sru_groups,
    write_sru_file,
    read_crypto_sru_content,
    # Constants
    SRU_FIELD_BLANKETT_START,
    SRU_FIELD_IDENTITET,
    SRU_FIELD_NAMN,
    SRU_FIELD_UPPGIFT_GROUP_START,
    SRU_LINE_START,
    SRU_FIELD_QUANTITY_SUFFIX,
    SRU_FIELD_STOCK_NAME_SUFFIX,
    SRU_FIELD_SOLD_AMOUNT_SUFFIX,
    SRU_FIELD_COST_BASIS_SUFFIX,
    SRU_FIELD_PROFIT_SUFFIX,
    SRU_FIELD_LOSS_SUFFIX,
    SRU_FIELD_GROUP_TOTAL_SOLD,
    SRU_FIELD_GROUP_TOTAL_COST_BASIS,
    SRU_FIELD_GROUP_TOTAL_PROFIT,
    SRU_FIELD_GROUP_TOTAL_LOSS,
    SRU_FIELD_BLANKETT_END,
    SRU_FIELD_FILE_END,
    WHOLE_NUMBER_ROUNDING,
    NUMBER_OF_CHARACTERS_FOR_STOCK_NAME,
    MAX_GROUP_NUMBER,
    MAX_MONETARY_VALUE,
)

from .character_converters import (
    convert_greek_characters_to_english,
    convert_swedish_characters_to_english,
    convert_german_characters_to_english,
    convert_french_characters_to_english,
    convert_spanish_characters_to_english,
    no_conversion,
    get_character_converter,
    CHARACTER_CONVERTERS,
)

# Enhanced features
from .config import SRUConfig, DEFAULT_CONFIG, get_default_config, create_config
from .currency import (
    CurrencyConverter,
    CurrencyAmount,
    convert_currency,
    convert_to_sek,
    set_exchange_rate,
    get_currency_converter,
)
from .validators import validate_trade_data, validate_personal_info, TradeDataValidator
from .exceptions import (
    SRUGeneratorError,
    ValidationError,
    DataFormatError,
    BusinessRuleError,
    CurrencyError,
    ConfigurationError,
    FileOperationError,
)

__version__ = "1.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

__all__ = [
    # Main functions
    "generate_sru_info_content",
    "generate_sru_header",
    "format_trade_item_sru",
    "calculate_group_totals",
    "format_group_totals_sru",
    "generate_sru_trade_content",
    "generate_sru_footer",
    "merge_sru_groups",
    "write_sru_file",
    "read_crypto_sru_content",
    # Character converters
    "convert_greek_characters_to_english",
    "convert_swedish_characters_to_english",
    "convert_german_characters_to_english",
    "convert_french_characters_to_english",
    "convert_spanish_characters_to_english",
    "no_conversion",
    "get_character_converter",
    "CHARACTER_CONVERTERS",
    # Enhanced features
    "SRUConfig",
    "DEFAULT_CONFIG",
    "get_default_config",
    "create_config",
    "CurrencyConverter",
    "CurrencyAmount",
    "convert_currency",
    "convert_to_sek",
    "set_exchange_rate",
    "get_currency_converter",
    "validate_trade_data",
    "validate_personal_info",
    "TradeDataValidator",
    # Exceptions
    "SRUGeneratorError",
    "ValidationError",
    "DataFormatError",
    "BusinessRuleError",
    "CurrencyError",
    "ConfigurationError",
    "FileOperationError",
    # Constants
    "SRU_FIELD_BLANKETT_START",
    "SRU_FIELD_IDENTITET",
    "SRU_FIELD_NAMN",
    "SRU_FIELD_UPPGIFT_GROUP_START",
    "SRU_LINE_START",
    "SRU_FIELD_QUANTITY_SUFFIX",
    "SRU_FIELD_STOCK_NAME_SUFFIX",
    "SRU_FIELD_SOLD_AMOUNT_SUFFIX",
    "SRU_FIELD_COST_BASIS_SUFFIX",
    "SRU_FIELD_PROFIT_SUFFIX",
    "SRU_FIELD_LOSS_SUFFIX",
    "SRU_FIELD_GROUP_TOTAL_SOLD",
    "SRU_FIELD_GROUP_TOTAL_COST_BASIS",
    "SRU_FIELD_GROUP_TOTAL_PROFIT",
    "SRU_FIELD_GROUP_TOTAL_LOSS",
    "SRU_FIELD_BLANKETT_END",
    "SRU_FIELD_FILE_END",
    "WHOLE_NUMBER_ROUNDING",
    "NUMBER_OF_CHARACTERS_FOR_STOCK_NAME",
    "MAX_GROUP_NUMBER",
    "MAX_MONETARY_VALUE",
]
