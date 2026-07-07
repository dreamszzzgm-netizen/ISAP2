"""Data Engine — сборка данных из карточки ОПО + БД."""
from __future__ import annotations

import logging

from src.application.engines.base import BaseEngine, DocumentContext, SectionContent
from src.application.engines.blocks import Block, ParagraphBlock, TableBlock
from src.application.services.references import (
    get_accidents,
    get_equipment_kit,
    get_notification_services,
    get_substance,
)

logger = logging.getLogger(__name__)


def _s(d: dict, key: str, default: str = "—") -> str:
    """
    Безопасный доступ к полю словаря: в отличие от d.get(key, default),
    подставляет default и тогда, когда ключ ЕСТЬ, но его значение None
    (например, NULL из БД) — иначе dict.get() вернёт буквальный None,
    и он попадёт в текст документа как строка "None".
    """
    value = d.get(key)
    return str(value) if value not in (None, "") else default


# Разделы, которые обрабатывает Data Engine (8 разделов, 0-10% AI)
ACCIDENT_SAMPLES = get_accidents(years=(2020, 2026), limit=9)


DATA_SECTIONS = {
    "section_1",       # Характеристика объекта (таблицы 1-3)
    "section_3",       # Аварийность (таблицы 7-9)
    "section_4",       # Силы и средства (таблица 10)
    "section_6",       # Состав и дислокация (таблицы 11-13)
    "section_8",       # Управление, связь (таблица 14)
    "section_13",      # Материально-техническое обеспечение
    "appendix_3",      # Состав ПАСФ
    "appendix_4",      # Оснащение ПАСФ
}


