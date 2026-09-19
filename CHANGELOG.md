# Changelog

All notable changes to this project are documented in this file.

## [1.3.2] - 2026-09-19

### Fixed
- `build_blanketter_sru` accepts an empty `trade_rows` when `crypto_groups` are given, and writes
  only the crypto pages, numbered 1..n (#8, #9). A tax year with crypto disposals and no stock
  sales used to raise `ValidationError: Trade data cannot be empty`. With neither it still
  raises; `validate_trade_data` itself is unchanged.

### Tests
- Stock-only and mixed stock + crypto files are compared byte for byte against golden files
  generated at 1.3.1 (`tests/golden/`), with the header's clock held fixed.

## [1.3.1] - 2026-09-16

### Fixed
- The "profit/loss mismatch" warning asked its question of the *rounded* amounts, so 1.3.0
  accused correct input: `floor(sale) - ceil(cost)` lies in `(sale - cost - 2, sale - cost]`,
  and a self-consistent row can therefore differ from its own rounded profit by a full 2.
  Measured at **12% of random rows**, which would have made a genuine inconsistency
  unnoticeable. It now compares the caller's `profit/loss` against the unrounded
  `sale - cost`, with the tolerance the validator layer already documents.

## [1.3.0] - 2026-09-16

### Changed
- **K4 amounts now round the way Skatteverket says they do, which is three rules rather than
  one.** Försäljningspris drops its öre (`ROUND_FLOOR`), omkostnadsbelopp gains a krona for
  any öre (`ROUND_CEILING`), and vinst/förlust is derived from those two rounded amounts
  instead of being rounded itself. Source: the Inkomstdeklaration 1 e-service's own help text
  for bilaga K4 avsnitt A and D, quoted in `sru_generator.py` beside `K4_SALE_PRICE_ROUNDING`.
  Previously every amount was independently `ROUND_HALF_EVEN`.
- **A trade row's `profit/loss` is no longer written.** It is cross-checked against the derived
  figure and reported when the two differ by more than 1 kr; an absent or unreadable value is
  not cross-checked. Independent rounding is what let a row state a vinst that was not its own
  försäljningspris minus its own omkostnadsbelopp — 104 of 450 rows in a real 2019–2025 archive.
- `calculate_group_totals` rounds each row exactly as `format_trade_item_sru` does, so every
  group total is the sum of the column printed above it.

### Added
- `round_k4_sale_price()`, `round_k4_cost_basis()`, `K4_SALE_PRICE_ROUNDING`,
  `K4_COST_BASIS_ROUNDING`.

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
