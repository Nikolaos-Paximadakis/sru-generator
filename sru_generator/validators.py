"""
Enhanced validation system for SRU Generator package.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional, Callable

from .exceptions import ValidationError, BusinessRuleError, DataFormatError
from .currency import is_supported_currency, SUPPORTED_CURRENCIES


class Validator:
    """Base validator class."""

    def __init__(self, field_name: str, required: bool = True):
        self.field_name = field_name
        self.required = required

    def validate(self, value: Any, context: Dict[str, Any] = None) -> Any:
        """Validate a value and return the cleaned value."""
        if value is None:
            if self.required:
                raise ValidationError(
                    f"Field '{self.field_name}' is required",
                    field=self.field_name,
                    value=value
                )
            return None

        return self._validate_value(value, context or {})

    def _validate_value(self, value: Any, context: Dict[str, Any]) -> Any:
        """Override in subclasses to implement specific validation."""
        return value


class StringValidator(Validator):
    """Validates string values."""

    def __init__(
            self,
            field_name: str,
            max_length: Optional[int] = None,
            min_length: Optional[int] = None,
            pattern: Optional[str] = None,
            required: bool = True):
        super().__init__(field_name, required)
        self.max_length = max_length
        self.min_length = min_length
        self.pattern = pattern

    def _validate_value(self, value: Any, context: Dict[str, Any]) -> str:
        if not isinstance(value, str):
            raise ValidationError(
                f"Field '{self.field_name}' must be a string, got "
                f"{type(value).__name__}",
                field=self.field_name,
                value=value)

        if self.min_length and len(value) < self.min_length:
            raise ValidationError(
                f"Field '{
                    self.field_name}' must be at least {
                    self.min_length} characters",
                field=self.field_name,
                value=value)

        if self.max_length and len(value) > self.max_length:
            raise ValidationError(
                f"Field '{
                    self.field_name}' must be at most {
                    self.max_length} characters",
                field=self.field_name,
                value=value)

        if self.pattern:
            import re
            if not re.match(self.pattern, value):
                raise ValidationError(
                    f"Field '{
                        self.field_name}' does not match required pattern",
                    field=self.field_name,
                    value=value)

        return value.strip()


class IntegerValidator(Validator):
    """Validates integer values."""

    def __init__(self, field_name: str, min_value: Optional[int] = None,
                 max_value: Optional[int] = None, required: bool = True):
        super().__init__(field_name, required)
        self.min_value = min_value
        self.max_value = max_value

    def _validate_value(self, value: Any, context: Dict[str, Any]) -> int:
        if isinstance(value, str):
            try:
                value = int(value)
            except ValueError:
                raise ValidationError(
                    f"Field '{self.field_name}' must be a valid integer",
                    field=self.field_name,
                    value=value
                )

        if not isinstance(value, int):
            raise ValidationError(
                f"Field '{
                    self.field_name}' must be an integer, got {
                    type(value).__name__}",
                field=self.field_name,
                value=value)

        if self.min_value is not None and value < self.min_value:
            raise ValidationError(
                f"Field '{self.field_name}' must be at least {self.min_value}",
                field=self.field_name,
                value=value
            )

        if self.max_value is not None and value > self.max_value:
            raise ValidationError(
                f"Field '{self.field_name}' must be at most {self.max_value}",
                field=self.field_name,
                value=value
            )

        return value


class DecimalValidator(Validator):
    """Validates decimal values."""

    def __init__(self, field_name: str, min_value: Optional[Decimal] = None,
                 max_value: Optional[Decimal] = None, required: bool = True):
        super().__init__(field_name, required)
        self.min_value = min_value
        self.max_value = max_value

    def _validate_value(self, value: Any, context: Dict[str, Any]) -> Decimal:
        if isinstance(value, str):
            try:
                value = Decimal(value)
            except Exception:
                raise ValidationError(
                    f"Field '{
                        self.field_name}' must be a valid decimal number",
                    field=self.field_name,
                    value=value)

        if isinstance(value, (int, float)):
            value = Decimal(str(value))

        if not isinstance(value, Decimal):
            raise ValidationError(
                f"Field '{
                    self.field_name}' must be a decimal number, got {
                    type(value).__name__}",
                field=self.field_name,
                value=value)

        if self.min_value is not None and value < self.min_value:
            raise ValidationError(
                f"Field '{self.field_name}' must be at least {self.min_value}",
                field=self.field_name,
                value=value
            )

        if self.max_value is not None and value > self.max_value:
            raise ValidationError(
                f"Field '{self.field_name}' must be at most {self.max_value}",
                field=self.field_name,
                value=value
            )

        return value


class CurrencyValidator(Validator):
    """Validates currency codes."""

    def _validate_value(self, value: Any, context: Dict[str, Any]) -> str:
        if not isinstance(value, str):
            raise ValidationError(
                f"Field '{self.field_name}' must be a string",
                field=self.field_name,
                value=value
            )

        currency = value.upper()
        if not is_supported_currency(currency):
            supported = ", ".join(sorted(SUPPORTED_CURRENCIES.keys()))
            raise ValidationError(
                f"Field '{self.field_name}' must be a supported currency. "
                f"Supported currencies: {supported}",
                field=self.field_name,
                value=value
            )

        return currency


class TradeDataValidator:
    """Validates trade data according to SRU specifications."""

    def __init__(self, config=None):
        self.config = config
        self.validators = self._create_validators()

    def _create_validators(self) -> Dict[str, Validator]:
        """Create validators for trade data fields."""
        return {
            "quantity": IntegerValidator(
                "quantity",
                min_value=0,
                max_value=999999999999
            ),
            "stock": StringValidator(
                "stock",
                max_length=80,
                min_length=1
            ),
            "net value": DecimalValidator(
                "net value",
                min_value=Decimal("0"),
                max_value=Decimal("999999999999")
            ),
            "total net value of purchase": DecimalValidator(
                "total net value of purchase",
                min_value=Decimal("0"),
                max_value=Decimal("999999999999")
            ),
            "profit/loss": DecimalValidator(
                "profit/loss",
                required=False
            ),
            "currency": CurrencyValidator("currency", required=False),
            "exchange_rate": DecimalValidator(
                "exchange_rate",
                min_value=Decimal("0.000001"),
                max_value=Decimal("1000000"),
                required=False
            )
        }

    def validate_trade_item(
            self, trade_item: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a single trade item."""
        if not isinstance(trade_item, dict):
            raise DataFormatError(
                "Trade item must be a dictionary",
                expected_format="dict",
                actual_format=type(trade_item).__name__
            )

        validated_item = {}

        # Validate each field
        for field_name, validator in self.validators.items():
            value = trade_item.get(field_name)
            validated_item[field_name] = validator.validate(value)

        # Business rule validations
        self._validate_business_rules(validated_item)

        return validated_item

    def _validate_business_rules(self, trade_item: Dict[str, Any]):
        """Validate business rules for trade data."""
        # Rule 1: Profit/Loss should equal net value - cost basis
        net_value = trade_item.get("net value")
        cost_basis = trade_item.get("total net value of purchase")
        profit_loss = trade_item.get("profit/loss")

        if net_value is not None and cost_basis is not None:
            calculated_profit_loss = net_value - cost_basis

            if profit_loss is not None:
                # Allow small rounding differences
                difference = abs(calculated_profit_loss - profit_loss)
                if difference > Decimal("1"):
                    raise BusinessRuleError(
                        f"Profit/loss mismatch: calculated={calculated_profit_loss}, "
                        f"provided={profit_loss}, difference={difference}",
                        rule="profit_loss_calculation",
                        context={
                            "net_value": net_value,
                            "cost_basis": cost_basis,
                            "calculated_profit_loss": calculated_profit_loss,
                            "provided_profit_loss": profit_loss
                        }
                    )
            else:
                # Auto-calculate if not provided
                trade_item["profit/loss"] = calculated_profit_loss

        # Rule 2: Currency validation
        currency = trade_item.get("currency")
        if currency and not is_supported_currency(currency):
            raise BusinessRuleError(
                f"Unsupported currency: {currency}",
                rule="currency_support",
                context={"currency": currency}
            )

    def validate_trade_data(
            self, trade_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate a list of trade items."""
        if not isinstance(trade_data, list):
            raise DataFormatError(
                "Trade data must be a list",
                expected_format="list",
                actual_format=type(trade_data).__name__
            )

        if not trade_data:
            raise ValidationError("Trade data cannot be empty")

        validated_data = []
        for i, trade_item in enumerate(trade_data):
            try:
                validated_item = self.validate_trade_item(trade_item)
                validated_data.append(validated_item)
            except (ValidationError, BusinessRuleError, DataFormatError) as e:
                raise ValidationError(
                    f"Validation failed for trade item {i}: {e}",
                    field=f"trade_data[{i}]",
                    value=trade_item
                ) from e

        return validated_data


class PersonalInfoValidator:
    """Validates personal information for SRU files."""

    def __init__(self):
        self.validators = {
            "personal_number": StringValidator(
                "personal_number",
                pattern=r"^\d{10,12}$",
                required=True
            ),
            "full_name": StringValidator(
                "full_name",
                max_length=100,
                min_length=1,
                required=True
            ),
            "postal_code": StringValidator(
                "postal_code",
                pattern=r"^\d{5}$",
                required=True
            ),
            "city_name": StringValidator(
                "city_name",
                max_length=50,
                min_length=1,
                required=True
            )
        }

    def validate_personal_info(
            self, personal_info: Dict[str, Any]) -> Dict[str, Any]:
        """Validate personal information."""
        if not isinstance(personal_info, dict):
            raise DataFormatError(
                "Personal info must be a dictionary",
                expected_format="dict",
                actual_format=type(personal_info).__name__
            )

        validated_info = {}
        for field_name, validator in self.validators.items():
            value = personal_info.get(field_name)
            validated_info[field_name] = validator.validate(value)

        return validated_info


# Global validator instances
_trade_validator = TradeDataValidator()
_personal_validator = PersonalInfoValidator()


def validate_trade_data(
        trade_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Validate trade data using the global validator."""
    return _trade_validator.validate_trade_data(trade_data)


def validate_personal_info(personal_info: Dict[str, Any]) -> Dict[str, Any]:
    """Validate personal info using the global validator."""
    return _personal_validator.validate_personal_info(personal_info)


def create_custom_validator(field_name: str,
                            validator_func: Callable) -> Validator:
    """Create a custom validator."""
    class CustomValidator(Validator):
        def _validate_value(self, value: Any, context: Dict[str, Any]) -> Any:
            return validator_func(value, context)

    return CustomValidator(field_name)
