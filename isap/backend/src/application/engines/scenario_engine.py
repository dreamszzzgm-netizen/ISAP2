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
    # facility_type может прийти как None, если в карточке ОПО тип не заполнен.
    # Без этой защиты последующий .lower() падает с AttributeError.
    if not facility_type:
        return None
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
        facility_type = facility.get("facility_type") or ""
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

        # RAG context injection for generated sections
        rag_used = False
        rag_chunks_count = 0
        rag_sources: list[str] = []
        rag_ctx = context.rag_contexts.get(section_id)
        if rag_ctx and rag_ctx.get("chunks"):
            rag_blocks = self._inject_rag_context(rag_ctx, section_id)
            if rag_blocks:
                blocks.extend(rag_blocks)
                rag_used = True
                rag_chunks_count = len(rag_ctx["chunks"])
                rag_sources = [c.get("source_title", "") for c in rag_ctx["chunks"]]

        return SectionContent(
            section_id=section_id,
            title=title,
            engine_name=self.name,
            blocks=blocks,
            metadata={
                "scenario_count": len(scenarios),
                "facility_type": facility_type,
                "rag_used": rag_used,
                "rag_chunks_count": rag_chunks_count,
                "rag_sources": rag_sources,
            },
        )

    def _inject_rag_context(self, rag_ctx: dict, section_id: str) -> list[Block]:
        """Inject RAG context as additional paragraphs. Same logic as RulesEngine."""
        from src.infrastructure.export.docx_helpers import sanitize_cyrillic_text, strip_html

        blocks: list[Block] = []
        chunks = rag_ctx.get("chunks", [])
        max_chunks = 3
        max_chars_per_chunk = 800
        max_total_chars = 2000
        total_chars = 0

        for chunk in chunks[:max_chunks]:
            text = chunk.get("text", "")
            if not text:
                continue
            text = strip_html(text)
            text = sanitize_cyrillic_text(text)
            text = text.strip()
            if len(text) > max_chars_per_chunk:
                text = text[:max_chars_per_chunk] + "..."
            if total_chars + len(text) > max_total_chars:
                break
            if text:
                blocks.append(ParagraphBlock(text=text))
                total_chars += len(text)

        return blocks

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

        # Расчётные параметры зон поражения (из context.calculation_results).
        # Выводим только успешные расчёты; ошибочные пропускаем.
        calc_results = getattr(context, "calculation_results", None) or []
        valid_calcs = [c for c in calc_results if c.get("validation_status") != "error"]
        if valid_calcs:
            blocks.append(HeadingBlock(text="Расчётные параметры зон поражения", level=2))
            method_titles = {
                "thermal_radiation_v1": "Тепловое излучение",
                "tnt_equivalent_v1": "Взрыв (ТНТ-эквивалент)",
                "toxic_dispersion_v1": "Токсическое поражение",
            }
            for calc in valid_calcs:
                method_id = calc.get("method_id", "—")
                substance = calc.get("substance") or "—"
                results = calc.get("results") or {}
                title = method_titles.get(method_id, method_id)
                blocks.append(ParagraphBlock(text=f"{title} — вещество: {substance}.", bold=True))
                if method_id == "thermal_radiation_v1":
                    zone = results.get("radiation_zone_m")
                    flux = results.get("heat_flux_kw_m2")
                    if zone is not None:
                        blocks.append(ParagraphBlock(text=f"Радиус зоны теплового излучения: {zone} м."))
                    if flux is not None:
                        blocks.append(ParagraphBlock(text=f"Плотность теплового потока на границе: {flux} кВт/м²."))
                elif method_id == "tnt_equivalent_v1":
                    outer = results.get("zone_radius_m")
                    if outer is not None:
                        blocks.append(ParagraphBlock(text=f"Радиус зоны возможного поражения: {outer} м."))
                    zones = results.get("zones") or {}
                    for zone_name, zone_val in zones.items():
                        if zone_val is not None:
                            blocks.append(ParagraphBlock(text=f"{zone_name.capitalize()}: {zone_val} м."))
                elif method_id == "toxic_dispersion_v1":
                    zone = results.get("toxic_zone_m")
                    conc = results.get("concentration_at_boundary")
                    if zone is not None:
                        blocks.append(ParagraphBlock(text=f"Радиус зоны токсического поражения: {zone} м."))
                    if conc is not None:
                        blocks.append(ParagraphBlock(text=f"Концентрация на границе зоны: {conc} мг/м³."))
                else:
                    # Универсальный вывод числовых полей результата.
                    for k, v in results.items():
                        if v is not None and not isinstance(v, (dict, list)):
                            blocks.append(ParagraphBlock(text=f"{k}: {v}."))
            blocks.append(ParagraphBlock(text="Значения получены расчётным путём по утверждённым методикам."))

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
