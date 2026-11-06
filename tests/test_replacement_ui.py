import csv
import json
from datetime import date, timedelta
from io import BytesIO, StringIO
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from marketprice.approvals import snapshot
from marketprice.i18n import translate


class Upload(BytesIO):
    def __init__(self, data, name):
        super().__init__(data)
        self.name = name


@pytest.mark.parametrize("language", ["en", "fa"])
def test_bilingual_quote_and_budget_evidence_without_cloud(monkeypatch, language):
    uploads = {"catalog": Upload(b"sku,purchase_cost,current_price\nDEMO,100,200\n", "demo.csv")}
    downloads = {}
    original = st.download_button

    def capture(label, data, file_name=None, **kwargs):
        downloads[file_name] = data
        assert kwargs.get("on_click") == "ignore"
        return original(label, data, file_name, **kwargs)

    def upload(*args, key, **kwargs):
        if key.startswith("catalog_upload"):
            return uploads["catalog"]
        if key.startswith("replacement_quotes_"):
            return uploads.get("quotes")
        return None

    monkeypatch.setattr(st, "file_uploader", upload)
    monkeypatch.setattr(st, "download_button", capture)
    app = AppTest.from_file(Path("app.py").resolve()).run()
    app.radio(key="ui_language").set_value(language).run()
    next(c for c in app.checkbox if c.key.startswith("confirm_")).check().run()
    app.checkbox(key="omitted_").check().run()
    next(b for b in app.button if b.label == translate("Validate and calculate", language)).click().run()
    assert not app.exception and not app.error
    before = snapshot(app.session_state["result"])
    quote_rows = list(
        csv.DictReader(StringIO(downloads["marketprice_replacement_quotes.csv"].decode("utf-8-sig")))
    )
    for row in quote_rows:
        row.update(
            replacement_net_unit_cost="140",
            quoted_on=date.today().isoformat(),
            valid_until=(date.today() + timedelta(days=1)).isoformat(),
            source_reference="SYNTHETIC TEST",
        )
    stream = StringIO()
    writer = csv.DictWriter(stream, fieldnames=quote_rows[0])
    writer.writeheader()
    writer.writerows(quote_rows)
    uploads["quotes"] = Upload(stream.getvalue().encode(), "quotes.csv")
    app.run()
    next(c for c in app.checkbox if c.key.startswith("replacement_confirm_")).check().run()
    evidence = json.loads(downloads["marketprice_replacement_review.json"])
    assert evidence["review"]["Replacement_Review"][0]["replacement_contribution"] == "60"
    assert not evidence["review"]["Quote_Errors"]
    next(c for c in app.number_input if c.key.startswith("replacement_units_")).set_value(10).run()
    next(c for c in app.text_input if c.key.startswith("replacement_budget_")).set_value("60").run()
    next(c for c in app.checkbox if c.key.startswith("replacement_budget_confirm_")).check().run()
    plan = json.loads(downloads["marketprice_campaign_budget.json"])
    assert plan["campaign_requirement"]["required_units"] == 27
    assert plan["campaign_requirement"]["decision_ready"] is False
    assert snapshot(app.session_state["result"]) == before
    assert not app.exception and not app.error
    assert any(
        d.proto.label == translate("Download campaign budget evidence", language)
        for d in app.get("download_button")
    )
    # A changed quote must not inherit a previous review confirmation.
    uploads["quotes"] = Upload(stream.getvalue().replace("140", "145").encode(), "quotes.csv")
    app.run()
    assert not next(c for c in app.checkbox if c.key.startswith("replacement_confirm_")).value
    assert not any(
        d.proto.label == translate("Download campaign budget evidence", language)
        for d in app.get("download_button")
    )
    app.button(key="clear_session").click().run()
    assert "result" not in app.session_state
    assert app.radio(key="ui_language").value == language
