"""
Configuration management for SRU Generator package.
"""

import math
from collections.abc import Mapping
from dataclasses import dataclass, field, fields
from typing import TypedDict, TypeGuard, Unpack

from .character_converters import CONVERTER_NAMES, load_character_converter
from .exceptions import ConfigurationError
from .models import CharacterConverter


def _is_object_dict(value: object) -> TypeGuard[dict[object, object]]:
    return isinstance(value, dict)


def _check_character_converter(value: object) -> str:
    if not isinstance(value, str) or value not in CONVERTER_NAMES:
        available = ", ".join(CONVERTER_NAMES)
        raise ConfigurationError(
            f"Invalid character_converter {value!r}. Available options: {available}",
            config_key="character_converter",
            config_value=value,
        )
    return value


def _check_default_currency(value: object) -> str:
    if not isinstance(value, str):
        raise ConfigurationError(
            "default_currency must be a currency code string",
            config_key="default_currency",
            config_value=value,
        )
    return value


def _check_exchange_rates(value: object) -> dict[str, float]:
    """A copy of ``value`` if it maps 'FROM_TO' strings to positive finite numbers."""
    if _is_object_dict(value):
        rates: dict[str, float] = {}
        for key, rate in value.items():
            if not (
                isinstance(key, str)
                and isinstance(rate, int | float)
                and not isinstance(rate, bool)
                and math.isfinite(rate)
                and rate > 0
            ):
                break
            rates[key] = rate
        else:
            return rates
    raise ConfigurationError(
        "exchange_rates must map 'FROM_TO' strings to positive finite numbers",
        config_key="exchange_rates",
        config_value=value,
    )


@dataclass
class SRUConfig:
    """
    Configuration for SRU generation: the character converter and currency settings.

    The K4 rounding rule, validation and file encoding are fixed by Skatteverket's
    rules, and currency is never converted automatically, so none of them is a setting.
    """

    character_converter: str = "none"
    default_currency: str = "SEK"
    exchange_rates: dict[str, float] = field(default_factory=dict[str, float])

    def __post_init__(self) -> None:
        """Validate every field: a wrong value fails now, not when it is used."""
        # The checks take object: the declared types are what is being checked.
        _check_character_converter(self.character_converter)
        _check_default_currency(self.default_currency)
        self.exchange_rates = _check_exchange_rates(self.exchange_rates)

    def get_character_converter(self) -> CharacterConverter:
        """The converter for ``character_converter`` (see ``load_character_converter``).

        Any name but "none" needs text-converters; without it this raises
        ``ConfigurationError``.
        """
        return load_character_converter(self.character_converter)

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
        if self.default_currency not in {from_currency, to_currency}:
            try:
                from_to_default = self.get_exchange_rate(
                    from_currency, self.default_currency
                )
                default_to_target = self.get_exchange_rate(
                    self.default_currency, to_currency
                )
                return from_to_default * default_to_target
            except ConfigurationError:
                pass

        raise ConfigurationError(
            f"No exchange rate found for {from_currency} to {to_currency}",
            config_key="exchange_rates",
            config_value=f"{from_currency}_{to_currency}",
        )

    def set_exchange_rate(
        self, from_currency: str, to_currency: str, rate: float
    ) -> None:
        """Set exchange rate between two currencies."""
        if rate <= 0:
            raise ConfigurationError(
                f"Exchange rate must be positive, got {rate}",
                config_key="exchange_rate",
                config_value=rate,
            )

        if from_currency.upper() == to_currency.upper():
            raise ConfigurationError(
                "Cannot set exchange rate for same currency",
                config_key="exchange_rate",
                config_value=f"{from_currency}_{to_currency}",
            )

        key = f"{from_currency.upper()}_{to_currency.upper()}"
        self.exchange_rates[key] = rate

    def to_dict(self) -> dict[str, object]:
        """Convert configuration to dictionary."""
        return {
            "character_converter": self.character_converter,
            "default_currency": self.default_currency,
            "exchange_rates": dict(self.exchange_rates),
        }

    @classmethod
    def from_dict(cls, config_dict: Mapping[str, object]) -> "SRUConfig":
        """Create a configuration from a mapping, checking each value's type.

        Unknown keys raise ``ConfigurationError``, including the fields removed in 2.0.
        The caller's mapping is not modified or kept.
        """
        known = {config_field.name for config_field in fields(cls)}
        unknown = sorted(set(config_dict) - known)
        if unknown:
            raise ConfigurationError(
                f"Unknown configuration keys: {', '.join(unknown)}. "
                f"Known: {', '.join(sorted(known))}",
                config_key=unknown[0],
                config_value=config_dict[unknown[0]],
            )
        options: SRUConfigOptions = {}
        if "character_converter" in config_dict:
            options["character_converter"] = _check_character_converter(
                config_dict["character_converter"]
            )
        if "default_currency" in config_dict:
            options["default_currency"] = _check_default_currency(
                config_dict["default_currency"]
            )
        if "exchange_rates" in config_dict:
            options["exchange_rates"] = _check_exchange_rates(
                config_dict["exchange_rates"]
            )
        return cls(**options)

    def copy(self) -> "SRUConfig":
        """Create a copy of the configuration."""
        return SRUConfig.from_dict(self.to_dict())


# Default configuration instance
DEFAULT_CONFIG = SRUConfig()


def get_default_config() -> SRUConfig:
    """Get the default configuration."""
    return DEFAULT_CONFIG.copy()


class SRUConfigOptions(TypedDict, total=False):
    """Keyword arguments ``create_config`` accepts: the fields of ``SRUConfig``."""

    character_converter: str
    default_currency: str
    exchange_rates: dict[str, float]


def create_config(**kwargs: Unpack[SRUConfigOptions]) -> SRUConfig:
    """Create a configuration (see ``SRUConfig.from_dict``)."""
    return SRUConfig.from_dict(dict(kwargs))
