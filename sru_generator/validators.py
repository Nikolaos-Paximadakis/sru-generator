"""
Enhanced validation system for SRU Generator package.
"""

import re
from collections.abc import Callable, Mapping, Sequence
from decimal import Decimal
from typing import Generic, NewType, TypeVar

from .amounts import to_decimal
from .currency import SUPPORTED_CURRENCIES, is_supported_currency
from .exceptions import BusinessRuleError, DataFormatError, ValidationError
from .models import PersonalInfo, ValidatedTradeRow

T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)

#: A personnummer that passed ``PersonalNumberValidator`` (12 digits, check digit OK).
PersonalNumber = NewType("PersonalNumber", str)

#: ASCII control characters (line breaks, tabs, DEL): never allowed in SRU text values.
_FIRST_PRINTABLE = 0x20
_DELETE = 0x7F

#: Personnummer in the SRU form: century + date + four digits (YYYYMMDDNNNN).
PERSONAL_NUMBER_LENGTH = 12
#: A hyphen is accepted in front of the last four digits ("-NNNN").
_SUFFIX_WITH_HYPHEN = 5

#: Extra information a validator may use; the built-in validators ignore it.
ValidationContext = Mapping[str, object]


# The public signatures declare Mapping/Sequence, but callers without a type checker can
# pass anything; these take object so the defensive checks are not "always true".
def _is_mapping(value: object) -> bool:
    return isinstance(value, Mapping)


def _is_row_sequence(value: object) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, str | bytes)


class Validator(Generic[T_co]):
    """Base validator: checks one field and returns its cleaned value (a ``T_co``)."""

    def __init__(self, field_name: str, required: bool = True) -> None:  # noqa: FBT001, FBT002 -- public API
        self.field_name = field_name
        self.required = required

    def validate(
        self, value: object, context: ValidationContext | None = None
    ) -> T_co | None:
        """Return the cleaned value, or None if the field is optional and absent."""
        if value is None:
            if self.required:
                raise ValidationError(
                    f"Field '{self.field_name}' is required",
                    field=self.field_name,
                    value=value,
                )
            return None

        return self._validate_value(value, context or {})

    def _validate_value(self, value: object, context: ValidationContext) -> T_co:
        """Override in subclasses to implement specific validation."""
        raise NotImplementedError


class StringValidator(Validator[str]):
    """Validates string values."""

    def __init__(
        self,
        field_name: str,
        max_length: int | None = None,
        min_length: int | None = None,
        pattern: str | None = None,
        required: bool = True,  # noqa: FBT001, FBT002 -- public API
        *,
        sru_text: bool = False,
    ) -> None:
        super().__init__(field_name, required)
        self.max_length = max_length
        self.min_length = min_length
        self.pattern = pattern
        # A value written into an SRU file: Skatteverket's file description forbids
        # "#" in string values, and a line break would end the record early.
        self.sru_text = sru_text

    def _validate_value(self, value: object, context: ValidationContext) -> str:
        if not isinstance(value, str):
            raise ValidationError(
                f"Field '{self.field_name}' must be a string, got "
                f"{type(value).__name__}",
                field=self.field_name,
                value=value,
            )
        # Check what will be written: the stripped value. Checking before stripping let
        # "   " pass min_length=1 and come out empty.
        value = value.strip()

        if self.min_length and len(value) < self.min_length:
            raise ValidationError(
                f"Field '{self.field_name}' must be at least "
                f"{self.min_length} characters",
                field=self.field_name,
                value=value,
            )

        if self.max_length and len(value) > self.max_length:
            raise ValidationError(
                f"Field '{self.field_name}' must be at most "
                f"{self.max_length} characters",
                field=self.field_name,
                value=value,
            )

        if self.sru_text:
            if "#" in value:
                raise ValidationError(
                    f"Field '{self.field_name}' may not contain '#' "
                    "(not allowed in SRU text values)",
                    field=self.field_name,
                    value=value,
                )
            if any(
                ord(char) < _FIRST_PRINTABLE or ord(char) == _DELETE for char in value
            ):
                raise ValidationError(
                    f"Field '{self.field_name}' may not contain line breaks or "
                    "other control characters",
                    field=self.field_name,
                    value=value,
                )

        if self.pattern:
            if not re.match(self.pattern, value):
                raise ValidationError(
                    f"Field '{self.field_name}' does not match required pattern",
                    field=self.field_name,
                    value=value,
                )

        return value


