from decimal import Decimal as D
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from marketprice.cost_impact import cost_impact
from marketprice.opportunity import descriptive_fit


def test_costs_independent_example():
    result = cost_impact(100, '.1', 20, 30, 200, 2, 100)
    assert result['total'] == 1000
    assert result['per_unit'] == 10
    assert result['expected_returns'] == 10
    for units, rate in [(0, '.1'), (100, '1.1'), ('1.5', '.1')]:
        with pytest.raises(ValueError):
            cost_impact(units, rate, 20, 30, 200, 2, 100)


def test_descriptive_regression():
    rows = [{'price': D(x), 'units': D(2*x+1), 'days': 1} for x in (1, 2, 3)]
    fit = descriptive_fit(rows)
    assert (fit['slope'], fit['intercept'], fit['r_squared']) == (2, 1, 1)
    assert descriptive_fit(rows[:2]) is None
    assert descriptive_fit([rows[0]] * 3) is None


@pytest.mark.parametrize('language', ['en', 'fa'])
def test_workspace_navigation(language):
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run()
    app.radio(key='ui_language').set_value(language).run()
    app.radio[1].set_value('Overview').run()
    app.button(key='open_2').click().run()
    assert app.radio[1].value == 'Cost impact'
    assert len(app.metric) == 3
    assert not app.exception


def test_cost_inputs_survive_language_and_clear():
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run()
    app.radio[1].set_value('Cost impact').run()
    app.number_input(key='cost_impact_units_0').set_value(245).run()
    app.radio(key='ui_language').set_value('fa').run()
    assert app.radio[1].value == 'Cost impact'
    assert app.number_input(key='cost_impact_units_0').value == 245
    app.button(key='clear_session').click().run()
    assert app.radio(key='ui_language').value == 'fa'
    assert app.number_input(key='cost_impact_units_1').value == 100
    assert not app.exception


def test_selected_season_survives_language_round_trip():
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run()
    selected = ['Yalda (یلدا)']
    app.multiselect[0].set_value(selected).run()
    for language in ('fa', 'en'):
        app.radio(key='ui_language').set_value(language).run()
        assert app.multiselect[0].value == selected
        assert not app.exception
