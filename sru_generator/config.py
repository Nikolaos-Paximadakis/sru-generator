"""
Configuration management for SRU Generator package.
"""

import math
import warnings
from collections.abc import Callable
from dataclasses import MISSING, dataclass, field, fields
from enum import Enum
from typing import Any, TypedDict, TypeGuard, Unpack

from .character_converters import CONVERTER_NAMES, load_character_converter
from .exceptions import ConfigurationError
from .models import CharacterConverter

#: Upper bound accepted for ``decimal_places``.
MAX_DECIMAL_PLACES = 10

#: Fields nothing in the package reads. Setting one to a non-default value warns; they
#: will be removed in 2.0. (The K4 rounding rule, validation and file encoding are fixed
#: by Skatteverket's rules, and currency is never converted automatically.)
NO_EFFECT_FIELDS = frozenset(
    {
        "validation_level",
        "strict_validation",
        "rounding_mode",
        "decimal_places",
        "output_format",
        "encoding",
        "line_ending",
        "auto_convert_currency",
        "batch_size",
        "enable_caching",
        "cache_size",
        "log_level",
        "log_file",
        "custom_validators",
        "custom_formatters",
    }
)


def _is_object_dict(value: object) -> TypeGuard[dict[object, object]]:
    return isinstance(value, dict)


def _is_rate_table(value: object) -> bool:
    """A dict of 'FROM_TO' strings to positive numbers (bools excluded)."""
    if not _is_object_dict(value):
        return False
    return all(
        isinstance(key, str)
        and isinstance(rate, int | float)
        and not isinstance(rate, bool)
        and math.isfinite(rate)
        and rate > 0
        for key, rate in value.items()
    )


def _is_currency_code(value: object) -> bool:
    return isinstance(value, str)


def _is_known_converter(value: object) -> bool:
    return isinstance(value, str) and value in CONVERTER_NAMES


class RoundingMode(Enum):
    """Rounding modes for monetary calculations."""

    HALF_EVEN = "half_even"
    HALF_UP = "half_up"
    HALF_DOWN = "half_down"
    ROUND_UP = "round_up"
    ROUND_DOWN = "round_down"


class ValidationLevel(Enum):
    """Validation levels for data processing."""

    NONE = "none"
    BASIC = "basic"
    STRICT = "strict"


