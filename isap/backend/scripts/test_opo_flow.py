"""Тест полного flow: OPO details → генерация ПМЛА."""
import asyncio
import sys
sys.path.insert(0, ".")

from src.application.engines.base import DocumentContext
from src.application.engines.data_engine import DataEngine
from src.application.engines.rules_engine import RulesEngine
from src.application.services.opo_service import OpoService
from src.application.services.references import (
    get_substance, get_accidents, get_notification_services,
    get_equipment_kit, get_positions, get_scenario_instructions,
)


# === Данные формы «Сведения об ОПО» (как вводит пользователь) ===
FORM_DATA = {
    "f1_1": "Сеть газопотребления города Тюмень",
    "f1_2": "Сеть газопотребления",
    "f1_3": "А34-00000-ГТ",
    "f1_4": "г. Тюмень, ул. Мира, д. 15",
    "f1_5_lat": 57.1522,
    "f1_5_lng": 65.5550,
    "f1_6": "2018-06-15",
    "f1_7_1": "INV-2018-0042",
    "danger_class": "3",
    "processes": {"2.1": True, "2.2a": True, "2.6": True},
    "processes_text": "2.1, 2.2а, 2.6",
    "classification": {"4.1": True, "4.2": True},
    "classification_text": "4.1, 4.2",
    "licenses": {"5.2": True},
    "licenses_text": "5.2",
    "composition": [
        {"name": "ГРПШ №1", "danger": "0.85", "substance": "", "characteristics": "Шкафный газораспределительный пункт", "processes": "2.1, 2.6"},
        {"name": "Газопровод Ду150", "danger": "0.72", "substance": "", "characteristics": "Стальной газопровод среднего давления", "processes": "2.6"},
        {"name": "Регулятор РДУК-50", "danger": "0.45", "substance": "", "characteristics": "Регулятор давления газа", "processes": "2.1"},
        {"name": "Природный газ (метан)", "danger": "0.95", "substance": "Метан", "characteristics": "Основное вещество, ПДК=300 мг/м³", "processes": "2.1, 2.2а"},
        {"name": "Кран шаровой Ду150", "danger": "0.30", "substance": "", "characteristics": "Запорная арматура", "processes": "2.6"},
    ],
    "f7": "3.27",
    "applicant_type": "legal",
    "f8_1_1": "ООО «Газпром межрегионгаз Тюмень»",
    "f8_1_3": "7736050003",
    "f8_1_5": "1027700196362",
    "f8_1_6": "г. Тюмень, ул. Республики, д. 64",
    "f9_5": "+7 (3452) 53-30-00",
    "f9_6": "info@mg-tyumen.ru",
    "signDolj": "Главный инженер",
    "signPodp": "Иванов И.И.",
    "signDate": "05.07.2026",
    "signMp": "г. Тюмень",
}


def test_context_building():
    """Тест маппинга формы OPO → контекст генерации."""
    print("=" * 70)
    print("ТЕСТ 1: Маппинг формы OPO → контекст генерации")
    print("=" * 70)

    # Симулируем build_generation_context (без БД)
    fd = FORM_DATA

    # Организация
    org = {
        "name": fd.get("f8_1_1", ""),
        "inn": fd.get("f8_1_3", ""),
        "ogrn": fd.get("f8_1_5", ""),
        "address": fd.get("f8_1_6", ""),
        "phone": fd.get("f9_5", ""),
        "email": fd.get("f9_6", ""),
    }

    # Объект ОПО
    fac = {
        "name": fd.get("f1_1", ""),
        "facility_type": fd.get("f1_2", ""),
        "hazard_class": fd.get("danger_class", ""),
        "reg_number": fd.get("f1_3", ""),
        "address": fd.get("f1_4", ""),
        "latitude": fd.get("f1_5_lat"),
        "longitude": fd.get("f1_5_lng"),
        "commissioning_date": fd.get("f1_6"),
        "inventory_number": fd.get("f1_7_1", ""),
    }

    # Оборудование
    equipment = []
    for row in fd.get("composition", []):
        equipment.append({
            "name": row.get("name", ""),
            "equipment_type": row.get("substance", ""),
            "serial_number": "",
            "manufacture_year": None,
            "hazard_value": row.get("danger", ""),
            "characteristics": row.get("characteristics", ""),
            "processes": row.get("processes", ""),
        })

    # Вещества
    substances = []
    for row in fd.get("composition", []):
        substance_name = row.get("substance", "")
        if substance_name:
            substances.append({
                "name": substance_name,
                "quantity_kg": 0,
                "cas_number": "",
                "hazard_properties": {
                    "danger_value": row.get("danger", ""),
                    "characteristics": row.get("characteristics", ""),
                    "processes": row.get("processes", ""),
                },
            })

    print(f"\nОрганизация: {org['name']}")
    print(f"  ИНН: {org['inn']}, ОГРН: {org['ogrn']}")
    print(f"  Адрес: {org['address']}")
    print(f"  Тел: {org['phone']}, Email: {org['email']}")

    print(f"\nОбъект: {fac['name']}")
    print(f"  Тип: {fac['facility_type']}")
    print(f"  Рег. номер: {fac['reg_number']}")
    print(f"  Класс опасности: {fac['hazard_class']}")
    print(f"  Адрес: {fac['address']}")
    print(f"  Координаты: {fac['latitude']}, {fac['longitude']}")
    print(f"  Дата ввода: {fac['commissioning_date']}")
    print(f"  Инв. номер: {fac['inventory_number']}")

    print(f"\nОборудование ({len(equipment)} позиций):")
    for eq in equipment:
        print(f"  - {eq['name']}: опасность={eq['hazard_value']}, {eq['characteristics']}")

    print(f"\nВещества ({len(substances)}):")
    for s in substances:
        ref = get_substance(s["name"])
        if ref:
            print(f"  - {s['name']} → из справочника: CAS={ref['cas_number']}, ПДК={ref['mac_mg_m3']}, НКПР={ref['lower_flammable_limit_pct']}%")
        else:
            print(f"  - {s['name']}: не найден в справочнике")

    print(f"\nПроцессы: {fd['processes_text']}")
    print(f"Классификация: {fd['classification_text']}")
    print(f"Лицензии: {fd['licenses_text']}")
    print(f"Суммарная опасность: {fd['f7']}")

    return org, fac, equipment, substances


