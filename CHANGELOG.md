# Changelog

All notable changes to this project are documented in this file.

## [1.2.0] - 2026-05-10

### Added
- `models.py` with `TypedDict` input types (`PersonalInfo`, `SRUTradeRow`, `CryptoSRUGroup`)
- `builders.py` with high-level helpers: `build_info_sru()`, `build_blanketter_sru()`, `encode_sru_content()`
- Full PyPI-ready `pyproject.toml` build-system and project metadata
- Expanded test coverage, including a new `test_cli.py`

### Changed
- Refactored the public API surface exposed via `__init__.py`

## [1.1.0] - 2025-09-07

### Added
- Configuration management system (`SRUConfig`, `create_config()`, `get_default_config()`)
- Enhanced validation with custom exceptions (`ValidationError`, `BusinessRuleError`, `DataFormatError`, `CurrencyError`, `ConfigurationError`, `FileOperationError`)
- Multi-currency support with exchange-rate conversion (`CurrencyConverter`, `convert_currency()`, `convert_to_sek()`)
- Business rule validation with automatic profit/loss calculation
- Extensible custom validator system (`create_custom_validator()`)

## [1.0.0] - 2025

### Added
- Initial release
- Support for stock trade SRU generation
- Support for crypto transaction merging
- Greek character conversion
- Comprehensive validation and error handling
