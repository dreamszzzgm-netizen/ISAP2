"""Tests for RAG consumption in generated engines."""
import asyncio
import pytest

from src.application.engines.base import DocumentContext
from src.application.engines.blocks import ParagraphBlock


def _make_context_with_rag(facility_type="Сеть газопотребления"):
    """Create a DocumentContext with RAG context for testing."""
    return DocumentContext(
        organization={"name": "Test Org"},
        facility={"facility_type": facility_type, "name": "Test"},
        equipment=[],
        substances=[],
        persons=[],
        rag_contexts={
            "section_10": {
                "chunks": [
                    {"source_id": "rag1", "source_title": "Source 1", "text": "Текст из RAG для первых действий"},
                    {"source_id": "rag2", "source_title": "Source 2", "text": "Ещё один фрагмент из RAG"},
                ],
                "summary": "Текст из RAG для первых действий\n\nЕщё один фрагмент из RAG",
            },
            "section_2": {
                "chunks": [
                    {"source_id": "rag3", "source_title": "Source 3", "text": "Сценарии из RAG базы знаний"},
                ],
                "summary": "Сценарии из RAG базы знаний",
            },
        },
    )


def _make_context_without_rag():
    """Create a DocumentContext without RAG context."""
    return DocumentContext(
        organization={"name": "Test Org"},
        facility={"facility_type": "Сеть газопотребления", "name": "Test"},
        equipment=[],
        substances=[],
        persons=[],
    )


# --- RulesEngine RAG tests ---


def test_rules_engine_section_10_uses_rag():
    """RulesEngine section_10 should inject RAG context."""
    from src.application.engines.rules_engine import RulesEngine

    engine = RulesEngine()
    ctx = _make_context_with_rag()
    section_def = {"id": "section_10", "title": "Первоочередные действия"}

    result = asyncio.run(engine.generate("section_10", section_def, ctx))
    rag_used = result.metadata.get("rag_used", False)
    rag_count = result.metadata.get("rag_chunks_count", 0)

    assert rag_used, "RAG should be used for section_10"
    assert rag_count == 2, f"Expected 2 RAG chunks, got {rag_count}"
    # Check RAG text is in blocks
    all_text = " ".join(b.text for b in result.blocks if isinstance(b, ParagraphBlock))
    assert "RAG" in all_text or "rag" in all_text.lower() or "из RAG" in all_text


def test_rules_engine_section_10_without_rag():
    """RulesEngine section_10 should work without RAG context."""
    from src.application.engines.rules_engine import RulesEngine

    engine = RulesEngine()
    ctx = _make_context_without_rag()
    section_def = {"id": "section_10", "title": "Первоочередные действия"}

    result = asyncio.run(engine.generate("section_10", section_def, ctx))
    rag_used = result.metadata.get("rag_used", False)
    assert not rag_used, "RAG should not be used when context is empty"
    assert len(result.blocks) > 0


def test_rules_engine_section_5_uses_rag():
    """RulesEngine section_5 should inject RAG context if available."""
    from src.application.engines.rules_engine import RulesEngine

    engine = RulesEngine()
    ctx = _make_context_with_rag()
    ctx.rag_contexts["section_5"] = {
        "chunks": [{"source_id": "rag4", "source_title": "Source 4", "text": "Взаимодействие из RAG"}],
        "summary": "Взаимодействие из RAG",
    }
    section_def = {"id": "section_5", "title": "Взаимодействие"}

    result = asyncio.run(engine.generate("section_5", section_def, ctx))
    rag_used = result.metadata.get("rag_used", False)
    assert rag_used


# --- ScenarioEngine RAG tests ---


def test_scenario_engine_section_2_uses_rag():
    """ScenarioEngine section_2 should inject RAG context."""
    from src.application.engines.scenario_engine import ScenarioEngine

    engine = ScenarioEngine()
    ctx = _make_context_with_rag()
    section_def = {"id": "section_2", "title": "Сценарии"}

    result = asyncio.run(engine.generate("section_2", section_def, ctx))
    rag_used = result.metadata.get("rag_used", False)
    rag_count = result.metadata.get("rag_chunks_count", 0)

    assert rag_used, "RAG should be used for section_2"
    assert rag_count >= 1


