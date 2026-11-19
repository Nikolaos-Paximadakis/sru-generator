"""Property-based tests: the K4 rules must hold for every input, not just examples.

Hypothesis generates many random amounts and trade lists and checks invariants that
the written file must satisfy whatever the figures are.
"""

import math
from datetime import date
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from hypothesis import given, settings
from hypothesis import strategies as st

from sru_generator import (
    build_blanketter_sru,
    read_crypto_sru_content,
    round_k4_cost_basis,
    round_k4_sale_price,
    validate_personal_info,
    write_sru_file,
)
from sru_generator.models import CryptoSRUGroup, PersonalInfo, SRUTradeRow
from sru_generator.validators import luhn_check_digit_ok

ME: PersonalInfo = {
    "personal_number": "198112189876",
    "full_name": "Test Person",
    "postal_code": "11122",
    "city_name": "Stockholm",
}

# Amounts as Skatteverket's fields allow (up to 12 digits of kronor), with up to four
# decimals so that sub-öre input is exercised too.
amounts = st.decimals(
    min_value=Decimal(0),
    max_value=Decimal("99999999999.9999"),
    places=4,
    allow_nan=False,
    allow_infinity=False,
)
ore_amounts = st.decimals(
    min_value=Decimal(0),
    max_value=Decimal("999999999.99"),
    places=2,
    allow_nan=False,
    allow_infinity=False,
)
rows = st.builds(
    lambda quantity, sale, cost, n: SRUTradeRow(
        {
            "quantity": quantity,
            "stock": f"Stock {n}",
            "net value": sale,
            "total net value of purchase": cost,
        }
    ),
    st.integers(min_value=0, max_value=10**6),
    ore_amounts,
    ore_amounts,
    st.integers(min_value=0, max_value=999),
)


def _pages(content: str) -> list[dict[str, list[str]]]:
    pages = []
    for block in content.split("#BLANKETT K4-")[1:]:
        fields: dict[str, list[str]] = {}
        for line in block.splitlines():
            if line.startswith("#UPPGIFT "):
                _, code, value = line.split(" ", 2)
                fields.setdefault(code, []).append(value)
        pages.append(fields)
    return pages


@given(amounts)
def test_sale_price_rounds_ore_down_and_cost_basis_rounds_ore_up(
    value: Decimal,
) -> None:
    sale = round_k4_sale_price(value)
    cost = round_k4_cost_basis(value)
    assert sale == math.floor(value)
    assert cost == math.ceil(value)
    assert sale <= value < sale + 1
    assert cost - 1 < value <= cost


@given(ore_amounts)
def test_a_float_rounds_like_its_exact_decimal(value: Decimal) -> None:
    """Float noise must never move a krona: 0.1 * 3 * 1000 is 300.00000000000006."""
    assert round_k4_sale_price(float(value)) == round_k4_sale_price(value)
    assert round_k4_cost_basis(float(value)) == round_k4_cost_basis(value)


@settings(deadline=None)
@given(st.lists(rows, min_size=1, max_size=30))
def test_every_row_and_page_adds_up(trades: list[SRUTradeRow]) -> None:
    pages = _pages(build_blanketter_sru(trades, ME, 2025))

    assert len(pages) == math.ceil(len(trades) / 9)
    assert [page["7014"] for page in pages] == [
        [str(n)] for n in range(1, len(pages) + 1)
    ]

    written_rows = 0
    for page in pages:
        sold = cost = profit = loss = 0
        for row in range(9):
            base = 3100 + 10 * row
            if str(base + 2) not in page:
                continue
            written_rows += 1
            row_sale = int(page[str(base + 2)][0])
            row_cost = int(page[str(base + 3)][0])
            row_profit = int(page.get(str(base + 4), ["0"])[0])
            row_loss = int(page.get(str(base + 5), ["0"])[0])
            assert row_sale - row_cost == row_profit - row_loss  # vinst/förlust derived
            assert row_profit >= 0 and row_loss >= 0
            assert not (row_profit and row_loss)
            sold, cost = sold + row_sale, cost + row_cost
            profit, loss = profit + row_profit, loss + row_loss
        assert int(page["3300"][0]) == sold
        assert int(page["3301"][0]) == cost
        assert int(page.get("3304", ["0"])[0]) == profit
        assert int(page.get("3305", ["0"])[0]) == loss
    assert written_rows == len(trades)


section_d_line = st.builds(
    lambda row, column, value: f"#UPPGIFT {3400 + 10 * row + column} {value}",
    st.integers(min_value=1, max_value=7),
    st.integers(min_value=0, max_value=5),
    st.integers(min_value=0, max_value=10**9),
)


@settings(deadline=None)
@given(
    st.lists(st.lists(section_d_line, min_size=1, max_size=10), min_size=1, max_size=5)
)
def test_crypto_pages_survive_a_write_and_read(pages: list[list[str]]) -> None:
    groups: list[CryptoSRUGroup] = [
        {"group_number": number, "uppgifter": lines}
        for number, lines in enumerate(pages, start=1)
    ]
    content = build_blanketter_sru([], ME, 2025, crypto_groups=groups)
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "crypto.sru"
        assert write_sru_file(str(path), content)
        assert read_crypto_sru_content(str(path)) == groups


def _with_check_digit(first_eleven: str) -> str:
    for digit in "0123456789":
        if luhn_check_digit_ok(first_eleven + digit):
            return first_eleven + digit
    raise AssertionError("unreachable: one digit always fits")


@given(
    st.dates(min_value=date(1900, 1, 1)),
    st.integers(min_value=0, max_value=999),
)
def test_personnummer_with_a_check_digit_pass_and_a_typo_does_not(
    born: date, serial: int
) -> None:
    number = _with_check_digit(f"{born:%Y%m%d}{serial:03d}")
    assert validate_personal_info({**ME, "personal_number": number})
    typo = number[:-1] + str((int(number[-1]) + 1) % 10)
    assert not luhn_check_digit_ok(typo)
