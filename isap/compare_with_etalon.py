"""Сравнение сгенерированного ПМЛА с эталоном ПМЛА ООО СПК ААА."""
import asyncio
import json
from pathlib import Path

# Добавляем путь к проекту
import sys
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from src.application.engines.base import DocumentContext
from src.application.engines.data_engine import DataEngine
from src.application.engines.narrative_engine import NarrativeEngine
from src.application.engines.rules_engine import RulesEngine
from src.application.engines.router import EngineRouter
from src.application.engines.scenario_engine import ScenarioEngine
from src.application.engines.table_engine import TableEngine
from src.application.engines.template_engine import TemplateEngine


# Контекст на основе эталонного документа ПМЛА ООО СПК ААА
ETALON_CONTEXT = DocumentContext(
    organization={
        "name": "Сельскохозяйственный производственный кооператив «ААА»",
        "short_name": "СПК «ААА»",
        "inn": "0703004222",
        "ogrn": "1020700001234",
        "address": "361402, Россия, Кабардино-Балкарская Республика, г. Нальчик",
        "phone": "+7 (8662) 12-34-56",
        "email": "info@spk-aaa.ru",
        "director": "И.Т. ААААА",
        "director_position": "Председатель",
    },
    facility={
        "name": "Сеть газопотребления СПК «ААА»",
        "reg_number": "А34-00000-0001",
        "hazard_class": "3",
        "facility_type": "Сеть газопотребления",
        "address": "361402, Россия, Кабардино-Балкарская Республика, г. Нальчик",
    },
    equipment=[
        {"name": "ГРПШ-1", "equipment_type": "Газораспределительный пункт шкафный", "serial_number": "SN-001", "manufacture_year": 2015},
        {"name": "Газопровод СИП Ду50", "equipment_type": "Газопровод", "serial_number": "SN-002", "manufacture_year": 2015},
        {"name": "Газопровод стальной Ду100", "equipment_type": "Газопровод", "serial_number": "SN-003", "manufacture_year": 2010},
        {"name": "Регулятор давления РДГ-50", "equipment_type": "Регулятор", "serial_number": "SN-004", "manufacture_year": 2018},
        {"name": "Кран газовый крановый Ду50 Ру16", "equipment_type": "Кран", "serial_number": "SN-005", "manufacture_year": 2015},
    ],
    substances=[
        {
            "name": "Природный газ",
            "cas_number": "74-82-8",
            "quantity_kg": 500,
            "threshold_quantity_kg": 1000,
            "hazard_properties": {
                "physical_state": "газ",
                "explosion_energy_mj": 50,
                "combustion_energy_mj_kg": 55,
                "mac_mg_m3": 300,
            },
        },
    ],
    persons=[
        {"full_name": "И.Т. ААААА", "position": "Председатель", "role": "director", "phone": "+7 (8662) 12-34-56"},
        {"full_name": "А.А. ААААА", "position": "Главный инженер", "role": "engineer", "phone": "+7 (8662) 12-34-57"},
        {"full_name": "Б.Б. БББББ", "position": "Диспетчер", "role": "dispatcher", "phone": "+7 (8662) 12-34-58"},
        {"full_name": "В.В. ВВВВВ", "position": "Начальник службы безопасности", "role": "safety", "phone": "+7 (8662) 12-34-59"},
    ],
    year=2026,
)


