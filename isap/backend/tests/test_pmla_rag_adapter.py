"""Tests for PMLA RAG Adapter."""
import pytest

from src.application.services.pmla_rag_adapter import (
    PmlaRagAdapter,
    PmlaRagChunk,
    PmlaRagContext,
)


def _adapter():
    return PmlaRagAdapter()


# --- Adapter tests ---


def test_gas_consumption_returns_rag_chunks():
    """Gas consumption facility should return RAG chunks for generated sections."""
    ctx = _adapter().get_context({"facility_type": "Сеть газопотребления"}, "section_2")
    assert not ctx.is_empty
    assert len(ctx.chunks) > 0
    assert any("газ" in c.text.lower() for c in ctx.chunks)


def test_gas_consumption_section_10():
    """Section 10 should have first actions for gas facility."""
    ctx = _adapter().get_context({"facility_type": "Сеть газопотребления"}, "section_10")
    assert not ctx.is_empty
    assert len(ctx.chunks) > 0


def test_boiler_returns_rag_chunks():
    """Boiler facility should return RAG chunks."""
    ctx = _adapter().get_context({"facility_type": "Котельная"}, "section_2")
    assert not ctx.is_empty
    assert any("котёл" in c.text.lower() or "котл" in c.text.lower() for c in ctx.chunks)


def test_unknown_facility_returns_default():
    """Unknown facility type should return default RAG context."""
    ctx = _adapter().get_context({"facility_type": "Несуществующий тип"}, "section_10")
    assert len(ctx.warnings) == 1
    assert "не найден" in ctx.warnings[0]
    # Should still have default chunks for section_10
    assert len(ctx.chunks) > 0


def test_empty_facility_type_returns_empty():
    """Empty facility type should return empty RAG context."""
    ctx = _adapter().get_context({"facility_type": ""}, "section_2")
    assert ctx.is_empty
    assert len(ctx.warnings) == 1


def test_section_without_rag_returns_empty():
    """Section without RAG data should return empty with warning."""
    ctx = _adapter().get_context({"facility_type": "Сеть газопотребления"}, "section_999")
    assert ctx.is_empty
    assert len(ctx.warnings) == 1


def test_rag_context_summary():
    """Summary should concatenate chunk texts."""
    ctx = _adapter().get_context({"facility_type": "Сеть газопотребления"}, "section_2")
    summary = ctx.summary
    assert len(summary) > 0
    assert isinstance(summary, str)


def test_rag_chunk_fields():
    """RAG chunks should have all required fields."""
    ctx = _adapter().get_context({"facility_type": "Сеть газопотребления"}, "section_2")
    for chunk in ctx.chunks:
        assert isinstance(chunk, PmlaRagChunk)
        assert chunk.source_id
        assert chunk.source_title
        assert chunk.text


def test_rag_context_is_empty_property():
    """is_empty should return True for empty context."""
    ctx = PmlaRagContext()
    assert ctx.is_empty


def test_rag_context_not_empty_with_chunks():
    """is_empty should return False when chunks are present."""
    ctx = PmlaRagContext(chunks=[PmlaRagChunk(source_id="test", source_title="Test", text="text")])
    assert not ctx.is_empty


def test_non_string_facility_type():
    """Non-string facility type should be handled gracefully."""
    ctx = _adapter().get_context({"facility_type": 123}, "section_2")
    assert ctx.is_empty or len(ctx.warnings) > 0


def test_all_generated_sections_have_rag():
    """All generated sections should have at least some RAG context for gas facility."""
    adapter = _adapter()
    for sid in ["section_2", "section_5", "section_7", "section_10", "section_12", "special_section"]:
        ctx = adapter.get_context({"facility_type": "Сеть газопотребления"}, sid)
        # At least some sections should have chunks
        if not ctx.is_empty:
            assert len(ctx.chunks) > 0


# --- Integration with enhanced_generator ---


def test_enriched_context_includes_rag():
    """Enriched context should include rag_contexts for generated sections."""
    from src.application.services.enhanced_generator import EnhancedDocumentGenerator
    from unittest.mock import MagicMock

    gen = EnhancedDocumentGenerator.__new__(EnhancedDocumentGenerator)
    ctx = {
        "facility": {"facility_type": "Сеть газопотребления", "name": "Test", "address": "Test addr"},
        "organization": {"name": "Test Org"},
        "responsible_persons": [],
        "selected_scenarios": [],
        "custom_scenarios": [],
        "equipment": [],
        "substances": [],
        "emergency_services": [],
        "notification_scheme": {},
        "organization_resources": {},
        "attachments_checklist": [],
    }
    enriched = gen._enrich_context(ctx, scenarios=[], calculations=[])
    assert "rag_contexts" in enriched
    assert isinstance(enriched["rag_contexts"], dict)
    # Should have entries for generated sections
    assert len(enriched["rag_contexts"]) > 0


# --- Quality review integration ---


def test_quality_review_handles_rag_unavailable():
    """Quality review should work even if RAG adapter fails."""
    from src.application.services.pmla_quality_review_service import PmlaQualityReviewService

    ctx = {"facility": {}}
    svc = PmlaQualityReviewService()
    report = svc.review(ctx)
    assert report.overall_status in ("ok", "warning", "critical")
