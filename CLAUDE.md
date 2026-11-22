# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`sru-generator` (v2.0.0) — installable Python package for generating Swedish Skatteverket SRU tax files (K4 form). Zero required runtime dependencies; stdlib only (optional extra `transliterate` = text-converters). Python >= 3.11.

## Common Commands

Dependency management and running tools is done via [uv](https://docs.astral.sh/uv/); there is no `requirements.txt`, `setup.py`, or manual venv activation.

```bash
uv sync --group dev                      # Install package + dev deps
uv run pytest --cov                      # Tests (strict: warnings are errors, --strict-markers/config)
uv run pytest tests/test_cli.py -v       # One file
uv run ruff check .                      # Lint (rules in pyproject.toml); --fix for safe fixes
uv run ruff format --check .             # Formatting (replaces black/isort)
uv run mypy                              # mypy --strict on sru_generator/ and tests/ (config in pyproject.toml)
uv run pre-commit run --all-files        # All hooks
uv build && uvx twine check --strict dist/*
```

CLI entry point (defined in `pyproject.toml` under `[project.scripts]`): `sru-generator info ...` and `sru-generator trades ...`.


## Architecture

### Module map

```
cli.py                      ← argparse CLI; subcommands: info, trades
builders.py                 ← High-level generic helpers: build_info_sru, build_blanketter_sru
models.py                   ← Public generic input types for personal info, trade rows, crypto groups
sru_generator.py            ← Core generation logic (functional, field constants, grouping)
validators.py               ← Validator class hierarchy; TradeDataValidator, PersonalInfoValidator
currency.py                 ← CurrencyConverter class + module-level globals; 10 supported currencies
config.py                   ← SRUConfig dataclass (character_converter, default_currency, exchange_rates)
character_converters.py     ← load_character_converter: names → text-converters (no bundled rules)
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
5. `sru_generator.py` groups trades into blocks of `items_per_group` (default 9), formats `#UPPGIFT` lines, calculates group totals, writes ISO-8859-1 files (`SRU_ENCODING`; unencodable characters raise `DataFormatError` rather than being replaced).
6. Crypto SRU data can be read from an existing file with `read_crypto_sru_content()` and merged into the stock output via `merge_sru_groups()`. `build_blanketter_sru()` accepts an empty `trade_rows` when crypto groups are given (a crypto-only year: the file is just the crypto pages, numbered 1..n); with neither it still raises `ValidationError`.

### Precision

All monetary arithmetic uses `decimal.Decimal`; floats and ints passed in are immediately wrapped in `Decimal(str(value))`.

**A K4 row's whole-krona rounding is Skatteverket's rule, and it is three rules, not one** (`K4_SALE_PRICE_ROUNDING` in `sru_generator.py` carries the citation). Försäljningspris rounds **öre down** (`ROUND_FLOOR`), omkostnadsbelopp rounds **öre up** (`ROUND_CEILING`), and vinst/förlust is **derived from those two rounded amounts** — never rounded on its own. Group totals round each row the same way and only then sum, so `3300`/`3301`/`3304`/`3305` are the sums of the columns printed above them and every row states its own difference. Rounding all three independently (e.g. `ROUND_HALF_EVEN`) is right for none of them and lets a row contradict itself by 1 kr.

`SRUConfig.rounding_mode` does **not** reach any of this and never did: the K4 rule is not a preference.

Every amount and quantity is read with `amounts.to_decimal`: a `float` at 15 significant digits (drops binary noise such as `0.1*3*1000 = 300.00000000000006`, which round-öre-up would turn into a krona), everything else exactly via `Decimal(str(value))`, so exact sub-öre input still gets the directional rule (`Decimal("100.001")` → 101). Do not pre-round to öre: that was tried and broke exact input. Validators use the same conversion; the CLI parses JSON with `parse_float=Decimal`.

A caller's `profit/loss` is now diagnostic only — it is cross-checked and never written. The comparison is against the **unrounded** `sale - cost`, with a tolerance of 1: asking it of the rounded figures accuses correct input, since `floor(sale) - ceil(cost)` can sit a full 2 below `sale - cost` (12% of random self-consistent rows tripped it in an earlier version). An absent, unreadable or non-finite value is not cross-checked at all. The validator layer still allows a difference of `Decimal("1")` against `net value - cost basis`.

### Writer checks

`generate_sru_trade_content` / `merge_sru_groups` raise `ValidationError` for an impossible `year` (`check_income_year`: 2000-9999), `items_per_group` outside 1-9 (`check_items_per_group`, `K4_SECTION_A_ROWS`), or crypto pages that are not section D lines numbered 1..n (`check_crypto_groups`, `K4_SECTION_D_FIELDS`). Page totals are summed over the rows actually written.

### Validation classes

`Validator` (base) → `StringValidator`, `IntegerValidator`, `DecimalValidator`, `CurrencyValidator`. Composite validators: `TradeDataValidator` (field + business rules), `PersonalInfoValidator`.

Personal number: `PersonalNumberValidator` — 12 digits with century and a correct Luhn check digit, as Skatteverket's file description requires; a hyphen before the last four digits is stripped; 10 digits are refused (century ambiguous). Text fields written to the file (`stock`, `full_name`, `city_name`) refuse `#` (forbidden in SRU strings) and control characters (`sru_text=True`). Postal code: `^\d{5}$`. Stock name max length: 80 characters (truncated silently in `format_trade_item_sru`; rejected by `StringValidator` in `TradeDataValidator`). Monetary field upper bound: 999,999,999,999. Values exceeding bounds are clamped to 0 with an error log in `sru_generator.py`; the validator layer raises `ValidationError` instead.

Use `create_custom_validator(field_name, callable)` for factory-pattern extensions.

### Configuration

`SRUConfig` (dataclass in `config.py`) has exactly three fields: `character_converter` (a name from `CONVERTER_NAMES`), `default_currency`, `exchange_rates`. The 15 no-effect fields, `NO_EFFECT_FIELDS` and the `ValidationLevel`/`RoundingMode` enums were removed in 2.0. Each field has a `_check_*` function used by both `__post_init__` and `from_dict`; `from_dict` takes `Mapping[str, object]` (no `Any`), refuses unknown keys with `ConfigurationError` and copies `exchange_rates`. `DEFAULT_CONFIG` is a module-level singleton; call `get_default_config()` to get a mutable copy via `.copy()`.

Exchange rate resolution order: direct key `FROM_TO` → inverse key `TO_FROM` → transitive through `default_currency` (SEK). `SRUConfig.from_dict()` and `create_config()` accept string values for enum fields (`"strict"`, `"half_even"`); the direct constructor requires the enum members. `from_dict` copies its input.

### character_converters

Character conversion belongs to the separate `text-converters` package; sru-generator bundles no rules (removed in 2.0 with the deprecated top-level re-exports and `resolve_character_converter`). Builders take any `Callable[[str], str]`. `load_character_converter(name)` is the only way the CLI and `SRUConfig.get_character_converter()` turn a name into a converter: `"none"` is the identity and imports nothing; an unknown name is `ValueError`; any other name lazily imports `text_converters` through `importlib.import_module` (no stubs needed under strict mypy/pyright) and uses its `get_character_converter`. Missing → `ConfigurationError` raised from the `ImportError`; installed but failing the behaviour check (its Greek converter must turn `Θεσσαλονίκη Παπαδόπουλος` into `Thessaloniki Papadopoulos`, `_GREEK_PROBE`) or lacking the contract → `ConfigurationError` "outdated". The CLI turns that into `parser.error` (exit 2) before reading the data.

Importing an optional, *installed* package lazily is allowed; never add `sys.path` manipulation, and never make text-converters a required dependency. Install hint everywhere (`TEXT_CONVERTERS_INSTALL`): `pip install "sru-generator[transliterate]"` (extra `transliterate = ["text-converters>=0.2.1"]`, no upper cap: the CI `text-converters` job tests the latest release instead). text-converters' `tests/test_downstream_contract.py` pins what we rely on. Test with it via `uv run --with text-converters pytest` (or `--with ../text_converters`); `test_contract_with_the_real_text_converters` in `tests/test_converter_loading.py` then runs the loader against the real package, and `tests/test_examples.py` also runs the example that imports `text_converters` (skipped without it). Quantity is accepted as a Decimal and rounded **up** to a whole antal (`round_k4_quantity`).

## Boundary

This package should stay generic. Do not add:

- broker lookup logic
- DB access
- application-specific storage paths
- application-specific taxpayer profile loading

Those belong in the consuming application.

### Logging

The package never configures logging: `sru_generator.py` uses `logging.getLogger("sru_generator")` and `__init__.py` adds only a `NullHandler`. The CLI calls `logging.basicConfig` (WARNING, or INFO with `-v`). `utils.setup_logger()` is an opt-in helper for applications and clears existing handlers on the logger; the package does not call it.

### Spec source

Skatteverket's SRU rules: the "Teknisk information om filöverföring" page (replaced the SKV 269 brochure on 2024-01-01) and its per-period ZIPs (field tables `K4_SKV2104-*.xls`, `Vardeforrad_*.xls`, `Medieleverantorsinfo_*.xlsx`). Facts used here: ISO 8859-1; LF record ends; 12-digit identity numbers; no `#` in strings; `#NAMN` optional in blankett blocks; 5 MB file limit; K4 section A antal is an integer (section D antal may be decimal since 2025P4).

## CI/CD

GitHub Actions (`.github/workflows/ci.yml`), actions pinned to commit SHAs, read-only token: `test` (Python 3.11–3.14, `pytest --cov`, coverage floor 95% in pyproject) · `lint` (ruff check, ruff format --check, mypy --strict, pyright strict pinned to 1.1.414) · `text-converters` (latest text-converters from PyPI against the converter/example/CLI tests, `SRU_REQUIRE_TEXT_CONVERTERS=1` so it fails instead of skipping; replaces an upper version cap) · `package` (uv build, twine check --strict, install the wheel and run the CLI; install it with `[transliterate]` and convert a Greek name). The `main` ruleset requires all seven. `.github/workflows/release.yml` (Trusted Publishing): a manual run uploads to TestPyPI; publishing a GitHub release `vX.Y.Z` (must match pyproject's version) uploads to PyPI after approval of the `pypi` environment.

Tests: `tests/test_properties.py` uses Hypothesis (dev dependency) for the K4 invariants; `tests/test_examples.py` runs every script in `examples/` and checks the SRU files they write are complete.
