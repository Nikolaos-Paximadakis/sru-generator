"""
Custom exceptions for SRU Generator package.
"""


class SRUGeneratorError(Exception):
    """Base exception for all SRU Generator errors."""

    pass


class ValidationError(SRUGeneratorError):
    """Raised when data validation fails."""

    def __init__(self, message: str, field: str = None, value: any = None):
        super().__init__(message)
        self.field = field
        self.value = value


class DataFormatError(SRUGeneratorError):
    """Raised when data format is invalid."""

    def __init__(
        self, message: str, expected_format: str = None, actual_format: str = None
    ):
        super().__init__(message)
        self.expected_format = expected_format
        self.actual_format = actual_format


class BusinessRuleError(SRUGeneratorError):
    """Raised when business rules are violated."""

    def __init__(self, message: str, rule: str = None, context: dict = None):
        super().__init__(message)
        self.rule = rule
        self.context = context or {}


class CurrencyError(SRUGeneratorError):
    """Raised when currency operations fail."""

    def __init__(self, message: str, currency: str = None, exchange_rate: float = None):
        super().__init__(message)
        self.currency = currency
        self.exchange_rate = exchange_rate


class ConfigurationError(SRUGeneratorError):
    """Raised when configuration is invalid."""

    def __init__(self, message: str, config_key: str = None, config_value: any = None):
        super().__init__(message)
        self.config_key = config_key
        self.config_value = config_value


class FileOperationError(SRUGeneratorError):
    """Raised when file operations fail."""

    def __init__(self, message: str, file_path: str = None, operation: str = None):
        super().__init__(message)
        self.file_path = file_path
        self.operation = operation
