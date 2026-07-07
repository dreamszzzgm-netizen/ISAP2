"""Tests for ScenarioEngine — детерминированная генерация сценариев."""
import pytest

from src.application.engines.base import DocumentContext
from src.application.engines.scenario_engine import (
    SCENARIO_SECTIONS,
    ScenarioEngine,
    _load_scenario_templates,
)


@pytest.fixture
def engine():
    return ScenarioEngine()


@pytest.fixture
def gas_network_context():
    """Контекст для сети газопотребления — совпадает с эталонным документом."""
    return DocumentContext(
        organization={"name": "ООО «СПК ААА»", "inn": "7700000001"},
        facility={
            "name": "Сеть газопотребления",
            "reg_number": "А34-00000-0001",
            "hazard_class": "3",
            "facility_type": "Сеть газопотребления",
            "address": "г. Тюмень, ул. Промышленная, д. 10",
        },
        equipment=[
            {"name": "ГРПШ-1", "equipment_type": "Газораспределительный пункт"},
            {"name": "Газопровод Ду100", "equipment_type": "Газопровод"},
            {"name": "Регулятор давления", "equipment_type": "Регулятор"},
            {"name": "Запорная арматура", "equipment_type": "Клапан"},
            {"name": "Газовый кран", "equipment_type": "Кран"},
        ],
        substances=[
            {"name": "Природный газ", "quantity_kg": 500, "cas_number": "74-82-8"},
        ],
        persons=[
            {"full_name": "Иванов И.И.", "position": "Диспетчер", "role": "dispatcher", "phone": "+7-999-111-22-33"},
        ],
    )


@pytest.fixture
def unknown_type_context():
    """Контекст с неизвестным типом ОПО."""
    return DocumentContext(
        organization={"name": "Тест"},
        facility={
            "name": "Неизвестный объект",
            "facility_type": "Неизвестный тип",
            "hazard_class": "3",
        },
        equipment=[],
        substances=[],
        persons=[],
    )


class TestScenarioEngineCanHandle:
    def test_handles_section_2(self, engine):
        assert engine.can_handle("section_2")

    def test_handles_special_section(self, engine):
        assert engine.can_handle("special_section")

    def test_does_not_handle_other_sections(self, engine):
        for sid in ["title_page", "section_1", "section_3", "introduction", "appendix_1"]:
            assert not engine.can_handle(sid)


class TestLoadScenarioTemplates:
    def test_loads_gas_network_template(self):
        template = _load_scenario_templates("Сеть газопотребления")
        assert template is not None
        assert template["facility_type"] == "Сеть газопотребления"
        assert len(template["scenarios"]) == 5

    def test_returns_none_for_unknown_type(self):
        template = _load_scenario_templates("Неизвестный тип")
        assert template is None


