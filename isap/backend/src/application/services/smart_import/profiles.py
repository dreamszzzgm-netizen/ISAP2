"""Smart import profiles and column mapping rules.

The first implementation intentionally avoids fully autonomous LLM decisions.
It relies on deterministic synonyms and safe normalizers. LLM can be added later
as an assistant for ambiguous columns, but user confirmation remains mandatory.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable

Normalizer = Callable[[Any], Any]


def normalize_header(value: str) -> str:
    """Normalize Excel/CSV column header for deterministic matching."""
    value = str(value or "").strip().lower().replace("ё", "е")
    value = re.sub(r"[\n\r\t]+", " ", value)
    value = re.sub(r"[^a-zа-я0-9]+", "_", value)
    return value.strip("_")


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    text = re.sub(r"\s+", " ", text)
    return text


def normalize_phone(value: Any) -> str:
    text = normalize_text(value)
    if not text:
        return ""
    # Preserve extension-like text but normalize common separators.
    text = text.replace("—", "-").replace("–", "-")
    return re.sub(r"\s+", " ", text)


def normalize_service_type(value: Any) -> str:
    text = normalize_header(normalize_text(value))
    if text in {"пожарная", "пожарная_охрана", "псч", "мчс", "fire"}:
        return "fire"
    if text in {"скорая", "медицинская", "medical", "ambulance"}:
        return "medical"
    if text in {"полиция", "мвд", "police"}:
        return "police"
    if text in {"газ", "газовая", "газовая_служба", "gas"}:
        return "gas"
    if text in {"еддс", "edds"}:
        return "edds"
    if text in {"администрация", "administration"}:
        return "administration"
    return text or "fire"


def split_list(value: Any) -> list[str]:
    text = normalize_text(value)
    if not text:
        return []
    parts = re.split(r"[;\n]+", text)
    return [part.strip(" -•\t") for part in parts if part.strip(" -•\t")]


@dataclass(frozen=True)
class ImportField:
    canonical: str
    title: str
    synonyms: list[str]
    required: bool = False
    normalizer: Normalizer = normalize_text

    def all_normalized_headers(self) -> set[str]:
        return {normalize_header(item) for item in [self.canonical, self.title, *self.synonyms]}


@dataclass(frozen=True)
class ImportProfile:
    code: str
    title: str
    description: str
    target_table: str
    fields: list[ImportField]
    duplicate_keys: list[str] = field(default_factory=list)

    @property
    def required_fields(self) -> list[str]:
        return [field.canonical for field in self.fields if field.required]

    def map_headers(self, headers: list[str]) -> dict[str, str]:
        """Return mapping from source header to canonical field."""
        normalized_source = {header: normalize_header(header) for header in headers}
        mapping: dict[str, str] = {}
        used: set[str] = set()
        for source, norm_source in normalized_source.items():
            for field in self.fields:
                if field.canonical in used:
                    continue
                if norm_source in field.all_normalized_headers():
                    mapping[source] = field.canonical
                    used.add(field.canonical)
                    break
        return mapping

    def normalize_row(self, raw_row: dict[str, Any], header_mapping: dict[str, str]) -> dict[str, Any]:
        by_field = {field.canonical: field for field in self.fields}
        normalized: dict[str, Any] = {}
        for source_header, value in raw_row.items():
            canonical = header_mapping.get(source_header)
            if not canonical:
                continue
            field_def = by_field[canonical]
            normalized[canonical] = field_def.normalizer(value)
        return normalized

    def validate_row(self, row: dict[str, Any]) -> tuple[list[str], list[str]]:
        errors: list[str] = []
        warnings: list[str] = []
        for field_name in self.required_fields:
            if not row.get(field_name):
                errors.append(f"Не заполнено обязательное поле: {field_name}")
        for key in self.duplicate_keys:
            if key not in row or not row.get(key):
                warnings.append(f"Нет поля для проверки дублей: {key}")
        return errors, warnings


IMPORT_PROFILES: dict[str, ImportProfile] = {
    "fire_departments": ImportProfile(
        code="fire_departments",
        title="Пожарные подразделения",
        description="Импорт ПСЧ/ПЧ/МЧС с адресами и телефонами диспетчеров.",
        target_table="emergency_services",
        duplicate_keys=["name", "address"],
        fields=[
            ImportField("name", "Наименование", ["подразделение", "пожарная часть", "псч", "пч", "мчс"], True),
            ImportField("address", "Адрес", ["местонахождение", "адрес подразделения"], True),
            ImportField("phone", "Телефон", ["тел", "номер", "контакт", "дежурная часть"], False, normalize_phone),
            ImportField("dispatcher_phone", "Телефон диспетчера", ["диспетчер", "тел диспетчера", "номер диспетчера"], False, normalize_phone),
            ImportField("municipality", "Муниципальный район", ["район", "мр", "муниципалитет"]),
            ImportField("settlement", "Населённый пункт", ["город", "село", "нп", "населенный пункт"]),
            ImportField("latitude", "Широта", ["lat", "координата широта"]),
            ImportField("longitude", "Долгота", ["lon", "lng", "координата долгота"]),
            ImportField("service_area", "Зона обслуживания", ["район обслуживания", "территория обслуживания"]),
            ImportField("notes", "Примечание", ["комментарий", "дополнительно"]),
        ],
    ),
    "pasf_units": ImportProfile(
        code="pasf_units",
        title="ПАСФ / АСФ",
        description="Импорт профессиональных аварийно-спасательных формирований.",
        target_table="emergency_rescue_units",
        duplicate_keys=["name", "certificate_number"],
        fields=[
            ImportField("name", "Наименование", ["асф", "пасф", "формирование", "организация"], True),
            ImportField("short_name", "Краткое наименование", ["сокращенное", "сокращенное наименование"]),
            ImportField("legal_address", "Юридический адрес", ["юр адрес", "адрес юридический"]),
            ImportField("actual_address", "Фактический адрес", ["адрес", "место дислокации", "дислокация"]),
            ImportField("dispatch_phone", "Телефон диспетчера", ["телефон", "тел", "диспетчер"], False, normalize_phone),
            ImportField("email", "Email", ["почта", "e-mail"]),
            ImportField("manager_name", "Руководитель", ["начальник", "директор"]),
            ImportField("certificate_number", "Номер свидетельства", ["свидетельство", "№ свидетельства", "номер аттестации"], True),
            ImportField("certificate_date", "Дата свидетельства", ["дата выдачи", "дата свидетельства"]),
            ImportField("certificate_valid_until", "Срок действия свидетельства", ["действует до", "срок действия"]),
            ImportField("permitted_work_types", "Виды работ", ["право ведения работ", "виды аварийно-спасательных работ"], False, split_list),
            ImportField("equipment_passport", "Паспорт / оснащение", ["паспорт асф", "оснащение", "табель оснащения"], False, split_list),
            ImportField("staff_count", "Количество спасателей", ["численность", "спасатели"]),
            ImportField("readiness_mode", "Режим готовности", ["готовность", "режим"]),
            ImportField("service_area", "Район обслуживания", ["территория обслуживания", "зона обслуживания"]),
            ImportField("notes", "Примечание", ["комментарий", "дополнительно"]),
        ],
    ),
    "emergency_services": ImportProfile(
        code="emergency_services",
        title="Аварийные службы",
        description="Импорт пожарных, скорой, полиции, газовой службы, ЕДДС с адресами и телефонами.",
        target_table="emergency_services",
        duplicate_keys=["name", "address"],
        fields=[
            ImportField("service_type", "Тип службы", ["вид службы", "тип", "категория"], False, normalize_service_type),
            ImportField("name", "Наименование", ["служба", "подразделение", "наименование"], True),
            ImportField("address", "Адрес", ["местонахождение", "адрес подразделения"], False),
            ImportField("phone", "Телефон", ["тел", "номер", "контакт", "дежурная часть"], False, normalize_phone),
            ImportField("dispatcher_phone", "Телефон диспетчера", ["диспетчер", "тел диспетчера", "номер диспетчера", "диспетчерский телефон"], False, normalize_phone),
            ImportField("municipality", "Муниципальный район", ["район", "мр", "муниципалитет"]),
            ImportField("settlement", "Населённый пункт", ["город", "село", "нп", "населенный пункт"]),
            ImportField("latitude", "Широта", ["lat", "координата широта"]),
            ImportField("longitude", "Долгота", ["lon", "lng", "координата долгота"]),
            ImportField("service_area", "Район обслуживания", ["зона обслуживания", "территория обслуживания"]),
            ImportField("notes", "Примечание", ["комментарий", "дополнительно"]),
        ],
    ),
    "pmla_questionnaire": ImportProfile(
        code="pmla_questionnaire",
        title="Анкета ПМЛА",
        description="Импорт ответов анкеты генерации ПМЛА из Excel или DOCX.",
        target_table="pmla_questionnaires",
        duplicate_keys=["facility_reg_number"],
        fields=[
            ImportField("organization_name", "Организация", ["заказчик", "эксплуатирующая организация"], True),
            ImportField("facility_name", "ОПО", ["объект", "опасный объект", "наименование опо"], True),
            ImportField("facility_reg_number", "Регистрационный номер ОПО", ["рег номер", "регистрационный номер"]),
            ImportField("has_incidents", "Были аварии/инциденты", ["аварии", "инциденты", "были инциденты"]),
            ImportField("incident_description", "Описание аварий/инцидентов", ["описание инцидентов", "сведения об авариях"]),
            ImportField("operation_mode", "Режим работы", ["режим", "сменность"]),
            ImportField("staff_per_shift", "Персонал в смену", ["численность", "людей в смену"]),
            ImportField("selected_scenarios", "Сценарии", ["сценарии аварий", "аварийные сценарии"], False, split_list),
            ImportField("custom_scenarios", "Другое / пользовательские сценарии", ["другое", "дополнительные сценарии"], False, split_list),
            ImportField("resources", "Силы и средства", ["оснащение", "средства", "аварийный запас"], False, split_list),
            ImportField("pasf_name", "ПАСФ", ["асф", "аварийно спасательное формирование"]),
            ImportField("financial_reserve", "Финансовый резерв", ["резерв", "приказ о резерве"]),
            ImportField("training", "Тренировки", ["учения", "тренировка", "практические тренировки"]),
            ImportField("attachments", "Приложения", ["схемы", "приложения", "документы"], False, split_list),
        ],
    ),
}
