import tempfile
from pathlib import Path
from uuid import UUID

from src.application.services import pmla_generation_from_questionnaire_service as module
from src.application.services.pmla_generation_from_questionnaire_service import PmlaGenerationFromQuestionnaireService


def _service():
    # Unit tests cover pure adapter/validator methods without DB dependencies.
    return object.__new__(PmlaGenerationFromQuestionnaireService)


def test_adapt_context_for_generator_merges_questionnaire_facts():
    service = _service()
    context = {
        "organization": {"id": "11111111-1111-1111-1111-111111111111", "name": "АО Хлебокомбинат"},
        "facility": {
            "id": "22222222-2222-2222-2222-222222222222",
            "name": "Сеть газопотребления",
            "facility_type": "Сеть газопотребления",
            "hazard_class": "III",
        },
        "substances": [{"name": "Природный газ (метан)"}],
        "equipment": [{"name": "Газопровод"}],
        "questionnaire": {
            "incident_history": {"has_incidents": "нет", "items": []},
            "selected_scenarios": ["Утечка природного газа"],
            "custom_scenarios": [{"title": "Отказ запорной арматуры"}],
            "financial_reserve": {"order_number": "№80-П", "order_date": "19.02.2026", "amount": "250 000 руб."},
            "insurance": {"company": "АО СОГАЗ", "contract_number": "123"},
            "organization_resources": {
                "actual_items": [
                    {"name": "Газоанализатор", "quantity": 1, "location": "котельная"}
                ]
            },
        },
        "pasf": {
            "name": "ПАСФ ООО ГазСпасСервис",
            "dispatch_phone": "+7",
            "actual_address": "г. Якутск",
            "certificate_number": "АСФ-001",
        },
        "emergency_services": [{"service_type": "fire", "name": "ПСЧ-1", "phone": "101"}],
    }

    adapted = service.adapt_context_for_generator(context)

    assert adapted["accidents_and_incidents"][0]["description"].startswith("За период эксплуатации")
    assert len(adapted["user_scenarios"]) == 2
    assert adapted["emergency_services"][0]["service_type"] == "pasf"
    assert adapted["material_reserve"]["fin_reserve_order"] == "№80-П от 19.02.2026"
    assert adapted["context_params"]["insurance_company"] == "АО СОГАЗ"
    assert adapted["protective_equipment"][0]["name"] == "Газоанализатор"


def _questionnaire_base_context(**overrides):
    """Базовый контекст анкеты для тестов adapt_context_for_generator."""
    ctx = {
        "organization": {"id": "1", "name": "АО Тест"},
        "facility": {"id": "2", "name": "ОПО", "facility_type": "Котельная", "hazard_class": "III"},
        "substances": [{"name": "Природный газ"}],
        "equipment": [{"name": "Котёл"}],
        "questionnaire": {
            "incident_history": {"has_incidents": False, "items": []},
            "selected_scenarios": [],
            "custom_scenarios": [],
            "financial_reserve": {"order_number": "№1", "amount": "1000"},
            "insurance": {"company": "СОГАЗ", "contract_number": "К-1", "valid_until": "2026-01-01"},
            "organization_resources": {"actual_items": []},
            "notification_scheme": {"first_receiver": "Оператор"},
        },
        "emergency_services": [],
        "protective_equipment": [],
    }
    ctx.update(overrides)
    return ctx


def test_adapt_context_carries_insurance_amount():
    """P0-3: страховая сумма переносится в material_reserve и ctx.insurance."""
    service = _service()
    ctx = _questionnaire_base_context()
    ctx["questionnaire"]["insurance"]["insured_amount"] = "10000000"
    adapted = service.adapt_context_for_generator(ctx)

    assert adapted["material_reserve"]["insurance_amount"] == "10000000"
    assert adapted["insurance"]["insured_amount"] == "10000000"
    assert adapted["insurance"]["company"] == "СОГАЗ"


