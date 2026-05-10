"""
Public input types for the SRU Generator package.
"""

from typing import List, TypedDict


class PersonalInfo(TypedDict):
    personal_number: str
    full_name: str
    postal_code: str
    city_name: str


SRUTradeRow = TypedDict(
    "SRUTradeRow",
    {
        "quantity": int,
        "stock": str,
        "net value": float,
        "total net value of purchase": float,
        "profit/loss": float,
        "currency": str,
        "exchange_rate": float,
    },
    total=False,
)


class CryptoSRUGroup(TypedDict):
    group_number: int
    uppgifter: List[str]
