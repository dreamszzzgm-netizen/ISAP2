from src.application.services.smart_import.profiles import IMPORT_PROFILES


def test_fire_department_column_mapping_synonyms():
    profile = IMPORT_PROFILES["fire_departments"]
    mapping = profile.map_headers(["ПСЧ", "Адрес", "Тел. диспетчера", "Район"])
    assert mapping["ПСЧ"] == "name"
    assert mapping["Адрес"] == "address"
    assert mapping["Тел. диспетчера"] == "dispatcher_phone"
    assert mapping["Район"] == "municipality"


def test_pasf_row_normalization_lists():
    profile = IMPORT_PROFILES["pasf_units"]
    headers = ["ПАСФ", "Номер свидетельства", "Виды работ", "Оснащение"]
    mapping = profile.map_headers(headers)
    row = {
        "ПАСФ": "ПАСФ ООО ГазСпасСервис",
        "Номер свидетельства": "АСФ-001",
        "Виды работ": "газоспасательные работы; аварийно-спасательные работы",
        "Оснащение": "газоанализатор; СИЗОД",
    }
    normalized = profile.normalize_row(row, mapping)
    errors, warnings = profile.validate_row(normalized)
    assert errors == []
    assert normalized["permitted_work_types"] == [
        "газоспасательные работы",
        "аварийно-спасательные работы",
    ]
    assert normalized["equipment_passport"] == ["газоанализатор", "СИЗОД"]


def test_pmla_questionnaire_custom_scenarios_field():
    profile = IMPORT_PROFILES["pmla_questionnaire"]
    mapping = profile.map_headers(["Организация", "ОПО", "Другое"])
    normalized = profile.normalize_row(
        {"Организация": "АО Хлебокомбинат", "ОПО": "Сеть газопотребления", "Другое": "Отказ задвижки; отказ автоматики"},
        mapping,
    )
    assert normalized["custom_scenarios"] == ["Отказ задвижки", "отказ автоматики"]
