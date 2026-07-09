"""Tests for PMLA Quality Review service."""
import os
import tempfile

from src.application.services.pmla_quality_review_service import PmlaQualityReviewService


def _service():
    return PmlaQualityReviewService()


def _full_context():
    """Return a fully populated questionnaire context."""
    return {
        "organization": {"name": "ООО Газпром"},
        "facility": {"name": "Котельная", "facility_type": "Котельная", "hazard_class": "III"},
        "questionnaire": {
            "incident_history": {"has_incidents": False, "items": []},
            "financial_reserve": {"created": True, "order_number": "12-ПБ", "order_date": "2026-01-15", "amount": "500 000 руб."},
            "insurance": {"has_contract": True, "company": "АО СОГАЗ", "contract_number": "ГО-123456", "valid_until": "2027-01-01"},
            "pasf_manual": {"name": "ПАСФ ООО ГазСпас"},
        },
        "selected_scenarios": ["утечка газа"],
        "custom_scenarios": [{"title": "Отказ арматуры"}],
        "pasf": {"name": "ПАСФ ООО ГазСпас", "certificate_number": "АСФ-001"},
        "emergency_services": [
            {"service_type": "fire", "name": "ПСЧ-1"},
            {"service_type": "medical", "name": "Больница №5"},
        ],
        "organization_resources": {"actual_items": [{"name": "Газоанализатор"}]},
        "notification_scheme": {
            "first_receiver": "Оператор",
            "incident_commander": "Начальник смены",
            "pasf_caller": "Диспетчер",
            "fire_caller": "Диспетчер",
        },
        "attachments_checklist": [
            "схема расположения ОПО",
            "схема оповещения",
            "договор с ПАСФ",
            "страховой полис",
        ],
    }


def test_full_context_gives_ok():
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        f.write(b"fake docx")
        docx_path = f.name
    try:
        report = _service().review(_full_context(), docx_path=docx_path)
        assert report.overall_status == "ok"
        assert report.score == 100
        assert len(report.checks) == 10
        assert all(c.status == "ok" for c in report.checks)
    finally:
        os.unlink(docx_path)


def test_no_pasf_gives_warning():
    ctx = _full_context()
    ctx["pasf"] = None
    ctx["questionnaire"]["pasf_manual"] = {}
    report = _service().review(ctx)
    assert report.overall_status == "warning"
    pasf_check = next(c for c in report.checks if c.code == "pasf")
    assert pasf_check.status == "warning"
    assert report.score < 100


def test_has_incidents_true_empty_items_gives_critical():
    ctx = _full_context()
    ctx["questionnaire"]["incident_history"] = {"has_incidents": True, "items": []}
    report = _service().review(ctx)
    incident_check = next(c for c in report.checks if c.code == "incident_history")
    assert incident_check.status == "critical"
    assert report.overall_status == "critical"
    assert report.score <= 80


def test_no_emergency_services_gives_critical():
    ctx = _full_context()
    ctx["emergency_services"] = []
    report = _service().review(ctx)
    es_check = next(c for c in report.checks if c.code == "emergency_services")
    assert es_check.status == "critical"
    assert report.overall_status == "critical"


def test_docx_path_not_found_gives_critical():
    report = _service().review(_full_context(), docx_path="/nonexistent/path/output.docx")
    docx_check = next(c for c in report.checks if c.code == "docx_created")
    assert docx_check.status == "critical"
    assert report.overall_status == "critical"


def test_score_decreases_with_warnings():
    ctx = _full_context()
    ctx["pasf"] = None
    ctx["questionnaire"]["pasf_manual"] = {}
    ctx["organization_resources"] = {"actual_items": []}
    report = _service().review(ctx)
    warnings = [c for c in report.checks if c.status == "warning"]
    assert len(warnings) >= 2
    assert report.score < 100


def test_score_decreases_with_critical():
    ctx = _full_context()
    ctx["emergency_services"] = []
    report = _service().review(ctx)
    assert report.score <= 80


def test_missing_required_data_populated_on_critical():
    ctx = _full_context()
    ctx["emergency_services"] = []
    report = _service().review(ctx)
    assert len(report.missing_required_data) > 0


def test_manual_review_required_populated_on_warning():
    ctx = _full_context()
    ctx["pasf"] = None
    ctx["questionnaire"]["pasf_manual"] = {}
    report = _service().review(ctx)
    assert len(report.manual_review_required) > 0


def test_recommendations_contain_actionable_items():
    report = _service().review(_full_context())
    assert len(report.recommendations) > 0
    assert any("проверить" in r.lower() for r in report.recommendations)