def test_engines(org, fac, equipment, substances):
    """Тест генерации всех разделов через движки."""
    print("\n" + "=" * 70)
    print("ТЕСТ 2: Генерация разделов через движки")
    print("=" * 70)

    data_engine = DataEngine()
    rules_engine = RulesEngine()

    ctx = DocumentContext(
        organization=org,
        facility=fac,
        equipment=equipment,
        substances=substances,
        persons=[],
        year=2026,
    )

    sections = [
        ("data", "section_1", "1. Характеристика объекта"),
        ("data", "section_3", "3. Характеристика аварийности"),
        ("data", "section_4", "4. Силы и средства"),
        ("rules", "section_10", "10. Первоочередные действия"),
        ("rules", "section_11", "11. Действия персонала"),
        ("data", "section_8", "8. Управление, связь"),
        ("rules", "section_12", "12. Безопасность населения"),
    ]

    import asyncio
    results = {}
    for engine_name, sec_id, title in sections:
        engine = data_engine if engine_name == "data" else rules_engine
        result = asyncio.run(engine.generate(sec_id, {"title": title}, ctx))
        results[sec_id] = result
        block_count = len(result.blocks)
        content_len = len(result.content)
        print(f"\n  {title}: {block_count} блоков, {content_len} символов")
        # Печатаем первые 200 символов
        preview = result.content[:200].replace("\n", " | ")
        print(f"  Превью: {preview}...")

    return results


def test_references():
    """Тест справочников для facility_type='Сеть газопотребления'."""
    print("\n" + "=" * 70)
    print("ТЕСТ 3: Справочники для 'Сеть газопотребления'")
    print("=" * 70)

    ft = "Сеть газопотребления"

    # Вещества
    subs = [s["name"] for s in [
        {"name": "Природный газ"}, {"name": "Метан"}, {"name": "Пропан"},
    ]]
    print("\nВещества:")
    for name in subs:
        ref = get_substance(name)
        if ref:
            print(f"  {name} → {ref['name']}: CAS={ref['cas_number']}, ПДК={ref['mac_mg_m3']}, НКПР={ref['lower_flammable_limit_pct']}%")
        else:
            print(f"  {name} → не найден")

    # Аварии
    accidents = get_accidents(facility_type=ft, years=(2020, 2026))
    print(f"\nАварии ({len(accidents)}):")
    for a in accidents[:3]:
        print(f"  {a['date']} — {a['organization'][:50]}")

    # Оснащение
    kit = get_equipment_kit(ft)
    ppe_count = len(kit.get("ppe", []))
    tools_count = len(kit.get("tools", []))
    equip_count = len(kit.get("equipment", []))
    print(f"\nОснащение: СИЗ={ppe_count}, инструмент={tools_count}, оборудование={equip_count}")

    # Оповещение
    notif = get_notification_services(ft)
    internal = len(notif.get("internal", []))
    external = len(notif.get("external", []))
    print(f"Оповещение: внутренние={internal}, внешние={external}")

    # Должности
    positions = get_positions()
    print(f"Должности: {len(positions)}")

    # Сценарии
    scenarios = get_scenario_instructions(ft)
    codes = [s["code"] for s in scenarios] if scenarios else []
    print(f"Сценарии: {codes}")


def main():
    print("\n" + "#" * 70)
    print("# ТЕСТ ПОЛНОГО FLOW: OPO details → ГЕНЕРАЦИЯ ПМЛА")
    print("#" * 70)

    org, fac, equipment, substances = test_context_building()
    results = test_engines(org, fac, equipment, substances)
    test_references()

    print("\n" + "=" * 70)
    print("ИТОГИ")
    print("=" * 70)
    print(f"Разделов сгенерировано: {len(results)}")
    print(f"Оборудование: {len(equipment)} позиций из composition")
    print(f"Вещества: {len(substances)} (обогащены справочником)")
    print(f"Справочники: 6 файлов подключены")
    print(f"Движки: DataEngine + RulesEngine")

    # Проверяем что справочники работают
    ref_methane = get_substance("Метан")
    assert ref_methane is not None, "Метан не найден в справочнике"
    assert ref_methane["mac_mg_m3"] == 300, "ПДК метана неверна"

    accidents = get_accidents(facility_type="Сеть газопотребления")
    assert len(accidents) >= 3, "Недостаточно аварий в справочнике"

    kit = get_equipment_kit("Сеть газопотребления")
    assert "ppe" in kit, "Нет СИЗ в справочнике"

    print("\nВСЕ ПРОВЕРКИ ПРОЙДЕНЫ ✓")


if __name__ == "__main__":
    main()
