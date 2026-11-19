"""
Reading amounts and quantities as exact decimals.
"""

from decimal import Decimal

#: A double carries 15 significant decimal digits reliably (DBL_DIG); the digits after
#: that are binary noise. 0.1 * 3 * 1000 is 300.00000000000006, and Skatteverket's
#: "round öre up" rule would turn that noise into a whole extra krona.
FLOAT_SIGNIFICANT_DIGITS = 15


def to_decimal(value: object) -> Decimal:
    """``value`` as a Decimal, without the binary noise a ``float`` carries.

    A ``float`` is read at 15 significant digits, so 300.00000000000006 becomes 300 and
    209.99999999999997 becomes 210, at any magnitude. Everything else (``Decimal``,
    ``int``, ``str``) is exact already and is converted with ``Decimal(str(value))``,
    so ``Decimal("1.999")`` stays 1.999 and the K4 rounding rules see it as given.

    The cut-off is a trade-off: a float with more than 15 significant digits, such as
    1.999999999999999, cannot be told apart from noise and is read as 2. Pass Decimal
    or str when every digit matters.
    """
    if isinstance(value, float):
        return Decimal(f"{value:.{FLOAT_SIGNIFICANT_DIGITS}g}")
    return Decimal(str(value))
