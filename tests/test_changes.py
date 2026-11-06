from decimal import Decimal as D
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from marketprice.changes import FIELDS, compare_snapshots


def row(**updates):
    return {'row': 2, 'sku':'A', 'marketplace':'custom', 'currency':'USD',
            'status':'VALID', 'cost_confidence':'CONFIRMED_INPUTS',
            **dict.fromkeys(FIELDS, 0), 'revenue':150, 'cogs':100, 'profit':50, **updates}


def test_cost_change_and_source_links():
    result = compare_snapshots([row()], [row(row=9, cogs=120, profit=30)])
    item = result['Changes'][0]
    assert item['profit_change'] == -20
    assert item['cogs_change'] == 20
    assert (item['previous_row'], item['current_row']) == (2, 9)
    assert item['review'] == 'REVIEW_CHANGE'
    assert item['decision_ready'] is False


def test_duplicates_currency_and_missing_costs():
    assert not compare_snapshots([row(), row()], [row()])['Changes']
    result = compare_snapshots([row()], [row(currency='EUR')])
    assert {r['review'] for r in result['Changes']} == {'ADDED','REMOVED'}
    assert compare_snapshots([row()], [row(cost_confidence=None)])['Changes'][0]['review'] == 'CONFIRM_COSTS'
    assert compare_snapshots([row()], [row(status='INVALID')])['Changes'][0]['review'] == 'FIX_PRODUCT'
    assert compare_snapshots([row()], [row(profit='bad')])['Changes'][0]['review'] == 'INCOMPLETE_LEDGER'


def test_fractional_and_ranking():
    result = compare_snapshots([row(), row(sku='B')], [row(profit=D('49.99')), row(sku='B', profit=40)])
    assert [r['sku'] for r in result['Changes']] == ['B','A']
    assert result['Changes'][1]['profit_change'] == D('-.01')


@pytest.mark.parametrize('language', ['en','fa'])
def test_workspace(language):
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run()
    app.radio(key='ui_language').set_value(language).run()
    app.radio[1].set_value('Changes').run()
    assert not app.exception
    assert len(app.get('file_uploader')) == 2


def test_existing_report_round_trip_and_literal_export():
    from marketprice.batch import process
    from marketprice.confidence import apply_confidence
    from marketprice.io import read_upload, workbook_bytes
    from marketprice.samples import sample_row

    reports = []
    for cost in ('70', '80'):
        source = [{**sample_row(), "purchase_cost": cost}]
        result = process(source)
        apply_confidence(result, source, omitted_confirmed=True)
        reports.append(read_upload(workbook_bytes(result), 'report.xlsx',
                                   sheet_name='Product_Calculations', preserve_headers=True))
    compared = compare_snapshots(*reports)
    assert compared['Changes'][0]['profit_change'] == -10
    exported = read_upload(workbook_bytes(compared), 'changes.xlsx',
                           sheet_name='Changes', preserve_headers=True)
    assert exported[0]['profit_change'] == -10
    assert exported[0]['decision_ready'] is False
