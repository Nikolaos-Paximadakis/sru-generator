#!/usr/bin/env python3
"""
Validation on its own, converting foreign amounts to SEK, then building the file.

Nothing is converted automatically: convert to SEK first (here with the package's
currency helpers; which rate to use is a tax question), then build.
"""

from decimal import Decimal

from sru_generator import (
    ValidationError,
    build_blanketter_sru,
    convert_to_sek,
    set_exchange_rate,
    validate_personal_info,
    validate_trade_data,
    write_sru_file,
)
from sru_generator.models import PersonalInfo, SRUTradeRow

ME: PersonalInfo = {
    "personal_number": "198112189876",  # made-up example
    "full_name": "Test Person",
    "postal_code": "11122",
    "city_name": "Stockholm",
}


def show_validation() -> None:
    print("=== Validation ===")
    person = validate_personal_info(ME)
    print(f"✓ Personal details for {person['full_name']}")

    invalid = [{"quantity": -10, "stock": "", "net value": "not a number"}]
    try:
        validate_trade_data(invalid)
    except ValidationError as e:
        print(f"✓ Refused as expected: {e}")

    try:
        validate_personal_info({**ME, "personal_number": "8112189876"})
    except ValidationError as e:
        print(f"✓ Refused as expected: {e}")


def build_from_foreign_amounts() -> str:
    print("\n=== Foreign amounts to SEK ===")
    set_exchange_rate("USD", "SEK", 10.5)
    set_exchange_rate("EUR", "SEK", 11.2)
    foreign = [
        ("Apple Inc", 100, Decimal("1500.00"), Decimal("1400.00"), "USD"),
        ("SAP SE", 50, Decimal("2000.00"), Decimal("1900.00"), "EUR"),
    ]
    sales: list[SRUTradeRow] = []
    for stock, quantity, sale, cost, currency in foreign:
        sale_sek = convert_to_sek(sale, currency)
        cost_sek = convert_to_sek(cost, currency)
        print(f"  {stock}: {sale} {currency} -> {sale_sek} SEK (cost {cost_sek} SEK)")
        sales.append(
            {
                "quantity": quantity,
                "stock": stock,
                "net value": sale_sek,
                "total net value of purchase": cost_sek,
            }
        )
    return build_blanketter_sru(sales, ME, year=2025)


def main() -> None:
    show_validation()
    content = build_from_foreign_amounts()
    if not write_sru_file("BLANKETTER.SRU", content):
        raise SystemExit("Could not write BLANKETTER.SRU")
    print("\n✓ BLANKETTER.SRU")


if __name__ == "__main__":
    main()
