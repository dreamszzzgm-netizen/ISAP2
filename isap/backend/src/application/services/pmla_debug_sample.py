"""Reference PMLA debug context.

This context is intentionally deterministic and independent from the database.
It is used to debug generation quality for the most important flow:
Организация → ОПО → контекст → разделы → DOCX → validation report.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime


GAS_CONSUMPTION_BAKERY_CONTEXT: dict = {
    "organization": {
        "name": "АО «Хлебокомбинат»",
        "inn": "14445071552",
        "kpp": "144501001",
        "address": "677004, Республика Саха (Якутия), г. Якутск, ул. Очиченко, д. 17",
        "phone": "+7 (4112) 43-33-01",
        "email": "info@example.local",
        "director": "Светлана Тарасовна",
        "director_phone": "+7 (4112) 43-33-01",
    },
    "facility": {
        "name": "Сеть газопотребления Хлебозавода №2",
        "facility_type": "Сеть газопотребления",
        "object_type": "Сеть газопотребления",
        "hazard_class": "III",
        "reg_number": "А01-0001-0005",
        "address": "Республика Саха (Якутия), г. Якутск, промышленная площадка Хлебозавода №2",
        "latitude": 62.0272,
        "longitude": 129.7322,
        "commissioning_date": "2016-05-20",
        "inventory_number": "ГС-ХБК-002",
    },
    "substances": [
        {
            "name": "Природный газ (метан)",
            "quantity_kg": 800,
            "quantity": "0,8 т",
            "cas_number": "74-82-8",
            "hazard_class": 4,
            "hazard_properties": {
                "flammable": True,
                "explosive_mixture": True,
                "description": "горючий газ, образующий взрывоопасные газовоздушные смеси",
            },
        }
    ],
    "equipment": [
        {
            "name": "Подводящий газопровод высокого давления наружный",
            "equipment_type": "газопровод",
            "serial_number": "ГП-001",
            "characteristics": "L=95 м; D=89 мм; P=0,6 МПа",
            "specifications": {"length_m": 95, "diameter_mm": 89, "pressure_mpa": 0.6},
        },
        {
            "name": "Газорегуляторная установка шкафного типа",
            "equipment_type": "ГРУ",
            "serial_number": "ГРУ-002",
            "characteristics": "регулирование давления газа перед котельной",
            "specifications": {"purpose": "снижение и поддержание давления газа"},
        },
        {
            "name": "Водогрейный котел ROSSEN RSD 1000",
            "equipment_type": "котел водогрейный газовый",
            "serial_number": "К-001/К-002",
            "characteristics": "2 ед.; Q=1 МВт; P=0,8 МПа",
            "specifications": {"quantity": 2, "power_mw": 1, "pressure_mpa": 0.8},
        },
        {
            "name": "Огнетушитель порошковый ОП-10",
            "equipment_type": "огнетушитель",
            "serial_number": "ОП-010",
            "characteristics": "первичные средства пожаротушения",
        },
        {
            "name": "Противогаз фильтрующий гражданский",
            "equipment_type": "СИЗОД противогаз",
            "serial_number": "СИЗ-001",
            "characteristics": "средство индивидуальной защиты органов дыхания",
        },
    ],
    "responsible_persons": [
        {
            "full_name": "Иванов Иван Иванович",
            "position": "Главный инженер",
            "role": "chief_engineer",
            "phone": "+7 (4112) 43-33-02",
        },
        {
            "full_name": "Петров Петр Петрович",
            "position": "Ответственный за эксплуатацию сети газопотребления",
            "role": "gas_facility_responsible",
            "phone": "+7 (4112) 43-33-03",
        },
        {
            "full_name": "Сидорова Анна Сергеевна",
            "position": "Диспетчер",
            "role": "dispatcher",
            "phone": "+7 (4112) 43-33-04",
        },
    ],
    "emergency_services": {
        "pasf": [
            {
                "name": "ПАСФ ООО «ГазСпасСервис»",
                "phone": "+7 (4112) 25-91-19",
                "address": "г. Якутск",
                "distance_km": 6.5,
            }
        ],
        "fire": [
            {
                "name": "ПСЧ-1 ФПС по Республике Саха (Якутия)",
                "phone": "101",
                "address": "г. Якутск",
                "distance_km": 4.2,
            }
        ],
        "medical": [
            {
                "name": "ГБУ РС(Я) «Станция скорой медицинской помощи»",
                "phone": "103",
                "address": "г. Якутск",
                "distance_km": 5.1,
            }
        ],
    },
    "forces_calculation": [
        {
            "scenario_name": "Привлечение ПАСФ при утечке природного газа",
            "items": [
                {
                    "name": "ПАСФ ООО «ГазСпасСервис»",
                    "unit": "подразделение",
                    "quantity": 1,
                    "location": "г. Якутск",
                }
            ],
        }
    ],
    "protective_equipment": [
        {
            "name": "Огнетушитель порошковый ОП-10",
            "type": "огнетушитель",
            "quantity": 6,
            "purpose": "Локализация очага возгорания до прибытия пожарной охраны",
        },
        {
            "name": "Противогаз фильтрующий гражданский",
            "type": "СИЗОД",
            "quantity": 4,
            "purpose": "Защита органов дыхания персонала при загазованности",
        },
    ],
    "material_reserve": {
        "fin_reserve_order": "№80-П от 19.02.2026",
        "fin_reserve_amount": "250 000 (двести пятьдесят тысяч) рублей",
        "insurance_company": "АО «СОГАЗ»",
    },
    "context_params": {
        "fin_reserve_order": "№80-П от 19.02.2026",
        "fin_reserve_amount": "250 000 (двести пятьдесят тысяч) рублей",
        "insurance_company": "АО «СОГАЗ»",
    },
    "retrieved_examples": [
        "Для сети газопотребления характерными сценариями являются разгерметизация газопровода, утечка газа в помещении котельной, образование газовоздушной смеси и воспламенение.",
        "Первоочередные действия персонала включают прекращение подачи газа, вывод людей из опасной зоны, вызов ПАСФ, пожарной охраны и скорой медицинской помощи.",
    ],
    "debug_meta": {
        "name": "gas_consumption_bakery",
        "created_for": "PMLA generation debug",
        "created_at": datetime(2026, 7, 6).isoformat(),
    },
}


def get_gas_consumption_bakery_context() -> dict:
    """Return a deep copy of the deterministic reference context."""
    return deepcopy(GAS_CONSUMPTION_BAKERY_CONTEXT)