def test_adapt_context_insurance_amount_fallback_keys():
    """P0-3: страховая сумма поддерживает альтернативные ключи (sum_rub и т.д.)."""
    service = _service()
    ctx = _questionnaire_base_context()
    ctx["questionnaire"]["insurance"] = {
        "company": "СОГАЗ",
        "contract_number": "К-2",
        "sum_rub": "5000000",
    }
    adapted = service.adapt_context_for_generator(ctx)

    assert adapted["material_reserve"]["insurance_amount"] == "5000000"


def test_adapt_context_normalizes_default_notification_keys():
    """P2-7: ключи DEFAULT_QUESTIONNAIRE маппятся в канонические engine-ключи."""
    service = _service()
    ctx = _questionnaire_base_context()
    ctx["questionnaire"]["notification_scheme"] = {
        "first_receiver": "Оператор котельной",
        "responsible_manager": "Дежурный инженер",
        "calls_pasf": "Диспетчер",
        "calls_fire": "Оператор",
        "meets_services": "Да",
        "contacts": [{"name": "ЕДДС", "phone": "112"}],
    }
    adapted = service.adapt_context_for_generator(ctx)
    notification = adapted["notification_scheme"]

    assert notification["first_receiver"] == "Оператор котельной"
    assert notification["incident_commander"] == "Дежурный инженер"
    assert notification["pasf_caller"] == "Диспетчер"
    assert notification["fire_caller"] == "Оператор"
    # contacts сохранены
    assert notification["contacts"] == [{"name": "ЕДДС", "phone": "112"}]


def test_adapt_context_preserves_canonical_notification_keys():
    """P2-7: канонические engine-ключи не перезаписываются алиасами."""
    service = _service()
    ctx = _questionnaire_base_context()
    ctx["questionnaire"]["notification_scheme"] = {
        "first_receiver": "Оператор",
        "incident_commander": "Рук-ль АСР (канон)",
        "pasf_caller": "Диспетчер ПАСФ",
        "calls_pasf": "не должно перезаписать",
    }
    adapted = service.adapt_context_for_generator(ctx)
    notification = adapted["notification_scheme"]

    assert notification["incident_commander"] == "Рук-ль АСР (канон)"
    assert notification["pasf_caller"] == "Диспетчер ПАСФ"


def test_validate_questionnaire_context_returns_soft_warnings():
    service = _service()
    context = {
        "organization": {"name": "АО Хлебокомбинат"},
        "facility": {"name": "ОПО", "facility_type": "Сеть газопотребления", "hazard_class": "III"},
        "substances": [{"name": "Природный газ"}],
        "equipment": [{"name": "Газопровод"}],
        "questionnaire": {"incident_history": {"has_incidents": None}},
        "selected_scenarios": [],
        "custom_scenarios": [],
        "emergency_services": [],
        "protective_equipment": [],
    }

    quality = service.validate_questionnaire_context(context)

    assert quality["passed"] is True
    assert quality["summary"]["warning_count"] >= 4


def test_save_debug_artifacts_includes_rendered_sections(monkeypatch):
    """Use a local subdirectory to avoid Windows temp-dir permission issues."""
    service = _service()
    local_dir = Path(tempfile.mkdtemp(prefix="isap_debug_test_"))
    monkeypatch.setattr(module, "QUESTIONNAIRE_DEBUG_DIR", local_dir)
    document = type(
        "Document",
        (),
        {
            "status": "pending_review",
            "generation_meta": {"source": "pmla_questionnaire"},
            "rendered_sections": {"1": {"title": "Раздел", "blocks": []}},
            "content_docx": b"docx",
        },
    )()

    artifacts = service._save_debug_artifacts(
        questionnaire_id=UUID("11111111-1111-1111-1111-111111111111"),
        document_id=UUID("22222222-2222-2222-2222-222222222222"),
        context={"facility": {"name": "ОПО"}},
        quality={"passed": True},
        document=document,
    )

    assert artifacts["context"].endswith("context.json")
    assert artifacts["rendered_sections"].endswith("rendered_sections.json")
    assert artifacts["docx"].endswith("output.docx")
