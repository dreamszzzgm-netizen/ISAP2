"""Tests for cross-facility guardrails."""
import pytest

from src.application.services.cross_facility_guardrails import (
    check_cross_facility_contamination,
    CROSS_FACILITY_FORBIDDEN,
)


# --- Forbidden terms dictionary tests ---


def test_forbidden_terms_for_boiler():
    """Boiler should have ГРПШ and ШРП as forbidden terms."""
    assert "ГРПШ" in CROSS_FACILITY_FORBIDDEN["котельная"]
    assert "ШРП" in CROSS_FACILITY_FORBIDDEN["котельная"]
    assert "газорегуляторный пункт" in CROSS_FACILITY_FORBIDDEN["котельная"]


def test_forbidden_terms_for_comppressor():
    """Compressor station should have boiler and gas network terms."""
    assert "котёл" in CROSS_FACILITY_FORBIDDEN["компрессорная станция"]
    assert "ГРПШ" in CROSS_FACILITY_FORBIDDEN["компрессорная станция"]


# --- Cross-facility contamination check tests ---


def test_boiler_text_with_grpsh_detected():
    """Boiler text with ГРПШ should be flagged."""
    text = "Проверить состояние ГРПШ и перекрыть газ"
    found = check_cross_facility_contamination(text, "котельная")
    assert "ГРПШ" in found


def test_boiler_text_clean():
    """Clean boiler text should not be flagged."""
    text = "Проверить состояние котла и перекрыть газовую горелку"
    found = check_cross_facility_contamination(text, "котельная")
    assert len(found) == 0


def test_gas_network_text_allows_grpsh():
    """Gas network text should NOT be flagged for ГРПШ."""
    text = "Проверить состояние ГРПШ и перекрыть газ"
    found = check_cross_facility_contamination(text, "сеть газопотребления")
    assert len(found) == 0


def test_unknown_facility_no_forbidden():
    """Unknown facility type should have no forbidden terms."""
    text = "Любой текст с любыми терминами"
    found = check_cross_facility_contamination(text, "несуществующий тип")
    assert len(found) == 0


def test_empty_facility_type():
    """Empty facility type should have no forbidden terms."""
    text = "Любой текст"
    found = check_cross_facility_contamination(text, "")
    assert len(found) == 0


def test_equipment_exclusion():
    """Term found in equipment context should not be flagged."""
    text = "Проверить ГРПШ на площадке"
    equipment = [{"name": "ГРПШ-100"}]
    found = check_cross_facility_contamination(text, "котельная", equipment)
    assert len(found) == 0


def test_case_insensitive():
    """Check should be case-insensitive."""
    text = "проверить грпш"
    found = check_cross_facility_contamination(text, "котельная")
    assert "ГРПШ" in found


# --- RAG cross-facility filter tests ---


def test_rag_filters_contaminated_chunks():
    """RAG adapter should filter chunks with forbidden terms."""
    from src.application.services.pmla_rag_adapter import PmlaRagAdapter

    adapter = PmlaRagAdapter()
    ctx = adapter.get_context({"facility_type": "Котельная"}, "section_10")
    # Boiler RAG should not contain ГРПШ/ШРП terms
    for chunk in ctx.chunks:
        for term in ["ГРПШ", "ШРП", "газорегуляторный пункт"]:
            assert term.lower() not in chunk.text.lower(), (
                f"Boiler RAG chunk contains gas network term: {term}"
            )


def test_gas_network_rag_allows_gas_terms():
    """Gas network RAG should contain gas-specific terms."""
    from src.application.services.pmla_rag_adapter import PmlaRagAdapter

    adapter = PmlaRagAdapter()
    ctx = adapter.get_context({"facility_type": "Сеть газопотребления"}, "section_2")
    assert not ctx.is_empty
    assert len(ctx.chunks) > 0


# --- Quality review cross-facility check tests ---


def test_quality_review_warns_on_contamination():
    """Quality review should warn when cross-facility contamination detected."""
    from src.application.services.pmla_quality_review_service import PmlaQualityReviewService

    # Create a context that would have contamination
    ctx = {
        "facility": {"facility_type": "Котельная"},
        "facility_type": "Котельная",
    }
    svc = PmlaQualityReviewService()
    # Mock rendered sections with contaminated text
    rendered = {"section_10": "Первоочередные действия на ГРПШ и ШРП"}
    report = svc.review(ctx, rendered_sections=rendered)
    contamination_check = next(
        (c for c in report.checks if c.code == "cross_facility_contamination"),
        None,
    )
    assert contamination_check is not None
    assert contamination_check.status == "warning"


def test_quality_review_ok_for_clean_content():
    """Quality review should pass when content is clean."""
    from src.application.services.pmla_quality_review_service import PmlaQualityReviewService

    ctx = {
        "facility": {"facility_type": "Котельная"},
        "facility_type": "Котельная",
    }
    svc = PmlaQualityReviewService()
    rendered = {"section_10": "Первоочередные действия при аварии на котельной"}
    report = svc.review(ctx, rendered_sections=rendered)
    contamination_check = next(
        (c for c in report.checks if c.code == "cross_facility_contamination"),
        None,
    )
    assert contamination_check is not None
    assert contamination_check.status == "ok"


# --- Regression: boiler section_10 ---


def test_boiler_section_10_no_gas_network():
    """Boiler section_10 should not contain gas network scenarios."""
    from src.application.engines.rules_engine import RulesEngine
    from src.application.engines.base import DocumentContext
    import asyncio

    engine = RulesEngine()
    ctx = DocumentContext(
        organization={"name": "Test"},
        facility={"facility_type": "Котельная", "name": "Котельная"},
        equipment=[], substances=[], persons=[],
    )
    section_def = {"id": "section_10", "title": "Первоочередные действия"}
    result = asyncio.run(engine.generate("section_10", section_def, ctx))

    all_text = " ".join(b.text for b in result.blocks)
    for term in ["ГРПШ", "ШРП", "газорегуляторный пункт"]:
        assert term not in all_text, f"Boiler section_10 contains gas network term: {term}"


def test_boiler_unknown_type_uses_generic():
    """Unknown facility type should use generic first actions."""
    from src.application.engines.rules_engine import RulesEngine
    from src.application.engines.base import DocumentContext
    import asyncio

    engine = RulesEngine()
    ctx = DocumentContext(
        organization={"name": "Test"},
        facility={"facility_type": "Несуществующий тип", "name": "Test"},
        equipment=[], substances=[], persons=[],
    )
    section_def = {"id": "section_10", "title": "Первоочередные действия"}
    result = asyncio.run(engine.generate("section_10", section_def, ctx))

    all_text = " ".join(b.text for b in result.blocks)
    # Should contain generic actions, not gas network specific
    assert "диспетчеру" in all_text.lower() or "аварии" in all_text.lower()
    assert "ГРПШ" not in all_text