def test_scenario_engine_without_rag():
    """ScenarioEngine should work without RAG context."""
    from src.application.engines.scenario_engine import ScenarioEngine

    engine = ScenarioEngine()
    ctx = _make_context_without_rag()
    section_def = {"id": "section_2", "title": "Сценарии"}

    result = asyncio.run(engine.generate("section_2", section_def, ctx))
    rag_used = result.metadata.get("rag_used", False)
    assert not rag_used


# --- NarrativeEngine RAG tests ---


def test_narrative_engine_uses_rag():
    """NarrativeEngine introduction should inject RAG context if available."""
    from src.application.engines.narrative_engine import NarrativeEngine

    engine = NarrativeEngine()
    ctx = _make_context_with_rag()
    ctx.rag_contexts["introduction"] = {
        "chunks": [{"source_id": "rag5", "source_title": "Source 5", "text": "Введение из RAG базы"}],
        "summary": "Введение из RAG базы",
    }
    section_def = {"id": "introduction", "title": "Введение"}

    result = asyncio.run(engine.generate("introduction", section_def, ctx))
    rag_used = result.metadata.get("rag_used", False)
    assert rag_used


# --- Static/variable blocks should NOT use RAG ---


def test_template_engine_does_not_use_rag():
    """TemplateEngine should not inject RAG context."""
    from src.application.engines.template_engine import TemplateEngine

    engine = TemplateEngine()
    ctx = _make_context_with_rag()
    section_def = {"id": "abbreviations", "title": "Обозначения", "template": "sections/00_abbreviations.j2"}

    result = asyncio.run(engine.generate("abbreviations", section_def, ctx))
    # TemplateEngine doesn't have rag_used in metadata
    assert "rag_used" not in result.metadata or not result.metadata.get("rag_used")


# --- RAG text sanitization ---


def test_rag_text_sanitized():
    """RAG text should be sanitized before injection."""
    from src.application.engines.rules_engine import RulesEngine

    engine = RulesEngine()
    ctx = DocumentContext(
        organization={"name": "Test"},
        facility={"facility_type": "Сеть газопотребления", "name": "Test"},
        equipment=[], substances=[], persons=[],
        rag_contexts={
            "section_10": {
                "chunks": [
                    {"source_id": "test", "source_title": "Test", "text": "Текст <b>с HTML</b> и 热画像 китайскими символами"},
                ],
                "summary": "",
            },
        },
    )
    section_def = {"id": "section_10", "title": "Действия"}
    result = asyncio.run(engine.generate("section_10", section_def, ctx))

    all_text = " ".join(b.text for b in result.blocks if isinstance(b, ParagraphBlock))
    assert "<b>" not in all_text, "HTML should be stripped"
    assert "熱画像" not in all_text, "Chinese should be sanitized"


# --- RAG limits ---


def test_rag_limits_chunks():
    """RAG should limit injected chunks to max_chunks (3)."""
    from src.application.engines.rules_engine import RulesEngine

    engine = RulesEngine()
    chunks = [
        {"source_id": f"r{i}", "source_title": f"Source {i}", "text": f"Chunk {i} text content"}
        for i in range(10)
    ]
    ctx = DocumentContext(
        organization={"name": "Test"},
        facility={"facility_type": "Сеть газопотребления", "name": "Test"},
        equipment=[], substances=[], persons=[],
        rag_contexts={"section_10": {"chunks": chunks, "summary": ""}},
    )
    section_def = {"id": "section_10", "title": "Действия"}
    result = asyncio.run(engine.generate("section_10", section_def, ctx))

    # Count RAG-injected paragraphs (they appear after the original rules content)
    all_text = " ".join(b.text for b in result.blocks if isinstance(b, ParagraphBlock))
    rag_paras = [b.text for b in result.blocks if isinstance(b, ParagraphBlock) and "Chunk" in b.text]
    assert len(rag_paras) <= 3, f"RAG paragraphs should be limited to 3, got {len(rag_paras)}"


# --- Integration with enriched context ---


def test_enriched_context_provides_rag_to_engines():
    """Enriched context should provide RAG to engine generate methods."""
    from src.application.services.enhanced_generator import EnhancedDocumentGenerator

    gen = EnhancedDocumentGenerator.__new__(EnhancedDocumentGenerator)
    raw_ctx = {
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
    enriched = gen._enrich_context(raw_ctx, scenarios=[], calculations=[])

    rag = enriched.get("rag_contexts", {})
    assert len(rag) > 0, "RAG contexts should be populated"
    assert "section_10" in rag, "section_10 should have RAG context"
