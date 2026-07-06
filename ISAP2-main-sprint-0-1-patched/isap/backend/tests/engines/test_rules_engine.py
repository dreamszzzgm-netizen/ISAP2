"""Tests for RulesEngine — параметризованные шаблоны правил."""
import pytest

from src.application.engines.base import DocumentContext
from src.application.engines.rules_engine import RULES_SECTIONS, RulesEngine


@pytest.fixture
def engine():
    return RulesEngine()


@pytest.fixture
def gas_network_context():
    return DocumentContext(
        organization={"name": "ООО «СПК ААА»"},
        facility={
            "name": "Сеть газопотребления",
            "facility_type": "Сеть газопотребления",
            "hazard_class": "3",
            "address": "г. Тюмень",
        },
        equipment=[],
        substances=[],
        persons=[
            {"full_name": "Иванов И.И.", "position": "Директор", "role": "director", "phone": "+7-999-111-22-33"},
        ],
    )


@pytest.fixture
def unknown_type_context():
    return DocumentContext(
        organization={"name": "Тест"},
        facility={"name": "Объект", "facility_type": "Неизвестный тип", "hazard_class": "3"},
        equipment=[], substances=[], persons=[],
    )


class TestRulesEngineCanHandle:
    def test_handles_all_rules_sections(self, engine):
        for sid in RULES_SECTIONS:
            assert engine.can_handle(sid), f"RulesEngine should handle '{sid}'"

    def test_does_not_handle_other_sections(self, engine):
        for sid in ["title_page", "section_1", "section_2", "section_3", "special_section"]:
            assert not engine.can_handle(sid)


@pytest.mark.asyncio
class TestRulesEngineGasNetwork:
    async def test_section_5_interaction(self, engine, gas_network_context):
        result = await engine.generate("section_5", {"id": "section_5", "title": "5. Взаимодействие"}, gas_network_context)

        assert "ВЗАИМОДЕЙСТВИЕ" in result.content.upper()
        assert "единоначалие" in result.content.lower()
        assert "газопотребления" in result.content.lower()

    async def test_section_7_readiness(self, engine, gas_network_context):
        result = await engine.generate("section_7", {"id": "section_7", "title": "7. Готовность"}, gas_network_context)

        assert "ГОТОВНОСТЬ" in result.content.upper()
        assert "тренировк" in result.content.lower()

    async def test_section_9_information_exchange(self, engine, gas_network_context):
        result = await engine.generate("section_9", {"id": "section_9", "title": "9. Обмен информацией"}, gas_network_context)

        assert "ОБМЕН" in result.content.upper()
        assert "диспетчерская" in result.content.lower()

    async def test_section_10_initial_actions(self, engine, gas_network_context):
        result = await engine.generate("section_10", {"id": "section_10", "title": "10. Первоочередные действия"}, gas_network_context)

        assert "ПЕРВООЧЕРЕДНЫЕ" in result.content.upper()
        assert "утечк" in result.content.lower()
        assert "Иванов И.И." in result.content

    async def test_section_11_personnel_actions(self, engine, gas_network_context):
        result = await engine.generate("section_11", {"id": "section_11", "title": "11. Действия персонала"}, gas_network_context)

        assert "ДЕЙСТВИЯ" in result.content.upper()
        assert "Диспетчер" in result.content

    async def test_section_12_population_safety(self, engine, gas_network_context):
        result = await engine.generate("section_12", {"id": "section_12", "title": "12. Безопасность населения"}, gas_network_context)

        assert "БЕЗОПАСНОСТИ" in result.content.upper()
        assert "оповещени" in result.content.lower()


@pytest.mark.asyncio
class TestRulesEngineDefaultRules:
    async def test_unknown_type_uses_defaults(self, engine, unknown_type_context):
        result = await engine.generate("section_5", {"id": "section_5", "title": "5. Взаимодействие"}, unknown_type_context)

        assert result.engine_name == "rules"
        assert "единоначалие" in result.content.lower()

    async def test_all_sections_render_for_unknown_type(self, engine, unknown_type_context):
        for sid in RULES_SECTIONS:
            result = await engine.generate(sid, {"id": sid, "title": sid}, unknown_type_context)
            assert len(result.content) > 50, f"Section {sid} too short"
            assert result.engine_name == "rules"
