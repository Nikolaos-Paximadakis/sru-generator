"""
High-level helpers for building complete SRU file contents.
"""

from typing import Iterable, Optional, Sequence

from .models import CryptoSRUGroup, PersonalInfo, SRUTradeRow
from .sru_generator import (
    generate_sru_info_content,
    generate_sru_trade_content,
    merge_sru_groups,
)
from .validators import validate_personal_info, validate_trade_data


def build_info_sru(personal_info: PersonalInfo) -> str:
    """
    Build a complete ``info.sru`` file content string from generic personal info.
    """
    validated = validate_personal_info(dict(personal_info))
    return generate_sru_info_content(
        personal_number=validated["personal_number"],
        full_name=validated["full_name"],
        postal_code=validated["postal_code"],
        city_name=validated["city_name"],
    )


def build_blanketter_sru(
    trade_rows: Sequence[SRUTradeRow],
    personal_info: PersonalInfo,
    year: int,
    crypto_groups: Optional[Iterable[CryptoSRUGroup]] = None,
    *,
    items_per_group: int = 9,
    character_converter=None,
) -> str:
    """
    Build a complete ``blanketter.sru`` file content string from generic trade rows.
    """
    validated_personal = validate_personal_info(dict(personal_info))
    validated_trades = validate_trade_data([dict(row) for row in trade_rows])
    normalized_crypto_groups = [dict(group) for group in (crypto_groups or [])]

    trade_content = generate_sru_trade_content(
        trade_data=validated_trades,
        full_name=validated_personal["full_name"],
        personal_number=validated_personal["personal_number"],
        year=year,
        items_per_group=items_per_group,
        character_converter=character_converter,
    )

    return merge_sru_groups(
        stock_content=trade_content,
        crypto_groups=normalized_crypto_groups,
        full_name=validated_personal["full_name"],
        personal_number=validated_personal["personal_number"],
        year=year,
    )


def encode_sru_content(content: str) -> bytes:
    """
    Encode SRU content for file downloads or HTTP responses.
    """
    return content.encode("utf-8")
