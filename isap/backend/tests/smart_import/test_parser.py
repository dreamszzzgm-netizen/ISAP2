from src.application.services.smart_import.parser import SmartImportParser


def test_parse_csv_semicolon():
    content = "Наименование;Адрес;Телефон\nПСЧ-1;г. Якутск;101\n".encode("utf-8")
    table = SmartImportParser().parse_bytes("fire.csv", content)
    assert table.headers == ["Наименование", "Адрес", "Телефон"]
    assert table.rows[0]["Наименование"] == "ПСЧ-1"
