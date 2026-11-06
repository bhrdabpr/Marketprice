"""Validated contracts. Monetary and rate inputs never default to zero."""

from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

D = Decimal
Money = Annotated[Decimal, Field(ge=0, le=D("1e18"), allow_inf_nan=False)]
Rate = Annotated[Decimal, Field(ge=0, le=1, allow_inf_nan=False)]
Margin = Annotated[Decimal, Field(ge=0, lt=1, allow_inf_nan=False)]
CURRENCIES = {
    "USD": 2,
    "EUR": 2,
    "GBP": 2,
    "AED": 2,
    "SAR": 2,
    "CAD": 2,
    "AUD": 2,
    "JPY": 0,
    "KRW": 0,
    "IRR": 0,
    "TOMAN": 0,
    "KWD": 3,
    "BHD": 3,
    "CHF": 2,
}
FIXED_FIELDS = (
    "shipping",
    "fulfillment",
    "packaging",
    "warehouse",
    "overhead",
    "advertising",
    "other_fixed",
    "expected_return_cost",
    "marketplace_extra",
    "inbound_freight",
    "customs_duty",
    "insurance",
    "inspection",
    "financing",
    "warranty",
    "customer_support",
    "software",
    "labor",
    "utilities",
    "expected_loss",
    "currency_conversion",
    "compliance",
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Product(StrictModel):
    sku: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=512)
    marketplace: str
    category: str
    currency: str
    current_price: Money
    purchase_cost: Money
    inbound_freight: Money = D(0)
    customs_duty: Money = D(0)
    insurance: Money = D(0)
    inspection: Money = D(0)
    financing: Money = D(0)
    warranty: Money = D(0)
    customer_support: Money = D(0)
    software: Money = D(0)
    labor: Money = D(0)
    utilities: Money = D(0)
    expected_loss: Money = D(0)
    currency_conversion: Money = D(0)
    compliance: Money = D(0)
    shipping: Money
    fulfillment: Money
    packaging: Money
    warehouse: Money
    overhead: Money
    advertising: Money
    other_fixed: Money
    expected_return_cost: Money
    marketplace_extra: Money
    commission_rate: Rate
    commission_fixed: Money
    payment_rate: Rate
    payment_fixed: Money
    other_rate: Rate
    transaction_tax_rate: Rate
    tax_rate: Rate
    tax_mode: Literal["inclusive", "exclusive"]
    input_tax_credit: Money
    fee_tax_rate: Rate
    fee_tax_recoverable: bool
    target_margin: Margin
    minimum_margin: Margin
    campaign_margin: Margin
    max_discount: Rate
    increment: Decimal = Field(gt=0, le=D("1e18"), allow_inf_nan=False)
    recommendation_rule: Literal["floor", "match_competitor", "keep_current"]
    quantity: int | None = Field(default=None, ge=0)
    competitor_price: Money | None = None
    price_ceiling: Money | None = None
    price_minimum: Money | None = None

    @model_validator(mode="after")
    def consistency(self) -> "Product":
        if self.currency not in CURRENCIES:
            raise ValueError("INVALID_CURRENCY: unsupported currency; IRR and TOMAN are distinct")
        unit = D(10) ** -CURRENCIES[self.currency]
        if self.increment % unit:
            raise ValueError("increment must be a multiple of currency minor unit")
        if self.current_price % unit:
            raise ValueError("current_price has unsupported currency precision")
        if self.input_tax_credit > self.purchase_cost:
            raise ValueError("input_tax_credit cannot exceed tax-inclusive purchase_cost")
        if self.recommendation_rule == "match_competitor" and self.competitor_price is None:
            raise ValueError("competitor_price required for match_competitor")
        if self.target_margin < self.minimum_margin:
            raise ValueError("target_margin must meet minimum_margin")
        return self


class Tier(StrictModel):
    up_to: Money | None
    rate: Rate


class CappedCharge(StrictModel):
    rate: Rate
    maximum: Money
    base: Literal["net", "gross", "list", "settlement"]
    taxable: bool


class CategoryCharges(StrictModel):
    shipping: CappedCharge | None = None
    processing: CappedCharge | None = None


class Profile(StrictModel):
    id: str
    version: str
    effective_date: str
    source: str
    official: Literal[False] = False
    commission_base: Literal["net", "gross", "list", "settlement"]
    payment_base: Literal["net", "gross", "list", "settlement"]
    other_base: Literal["net", "gross", "list", "settlement"]
    subsidy_taxable: bool
    tiers: tuple[Tier, ...] = ()
    category_tiers: dict[str, tuple[Tier, ...]] = Field(default_factory=dict)
    category_charges: dict[str, CategoryCharges] = Field(default_factory=dict)
    require_category_charges: bool = False
    campaign_commission_rate: Rate | None = None
    campaign_fixed_fee: Money
    required_fields: tuple[str, ...] = ()
    description: str

    @model_validator(mode="after")
    def valid_tiers(self) -> "Profile":
        for tiers in [self.tiers, *self.category_tiers.values()]:
            if not tiers:
                continue
            last = D(0)
            for i, tier in enumerate(tiers):
                if tier.up_to is None:
                    if i != len(tiers) - 1:
                        raise ValueError("unbounded tier must be last")
                elif tier.up_to <= last:
                    raise ValueError("tier boundaries must strictly increase")
                else:
                    last = tier.up_to
            if tiers[-1].up_to is not None:
                raise ValueError("last tier must be unbounded")
        if self.campaign_commission_rate is not None and (self.tiers or self.category_tiers):
            raise ValueError("campaign flat override conflicts with tiers")
        if any(x not in Product.model_fields for x in self.required_fields):
            raise ValueError("unknown required field")
        return self


class Issue(StrictModel):
    sku: str
    row: int
    field: str
    code: str
    explanation: str
    correction: str