def test_to_dict_returns_expected_structure():
    report = _service().review(_full_context())
    d = report.to_dict()
    assert "overall_status" in d
    assert "score" in d
    assert "checks" in d
    assert "missing_required_data" in d
    assert "manual_review_required" in d
    assert "recommendations" in d
    assert isinstance(d["checks"], list)
    assert all("code" in c and "status" in c for c in d["checks"])


def test_notification_scheme_critical_when_empty():
    ctx = _full_context()
    ctx["notification_scheme"] = {}
    report = _service().review(ctx)
    notify_check = next(c for c in report.checks if c.code == "notification_scheme")
    assert notify_check.status == "critical"


def test_notification_scheme_warning_when_partial():
    ctx = _full_context()
    ctx["notification_scheme"] = {"first_receiver": "Оператор"}
    report = _service().review(ctx)
    notify_check = next(c for c in report.checks if c.code == "notification_scheme")
    assert notify_check.status == "warning"


# --- Patch A regression tests (P0-1, P1-4, P1-5) ---


def test_docx_created_ok_when_content_docx_bytes_present():
    """P0-1: DOCX хранится байтами в content_docx — check должен быть ok,
    даже если debug-файл ещё не записан на диск."""
    report = _service().review(_full_context(), content_docx=b"fake docx bytes")
    docx_check = next(c for c in report.checks if c.code == "docx_created")
    assert docx_check.status == "ok"


def test_docx_created_bytes_win_over_missing_path():
    """P0-1: байты имеют приоритет — даже с несуществующим путём файловый
    fallback не должен давать critical, если байты есть."""
    report = _service().review(
        _full_context(), docx_path="/nonexistent/output.docx", content_docx=b"docx"
    )
    docx_check = next(c for c in report.checks if c.code == "docx_created")
    assert docx_check.status == "ok"


def test_docx_created_warning_when_no_bytes_no_path():
    """P0-1: ни байтов, ни пути — warning (не critical)."""
    report = _service().review(_full_context())
    docx_check = next(c for c in report.checks if c.code == "docx_created")
    assert docx_check.status == "warning"


def test_organization_resources_ok_with_alternative_keys():
    """P1-4: расширенные ключи ppe/fire_fighting считаются заполненным блоком."""
    ctx = _full_context()
    ctx["organization_resources"] = {
        "ppe": [{"name": "Противогаз"}],
        "fire_fighting": [{"name": "Огнетушитель ОП-10"}],
    }
    report = _service().review(ctx)
    res_check = next(c for c in report.checks if c.code == "organization_resources")
    assert res_check.status == "ok"


def test_organization_resources_ok_with_single_alt_key():
    """P1-4: один расширенный ключ (monitoring) достаточен."""
    ctx = _full_context()
    ctx["organization_resources"] = {"monitoring": [{"name": "Газоанализатор"}]}
    report = _service().review(ctx)
    res_check = next(c for c in report.checks if c.code == "organization_resources")
    assert res_check.status == "ok"


def test_organization_resources_warning_when_all_empty():
    """P1-4: все расширенные ключи пусты — warning."""
    ctx = _full_context()
    ctx["organization_resources"] = {"ppe": [], "fire_fighting": [], "actual_items": []}
    report = _service().review(ctx)
    res_check = next(c for c in report.checks if c.code == "organization_resources")
    assert res_check.status == "warning"


def test_emergency_services_ambulance_recognized_as_medical():
    """P1-5: service_type=ambulance закрывает requirement medical."""
    ctx = _full_context()
    ctx["emergency_services"] = [
        {"service_type": "fire", "name": "ПСЧ-1"},
        {"service_type": "ambulance", "name": "Скорая"},
    ]
    report = _service().review(ctx)
    es_check = next(c for c in report.checks if c.code == "emergency_services")
    assert es_check.status == "ok"


def test_emergency_services_russian_aliases_recognized():
    """P1-5: русские алиасы (скорая/МЧС) нормализуются."""
    ctx = _full_context()
    ctx["emergency_services"] = [
        {"service_type": "МЧС", "name": "Пожарные"},
        {"service_type": "скорая помощь", "name": "Скорая"},
    ]
    report = _service().review(ctx)
    es_check = next(c for c in report.checks if c.code == "emergency_services")
    assert es_check.status == "ok"


def test_emergency_services_other_types_not_broken():
    """P1-5: police/gas/edds проходят через нормализацию без изменений."""
    ctx = _full_context()
    ctx["emergency_services"] = [
        {"service_type": "fire", "name": "ПСЧ-1"},
        {"service_type": "medical", "name": "Больница"},
        {"service_type": "police", "name": "ОВД"},
        {"service_type": "gas", "name": "АГС"},
    ]
    report = _service().review(ctx)
    es_check = next(c for c in report.checks if c.code == "emergency_services")
    assert es_check.status == "ok"
