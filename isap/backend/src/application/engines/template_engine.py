"""Template Engine — чистые Jinja2-шаблоны без AI."""
from __future__ import annotations

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from src.application.engines.base import BaseEngine, DocumentContext, SectionContent
from src.application.engines.blocks import ParagraphBlock, Block

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent.parent.parent.parent / "templates"

# Разделы, которые обрабатывает Template Engine (10 разделов, 0% AI).
# Эти шаблоны не требуют LLM — только подстановка данных из контекста.
TEMPLATE_SECTIONS = {
    "title_page",           # Титульный лист
    "correction_log",       # Журнал корректировки
    "toc",                  # Содержание
    "abbreviations",        # Обозначения и сокращения
    "terms",                # Термины и определения
    "appendix_1",           # Порядок изучения ПМЛА
    "appendix_2",           # Форма оперативного сообщения
    "appendix_5",           # Схема оповещения
    "bibliography",         # Список литературы
    "familiarization_sheet",# Лист ознакомления
}


class TemplateEngine(BaseEngine):
    """
    Движок чистых шаблонов. Загружает Jinja2-шаблон по section_id
    и рендерит его с данными из DocumentContext.

    Используется для разделов, где нет расчётных данных и не нужен AI:
    титульный лист, оглавление, обозначения, термины, приложения и т.д.
    """

    def __init__(self, templates_dir: Path | None = None):
        self._templates_dir = templates_dir or TEMPLATES_DIR
        self._env = Environment(
            loader=FileSystemLoader(str(self._templates_dir / "pmla")),
            autoescape=False,
        )
        # Глобальный фильтр finalize: None → пустая строка
        self._env.filters["finalize"] = lambda x: "" if x is None else x

    @property
    def name(self) -> str:
        return "template"

    def can_handle(self, section_id: str) -> bool:
        return section_id in TEMPLATE_SECTIONS

    async def generate(self, section_id: str, section_def: dict, context: DocumentContext) -> SectionContent:
        """Рендерит Jinja2-шаблон с данными из контекста."""
        template_name = section_def.get("template", "")
        title = section_def.get("title", section_id)

        if not template_name:
            logger.warning("No template specified for section '%s'", section_id)
            return SectionContent(
                section_id=section_id,
                title=title,
                engine_name=self.name,
                blocks=[ParagraphBlock(text=f"[Шаблон не указан для раздела {section_id}]")],
            )

        try:
            template = self._env.get_template(template_name)
            rendered = template.render(**context.to_dict())
        except Exception as e:
            logger.error("Template render failed for '%s': %s", section_id, e)
            rendered = f"[Ошибка рендеринга шаблона {template_name}: {e}]"

        blocks = [ParagraphBlock(text=line) for line in rendered.split("\n") if line.strip()]

        return SectionContent(
            section_id=section_id,
            title=title,
            engine_name=self.name,
            blocks=blocks,
            metadata={"template": template_name},
        )
