"""Tests for DataEngine — сборка данных из карточки ОПО."""
import pytest

from src.application.engines.base import DocumentContext
from src.application.engines.data_engine import ACCIDENT_SAMPLES, DATA_SECTIONS, DataEngine


@pytest.fixture
def engine():
    return DataEngine()


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


class TestDataEngineCanHandle:
    def test_handles_all_data_sections(self, engine):
        for sid in DATA_SECTIONS:
            assert engine.can_handle(sid), f"DataEngine should handle '{sid}'"

    def test_does_not_handle_other_sections(self, engine):
        for sid in ["title_page", "section_2", "special_section", "introduction", "section_5"]:
            assert not engine.can_handle(sid)


@pytest.mark.asyncio
class TestDataEngineSection1:
    async def test_section_1_renders_org_info(self, engine, full_context):
        section_def = {"id": "section_1", "title": "1. Характеристика ОПО"}
        result = await engine.generate("section_1", section_def, full_context)

        assert "ООО «СПК ААА»" in result.content
        assert "7700000001" in result.content
        assert "А34-00000-0001" in result.content

    async def test_section_1_renders_equipment_table(self, engine, full_context):
        section_def = {"id": "section_1", "title": "1. Характеристика ОПО"}
        result = await engine.generate("section_1", section_def, full_context)

        assert "ГРПШ-1" in result.content
        assert "Газопровод" in result.content
        assert "Таблица 2" in result.content

    async def test_section_1_renders_substances_table(self, engine, full_context):
        section_def = {"id": "section_1", "title": "1. Характеристика ОПО"}
        result = await engine.generate("section_1", section_def, full_context)

        assert "Природный газ" in result.content
        assert "74-82-8" in result.content
        assert "Таблица 3" in result.content

    async def test_section_1_empty_data(self, engine):
        ctx = DocumentContext(
            organization={},
            facility={},
            equipment=[],
            substances=[],
            persons=[],
        )
        section_def = {"id": "section_1", "title": "1. Характеристика ОПО"}
        result = await engine.generate("section_1", section_def, ctx)

        assert "не предоставлены" in result.content


@pytest.mark.asyncio
class TestDataEngineSection3:
    async def test_section_3_renders_accident_history(self, engine, full_context):
        section_def = {"id": "section_3", "title": "3. Аварийность"}
        result = await engine.generate("section_3", section_def, full_context)

        assert "Таблица 7" in result.content
        assert "Таблица 8" in result.content
        assert "Таблица 9" in result.content

    async def test_section_3_has_real_accidents(self, engine, full_context):
        section_def = {"id": "section_3", "title": "3. Аварийность"}
        result = await engine.generate("section_3", section_def, full_context)

        assert "Пермская сетевая компания" in result.content
        assert "20.01.2020" in result.content

    async def test_accident_samples_count(self):
        assert len(ACCIDENT_SAMPLES) == 9


@pytest.mark.asyncio
class TestDataEngineSection4:
    async def test_section_4_renders_resources(self, engine, full_context):
        section_def = {"id": "section_4", "title": "4. Силы и средства"}
        result = await engine.generate("section_4", section_def, full_context)

        assert "Таблица 10" in result.content
        assert "СИЗОД" in result.content
        assert "Газоанализатор" in result.content


    async def test_section_4_renders_questionnaire_resources(self, engine, full_context):
        full_context.protective_equipment = [{"name": "Portable extinguisher", "quantity": "4", "storage_place": "boiler room"}]
        section_def = {"id": "section_4", "title": "4. РЎРёР»С‹ Рё СЃСЂРµРґСЃС‚РІР°"}
        result = await engine.generate("section_4", section_def, full_context)

        assert "Portable extinguisher" in result.content
        assert "boiler room" in result.content


class TestDataEngineSection6:
    async def test_section_6_renders_composition(self, engine, full_context):
        section_def = {"id": "section_6", "title": "6. Состав и дислокация"}
        result = await engine.generate("section_6", section_def, full_context)

        assert "Таблица 11" in result.content
        assert "Таблица 12" in result.content
        assert "Таблица 13" in result.content

    async def test_section_6_has_persons(self, engine, full_context):
        section_def = {"id": "section_6", "title": "6. Состав и дислокация"}
        result = await engine.generate("section_6", section_def, full_context)

        assert "Иванов И.И." in result.content
        assert "Петров П.П." in result.content


@pytest.mark.asyncio
class TestDataEngineSection8:
    async def test_section_8_renders_notification_table(self, engine, full_context):
        section_def = {"id": "section_8", "title": "8. Управление"}
        result = await engine.generate("section_8", section_def, full_context)

        assert "Таблица 14" in result.content
        assert "Диспетчер" in result.content


    async def test_section_8_renders_questionnaire_notification_scheme(self, engine, full_context):
        full_context.notification_scheme = {"first_receiver": "boiler operator"}
        section_def = {"id": "section_8", "title": "8. РЈРїСЂР°РІР»РµРЅРёРµ"}
        result = await engine.generate("section_8", section_def, full_context)

        assert "boiler operator" in result.content


class TestDataEngineSection13:
    async def test_section_13_renders_material_support(self, engine, full_context):
        section_def = {"id": "section_13", "title": "13. Материальное обеспечение"}
        result = await engine.generate("section_13", section_def, full_context)

        assert "ГОСТ Р 22.10.03-2020" in result.content
        assert "ООО «СПК ААА»" in result.content


    async def test_section_13_preserves_questionnaire_finance_and_insurance(self, engine, full_context):
        full_context.material_reserve = {
            "fin_reserve_order": "12-PB",
            "fin_reserve_amount": "500000",
            "insurance_company": "Acme Insurance",
        }
        section_def = {"id": "section_13", "title": "13. РњР°С‚РµСЂРёР°Р»СЊРЅРѕРµ РѕР±РµСЃРїРµС‡РµРЅРёРµ"}
        result = await engine.generate("section_13", section_def, full_context)

        assert "12-PB" in result.content
        assert "Acme Insurance" in result.content


class TestDataEngineAppendices:
    async def test_appendix_3_renders_pasf(self, engine, full_context):
        section_def = {"id": "appendix_3", "title": "Приложение 3"}
        result = await engine.generate("appendix_3", section_def, full_context)

        assert "ПАСФ" in result.content
        assert "Иванов И.И." in result.content

    async def test_appendix_4_renders_equipment(self, engine, full_context):
        section_def = {"id": "appendix_4", "title": "Приложение 4"}
        result = await engine.generate("appendix_4", section_def, full_context)

        assert "Оснащение" in result.content
        assert "СИЗОД" in result.content
