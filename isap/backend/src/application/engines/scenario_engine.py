"""Scenario Engine — детерминированная генерация сценариев аварий."""
from __future__ import annotations

import json
import logging
from pathlib import Path

from src.application.engines.base import BaseEngine, DocumentContext, SectionContent
from src.application.engines.blocks import (
    Block,
    HeadingBlock,
    ParagraphBlock,
    TableBlock,
)

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent.parent.parent.parent / "templates"

# Разделы, которые обрабатывает Scenario Engine
SCENARIO_SECTIONS = {"section_2", "special_section"}

# Кэш загруженных шаблонов сценариев
_SCENARIO_TEMPLATES_CACHE: dict[str, dict] = {}


def _load_scenario_templates(facility_type: str) -> dict | None:
    """Загружает шаблон сценариев для указанного типа ОПО."""
    if facility_type in _SCENARIO_TEMPLATES_CACHE:
        return _SCENARIO_TEMPLATES_CACHE[facility_type]

    templates_dir = TEMPLATES_DIR / "pmla" / "scenario_templates"
    if not templates_dir.exists():
        return None

    # Ищем файл по типу объекта
    for json_file in templates_dir.glob("*.json"):
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
            if data.get("facility_type", "").lower() == facility_type.lower():
                _SCENARIO_TEMPLATES_CACHE[facility_type] = data
                return data
        except (json.JSONDecodeError, KeyError):
            continue

    # Если точное совпадение не найдено, ищем частичное
    for json_file in templates_dir.glob("*.json"):
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
            template_type = data.get("facility_type", "").lower()
            if template_type in facility_type.lower() or facility_type.lower() in template_type:
                _SCENARIO_TEMPLATES_CACHE[facility_type] = data
                return data
        except (json.JSONDecodeError, KeyError):
            continue

    return None


def _select_scenarios_from_template(
    template_data: dict,
    facility_type: str,
    hazard_class: str | int,
) -> list[dict]:
    """
    Выбирает сценарии из шаблона по facility_type и hazard_class.
    Для 3 класса опасности — все сценарии.
    Для 1-2 класса — все сценарии + дополнительные меры.
    """
    all_scenarios = template_data.get("scenarios", [])
    # Пока возвращаем все сценарии из шаблона.
    # В будущем: фильтрация по классу опасности.
    return all_scenarios


def _normalize_context_scenarios(scenarios: list) -> list[dict]:
    """Normalize questionnaire/user scenarios into the table shape used here."""
    normalized: list[dict] = []
    for i, scenario in enumerate(scenarios or [], 1):
        if isinstance(scenario, dict):
            name = scenario.get("name") or scenario.get("title") or f"Сценарий {i}"
            description = scenario.get("description") or scenario.get("causes") or "—"
            source = (
                scenario.get("sources")
                or scenario.get("source_equipment")
                or scenario.get("equipment")
                or scenario.get("place")
                or "—"
            )
            consequences = scenario.get("consequences") or scenario.get("factors") or "—"
            normalized.append(
                {
                    "code": scenario.get("code") or scenario.get("id") or f"Q-{i}",
                    "name": name,
                    "sources": source,
                    "causes": description,
                    "signs": scenario.get("signs") or consequences,
                    "factors": consequences,
                    "protection": scenario.get("protection") or "—",
                    "technical_means": scenario.get("technical_means") or scenario.get("response_actions") or "—",
                    "executors": scenario.get("executors") or scenario.get("personnel_actions") or "—",
                    "actions": scenario.get("actions") or description,
                    "category": scenario.get("category") or "questionnaire",
                    # Дополнительные поля из анкеты для качественного рендера
                    "place": scenario.get("place") or scenario.get("source_equipment") or "",
                    "equipment": scenario.get("equipment") or "",
                    "hazardous_substance": scenario.get("hazardous_substance") or "",
                }
            )
        else:
            normalized.append(
                {
                    "code": f"Q-{i}",
                    "name": str(scenario),
                    "sources": "—",
                    "causes": "—",
                    "signs": "—",
                    "factors": "—",
                    "category": "questionnaire",
                    "place": "",
                    "equipment": "",
                    "hazardous_substance": "",
                }
            )
    return normalized


