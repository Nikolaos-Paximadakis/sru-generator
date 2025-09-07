"""
Configuration management for SRU Generator package.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional

from .exceptions import ConfigurationError


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
    encoding: str = "utf-8"
    line_ending: str = "\n"

    # Currency settings
    default_currency: str = "SEK"
    auto_convert_currency: bool = True
    exchange_rates: Dict[str, float] = field(default_factory=dict)

    # Processing settings
    batch_size: int = 1000
    enable_caching: bool = True
    cache_size: int = 100

    # Logging settings
    log_level: str = "INFO"
    log_file: Optional[str] = None

    # Advanced settings
    custom_validators: Dict[str, Callable] = field(default_factory=dict)
    custom_formatters: Dict[str, Callable] = field(default_factory=dict)

    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate_config()

    def _validate_config(self):
        """Validate configuration values."""
        # Validate character converter
        from .character_converters import CHARACTER_CONVERTERS

        if self.character_converter not in CHARACTER_CONVERTERS:
            available = ", ".join(CHARACTER_CONVERTERS.keys())
            raise ConfigurationError(
                f"Invalid character_converter '{self.character_converter}'. "
                f"Available options: {available}",
                config_key="character_converter",
                config_value=self.character_converter,
            )

        # Validate decimal places
        if self.decimal_places < 0 or self.decimal_places > 10:
            raise ConfigurationError(
                f"decimal_places must be between 0 and 10, got "
                f"{self.decimal_places}",
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

    def get_character_converter(self):
        """Get the character converter function."""
        from .character_converters import get_character_converter

        return get_character_converter(self.character_converter)

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
        if (
            from_currency != self.default_currency
            and to_currency != self.default_currency
        ):
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

    def set_exchange_rate(self, from_currency: str, to_currency: str, rate: float):
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

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, Enum):
                result[key] = value.value
            elif isinstance(value, dict):
                result[key] = value.copy()
            else:
                result[key] = value
        return result

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "SRUConfig":
        """Create configuration from dictionary."""
        # Convert string values back to enums
        if "validation_level" in config_dict:
            config_dict["validation_level"] = ValidationLevel(
                config_dict["validation_level"]
            )
        if "rounding_mode" in config_dict:
            config_dict["rounding_mode"] = RoundingMode(config_dict["rounding_mode"])

        return cls(**config_dict)

    def copy(self) -> "SRUConfig":
        """Create a copy of the configuration."""
        return SRUConfig.from_dict(self.to_dict())


# Default configuration instance
DEFAULT_CONFIG = SRUConfig()


def get_default_config() -> SRUConfig:
    """Get the default configuration."""
    return DEFAULT_CONFIG.copy()


def create_config(**kwargs) -> SRUConfig:
    """Create a new configuration with custom settings."""
    return SRUConfig(**kwargs)
