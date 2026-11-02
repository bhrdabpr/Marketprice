"""Explicit, sourced conversion only. Never fetches or guesses exchange rates."""

from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal, localcontext

from pydantic import Field, model_validator

from .models import CURRENCIES, StrictModel


class Conversion(StrictModel):
    source_currency: str
    target_currency: str
    rate: Decimal = Field(gt=0, allow_inf_nan=False)
    timestamp: datetime
    source: str = Field(min_length=1)

    @model_validator(mode="after")
    def valid(self):
        if self.source_currency not in CURRENCIES or self.target_currency not in CURRENCIES:
            raise ValueError("INVALID_CURRENCY")
        if self.timestamp.tzinfo is None:
            raise ValueError("timestamp must include timezone")
        return self

    def convert(self, amount: Decimal) -> Decimal:
        if not amount.is_finite() or amount < 0:
            raise ValueError("INVALID_AMOUNT")
        with localcontext() as context:
            context.prec = 50
            return (amount * self.rate).quantize(
                Decimal(10) ** -CURRENCIES[self.target_currency], rounding=ROUND_HALF_UP
            )