async def main():
    print("=" * 80)
    print("СРАВНЕНИЕ: Новая архитектура 6 движков vs Эталон ПМЛА ООО СПК ААА")
    print("=" * 80)
    print()

    # Создаём EngineRouter
    router = EngineRouter([
        TemplateEngine(),
        DataEngine(),
        ScenarioEngine(),
        RulesEngine(),
        NarrativeEngine(),
    ])

    # Генерируем все разделы
    results = await router.generate_all(ETALON_CONTEXT)

    # Загружаем эталонный анализ
    etalon_path = Path(__file__).parent / "docx_analysis.json"
    if etalon_path.exists():
        etalon = json.loads(etalon_path.read_text(encoding="utf-8"))
    else:
        etalon = None
        print("[WARNING] docx_analysis.json не найден, сравнение без эталона")
        print()

    # 1. Сравнение структуры разделов
    print("1. СТРУКТУРА РАЗДЕЛОВ")
    print("-" * 60)

    etalon_sections = [
        "Титульный лист",
        "Журнал корректировки",
        "Содержание",
        "Перечень обозначений",
        "Термины и определения",
        "Введение",
        "1. Характеристика объекта",
        "2. Сценарии аварий",
        "3. Аварийность",
        "4. Силы и средства",
        "5. Взаимодействие",
        "6. Состав и дислокация",
        "7. Готовность",
        "8. Управление, связь",
        "9. Обмен информацией",
        "10. Первоочередные действия",
        "11. Действия персонала",
        "12. Безопасность населения",
        "13. Материальное обеспечение",
        "Специальный раздел",
        "Приложение 1",
        "Приложение 2",
        "Приложение 3",
        "Приложение 4",
        "Приложение 5",
        "Список литературы",
        "Лист ознакомления",
    ]

    generated_sections = list(results.keys())
    print(f"Эталон:  {len(etalon_sections)} разделов")
    print(f"Генерация: {len(generated_sections)} разделов")
    print()

    # Проверяем покрытие
    for i, (etalon_s, gen_s) in enumerate(zip(etalon_sections, generated_sections), 1):
        status = "✅" if gen_s else "❌"
        print(f"  {i:2d}. {status} {etalon_s}")

    print()

    # 2. Сравнение таблиц
    print("2. ТАБЛИЦЫ")
    print("-" * 60)

    etalon_tables = {
        "T0": "Согласование/Утверждение (6x3)",
        "T1": "Журнал корректировки (43x4)",
        "T2": "Содержание (22x2)",
        "T3": "Обозначения (19x2)",
        "T4": "Таблица 1 - Общие сведения (16x2)",
        "T5": "Таблица 2 - Оборудование (5x6)",
        "T6": "Таблица 3 - Вещества (9x2)",
        "T7": "Таблица 4 - Сценарии по элементам (4x5)",
        "T8": "Таблица 5 - Источники аварий (14x6)",
        "T9": "Таблица 6 - Сценарии (7x6)",
        "T10": "Таблица 7 - Травматизм (6x7)",
        "T11": "Таблица 8 - Аварийность (6x7)",
        "T12": "Таблица 9 - Аналогичные аварии (10x4)",
        "T13": "Таблица 10 - Ресурсы (22x4)",
        "T14": "Таблица 11 - Силы (5x2)",
        "T15": "Таблица 12 - Состав (5x3)",
        "T16": "Таблица 13 - Дислокация (5x3)",
        "T17": "Таблица 14 - Оповещение (14x7)",
        "T18": "Таблица 15 - Спецраздел (6x5)",
    }

    print(f"Эталон: {len(etalon_tables)} таблиц")
    print()

    # Проверяем наличие таблиц в сгенерированных разделах
    table_checks = {
        "Таблица 1": "section_1",
        "Таблица 2": "section_1",
        "Таблица 3": "section_1",
        "Таблица 4": "section_2",
        "Таблица 5": "section_2",
        "Таблица 6": "section_2",
        "Таблица 7": "section_3",
        "Таблица 8": "section_3",
        "Таблица 9": "section_3",
        "Таблица 10": "section_4",
        "Таблица 11": "section_6",
        "Таблица 12": "section_6",
        "Таблица 13": "section_6",
        "Таблица 14": "section_8",
        "Таблица 15": "special_section",
    }

    for table_name, section_id in table_checks.items():
        section = results.get(section_id)
        if section and table_name in section.content:
            print(f"  ✅ {table_name} ({section_id})")
        else:
            print(f"  ❌ {table_name} ({section_id}) - ОТСУТСТВУЕТ")

    print()

    # 3. Сравнение сценариев
    print("3. СЦЕНАРИИ АВАРИЙ")
    print("-" * 60)

    etalon_scenarios = ["С-1", "С-2", "С-3", "С-4", "С-5"]
    section_2 = results.get("section_2")
    special = results.get("special_section")

    for code in etalon_scenarios:
        in_s2 = code in (section_2.content if section_2 else "")
        in_ss = code in (special.content if special else "")
        status = "✅" if in_s2 and in_ss else "❌"
        print(f"  {status} {code}: section_2={in_s2}, special_section={in_ss}")

    print()

    # 4. Ключевые данные
    print("4. КЛЮЧЕВЫЕ ДАННЫЕ")
    print("-" * 60)

    checks = [
        ("Название организации", "СПК «ААА»"),
        ("ИНН", "0703004222"),
        ("Рег. номер ОПО", "А34-00000-0001"),
        ("Класс опасности", "3"),
        ("Название объекта", "Сеть газопотребления"),
        ("Природный газ", "74-82-8"),
        ("116-ФЗ", "116-ФЗ"),
        ("Постановление 1437", "1437"),
        ("Приказ 531", "531"),
    ]

    for label, pattern in checks:
        found = False
        for sid, section in results.items():
            if pattern in section.content:
                found = True
                break
        status = "✅" if found else "❌"
        print(f"  {status} {label}: '{pattern}'")

    print()

    # 5. Примеры аварий (Таблица 9)
    print("5. ПРИМЕРЫ АВАРИЙ (Таблица 9)")
    print("-" * 60)

    section_3 = results.get("section_3")
    if section_3:
        accident_keywords = ["Пермская", "Газпром", "Нальчик", "Уфа"]
        for kw in accident_keywords:
            found = kw in section_3.content
            status = "✅" if found else "❌"
            print(f"  {status} {kw}")

    print()

    # 6. Сводка
    print("6. СВОДКА")
    print("-" * 60)

    total_checks = 0
    passed_checks = 0

    # Разделы
    for i in range(min(len(etalon_sections), len(generated_sections))):
        total_checks += 1
        if generated_sections[i]:
            passed_checks += 1

    # Таблицы
    for table_name, section_id in table_checks.items():
        total_checks += 1
        section = results.get(section_id)
        if section and table_name in section.content:
            passed_checks += 1

    # Сценарии
    for code in etalon_scenarios:
        total_checks += 1
        in_s2 = code in (section_2.content if section_2 else "")
        in_ss = code in (special.content if special else "")
        if in_s2 and in_ss:
            passed_checks += 1

    # Ключевые данные
    for label, pattern in checks:
        total_checks += 1
        for sid, section in results.items():
            if pattern in section.content:
                passed_checks += 1
                break

    # Примеры аварий
    for kw in accident_keywords:
        total_checks += 1
        if section_3 and kw in section_3.content:
            passed_checks += 1

    score = (passed_checks / total_checks * 100) if total_checks > 0 else 0

    print(f"  Проверок: {passed_checks}/{total_checks}")
    print(f"  Оценка: {score:.1f}%")
    print()

    if score >= 90:
        print("  ✅ ОТЛИЧНО - архитектура готова к использованию")
    elif score >= 70:
        print("  ⚠️  ХОРОШО - есть замечания для доработки")
    else:
        print("  ❌ НУЖНА ДОРАБОТКА - критические расхождения")


if __name__ == "__main__":
    asyncio.run(main())