def luhn_check_digit_ok(digits: str) -> bool:
    """Luhn (mod 10) check of Swedish person-, samordnings- and organisationsnummer.

    Applied to the last ten digits, so it works on the 12-digit form too.
    """
    total = 0
    for position, char in enumerate(digits[-10:]):
        product = int(char) * (2 if position % 2 == 0 else 1)
        total += product // 10 + product % 10
    return total % 10 == 0


class PersonalNumberValidator(Validator[PersonalNumber]):
    """Personnummer (or samordnings-/organisationsnummer) in the 12-digit SRU form.

    Skatteverket's file description requires the century and digits only, for example
    811218-9876 written as 198112189876, and a correct check digit. A hyphen between
    the date and the last four digits is accepted and removed. Ten-digit numbers are
    refused rather than guessed: the century cannot be known from them reliably.
    """

    def _validate_value(
        self, value: object, context: ValidationContext
    ) -> PersonalNumber:
        if not isinstance(value, str):
            raise ValidationError(
                f"Field '{self.field_name}' must be a string, got "
                f"{type(value).__name__}",
                field=self.field_name,
            )
        cleaned = value.strip()
        if len(cleaned) > _SUFFIX_WITH_HYPHEN and cleaned[-_SUFFIX_WITH_HYPHEN] == "-":
            cleaned = cleaned[:-_SUFFIX_WITH_HYPHEN] + cleaned[-4:]
        if not cleaned.isdigit() or not cleaned.isascii():
            raise ValidationError(
                f"Field '{self.field_name}' must contain digits only "
                "(YYYYMMDDNNNN, no '+' or spaces)",
                field=self.field_name,
            )
        if len(cleaned) != PERSONAL_NUMBER_LENGTH:
            raise ValidationError(
                f"Field '{self.field_name}' must be 12 digits including the century, "
                "for example 811218-9876 written as 198112189876",
                field=self.field_name,
            )
        if not luhn_check_digit_ok(cleaned):
            raise ValidationError(
                f"Field '{self.field_name}' has a wrong check digit (last digit); "
                "check for a typo",
                field=self.field_name,
            )
        return PersonalNumber(cleaned)


class IntegerValidator(Validator[int]):
    """Validates integer values."""

    def __init__(
        self,
        field_name: str,
        min_value: int | None = None,
        max_value: int | None = None,
        required: bool = True,  # noqa: FBT001, FBT002 -- public API
    ) -> None:
        super().__init__(field_name, required)
        self.min_value = min_value
        self.max_value = max_value

    def _validate_value(self, value: object, context: ValidationContext) -> int:
        if isinstance(value, bool):  # bool is an int subclass; True is not a quantity
            raise ValidationError(
                f"Field '{self.field_name}' must be an integer, got bool",
                field=self.field_name,
                value=value,
            )
        if isinstance(value, str):
            try:
                value = int(value)
            except ValueError:
                raise ValidationError(
                    f"Field '{self.field_name}' must be a valid integer",
                    field=self.field_name,
                    value=value,
                ) from None

        if not isinstance(value, int):
            raise ValidationError(
                f"Field '{self.field_name}' must be an integer, "
                f"got {type(value).__name__}",
                field=self.field_name,
                value=value,
            )

        if self.min_value is not None and value < self.min_value:
            raise ValidationError(
                f"Field '{self.field_name}' must be at least {self.min_value}",
                field=self.field_name,
                value=value,
            )

        if self.max_value is not None and value > self.max_value:
            raise ValidationError(
                f"Field '{self.field_name}' must be at most {self.max_value}",
                field=self.field_name,
                value=value,
            )

        return value


class DecimalValidator(Validator[Decimal]):
    """Validates decimal values."""

    def __init__(
        self,
        field_name: str,
        min_value: Decimal | None = None,
        max_value: Decimal | None = None,
        required: bool = True,  # noqa: FBT001, FBT002 -- public API
    ) -> None:
        super().__init__(field_name, required)
        self.min_value = min_value
        self.max_value = max_value

    def _validate_value(self, value: object, context: ValidationContext) -> Decimal:
        if isinstance(value, bool):  # bool is an int subclass; True is not an amount
            raise ValidationError(
                f"Field '{self.field_name}' must be a decimal number, got bool",
                field=self.field_name,
                value=value,
            )
        if isinstance(value, str):
            try:
                value = Decimal(value)
            except Exception:
                raise ValidationError(
                    f"Field '{self.field_name}' must be a valid decimal number",
                    field=self.field_name,
                    value=value,
                ) from None

        if isinstance(value, (int, float)):
            value = to_decimal(value)  # drops a float's binary noise

        if not isinstance(value, Decimal):
            raise ValidationError(
                f"Field '{self.field_name}' must be a decimal number, "
                f"got {type(value).__name__}",
                field=self.field_name,
                value=value,
            )

        # Before any comparison: comparing NaN raises decimal.InvalidOperation, which
        # escaped as a non-ValidationError.
        if not value.is_finite():
            raise ValidationError(
                f"Field '{self.field_name}' must be a finite number",
                field=self.field_name,
                value=value,
            )

        if self.min_value is not None and value < self.min_value:
            raise ValidationError(
                f"Field '{self.field_name}' must be at least {self.min_value}",
                field=self.field_name,
                value=value,
            )

        if self.max_value is not None and value > self.max_value:
            raise ValidationError(
                f"Field '{self.field_name}' must be at most {self.max_value}",
                field=self.field_name,
                value=value,
            )

        return value


