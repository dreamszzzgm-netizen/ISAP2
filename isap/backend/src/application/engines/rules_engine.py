"""Rules Engine — параметризованные шаблоны правил по типу ОПО."""
from __future__ import annotations

import logging

from src.application.engines.base import BaseEngine, DocumentContext, SectionContent
from src.application.engines.blocks import Block, ParagraphBlock, TableBlock
from src.application.services.references import (
    get_notification_services,
    get_positions,
    get_scenario_instructions,
)

logger = logging.getLogger(__name__)

# Разделы, которые обрабатывает Rules Engine (6 разделов, 15-25% AI)
RULES_SECTIONS = {
    "section_5",    # Взаимодействие сил
    "section_7",    # Готовность сил
    "section_9",    # Обмен информацией
    "section_10",   # Первоочередные действия
    "section_11",   # Действия персонала
    "section_12",   # Безопасность населения
}

# Правила по типам ОПО (параметризованные шаблоны)
FACILITY_RULES: dict[str, dict] = {
    "Сеть газопотребления": {
        "section_5": {
            "title": "Организация взаимодействия сил и средств",
            "text": (
                "Взаимодействие сил и средств при локализации и ликвидации аварий "
                "на сети газопотребления осуществляется в соответствии с планом "
                "взаимодействия, утверждённым руководителем организации.\n\n"
                "Основные принципы взаимодействия:\n"
                "1. Единоначалие — общее руководство осуществляет руководитель аварийно-спасательных работ.\n"
                "2. Взаимная информированность — все участники непрерывно обмениваются информацией.\n"
                "3. Координация действий — согласование действий через диспетчерскую службу.\n"
                "4. Безопасность персонала — приоритет жизни и здоровья людей.\n"
                "5. Поэтапность — последовательность действий от локализации до ликвидации.\n\n"
                "Порядок взаимодействия:\n"
                "- Диспетчер координирует действия всех подразделений;\n"
                "- Аварийная газовая служба определяет место и характер повреждения;\n"
                "- Пожарная охрана обеспечивает готовность к тушению;\n"
                "- Медицинская служба организует оказание помощи;\n"
                "- Служба охраны обеспечивает оцепление зоны аварии."
            ),
        },
        "section_7": {
            "title": "Порядок обеспечения готовности сил и средств",
            "text": (
                "Готовность сил и средств к локализации и ликвидации аварий "
                "обеспечивается следующими мероприятиями:\n\n"
                "1. Постоянная готовность:\n"
                "   - Ежедневная проверка технических средств связи;\n"
                "   - Еженедельная проверка газоанализаторов;\n"
                "   - Ежемесячная проверка СИЗОД;\n"
                "   - Ежеквартальная проверка огнетушителей.\n\n"
                "2. Тренировочные мероприятия:\n"
                "   - Ежемесячные тактические тренировки;\n"
                "   - Ежеквартальные учения с привлечением аварийных служб;\n"
                "   - Ежегодные комплексные учения.\n\n"
                "3. Обучение персонала:\n"
                "   - Ежегодная аттестация по промышленной безопасности;\n"
                "   - Обучение действиям при авариях;\n"
                "   - Инструктаж по плану ликвидации аварий.\n\n"
                "4. Техническое обслуживание:\n"
                "   - Плановое техническое обслуживание оборудования;\n"
                "   - Своевременная замена изношенных деталей;\n"
                "   - Контроль за состоянием газоанализаторов."
            ),
        },
        "section_9": {
            "title": "Система взаимного обмена информацией",
            "text": (
                "Обмен информацией при локализации и ликвидации аварий "
                "осуществляется через следующие каналы:\n\n"
                "1. Диспетчерская связь — основной канал обмена информацией.\n"
                "2. Мобильная связь — для связи с выездными подразделениями.\n"
                "3. Радиосвязь — для связи в зоне аварии.\n"
                "4. Громкоговорящая связь — для оповещения персонала.\n\n"
                "Информация передаётся:\n"
                "- О начале аварии — немедленно;\n"
                "- О характере аварии — в течение 5 минут;\n"
                "- О мерах по ликвидации — каждые 15 минут;\n"
                "- О завершении работ — немедленно.\n\n"
                "Форма передачи информации:\n"
                "- Устная — через диспетчера;\n"
                "- Письменная — акт о аварии;\n"
                "- Электронная — через систему мониторинга."
            ),
        },
        "section_10": {
            "title": "Первоочередные действия по локализации и ликвидации аварий",
            "text": (
                "Первоочередные действия при аварии на сети газопотребления:\n\n"
                "1. При обнаружении утечки газа:\n"
                "   - Немедленно сообщить диспетчеру;\n"
                "   - Перекрыть газ на ближайшем вентиле;\n"
                "   - Не допускать открытого огня;\n"
                "   - Проветрить помещение;\n"
                "   - Вызвать аварийную газовую службу.\n\n"
                "2. При горении газа:\n"
                "   - Немедленно эвакуировать людей;\n"
                "   - Перекрыть газ до горящего участка;\n"
                "   - Вызвать пожарную охрану;\n"
                "   - Охлаждать конструкции водой.\n\n"
                "3. При взрыве:\n"
                "   - Начать эвакуацию на 200 м;\n"
                "   - Перекрыть газ на всех подходах;\n"
                "   - Вызвать МЧС;\n"
                "   - Оцепить территорию;\n"
                "   - Оказать первую помощь."
            ),
        },
        "section_11": {
            "title": "Действия производственного персонала при угрозе и возникновении аварий",
            "text": (
                "Действия персонала при угрозе аварии:\n\n"
                "1. Диспетчер:\n"
                "   - Принять сигнал об аварии;\n"
                "   - Зафиксировать время и характер аварии;\n"
                "   - Оповестить руководителя смены;\n"
                "   - Вызвать аварийные службы;\n"
                "   - Координировать действия.\n\n"
                "2. Работник объекта:\n"
                "   - Перекрыть газ на вентиле;\n"
                "   - Проветрить помещение;\n"
                "   - Эвакуировать людей;\n"
                "   - Не допускать искрообразования.\n\n"
                "3. Руководитель смены:\n"
                "   - Принять руководство ликвидацией аварии;\n"
                "   - Организовать работы по локализации;\n"
                "   - Обеспечить безопасность персонала;\n"
                "   - Связаться с аварийными службами.\n\n"
                "4. Электрик:\n"
                "   - Отключить электроэнергии в зоне аварии;\n"
                "   - Обеспечить электроснабжение аварийных служб;\n"
                "   - Контролировать за искрообразованием."
            ),
        },
        "section_12": {
            "title": "Мероприятия по обеспечению безопасности населения",
            "text": (
                "Мероприятия по обеспечению безопасности населения при аварии "
                "на сети газопотребления:\n\n"
                "1. Оповещение населения:\n"
                "   - Система оповещения через громкоговорящую связь;\n"
                "   - Оповещение через дежурные службы;\n"
                "   - Информирование через СМИ.\n\n"
                "2. Эвакуация:\n"
                "   - Эвакуация из зоны поражения (радиус — определяется расчётом);\n"
                "   - Эвакуация через обозначенные маршруты;\n"
                "   - Сборный пункт — определённый объект.\n\n"
                "3. Медицинская помощь:\n"
                "   - Организация медицинского пункта;\n"
                "   - Сортировка пострадавших;\n"
                "   - Эвакуация в медицинские учреждения.\n\n"
                "4. Меры по защите населения:\n"
                "   - Запрет на использование открытого огня;\n"
                "   - Запрет на включение электрооборудования;\n"
                "   - Рекомендации по защите органов дыхания."
            ),
        },
    },
}