class ScenarioEngine(BaseEngine):
    """
    Движок сценариев аварий. Генерирует:
    - Таблицы 4-6 (раздел 2): матрица сценариев, источники, описания
    - Таблицу 15 (специальный раздел): действия по каждому сценарию

    Использует предопределённые шаблоны сценариев для каждого типа ОПО
    вместо LLM-генерации.
    """

    @property
    def name(self) -> str:
        return "scenario"

    def can_handle(self, section_id: str) -> bool:
        return section_id in SCENARIO_SECTIONS

    async def generate(self, section_id: str, section_def: dict, context: DocumentContext) -> SectionContent:
        """Генерирует содержимое сценарного раздела."""
        facility = context.facility
        facility_type = facility.get("facility_type", "")
        hazard_class = str(facility.get("hazard_class", ""))
        title = section_def.get("title", section_id)

        # Загружаем шаблон сценариев для типа ОПО
        template_data = _load_scenario_templates(facility_type)
        if template_data is None and not context.scenarios:
            logger.warning("No scenario template found for facility_type '%s'", facility_type)
            return SectionContent(
                section_id=section_id,
                title=title,
                engine_name=self.name,
                blocks=[ParagraphBlock(text=f"[Шаблон сценариев не найден для типа ОПО: {facility_type}]")],
            )

        # Выбираем сценарии
        scenarios = []
        if template_data is not None:
            scenarios.extend(_select_scenarios_from_template(template_data, facility_type, hazard_class))
        scenarios.extend(_normalize_context_scenarios(context.scenarios))

        if section_id == "section_2":
            blocks = self._render_section_2(scenarios, context)
        elif section_id == "special_section":
            blocks = self._render_special_section(scenarios, context)
        else:
            blocks = [ParagraphBlock(text=f"[Неизвестный section_id: {section_id}]")]

        return SectionContent(
            section_id=section_id,
            title=title,
            engine_name=self.name,
            blocks=blocks,
            metadata={
                "scenario_count": len(scenarios),
                "facility_type": facility_type,
            },
        )

    @staticmethod
    def _render_custom_scenario_narrative(scenario: dict, idx: int) -> list[Block]:
        """Рендерит кастомный сценарий из анкеты в виде связного текста."""
        blocks: list[Block] = []
        name = scenario.get("name", f"Сценарий {idx}")
        blocks.append(ParagraphBlock(text=f"Сценарий: {name}.", bold=True))

        place = scenario.get("place", "")
        if place:
            blocks.append(ParagraphBlock(text=f"Место возможного возникновения аварии: {place}."))
        equipment = scenario.get("equipment", "")
        if equipment:
            blocks.append(ParagraphBlock(text=f"Задействованное оборудование: {equipment}."))
        substance = scenario.get("hazardous_substance", "")
        if substance:
            blocks.append(ParagraphBlock(text=f"Опасное вещество: {substance}."))
        consequences = scenario.get("consequences", "")
        if consequences:
            blocks.append(ParagraphBlock(text=f"Возможные последствия: {consequences}."))
        description = scenario.get("description", "") or scenario.get("causes", "")
        if description:
            blocks.append(ParagraphBlock(text=f"Описание сценария: {description}."))
        return blocks

    def _render_section_2(self, scenarios: list[dict], context: DocumentContext) -> list[Block]:
        """
        Рендерит раздел 2 — Сценарии наиболее вероятных аварий.
        Содержит: Таблицу 4 (сценарии по элементам), Таблицу 5 (источники),
        Таблицу 6 (детальные сценарии).
        """
        equipment = context.equipment
        blocks: list[Block] = []

        # Текстовый блок: кастомные сценарии из анкеты
        custom_scenarios = [s for s in scenarios if s.get("category") == "questionnaire"]
        if custom_scenarios:
            blocks.append(ParagraphBlock(text="Сценарии, определённые по результатам анализа объекта:"))
            for i, cs in enumerate(custom_scenarios, 1):
                blocks.extend(self._render_custom_scenario_narrative(cs, i))
            blocks.append(ParagraphBlock(text=""))

        # Таблица 4 — Сценарии по элементам оборудования
        table4_headers = ["№ п/п", "Элемент оборудования", "Наименование сценария", "Вероятность"]
        table4_rows = []
        for i, scenario in enumerate(scenarios, 1):
            # Привязываем сценарии к оборудованию
            eq_name = equipment[i - 1].get("name", "—") if i <= len(equipment) else "—"
            table4_rows.append([
                str(i),
                eq_name,
                scenario.get("name", "—"),
                scenario.get("category", "средняя"),
            ])
        blocks.append(TableBlock(
            headers=table4_headers,
            rows=table4_rows,
            caption="Таблица 4. Сценарии наиболее вероятных аварий по элементам оборудования",
        ))

        # Таблица 5 — Перечень возможных источников и мест аварий
        table5_headers = ["№ п/п", "Наименование источника аварии", "Характерные дефекты", "Сценарий"]
        table5_rows = []
        for i, scenario in enumerate(scenarios, 1):
            table5_rows.append([
                str(i),
                scenario.get("sources", "—"),
                scenario.get("causes", "—"),
                f"С-{i}",
            ])
        blocks.append(TableBlock(
            headers=table5_headers,
            rows=table5_rows,
            caption="Таблица 5. Перечень возможных источников и мест возникновения аварий",
        ))

        # Таблица 6 — Сценарии аварий (детальные описания)
        table6_headers = [
            "№ сценария",
            "Наименование сценария",
            "Источники аварий",
            "Причины аварии",
            "Признаки",
            "Поражающие факторы",
        ]
        table6_rows = []
        for i, s in enumerate(scenarios, 1):
            table6_rows.append([
                s.get("code", f"С-{i}"),
                s.get("name", "—"),
                s.get("sources", "—"),
                s.get("causes", "—"),
                s.get("signs", "—") if isinstance(s.get("signs"), str) else ", ".join(s.get("signs", ["—"])),
                s.get("factors", "—") if isinstance(s.get("factors"), str) else ", ".join(s.get("factors", ["—"])),
            ])
        blocks.append(TableBlock(
            headers=table6_headers,
            rows=table6_rows,
            caption="Таблица 6. Сценарии наиболее вероятных аварий на ОПО",
        ))

        # Блок-схема развития аварий (для каждого сценария)
        for i, scenario in enumerate(scenarios, 1):
            blocks.append(HeadingBlock(text=f"Схема возникновения и развития аварий (Сценарий С-{i})", level=2))
            signs_raw = scenario.get("signs", ["—"])
            signs_text = signs_raw[0] if isinstance(signs_raw, list) and signs_raw else signs_raw if isinstance(signs_raw, str) else "—"
            blocks.append(ParagraphBlock(text=f"Этап 1. Инициирующее событие — {scenario.get('sources', 'повреждение оборудования')}"))
            blocks.append(ParagraphBlock(text=f"Этап 2. Формирование газовоздушной смеси — {scenario.get('causes', 'утечка газа')}"))
            blocks.append(ParagraphBlock(text="Этап 3. Появление источника зажигания — искра, статическое электричество"))
            blocks.append(ParagraphBlock(text="Этап 4. Воспламенение и переход к взрыву/горению"))
            blocks.append(ParagraphBlock(text=f"Этап 5. Поражающие факторы — {signs_text}"))
            blocks.append(ParagraphBlock(text="Этап 6. Вторичные последствия (каскадный эффект)"))
            blocks.append(ParagraphBlock(text="Этап 7. Последствия для персонала и населения"))

        return blocks

    def _render_special_section(self, scenarios: list[dict], context: DocumentContext) -> list[Block]:
        """
        Рендерит специальный раздел — Таблицу 15 с действиями по каждому сценарию.
        Каждый сценарий содержит: опознавательные признаки, способы защиты,
        технические средства, действия персонала.
        """
        blocks: list[Block] = []

        # Таблица 15 — Действия по сценариям
        table15_headers = [
            "№ сценария / Наименование аварийной ситуации",
            "Опознавательные признаки",
            "Оптимальные способы противоаварийной защиты (ПАЗ)",
            "Технические средства, способы локализации и ликвидации",
            "Исполнители и порядок их действий",
        ]
        table15_rows = []
        for i, s in enumerate(scenarios, 1):
            protection = s.get("protection", "—")
            if isinstance(protection, list):
                protection = "; ".join(protection)
            executors = s.get("executors", "—")
            if isinstance(executors, list):
                executors = "; ".join(executors)
            signs = s.get("signs", "—")
            if isinstance(signs, list):
                signs = "; ".join(signs)
            table15_rows.append([
                f"С-{i}. {s.get('name', '—')}",
                signs,
                protection,
                s.get("technical_means", "—"),
                executors,
            ])
        blocks.append(TableBlock(
            headers=table15_headers,
            rows=table15_rows,
            caption="Таблица 15. Первоочередные действия при получении сигнала об аварии на объекте",
        ))

        # Подробное описание действий по каждому сценарию
        for i, scenario in enumerate(scenarios, 1):
            blocks.append(HeadingBlock(text=f"{i}. {scenario.get('name', f'Сценарий С-{i}')}", level=2))

            # Опознавательные признаки
            signs = scenario.get("signs", [])
            if isinstance(signs, list):
                blocks.append(ParagraphBlock(text="Опознавательные признаки:"))
                for j, sign in enumerate(signs, 1):
                    blocks.append(ParagraphBlock(text=f"  {j}) {sign}"))
            else:
                blocks.append(ParagraphBlock(text=f"Опознавательные признаки: {signs}"))

            # Способы защиты
            protection = scenario.get("protection", [])
            if isinstance(protection, list):
                blocks.append(ParagraphBlock(text="Оптимальные способы противоаварийной защиты (ПАЗ):"))
                for j, step in enumerate(protection, 1):
                    blocks.append(ParagraphBlock(text=f"  {j}) {step}"))
            else:
                blocks.append(ParagraphBlock(text=f"Способы защиты: {protection}"))

            # Технические средства
            blocks.append(ParagraphBlock(text="Технические средства, способы локализации и ликвидации:"))
            blocks.append(ParagraphBlock(text=f"  {scenario.get('technical_means', '—')}"))

            # Действия персонала
            executors = scenario.get("executors", [])
            if isinstance(executors, list):
                blocks.append(ParagraphBlock(text="Исполнители и порядок их действий:"))
                for j, executor in enumerate(executors, 1):
                    blocks.append(ParagraphBlock(text=f"  {j}) {executor}"))
            else:
                blocks.append(ParagraphBlock(text=f"Действия персонала: {executors}"))

            # Полный порядок действий
            actions = scenario.get("actions", "")
            if actions:
                blocks.append(ParagraphBlock(text="Порядок действий:"))
                blocks.append(ParagraphBlock(text=f"  {actions}"))

        return blocks
