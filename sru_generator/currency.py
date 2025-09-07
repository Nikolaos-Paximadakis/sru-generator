"""
Currency handling and conversion for SRU Generator package.
"""

from decimal import Decimal, ROUND_HALF_EVEN
from typing import Dict, Optional, Union
from dataclasses import dataclass

from .exceptions import CurrencyError, ValidationError


@dataclass
class CurrencyAmount:
    """
    Represents a monetary amount with currency information.
    """
    amount: Decimal
    currency: str

    def __post_init__(self):
        """Validate currency amount after initialization."""
        if self.amount < 0:
            raise ValidationError(
                f"Currency amount cannot be negative: {self.amount}",
                field="amount",
                value=self.amount
            )

        if not self.currency or len(self.currency) != 3:
            raise ValidationError(
                f"Currency code must be 3 characters: {self.currency}",
                field="currency",
                value=self.currency
            )

    def to_sek(self, exchange_rate: float) -> Decimal:
        """Convert amount to SEK using exchange rate."""
        if exchange_rate <= 0:
            raise CurrencyError(
                f"Exchange rate must be positive: {exchange_rate}",
                exchange_rate=exchange_rate
            )

        return (self.amount * Decimal(str(exchange_rate))).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_EVEN
        )

    def __str__(self) -> str:
        return f"{self.amount} {self.currency}"


class CurrencyConverter:
    """
    Handles currency conversion operations.
    """

    def __init__(self, default_currency: str = "SEK"):
        self.default_currency = default_currency.upper()
        self.exchange_rates: Dict[str, float] = {}

    def set_exchange_rate(
            self,
            from_currency: str,
            to_currency: str,
            rate: float):
        """Set exchange rate between two currencies."""
        if rate <= 0:
            raise CurrencyError(
                f"Exchange rate must be positive: {rate}",
                exchange_rate=rate
            )

        key = f"{from_currency.upper()}_{to_currency.upper()}"
        self.exchange_rates[key] = rate

    def get_exchange_rate(self, from_currency: str, to_currency: str) -> float:
        """Get exchange rate between two currencies."""
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()

        if from_currency == to_currency:
            return 1.0

        # Try direct rate
        key = f"{from_currency}_{to_currency}"
        if key in self.exchange_rates:
            return self.exchange_rates[key]

        # Try inverse rate
        inverse_key = f"{to_currency}_{from_currency}"
        if inverse_key in self.exchange_rates:
            return 1.0 / self.exchange_rates[inverse_key]

        # Try through default currency
        if from_currency != self.default_currency and to_currency != self.default_currency:
            try:
                from_to_default = self.get_exchange_rate(
                    from_currency, self.default_currency)
                default_to_target = self.get_exchange_rate(
                    self.default_currency, to_currency)
                return from_to_default * default_to_target
            except CurrencyError:
                pass

        raise CurrencyError(
            f"No exchange rate found for {from_currency} to {to_currency}",
            currency=f"{from_currency}_{to_currency}"
        )

    def convert(self, amount: Union[Decimal, float, int],
                from_currency: str, to_currency: str) -> Decimal:
        """Convert amount from one currency to another."""
        if isinstance(amount, (int, float)):
            amount = Decimal(str(amount))

        if amount < 0:
            raise ValidationError(
                f"Amount cannot be negative: {amount}",
                field="amount",
                value=amount
            )

        exchange_rate = self.get_exchange_rate(from_currency, to_currency)
        converted = amount * Decimal(str(exchange_rate))

        return converted.quantize(Decimal('0.01'), rounding=ROUND_HALF_EVEN)

    def convert_to_sek(self, amount: Union[Decimal, float, int],
                       currency: str) -> Decimal:
        """Convert amount to SEK."""
        return self.convert(amount, currency, self.default_currency)

    def load_exchange_rates(self, rates: Dict[str, float]):
        """Load multiple exchange rates at once."""
        for currency, rate in rates.items():
            if currency.upper() != self.default_currency:
                self.set_exchange_rate(currency, self.default_currency, rate)


# Global currency converter instance
_currency_converter = CurrencyConverter()


def get_currency_converter() -> CurrencyConverter:
    """Get the global currency converter instance."""
    return _currency_converter


def set_exchange_rate(from_currency: str, to_currency: str, rate: float):
    """Set exchange rate in the global converter."""
    _currency_converter.set_exchange_rate(from_currency, to_currency, rate)


def convert_currency(amount: Union[Decimal, float, int],
                     from_currency: str, to_currency: str) -> Decimal:
    """Convert amount using the global converter."""
    return _currency_converter.convert(amount, from_currency, to_currency)


def convert_to_sek(
        amount: Union[Decimal, float, int], currency: str) -> Decimal:
    """Convert amount to SEK using the global converter."""
    return _currency_converter.convert_to_sek(amount, currency)


# Common currency codes
SUPPORTED_CURRENCIES = {
    "SEK": "Swedish Krona",
    "USD": "US Dollar",
    "EUR": "Euro",
    "GBP": "British Pound",
    "NOK": "Norwegian Krone",
    "DKK": "Danish Krone",
    "CHF": "Swiss Franc",
    "JPY": "Japanese Yen",
    "CAD": "Canadian Dollar",
    "AUD": "Australian Dollar",
}


def is_supported_currency(currency: str) -> bool:
    """Check if currency is supported."""
    return currency.upper() in SUPPORTED_CURRENCIES


def get_currency_name(currency: str) -> Optional[str]:
    """Get the full name of a currency."""
    return SUPPORTED_CURRENCIES.get(currency.upper())
