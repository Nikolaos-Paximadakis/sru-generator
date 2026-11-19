"""
Public input types for the SRU Generator package.
"""

from collections.abc import Callable
from decimal import Decimal
from typing import NotRequired, TypedDict

#: A monetary amount or quantity as callers may supply it. Every value is converted with
#: ``to_decimal`` before any arithmetic. Prefer ``Decimal`` or ``str``: a
#: ``float`` carries binary noise (``0.1 * 3 * 1000 == 300.00000000000006``), which is
#: why a float is read at 15 significant digits (see ``to_decimal`` in ``amounts.py``).
Amount = Decimal | int | float | str

#: Transliterates text before it is written, e.g. Greek to Latin letters.
CharacterConverter = Callable[[str], str]


class PersonalInfo(TypedDict):
    personal_number: str
    full_name: str
    postal_code: str
    city_name: str


# Functional syntax because several keys contain spaces or slashes.
SRUTradeRow = TypedDict(
    "SRUTradeRow",
    {
        "quantity": Amount,
        "stock": str,
        "net value": Amount,
        "total net value of purchase": Amount,
        "profit/loss": NotRequired[Amount],
        "currency": NotRequired[str],
        "exchange_rate": NotRequired[Amount],
    },
)


# What ``validate_trade_data`` returns: every amount is a Decimal, and "profit/loss" is
# filled in (calculated) when the caller left it out. Still a plain dict at runtime.
ValidatedTradeRow = TypedDict(
    "ValidatedTradeRow",
    {
        "quantity": Decimal,
        "stock": str,
        "net value": Decimal,
        "total net value of purchase": Decimal,
        "profit/loss": Decimal | None,
        "currency": str | None,
        "exchange_rate": Decimal | None,
    },
)


class CryptoSRUGroup(TypedDict):
    """One K4 page of section D lines, as read by ``read_crypto_sru_content``."""

    group_number: int
    uppgifter: list[str]