class DataEngine(BaseEngine):
    """
    Движок данных. Собирает информацию из карточки ОПО, БД и расчётов
    для генерации таблиц и списков без использования LLM.

    Обрабатывает 8 разделов: характеристика объекта, аварийность,
    силы и средства, состав/дислокация, управление, материальное обеспечение,
    приложения 3-4.
    """

    @property
    def name(self) -> str:
        return "data"

    def can_handle(self, section_id: str) -> bool:
        return section_id in DATA_SECTIONS

    async def generate(self, section_id: str, section_def: dict, context: DocumentContext) -> SectionContent:
        """Генерирует содержимое раздела на основе данных из контекста."""
        title = section_def.get("title", section_id)

        renderers = {
            "section_1": self._render_section_1,
            "section_3": self._render_section_3,
            "section_4": self._render_section_4,
            "section_6": self._render_section_6,
            "section_8": self._render_section_8,
            "section_13": self._render_section_13,
            "appendix_3": self._render_appendix_3,
            "appendix_4": self._render_appendix_4,
        }

        renderer = renderers.get(section_id)
        if renderer is None:
            blocks: list[Block] = [ParagraphBlock(text=f"[DataEngine: renderer not found for {section_id}]")]
        else:
            blocks = renderer(context)

        return SectionContent(
            section_id=section_id,
            title=title,
            engine_name=self.name,
            blocks=blocks,
        )

    def _render_section_1(self, ctx: DocumentContext) -> list[Block]:
        """Раздел 1 — Характеристика ОПО (Таблицы 1-3)."""
        org = ctx.organization
        fac = ctx.facility
        blocks: list[Block] = []

        # Таблица 1 — Общие сведения
        t1_data = {
            "Наименование объекта": _s(fac, "name"),
            "Регистрационный номер ОПО": _s(fac, "reg_number"),
            "Класс опасности": _s(fac, "hazard_class"),
            "Тип объекта": _s(fac, "facility_type"),
            "Место расположения": _s(fac, "address") if fac.get("address") not in (None, "") else _s(org, "address"),
            "Наименование организации": _s(org, "name"),
            "ИНН": _s(org, "inn"),
            "ОГРН": _s(org, "ogrn"),
            "Адрес организации": _s(org, "address"),
            "Телефон": _s(org, "phone"),
            "Email": _s(org, "email"),
        }
        blocks.append(TableBlock(
            headers=["Параметр", "Значение"],
            rows=[[k, v] for k, v in t1_data.items()],
            caption="Таблица 1. Общие сведения об организации и объекте",
        ))

        # Таблица 2 — Оборудование
        eq_headers = ["№ п/п", "Наименование", "Тип", "Заводской номер", "Год выпуска"]
        eq_rows = []
        for i, eq in enumerate(ctx.equipment, 1):
            eq_rows.append([
                str(i),
                _s(eq, "name"),
                _s(eq, "equipment_type"),
                _s(eq, "serial_number"),
                _s(eq, "manufacture_year"),
            ])
        if not eq_rows:
            eq_rows = [["—", "Сведения об оборудовании не предоставлены.", "—", "—", "—"]]
        blocks.append(TableBlock(
            headers=eq_headers,
            rows=eq_rows,
            caption="Таблица 2. Технические устройства ОПО",
        ))

        # Таблица 3 — Опасные вещества (обогащена справочником)
        sub_headers = [
            "№ п/п", "Наименование", "CAS", "Формула",
            "Класс опасн.", "Агр. сост.", "Кол-во, кг",
            "ПДК, мг/м³", "НКПР, %", "ВКПР, %",
        ]
        sub_rows = []
        for i, s in enumerate(ctx.substances, 1):
            name = _s(s, "name")
            ref = get_substance(name)
            if ref:
                sub_rows.append([
                    str(i),
                    name,
                    _s(ref, "cas_number"),
                    _s(ref, "chemical_formula"),
                    str(ref.get("hazard_class_gost", "—")),
                    _s(ref, "physical_state"),
                    _s(s, "quantity_kg"),
                    str(ref.get("mac_mg_m3", "—")),
                    str(ref.get("lower_flammable_limit_pct", "—")),
                    str(ref.get("upper_flammable_limit_pct", "—")),
                ])
            else:
                sub_rows.append([
                    str(i), name, _s(s, "cas_number"), "—", "—", "—",
                    _s(s, "quantity_kg"), "—", "—", "—",
                ])
        if not sub_rows:
            sub_rows = [["—", "Сведения об опасных веществах не предоставлены.", "—", "—", "—", "—", "—", "—", "—", "—"]]
        blocks.append(TableBlock(
            headers=sub_headers,
            rows=sub_rows,
            caption="Таблица 3. Опасные вещества, используемые/хранящиеся на объекте",
        ))

        return blocks

    def _render_section_3(self, ctx: DocumentContext) -> list[Block]:
        """Раздел 3 — Характеристика аварийности (Таблицы 7-9)."""
        blocks: list[Block] = []
        year = ctx.year

        # Информация из анкеты об авариях/инцидентах
        incidents = ctx.accidents_and_incidents or []
        has_incident_items = False
        for item in incidents:
            if not isinstance(item, dict):
                continue
            item_type = item.get("type", "")
            # Statement = "аварий не зарегистрированы" — выводим как абзац
            if item_type == "statement":
                desc = item.get("description", "")
                if desc:
                    blocks.append(ParagraphBlock(text=desc))
                continue
            # Требуют заполнения — пропускаем служебный маркер
            if item_type == "requires_manual_details":
                continue
            # Реальный инцидент — собираем таблицу
            has_incident_items = True

        if has_incident_items:
            inc_headers = [
                "Дата", "Тип события", "Место", "Описание",
                "Причина", "Последствия", "Принятые меры", "Документ-основание",
            ]
            inc_rows = []
            for item in incidents:
                if not isinstance(item, dict) or item.get("type") in ("statement", "requires_manual_details"):
                    continue
                row = [
                    _s(item, "date", "не указано"),
                    _s(item, "type", "не указано"),
                    _s(item, "place", "не указано"),
                    _s(item, "description", "не указано"),
                    _s(item, "cause", "не указано"),
                    _s(item, "consequences", "не указано"),
                    _s(item, "measures", "не указано"),
                    _s(item, "document", "не указано"),
                ]
                # Убираем пустые значения
                row = [v if v and v not in ("—", "None") else "не указано" for v in row]
                inc_rows.append(row)
            if inc_rows:
                blocks.append(TableBlock(
                    headers=inc_headers,
                    rows=inc_rows,
                    caption="Сведения об авариях и инцидентах на объекте",
                ))

        # Таблица 7 — Травматизм за 3 года
        t7_headers = ["№ п/п", "Год", "Количество травмированных", "Количество погибших", "Причина"]
        t7_rows = [[str(i), str(y), "—", "—", "—"] for i, y in enumerate(range(year-2, year+1), 1)]
        blocks.append(TableBlock(
            headers=t7_headers,
            rows=t7_rows,
            caption=f"Таблица 7. Данные о травматизме на объекте за {year-2}-{year}",
        ))

        # Таблица 8 — Аварийность за 3 года
        t8_headers = ["№ п/п", "Год", "Количество аварий", "Материальный ущерб", "Последствия"]
        t8_rows = [[str(i), str(y), "—", "—", "—"] for i, y in enumerate(range(year-2, year+1), 1)]
        blocks.append(TableBlock(
            headers=t8_headers,
            rows=t8_rows,
            caption=f"Таблица 8. Данные об аварийности на объекте за {year-2}-{year}",
        ))

        # Таблица 9 — Аварии на аналогичных объектах (из справочника)
        t9_headers = ["Дата", "Организация", "Тип аварии", "Характер", "Причины", "Последствия"]
        facility_type = ctx.facility.get("facility_type") if ctx.facility else None
        accidents = get_accidents(facility_type=facility_type, years=(2020, 2026), limit=15)
        accidents = ACCIDENT_SAMPLES + [
            acc for acc in accidents
            if acc.get("organization") not in {sample.get("organization") for sample in ACCIDENT_SAMPLES}
        ]
        accidents = accidents[:15]
        if not accidents:
            accidents = get_accidents(years=(2020, 2026), limit=10)
        t9_rows = []
        for acc in accidents:
            causes = "; ".join(filter(None, [
                _s(acc, "causes_technical") if acc.get("causes_technical") and acc["causes_technical"] != "В настоящее время ведётся расследование технических причин аварии." else None,
                _s(acc, "causes_organizational") if acc.get("causes_organizational") and acc["causes_organizational"] != "В настоящее время ведётся расследование организационных причин аварии." else None,
            ])) or "—"
            t9_rows.append([
                _s(acc, "date"),
                _s(acc, "organization"),
                _s(acc, "type"),
                _s(acc, "description"),
                causes,
                _s(acc, "consequences"),
            ])
        blocks.append(TableBlock(
            headers=t9_headers,
            rows=t9_rows,
            caption="Таблица 9. Аварии на аналогичных объектах (2020-2025)",
        ))

        return blocks

    def _resource_name(self, category: str, name: str) -> str:
        lower = str(name).lower()
        if "противогаз" in lower or "сизод" in lower:
            return f"СИЗОД: {name}"
        if "газоанализатор" in lower:
            return f"Газоанализатор: {name}"
        return f"{category}: {name}"

    @staticmethod
    def _resource_type_label(item: dict) -> str:
        """Человекочитаемая метка типа ресурса."""
        raw = (item.get("type") or "").lower()
        mapping = {
            "control": "Контрольно-измерительный",
            "firefighting": "Пожарный",
            "ppe": "Средства индивидуальной защиты",
            "rescue": "Спасательный",
            "medical": "Медицинский",
            "communication": "Средство связи",
            "tools": "Инструмент",
            "equipment": "Оборудование",
        }
        return mapping.get(raw, raw or "не указано")

    def _render_section_4(self, ctx: DocumentContext) -> list[Block]:
        """Раздел 4 — Количество необходимых сил и средств (Таблица 10)."""
        blocks: list[Block] = []

        facility_type = ctx.facility.get("facility_type") if ctx.facility else None
        kit = get_equipment_kit(facility_type) if facility_type else get_equipment_kit("default")

        t10_headers = [
            "№ п/п", "Наименование", "Тип", "Количество",
            "Место хранения", "Ответственное лицо", "Назначение",
        ]
        t10_rows = []
        idx = 1
        for category, key in [("СИЗ", "ppe"), ("Инструмент", "tools"), ("Оборудование", "equipment")]:
            for item in kit.get(key, []):
                t10_rows.append([
                    str(idx),
                    self._resource_name(category, item.get("name", "—")),
                    category,
                    item.get("quantity", "не указано"),
                    item.get("location", "не указано"),
                    "не указано",
                    "не указано",
                ])
                idx += 1
        for item in ctx.protective_equipment:
            t10_rows.append([
                str(idx),
                _s(item, "name", "не указано"),
                self._resource_type_label(item),
                _s(item, "quantity", "не указано"),
                _s(item, "location") if item.get("location") else _s(item, "storage_place", "не указано"),
                _s(item, "responsible_person", "не указано"),
                _s(item, "purpose", "не указано"),
            ])
            idx += 1
        # Заменяем — и None на «не указано»
        for row in t10_rows:
            for i in range(len(row)):
                if row[i] in ("—", "None", ""):
                    row[i] = "не указано"
        if not t10_rows:
            t10_rows = [["—", "Сведения о ресурсах не предоставлены.", "—", "—", "—", "—", "—"]]
        blocks.append(TableBlock(
            headers=t10_headers,
            rows=t10_rows,
            caption="Таблица 10. Материально-технические ресурсы для ликвидации аварий",
        ))

        return blocks

    def _render_section_6(self, ctx: DocumentContext) -> list[Block]:
        """Раздел 6 — Состав и дислокация сил (Таблицы 11-13)."""
        blocks: list[Block] = []
        org = ctx.organization

        # Таблица 11 — Силы и средства
        t11_headers = ["№ п/п", "Наименование подразделения", "Количество", "Место дислокации"]
        t11_rows = [
            ["1", "Аварийно-спасательная бригада", "1", _s(org, "address")],
            ["2", "Пожарная охрана", "1", "Ближайшая ПЧ"],
            ["3", "Аварийная газовая служба", "1", "Диспетчерская"],
            ["4", "Медицинская служба", "1", "Медпункт"],
        ]
        blocks.append(TableBlock(
            headers=t11_headers,
            rows=t11_rows,
            caption="Таблица 11. Силы и средства для локализации и ликвидации аварий",
        ))

        # Таблица 12 — Состав
        t12_headers = ["Должность", "ФИО", "Телефон"]
        persons = ctx.persons or []
        t12_rows = []
        for p in persons[:10]:
            t12_rows.append([
                _s(p, "position"),
                _s(p, "full_name"),
                _s(p, "phone"),
            ])
        if not t12_rows:
            t12_rows = [["—", "—", "—"]]
        blocks.append(TableBlock(
            headers=t12_headers,
            rows=t12_rows,
            caption="Таблица 12. Состав сил для ликвидации аварий",
        ))

        # Таблица 13 — Дислокация
        t13_headers = ["Подразделение", "Адрес", "Зона ответственности"]
        t13_rows = [
            [_s(org, "name"), _s(org, "address"), "Территория объекта"],
            ["Пожарная охрана", "Ближайшая ПЧ", "Пожарная безопасность"],
            ["Аварийная газовая служба", "Диспетчерская", "Газоснабжение"],
        ]
        blocks.append(TableBlock(
            headers=t13_headers,
            rows=t13_rows,
            caption="Таблица 13. Дислокация подразделений",
        ))

        return blocks

    # Маппинг ключей notification_scheme → русские описания действий
    _NOTIFICATION_ACTION_MAP: list[tuple[str, str]] = [
        ("first_receiver", "Первое сообщение об аварии принимает"),
        ("incident_commander", "Общее руководство первоочередными действиями осуществляет"),
        ("pasf_caller", "Вызов ПАСФ осуществляет"),
        ("fire_caller", "Вызов пожарной охраны осуществляет"),
        ("medical_caller", "Вызов скорой медицинской помощи осуществляет"),
        ("shutdown_responsible", "Отключение оборудования выполняет"),
        ("evacuation_responsible", "Эвакуацию персонала организует"),
        ("service_meeting_responsible", "Встречу прибывающих аварийных служб обеспечивает"),
    ]

    def _render_section_8(self, ctx: DocumentContext) -> list[Block]:
        """Раздел 8 — Управление, связь, оповещение (Таблица 14 + текст)."""
        blocks: list[Block] = []

        facility_type = ctx.facility.get("facility_type") if ctx.facility else None
        template = get_notification_services(facility_type) if facility_type else get_notification_services("default")
        persons = ctx.persons or []

        # --- Текстовый блок: порядок оповещения из анкеты ---
        notification = ctx.notification_scheme or {}
        notification_lines = []
        for key, action_prefix in self._NOTIFICATION_ACTION_MAP:
            value = notification.get(key)
            if value:
                notification_lines.append(f"{action_prefix} {value}.")
        if notification_lines:
            blocks.append(ParagraphBlock(text="Порядок оповещения при аварии:"))
            for line in notification_lines:
                blocks.append(ParagraphBlock(text=line))
            blocks.append(ParagraphBlock(text=""))

        # --- Таблица 14: Схема оповещения ---
        t14_headers = ["№ п/п", "Должность / Служба", "ФИО / Наименование", "Телефон", "Порядок оповещения"]
        t14_rows = []

        for item in template.get("internal", []):
            position = item.get("position", "")
            person = None
            for p in persons:
                if position.lower() in _s(p, "position").lower():
                    person = p
                    break
            t14_rows.append([
                str(item.get("order", len(t14_rows) + 1)),
                position,
                _s(person, "full_name") if person else "не указано",
                _s(person, "phone") if person else "не указано",
                "Немедленно",
            ])

        existing_names = {row[2] for row in t14_rows}
        for person in persons:
            full_name = _s(person, "full_name")
            if full_name not in existing_names:
                t14_rows.append([
                    str(len(t14_rows) + 1),
                    _s(person, "position"),
                    full_name,
                    _s(person, "phone"),
                    "Немедленно",
                ])

        # Роли из анкеты — с русскими названиями
        _notification_russian_labels = {
            "first_receiver": "Приём первого сообщения",
            "incident_commander": "Руководитель первоочередных действий",
            "pasf_caller": "Вызов ПАСФ",
            "fire_caller": "Вызов пожарной охраны",
            "medical_caller": "Вызов скорой помощи",
            "shutdown_responsible": "Отключение оборудования",
            "evacuation_responsible": "Эвакуация персонала",
            "service_meeting_responsible": "Встреча аварийных служб",
        }
        for key, russian_label in _notification_russian_labels.items():
            value = notification.get(key)
            if value:
                t14_rows.append([
                    str(len(t14_rows) + 1),
                    russian_label,
                    str(value),
                    "—",
                    "Немедленно",
                ])

        for item in template.get("external", []):
            t14_rows.append([
                str(item.get("order", len(t14_rows) + 1)),
                item.get("service", "—"),
                "—",
                item.get("phone_primary", "—"),
                "По вызову",
            ])

        # Заменяем пустые значения
        for row in t14_rows:
            for i in range(len(row)):
                if row[i] in ("—", "None", ""):
                    row[i] = "не указано"

        if not t14_rows:
            t14_rows = [["1", "—", "—", "—", "—"]]
        blocks.append(TableBlock(
            headers=t14_headers,
            rows=t14_rows,
            caption="Таблица 14. Схема оповещения",
        ))

        return blocks

    @staticmethod
    def _format_date_ru(date_str: str) -> str:
        """Конвертирует YYYY-MM-DD → DD.MM.YYYY для официального текста."""
        if not date_str or date_str in ("—", "None"):
            return ""
        try:
            parts = date_str.split("-")
            if len(parts) == 3:
                return f"{parts[2]}.{parts[1]}.{parts[0]}"
        except (ValueError, IndexError):
            pass
        return date_str

    def _render_section_13(self, ctx: DocumentContext) -> list[Block]:
        """Раздел 13 — Материально-техническое обеспечение."""
        blocks: list[Block] = []
        org = ctx.organization

        blocks.append(ParagraphBlock(text="Финансовое обеспечение мероприятий по локализации и ликвидации аварий"))
        blocks.append(ParagraphBlock(text="осуществляется за счёт средств организации в соответствии с ГОСТ Р 22.10.03-2020."))
        blocks.append(ParagraphBlock(text="Сумма финансового резерва определяется исходя из:"))
        blocks.append(ParagraphBlock(text="- стоимости аварийно-спасательных работ;"))
        blocks.append(ParagraphBlock(text="- стоимости восстановления повреждённого оборудования;"))
        blocks.append(ParagraphBlock(text="- компенсации пострадавшим."))
        blocks.append(ParagraphBlock(text=f"Эксплуатирующая организация: {_s(org, 'name')}"))
        blocks.append(ParagraphBlock(text=f"Юридический адрес: {_s(org, 'address')}"))
        blocks.append(ParagraphBlock(text=f"ИНН: {_s(org, 'inn')}"))

        # --- Финансовый резерв ---
        reserve = ctx.material_reserve or {}
        order = reserve.get("fin_reserve_order", "")
        amount = reserve.get("fin_reserve_amount", "")

        has_reserve = order and order not in ("—", "None") and amount and amount not in ("—", "None")
        if has_reserve:
            # Извлекаем номер и дату из строки вида "12-ПБ от 2026-01-15"
            order_number = order
            order_date = ""
            if " от " in order:
                parts = order.split(" от ", 1)
                order_number = parts[0]
                order_date = self._format_date_ru(parts[1])

            date_text = f" от {order_date}" if order_date else ""
            blocks.append(ParagraphBlock(text=(
                f"Финансовый резерв для локализации и ликвидации последствий аварий "
                f"создан на основании приказа № {order_number}{date_text}. "
                f"Размер финансового резерва составляет {amount} руб."
            )))
            responsible = reserve.get("responsible")
            if responsible and responsible not in ("—", "None"):
                blocks.append(ParagraphBlock(text=(
                    f"Ответственным за учёт и использование финансового резерва "
                    f"назначен {responsible}."
                )))
        else:
            blocks.append(ParagraphBlock(text=(
                "Сведения о создании финансового резерва в представленных исходных данных отсутствуют."
            )))

        # --- Страхование ---
        # Данные могут быть в ctx.insurance (из прямого контекста) или
        # в material_reserve (из анкеты — адаптированной).
        insurance = ctx.insurance or {}
        company = insurance.get("company") or reserve.get("insurance_company") or ""
        contract_number = insurance.get("contract_number") or reserve.get("insurance_contract") or ""
        valid_until = insurance.get("valid_until") or reserve.get("insurance_valid_until") or ""
        insured_amount = insurance.get("insured_amount") or reserve.get("insurance_amount") or ""
        has_contract = insurance.get("has_contract") if "has_contract" in insurance else bool(company and company not in ("—", "None"))

        if has_contract and company and company not in ("—", "None"):
            valid_until_text = ""
            if valid_until and valid_until not in ("—", "None"):
                formatted_date = self._format_date_ru(valid_until)
                valid_until_text = f" Срок действия договора — до {formatted_date}."
            amount_text = ""
            if insured_amount and insured_amount not in ("—", "None"):
                amount_text = f" Страховая сумма составляет {insured_amount} руб."
            contract_text = f" по договору № {contract_number}" if contract_number and contract_number not in ("—", "None") else ""
            blocks.append(ParagraphBlock(text=(
                f"Гражданская ответственность владельца опасного производственного объекта "
                f"за причинение вреда в результате аварии застрахована в {company}"
                f"{contract_text}.{valid_until_text}{amount_text}"
            )))
        else:
            blocks.append(ParagraphBlock(text=(
                "Сведения о договоре обязательного страхования гражданской ответственности "
                "в исходных данных отсутствуют."
            )))

        return blocks

    def _render_appendix_3(self, ctx: DocumentContext) -> list[Block]:
        """Приложение 3 — Состав ПАСФ."""
        blocks: list[Block] = []

        blocks.append(ParagraphBlock(text="В состав ПАСФ входят:"))
        blocks.append(ParagraphBlock(text="1. Руководитель аварийно-спасательных работ"))
        blocks.append(ParagraphBlock(text="2. Специалисты по ликвидации аварий"))
        blocks.append(ParagraphBlock(text="3. Спасатели"))
        blocks.append(ParagraphBlock(text="4. Водители-механики"))

        if ctx.persons:
            blocks.append(ParagraphBlock(text="Личный состав ПАСФ:"))
            for i, p in enumerate(ctx.persons[:10], 1):
                blocks.append(ParagraphBlock(text=f"{i}. {_s(p, 'full_name')} — {_s(p, 'position')}"))

        return blocks

    def _render_appendix_4(self, ctx: DocumentContext) -> list[Block]:
        """Приложение 4 — Оснащение ПАСФ (из справочника)."""
        blocks: list[Block] = []

        facility_type = ctx.facility.get("facility_type") if ctx.facility else None
        kit = get_equipment_kit(facility_type) if facility_type else get_equipment_kit("default")

        t_headers = ["№ п/п", "Категория", "Наименование", "Количество", "Место хранения"]
        t_rows = []
        idx = 1
        for category, key in [("СИЗ", "ppe"), ("Инструмент", "tools"), ("Оборудование", "equipment")]:
            for item in kit.get(key, []):
                t_rows.append([
                    str(idx),
                    category,
                    self._resource_name(category, item.get("name", "—")),
                    item.get("quantity", "—"),
                    item.get("location", "—"),
                ])
                idx += 1
        if not t_rows:
            t_rows = [["—", "—", "Сведения об оснащении не предоставлены.", "—", "—"]]
        blocks.append(TableBlock(
            headers=t_headers,
            rows=t_rows,
            caption="Оснащение ПАСФ",
        ))

        return blocks
