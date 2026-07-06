from src.application.services.pmla_questionnaire_service import DEFAULT_QUESTIONNAIRE, PmlaQuestionnaireService


class DummyService(PmlaQuestionnaireService):
    def __init__(self):
        pass


def test_default_questionnaire_contains_required_engineering_blocks():
    assert "incident_history" in DEFAULT_QUESTIONNAIRE
    assert "custom_scenarios" in DEFAULT_QUESTIONNAIRE
    assert "selected_pasf_id" in DEFAULT_QUESTIONNAIRE
    assert "organization_resources" in DEFAULT_QUESTIONNAIRE
    assert "notification_scheme" in DEFAULT_QUESTIONNAIRE


def test_resource_recommendations_for_gas_facility():
    facility = type("Facility", (), {"facility_type": "Сеть газопотребления"})()
    service = DummyService()
    result = service._build_resource_recommendations(
        facility,
        [{"name": "Природный газ (метан)"}],
        {"selected_scenarios": ["утечка газа", "пожар"], "custom_scenarios": []},
    )
    names = [item["name"] for item in result["resources"]]
    assert "Переносной газоанализатор" in names
    assert "СИЗОД / противогазы" in names
