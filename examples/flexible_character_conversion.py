#!/usr/bin/env python3
"""
Example demonstrating character conversion for SRU files.

Converters come from the text-converters package:
    pip install text-converters
Inside an application, sru_generator.load_character_converter(name) gives the same
converters and falls back to sru-generator's bundled copy (deprecated) when
text-converters is not installed.
"""

from sru_generator import build_blanketter_sru, write_sru_file
from sru_generator.models import PersonalInfo

try:
    from text_converters import get_character_converter
except ImportError:
    raise SystemExit(
        "This example needs text-converters: pip install text-converters"
    ) from None

ME: PersonalInfo = {
    "personal_number": "198112189876",  # made-up example
    "full_name": "John Doe",
    "postal_code": "11122",
    "city_name": "Stockholm",
}

TRADE_DATA = [
    {
        "quantity": 100,
        "stock": "Αθήνα",  # Greek: not representable in ISO-8859-1
        "net value": 15000.00,
        "total net value of purchase": 14000.00,
    },
    {
        "quantity": 50,
        "stock": "Göteborg",  # Swedish: ISO-8859-1 holds it as it is
        "net value": 12000.00,
        "total net value of purchase": 13000.00,
    },
    {
        "quantity": 200,
        "stock": "München",  # German
        "net value": 25000.00,
        "total net value of purchase": 20000.00,
    },
]


def write_and_report(file_name, converter):
    """SRU files are ISO-8859-1: transliterate Greek text, or the write fails."""
    # build_blanketter_sru validates and writes a complete file (ending #FIL_SLUT).
    content = build_blanketter_sru(TRADE_DATA, ME, 2024, character_converter=converter)
    if write_sru_file(file_name, content):
        print(f"✓ Generated: {file_name}")
    else:
        print(
            f"✗ Not written: {file_name} "
            "(text outside ISO-8859-1; use the greek converter)"
        )


def keep_latin1(text: str) -> str:
    """A custom converter: drop what ISO-8859-1 cannot hold (any str -> str works)."""
    return "".join(c for c in text if ord(c) <= 0xFF)


def main():
    print("=== SRU Generator - Character Conversion Demo ===\n")
    for name in ("none", "greek", "swedish", "german"):
        print(f"{name} converter:")
        write_and_report(f"{name}_conversion.sru", get_character_converter(name))
    print("custom converter:")
    write_and_report("custom_converter.sru", keep_latin1)
    print("\nOnly 'greek' (and the custom one) can write the Greek stock name.")


if __name__ == "__main__":
    main()