@dataclass
class SRUConfig:
    """
    Configuration class for SRU Generator.

    This class provides a centralized way to configure all aspects
    of SRU file generation including validation, formatting, and processing options.
    """

    # Character conversion settings
    character_converter: str = "none"

    # Validation settings
    validation_level: ValidationLevel = ValidationLevel.BASIC
    strict_validation: bool = False

    # Formatting settings
    rounding_mode: RoundingMode = RoundingMode.HALF_EVEN
    decimal_places: int = 0  # For monetary values

    # File settings
    output_format: str = "sru"
    encoding: str = "iso-8859-1"
    line_ending: str = "\n"

    # Currency settings
    default_currency: str = "SEK"
    auto_convert_currency: bool = False  # no effect: nothing converts automatically
    exchange_rates: dict[str, float] = field(default_factory=dict[str, float])

    # Processing settings
    batch_size: int = 1000
    enable_caching: bool = True
    cache_size: int = 100

    # Logging settings
    log_level: str = "INFO"
    log_file: str | None = None

    # Advanced settings
    custom_validators: dict[str, Callable[..., object]] = field(
        default_factory=dict[str, Callable[..., object]]
    )
    custom_formatters: dict[str, Callable[..., object]] = field(
        default_factory=dict[str, Callable[..., object]]
    )

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        try:
            self._validate_config()
        except (TypeError, AttributeError) as e:  # e.g. log_level=[] or batch_size="9"
            raise ConfigurationError(f"Invalid configuration: {e}") from e
        self._warn_about_fields_without_effect()

    def _warn_about_fields_without_effect(self) -> None:
        for config_field in fields(self):
            if config_field.name not in NO_EFFECT_FIELDS:
                continue
            if config_field.default is not MISSING:
                default: object = config_field.default
            elif config_field.default_factory is not MISSING:
                default = config_field.default_factory()
            else:  # every SRUConfig field has a default
                continue
            if getattr(self, config_field.name) != default:
                warnings.warn(
                    f"SRUConfig.{config_field.name} has no effect and will be removed "
                    "in 2.0",
                    DeprecationWarning,
                    stacklevel=4,
                )

    def _validate_config(self) -> None:
        """Validate configuration values."""
        # The helpers take object: from_dict passes untyped values, so the declared
        # field types are what is being checked here, not something to assume.
        if not _is_known_converter(self.character_converter):
            available = ", ".join(CONVERTER_NAMES)
            raise ConfigurationError(
                f"Invalid character_converter '{self.character_converter}'. "
                f"Available options: {available}",
                config_key="character_converter",
                config_value=self.character_converter,
            )

        # The fields that do something are checked here, so a wrong type fails now with
        # a ConfigurationError rather than later with a raw TypeError.
        if not _is_currency_code(self.default_currency):
            raise ConfigurationError(
                "default_currency must be a currency code string",
                config_key="default_currency",
                config_value=self.default_currency,
            )
        if not _is_rate_table(self.exchange_rates):
            raise ConfigurationError(
                "exchange_rates must map 'FROM_TO' strings to positive finite numbers",
                config_key="exchange_rates",
                config_value=self.exchange_rates,
            )

        # Validate decimal places
        if not 0 <= self.decimal_places <= MAX_DECIMAL_PLACES:
            raise ConfigurationError(
                f"decimal_places must be between 0 and 10, got {self.decimal_places}",
                config_key="decimal_places",
                config_value=self.decimal_places,
            )

        # Validate batch size
        if self.batch_size <= 0:
            raise ConfigurationError(
                f"batch_size must be positive, got {self.batch_size}",
                config_key="batch_size",
                config_value=self.batch_size,
            )

        # Validate cache size
        if self.cache_size <= 0:
            raise ConfigurationError(
                f"cache_size must be positive, got {self.cache_size}",
                config_key="cache_size",
                config_value=self.cache_size,
            )

        # Validate log level
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level.upper() not in valid_log_levels:
            raise ConfigurationError(
                f"Invalid log_level '{self.log_level}'. "
                f"Available options: {', '.join(valid_log_levels)}",
                config_key="log_level",
                config_value=self.log_level,
            )

    def get_character_converter(self) -> CharacterConverter:
        """The converter for ``character_converter`` (see ``load_character_converter``).

        Uses text-converters when installed; otherwise the bundled copy, with a
        ``DeprecationWarning``.
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
        result: dict[str, object] = {}
        for key, value in self.__dict__.items():
            if isinstance(value, Enum):
                result[key] = value.value
            elif isinstance(value, dict):
                result[key] = value.copy()
            else:
                result[key] = value
        return result

    @classmethod
    # Any: a deserialisation boundary. The values go to the dataclass constructor;
    # __post_init__ checks the fields that have an effect (character_converter,
    # default_currency, exchange_rates) and the numeric limits. The fields without
    # effect are not type-checked beyond the enum conversion below.
    def from_dict(cls, config_dict: dict[str, Any]) -> "SRUConfig":
        """Create configuration from a dictionary; enum fields may be strings."""
        config_dict = dict(config_dict)  # do not modify the caller's dictionary
        try:
            if "validation_level" in config_dict:
                config_dict["validation_level"] = ValidationLevel(
                    config_dict["validation_level"]
                )
            if "rounding_mode" in config_dict:
                config_dict["rounding_mode"] = RoundingMode(
                    config_dict["rounding_mode"]
                )
            return cls(**config_dict)
        except (ValueError, TypeError) as e:  # bad enum value or unknown field name
            raise ConfigurationError(f"Invalid configuration: {e}") from e

    def copy(self) -> "SRUConfig":
        """Create a copy of the configuration.

        A field without effect warned when it was set; copying does not warn again.
        """
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            return SRUConfig.from_dict(self.to_dict())


# Default configuration instance
DEFAULT_CONFIG = SRUConfig()


def get_default_config() -> SRUConfig:
    """Get the default configuration."""
    return DEFAULT_CONFIG.copy()


class SRUConfigOptions(TypedDict, total=False):
    """Keyword arguments ``create_config`` accepts: the fields of ``SRUConfig``."""

    character_converter: str
    validation_level: ValidationLevel | str
    strict_validation: bool
    rounding_mode: RoundingMode | str
    decimal_places: int
    output_format: str
    encoding: str
    line_ending: str
    default_currency: str
    auto_convert_currency: bool
    exchange_rates: dict[str, float]
    batch_size: int
    enable_caching: bool
    cache_size: int
    log_level: str
    log_file: str | None
    custom_validators: dict[str, Callable[..., object]]
    custom_formatters: dict[str, Callable[..., object]]


def create_config(**kwargs: Unpack[SRUConfigOptions]) -> SRUConfig:
    """Create a configuration; enum fields may be strings (e.g. "strict")."""
    return SRUConfig.from_dict(dict(kwargs))
