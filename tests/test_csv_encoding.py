import pytest

from marketprice.io import read_upload


@pytest.mark.parametrize("encoding", ["utf-8-sig", "utf-16", "cp1256"])
def test_explicit_persian_csv_encoding_preserves_headers_identifiers_and_blanks(encoding):
    text = "کد,بها,نرخ\n001,100,\n002,200,0\n"
    rows = read_upload(text.encode(encoding), "products.csv", preserve_headers=True, encoding=encoding)
    assert rows == [{"کد": "001", "بها": "100", "نرخ": ""}, {"کد": "002", "بها": "200", "نرخ": "0"}]


def test_legacy_csv_is_not_silently_guessed():
    with pytest.raises(ValueError, match="INVALID_FILE"):
        read_upload("کد,بها\n001,100".encode("cp1256"), "products.csv")
    with pytest.raises(ValueError, match="UNSUPPORTED_ENCODING"):
        read_upload(b"a\n1", "products.csv", encoding="unknown")
