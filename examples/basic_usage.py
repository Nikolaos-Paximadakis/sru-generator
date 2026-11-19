#!/usr/bin/env python3
"""
Basic usage: build INFO.SRU and BLANKETTER.SRU from SEK amounts.

The builders validate the input and write complete files (BLANKETTER.SRU ends with
#FIL_SLUT). Check every row and total in Skatteverket's e-service before you sign.
"""

from decimal import Decimal

from sru_generator import (
    ValidationError,
    build_blanketter_sru,
    build_info_sru,
    write_sru_file,
)
from sru_generator.models import PersonalInfo, SRUTradeRow

ME: PersonalInfo = {
    "personal_number": "198112189876",  # made-up example
    "full_name": "Test Person",
    "postal_code": "11122",
    "city_name": "Stockholm",
}

SALES: list[SRUTradeRow] = [
    {
        "quantity": 100,
        "stock": "Ericsson B",
        "net value": Decimal("15000.75"),  # försäljningspris, SEK
        "total net value of purchase": Decimal("14000.20"),  # omkostnadsbelopp, SEK
    },
    {
        "quantity": Decimal("2.5"),  # fractional shares: written rounded up
        "stock": "Investor B",
        "net value": Decimal("2000"),
        "total net value of purchase": Decimal("2600"),
    },
]


def main() -> None:
    try:
        info = build_info_sru(ME)
        blanketter = build_blanketter_sru(SALES, ME, year=2025)
    except ValidationError as e:
        raise SystemExit(f"Invalid input: {e}") from e

    for file_name, content in (("INFO.SRU", info), ("BLANKETTER.SRU", blanketter)):
        if not write_sru_file(file_name, content):
            raise SystemExit(f"Could not write {file_name}")
        print(f"✓ {file_name}")
    print(blanketter)


if __name__ == "__main__":
    main()
