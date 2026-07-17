"""Test render of the v2 PMLA template with synthetic context.

Renders two DOCX files:
1. pmla_v2_rendered_test.docx — full context with data
2. pmla_v2_rendered_empty.docx — empty lists fallback
"""
from __future__ import annotations

import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.infrastructure.export.pmla_template_renderer import PmlaTemplateRenderer

FILES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "files")

# Full test context
FULL_CONTEXT = {
    # === Organization ===
    "organization_full_name": "Общество с ограниченной ответственностью «ТестПром»",
    "organization_short_name": "ООО «ТестПром»",
    "legal_address": "123456, Россия, г. Москва, ул. Тестовая, д. 1, корп. 2",
    "inn": "7701234567",
    "ogrn": "1027700000123",
    "phone": "+7 (495) 123-45-67",
    "email": "info@testprom.ru",
    "director_position_fullname": "Генеральный директор Иванов Иван Иванович",
    "director_initials_surname": "И.И. Иванов",
    "director_initials_surname_full": "Иванов Иван Иванович",
    "deputy_chairman_fullname": "Петров Пётр Петрович",
    "main_activity_description": "01.11 Выращивание зерновых культур",

    # === Facility ===
    "facility_name": "Сеть газопотребления",
    "facility_reg_number": "А34-99999-0001",
    "facility_location": "Московская область, г. Тест",
    "hazard_class": "III",
    "hazardous_substances_info": "Природный газ (метан) по ГОСТ 5542-2014",
    "hazard_characteristics_116fz": "Использование горючих газов",

    # === Contractor ===
    "contractor_organization_name": "ООО «Спасатель»",
    "contractor_organization_short_name": "«Спасатель»",
    "contractor_agreement_date": "01.01.2026",
    "gas_supplier_name": "ПАО «Газпром»",
    "total_hazardous_substance_quantity": "0.5",

    # === Table 5: Equipment ===
    "equipment_list": [
        {
            "location": "Площадка ГРП",
            "hazard_characteristic": "Использование горючих газов",
            "device_name": "ГРПШ-1 (РДНК-400, зав. № 92)",
            "specifications": "Р=0.6 МПа, Траб=50°С",
            "process_codes": "2.1",
        },
        {
            "location": "Газопровод ВД №1",
            "hazard_characteristic": "Использование горючих газов",
            "device_name": "Труба стальная Ø57 мм, L=13.4 м",
            "specifications": "Р=0.3-0.6 МПа",
            "process_codes": "2.1",
        },
        {
            "location": "Площадка котельной",
            "hazard_characteristic": "Использование горючих газов",
            "device_name": "Котёл КГВМ-50",
            "specifications": "Q=50 Гкал/ч, 2015 г.",
            "process_codes": "2.2",
        },
    ],

    # === Table 6: Substance Parameters ===
    "substance_params": [
        {"parameter": "Класс опасности по ГОСТ 12.1.007", "value": "4 (малоопасный)"},
        {"parameter": "ПДК в воздухе рабочей зоны (по метану)", "value": "300 мг/м³"},
        {"parameter": "Нижний концентрационный предел воспламенения (НКПР)", "value": "5 % об."},
        {"parameter": "Верхний концентрационный предел воспламенения (ВКПР)", "value": "15 % об."},
        {"parameter": "Категория взрывоопасной смеси по ПУЭ", "value": "IIА – Т1"},
        {"parameter": "Характер воздействия на человека", "value": "Удушающее действие (асфиксия) при снижении O₂ в воздухе до 16-18 % об."},
        {"parameter": "Средства индивидуальной защиты (СИЗ)", "value": "Изолирующие дыхательные аппараты АП-2, защитные костюмы"},
        {"parameter": "Первая помощь при отравлении", "value": "Вынести пострадавшего из зоны загазованности на свежий воздух. Расстегнуть одежду. При необходимости — ИВЛ."},
    ],

    # === Table 7: Equipment-Scenario Links ===
    "equipment_scenario_links": [
        {
            "equipment_name": "ГРПШ-1 (РДНК-400, зав. № 92)",
            "scenario_codes": "С-1, С-2, С-4, С-5",
            "description": "С-1: утечка через неплотности фланцев, сальников регулятора — загазованность; С-2: разрыв корпуса — струйное горение; С-4: взрыв внутри шкафа; С-5: отказ регулятора — повышение давления",
            "damaging_factors": "взрывоопасное облако; тепловое излучение от факела; ударная волна и осколки",
        },
        {
            "equipment_name": "Газопровод ВД №1 (Ø57 мм, L=13.4 м)",
            "scenario_codes": "С-1, С-2, С-3",
            "description": "С-1: микротрещина на сварном шве — утечка газа; С-2: полный разрыв — струйное горение; С-3: взрыв ГВС на площадке",
            "damaging_factors": "зона загазованности; тепловое излучение от факела; избыточное давление",
        },
        {
            "equipment_name": "Котёл КГВМ-50",
            "scenario_codes": "С-5, С-6",
            "description": "С-5: повышение давления газа → нарушение работы горелки; С-6: хлопок в камере сгорания",
            "damaging_factors": "ударная волна; тепловое излучение; разрушение конструкций",
        },
    ],

    # === Table 8: Equipment Defects ===
    "equipment_defects": [
        {"equipment_name": "ГРПШ-1", "defect": "Разгерметизация фланцевых соединений", "cause": "Износ прокладок, ослабление болтов", "source": "Входной/выходной фланцы ГРПШ", "scenario": "С-1"},
        {"equipment_name": "ГРПШ-1", "defect": "Разрушение корпуса регулятора", "cause": "Замерзание конденсата, коррозия", "source": "Корпус РДНК-400", "scenario": "С-2"},
        {"equipment_name": "ГРПШ-1", "defect": "Взрыв ГВС внутри шкафа", "cause": "Накопление газа от микропропусков", "source": "Внутреннее пространство шкафа", "scenario": "С-4"},
        {"equipment_name": "ГРПШ-1", "defect": "Отказ регулятора", "cause": "Износ мембраны, залипание клапана", "source": "Мембранный узел РДНК-400", "scenario": "С-5"},
        {"equipment_name": "Газопровод ВД №1", "defect": "Микротрещина, свищ", "cause": "Коррозия, дефекты сварных швов", "source": "Сварные швы, тело трубы", "scenario": "С-1"},
        {"equipment_name": "Газопровод ВД №1", "defect": "Полный разрыв трубы", "cause": "Механическое повреждение", "source": "Любой участок ВД", "scenario": "С-2, С-3"},
        {"equipment_name": "Газопровод ВД №2", "defect": "Микротрещина", "cause": "Коррозия, дефекты швов", "source": "Сварные швы", "scenario": "С-1"},
        {"equipment_name": "Газопровод ВД №2", "defect": "Разрыв трубы", "cause": "Механическое повреждение", "source": "Участок за ГРПШ", "scenario": "С-2, С-3"},
        {"equipment_name": "Запорная арматура", "defect": "Неплотное закрытие", "cause": "Износ уплотнений", "source": "Седла и затворы кранов", "scenario": "С-1"},
        {"equipment_name": "Сварные соединения", "defect": "Дефекты сварных швов", "cause": "Нарушение технологии сварки", "source": "Стыки труб", "scenario": "С-1, С-2"},
        {"equipment_name": "ПСК в составе ГРПШ", "defect": "Дребезг / микросброс", "cause": "Износ седла клапана", "source": "ПСК на ГРПШ", "scenario": "С-1"},
        {"equipment_name": "Импульсные линии", "defect": "Разгерметизация / закупорка", "cause": "Коррозия, замерзание конденсата", "source": "Импульсные трубки", "scenario": "С-1, С-5"},
        {"equipment_name": "Газоиспользующее оборудование", "defect": "Нарушение режима зажигания", "cause": "Колебания давления газа", "source": "Газогорелочные устройства", "scenario": "С-5, С-6"},
    ],

    # === Table 9: Accident Scenarios ===
    "accident_scenarios": [
        {"code": "С-1", "name": "Выброс газа без воспламенения", "source": "Фланцевые соединения, арматура на ГРПШ, газопроводы ВД", "preconditions": "Разгерметизация соединений, износ уплотнений, коррозия", "signs": "Характерный запах (одорант), шум истекающего газа, показания газоанализатора", "damaging_factors": "Токсическое действие, удушье, взрывопожароопасность при накоплении"},
        {"code": "С-2", "name": "Струйное горение газа на открытой площадке", "source": "Место разрыва газопровода ВД или корпус регулятора", "preconditions": "Разрыв трубы, повреждение регулятора, отказ запорной арматуры", "signs": "Открытое пламя, шум, тепловое излучение", "damaging_factors": "Тепловое излучение (поражает людей, вызывает возгорание конструкций)"},
        {"code": "С-3", "name": "Взрыв ГВС на открытой площадке", "source": "Территория ГРПШ, прилегающая зона", "preconditions": "Утечка газа + образование облака ГВС + воспламенение", "signs": "Хлопок, ударная волна, разрушение оборудования", "damaging_factors": "Избыточное давление во фронте ударной волны"},
        {"code": "С-4", "name": "Взрыв ГВС в замкнутом объеме", "source": "Внутреннее пространство шкафа ГРПШ", "preconditions": "Утечка газа внутри шкафа + накопление ГВС + искрение", "signs": "Хлопок, разрушение шкафа, разлет осколков", "damaging_factors": "Избыточное давление, осколочное поражение"},
        {"code": "С-5", "name": "Отказ регулятора давления с повышением выходного давления", "source": "Регулятор РДНК-400 (зав. № 92)", "preconditions": "Неисправность мембраны, засорение, обмерзание", "signs": "Повышение давления на выходе, срабатывание ПЗК", "damaging_factors": "Разрушение газового оборудования, срыв мембран"},
        {"code": "С-6", "name": "Хлопок (взрыв) в газоиспользующем оборудовании", "source": "Газогорелочное устройство потребителя", "preconditions": "Нарушение режима зажигания, отрыв пламени", "signs": "Хлопок, погасание пламени, резкий звук", "damaging_factors": "Ударная волна, повреждение оборудования"},
    ],

    # === Tables 10, 11: Injury/Accident History (empty) ===
    "injury_history": [],
    "accident_history": [],

    # === Table 13: Material Reserve ===
    "material_reserve": [
        {"is_group_header": True, "group_name": "Средства индивидуальной защиты (СИЗ)"},
        {"name": "Изолирующий противогаз (кислородный или шланговый)", "quantity": "4 шт.", "location": "Аварийный шкаф"},
        {"name": "Защитный костюм (брезентовый)", "quantity": "4 шт.", "location": "Аварийный шкаф"},
        {"name": "Диэлектрические перчатки", "quantity": "2 пары", "location": "Аварийный шкаф"},
        {"name": "Диэлектрические сапоги (боты)", "quantity": "2 пары", "location": "Аварийный шкаф"},
        {"name": "Защитные каски", "quantity": "4 шт.", "location": "Аварийный шкаф"},
        {"is_group_header": True, "group_name": "Инструмент и приспособления"},
        {"name": "Переносной газоанализатор (течеискатель)", "quantity": "1 шт.", "location": "Аварийный шкаф"},
        {"name": "Ключи газовые (№1, №2)", "quantity": "2 компл.", "location": "Аварийный шкаф"},
        {"name": "Ключи гаечные (набор)", "quantity": "1 компл.", "location": "Аварийный шкаф"},
        {"name": "Приспособление для хомутов на трубопроводы", "quantity": "2 компл.", "location": "Склад"},
        {"name": "Заглушки стальные (разные диаметры)", "quantity": "4 шт.", "location": "Склад"},
        {"name": "Набор прокладок паронитовых", "quantity": "1 компл.", "location": "Аварийный шкаф"},
        {"name": "Инструмент немелящий (бронзовый)", "quantity": "1 компл.", "location": "Аварийный шкаф"},
        {"name": "Молоток (с медным бойком)", "quantity": "1 шт.", "location": "Аварийный шкаф"},
        {"name": "Зубило (из цветного металла)", "quantity": "1 шт.", "location": "Аварийный шкаф"},
        {"is_group_header": True, "group_name": "Оборудование и материалы"},
        {"name": "Переносной светильник взрывозащищенный (12 В)", "quantity": "2 шт.", "location": "Аварийный шкаф"},
        {"name": "Сигнальные знаки и оградительная лента", "quantity": "1 компл.", "location": "Аварийный шкаф"},
        {"name": "Порошковый огнетушитель ОП-8", "quantity": "2 шт.", "location": "Пожарный щит"},
        {"name": "Аварийный запас уплотнительных материалов", "quantity": "1 компл.", "location": "Аварийный шкаф"},
    ],

    # === Table 17: Notification List (phones parameterized) ===
    "notification_chairman_phone": "+7 928 709-95-15",
    "notification_deputy_phone": "+7 906 881-07-07",
    "notification_edds_phone": "112",
    "notification_pasf_phone": "+7 (903) 495-75-57",
    "notification_fire_phone": "+7 (8663) 04-14-91",
    "notification_ambulance_phone": "112/03/103",
    "notification_gas_phone": "+7 (86630) 4-18-68",
    "notification_electric_phone": "+7 (86630) 4-27-70",
    "notification_mchs_phone": "+7 (8662) 39-99-99",
    "notification_rostechnadzor_phone": "+7 (928) 307-04-62",
    "notification_admin_phone": "+7 (86630) 7-63-99",

    # === Table 18: Countermeasures ===
    "countermeasures": [
        {
            "scenario_label": "С-1 Выброс природного газа без воспламенения",
            "signs": "1. Характерный запах одоранта на площадке ГРПШ\n2. Шум истекающего газа\n3. Показания газоанализатора выше ПДК",
            "protection": "1. НЕМЕДЛЕННО прекратить все огневые и ремонтные работы\n2. Отключить электрооборудование\n3. Организовать проветривание",
            "technical_means": "Стационарный сигнализатор загазованности\nПереносной газоанализатор\nСредства связи",
            "executors": "1. Работник, заметивший утечку:\n- Покидает загазованную зону\n- Сообщает диспетчеру\n2. Диспетчер:\n- Оповещает ПСЧ, ПАСФ\n- Включает вентиляцию",
        },
        {
            "scenario_label": "С-2 Струйное горение газа на открытой площадке",
            "signs": "1. Открытое пламя, факел газа\n2. Шум горения\n3. Тепловое излучение",
            "protection": "1. НЕМЕДЛЕННО приступить к локализации\n2. Не пытаться тушить факел до отсечения газа\n3. Отвести людей на безопасное расстояние",
            "technical_means": "Ручные шаровые краны (поз.1, поз.2)\nПожарные гидранты и стволы\nСредства связи",
            "executors": "1. Любой работник:\n- Сообщает диспетчеру\n- Покидает зону\n2. Диспетчер:\n- Вызывает ПСЧ, ПАСФ\n- Отключает подачу газа",
        },
        {
            "scenario_label": "С-3 Взрыв ГВС на открытой площадке",
            "signs": "1. Сильный хлопок или звук взрыва\n2. Ударная волна\n3. Разрушение оборудования",
            "protection": "1. Прекратить все работы в радиусе 100 м\n2. Отвести людей на безопасное расстояние\n3. Оцепить зону",
            "technical_means": "Ручные шаровые краны\nСредства ограждения\nСредства связи",
            "executors": "1. Свидетель:\n- Укрывается или покидает зону\n- Сообщает диспетчеру\n2. Диспетчер:\n- Вызывает все службы\n- Организует встречу подразделений",
        },
        {
            "scenario_label": "С-4 Взрыв ГВС в замкнутом объеме (шкаф ГРПШ)",
            "signs": "1. Сильный хлопок\n2. Разрушение (деформация) шкафа ГРПШ\n3. Выбиты стёкла",
            "protection": "1. Прекратить все работы в радиусе 50 м\n2. Оцепить зону\n3. Оценить пострадавших",
            "technical_means": "Индивидуальные средства защиты (каски, костюмы)\nПорошковые/углекислотные огнетушители\nСредства связи",
            "executors": "1. Свидетель:\n- Укрывается или покидает зону\n- Сообщает диспетчеру\n2. Диспетчер:\n- Вызывает все службы\n- Организует встречу подразделений",
        },
        {
            "scenario_label": "С-5 Отказ регулятора давления с повышением выходного давления",
            "signs": "1. Резкое повышение давления по манометру (выше 0,005 МПа)\n2. Срабатывание ПЗК\n3. Повышение давления на газоиспользующем оборудовании",
            "protection": "1. Контроль срабатывания ПЗК\n2. Контроль сброса через ПСК\n3. Ручное отключение при необходимости",
            "technical_means": "Манометры на входе и выходе ГРПШ\nВстроенные ПЗК и ПСК регулятора\nРучные шаровые краны",
            "executors": "1. Оператор (дежурный):\n- Замечает повышение давления\n- Контролирует срабатывание ПЗК\n- Сообщает диспетчеру\n2. Диспетчер:\n- Принимает решение об отключении\n- Вызывает аварийную бригаду",
        },
    ],
}

