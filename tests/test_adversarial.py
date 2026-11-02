import io
import zipfile
from decimal import Decimal as D

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from marketprice.batch import process
from marketprice.campaign import discount_limits, simulate
from marketprice.config import load_profiles
from marketprice.engine import CalculationError, evaluate, floor_price
from marketprice.io import MAX_BYTES, read_upload
from marketprice.models import Tier
from marketprice.recommendation import recommend
from marketprice.samples import sample_row
from marketprice.validation import validate

RULE = load_profiles()["generic"]


def p(**kw):
    product, errors = validate({**sample_row(), **kw}, 2, {"generic": RULE})
    assert not errors
    return product


@given(st.integers(0, 60), st.integers(0, 100), st.integers(0, 100), st.integers(0, 40))
@settings(max_examples=80, deadline=None)
def test_piecewise_against_independent_integer_grid(cost, rate1, rate2, margin):
    product = p(purchase_cost=str(cost), shipping="0", other_fixed="0", payment_rate="0", increment="1")
    rule = RULE.model_copy(
        update={"tiers": (Tier(up_to=D(100), rate=D(rate1) / 100), Tier(up_to=None, rate=D(rate2) / 100))}
    )
    # Independent finite-grid enumeration; no production evaluator used to find expected price.
    expected = next(
        (
            D(x)
            for x in range(1, 1001)
            if D(x) - cost - min(x, 100) * D(rate1) / 100 - max(x - 100, 0) * D(rate2) / 100
            >= D(x) * margin / 100
        ),
        None,
    )
    if expected is not None:
        assert floor_price(product, rule, D(margin) / 100) == expected
    else:
        try:
            assert floor_price(product, rule, D(margin) / 100) > 1000
        except CalculationError:
            pass


def test_higher_recommendation_cannot_break_margin():
    rule = RULE.model_copy(update={"tiers": (Tier(up_to=D(100), rate=D(0)), Tier(up_to=None, rate=D(1)))})
    product = p(
        purchase_cost="20",
        shipping="0",
        other_fixed="0",
        payment_rate="0",
        current_price="1000",
        recommendation_rule="keep_current",
    )
    with pytest.raises(CalculationError):
        recommend(product, rule, D(".2"))


def test_subsidy_tax_and_shared_funding():
    product = p(tax_rate="20%", tax_mode="inclusive", current_price="120", payment_rate="0")
    result = simulate(product, RULE, D(".2"), platform_share=D(".5"))
    # Price 96 => net80; subsidy12 => net10; commission8; fixed+COGS80 => profit2.
    assert result["profit"] == 2
    ledger = evaluate(product, RULE, D(96), subsidy=D(12))
    assert ledger.tax_collected == 18 and ledger.revenue == 90
    nontax = RULE.model_copy(update={"subsidy_taxable": False})
    assert evaluate(product, nontax, D(96), subsidy=D(12)).revenue == 92


def test_campaign_specific_fees():
    rule = RULE.model_copy(update={"campaign_commission_rate": D(".5"), "campaign_fixed_fee": D(10)})
    result = simulate(p(), rule, D(".1"))
    assert result["profit"] == D("-29.52") and not result["safe"]
    assert discount_limits(p(), rule)["max_break_even_discount"] is None


def test_unreachable_campaign_margin_does_not_hide_regular_price():
    result = process([{**sample_row(), "campaign_margin": "99%"}])
    assert result["Price_Recommendations"] and result["Warnings"]
    assert not any(x["safe"] for x in result["Campaign_Simulations"])


def test_amount_cannot_be_percent():
    assert process([{**sample_row(), "purchase_cost": "70%"}])["Errors"]


def test_numeric_sku_and_blank_row():
    result = process([{**sample_row(), "sku": 123}, {}])
    assert len(result["Product_Calculations"]) == 2 and not result["Price_Recommendations"]


def test_upload_size_and_external_links():
    with pytest.raises(ValueError):
        read_upload(b"x" * (MAX_BYTES + 1), "x.csv")
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as z:
        z.writestr("xl/externalLinks/externalLink1.xml", "x")
    with pytest.raises(ValueError, match="external links"):
        read_upload(stream.getvalue(), "x.xlsx")


def test_cogs_vs_revenue_identity():
    product = p(tax_rate="10%", fee_tax_rate="20%", input_tax_credit="5", transaction_tax_rate="3%")
    ledger = evaluate(product, RULE, D(100))
    assert ledger.revenue == 100 and ledger.customer_gross == 110 and ledger.tax_collected == 10
    assert ledger.total_cost == D("92.64") and ledger.profit == D("7.36")


def test_explicit_currency_conversion():
    from marketprice.currency import Conversion

    conversion = Conversion(
        source_currency="IRR",
        target_currency="TOMAN",
        rate=D(".1"),
        timestamp="2026-11-02T00:00:00+03:30",
        source="Explicit unit conversion supplied by test",
    )
    assert conversion.convert(D(1000)) == 100
    with pytest.raises(ValueError):
        Conversion(source_currency="USD", target_currency="IRR", rate=D(1), timestamp="2026-11-02", source="")


def test_campaign_limit_includes_fixed_and_list_fee():
    rule = RULE.model_copy(update={"commission_base": "list", "campaign_fixed_fee": D(5)})
    limits = discount_limits(p(), rule)
    # Seller campaign: .98P - 80 - 14 - 5. At 10% margin: .88P=99 =>112.50.
    from decimal import localcontext

    with localcontext() as ctx:
        ctx.prec = 50
        assert limits["max_minimum_margin_discount"] == D("27.5") / 140
    scenario = simulate(p(), rule, limits["max_minimum_margin_discount"])
    assert scenario["safe"] and scenario["campaign_price"] == D("112.50")


def test_no_discount_available_if_already_below_floor():
    assert discount_limits(p(current_price="50"), RULE)["max_break_even_discount"] is None


def test_caller_decimal_context_does_not_change_financial_result():
    from decimal import ROUND_DOWN, localcontext

    product = p()
    baseline = simulate(product, RULE, D(".17"), platform_share=D(".5"))
    with localcontext() as ctx:
        ctx.prec = 8
        ctx.rounding = ROUND_DOWN
        assert simulate(product, RULE, D(".17"), platform_share=D(".5")) == baseline
        assert floor_price(product, RULE, D(".2")) == D("117.65")
