# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`sru-generator` (v1.2.0) — installable Python package for generating Swedish Skatteverket SRU tax files (K4 form). Zero external runtime dependencies; stdlib only. Python >= 3.8.

## Common Commands

```bash
pip install -e .                                          # Install in editable mode
pytest tests/ -v --cov=sru_generator                     # Run all tests with coverage
pytest tests/test_sru_generator.py::TestSRUGenerator -v  # Run a single test class
pytest tests/test_enhanced_features.py::TestValidation -v
flake8 sru_generator/ tests/
black --check sru_generator/ tests/
isort --check-only sru_generator/ tests/
mypy sru_generator/ --ignore-missing-imports
python -m build                                           # Build distribution packages
twine check dist/*                                        # Validate built packages
```

CLI entry point (defined in `setup.py`): `sru-generator info ...` and `sru-generator trades ...`.

Note: the CI flake8 step runs with `--select=E9,F63,F7,F82` (fatal errors only, not style). Full style checks are done via black/isort.

## Architecture

### Module map

```
cli.py                      ← argparse CLI; subcommands: info, trades
builders.py                 ← High-level generic helpers: build_info_sru, build_blanketter_sru
models.py                   ← Public generic input types for personal info, trade rows, crypto groups
sru_generator.py            ← Core generation logic (functional, field constants, grouping)
validators.py               ← Validator class hierarchy; TradeDataValidator, PersonalInfoValidator
currency.py                 ← CurrencyConverter class + module-level globals; 10 supported currencies
config.py                   ← SRUConfig dataclass + ValidationLevel/RoundingMode enums
character_converters.py     ← Delegates to sibling text_converters package; no-op fallbacks if absent
exceptions.py               ← Exception hierarchy rooted at SRUGeneratorError
utils.py                    ← setup_logger() only
__init__.py                 ← Re-exports ~70 public symbols as the package API
```

### SRU file format

SRU files are plain-text with `#UPPGIFT field_id value` lines. The K4 trade form (BLANKETTER.SRU) groups up to 9 trades per `#BLANKETT K4-{year}P4` block. Each block starts with `#BLANKETT`, `#IDENTITET`, `#NAMN`, `#UPPGIFT 7014 {group_number}`, followed by per-trade lines, group total lines, and `#BLANKETTSLUT`. The file ends with `#FIL_SLUT`.

Per-trade field IDs follow `31{item_index_in_group}{field_type}` where field_type 0=quantity, 1=stock name, 2=sale price, 3=cost basis, 4=profit, 5=loss. Group totals use IDs 3300 (sold), 3301 (cost basis), 3304 (profit), 3305 (loss). Profit and loss are always written as positive integers; they occupy separate fields.

A companion info file (INFO.SRU) uses `#DATABESKRIVNING_START ... #DATABESKRIVNING_SLUT` and `#MEDIELEV_START ... #MEDIELEV_SLUT` blocks.

### Key data flow

1. Input: list of generic trade dicts with keys `quantity`, `stock`, `net value`, `total net value of purchase`, and optionally `profit/loss`, `currency`, `exchange_rate`.
2. `builders.py` provides `build_info_sru(...)` and `build_blanketter_sru(...)` for callers that already have normalized generic inputs.
3. `validators.py` normalises and validates each item; auto-calculates `profit/loss` if omitted; raises `BusinessRuleError` if the supplied value differs from `net value - cost basis` by more than 1 (Decimal).
4. `currency.py` converts non-SEK values using stored exchange rates (not called automatically by `sru_generator.py` — callers must convert before passing trade dicts unless they own that conversion separately).
5. `sru_generator.py` groups trades into blocks of `items_per_group` (default 9), formats `#UPPGIFT` lines, calculates group totals, writes UTF-8 files.
6. Crypto SRU data can be read from an existing file with `read_crypto_sru_content()` and merged into the stock output via `merge_sru_groups()`.

### Precision

All monetary arithmetic uses `decimal.Decimal` (ROUND_HALF_EVEN to whole numbers). Floats and ints passed in are immediately wrapped in `Decimal(str(value))`. The tolerance check in `format_trade_item_sru` allows a difference of 1 (integer) between calculated and supplied profit/loss; the validator layer allows a difference of `Decimal("1")`.

### Validation classes

`Validator` (base) → `StringValidator`, `IntegerValidator`, `DecimalValidator`, `CurrencyValidator`. Composite validators: `TradeDataValidator` (field + business rules), `PersonalInfoValidator`.

Personal number pattern: `^\d{10,12}$`. Postal code: `^\d{5}$`. Stock name max length: 80 characters (truncated silently in `format_trade_item_sru`; rejected by `StringValidator` in `TradeDataValidator`). Monetary field upper bound: 999,999,999,999. Values exceeding bounds are clamped to 0 with an error log in `sru_generator.py`; the validator layer raises `ValidationError` instead.

Use `create_custom_validator(field_name, callable)` for factory-pattern extensions.

### Configuration

`SRUConfig` (dataclass in `config.py`) controls: `character_converter` (string key), `validation_level` (`ValidationLevel` enum: NONE/BASIC/STRICT), `rounding_mode` (`RoundingMode` enum), `default_currency`, `auto_convert_currency`, `exchange_rates` dict, `log_level`, `custom_validators`, `custom_formatters`. `DEFAULT_CONFIG` is a module-level singleton; call `get_default_config()` to get a mutable copy via `.copy()`.

Exchange rate resolution order: direct key `FROM_TO` → inverse key `TO_FROM` → transitive through `default_currency` (SEK). `SRUConfig.from_dict()` accepts string values for enum fields (`"strict"` for `ValidationLevel`, `"half_even"` for `RoundingMode`); direct constructor requires the enum members.

### character_converters dependency

`character_converters.py` adds `../../text_converters` to `sys.path` at import time and tries `from character_converters import ...` (the `text_converters` package's module). If that import fails, all converters fall back to identity functions and `CHARACTER_CONVERTERS` is populated with built-in fallback mappings including `"none"`, `"greek"`, `"swedish"`, `"german"`, `"french"`, and `"spanish"`.

## Boundary

This package should stay generic. Do not add:

- broker lookup logic
- DB access
- application-specific storage paths
- application-specific taxpayer profile loading

Those belong in the consuming application. Mihalis now uses this package with exactly that split.

### utils.py logger behaviour

`setup_logger()` clears all existing handlers on every call before adding a new `StreamHandler`. Calling it multiple times resets the handler list — avoid calling it in a loop or in code that re-imports the module.

## CI/CD

GitHub Actions (`.github/workflows/ci.yml`): three jobs — `test` (Python 3.8–3.12 matrix, pytest + codecov) → `lint` (flake8 fatal-errors-only, black, isort, mypy) → `build` (python -m build + twine check). The build job only runs when both test and lint pass.
