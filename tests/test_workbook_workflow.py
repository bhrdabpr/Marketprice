import zipfile
from io import BytesIO

import pytest
from openpyxl import Workbook

from marketprice.io import read_upload, workbook_sheets


def fixture():
    b = Workbook()
    s = b.active
    s.title = "First"
    s.append(["sku", "purchase_cost"])
    s.append(["001", "=10+20"])
    t = b.create_sheet("Second")
    t.append(["sku", "purchase_cost", None])
    t.append(["002", 50, "=B2"])
    t.append([None, None, None])
    t.append(["003", 60, None])
    t.cell(100005, 1).number_format = "0"
    out = BytesIO()
    b.save(out)
    return out.getvalue()


def test_sheet_selection_blank_tail_and_internal_source_rows():
    content = fixture()
    assert workbook_sheets(content) == ["First", "Second"]
    rows = read_upload(content, "book.xlsx", preserve_headers=True, sheet_name="Second")
    assert len(rows) == 3 and rows[0]["sku"] == "002" and rows[2]["sku"] == "003"
    assert rows[1]["sku"] is None
    assert "Unnamed column 3" in rows[0]


def test_cached_mode_keeps_missing_formula_result_missing_and_does_not_execute():
    content = fixture()
    assert read_upload(content, "book.xlsx", preserve_headers=True)[0]["purchase_cost"] == "=10+20"
    assert (
        read_upload(content, "book.xlsx", preserve_headers=True, cached_values=True)[0]["purchase_cost"]
        is None
    )


def test_external_links_require_explicit_cached_mode_but_macros_still_rejected():
    source = fixture()

    def add(name):
        out = BytesIO()
        with zipfile.ZipFile(BytesIO(source)) as old, zipfile.ZipFile(out, "w") as new:
            for entry in old.infolist():
                new.writestr(entry, old.read(entry.filename))
            new.writestr(name, b"placeholder")
        return out.getvalue()

    linked = add("xl/externalLinks/externalLink1.xml")
    with pytest.raises(ValueError, match="external links forbidden"):
        read_upload(linked, "book.xlsx", preserve_headers=True)
    assert (
        read_upload(linked, "book.xlsx", preserve_headers=True, cached_values=True)[0]["purchase_cost"]
        is None
    )
    with pytest.raises(ValueError, match="macros/external links forbidden"):
        read_upload(add("xl/vbaProject.bin"), "book.xlsx", cached_values=True)


def test_direct_price_dependent_cost_is_flagged_without_formula_execution():
    from marketprice.workbook_review import price_dependent_costs

    b = Workbook()
    s = b.active
    s.title = "Products"
    s.append(["sku", "purchase_cost", "shipping", "current_price"])
    s.append(["001", 100, "=IF(D2<1000,0.07*D2,70)", 200])
    out = BytesIO()
    b.save(out)
    mapping = {k: k for k in ["sku", "purchase_cost", "shipping", "current_price"]}
    assert price_dependent_costs(out.getvalue(), "Products", mapping, 1) == ["shipping"]
