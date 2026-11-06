from decimal import Decimal as D
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from marketprice.opportunity import compare, sales_rows


def test_observed_map_zero_baseline_unknown_margin_and_group_validation():
    rows = [
        {
            "sku": str(i),
            "marketplace": "demo",
            "category": "A",
            "currency": "IRR",
            "price": p,
            "units": u,
            "previous_units": old,
            "margin": m,
            "target_margin": ".2",
        }
        for i, (p, u, old, m) in enumerate([(100, 30, 0, ""), (200, 60, 30, "-.1"), (300, 0, 0, ".3")])
    ]
    results, price, velocity = compare(sales_rows(rows, 30))
    assert (price, velocity) == (200, 1)
    assert results[0]["growth_rate"] is None and results[0]["margin_risk"] == "Unknown"
    assert results[1]["growth_rate"] == 1 and results[1]["margin_risk"] == "Loss"
    assert results[2]["trend"] == "Stable"
    with pytest.raises(ValueError):
        sales_rows(rows + [rows[0]], 30)


@pytest.mark.parametrize("language", ["fa", "en"])
def test_map_workspace_and_clear(monkeypatch, language):
    import streamlit as st

    charts = []
    original = st.altair_chart

    def capture(chart, **kwargs):
        charts.append(chart.to_dict())
        return original(chart, **kwargs)

    monkeypatch.setattr(st, "altair_chart", capture)
    app = AppTest.from_file(Path("app.py").resolve()).run()
    app.radio(key="ui_language").set_value(language).run()
    app.radio[1].set_value("Sales map").run()
    app.checkbox(key="sales_map_demo").check().run()
    assert not app.exception and not app.error
    assert len(charts[-1]["layer"]) == 3
    assert len(app.metric) == 3
    app.selectbox(key="display_currency__" + language).set_value("TOMAN").run()
    chart = charts[-1]
    assert "TOMAN" in chart["layer"][0]["encoding"]["x"]["title"]
    data = chart["datasets"][chart["layer"][0]["data"]["name"]]
    assert data[0]["price"] == 10
    app.button(key="clear_session").click().run()
    assert app.radio(key="ui_language").value == language
    assert app.selectbox(key="display_currency__" + language).value == "TOMAN"
    assert app.radio[1].value == "Sales map"
    assert not app.checkbox(key="sales_map_demo").value
    assert not app.metric


def test_sales_velocity_display_preserves_calculation_precision():
    from marketprice.presentation import display_value

    velocity = D(40) / D(30)
    assert display_value("units_per_day", velocity) == "1.3333"
    assert display_value("units_per_day", velocity, persian_digits=True) == "۱٫۳۳۳۳"
    assert velocity > D("1.3333")


def test_capped_charges_thresholds_and_floor():
    from marketprice.engine import CalculationError, evaluate, floor_price
    from marketprice.models import CappedCharge, CategoryCharges
    from tests.test_engine import RULE, product

    p = product(category="test", shipping=0, fulfillment=0)
    rule = RULE.model_copy(
        update={
            "require_category_charges": True,
            "category_charges": {
                "test": CategoryCharges(
                    shipping=CappedCharge(rate=D(".1"), maximum=D(20), base="gross", taxable=False),
                    processing=CappedCharge(rate=D(".05"), maximum=D(7), base="gross", taxable=True),
                )
            },
        }
    )
    for price in (D("139.99"), D(140), D("140.01"), D("199.99"), D(200), D("200.01"), D(400)):
        ledger = evaluate(p, rule, price)
        assert ledger.capped_shipping == min(ledger.customer_gross * D(".1"), D(20))
        assert ledger.capped_processing == min(ledger.customer_gross * D(".05"), D(7))
    floor = floor_price(p, rule, D(".2"))
    assert evaluate(p, rule, floor).margin >= D(".2")
    assert evaluate(p, rule, floor - p.increment).margin < D(".2")
    with pytest.raises(CalculationError, match="MISSING_CATEGORY"):
        evaluate(p.model_copy(update={"category": "unknown"}), rule, D(200))
    with pytest.raises(CalculationError, match="DUPLICATES"):
        evaluate(p.model_copy(update={"shipping": D(1)}), rule, D(200))
