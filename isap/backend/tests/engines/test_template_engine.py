"""Tests for TemplateEngine — чистые Jinja2-шаблоны."""
import pytest

from src.application.engines.base import DocumentContext
from src.application.engines.template_engine import TEMPLATE_SECTIONS, TemplateEngine


@pytest.fixture
def engine():
    return TemplateEngine()


@pytest.fixture
def sample_context():
    return DocumentContext(
        organization={
            "name": "ООО «ТестОрганизация»",
            "inn": "7700000001",
            "address": "г. Москва, ул. Тестовая, д. 1",
        },
        facility={
            "name": "Газораспределительная станция",
            "reg_number": "А34-00000-0001",
            "hazard_class": "3",
            "facility_type": "Сеть газопотребления",
            "address": "г. Тюмень, ул. Промышленная, д. 10",
        },
        equipment=[
            {"name": "ГРПШ-1", "equipment_type": "Газораспределительный пункт", "serial_number": "SN-001"},
        ],
        substances=[
            {"name": "Природный газ", "quantity_kg": 500, "cas_number": "74-82-8"},
        ],
        persons=[
            {"full_name": "Иванов И.И.", "position": "Директор", "role": "director", "phone": "+7-999-111-22-33"},
        ],
    )


class TestTemplateEngineCanHandle:
    def test_handles_all_template_sections(self, engine):
        for section_id in TEMPLATE_SECTIONS:
            assert engine.can_handle(section_id), f"TemplateEngine should handle '{section_id}'"

    def test_does_not_handle_llm_sections(self, engine):
        llm_sections = ["introduction", "section_5", "section_7", "section_9", "section_10", "section_12"]
        for section_id in llm_sections:
            assert not engine.can_handle(section_id), f"TemplateEngine should NOT handle '{section_id}'"

    def test_does_not_handle_data_sections_needing_calc(self, engine):
        # Разделы, которые обрабатываются DataEngine, не TemplateEngine
        data_sections = ["section_1", "section_3", "section_4", "section_6", "section_8", "section_13"]
        for section_id in data_sections:
            assert not engine.can_handle(section_id), f"TemplateEngine should NOT handle '{section_id}'"


@pytest.mark.asyncio
class TestTemplateEngineGenerate:
    @pytest.mark.asyncio
    async def test_render_title_page(self, engine, sample_context):
        section_def = {"id": "title_page", "title": "Титульный лист", "template": "sections/00_title_page.j2"}
        result = await engine.generate("title_page", section_def, sample_context)

        assert result.section_id == "title_page"
        assert result.engine_name == "template"
        assert "ТестОрганизация" in result.content
        assert "А34-00000-0001" in result.content
        assert "Газораспределительная станция" in result.content

    @pytest.mark.asyncio
    async def test_render_abbreviations(self, engine, sample_context):
        section_def = {"id": "abbreviations", "title": "Обозначения", "template": "sections/00_abbreviations.j2"}
        result = await engine.generate("abbreviations", section_def, sample_context)

        assert result.section_id == "abbreviations"
        assert "АСФ" in result.content
        assert "ОПО" in result.content
        assert "ПМЛА" in result.content

    @pytest.mark.asyncio
    async def test_render_bibliography(self, engine, sample_context):
        section_def = {"id": "bibliography", "title": "Список литературы", "template": "sections/40_bibliography.j2"}
        result = await engine.generate("bibliography", section_def, sample_context)

        assert result.section_id == "bibliography"
        assert "116-ФЗ" in result.content
        assert "1437" in result.content

    @pytest.mark.asyncio
    async def test_render_terms(self, engine, sample_context):
        section_def = {"id": "terms", "title": "Термины", "template": "sections/00_terms.j2"}
        result = await engine.generate("terms", section_def, sample_context)

        assert result.section_id == "terms"
        assert len(result.content) > 100  # Должен содержать термины

    @pytest.mark.asyncio
    async def test_missing_template_returns_error(self, engine, sample_context):
        section_def = {"id": "title_page", "title": "Титульный лист", "template": ""}
        result = await engine.generate("title_page", section_def, sample_context)

        assert "Шаблон не указан" in result.content

    @pytest.mark.asyncio
    async def test_nonexistent_template_returns_error(self, engine, sample_context):
        section_def = {"id": "title_page", "title": "Титульный лист", "template": "sections/99_nonexistent.j2"}
        result = await engine.generate("title_page", section_def, sample_context)

        assert "Ошибка рендеринга" in result.content

    @pytest.mark.asyncio
    async def test_none_values_rendered_as_empty(self, engine):
        """Проверяет, что undefined-поля отображаются как прочерк."""
        ctx = DocumentContext(
            organization={"name": "Тест"},
            facility={"name": "Объект"},
            equipment=[],
            substances=[],
            persons=[],
        )
        section_def = {"id": "title_page", "title": "Титульный лист", "template": "sections/00_title_page.j2"}
        result = await engine.generate("title_page", section_def, ctx)

        assert "Тест" in result.content
        assert "Объект" in result.content
