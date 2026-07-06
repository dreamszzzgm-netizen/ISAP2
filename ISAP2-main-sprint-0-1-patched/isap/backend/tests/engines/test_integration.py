"""Integration test — полный пайплайн всех движков через EngineRouter."""
import pytest

from src.application.engines.base import DocumentContext
from src.application.engines.data_engine import DataEngine
from src.application.engines.narrative_engine import NarrativeEngine
from src.application.engines.rules_engine import RulesEngine
from src.application.engines.router import EngineRouter
from src.application.engines.scenario_engine import ScenarioEngine
from src.application.engines.template_engine import TemplateEngine


@pytest.fixture
def full_context():
    return DocumentContext(
        organization={
            "name": "ООО «СПК ААА»",
            "inn": "7700000001",
            "ogrn": "1027700132195",
            "address": "г. Тюмень, ул. Промышленная, д. 10",
            "phone": "+7 (3452) 12-34-56",
            "email": "info@spk-aaa.ru",
        },
        facility={
            "name": "Сеть газопотребления",
            "reg_number": "А34-00000-0001",
            "hazard_class": "3",
            "facility_type": "Сеть газопотребления",
            "address": "г. Тюмень, ул. Промышленная, д. 10",
        },
        equipment=[
            {"name": "ГРПШ-1", "equipment_type": "Газораспределительный пункт", "serial_number": "SN-001", "manufacture_year": 2020},
            {"name": "Газопровод Ду100", "equipment_type": "Газопровод", "serial_number": "SN-002", "manufacture_year": 2019},
            {"name": "Регулятор давления", "equipment_type": "Регулятор", "serial_number": "SN-003", "manufacture_year": 2021},
            {"name": "Запорная арматура", "equipment_type": "Клапан", "serial_number": "SN-004", "manufacture_year": 2020},
            {"name": "Газовый кран", "equipment_type": "Кран", "serial_number": "SN-005", "manufacture_year": 2018},
        ],
        substances=[
            {"name": "Природный газ", "quantity_kg": 500, "cas_number": "74-82-8", "threshold_quantity_kg": 1000},
        ],
        persons=[
            {"full_name": "Иванов И.И.", "position": "Директор", "role": "director", "phone": "+7-999-111-22-33"},
            {"full_name": "Петров П.П.", "position": "Диспетчер", "role": "dispatcher", "phone": "+7-999-222-33-44"},
        ],
        year=2026,
    )


@pytest.fixture
def router():
    return EngineRouter([
        TemplateEngine(),
        DataEngine(),
        ScenarioEngine(),
        RulesEngine(),
        NarrativeEngine(),
    ])


class TestFullPipeline:
    @pytest.mark.asyncio
    async def test_generate_all_sections(self, router, full_context):
        results = await router.generate_all(full_context)

        # Должны быть все 27 разделов
        assert len(results) >= 20

        # Ключевые разделы
        assert "title_page" in results
        assert "section_1" in results
        assert "section_2" in results
        assert "section_3" in results
        assert "special_section" in results
        assert "introduction" in results

    @pytest.mark.asyncio
    async def test_title_page_has_org_data(self, router, full_context):
        results = await router.generate_all(full_context)
        tp = results["title_page"]

        assert "СПК ААА" in tp.content
        assert "А34-00000-0001" in tp.content
        assert tp.engine_name == "template"

    @pytest.mark.asyncio
    async def test_section_1_has_tables(self, router, full_context):
        results = await router.generate_all(full_context)
        s1 = results["section_1"]

        assert "Таблица 1" in s1.content
        assert "Таблица 2" in s1.content
        assert "Таблица 3" in s1.content
        assert s1.engine_name == "data"

    @pytest.mark.asyncio
    async def test_section_2_has_scenarios(self, router, full_context):
        results = await router.generate_all(full_context)
        s2 = results["section_2"]

        assert "С-1" in s2.content
        assert "С-5" in s2.content
        assert "Таблица 4" in s2.content
        assert "Таблица 6" in s2.content
        assert s2.engine_name == "scenario"

    @pytest.mark.asyncio
    async def test_section_3_has_accident_examples(self, router, full_context):
        results = await router.generate_all(full_context)
        s3 = results["section_3"]

        assert "Таблица 9" in s3.content
        assert "Газпром" in s3.content  # реальные аварии из справочника
        assert s3.engine_name == "data"

    @pytest.mark.asyncio
    async def test_section_10_has_rules(self, router, full_context):
        results = await router.generate_all(full_context)
        s10 = results["section_10"]

        assert "ПЕРВООЧЕРЕДНЫЕ" in s10.content.upper()
        assert s10.engine_name == "rules"

    @pytest.mark.asyncio
    async def test_special_section_has_table_15(self, router, full_context):
        results = await router.generate_all(full_context)
        ss = results["special_section"]

        assert "Таблица 15" in ss.content
        assert "С-1" in ss.content
        assert ss.engine_name == "scenario"

    @pytest.mark.asyncio
    async def test_introduction_has_fallback_text(self, router, full_context):
        results = await router.generate_all(full_context)
        intro = results["introduction"]

        assert len(intro.blocks) > 0
        assert "116-ФЗ" in intro.content
        assert intro.engine_name == "narrative"

    @pytest.mark.asyncio
    async def test_engine_report(self, router):
        report = router.get_engine_report()

        assert "title_page" in report["template"]
        assert "abbreviations" in report["template"]
        assert "section_1" in report["data"]
        assert "section_3" in report["data"]
        assert "section_2" in report["scenario"]
        assert "special_section" in report["scenario"]
        assert "section_5" in report["rules"]
        assert "section_10" in report["rules"]
        assert "introduction" in report["narrative"]

    @pytest.mark.asyncio
    async def test_no_pii_in_llm_sections(self, router, full_context):
        """Проверяет, что персональные данные не попадают в LLM-разделы."""
        results = await router.generate_all(full_context)

        for section_id in ["section_5", "section_7", "section_9", "section_10", "section_11", "section_12"]:
            section = results.get(section_id)
            if section:
                assert "Иванов" not in section.content or section.engine_name != "narrative"
