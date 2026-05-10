# SRU Generator

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Educational Use](https://img.shields.io/badge/Use-Educational%20Only-red.svg)](https://github.com/Nikolaos-Paximadakis/sru-generator)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Status: Beta](https://img.shields.io/badge/Status-Beta-orange.svg)](https://github.com/Nikolaos-Paximadakis/sru-generator)
[![Tests](https://github.com/Nikolaos-Paximadakis/sru-generator/workflows/CI/CD%20Pipeline/badge.svg)](https://github.com/Nikolaos-Paximadakis/sru-generator/actions)

A Python package for generating Swedish SRU (Skatteverket) files for tax reporting.

## Overview

The SRU Generator package provides functionality to create SRU files that comply with Swedish tax authority (Skatteverket) specifications. It supports generating files for stock trades, crypto transactions, and other financial instruments that need to be reported to Swedish tax authorities.

The package is intentionally generic. It owns SRU formatting, validation, crypto merge handling, and high-level SRU content builders. Application-specific concerns such as broker selection, database reads, taxpayer-profile storage, and sell-report sourcing should stay in the consuming application.

## ⚠️ Important Disclaimer

**This software is provided for EDUCATIONAL and RESEARCH purposes only.** It is NOT intended for use in preparing official tax returns without proper verification and professional review.

### Tax Compliance Notice
- The accuracy of generated SRU files depends entirely on the accuracy of input data
- Users are solely responsible for verifying all calculations and ensuring compliance with current Swedish tax laws
- The authors make no representations about the accuracy or completeness of generated files
- **Users should consult with qualified tax professionals before submitting any tax-related documents**

### No Warranty for Tax Compliance
- The software is provided "AS IS" without any warranty regarding tax compliance
- The authors disclaim all responsibility for any tax penalties, fines, or legal issues
- Users assume all risks and responsibilities for their tax reporting obligations

**By using this software, you acknowledge that you have read and understood these disclaimers.**

## Features

### Core Features
- Generate SRU info files with personal information
- Create SRU trade content for stock transactions
- Build complete `info.sru` and `blanketter.sru` content from generic input data
- Support for crypto transaction reporting
- Automatic grouping of transactions according to SRU specifications
- Greek character conversion to English equivalents
- Comprehensive validation and error handling
- Detailed logging for debugging and monitoring

### Enhanced Features (v1.1.0)
- **Configuration Management**: Centralized configuration system with validation
- **Enhanced Validation**: Comprehensive data validation with custom exceptions
- **Multi-Currency Support**: Automatic currency conversion with exchange rates
- **Business Rule Validation**: Automatic profit/loss calculation and validation
- **Custom Validators**: Extensible validation system for custom requirements
- **Error Handling**: Detailed error messages with context information

## Installation

### From PyPI (when published)
```bash
pip install sru-generator
```

### From source
```bash
git clone https://github.com/Nikolaos-Paximadakis/sru-generator.git
cd sru-generator
pip install -e .
```

### Local workspace dependency

If another local project depends on `sru_generator`, install it as an editable local dependency:

```bash
pip install -e /path/to/sru_generator
```

## Quick Start

### Basic Usage

```python
from sru_generator import (
    build_blanketter_sru,
    build_info_sru,
    generate_sru_info_content,
    generate_sru_trade_content,
    write_sru_file
)

# Generate info file
info_content = generate_sru_info_content(
    personal_number="1234567890",
    full_name="John Doe",
    postal_code="12345",
    city_name="Stockholm"
)

# Generate trade content
trade_data = [
    {
        "quantity": 100,
        "stock": "Apple Inc",
        "net value": 15000.00,
        "total net value of purchase": 14000.00,
        "profit/loss": 1000.00
    }
]

trade_content = generate_sru_trade_content(
    trade_data=trade_data,
    full_name="John Doe",
    personal_number="1234567890",
    year=2024
)

# Write to file
write_sru_file("output.sru", trade_content)
```

### High-Level Builders

If your application already has normalized taxpayer data and sell rows, use the
high-level builders instead of assembling SRU content manually:

```python
from sru_generator import build_blanketter_sru, build_info_sru

personal_info = {
    "personal_number": "1234567890",
    "full_name": "John Doe",
    "postal_code": "12345",
    "city_name": "Stockholm",
}

trade_rows = [
    {
        "quantity": 100,
        "stock": "Apple Inc",
        "net value": 15000.00,
        "total net value of purchase": 14000.00,
        "profit/loss": 1000.00,
    }
]

info_content = build_info_sru(personal_info)
blanketter_content = build_blanketter_sru(trade_rows, personal_info, year=2024)
```

This split is how Mihalis now uses the package: Mihalis computes SEK sell rows and loads taxpayer profile data locally, then hands generic rows into `build_blanketter_sru(...)`.

### Advanced Usage with Crypto

```python
from sru_generator import merge_sru_groups, read_crypto_sru_content

# Read crypto data
crypto_groups = read_crypto_sru_content("crypto_data.sru")

# Merge stock and crypto data
merged_content = merge_sru_groups(
    stock_content=trade_content,
    crypto_groups=crypto_groups,
    full_name="John Doe",
    personal_number="1234567890",
    year=2024
)

write_sru_file("complete_report.sru", merged_content)
```

### Enhanced Configuration Management

The package now supports centralized configuration management:

```python
from sru_generator import SRUConfig, create_config

# Create custom configuration
config = create_config(
    character_converter="greek",
    validation_level="strict",
    default_currency="SEK",
    auto_convert_currency=True
)

# Set exchange rates
config.set_exchange_rate("USD", "SEK", 10.5)
config.set_exchange_rate("EUR", "SEK", 11.2)

# Get character converter from config
converter = config.get_character_converter()
```

### Enhanced Validation System

Comprehensive data validation with detailed error messages:

```python
from sru_generator import validate_trade_data, validate_personal_info, ValidationError

# Validate trade data
try:
    validated_data = validate_trade_data(trade_data)
    print("✅ Data validation successful!")
except ValidationError as e:
    print(f"❌ Validation failed: {e}")

# Validate personal information
personal_info = {
    "personal_number": "1234567890",
    "full_name": "John Doe",
    "postal_code": "12345",
    "city_name": "Stockholm"
}
validated_personal = validate_personal_info(personal_info)
```

### Multi-Currency Support

Automatic currency conversion with exchange rates:

```python
from sru_generator import convert_currency, convert_to_sek, set_exchange_rate

# Set exchange rates
set_exchange_rate("USD", "SEK", 10.5)
set_exchange_rate("EUR", "SEK", 11.2)

# Convert currencies
usd_amount = 1000.00
sek_amount = convert_to_sek(usd_amount, "USD")  # 10500.00 SEK
eur_amount = convert_currency(usd_amount, "USD", "EUR")  # 937.50 EUR

# Multi-currency trade data
trade_data = [
    {
        "quantity": 100,
        "stock": "Apple Inc",
        "net value": 1500.00,
        "total net value of purchase": 1400.00,
        "currency": "USD"  # Will be converted to SEK
    }
]
```

### Character Conversion Support

The package supports flexible character conversion for different languages:

```python
from sru_generator import (
    generate_sru_trade_content,
    convert_greek_characters_to_english,
    convert_swedish_characters_to_english,
    convert_german_characters_to_english,
    get_character_converter
)

# Using specific converter functions
trade_content = generate_sru_trade_content(
    trade_data=trade_data,
    full_name="John Doe",
    personal_number="1234567890",
    character_converter=convert_swedish_characters_to_english
)

# Using convenience function
converter = get_character_converter("greek")
trade_content = generate_sru_trade_content(
    trade_data=trade_data,
    full_name="John Doe",
    personal_number="1234567890",
    character_converter=converter
)

# Custom character converter
def custom_converter(text: str) -> str:
    return text.upper()  # Convert to uppercase

trade_content = generate_sru_trade_content(
    trade_data=trade_data,
    full_name="John Doe",
    personal_number="1234567890",
    character_converter=custom_converter
)
```

For detailed information about all available character converters, migration guides, and advanced usage patterns, see [CHARACTER_CONVERSION_OPTIONS.md](CHARACTER_CONVERSION_OPTIONS.md).

## Data Format

### Trade Data Structure

The trade data must be a **list of dictionaries**, where each dictionary represents a single trade transaction:

```python
trade_data = [
    {
        "quantity": 100,                    # Required: Number of shares/units sold
        "stock": "Apple Inc",               # Required: Stock name/identifier
        "net value": 15000.00,              # Required: Sale price (total amount received)
        "total net value of purchase": 14000.00,  # Required: Cost basis (total amount paid)
        "profit/loss": 1000.00,             # Optional: Profit or loss amount
        "currency": "USD",                  # Optional: Currency code (defaults to SEK)
        "exchange_rate": 10.5               # Optional: Exchange rate to SEK
    }
]
```

#### Trade Data Field Specifications

| Field | Type | Required | Description | Validation Rules |
|-------|------|----------|-------------|------------------|
| `quantity` | Integer | ✅ Yes | Number of shares/units sold | 0 ≤ value ≤ 999,999,999,999 |
| `stock` | String | ✅ Yes | Stock name/identifier | 1-80 characters |
| `net value` | Decimal | ✅ Yes | Sale price (total amount received) | 0 ≤ value ≤ 999,999,999,999 |
| `total net value of purchase` | Decimal | ✅ Yes | Cost basis (total amount paid) | 0 ≤ value ≤ 999,999,999,999 |
| `profit/loss` | Decimal | ❌ No | Profit or loss amount | Auto-calculated if not provided |
| `currency` | String | ❌ No | Currency code | Must be supported currency (see below) |
| `exchange_rate` | Decimal | ❌ No | Exchange rate to SEK | 0.000001 ≤ value ≤ 1,000,000 |

#### Supported Currencies

- **SEK** (Swedish Krona) - Default
- **USD** (US Dollar)
- **EUR** (Euro)
- **GBP** (British Pound)
- **NOK** (Norwegian Krone)
- **DKK** (Danish Krone)
- **CHF** (Swiss Franc)
- **JPY** (Japanese Yen)
- **CAD** (Canadian Dollar)
- **AUD** (Australian Dollar)

### Personal Information Structure

Personal information must be a **dictionary** with the following fields:

```python
personal_info = {
    "personal_number": "1234567890",    # Required: Swedish personal number
    "full_name": "John Doe",            # Required: Full name
    "postal_code": "12345",             # Required: Swedish postal code
    "city_name": "Stockholm"            # Required: City name
}
```

#### Personal Information Field Specifications

| Field | Type | Required | Description | Validation Rules |
|-------|------|----------|-------------|------------------|
| `personal_number` | String | ✅ Yes | Swedish personal number | 10-12 digits |
| `full_name` | String | ✅ Yes | Full name | 1-100 characters |
| `postal_code` | String | ✅ Yes | Swedish postal code | Exactly 5 digits |
| `city_name` | String | ✅ Yes | City name | 1-50 characters |

### Example Data

#### Basic Trade Data (SEK)
```python
trade_data = [
    {
        "quantity": 100,
        "stock": "Apple Inc",
        "net value": 15000.00,
        "total net value of purchase": 14000.00,
        "profit/loss": 1000.00
    },
    {
        "quantity": 50,
        "stock": "Microsoft Corp",
        "net value": 12000.00,
        "total net value of purchase": 13000.00,
        "profit/loss": -1000.00
    }
]
```

#### Multi-Currency Trade Data
```python
trade_data = [
    {
        "quantity": 100,
        "stock": "Apple Inc",
        "net value": 1500.00,
        "total net value of purchase": 1400.00,
        "currency": "USD",
        "exchange_rate": 10.5
    },
    {
        "quantity": 50,
        "stock": "SAP SE",
        "net value": 2000.00,
        "total net value of purchase": 1900.00,
        "currency": "EUR",
        "exchange_rate": 11.2
    }
]
```

#### Complete Personal Information
```python
personal_info = {
    "personal_number": "1234567890",
    "full_name": "John Doe",
    "postal_code": "12345",
    "city_name": "Stockholm"
}
```

### Important Notes

#### Automatic Calculations
- **Profit/Loss**: If not provided, it's automatically calculated as `net value - total net value of purchase`
- **Currency Conversion**: If currency is not SEK, amounts are converted using exchange rates

#### Business Rules
- **Profit/Loss Validation**: If provided, profit/loss must match the calculated value (within 1 SEK tolerance)
- **Currency Support**: Only supported currencies are allowed
- **Data Types**: All monetary values are converted to Decimal for precision

#### Validation
- **Required Fields**: All required fields must be present and valid
- **Data Types**: Automatic type conversion (string numbers → Decimal/Integer)
- **Range Validation**: All values must be within allowed ranges
- **Format Validation**: Personal numbers and postal codes must match Swedish formats

### Complete Usage Example

Here's a complete example showing how to use the enhanced features:

```python
from sru_generator import (
    validate_trade_data, 
    validate_personal_info,
    generate_sru_trade_content,
    write_sru_file,
    create_config,
    convert_to_sek,
    set_exchange_rate
)

# 1. Set up exchange rates for multi-currency support
set_exchange_rate("USD", "SEK", 10.5)
set_exchange_rate("EUR", "SEK", 11.2)

# 2. Prepare your data
trade_data = [
    {
        "quantity": 100,
        "stock": "Apple Inc",
        "net value": 1500.00,
        "total net value of purchase": 1400.00,
        "currency": "USD"
    },
    {
        "quantity": 50,
        "stock": "SAP SE",
        "net value": 2000.00,
        "total net value of purchase": 1900.00,
        "currency": "EUR"
    }
]

personal_info = {
    "personal_number": "1234567890",
    "full_name": "John Doe",
    "postal_code": "12345",
    "city_name": "Stockholm"
}

# 3. Validate data (recommended)
try:
    validated_trades = validate_trade_data(trade_data)
    validated_personal = validate_personal_info(personal_info)
    print("✅ Data validation successful!")
except ValidationError as e:
    print(f"❌ Validation failed: {e}")
    exit(1)

# 4. Convert currencies to SEK
for trade in validated_trades:
    if trade.get('currency') and trade['currency'] != 'SEK':
        trade['net value'] = float(convert_to_sek(trade['net value'], trade['currency']))
        trade['total net value of purchase'] = float(convert_to_sek(trade['total net value of purchase'], trade['currency']))
        trade['profit/loss'] = trade['net value'] - trade['total net value of purchase']
        trade['currency'] = 'SEK'  # Mark as converted

# 5. Create configuration
config = create_config(
    character_converter="greek",
    validation_level="strict"
)

# 6. Generate SRU content
character_converter = config.get_character_converter()
sru_content = generate_sru_trade_content(
    trade_data=validated_trades,
    full_name=validated_personal["full_name"],
    personal_number=validated_personal["personal_number"],
    year=2024,
    character_converter=character_converter
)

# 7. Write to file
write_sru_file("output.sru", sru_content)
print("✅ SRU file generated successfully!")
```

## API Reference

### Core Functions

- `build_info_sru()`: Build a complete `info.sru` content string
- `build_blanketter_sru()`: Build a complete `blanketter.sru` content string
- `encode_sru_content()`: Encode generated SRU content for file responses or writes
- `generate_sru_info_content()`: Generate SRU info file content
- `generate_sru_trade_content()`: Generate SRU trade content
- `merge_sru_groups()`: Merge stock and crypto groups
- `write_sru_file()`: Write content to SRU file
- `read_crypto_sru_content()`: Read crypto SRU content from file

### Enhanced Functions (v1.1.0)

#### Configuration Management
- `SRUConfig`: Configuration class for all settings
- `create_config()`: Create custom configuration
- `get_default_config()`: Get default configuration

#### Validation Functions
- `validate_trade_data()`: Validate trade data with comprehensive checks
- `validate_personal_info()`: Validate personal information
- `TradeDataValidator`: Customizable trade data validator

#### Currency Functions
- `convert_currency()`: Convert between currencies
- `convert_to_sek()`: Convert amount to Swedish Krona
- `set_exchange_rate()`: Set exchange rate between currencies
- `CurrencyConverter`: Currency conversion class

#### Exception Classes
- `ValidationError`: Data validation failures
- `BusinessRuleError`: Business logic violations
- `DataFormatError`: Format/schema issues
- `CurrencyError`: Currency-related errors
- `ConfigurationError`: Configuration issues
- `FileOperationError`: File I/O errors

### Constants

- `MAX_GROUP_NUMBER`: Maximum number of groups allowed (99999)
- `MAX_MONETARY_VALUE`: Maximum monetary value allowed (999999999999)
- `NUMBER_OF_CHARACTERS_FOR_STOCK_NAME`: Maximum stock name length (80)

## Error Handling

The package includes comprehensive error handling and validation:

- Validates quantity and monetary values within allowed ranges
- Converts Greek characters to English equivalents
- Handles invalid data gracefully with appropriate logging
- Provides detailed error messages for debugging

## Logging

The package uses Python's built-in logging module. To enable logging:

```python
import logging
logging.basicConfig(level=logging.INFO)
```

## CLI Usage

The package includes a command-line interface for easy usage:

```bash
# Generate info file
sru-generator info --personal-number "1234567890" --full-name "John Doe" --postal-code "12345" --city-name "Stockholm"

# Generate trade file
sru-generator trades --data "trades.json" --personal-number "1234567890" --full-name "John Doe"

# Generate trade file with character conversion
sru-generator trades --data "trades.json" --personal-number "1234567890" --full-name "John Doe" --character-conversion swedish

# Available character conversions: greek, swedish, german, french, spanish, none
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For questions, issues, or contributions, please visit the [GitHub repository](https://github.com/Nikolaos-Paximadakis/sru-generator).

## Changelog

### Version 1.0.0
- Initial release
- Support for stock trade SRU generation
- Support for crypto transaction merging
- Greek character conversion
- Comprehensive validation and error handling
