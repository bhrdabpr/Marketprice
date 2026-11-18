import hashlib
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest
from streamlit.testing.v1 import AppTest

from marketprice.quick_review import analyze, file_rows
from marketprice.seller_project import (
    changes,
    export_project,
    next_revision,
    restore_project,
    revision,
    sign_in,
    team_history,
)


def test_campaign_incomplete_rows_zero_and_bad_counts():
    rows = file_rows(b"SKU;clicks;impressions;attributed orders;spend;attributed revenue;currency\nA;10;200;2;18;54;AED\nB;1;0;0;7;;AED", "ads.csv")
    a, b = analyze("campaign", rows)["Answers"]
    assert (a["CTR (%)"], a["Cost per attributed order"], a["ROAS (×)"], a["Orders per click (%)"]) == (5, 9, 3, 20)
    assert "CTR (%)" not in b and "Cost per attributed order" not in b and b["Check"]
    assert "attributed sales" in b["Next input"]
    partial = analyze("campaign", [{"clicks": "0", "impressions": "30"}])["Answers"][0]
    assert partial["CTR (%)"] == 0 and "ROAS (×)" not in partial


def test_catalog_thousand_rows_profit_and_floor():
    rows = [{"sku": str(i), "currency": "AED", "purchase_cost": "24", "current_price": "40",
             "fulfillment": "4", "target_margin": "20%", "net profit": 6, "invested capital": 30}
            for i in range(1000)]
    report = analyze("pricing", rows)
    assert len(report["Answers"]) == 1000
    assert report["Answers"][-1]["margin_floor"] == 35
    assert report["Answers"][-1]["cost_confidence"] != "CONFIRMED_INPUTS"
    r = analyze("profit", rows[:1])["Answers"][0]
    assert r["Gross margin (%)"] == 40 and r["Markup on purchase cost (%)"] == Decimal("66.6667")
    assert r["ROI (%)"] == 20 and r["profit"] == 12
    assert not analyze("pricing", [{"sku": "1", "purchase_cost": 5}])["Answers"]
    blank = analyze("pricing", [{**rows[0], "currency": None}])
    assert not blank["Answers"] and blank["Checks"]


def test_storage_and_listing_without_typing_or_confirmation():
    r = analyze("storage", [{"currency":"USD", "units stored":25, "monthly storage fee per unit":".4", "months stored":3}])
    assert r["Answers"][0]["Storage cost"] == 30
    assert analyze("listing", [{"ASIN":"B123", "item name":"A plastic box"}])["Listing_Summary"][0]["sku"] == "B123"


def test_project_round_trip_changes_and_access(tmp_path):
    old = revision("storage", "catalog.csv", [{"sku": "A", "fee": 3}], {})
    new = revision("storage", "catalog.csv", [{"sku": "A", "fee": 4}], {})
    assert restore_project(export_project([old, new])) == [old, new]
    assert not next_revision([old], old) and next_revision([old, new], old)
    assert changes(old["inputs"], new["inputs"])[0]["Later"] == 4
    assert "Check" in changes([{"sku":"A"}, {"sku":"A"}], [])[0]
    with pytest.raises(ValueError):
        restore_project(export_project([{**old, "inputs": []}]))
    members = {"worker":{"token_sha256":hashlib.sha256(b"a synthetic key").hexdigest(), "role":"editor"}}
    assert sign_in(members,"worker","a synthetic key") == "editor"
    with pytest.raises(ValueError):
        sign_in(members,"worker","other")
    path = tmp_path / "team.db"
    with pytest.raises(PermissionError):
        team_history(path, "viewer", new=old, user="worker")
    team_history(path, "manager")
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _: team_history(path, "editor", new=old, user="worker"), range(2)))
    saved = team_history(path, "viewer")
    assert len(saved) == 1 and saved[0]["author"] == "worker"


def test_beginner_entry_and_two_action_file_review():
    app = AppTest.from_file("../app.py").run()
    app.button(key="quick_campaign").click().run()
    app.get("file_uploader")[0].upload("campaign.csv", b"impressions,clicks\n200,6").run()
    assert not app.exception
    assert any(m.label == "CTR (%)" for m in app.metric)
    history = app.session_state["quick_history"]
    assert history[0]["report"]["Answers"][0]["CTR (%)"] == "3.0000"
    app.run()
    assert len(app.session_state["quick_history"]) == 1


def test_pdf_needs_readable_table():
    with pytest.raises(ValueError, match="readable"):
        file_rows(b"no pdf", "catalog.pdf")


def test_read_only_team_dashboard_has_no_review_or_project_download():
    app = AppTest.from_file("../app.py")
    from tempfile import TemporaryDirectory

    with TemporaryDirectory() as folder:
        proof = hashlib.sha256(b"test-only").hexdigest()
        app.secrets["team_project"] = {"database": folder + "/project.sqlite3",
                                       "members":{"reader":{"role":"viewer", "token_sha256":proof}}}
        app.session_state["team_user"] = "reader"
        app.session_state["team_proof"] = proof
        app.run()
        assert not app.exception
        assert app.title[0].value == "Project dashboard"
        assert not app.get("file_uploader") and not app.get("download_button")
        assert not any(b.key == "quick_pricing" for b in app.button)
