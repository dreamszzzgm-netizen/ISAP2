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

    def _render_section_4(self, ctx: DocumentContext) -> list[Block]:
        """Раздел 4 — Количество необходимых сил и средств (Таблица 10)."""
        blocks: list[Block] = []

        facility_type = ctx.facility.get("facility_type") if ctx.facility else None
        kit = get_equipment_kit(facility_type) if facility_type else get_equipment_kit("default")

        t10_headers = ["№ п/п", "Наименование ресурсов", "Количество", "Место хранения"]
        t10_rows = []
        idx = 1
        for category, key in [("СИЗ", "ppe"), ("Инструмент", "tools"), ("Оборудование", "equipment")]:
            for item in kit.get(key, []):
                t10_rows.append([
                    str(idx),
                    self._resource_name(category, item.get("name", "—")),
                    item.get("quantity", "—"),
                    item.get("location", "—"),
                ])
                idx += 1
        for item in ctx.protective_equipment:
            t10_rows.append([
                str(idx),
                _s(item, "name"),
                _s(item, "quantity"),
                item.get("location") or item.get("storage_place") or "—",
            ])
            idx += 1
        if not t10_rows:
            t10_rows = [["—", "Сведения о ресурсах не предоставлены.", "—", "—"]]
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

    def _render_section_8(self, ctx: DocumentContext) -> list[Block]:
        """Раздел 8 — Управление, связь, оповещение (Таблица 14)."""
        blocks: list[Block] = []

        facility_type = ctx.facility.get("facility_type") if ctx.facility else None
        template = get_notification_services(facility_type) if facility_type else get_notification_services("default")
        persons = ctx.persons or []

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
                _s(person, "full_name") if person else "—",
                _s(person, "phone") if person else "—",
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

        notification = ctx.notification_scheme or {}
        for key, label in [
            ("first_receiver", "first receiver"),
            ("incident_commander", "incident commander"),
            ("pasf_caller", "PASF caller"),
            ("fire_caller", "fire caller"),
            ("medical_caller", "medical caller"),
            ("shutdown_responsible", "shutdown responsible"),
            ("evacuation_responsible", "evacuation responsible"),
            ("service_meeting_responsible", "service meeting responsible"),
        ]:
            value = notification.get(key)
            if value:
                t14_rows.append([
                    str(len(t14_rows) + 1),
                    label,
                    str(value),
                    "—",
                    "questionnaire",
                ])

        for item in template.get("external", []):
            t14_rows.append([
                str(item.get("order", len(t14_rows) + 1)),
                item.get("service", "—"),
                "—",
                item.get("phone_primary", "—"),
                "По вызову",
            ])

        if not t14_rows:
            t14_rows = [["1", "—", "—", "—", "—"]]
        blocks.append(TableBlock(
            headers=t14_headers,
            rows=t14_rows,
            caption="Таблица 14. Схема оповещения",
        ))

        return blocks

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

        reserve = ctx.material_reserve or {}
        if reserve:
            blocks.append(ParagraphBlock(text=f"Financial reserve order: {reserve.get('fin_reserve_order', '—')}"))
            blocks.append(ParagraphBlock(text=f"Financial reserve amount: {reserve.get('fin_reserve_amount', '—')}"))
            blocks.append(ParagraphBlock(text=f"Insurance company: {reserve.get('insurance_company', '—')}"))
            blocks.append(ParagraphBlock(text=f"Insurance contract: {reserve.get('insurance_contract', '—')}"))
            blocks.append(ParagraphBlock(text=f"Insurance valid until: {reserve.get('insurance_valid_until', '—')}"))

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
