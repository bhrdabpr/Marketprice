from marketprice.batch import COST_FIELDS, process
from marketprice.samples import sample_row


def scoped(count):
    fields = set(sorted(COST_FIELDS)[: count - 1]) | {"commission_rate"}
    while len(fields) > count:
        fields.remove(next(x for x in sorted(fields) if x != "commission_rate"))
    row = {k: v for k, v in sample_row().items() if k not in COST_FIELDS or k in fields}
    return fields, row


def test_five_and_ten_cost_workbooks_and_row_isolation():
    for count in [5, 10]:
        fields, row = scoped(count)
        result = process(
            [
                {**row, "sku": "GOOD"},
                {**row, "sku": "MISSING", "commission_rate": ""},
                {**row, "sku": "ZERO", "commission_rate": "0"},
            ],
            applicable_costs=fields,
        )
        assert [x["status"] for x in result["Product_Calculations"]] == ["VALID", "INVALID", "VALID"]
        assert {x["sku"] for x in result["Price_Recommendations"]} == {"GOOD", "ZERO"}
        assert any(x["sku"] == "MISSING" and x["code"] == "MISSING_COMMISSION" for x in result["Errors"])


def test_present_blank_cannot_be_disabled():
    fields, row = scoped(5)
    field = next(iter(COST_FIELDS - fields))
    assert process([{**row, field: ""}], applicable_costs=fields)["Errors"]
