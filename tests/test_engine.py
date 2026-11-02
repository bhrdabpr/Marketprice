from decimal import Decimal as D
from decimal import localcontext

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from marketprice.batch import process
from marketprice.campaign import simulate
from marketprice.config import load_profiles
from marketprice.engine import CalculationError, evaluate, floor_price
from marketprice.models import Profile, Tier
from marketprice.samples import sample_row
from marketprice.validation import validate

RULE = load_profiles()["generic"]


def product(**changes):
    raw = {**sample_row(), **changes}
    p, errors = validate(raw, 2, {"generic": RULE})
    assert not errors, errors
    return p


def test_independent_golden():
    p = product()
    price = floor_price(p, RULE, D(".2"))
    assert price == D("117.65")
    assert floor_price(p, RULE, D(0)) == D("90.91")
    result = evaluate(p, RULE, price)
    assert result.profit == D("23.532")
    assert result.margin >= D(".2")
    assert evaluate(p, RULE, price - D(".01")).margin < D(".2")
    with localcontext() as ctx:
        ctx.prec = 50
        assert result.markup == result.profit / result.total_cost
    assert result.markup != result.margin


@pytest.mark.parametrize(
    "currency,increment,expected",
    [
        ("USD", ".01", "117.65"),
        ("IRR", "1", "118"),
        ("TOMAN", "1", "118"),
        ("JPY", "1", "118"),
        ("KWD", ".001", "117.648"),
    ],
)
def test_units(currency, increment, expected):
    assert floor_price(product(currency=currency, increment=increment), RULE, D(".2")) == D(expected)


@pytest.mark.parametrize(
    "field,code",
    [
        ("purchase_cost", "MISSING_PURCHASE_COST"),
        ("shipping", "MISSING_SHIPPING_COST"),
        ("commission_rate", "MISSING_COMMISSION"),
        ("tax_rate", "MISSING_TAX_CONFIGURATION"),
    ],
)
def test_missing_never_recommends(field, code):
    result = process([{**sample_row(), field: ""}])
    assert not result["Price_Recommendations"]
    assert code in {r["code"] for r in result["Errors"]}
    assert len(result["Product_Calculations"]) == 1


@pytest.mark.parametrize("field", ["shipping", "commission_rate", "purchase_cost", "tax_rate"])
def test_explicit_zero(field):
    assert process([{**sample_row(), field: "0"}])["Product_Calculations"][0]["status"] == "VALID"


def test_tax_exclusive_and_inclusive():
    a = evaluate(product(tax_rate="20%", tax_mode="exclusive", payment_rate="0"), RULE, D(100))
    b = evaluate(product(tax_rate="20%", tax_mode="inclusive", payment_rate="0"), RULE, D(120))
    assert a.revenue == b.revenue == 100
    assert a.tax_collected == b.tax_collected == 20
    assert a.profit == b.profit == 10
    assert floor_price(product(tax_rate="20%", tax_mode="inclusive", payment_rate="0"), RULE, D(".2")) == D(
        "137.15"
    )


def test_credits():
    a = evaluate(
        product(input_tax_credit="10", fee_tax_rate="10%", fee_tax_recoverable="false"), RULE, D(100)
    )
    b = evaluate(product(input_tax_credit="10", fee_tax_rate="10%", fee_tax_recoverable="true"), RULE, D(100))
    assert a.cogs == 60 and a.fee_tax == D("1.2")
    assert b.profit - a.profit == D("1.2")


def test_progressive_tiers():
    rule = RULE.model_copy(
        update={"tiers": (Tier(up_to=D(100), rate=D(".1")), Tier(up_to=None, rate=D(".2")))}
    )
    p = product(payment_rate="0")
    assert evaluate(p, rule, D(150)).commission == 20
    # Below 100: .9P-80=.2P =>114.28 outside segment.
    # Above 100: .8P-70=.2P =>116.6667.
    assert floor_price(p, rule, D(".2")) == D("116.67")


def test_tier_categories():
    rule = RULE.model_copy(update={"category_tiers": {"general": (Tier(up_to=None, rate=D(".3")),)}})
    assert evaluate(product(), rule, D(100)).commission == 30


@pytest.mark.parametrize("base,fee", [("net", "10"), ("gross", "12"), ("list", "15"), ("settlement", "14")])
def test_fee_bases(base, fee):
    rule = RULE.model_copy(update={"commission_base": base})
    ledger = evaluate(
        product(tax_rate="20%"), rule, D(100), subsidy=D("16.66666666666666666666666667"), list_price=D(150)
    )
    assert abs(ledger.commission - D(fee)) < D("1e-20")


def test_campaign_funding_and_guard():
    p = product()
    seller = simulate(p, RULE, D(".2"))
    platform = simulate(p, RULE, D(".2"), platform_share=D(1))
    assert seller["campaign_price"] == 112 and seller["profit"] == D("18.56")
    assert platform["profit"] == D("46.56")  # payment on customer gross, subsidy not in fee base
    assert platform["profit"] > seller["profit"]
    loss = simulate(p, RULE, D(".8"))
    assert not loss["safe"] and not loss["approved"]
    overridden = simulate(p, RULE, D(".8"), override=True)
    assert not overridden["safe"] and overridden["approved"]
    assert simulate(p, RULE, D(28), kind="fixed")["profit"] == seller["profit"]


def test_impossible():
    with pytest.raises(CalculationError):
        floor_price(product(commission_rate="80%", payment_rate="20%"), RULE, D(".2"))


@pytest.mark.parametrize(
    "field,value",
    [
        ("shipping", "-1"),
        ("commission_rate", "101%"),
        ("currency", "XYZ"),
        ("tax_rate", "NaN"),
        ("purchase_cost", "=2+3"),
        ("increment", "0"),
        ("target_margin", "100%"),
        ("shipping", "infinity"),
    ],
)
def test_bad_inputs(field, value):
    assert process([{**sample_row(), field: value}])["Errors"]


def test_duplicate_and_order():
    rows = [sample_row("A"), {**sample_row("B"), "purchase_cost": "95"}]
    a = process(rows)
    b = process(list(reversed(rows)))
    assert {r["sku"]: r["recommended_price"] for r in a["Price_Recommendations"]} == {
        r["sku"]: r["recommended_price"] for r in b["Price_Recommendations"]
    }
    assert not process([rows[0], rows[0]])["Price_Recommendations"]
    assert a == process(rows)


@given(st.integers(0, 100000), st.integers(0, 100000), st.integers(0, 65))
@settings(max_examples=120)
def test_monotonic_cost_and_margin(a, b, m):
    p = product(purchase_cost=str(a))
    q = product(purchase_cost=str(a + b))
    target = D(m) / 100
    assert floor_price(q, RULE, target) >= floor_price(p, RULE, target)
    assert floor_price(p, RULE, target + D(".01")) >= floor_price(p, RULE, target)


@given(st.integers(0, 100))
def test_campaign_property(discount):
    p = product()
    result = simulate(p, RULE, D(discount) / 100)
    if result["safe"]:
        assert result["profit"] >= 0 and result["margin"] >= p.minimum_margin


def test_very_large():
    p = product(purchase_cost="100000000000000", current_price="200000000000000")
    price = floor_price(p, RULE, D(".2"))
    assert evaluate(p, RULE, price).margin >= D(".2")


def test_profile_conflicts():
    with pytest.raises(ValueError):
        Profile.model_validate({**RULE.model_dump(), "tiers": [{"up_to": 100, "rate": ".1"}]})