@pytest.mark.asyncio
class TestScenarioEngineGenerate:
    @pytest.mark.asyncio
    async def test_section_2_renders_all_scenarios(self, engine, gas_network_context):
        section_def = {"id": "section_2", "title": "2. Сценарии аварий"}
        result = await engine.generate("section_2", section_def, gas_network_context)

        assert result.section_id == "section_2"
        assert result.engine_name == "scenario"
        assert "С-1" in result.content
        assert "С-5" in result.content
        assert "Выброс газа" in result.content
        assert result.metadata["scenario_count"] == 5

    @pytest.mark.asyncio
    async def test_section_2_contains_table_4(self, engine, gas_network_context):
        section_def = {"id": "section_2", "title": "2. Сценарии аварий"}
        result = await engine.generate("section_2", section_def, gas_network_context)

        assert "Таблица 4" in result.content
        assert "Элемент оборудования" in result.content

    @pytest.mark.asyncio
    async def test_section_2_contains_table_5(self, engine, gas_network_context):
        section_def = {"id": "section_2", "title": "2. Сценарии аварий"}
        result = await engine.generate("section_2", section_def, gas_network_context)

        assert "Таблица 5" in result.content
        assert "источник" in result.content.lower()

    @pytest.mark.asyncio
    async def test_section_2_contains_table_6(self, engine, gas_network_context):
        section_def = {"id": "section_2", "title": "2. Сценарии аварий"}
        result = await engine.generate("section_2", section_def, gas_network_context)

        assert "Таблица 6" in result.content
        assert "Наименование сценария" in result.content

    @pytest.mark.asyncio
    async def test_section_2_contains_block_schemas(self, engine, gas_network_context):
        section_def = {"id": "section_2", "title": "2. Сценарии аварий"}
        result = await engine.generate("section_2", section_def, gas_network_context)

        assert "СХЕМА ВОЗНИКНОВЕНИЯ" in result.content
        assert "Этап 1" in result.content
        assert "Этап 7" in result.content

    @pytest.mark.asyncio
    async def test_special_section_renders_table_15(self, engine, gas_network_context):
        section_def = {"id": "special_section", "title": "Специальный раздел"}
        result = await engine.generate("special_section", section_def, gas_network_context)

        assert result.section_id == "special_section"
        assert "Таблица 15" in result.content
        assert "Опознавательные признаки" in result.content

    @pytest.mark.asyncio
    async def test_special_section_has_all_scenarios(self, engine, gas_network_context):
        section_def = {"id": "special_section", "title": "Специальный раздел"}
        result = await engine.generate("special_section", section_def, gas_network_context)

        for i in range(1, 6):
            assert f"С-{i}" in result.content

    @pytest.mark.asyncio
    async def test_special_section_has_detailed_actions(self, engine, gas_network_context):
        section_def = {"id": "special_section", "title": "Специальный раздел"}
        result = await engine.generate("special_section", section_def, gas_network_context)

        assert "Перекрытие газа" in result.content
        assert "Диспетчер" in result.content
        assert "Эвакуация" in result.content

    @pytest.mark.asyncio
    async def test_unknown_facility_type_returns_error(self, engine, unknown_type_context):
        section_def = {"id": "section_2", "title": "2. Сценарии аварий"}
        result = await engine.generate("section_2", section_def, unknown_type_context)

        assert "Шаблон сценариев не найден" in result.content

    @pytest.mark.asyncio
    async def test_unknown_facility_type_uses_questionnaire_scenarios(self, engine, unknown_type_context):
        unknown_type_context.scenarios = [{"title": "Custom valve failure", "source_equipment": "Valve"}]
        section_def = {"id": "section_2", "title": "2. РЎС†РµРЅР°СЂРёРё Р°РІР°СЂРёР№"}
        result = await engine.generate("section_2", section_def, unknown_type_context)

        assert "Custom valve failure" in result.content
        assert "Valve" in result.content

    @pytest.mark.asyncio
    async def test_no_pii_in_output(self, engine, gas_network_context):
        """Проверяет, что персональные данные не попадают в сценарии."""
        section_def = {"id": "section_2", "title": "2. Сценарии аварий"}
        result = await engine.generate("section_2", section_def, gas_network_context)

        assert "Иванов" not in result.content


class TestScenarioTemplatesAllTypes:
    """Тесты для всех типов ОПО с шаблонами сценариев."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("facility_type,expected_scenarios", [
        ("Сеть газопотребления", ["С-1", "С-2", "С-3", "С-4", "С-5"]),
        ("Нефтедобыча", ["НД-1", "НД-2", "НД-3"]),
        ("Нефтепереработка", ["НП-1", "НП-2", "НП-3"]),
        ("Химическое производство", ["ХП-1", "ХП-2"]),
        ("Газораспределение", ["ГР-1", "ГР-2"]),
        ("Транспортировка", ["ТР-1", "ТР-2"]),
    ])
    async def test_facility_type_has_scenarios(self, engine, facility_type, expected_scenarios):
        ctx = DocumentContext(
            organization={"name": "Тест"},
            facility={"name": "Объект", "facility_type": facility_type, "hazard_class": "3"},
            equipment=[], substances=[], persons=[],
        )
        section_def = {"id": "section_2", "title": "2. Сценарии аварий"}
        result = await engine.generate("section_2", section_def, ctx)

        for code in expected_scenarios:
            assert code in result.content, f"Scenario {code} not found for {facility_type}"

    def test_all_templates_loaded(self):
        from src.application.engines.scenario_engine import _load_scenario_templates

        types = [
            "Сеть газопотребления",
            "Нефтедобыча",
            "Нефтепереработка",
            "Химическое производство",
            "Газораспределение",
            "Транспортировка",
        ]
        for ft in types:
            template = _load_scenario_templates(ft)
            assert template is not None, f"No template for {ft}"
            assert len(template["scenarios"]) >= 2, f"Too few scenarios for {ft}"
