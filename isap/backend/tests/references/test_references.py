"""Тесты сервиса справочников."""
import pytest
from src.application.services.references import (
    ReferenceLoader,
    get_substance,
    get_substances_by_facility_type,
    get_accidents,
    get_notification_services,
    get_equipment_kit,
    get_positions,
    get_scenario_instructions,
)


class TestSubstances:
    def test_get_substance_by_name(self):
        substance = get_substance("Метан")
        assert substance is not None
        assert substance["cas_number"] == "74-82-8"
        assert substance["mac_mg_m3"] == 300
        assert substance["lower_flammable_limit_pct"] == 5.0

    def test_get_substance_by_synonym(self):
        substance = get_substance("Природный газ")
        assert substance is not None
        assert substance["name"] == "Метан"

    def test_get_substance_not_found(self):
        substance = get_substance("Несуществующее вещество")
        assert substance is None

    def test_get_substances_by_facility_type(self):
        substances = get_substances_by_facility_type("Сеть газопотребления")
        assert len(substances) >= 1
        names = [s["name"] for s in substances]
        assert "Метан" in names

    def test_all_substances_have_required_fields(self):
        data = ReferenceLoader.load("substances")
        required = ["name", "cas_number", "mac_mg_m3", "hazard_characteristics", "ppe", "first_aid"]
        for substance in data["substances"]:
            for field in required:
                assert field in substance, f"В веществе '{substance.get('name')}' нет поля {field}"


class TestAccidents:
    def test_get_all_accidents(self):
        accidents = get_accidents()
        assert len(accidents) >= 10

    def test_get_accidents_by_facility_type(self):
        accidents = get_accidents(facility_type="Сеть газопотребления")
        assert len(accidents) >= 3
        for a in accidents:
            assert a["facility_type"] == "Сеть газопотребления"

    def test_get_accidents_by_years(self):
        accidents = get_accidents(years=(2020, 2022))
        assert len(accidents) >= 3
        for a in accidents:
            year = int(a["date"].split(".")[-1])
            assert 2020 <= year <= 2022

    def test_get_accidents_with_limit(self):
        accidents = get_accidents(limit=5)
        assert len(accidents) == 5


class TestNotificationServices:
    def test_get_services_for_gas_network(self):
        services = get_notification_services("Сеть газопотребления")
        assert "internal" in services
        assert "external" in services
        assert len(services["external"]) >= 9

    def test_get_services_for_unknown_type_returns_default(self):
        services = get_notification_services("Неизвестный тип")
        assert "internal" in services
        assert "external" in services


class TestEquipmentKit:
    def test_get_kit_for_gas_network(self):
        kit = get_equipment_kit("Сеть газопотребления")
        assert "ppe" in kit
        assert "tools" in kit
        assert "equipment" in kit
        assert len(kit["tools"]) >= 5

    def test_get_kit_for_unknown_type_returns_default(self):
        kit = get_equipment_kit("Неизвестный тип")
        assert "ppe" in kit


class TestPositions:
    def test_get_all_positions(self):
        positions = get_positions()
        assert isinstance(positions, list)
        assert len(positions) >= 5

    def test_get_position_by_role(self):
        position = get_positions("chairman")
        assert position is not None
        assert "Председатель" in position["title"]


class TestScenarioInstructions:
    def test_get_instructions_for_gas_network(self):
        instructions = get_scenario_instructions("Сеть газопотребления")
        assert isinstance(instructions, list)
        assert len(instructions) == 5
        codes = [s["code"] for s in instructions]
        assert codes == ["С-1", "С-2", "С-3", "С-4", "С-5"]

    def test_get_specific_scenario(self):
        scenario = get_scenario_instructions("Сеть газопотребления", "С-3")
        assert scenario is not None
        assert scenario["code"] == "С-3"
        assert "signs" in scenario
        assert "protection_methods" in scenario
        assert "actions" in scenario
        assert len(scenario["actions"]) >= 5


class TestReferenceLoader:
    def test_list_available(self):
        available = ReferenceLoader.list_available()
        assert "substances" in available
        assert "accidents" in available
        assert "notification_services" in available

    def test_reload_clears_cache(self):
        data1 = ReferenceLoader.load("substances")
        ReferenceLoader.reload("substances")
        data2 = ReferenceLoader.load("substances")
        assert data1 == data2
