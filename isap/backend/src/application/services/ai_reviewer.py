"""AI-ревьюер ПМЛА — проверка документа по чек-листу."""
import json
import logging

from src.application.services.types import AIReviewItem, AIReviewResult
from src.infrastructure.llm.providers import LLMMessage, LLMProvider

logger = logging.getLogger(__name__)

REVIEW_CHECKLIST = [
    {"id": 1, "name": "Сценарии соответствуют типу ОПО", "prompt": "Проверь, что каждый сценарий аварии соответствует типу опасного производственного объекта и классу опасности."},
    {"id": 2, "name": "Сценарии содержат причину, развитие, зоны", "prompt": "Для каждого сценария проверь наличие: причины аварии, развития аварии, зон поражения."},
    {"id": 3, "name": "Зоны поражения совпадают с расчётами", "prompt": "Проверь, что описанные зоны поражения (смертельная, тяжёлая, лёгкая) совпадают с расчётными данными."},
    {"id": 4, "name": "Мероприятия привязаны к сценариям", "prompt": "Проверь, что каждое мероприятие по ликвидации аварии привязано к конкретному сценарию."},
    {"id": 5, "name": "СИЗ соответствуют классу опасности", "prompt": "Проверь, что средства индивидуальной защиты соответствуют классу опасности объекта."},
    {"id": 6, "name": "Системы защиты учтены", "prompt": "Проверь, что противопожарные системы, системы оповещения и газоспасательной службы учтены."},
    {"id": 7, "name": "Алгоритм действий логичен", "prompt": "Проверь логичность и последовательность алгоритма действий персонала при аварии."},
    {"id": 8, "name": "Ответственные лица присутствуют", "prompt": "Проверь, что все ответственные лица из данных организации указаны в документе."},
    {"id": 9, "name": "Порядок оповещения указан", "prompt": "Проверь наличие порядка оповещения при аварии (кого, когда, как оповещать)."},
    {"id": 10, "name": "Аварийные службы совпадают с справочником", "prompt": "Проверь, что указанные аварийные службы (пожарные, скорая, газовая) соответствуют ближайшим службам по координатам объекта."},
    {"id": 11, "name": "Разделы не противоречат друг другу", "prompt": "Проверь отсутствие противоречий между разделами документа."},
]


class AIReviewer:
    """AI-ревьюер ПМЛА с чек-листом из 11 пунктов."""

    def __init__(self, llm: LLMProvider | None):
        self._llm = llm

    async def review(
        self,
        rendered_sections: dict[str, str],
        context: dict,
    ) -> AIReviewResult:
        """
        Запуск AI-ревью документа.
        Возвращает AIReviewResult с оценкой по каждому пункту чек-листа.
        """
        if self._llm is None:
            return AIReviewResult(
                overall_confidence=0.0,
                decision="escalate_to_human",
                summary="LLM недоступен — AI-ревью невозможен",
            )

        # Собираем текст документа для анализа
        doc_text = self._prepare_document_text(rendered_sections, context)

        items = []
        for check in REVIEW_CHECKLIST:
            item = await self._check_item(check, doc_text, context)
            items.append(item)

        # Расчёт общей уверенности
        if items:
            overall = sum(i.confidence for i in items) / len(items)
        else:
            overall = 0.0

        # Определение решения
        failed = [i for i in items if not i.passed]
        low_confidence = [i for i in items if i.confidence < 0.6]

        if overall >= 0.85 and len(failed) == 0:
            decision = "auto_approve"
        elif len(low_confidence) > 3 or overall < 0.5:
            decision = "needs_revision"
        else:
            decision = "escalate_to_human"

        summary = self._build_summary(items, overall, decision)

        return AIReviewResult(
            overall_confidence=round(overall, 2),
            decision=decision,
            items=items,
            summary=summary,
        )

    async def _check_item(
        self, check: dict, doc_text: str, context: dict
    ) -> AIReviewItem:
        """Проверка одного пункта чек-листа через LLM."""
        try:
            facility = context.get("facility", {})
            prompt = f"""Ты — эксперт по промышленной безопасности. Проверь раздел ПМЛА.

Тип объекта: {facility.get('facility_type', '—')}
Класс опасности: {facility.get('hazard_class', '—')}

Текст документа:
{doc_text[:3000]}

Задание: {check['prompt']}

Оцени по шкале 0-1:
- confidence: уверенность в оценке (0.0-1.0)
- passed: прошёл ли проверку (true/false)
- details: краткое пояснение (1-2 предложения)

Ответ ТОЛЬКО в формате JSON:
{{"confidence": 0.9, "passed": true, "details": "Пункт пройден"}}"""

            messages = [LLMMessage(role="user", content=prompt)]
            response = await self._llm.complete(messages, temperature=0.3)
            result = self._parse_response(response.content)

            return AIReviewItem(
                check_id=check["id"],
                check_name=check["name"],
                passed=result.get("passed", False),
                confidence=result.get("confidence", 0.5),
                details=result.get("details", ""),
            )
        except Exception as e:
            logger.warning("AI review check %d failed: %s", check["id"], e)
            return AIReviewItem(
                check_id=check["id"],
                check_name=check["name"],
                passed=False,
                confidence=0.0,
                details=f"Ошибка: {e}",
            )

    def _prepare_document_text(
        self, rendered_sections: dict[str, str | list], context: dict
    ) -> str:
        """Подготовка текста документа для анализа."""
        parts = []
        for title, value in rendered_sections.items():
            if isinstance(value, str):
                text = value[:500]
            elif isinstance(value, list):
                # Блоки → текст
                lines = []
                for b in value:
                    if hasattr(b, "text"):
                        lines.append(b.text)
                    elif hasattr(b, "headers"):
                        lines.append(" ".join(b.headers))
                text = "\n".join(lines)[:500]
            else:
                text = str(value)[:500]
            parts.append(f"=== {title} ===\n{text}")
        return "\n\n".join(parts)

    def _parse_response(self, response: str) -> dict:
        """Парсинг ответа LLM."""
        try:
            text = response.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            return json.loads(text)
        except (json.JSONDecodeError, IndexError):
            return {"confidence": 0.5, "passed": False, "details": "Не удалось распознать ответ"}

    def _build_summary(
        self, items: list[AIReviewItem], overall: float, decision: str
    ) -> str:
        """Построение сводки ревью."""
        passed = sum(1 for i in items if i.passed)
        failed = [i for i in items if not i.passed]

        lines = [
            f"AI-ревью: {passed}/{len(items)} пунктов пройдено",
            f"Общая уверенность: {overall:.0%}",
            f"Решение: {decision}",
        ]

        if failed:
            lines.append("\nПроблемные пункты:")
            for i in failed:
                lines.append(f"  - [{i.check_id}] {i.check_name}: {i.details}")

        return "\n".join(lines)