# Дефолтные правила для неизвестных типов ОПО
DEFAULT_RULES = {
    "section_5": {
        "title": "Организация взаимодействия сил и средств",
        "text": (
            "Взаимодействие сил и средств при локализации и ликвидации аварий "
            "осуществляется в соответствии с планом взаимодействия, утверждённым "
            "руководителем организации.\n\n"
            "Основные принципы: единоначалие, взаимная информированность, "
            "координация действий, безопасность персонала."
        ),
    },
    "section_7": {
        "title": "Порядок обеспечения готовности сил и средств",
        "text": (
            "Готовность сил и средств обеспечивается:\n"
            "1. Ежедневной проверкой технических средств;\n"
            "2. Ежемесячными тренировками;\n"
            "3. Ежегодной аттестацией персонала;\n"
            "4. Плановым техническим обслуживанием оборудования."
        ),
    },
    "section_9": {
        "title": "Система взаимного обмена информацией",
        "text": (
            "Обмен информацией осуществляется через:\n"
            "1. Диспетчерскую связь;\n"
            "2. Мобильную связь;\n"
            "3. Радиосвязь;\n"
            "4. Громкоговорящую связь."
        ),
    },
    "section_10": {
        "title": "Первоочередные действия по локализации и ликвидации аварий",
        "text": (
            "Первоочередные действия:\n"
            "1. Немедленно сообщить диспетчеру;\n"
            "2. Перекрыть источник аварии;\n"
            "3. Эвакуировать людей;\n"
            "4. Вызвать аварийные службы;\n"
            "5. Оцепить зону аварии."
        ),
    },
    "section_11": {
        "title": "Действия производственного персонала при угрозе и возникновении аварий",
        "text": (
            "Действия персонала:\n"
            "1. Диспетчер — координация и оповещение;\n"
            "2. Работник — перекрытие, эвакуация;\n"
            "3. Руководитель — общее руководство;\n"
            "4. Электрик — отключение электроэнергии."
        ),
    },
    "section_12": {
        "title": "Мероприятия по обеспечению безопасности населения",
        "text": (
            "Мероприятия по защите населения:\n"
            "1. Оповещение через систему оповещения;\n"
            "2. Эвакуация из зоны поражения;\n"
            "3. Медицинская помощь пострадавшим;\n"
            "4. Запрет на использование открытого огня."
        ),
    },
}


