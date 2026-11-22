# sru-generator

[![CI](https://github.com/Nikolaos-Paximadakis/sru-generator/actions/workflows/ci.yml/badge.svg)](https://github.com/Nikolaos-Paximadakis/sru-generator/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/sru-generator.svg)](https://pypi.org/project/sru-generator/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/Nikolaos-Paximadakis/sru-generator/blob/main/LICENSE)
[![Not tax advice](https://img.shields.io/badge/Not-tax%20advice-orange.svg)](https://github.com/Nikolaos-Paximadakis/sru-generator/blob/main/DISCLAIMER.md)

Generate the SRU files (`INFO.SRU` + `BLANKETTER.SRU`) that Skatteverket's e-service
imports for **bilaga K4**: sales of shares, funds and crypto. Pure Python, no
dependencies.

> **Not tax advice. Not affiliated with Skatteverket.** You are responsible for every figure
> you submit: check the imported K4 in Skatteverket's e-service before you sign. Provided
> as is, without warranty — see the [disclaimer](https://github.com/Nikolaos-Paximadakis/sru-generator/blob/main/DISCLAIMER.md) (also in
> Swedish) and the [license](https://github.com/Nikolaos-Paximadakis/sru-generator/blob/main/LICENSE).

**Who it is for:** people writing a tool that turns broker or exchange exports into a
K4. Most such tools are tied to one broker and re-implement the same file details. This
package is that shared part: page grouping, field codes, Skatteverket's rounding rules,
page totals and the file encoding. You bring the figures, already in SEK; it writes the
file.

**På svenska:** ett Python-bibliotek som skapar SRU-filer för bilaga K4 (försäljning av
aktier, fonder och kryptovalutor) som kan importeras i Skatteverkets e-tjänst. Du lämnar
beloppen i kronor; biblioteket sköter filformatet, avrundningen och summeringen. Inte
skatterådgivning — du ansvarar själv för deklarationen.

## Install

```bash
pip install sru-generator
pip install "sru-generator[transliterate]"   # also the named character converters
```

Python 3.11 or newer. The extra installs
[text-converters](https://github.com/Nikolaos-Paximadakis/text-converters), for stock
names in Greek and other text ISO-8859-1 cannot hold ([Characters](#characters)).

## Quick start

```python
from sru_generator import build_blanketter_sru, build_info_sru, write_sru_file

me = {
    "personal_number": "198112189876",  # made-up example
    "full_name": "Test Person",
    "postal_code": "11122",
    "city_name": "Stockholm",
}
sales = [
    {
        "quantity": 100,
        "stock": "Ericsson B",
        "net value": 15000.75,  # försäljningspris, SEK
        "total net value of purchase": 14000.20,  # omkostnadsbelopp, SEK
    },
    {
        "quantity": 2.5,  # fractional shares are fine; written rounded up
        "stock": "Investor B",
        "net value": 2000,
        "total net value of purchase": 2600,
    },
]

write_sru_file("INFO.SRU", build_info_sru(me))
write_sru_file("BLANKETTER.SRU", build_blanketter_sru(sales, me, year=2025))
```

`BLANKETTER.SRU` then contains (the header's date and time will differ):

```text
#BLANKETT K4-2025P4
#IDENTITET 198112189876 20260301 120000
#NAMN Test Person
#UPPGIFT 7014 1
#UPPGIFT 3100 100
#UPPGIFT 3101 Ericsson B
#UPPGIFT 3102 15000
#UPPGIFT 3103 14001
#UPPGIFT 3104 999
#UPPGIFT 3110 3
#UPPGIFT 3111 Investor B
#UPPGIFT 3112 2000
#UPPGIFT 3113 2600
#UPPGIFT 3115 600
#UPPGIFT 3300 17000
#UPPGIFT 3301 16601
#UPPGIFT 3304 999
#UPPGIFT 3305 600
#BLANKETTSLUT
#FIL_SLUT
```

Note the rounding: 15000.75 became 15000 and 14000.20 became 14001 (see
[Rounding](#rounding)). Up to nine sales go on each K4 page; more sales give more pages.

Then, in Skatteverket's **Inkomstdeklaration 1** e-service, open **Bilagor**, choose K4,
then **Importera** and select `BLANKETTER.SRU` (see Skatteverket's page
[Lämna en bilaga till deklarationen](https://skatteverket.se/privat/deklaration/lamnaenbilagatilldeklarationen.4.515a6be615c637b9aa46366.html)).
`INFO.SRU` is needed when you send files through Skatteverket's Filöverföring service.
**Check every row and total in the e-service before you sign.**

### Command line

The same from a shell. Personal details can come from options, environment variables or
a JSON profile; prefer the environment or a profile for the personnummer, because
command-line arguments end up in shell history.

```bash
export SRU_PERSONAL_NUMBER=198112189876 SRU_FULL_NAME="Test Person"
sru-generator info --postal-code 11122 --city-name Stockholm   # writes INFO.SRU
sru-generator trades --data sales.json --year 2025             # writes BLANKETTER.SRU

# or keep everything in a profile file (git-ignored if named profile*.json):
sru-generator info --profile profile.json
```

`sales.json` is a JSON list of the same dictionaries as `sales` above. `--year` defaults
to last year. Run `sru-generator trades --help` for the other options (crypto file,
character conversion, output path, `-v` for log messages).

## What the package does — and does not do

It **does**:

- validate each sale and your personal details, with clear errors;
- round each amount the way Skatteverket's K4 help text says (below);
- derive vinst/förlust from the rounded amounts, so every row adds up;
- split sales into pages of nine, number them, and write each page's totals;
- write ISO-8859-1, refusing characters that encoding cannot hold instead of writing `?`;
- merge K4 section D pages from an existing crypto SRU file with the share pages.

It does **not**:

- read broker or exchange exports;
- convert foreign currency for you (helpers exist, but nothing converts automatically);
- choose a cost-basis method (genomsnittsmetoden or schablonmetoden) or decide which K4
  section an asset belongs in;
- generate section D rows itself (it merges them from an existing file). Crypto belongs
  in section D, not in the share rows this package writes;
- contact Skatteverket or anything else on the network.

## Rounding

K4 amounts are whole kronor, and Skatteverket gives a different rule per column
([help text for bilaga K4](https://www8.skatteverket.se/hjalptexter/EfInk1k4_aktie.html)):

- **Försäljningspris:** öre rounded **down**.
- **Omkostnadsbelopp:** öre rounded **up**.
- **Vinst/förlust:** försäljningspris minus omkostnadsbelopp, *after* rounding. It is
  never rounded on its own. A `profit/loss` you supply is only cross-checked against
  the unrounded difference (tolerance 1 kr) and a warning is logged if it differs; it
  is not written.

A `float` is first read at 15 significant digits, so its binary noise cannot move a
figure by a krona: `0.1 * 3 * 1000` is `300.00000000000006`, which would otherwise
round *up* to an omkostnadsbelopp of 301. `Decimal`, `int` and `str` are exact and are
used as given, so `Decimal("100.001")` still rounds up to 101. (A float with more than
15 significant digits, such as `1.999999999999999`, cannot be told apart from noise and
is read as 2.) Prefer `Decimal` or strings for money; the CLI reads JSON numbers as
`Decimal`.

Page totals (3300, 3301, 3304, 3305) are the sums of the rows printed above them. Many
other K4 tools round every amount to the nearest krona, so their figures can differ from
this package's by 1 kr per row.

`quantity` (antal) may be fractional and is rounded **up** to a whole number, so a sale
of 0.25 units shows 1, not 0: section A's antal is a whole number in Skatteverket's file
description. Antal does not affect the gain or loss.

`year` must be a four-digit income year from 2000: `K4-2025P4` declares income year
2025. `items_per_group` (rows per page) may be 1–9, the rows K4 section A has.

## Input reference

### A sale

| Key | Type | Required | Meaning | Allowed |
|-----|------|----------|---------|---------|
| `quantity` | number | yes | Units sold; fractions allowed, written rounded up | 0 – 999,999,999,999 |
| `stock` | string | yes | Name of the security (Beteckning) | 1–80 characters, no `#` or line breaks |
| `net value` | number | yes | Försäljningspris in SEK, after fees | 0 – 999,999,999,999 |
| `total net value of purchase` | number | yes | Omkostnadsbelopp in SEK, including fees | 0 – 999,999,999,999 |
| `profit/loss` | number | no | Your own figure, cross-checked only | |
| `currency` | string | no | Validated only (see below); amounts must already be SEK | one of the supported codes |
| `exchange_rate` | number | no | Validated only | 0.000001 – 1,000,000 |

Numbers may be `int`, `float`, `Decimal` or numeric strings; all arithmetic uses
`Decimal`.

### Personal details

| Key | Meaning | Allowed |
|-----|---------|---------|
| `personal_number` | Personnummer with century, as Skatteverket requires: `198112189876` (a hyphen before the last four digits is accepted) | 12 digits, correct check digit |
| `full_name` | Name | 1–100 characters, no `#` or line breaks |
| `postal_code` | Postnummer | 5 digits |
| `city_name` | Postort | 1–50 characters, no `#` or line breaks |

### Characters

SRU files are ISO-8859-1, so Swedish letters (å, ä, ö, é) are written as they are and
need no conversion. Text the encoding cannot hold — Greek, Cyrillic, `€`, typographic
quotes — makes `write_sru_file` (returns `False`) and `encode_sru_content` (raises
`DataFormatError`) fail with a message naming the characters, instead of silently
writing `?`. Pass a `character_converter` (any `str -> str` function) to transliterate
stock names.

**The named converters come from [text-converters](https://github.com/Nikolaos-Paximadakis/text-converters)**
(`greek`, `swedish`, `german`, `french`, `spanish`), installed with the `transliterate`
extra:

```bash
pip install "sru-generator[transliterate]"
```

```python
from sru_generator import build_blanketter_sru, load_character_converter

greek = load_character_converter("greek")  # needs the transliterate extra
content = build_blanketter_sru(sales, me, year=2025, character_converter=greek)
```

sru-generator bundles no conversion rules and still has no required dependencies:
text-converters is imported only when a named converter is asked for (`"none"` never
imports it). **Without it, a named converter raises `ConfigurationError`** with the
install command — from `load_character_converter`, `SRUConfig.get_character_converter()`
and the CLI's `--character-conversion` (which exits with status 2). So does an outdated
text-converters (one whose Greek converter does not give `Thessaloniki` for
`Θεσσαλονίκη`). A name is only a shortcut: `character_converter` takes any
`str -> str` function, such as the recipe below.

`greek` follows the Greek standard ELOT 743 letter by letter (η is `i`, ου is `ou`,
Θ/Χ/Ψ give `Th`/`Ch`/`Ps`, or `TH`/`CH`/`PS` in a word written in capitals) but not its
other letter pairs: `Ευαγγελισμός` becomes `Eyaggelismos`, not `Evangelismos`. `french`
writes œ/æ as `oe`/`ae`. The `swedish` converter strips å, ä and ö, which SRU files
do not require.

**For names in other scripts:** convert only the characters ISO-8859-1 cannot hold.
Apply the Greek converter first, then a transliteration library such as
[anyascii](https://pypi.org/project/anyascii/) (ISC licence) for any other script:

```python
from anyascii import anyascii
from text_converters import convert_greek_characters_to_english

from sru_generator import build_blanketter_sru


def to_latin1(text: str) -> str:
    """Transliterate only what ISO-8859-1 cannot hold; keep å, ä, ö as they are."""
    text = convert_greek_characters_to_english(text)
    return "".join(c if ord(c) <= 0xFF else anyascii(c) for c in text)


content = build_blanketter_sru(sales, me, year=2025, character_converter=to_latin1)
```

| Input | `to_latin1` | `anyascii` alone | `greek` |
|---|---|---|---|
| `Åsa Öberg` | `Åsa Öberg` | `Asa Oberg` | `Åsa Öberg` |
| `Θεσσαλονίκη Χανιά` | `Thessaloniki Chania` | `Thessaloniki Chania` | `Thessaloniki Chania` |
| `Παπαδόπουλος` | `Papadopoulos` | `Papadopoylos` | `Papadopoulos` |
| `Москва` | `Moskva` | `Moskva` | `Москва` (still fails) |
| `Ørsted €` | `Ørsted EUR` | `Orsted EUR` | `Ørsted €` (still fails) |

Don't pass `anyascii` directly: it converts *every* non-ASCII character, so Swedish
names would lose their å, ä and ö for no reason.

## More features

### Crypto pages (K4 section D)

If another tool produced a K4 SRU file with section D rows (for example from a crypto
tax service), merge its pages with your share pages:

```python
from sru_generator import build_blanketter_sru, read_crypto_sru_content

crypto_pages = read_crypto_sru_content("crypto_k4.sru")  # UTF-8 or ISO-8859-1
content = build_blanketter_sru(sales, me, year=2025, crypto_groups=crypto_pages)
```

With only crypto pages and no share sales, pass `sales=[]`.

The pages are checked before they are merged: every line must be a section D field
(`#UPPGIFT 3410`–`3475`, or the totals `3500`, `3501`, `3503`, `3504`), and the pages
must be numbered 1..n. `7014` (the page number) may appear anywhere on a page; a page
without it is numbered by its position. A file that cannot be read raises
`FileOperationError`, an unreadable page number `DataFormatError`; a missing file gives
an empty list and a warning.

### Currency helpers

Nothing is converted automatically. If you want help converting before you build:

```python
from sru_generator import convert_to_sek, set_exchange_rate

set_exchange_rate("USD", "SEK", 10.5)
sek = convert_to_sek(1500, "USD")  # Decimal("15750.00")
```

Supported codes: SEK, USD, EUR, GBP, NOK, DKK, CHF, JPY, CAD, AUD. Which rate to use
(the transaction day's or an average) is a tax question; check Skatteverket's guidance.

### Validation on its own

```python
from sru_generator import ValidationError, validate_personal_info, validate_trade_data

try:
    rows = validate_trade_data(sales)
    person = validate_personal_info(me)
except ValidationError as e:
    print(f"{e.field}: {e}")
```

`build_info_sru` and `build_blanketter_sru` run these for you.

### Configuration

`SRUConfig` / `create_config(...)` bundle the character converter, default currency and
exchange rates for applications that want one object to pass around: those three fields
are all it has. `SRUConfig.from_dict` checks each value and refuses unknown keys with a
`ConfigurationError`. The K4 rounding rule is not configurable.

### Logging

The package logs through the standard `logging` module under the name `sru_generator`
and is silent unless your application configures logging, for example
`logging.basicConfig(level=logging.INFO)`. Messages can include stock names and
amounts. The CLI shows warnings by default and more with `-v`.

## API overview

- **Build whole files:** `build_info_sru`, `build_blanketter_sru`, `write_sru_file`,
  `encode_sru_content` (bytes, for downloads or HTTP responses)
- **Lower level:** `generate_sru_info_content`, `generate_sru_trade_content` (pages
  only, without the closing `#FIL_SLUT`), `merge_sru_groups`, `read_crypto_sru_content`,
  `round_k4_sale_price`, `round_k4_cost_basis`, `round_k4_quantity`
- **Validation:** `validate_trade_data`, `validate_personal_info`,
  `TradeDataValidator`, `PersonalInfoValidator`, `create_custom_validator`
- **Characters and encoding:** `load_character_converter` (named converters, from the
  `transliterate` extra), `encode_sru_text`, `decode_sru_bytes`, `SRU_ENCODING`
- **Currency:** `convert_to_sek`, `convert_currency`, `set_exchange_rate`,
  `CurrencyConverter`
- **Configuration:** `SRUConfig`, `create_config`, `get_default_config`
- **Exceptions** (all subclass `SRUGeneratorError`): `ValidationError`,
  `BusinessRuleError`, `DataFormatError`, `CurrencyError`, `ConfigurationError`,
  `FileOperationError`

## Privacy and security

SRU files hold your personnummer and your transactions. The package writes them readable
by you only, never touches the network, and logs nothing unless asked. Never paste a real
SRU file or personnummer into an issue. See
[SECURITY.md](https://github.com/Nikolaos-Paximadakis/sru-generator/blob/main/SECURITY.md).

## Related projects

Broker-specific K4 tools that could build on a library like this include
[K4SRU](https://github.com/ebtcap/K4SRU) (Java, several brokers),
[IbkrToSru](https://github.com/JohanLarsson/IbkrToSru) (C#, IBKR) and
[K4Skatt](https://github.com/duga3/K4Skatt) (Python, IBKR).
[pysru-mab](https://pypi.org/project/pysru-mab/) reads and writes general SRU files and
targets the company forms (INK2).

## Contributing, changelog, license

- [CONTRIBUTING.md](https://github.com/Nikolaos-Paximadakis/sru-generator/blob/main/CONTRIBUTING.md)
  — setup, checks, and what belongs in this package
- [CHANGELOG.md](https://github.com/Nikolaos-Paximadakis/sru-generator/blob/main/CHANGELOG.md)
- [MIT License](https://github.com/Nikolaos-Paximadakis/sru-generator/blob/main/LICENSE)
  and [disclaimer](https://github.com/Nikolaos-Paximadakis/sru-generator/blob/main/DISCLAIMER.md)
