"""Narrative Engine — AI-движок для описательного текста (только introduction)."""
from __future__ import annotations

import logging

from src.application.engines.base import BaseEngine, DocumentContext, SectionContent
from src.application.engines.blocks import ParagraphBlock, Block

logger = logging.getLogger(__name__)

NARRATIVE_SECTIONS = {"introduction"}


class NarrativeEngine(BaseEngine):
    """
    Движок описательного текста. Генерирует связный текст через LLM
    для разделов, где требуются аналитические описания.

    В текущей реализации обрабатывает только introduction (цели и задачи).
    """

    def __init__(self, llm_provider=None, retriever=None):
        self._llm = llm_provider
        self._retriever = retriever

    @property
    def name(self) -> str:
        return "narrative"

    def can_handle(self, section_id: str) -> bool:
        return section_id in NARRATIVE_SECTIONS

    async def generate(self, section_id: str, section_def: dict, context: DocumentContext) -> SectionContent:
        title = section_def.get("title", section_id)

        if self._llm is not None:
            try:
                content = await self._generate_via_llm(section_def, context)
                blocks = [ParagraphBlock(text=line) for line in content.split("\n") if line.strip()]
                return SectionContent(
                    section_id=section_id,
                    title=title,
                    engine_name=self.name,
                    blocks=blocks,
                    metadata={"source": "llm"},
                )
            except Exception as e:
                logger.warning("LLM generation failed for '%s': %s", section_id, e)

        blocks = self._generate_fallback(section_id, context)
        return SectionContent(
            section_id=section_id,
            title=title,
            engine_name=self.name,
            blocks=blocks,
            metadata={"source": "fallback"},
        )

    async def _generate_via_llm(self, section_def: dict, context: DocumentContext) -> str:
        from src.infrastructure.llm.providers import LLMMessage
        from src.application.services.prompts import SYSTEM_PROMPT

        facility = context.facility
        org = context.organization

        user_prompt = (
            f"Составь раздел «Введение» для ПМЛА (План мероприятий по ликвидации аварий) "
            f"для объекта «{facility.get('name', 'объект')}» "
            f"типа «{facility.get('facility_type', '—')}» "
            f"{facility.get('hazard_class', '—')} класса опасности.\n"
            f"Организация: {org.get('name', '—')}\n"
            f"Адрес: {facility.get('address', '—')}\n\n"
            f"Раздел должен содержать:\n"
            f"1. Нормативную базу (ФЗ-116, Постановление Правительства РФ №1437, "
            f"Приказ Ростехнадзора №531)\n"
            f"2. Цели и задачи ПМЛА\n"
            f"3. Область применения\n\n"
            f"Формат: текст, 3-5 абзацев. Без Markdown-разметки."
        )

        response = await self._llm.complete(
            messages=[
                LLMMessage(role="system", content=SYSTEM_PROMPT),
                LLMMessage(role="user", content=user_prompt),
            ]
        )
        content = response.content.strip()
        content = content.replace("**", "").replace("##", "").replace("#", "")
        return content

    def _generate_fallback(self, section_id: str, context: DocumentContext) -> list[Block]:
        facility = context.facility
        org = context.organization
        fac_name = facility.get("name", "объект")
        fac_type = facility.get("facility_type", "—")
        hazard_class = facility.get("hazard_class", "—")
        org_name = org.get("name", "организация")
        address = facility.get("address", "—")

        if section_id == "introduction":
            return [
                ParagraphBlock(text=(
                    f"Настоящий План мероприятий по локализации и ликвидации последствий аварий "
                    f"(далее — ПМЛА) разработан для {fac_name} ({fac_type}, "
                    f"{hazard_class} класс опасности), эксплуатируемого {org_name}, "
                    f"расположенного по адресу: {address}."
                )),
                ParagraphBlock(text=(
                    f"ПМЛА разработан на основании:\n"
                    f"- Федерального закона от 21.07.1997 № 116-ФЗ «О промышленной безопасности "
                    f"опасных производственных объектов»;\n"
                    f"- Постановления Правительства РФ от 15.09.2020 № 1437 «О федеральном "
                    f"государственном надзоре в области промышленной безопасности»;\n"
                    f"- Приказа Ростехнадзора от 11.12.2020 № 472 «Об утверждении Федеральных "
                    f"норм и правил в области промышленной безопасности «Требования к разработке "
                    f"планов мероприятий по ликвидации аварий на опасных производственных "
                    f"объектах»»;\n"
                    f"- Приказа Ростехнадзора от 15.12.2020 № 531 «Об утверждении Федеральных "
                    f"норм и правил в области промышленной безопасности «Порядок расследования "
                    f"и учёта несчастных случаев на производстве»»."
                )),
                ParagraphBlock(text=(
                    f"Целью разработки ПМЛА является обеспечение готовности организации к "
                    f"локализации и ликвидации последствий аварий на опасном производственном "
                    f"объекте, минимизация их масштаба и последствий."
                )),
                ParagraphBlock(text=(
                    f"Задачами ПМЛА являются:\n"
                    f"- определение сценариев наиболее вероятных аварий;\n"
                    f"- расчёт необходимых сил и средств для ликвидации аварий;\n"
                    f"- разработка мероприятий по локализации и ликвидации последствий аварий;\n"
                    f"- определение порядка оповещения и взаимодействия служб."
                )),
                ParagraphBlock(text=(
                    f"Настоящий ПМЛА действует на территории {org_name} и является "
                    f"обязательным для исполнения всеми работниками организации."
                )),
            ]

        return [ParagraphBlock(text=f"[Раздел {section_id} не поддерживается NarrativeEngine]")]