# Empty context (all lists empty)
EMPTY_CONTEXT = {**FULL_CONTEXT}
EMPTY_CONTEXT["equipment_list"] = []
EMPTY_CONTEXT["substance_params"] = []
EMPTY_CONTEXT["equipment_scenario_links"] = []
EMPTY_CONTEXT["equipment_defects"] = []
EMPTY_CONTEXT["accident_scenarios"] = []
EMPTY_CONTEXT["injury_history"] = []
EMPTY_CONTEXT["accident_history"] = []
EMPTY_CONTEXT["material_reserve"] = []
EMPTY_CONTEXT["countermeasures"] = []


def main():
    renderer = PmlaTemplateRenderer()

    # 1. Full render
    print("=== Rendering full context ===")
    full_path = os.path.join(FILES_DIR, "pmla_v2_rendered_test.docx")
    renderer.render_to_file(FULL_CONTEXT, full_path)
    size = os.path.getsize(full_path)
    print(f"  Saved: {full_path} ({size:,} bytes)")

    # 2. Empty render
    print("\n=== Rendering empty context ===")
    empty_path = os.path.join(FILES_DIR, "pmla_v2_rendered_empty.docx")
    renderer.render_to_file(EMPTY_CONTEXT, empty_path)
    size = os.path.getsize(empty_path)
    print(f"  Saved: {empty_path} ({size:,} bytes)")

    # 3. Verify no Jinja artifacts
    print("\n=== Verifying no Jinja artifacts ===")
    from docx import Document
    for label, path in [("Full", full_path), ("Empty", empty_path)]:
        doc = Document(path)
        artifacts = 0
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    text = cell.text
                    if "{{" in text or "{%" in text:
                        artifacts += 1
                        print(f"  {label}: ARTIFACT in table: {text[:80]}")
        print(f"  {label}: {artifacts} remaining Jinja artifacts")

    print("\nDone!")


if __name__ == "__main__":
    main()