class CurrencyValidator(Validator[str]):
    """Validates currency codes."""

    def _validate_value(self, value: object, context: ValidationContext) -> str:
        if not isinstance(value, str):
            raise ValidationError(
                f"Field '{self.field_name}' must be a string",
                field=self.field_name,
                value=value,
            )

        currency = value.upper()
        if not is_supported_currency(currency):
            supported = ", ".join(sorted(SUPPORTED_CURRENCIES.keys()))
            raise ValidationError(
                f"Field '{self.field_name}' must be a supported currency. "
                f"Supported currencies: {supported}",
                field=self.field_name,
                value=value,
            )

        return currency


class TradeDataValidator:
    """Validates trade data according to SRU specifications."""

    def __init__(self, config: object = None) -> None:
        self.config = config  # unused; kept for API compatibility
        self.validators = self._create_validators()

    def _create_validators(self) -> dict[str, Validator[object]]:
        """Create validators for trade data fields."""
        return {
            # Fractional quantities (fractional shares, crypto) are accepted; they are
            # rounded up to a whole antal when written (see `round_k4_quantity`).
            "quantity": DecimalValidator(
                "quantity", min_value=Decimal("0"), max_value=Decimal("999999999999")
            ),
            "stock": StringValidator(
                "stock", max_length=80, min_length=1, sru_text=True
            ),
            "net value": DecimalValidator(
                "net value", min_value=Decimal("0"), max_value=Decimal("999999999999")
            ),
            "total net value of purchase": DecimalValidator(
                "total net value of purchase",
                min_value=Decimal("0"),
                max_value=Decimal("999999999999"),
            ),
            "profit/loss": DecimalValidator("profit/loss", required=False),
            "currency": CurrencyValidator("currency", required=False),
            "exchange_rate": DecimalValidator(
                "exchange_rate",
                min_value=Decimal("0.000001"),
                max_value=Decimal("1000000"),
                required=False,
            ),
        }

    def validate_trade_item(
        self, trade_item: Mapping[str, object]
    ) -> ValidatedTradeRow:
        """Validate a single trade item."""
        if not _is_mapping(trade_item):
            raise DataFormatError(
                "Trade item must be a dictionary (mapping)",
                expected_format="mapping",
                actual_format=type(trade_item).__name__,
            )

        cleaned = {
            field_name: validator.validate(trade_item.get(field_name))
            for field_name, validator in self.validators.items()
        }
        validated_item: ValidatedTradeRow = {
            "quantity": _expect(cleaned["quantity"], Decimal, "quantity"),
            "stock": _expect(cleaned["stock"], str, "stock"),
            "net value": _expect(cleaned["net value"], Decimal, "net value"),
            "total net value of purchase": _expect(
                cleaned["total net value of purchase"],
                Decimal,
                "total net value of purchase",
            ),
            "profit/loss": _optional(cleaned["profit/loss"], Decimal, "profit/loss"),
            "currency": _optional(cleaned["currency"], str, "currency"),
            "exchange_rate": _optional(
                cleaned["exchange_rate"], Decimal, "exchange_rate"
            ),
        }

        # Business rule validations
        self._validate_business_rules(validated_item)

        return validated_item

    def _validate_business_rules(self, trade_item: ValidatedTradeRow) -> None:
        """Validate business rules for trade data."""
        # Rule 1: Profit/Loss should equal net value - cost basis
        net_value = trade_item["net value"]
        cost_basis = trade_item["total net value of purchase"]
        profit_loss = trade_item["profit/loss"]

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
                        "provided_profit_loss": profit_loss,
                    },
                )
        else:
            # Auto-calculate if not provided
            trade_item["profit/loss"] = calculated_profit_loss
        # Rule 2: Currency validation
        currency = trade_item["currency"]
        if currency and not is_supported_currency(currency):
            raise BusinessRuleError(
                f"Unsupported currency: {currency}",
                rule="currency_support",
                context={"currency": currency},
            )

    def validate_trade_data(
        self, trade_data: Sequence[Mapping[str, object]]
    ) -> list[ValidatedTradeRow]:
        """Validate a list of trade items."""
        # Any sequence of rows, as annotated, but not a string (also a sequence).
        if not _is_row_sequence(trade_data):
            raise DataFormatError(
                "Trade data must be a list (sequence) of rows",
                expected_format="sequence",
                actual_format=type(trade_data).__name__,
            )

        if not trade_data:
            raise ValidationError("Trade data cannot be empty")

        validated_data: list[ValidatedTradeRow] = []
        for i, trade_item in enumerate(trade_data):
            try:
                validated_item = self.validate_trade_item(trade_item)
                validated_data.append(validated_item)
            except (ValidationError, BusinessRuleError, DataFormatError) as e:
                raise ValidationError(
                    f"Validation failed for trade item {i}: {e}",
                    field=f"trade_data[{i}]",
                    value=trade_item,
                ) from e

        return validated_data


