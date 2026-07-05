"""Tests for NarrativeEngine — AI-движок для описательного текста."""
import pytest

from src.application.engines.base import DocumentContext
from src.application.engines.narrative_engine import NARRATIVE_SECTIONS, NarrativeEngine


@pytest.fixture
def engine():
    return NarrativeEngine()


@pytest.fixture
def sample_context():
    return DocumentContext(
        organization={"name": "ООО «СПК ААА»"},
        facility={
            "name": "Сеть газопотребления",
            "facility_type": "Сеть газопотребления",
            "hazard_class": "3",
            "address": "г. Тюмень, ул. Промышленная, д. 10",
        },
        equipment=[], substances=[], persons=[], year=2026,
    )


class TestNarrativeEngineCanHandle:
    def test_handles_introduction(self, engine):
        assert engine.can_handle("introduction")

    def test_does_not_handle_other_sections(self, engine):
        for sid in ["title_page", "section_1", "section_2", "section_5", "special_section"]:
            assert not engine.can_handle(sid)


@pytest.mark.asyncio
class TestNarrativeEngineGenerate:
    async def test_introduction_fallback(self, engine, sample_context):
        result = await engine.generate("introduction", {"id": "introduction", "title": "Введение"}, sample_context)

        assert result.section_id == "introduction"
        assert result.engine_name == "narrative"
        assert len(result.blocks) > 0
        assert "СПК ААА" in result.content
        assert "116-ФЗ" in result.content
        assert "1437" in result.content

    async def test_introduction_contains_regulatory_base(self, engine, sample_context):
        result = await engine.generate("introduction", {"id": "introduction", "title": "Введение"}, sample_context)

        assert "116-ФЗ" in result.content
        assert "1437" in result.content
        assert "472" in result.content

    async def test_introduction_contains_goals(self, engine, sample_context):
        result = await engine.generate("introduction", {"id": "introduction", "title": "Введение"}, sample_context)

        assert "Цель" in result.content
        assert "задач" in result.content.lower()

    async def test_no_llm_returns_fallback(self, engine, sample_context):
        """Проверяет, что без LLM используется fallback."""
        result = await engine.generate("introduction", {"id": "introduction", "title": "Введение"}, sample_context)
        assert result.metadata["source"] == "fallback"
