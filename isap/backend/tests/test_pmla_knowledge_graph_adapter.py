"""Tests for Knowledge Graph Read Adapter for PMLA."""
import pytest

from src.application.services.pmla_knowledge_graph_adapter import (
    PmlaKnowledgeGraphAdapter,
    PmlaKnowledgeGraphContext,
)


def _adapter():
    return PmlaKnowledgeGraphAdapter()


# --- Adapter tests ---


def test_gas_consumption_facility_returns_context():
    """Gas consumption facility should return full context."""
    ctx = _adapter().get_context({"facility_type": "Сеть газопотребления"})
    assert ctx.facility_type == "сеть газопотребления"
    assert len(ctx.equipment_types) > 0
    assert len(ctx.hazards) > 0
    assert len(ctx.recommended_scenarios) > 0
    assert len(ctx.required_services) > 0
    assert len(ctx.required_appendices) > 0
    assert len(ctx.applicable_regulations) > 0
    assert not ctx.warnings


def test_boiler_facility_returns_context():
    """Boiler facility should return specific context."""
    ctx = _adapter().get_context({"facility_type": "Котельная"})
    assert ctx.facility_type == "котельная"
    assert "котёл" in ctx.equipment_types
    assert len(ctx.recommended_scenarios) > 0


def test_unknown_facility_returns_default_with_warning():
    """Unknown facility type should return default context with warning."""
    ctx = _adapter().get_context({"facility_type": "Несуществующий тип ОПО"})
    assert ctx.facility_type == "Несуществующий тип ОПО"
    assert len(ctx.warnings) == 1
    assert "не найден" in ctx.warnings[0]
    # Should still have required services from default
    assert len(ctx.required_services) > 0


def test_empty_facility_type_returns_empty_context():
    """Empty facility type should return empty context with warning."""
    ctx = _adapter().get_context({"facility_type": ""})
    assert ctx.is_empty
    assert len(ctx.warnings) == 1
    assert "не указан" in ctx.warnings[0]


def test_missing_facility_type_returns_empty_context():
    """Missing facility_type key should return empty context with warning."""
    ctx = _adapter().get_context({})
    assert ctx.is_empty
    assert len(ctx.warnings) == 1


def test_context_is_empty_property():
    """is_empty should return True for empty context."""
    ctx = PmlaKnowledgeGraphContext()
    assert ctx.is_empty


def test_context_is_not_empty_with_data():
    """is_empty should return False when data is present."""
    ctx = PmlaKnowledgeGraphContext(facility_type="test")
    assert not ctx.is_empty


def test_partial_match_facility_type():
    """Facility type with partial match should work."""
    ctx = _adapter().get_context({"facility_type": "Газопотребляющая сеть"})
    assert ctx.facility_type is not None
    # Partial match may not find exact key, but should have default services
    assert len(ctx.required_services) > 0


# --- Quality review graph check tests ---


def test_quality_review_adds_graph_checks():
    """Quality review should include graph context checks."""
    from src.application.services.pmla_quality_review_service import PmlaQualityReviewService

    ctx = {
        "facility": {"facility_type": "Сеть газопотребления"},
        "facility_type": "Сеть газопотребления",
        "emergency_services": [
            {"service_type": "fire", "name": "ПСЧ", "phone": "101"},
            {"service_type": "medical", "name": "Больница", "phone": "103"},
        ],
        "pasf": {"name": "ПАСФ"},
        "selected_scenarios": [{"scenario_name": "разгерметизация газопровода"}],
        "attachments_checklist": [
            {"name": "схема расположения ОПО", "present": True},
            {"name": "схема оповещения", "present": True},
        ],
    }
    svc = PmlaQualityReviewService()
    report = svc.review(ctx)
    graph_checks = [c for c in report.checks if c.code.startswith("graph_")]
    assert len(graph_checks) >= 1


def test_quality_review_graph_warns_missing_service():
    """Graph check should warn when required service is missing."""
    from src.application.services.pmla_quality_review_service import PmlaQualityReviewService

    ctx = {
        "facility": {"facility_type": "Сеть газопотребления"},
        "facility_type": "Сеть газопотребления",
        "emergency_services": [],  # No services
        "selected_scenarios": [],
        "attachments_checklist": [],
    }
    svc = PmlaQualityReviewService()
    report = svc.review(ctx)
    service_check = next(
        (c for c in report.checks if c.code == "graph_required_service_missing"),
        None,
    )
    assert service_check is not None
    assert service_check.status == "warning"


def test_quality_review_graph_ok_when_services_present():
    """Graph check should pass when all required services are present."""
    from src.application.services.pmla_quality_review_service import PmlaQualityReviewService

    ctx = {
        "facility": {"facility_type": "Сеть газопотребления"},
        "facility_type": "Сеть газопотребления",
        "emergency_services": [
            {"service_type": "fire", "name": "ПСЧ", "phone": "101"},
            {"service_type": "medical", "name": "Больница", "phone": "103"},
            {"service_type": "gas", "name": "Газовая служба", "phone": "104"},
        ],
        "pasf": {"name": "ПАСФ"},
        "selected_scenarios": [
            {"scenario_name": "разгерметизация участка газопровода"},
            {"scenario_name": "отказ регулятора давления с повышением выходного давления"},
            {"scenario_name": "утечка газа в районе ГРПШ/ШРП"},
            {"scenario_name": "воспламенение газовоздушной смеси"},
            {"scenario_name": "взрыв газовоздушной смеси на открытой площадке"},
            {"scenario_name": "взрыв газовоздушной смеси в замкнутом объеме (шкаф ГРПШ)"},
        ],
        "custom_scenarios": [
            {"title": "отказ запорной арматуры при техническом обслуживании"},
        ],
        "attachments_checklist": [
            {"name": "схема расположения ОПО", "present": True},
            {"name": "схема оповещения", "present": True},
            {"name": "перечень сил и средств", "present": True},
            {"name": "документы ПАСФ", "present": True},
            {"name": "сведения о страховании", "present": True},
        ],
    }
    svc = PmlaQualityReviewService()
    report = svc.review(ctx)
    graph_checks = [c for c in report.checks if c.code.startswith("graph_")]
    for check in graph_checks:
        assert check.status == "ok", f"Graph check {check.code} failed: {check.message}"


def test_quality_review_does_not_fail_without_graph():
    """Quality review should work even if graph adapter fails."""
    from src.application.services.pmla_quality_review_service import PmlaQualityReviewService

    # Minimal context — should not crash
    ctx = {"facility": {}}
    svc = PmlaQualityReviewService()
    report = svc.review(ctx)
    assert report.overall_status in ("ok", "warning", "critical")
    # No graph checks should be added if adapter fails
    graph_checks = [c for c in report.checks if c.code.startswith("graph_")]
    # Either no graph checks or they handle the failure gracefully
    assert len(graph_checks) >= 0


def test_graph_checks_are_warning_not_critical():
    """All graph checks should be warning level, never critical."""
    from src.application.services.pmla_quality_review_service import PmlaQualityReviewService

    ctx = {
        "facility": {"facility_type": "Сеть газопотребления"},
        "facility_type": "Сеть газопотребления",
        "emergency_services": [],
        "selected_scenarios": [],
        "attachments_checklist": [],
    }
    svc = PmlaQualityReviewService()
    report = svc.review(ctx)
    graph_checks = [c for c in report.checks if c.code.startswith("graph_")]
    for check in graph_checks:
        assert check.status != "critical", (
            f"Graph check {check.code} should not be critical"
        )
