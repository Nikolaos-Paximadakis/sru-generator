#!/usr/bin/env python3
"""
Trades from a JSON file, optionally merged with crypto pages from another tool.

The JSON is read with parse_float=Decimal so amounts keep their exact value. If
crypto_k4.sru exists (a K4 SRU file with section D rows, e.g. from a crypto tax
service), its pages are merged with the share pages.
"""

import json
from decimal import Decimal
from pathlib import Path

from sru_generator import (
    SRUGeneratorError,
    build_blanketter_sru,
    build_info_sru,
    read_crypto_sru_content,
    write_sru_file,
)
from sru_generator.models import PersonalInfo

ME: PersonalInfo = {
    "personal_number": "198112189876",  # made-up example
    "full_name": "Test Person",
    "postal_code": "11122",
    "city_name": "Stockholm",
}
HERE = Path(__file__).parent


def main() -> None:
    with (HERE / "sample_trades.json").open(encoding="utf-8") as f:
        sales = json.load(f, parse_float=Decimal)
    print(f"✓ Loaded {len(sales)} sales")

    crypto_file = Path("crypto_k4.sru")
    crypto_pages = read_crypto_sru_content(str(crypto_file))  # [] if it is missing
    print(f"✓ {len(crypto_pages)} crypto page(s) from {crypto_file}")

    try:
        blanketter = build_blanketter_sru(sales, ME, 2024, crypto_groups=crypto_pages)
    except SRUGeneratorError as e:
        raise SystemExit(f"Cannot build BLANKETTER.SRU: {e}") from e

    for file_name, content in (
        ("INFO.SRU", build_info_sru(ME)),
        ("BLANKETTER.SRU", blanketter),
    ):
        if not write_sru_file(file_name, content):
            raise SystemExit(f"Could not write {file_name}")
        print(f"✓ {file_name}")


if __name__ == "__main__":
    main()