class PersonalInfoValidator:
    """Validates personal information for SRU files."""

    def __init__(self) -> None:
        self.validators: dict[str, Validator[str]] = {
            "personal_number": PersonalNumberValidator("personal_number"),
            "full_name": StringValidator(
                "full_name", max_length=100, min_length=1, required=True, sru_text=True
            ),
            "postal_code": StringValidator(
                "postal_code", pattern=r"^\d{5}$", required=True
            ),
            "city_name": StringValidator(
                "city_name", max_length=50, min_length=1, required=True, sru_text=True
            ),
        }

    def validate_personal_info(
        self, personal_info: Mapping[str, object]
    ) -> PersonalInfo:
        """Validate personal information."""
        if not _is_mapping(personal_info):
            raise DataFormatError(
                "Personal info must be a dictionary (mapping)",
                expected_format="mapping",
                actual_format=type(personal_info).__name__,
            )

        cleaned = {
            field_name: validator.validate(personal_info.get(field_name))
            for field_name, validator in self.validators.items()
        }
        return {
            "personal_number": _expect(
                cleaned["personal_number"], str, "personal_number"
            ),
            "full_name": _expect(cleaned["full_name"], str, "full_name"),
            "postal_code": _expect(cleaned["postal_code"], str, "postal_code"),
            "city_name": _expect(cleaned["city_name"], str, "city_name"),
        }


# Global validator instances
_trade_validator = TradeDataValidator()
_personal_validator = PersonalInfoValidator()


def validate_trade_data(
    trade_data: Sequence[Mapping[str, object]],
) -> list[ValidatedTradeRow]:
    """Validate trade data using the global validator."""
    return _trade_validator.validate_trade_data(trade_data)


def validate_personal_info(personal_info: Mapping[str, object]) -> PersonalInfo:
    """Validate personal info using the global validator."""
    return _personal_validator.validate_personal_info(personal_info)


class FunctionValidator(Validator[T_co]):
    """A validator whose check is a function ``(value, context) -> cleaned value``."""

    def __init__(
        self,
        field_name: str,
        validator_func: Callable[[object, ValidationContext], T_co],
    ) -> None:
        super().__init__(field_name)
        self._validator_func = validator_func

    def _validate_value(self, value: object, context: ValidationContext) -> T_co:
        return self._validator_func(value, context)


def create_custom_validator(
    field_name: str, validator_func: Callable[[object, ValidationContext], T]
) -> Validator[T]:
    """Create a validator from a function ``(value, context) -> cleaned value``."""
    return FunctionValidator(field_name, validator_func)


def _expect(value: object, kind: type[T], field_name: str) -> T:
    """Narrow a required validator result to the type the row promises.

    The built-in validators always return ``kind``; this catches a replaced entry in
    ``validators`` returning something else, or ``None`` for a required field.
    """
    if isinstance(value, kind):
        return value
    raise ValidationError(
        f"Field '{field_name}' must be {kind.__name__}, got {type(value).__name__}",
        field=field_name,
        value=value,
    )


def _optional(value: object, kind: type[T], field_name: str) -> T | None:
    """Like ``_expect`` for an optional field: ``None`` stays ``None``."""
    return None if value is None else _expect(value, kind, field_name)
