from decimal import Decimal as D

import pytest

from marketprice.flexible import calculate_catalog
from marketprice.importing import map_rows
from marketprice.validation import number


@pytest.mark.parametrize('locale,value', [('comma','1,000'),('en','1.000'),('fa','۱٫۰۰۰')])
def test_conversion_parsed_once(locale, value):
    row = map_rows([{'cost':value}], {'cost':'purchase_cost'}, {'cost':'TOMAN → IRR'}, locale=locale)[0]
    assert row['purchase_cost'] == 10
    assert number(row['purchase_cost'], locale) == 10


def test_percentage_and_invalid_conversion():
    rows = map_rows([{'cost':'100','fee':'12,5'}, {'cost':'100','fee':'bad'}],
                    {'cost':'purchase_cost','fee':'commission_rate'},
                    {'fee':'Percentage number'}, locale='comma')
    assert rows[0]['commission_rate'] == D('.125')
    assert 'INVALID_CONVERSION' in rows[1]['commission_rate']


@pytest.mark.parametrize('currency,expected', [('IRR',112),('USD',D('111.12'))])
def test_generated_defaults(currency, expected):
    result = calculate_catalog([{'purchase_cost':100}], currency=currency, target_margin='10%', locale='comma')
    assert result['Price_Recommendations'][0]['recommended_price'] == expected
    assert not result['Price_Recommendations'][0]['decision_ready']


def test_confidence_controls_approval_and_competitor_review():
    from marketprice.approvals import approved_changes, snapshot
    from marketprice.batch import process
    from marketprice.competition import review_campaigns
    from marketprice.confidence import apply_confidence
    from marketprice.samples import sample_row

    for states, confirmed in [({}, True), ({'purchase_cost':'estimated'}, False),
                              ({'purchase_cost':'missing'}, False)]:
        result = process([sample_row()])
        apply_confidence(result, [sample_row()], states, omitted_confirmed=True)
        key = (2, str(result['Price_Analysis'][0]['target_margin']))
        if confirmed:
            assert approved_changes(result, [key], expected_snapshot=snapshot(result), fee_rules_confirmed=True)
        else:
            assert not any(r['decision_ready'] for r in result['Campaign_Simulations'])
            with pytest.raises(ValueError):
                approved_changes(result, [key], expected_snapshot=snapshot(result), fee_rules_confirmed=True)
    result = process([sample_row()])
    assert all(r['review']=='CONFIRM_COSTS_OR_MARGIN' for r in review_campaigns(result, []))
    with pytest.raises(ValueError):
        approved_changes(result, [(2, str(result['Price_Analysis'][0]['target_margin']))],
                         expected_snapshot=snapshot(result), fee_rules_confirmed=True)
