# Changelog

All notable changes to this project are documented in this file. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[semantic versioning](https://semver.org/).

## [2.0.0] - 2026-11-22

Character conversion is now entirely text-converters' job, and the deprecated API from
1.0 is gone.

### Added
- The `transliterate` extra: `pip install "sru-generator[transliterate]"` installs
  text-converters (`>=0.2.1`) for the named character converters.

### Changed
- A named converter (`greek`, `swedish`, `german`, `french`, `spanish`) without
  text-converters, or with an outdated one, raises `ConfigurationError` from
  `load_character_converter` and `SRUConfig.get_character_converter()`, with the install
  command. The CLI reports it as a usage error (exit status 2) before reading the data.
  `"none"` still needs nothing.
- `SRUConfig.from_dict` takes any `Mapping[str, object]`, checks the type of each value
  and refuses unknown keys with `ConfigurationError`. `exchange_rates` is copied, not
  shared with the caller.

### Removed
- The character converters bundled with sru-generator, and with them the fallback, its
  `DeprecationWarning` and the CLI's stderr note.
- The top-level names `convert_*_characters_to_english`, `get_character_converter`,
  `CHARACTER_CONVERTERS` and `no_conversion`; from `sru_generator.character_converters`
  also `resolve_character_converter`, `BUNDLED_CONVERTERS_WARNING` and
  `TEXT_CONVERTERS_SOURCE`.
- The `SRUConfig` fields that nothing read: `validation_level`, `strict_validation`,
  `rounding_mode`, `decimal_places`, `output_format`, `encoding`, `line_ending`,
  `auto_convert_currency`, `batch_size`, `enable_caching`, `cache_size`, `log_level`,
  `log_file`, `custom_validators`, `custom_formatters`; `NO_EFFECT_FIELDS`; the
  `ValidationLevel` and `RoundingMode` enums.

### Migrating from 1.x
- **Named converters:** install the extra, `pip install "sru-generator[transliterate]"`
  (or text-converters itself), or pass your own `str -> str` function as
  `character_converter`. Output is unchanged: the bundled copy matched text-converters.
- **Converter functions:** import them from `text_converters` instead of
  `sru_generator` (`from text_converters import convert_greek_characters_to_english`),
  or use `load_character_converter(name)`.
- **Configuration:** drop the removed keys from dicts passed to `SRUConfig.from_dict` /
  `create_config`; they now raise `ConfigurationError` instead of warning.

## [1.0.1] - 2026-11-22

### Changed
- text-converters is on PyPI (from 0.2.1), so the install hint in the deprecation
  warning, the CLI's note, the README and the example is now
  `pip install text-converters` instead of the pinned git URL. No version pin is needed:
  an outdated copy is still detected by its output and not used.
- CI also tests against the latest text-converters from PyPI.

## [1.0.0] - 2026-11-22

First public release.

### What it does
- Builds the SRU files Skatteverket's e-service imports for **bilaga K4**: `INFO.SRU`
  (`build_info_sru`) and `BLANKETTER.SRU` (`build_blanketter_sru`), with section A rows
  in pages of nine, page numbers (7014) and page totals (3300/3301/3304/3305).
- Merges K4 **section D** pages (e.g. crypto) from an existing SRU file
  (`read_crypto_sru_content`), in UTF-8 or ISO-8859-1 and with 7014 anywhere on a page;
  a crypto-only year is supported.
- A command-line tool, `sru-generator info` / `sru-generator trades`, which takes
  personal details from options, environment variables (`SRU_PERSONAL_NUMBER`, ...) or a
  JSON profile, so the personnummer need not enter shell history.

### Skatteverket's rules
- **Rounding per column:** försäljningspris rounds öre down, omkostnadsbelopp rounds öre
  up, and vinst/förlust is derived from the two rounded amounts; page totals are the sums
  of the rows printed above them.
- **ISO-8859-1** output; characters the encoding cannot hold are refused with a
  `DataFormatError` that names them, never written as `?`.
- **Personnummer:** 12 digits with century and a correct check digit.
- Text values may not contain `#` or line breaks; `year` must be a four-digit income year;
  at most nine rows per page; merged crypto lines must be section D fields, numbered 1..n.

### Correctness and safety
- All arithmetic in `Decimal`. A `float` is read at 15 significant digits, so binary noise
  (`0.1 * 3 * 1000 == 300.00000000000006`) cannot move a krona; exact input is used as
  given. The CLI reads JSON numbers as `Decimal`.
- Fractional quantities are accepted and rounded up to a whole antal.
- Validation errors are `ValidationError` / `DataFormatError` / `ConfigurationError`
  (all `SRUGeneratorError`), never raw `decimal` or `TypeError` exceptions.
- SRU files are written readable by their owner only (`0600`); importing the package
  configures no logging; no network access, no runtime dependencies.
- Character conversion for names ISO-8859-1 cannot hold comes from the optional
  [text-converters](https://github.com/Nikolaos-Paximadakis/text-converters) package:
  `load_character_converter(name)` (also behind the CLI's `--character-conversion` and
  `SRUConfig.get_character_converter()`) imports it lazily when installed (tested with
  0.2.0: `pip install "git+https://github.com/Nikolaos-Paximadakis/text-converters.git@v0.2.0"`);
  `"none"` imports nothing. sru-generator still has no runtime dependencies. The bundled
  fallback gives the same output as text-converters 0.2.0, including French œ/æ as oe/ae.

### Quality
- Typed (`py.typed`); `mypy --strict` and pyright strict pass. ruff, strict pytest
  (warnings are errors), 99% test coverage including property-based tests of the K4
  rules, and tests that run every example.
- Python 3.11-3.14.

### Deprecated
- The character converters bundled with sru-generator: used as a fallback, with a
  `DeprecationWarning` (and a note on the CLI's stderr), when text-converters is not
  installed or is outdated. They will be removed in 2.0, as will the top-level names
  `convert_*_characters_to_english`, `get_character_converter`, `CHARACTER_CONVERTERS`
  and `no_conversion` (they warn when used; use `load_character_converter` or
  `text_converters`).
- `SRUConfig` fields that nothing reads (`validation_level`, `rounding_mode`,
  `auto_convert_currency`, `log_level`, `custom_validators`, ...) warn when set and will
  be removed in 2.0.
