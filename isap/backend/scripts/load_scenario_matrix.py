"""Загрузка матрицы сценариев для сети газопотребления."""
import asyncio
from src.infrastructure.database.engine import async_session_factory
from src.infrastructure.repositories.scenario_matrix_repo import ScenarioMatrixRepository


SCENARIOS = [
    # Сеть газопотребления
    {"facility_type": "Сеть газопотребления", "hazard_class": "3", "scenario_code": "СГ-1", "scenario_name": "Выброс газа без воспламенения", "factor_type": "Токсическое облако", "calculation_method": "toxic_dispersion_v1", "probability": "высокая"},
    {"facility_type": "Сеть газопотребления", "hazard_class": "3", "scenario_code": "СГ-2", "scenario_name": "Струйное горение газа", "factor_type": "Тепловое излучение", "calculation_method": "thermal_radiation_v1", "probability": "средняя"},
    {"facility_type": "Сеть газопотребления", "hazard_class": "3", "scenario_code": "СГ-3", "scenario_name": "Взрыв газовоздушной смеси", "factor_type": "Взрывная волна", "calculation_method": "tnt_equivalent_v1", "probability": "средняя"},
    {"facility_type": "Сеть газопотребления", "hazard_class": "3", "scenario_code": "СГ-4", "scenario_name": "Пожар газа в обвалке", "factor_type": "Тепловое излучение", "calculation_method": "thermal_radiation_v1", "probability": "низкая"},
    # Нефтедобыча
    {"facility_type": "Нефтедобыча", "hazard_class": "2", "scenario_code": "НД-1", "scenario_name": "Аварийный выброс нефти", "factor_type": "Загрязнение почвы", "calculation_method": None, "probability": "высокая"},
    {"facility_type": "Нефтедобыча", "hazard_class": "2", "scenario_code": "НД-2", "scenario_name": "Взрыв нефтяного паровоздушного облака", "factor_type": "Взрывная волна", "calculation_method": "tnt_equivalent_v1", "probability": "средняя"},
    {"facility_type": "Нефтедобыча", "hazard_class": "2", "scenario_code": "НД-3", "scenario_name": "Пожар на промысле", "factor_type": "Тепловое излучение", "calculation_method": "thermal_radiation_v1", "probability": "средняя"},
    # Нефтепереработка
    {"facility_type": "Нефтепереработка", "hazard_class": "1", "scenario_code": "НП-1", "scenario_name": "Взрыв резервуара с нефтепродуктами", "factor_type": "Взрывная волна + осколки", "calculation_method": "tnt_equivalent_v1", "probability": "низкая"},
    {"facility_type": "Нефтепереработка", "hazard_class": "1", "scenario_code": "НП-2", "scenario_name": "Пожар резервуарного парка", "factor_type": "Тепловое излучение", "calculation_method": "thermal_radiation_v1", "probability": "средняя"},
    {"facility_type": "Нефтепереработка", "hazard_class": "1", "scenario_code": "НП-3", "scenario_name": "Выброс хлористого водорода", "factor_type": "Токсическое облако", "calculation_method": "toxic_dispersion_v1", "probability": "средняя"},
    # Химическое производство
    {"facility_type": "Химическое производство", "hazard_class": "1", "scenario_code": "ХП-1", "scenario_name": "Разгерметизация реактора", "factor_type": "Токсическое облако", "calculation_method": "toxic_dispersion_v1", "probability": "средняя"},
    {"facility_type": "Химическое производство", "hazard_class": "1", "scenario_code": "ХП-2", "scenario_name": "Взрыв паров аммиака", "factor_type": "Взрывная волна", "calculation_method": "tnt_equivalent_v1", "probability": "низкая"},
    # Газораспределение
    {"facility_type": "Газораспределение", "hazard_class": "3", "scenario_code": "ГР-1", "scenario_name": "Повреждение газопровода СИП", "factor_type": "Выброс газа", "calculation_method": "toxic_dispersion_v1", "probability": "высокая"},
    {"facility_type": "Газораспределение", "hazard_class": "3", "scenario_code": "ГР-2", "scenario_name": "Взрыв в подвальном помещении", "factor_type": "Взрывная волна", "calculation_method": "tnt_equivalent_v1", "probability": "средняя"},
    # Транспортировка
    {"facility_type": "Транспортировка", "hazard_class": "2", "scenario_code": "ТР-1", "scenario_name": "Авария цистерны с нефтепродуктами", "factor_type": "Пожар + загрязнение", "calculation_method": "thermal_radiation_v1", "probability": "средняя"},
    {"facility_type": "Транспортировка", "hazard_class": "2", "scenario_code": "ТР-2", "scenario_name": "Утечка газа из трубопровода", "factor_type": "Токсическое облако", "calculation_method": "toxic_dispersion_v1", "probability": "средняя"},
]


async def seed():
    async with async_session_factory() as session:
        repo = ScenarioMatrixRepository(session)

        # Проверяем, есть ли уже данные
        existing = await repo.get_multi(limit=1)
        if existing:
            print(f"Already have {len(existing)} scenarios, skipping seed")
            return

        for scenario in SCENARIOS:
            await repo.create(scenario)
            print(f"Created: {scenario['scenario_code']} - {scenario['scenario_name']}")

        print(f"\nSeeded {len(SCENARIOS)} scenarios")


if __name__ == "__main__":
    asyncio.run(seed())
