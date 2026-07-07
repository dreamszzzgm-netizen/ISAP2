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
