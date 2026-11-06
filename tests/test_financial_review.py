"""Independent rational-arithmetic oracle across tax and fee-base combinations."""

from decimal import Decimal as D
from decimal import localcontext
from fractions import Fraction as F
from itertools import product

import pytest

from marketprice.analysis import seasonal_offers
from marketprice.config import load_profiles
from marketprice.engine import evaluate
from marketprice.samples import sample_row
from marketprice.validation import validate


@pytest.mark.parametrize(
    "mode,base,recoverable,taxable",
    list(
        product(
            ["inclusive", "exclusive"], ["net", "gross", "list", "settlement"], [False, True], [False, True]
        )
    ),
)
def test_ledger_against_rational_oracle(mode, base, recoverable, taxable):
    rule = load_profiles()["generic"].model_copy(
        update={
            "commission_base": base,
            "payment_base": base,
            "other_base": base,
            "subsidy_taxable": taxable,
            "campaign_fixed_fee": D(3),
        }
    )
    p, errors = validate(
        {
            **sample_row(),
            "tax_mode": mode,
            "tax_rate": "20%",
            "commission_rate": "10%",
            "commission_fixed": "2",
            "payment_rate": "3%",
            "payment_fixed": "1",
            "other_rate": "4%",
            "fee_tax_rate": "10%",
            "fee_tax_recoverable": recoverable,
            "input_tax_credit": "5",
            "transaction_tax_rate": "2%",
        },
        2,
        {"generic": rule},
    )
    assert not errors
    # Independent hand-specified costs: purchase70-credit5 + shipping8+other2+campaign3.
    net = F(100) if mode == "inclusive" else F(120)
    gross = F(120) if mode == "inclusive" else F(144)
    subsidy_net = F(10) if taxable and mode == "inclusive" else F(12)
    subsidy_tax = (F(2) if mode == "inclusive" else F(12, 5)) if taxable else F(0)
    revenue = net + subsidy_net
    bases = {"net": net, "gross": gross, "list": F(150), "settlement": gross + subsidy_net + subsidy_tax}
    commission = bases[base] / 10 + 2
    payment = bases[base] * F(3, 100) + 1
    other = bases[base] / 25
    fee_tax = (commission + payment) / 10
    cost = 65 + 13 + commission + payment + other + (0 if recoverable else fee_tax) + revenue / 50
    ledger = evaluate(p, rule, D(120), subsidy=D(12), list_price=D(150), campaign=True)
    expected = {
        "revenue": revenue,
        "total_cost": cost,
        "profit": revenue - cost,
        "tax_collected": gross - net + subsidy_tax,
        "margin": (revenue - cost) / revenue,
    }
    with localcontext() as ctx:
        ctx.prec = 60
        for key, value in expected.items():
            exact = D(value.numerator) / D(value.denominator)
            assert abs(getattr(ledger, key) - exact) < D("1e-45"), key


def test_nonpositive_baseline_has_no_seasonal_sales_multiplier():
    rule = load_profiles()["generic"].model_copy(update={"campaign_commission_rate": D(0)})
    p, errors = validate(
        {
            **sample_row(),
            "purchase_cost": "70",
            "current_price": "100",
            "shipping": "0",
            "other_fixed": "0",
            "payment_rate": "0",
            "commission_rate": "50%",
        },
        2,
        {"generic": rule},
    )
    assert not errors
    # A campaign-specific lower commission creates a positive campaign from a loss baseline.
    offer = seasonal_offers(p, rule, ("demo", D(0), D(0)), D(1))
    assert offer["status"] == "SAFE" and offer["profit"] > 0
    assert offer["required_sales_multiplier"] is None