class RulesEngine(BaseEngine):
    """
    Движок правил. Генерирует параметризованные тексты для разделов,
    которые зависят от типа ОПО и класса опасности, но не требуют LLM.

    Обрабатывает 6 разделов: взаимодействие, готовность, обмен информацией,
    первоочередные действия, действия персонала, безопасность населения.
    """

    @property
    def name(self) -> str:
        return "rules"

    def can_handle(self, section_id: str) -> bool:
        return section_id in RULES_SECTIONS

    async def generate(self, section_id: str, section_def: dict, context: DocumentContext) -> SectionContent:
        """Генерирует содержимое раздела на основе правил по типу ОПО."""
        title = section_def.get("title", section_id)
        facility_type = context.facility.get("facility_type", "")

        rules = FACILITY_RULES.get(facility_type, DEFAULT_RULES)
        section_rules = rules.get(section_id)

        if section_rules is None:
            section_rules = DEFAULT_RULES.get(section_id, {"title": title, "text": f"[Правила не найдены для {section_id}]"})

        blocks = self._render_section(section_id, section_rules, context)

        return SectionContent(
            section_id=section_id,
            title=title,
            engine_name=self.name,
            blocks=blocks,
            metadata={"facility_type": facility_type, "rules_source": "deterministic"},
        )

    def _render_section(self, section_id: str, rules: dict, context: DocumentContext) -> list[Block]:
        """Рендерит раздел с подстановкой данных из контекста и справочников."""
        blocks: list[Block] = []

        facility_type = context.facility.get("facility_type", "")

        # Секции, которые обогащаются справочниками
        if section_id == "section_10":
            return self._render_section_10(facility_type, context)
        elif section_id == "section_11":
            return self._render_section_11(facility_type, context)
        elif section_id == "section_12":
            return self._render_section_12(facility_type, context)

        text = rules.get("text", "")
        for paragraph in text.split("\n\n"):
            stripped = paragraph.strip()
            if stripped:
                blocks.append(ParagraphBlock(text=stripped))

        return blocks

    def _render_section_10(self, facility_type: str, ctx: DocumentContext) -> list[Block]:
        """Раздел 10 — Первоочередные действия (из справочника сценариев)."""
        blocks: list[Block] = []

        instructions = get_scenario_instructions(facility_type)
        if not instructions:
            instructions = get_scenario_instructions("Сеть газопотребления")

        if instructions:
            blocks.append(ParagraphBlock(text=(
                "Первоочередные действия по локализации и ликвидации аварий "
                f"на объекте типа «{facility_type}» определяются следующими сценариями:"
            )))

            for scenario in instructions:
                code = scenario.get("code", "")
                name = scenario.get("name", "")
                blocks.append(ParagraphBlock(text=f"{code} — {name}", bold=True))

                # Признаки аварии
                signs = scenario.get("signs", [])
                if signs:
                    blocks.append(ParagraphBlock(text="Признаки аварии:", bold=True))
                    for i, s in enumerate(signs, 1):
                        blocks.append(ParagraphBlock(text=f"{i}. {s}"))

                # Защитные мероприятия
                protection = scenario.get("protection_methods", [])
                if protection:
                    blocks.append(ParagraphBlock(text="Защитные мероприятия:", bold=True))
                    for i, p in enumerate(protection, 1):
                        blocks.append(ParagraphBlock(text=f"{i}. {p}"))

                # Технические средства
                means = scenario.get("technical_means", [])
                if means:
                    blocks.append(ParagraphBlock(text="Технические средства:", bold=True))
                    for m in means:
                        blocks.append(ParagraphBlock(text=f"- {m}"))

                # Действия по ролям
                actions = scenario.get("actions", [])
                if actions:
                    blocks.append(ParagraphBlock(text="Порядок действий:", bold=True))
                    for i, a in enumerate(actions, 1):
                        blocks.append(ParagraphBlock(text=f"{i}. {a}"))

                blocks.append(ParagraphBlock(text=""))
        else:
            blocks.append(ParagraphBlock(text="Детальные инструкции по сценариям не найдены."))
            fallback = DEFAULT_RULES.get("section_10", {})
            text = fallback.get("text", "")
            for paragraph in text.split("\n\n"):
                stripped = paragraph.strip()
                if stripped:
                    blocks.append(ParagraphBlock(text=stripped))

        return blocks

    def _render_section_11(self, facility_type: str, ctx: DocumentContext) -> list[Block]:
        """Раздел 11 — Действия персонала (из справочника должностей)."""
        blocks: list[Block] = []

        positions = get_positions()
        if positions:
            blocks.append(ParagraphBlock(text=(
                "Действия производственного персонала при угрозе и возникновении аварий "
                "определяются должностными обязанностями по плану ликвидации аварий:"
            )))

            for pos in positions:
                title = pos.get("title", "")
                desc = pos.get("description", "")
                blocks.append(ParagraphBlock(text=f"{title}", bold=True))
                blocks.append(ParagraphBlock(text=desc))
                blocks.append(ParagraphBlock(text=""))

            # Дополнительные действия из контекста
            persons = ctx.persons or ctx.personnel
            if persons:
                blocks.append(ParagraphBlock(text="Ответственные лица на объекте:", bold=True))
                for p in persons:
                    blocks.append(ParagraphBlock(text=(
                        f"- {p.get('full_name', '—')} — {p.get('position', '—')}, "
                        f"тел. {p.get('phone', '—')}"
                    )))
        else:
            fallback = DEFAULT_RULES.get("section_11", {})
            text = fallback.get("text", "")
            for paragraph in text.split("\n\n"):
                stripped = paragraph.strip()
                if stripped:
                    blocks.append(ParagraphBlock(text=stripped))

        return blocks

    def _render_section_12(self, facility_type: str, ctx: DocumentContext) -> list[Block]:
        """Раздел 12 — Безопасность населения (из справочника служб оповещения)."""
        blocks: list[Block] = []

        template = get_notification_services(facility_type) if facility_type else get_notification_services("default")
        fac = ctx.facility

        blocks.append(ParagraphBlock(text=f"Объект: {fac.get('name', '—')}"))
        blocks.append(ParagraphBlock(text=f"Адрес: {fac.get('address', '—')}"))
        blocks.append(ParagraphBlock(text=f"Класс опасности: {fac.get('hazard_class', '—')}"))
        blocks.append(ParagraphBlock(text=""))

        blocks.append(ParagraphBlock(text="1. Оповещение населения:", bold=True))
        blocks.append(ParagraphBlock(text=(
            "Оповещение населения осуществляется через:\n"
            "- Систему оповещения через громкоговорящую связь;\n"
            "- Оповещение через дежурные службы;\n"
            "- Информирование через СМИ."
        )))

        blocks.append(ParagraphBlock(text="2. Эвакуация:", bold=True))
        blocks.append(ParagraphBlock(text=(
            "- Эвакуация из зоны поражения (радиус определяется расчётом);\n"
            "- Эвакуация через обозначенные маршруты;\n"
            "- Сборный пункт — определённый объект."
        )))

        blocks.append(ParagraphBlock(text="3. Медицинская помощь:", bold=True))
        blocks.append(ParagraphBlock(text=(
            "- Организация медицинского пункта;\n"
            "- Сортировка пострадавших;\n"
            "- Эвакуация в медицинские учреждения."
        )))

        # Таблица служб оповещения
        if template:
            blocks.append(ParagraphBlock(text="4. Службы оповещения:", bold=True))
            rows = []
            for item in template.get("internal", []):
                rows.append([
                    str(item.get("order", "")),
                    item.get("position", ""),
                    "Внутренняя",
                    item.get("phone_primary", "—"),
                ])
            for item in template.get("external", []):
                rows.append([
                    str(item.get("order", "")),
                    item.get("service", ""),
                    "Внешняя",
                    item.get("phone_primary", "—"),
                ])
            if rows:
                blocks.append(TableBlock(
                    headers=["№", "Должность / Служба", "Тип", "Телефон"],
                    rows=rows,
                    caption="Службы оповещения",
                ))

        blocks.append(ParagraphBlock(text="4. Меры по защите населения:", bold=True))
        blocks.append(ParagraphBlock(text=(
            "- Запрет на использование открытого огня;\n"
            "- Запрет на включение электрооборудования;\n"
            "- Рекомендации по защите органов дыхания."
        )))

        return blocks
